"""
Capture Review Orchestrator — V0 CLI (no AI/LLM).

This is the main CLI orchestrator for the capture review pipeline.
It coordinates deterministic specialist agents (classifier, knowledge
curator, import planner, QA verifier) to produce proposal packets
for human review before vault import.

All agents are deterministic local Python modules — no external AI/LLM
calls. Proposals are saved to the buffer vault review packets directory.
No direct writes to the canonical LifeOS vault are performed by this
orchestrator.

Usage:
    python3 capture_review_orchestrator.py propose-knowledge --capture latest
    python3 capture_review_orchestrator.py view-proposal --proposal-id <id>
    python3 capture_review_orchestrator.py reject-proposal --proposal-id <id> --reason "..."
    python3 capture_review_orchestrator.py revise-proposal --proposal-id <id> --instruction "..."
    python3 capture_review_orchestrator.py approve-import --proposal-id <id>
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# Ensure the orchestrator package is importable from parent
_ORCHESTRATOR_DIR = Path(__file__).resolve().parent
if str(_ORCHESTRATOR_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_ORCHESTRATOR_DIR.parent))

# Lazy imports to avoid circular issues
from security import (
    PROPOSAL_DIR,
    BUFFER_ROOT,
    VAULT_ROOT,
    KNOWLEDGE_ROOT,
    generate_proposal_id,
    compute_content_hash,
    sanitize_filename,
    sanitize_yaml_body,
    validate_vault_path,
    is_forbidden_output,
)

# --- Action API Client ---

ACTION_API_BASE = "http://localhost:8788"


def _action_api_get(path: str) -> dict:
    """Make a GET request to the Action API and return parsed JSON."""
    url = f"{ACTION_API_BASE}{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            body = {}
        return {"success": False, "error": body.get("error", str(e)), "http_status": e.code}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"Connection error: {e.reason}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _action_api_post(path: str, payload: dict = None) -> dict:
    """Make a POST request to the Action API."""
    url = f"{ACTION_API_BASE}{path}"
    data_bytes = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(url, data=data_bytes, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"success": False, "error": str(e)}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"Connection error: {e.reason}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Capture Resolution ---

def resolve_capture(ref: str) -> dict:
    """Resolve a capture reference to capture data.

    Supports:
    - "latest": fetches the most recent pending capture
    - Numeric index (1-based): fetches by position in pending list
    - Capture ID: fetches by exact capture_id match

    Raises ValueError with a clear message on failure.

    This is a deterministic resolution function — no AI/LLM calls.
    Resolution is via the Action API (localhost:8788).

    Args:
        ref: A reference string — "latest", "1", "cap_xxx_slug", etc.

    Returns:
        A dict with capture data including capture_id, content,
        frontmatter, file_name, etc.

    Raises:
        ValueError: If the capture cannot be found.

    Example:
        >>> # resolve_capture("latest")  # requires Action API running
    """
    if ref == "latest":
        resp = _action_api_get("/captures/pending/latest")
    elif ref.isdigit():
        resp = _action_api_get(f"/captures/pending/{ref}")
    else:
        resp = _action_api_get(f"/captures/{ref}")

    if not resp.get("success") and resp.get("success") is not True:
        error = resp.get("error", "unknown error")
        raise ValueError(f"Failed to resolve capture '{ref}': {error}")

    if resp.get("capture"):
        return resp["capture"]

    # Try alternate response formats
    if "pending" in resp and isinstance(resp["pending"], list):
        pending = resp["pending"]
        if ref == "latest":
            if not pending:
                raise ValueError("No pending captures found.")
            return _action_api_get(f"/captures/pending/{len(pending)}").get("capture", pending[-1])
        if ref.isdigit():
            idx = int(ref) - 1
            if 0 <= idx < len(pending):
                return _action_api_get(f"/captures/pending/{ref}").get("capture", pending[idx])
            raise ValueError(f"Invalid index: {ref} (available: 1-{len(pending)})")

    raise ValueError(f"Unexpected response format when resolving '{ref}'.")


# --- MCP Context Gathering ---

def _gather_mcp_context(capture_data: dict) -> dict:
    """Gather MCP context including capture metadata, template catalog,
    and working state summary. Graceful fallback if MCP is unavailable.

    In V0, MCP tools may not be available. We return whatever we can
    extract from the capture data itself and provide sensible defaults.

    Args:
        capture_data: The resolved capture dict from the Action API.

    Returns:
        A dict with keys: capture_metadata, template_catalog,
        working_state_summary.
    """
    capture_metadata = {
        "capture_id": capture_data.get("capture_id", ""),
        "source": (capture_data.get("frontmatter", {}).get("source", "unknown")
                   if isinstance(capture_data.get("frontmatter"), dict)
                   else "unknown"),
        "created_at": (capture_data.get("frontmatter", {}).get("created_at", "")
                       if isinstance(capture_data.get("frontmatter"), dict)
                       else capture_data.get("created_at", "")),
        "classification": capture_data.get("classification", "unknown"),
    }

    # Template catalog — V0 has no dynamic template resolution
    template_catalog = ["knowledge_v0"]

    # Working state summary — try Status API, fallback to generic
    working_state_summary = None
    try:
        status_url = "http://localhost:8787/status"
        with urllib.request.urlopen(status_url, timeout=5) as resp:
            status_data = json.loads(resp.read().decode("utf-8"))
            working_state_summary = (
                f"Pending captures: {status_data.get('pending_captures', '?')}. "
                f"Event log lines: {status_data.get('event_log_line_count', '?')}."
            )
    except Exception:
        working_state_summary = None

    return {
        "capture_metadata": capture_metadata,
        "template_catalog": template_catalog,
        "working_state_summary": working_state_summary,
    }


# --- YAML Serialization (stdlib only, no PyYAML) ---

def _yaml_value(val, indent=0, is_flow=False) -> str:
    """Serialize a Python value to a YAML string fragment."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        # Quote strings with special chars
        if any(c in val for c in ':#{}[]&*!|>%@`,\'"\n'):
            return f'"{val}"'
        if not val:
            return '""'
        return val
    if isinstance(val, list):
        if not val:
            return "[]"
        if is_flow:
            items = ', '.join(_yaml_value(v, is_flow=True) for v in val)
            return f"[{items}]"
        result = []
        for item in val:
            item_str = _yaml_value(item, indent=indent)
            result.append(f"{'  ' * indent}- {item_str}")
        return '\n'.join(result)
    if isinstance(val, dict):
        if not val:
            return "{}"
        if is_flow:
            items = ', '.join(
                f"{_yaml_value(k, is_flow=True)}: {_yaml_value(v, is_flow=True)}"
                for k, v in val.items()
            )
            return f"{{{items}}}"
        result = []
        for k, v in val.items():
            v_str = _yaml_value(v, indent=indent + 1, is_flow=True if isinstance(v, list) and len(v) <= 3 else False)
            key_str = _yaml_value(k)
            if '\n' in v_str:
                result.append(f"{'  ' * indent}{key_str}:")
                result.append(v_str)
            else:
                result.append(f"{'  ' * indent}{key_str}: {v_str}")
        return '\n'.join(result)
    return str(val)


def _yaml_dump(data: dict) -> str:
    """Serialize a dict as YAML frontmatter."""
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list) and all(isinstance(v, str) for v in value) and len(value) <= 3:
            v_str = _yaml_value(value, is_flow=True)
        elif isinstance(value, list):
            v_str = _yaml_value(value, indent=1)
        else:
            v_str = _yaml_value(value)
        if '\n' in v_str:
            lines.append(f"{key}:")
            lines.append(v_str)
        else:
            lines.append(f"{key}: {v_str}")
    lines.append("---")
    return '\n'.join(lines)


# --- Proposal Packet Builder ---

def build_proposal_packet(
    capture_text: str,
    capture_data: dict,
    classification: dict,
    curated: dict,
    import_path: str,
    mcp_context: dict = None,
) -> dict:
    """Build the full Markdown + YAML proposal packet.

    This assembles all agent outputs into a structured proposal
    following the LifeOS review packet format. The output is a dict
    with frontmatter, body, and metadata — ready to be serialized
    to a .md file and saved to the buffer vault.

    Args:
        capture_text: Raw capture text.
        capture_data: Resolved capture dict from Action API.
        classification: Output from classifier.classify_capture().
        curated: Output from knowledge_curator.curate_knowledge().
        import_path: Output from import_planner.plan_import_path().
        mcp_context: Optional MCP context dict.

    Returns:
        A dict representing the full proposal packet.
    """
    if mcp_context is None:
        mcp_context = {}

    capture_id = capture_data.get("capture_id", "unknown")
    proposal_id = generate_proposal_id(capture_id)
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    capture_metadata = mcp_context.get("capture_metadata", {})
    source = capture_metadata.get("source", "unknown")
    working_state = mcp_context.get("working_state_summary")

    # Build body sections first — the content_hash must be computed
    # from the body portion (after YAML frontmatter), matching what
    # the approved_proposal_importer will verify.
    yaml_block = _yaml_dump(curated.get("yaml_frontmatter", {}))
    body_sections = curated.get("body_sections", {})

    safety_notice = (
        "This is a buffer-only proposal. It has not been imported "
        "into the canonical LifeOS vault. All content is machine-generated "
        "by deterministic V0 modules (no AI/LLM). Human review is required "
        "before any vault import. No automated import will occur."
    )

    mcp_context_text = ""
    if working_state:
        mcp_context_text = f"Working State Summary: {working_state}"
    else:
        mcp_context_text = (
            "MCP context was not available during curation. "
            "Status API may not be running."
        )

    body = f"""## Proposal Summary
- **Proposal ID:** {proposal_id}
- **Status:** pending
- **Created:** {now_ts}

## Source Capture
- **Capture ID:** {capture_id}
- **Source:** {source}
- **Content Preview:** {capture_text[:200]}

## Classification
- **Result:** {classification.get('classification', 'unknown')}
- **Confidence:** {classification.get('confidence', 'unknown')}
- **Reasons:** {', '.join(classification.get('reasons', []))}

## MCP Context Used
{mcp_context_text}

## Proposed Vault File
- **Path:** `{import_path}`
- **Type:** knowledge note

## Proposed YAML
```yaml
{yaml_block}
```

## Proposed Note Body
### Summary
{body_sections.get('summary', 'N/A')}

### Definition / Context
{body_sections.get('definition_context', 'N/A')}

### Key Details
{body_sections.get('key_details', 'N/A')}

### Why It Matters
{body_sections.get('why_it_matters', 'N/A')}

### How It Connects
{body_sections.get('how_it_connects', 'N/A')}

### Source Trail
{body_sections.get('source_trail', 'N/A')}

### Related Concepts
{body_sections.get('related_concepts', 'N/A')}

### Review Notes
{body_sections.get('review_notes', 'N/A')}

## Uncertainty / Risks
This is a V0 deterministic proposal. The classification and curation
are rule-based with no AI verification. The proposal may misclassify
or miscategorize the capture. Review the proposed placement and note
content carefully.

## QA Checklist
- [ ] Capture content is worth preserving in the vault
- [ ] Classification (knowledge) is correct
- [ ] Proposed vault path is appropriate
- [ ] Note content is accurate and useful
- [ ] No secrets, passwords, or personal data exposed
- [ ] Source trail is complete and traceable
- [ ] Rollback plan is understood

## Human Decision
- **Decision:** [ ] Approve  [ ] Reject  [ ] Request Changes
- **Reviewed By:** ________
- **Reviewed At:** ________
- **Notes:** ________

## Revision Instructions
To revise this proposal, run:
```
python3 capture_review_orchestrator.py revise-proposal --proposal-id {proposal_id} --instruction "..."
```

## Import Plan
To import after approval:
```
python3 capture_review_orchestrator.py approve-import --proposal-id {proposal_id}
```
(This will create the file in the LifeOS vault under `{import_path}`.)

## Rollback Plan
To roll back the import:
Delete the file at `{import_path}` from the LifeOS vault.
The buffer copy of this proposal remains in `{PROPOSAL_DIR}/{proposal_id}.md`.

## Safety Notice
{safety_notice}
"""

    # Hash matches what the importer will verify:
    # The importer extracts everything after the closing --- in the saved file,
    # which includes the \n separator between frontmatter and body.
    content_hash = compute_content_hash("\n" + body)

    # Build frontmatter
    frontmatter = {
        "type": "capture_to_vault_proposal",
        "schema_version": "1",
        "proposal_id": proposal_id,
        "proposal_version": "1",
        "approval_required": "true",
        "import_status": "not_imported",
        "proposed_note_type": "knowledge",
        "status": "pending",
        "capture_id": capture_id,
        "classification": classification.get("classification", "unknown"),
        "classification_confidence": classification.get("confidence", "unknown"),
        "classification_reasons": classification.get("reasons", []),
        "content_hash": content_hash,
        "proposed_vault_path": import_path,
        "source": source,
        "created_at": now_ts,
        "importable": classification.get("classification") == "knowledge",
    }

    return {
        "proposal_id": proposal_id,
        "frontmatter": frontmatter,
        "body": body,
        "proposed_vault_path": import_path,
        "classification": classification,
        "content_hash": content_hash,
        "status": "pending",
        "capture_id": capture_id,
    }


# --- Proposal File I/O ---

def _ensure_proposal_dir():
    """Ensure the proposal directory exists."""
    Path(PROPOSAL_DIR).mkdir(parents=True, exist_ok=True)


def save_proposal(proposal_id: str, proposal: dict) -> str:
    """Save a proposal packet to the buffer vault proposals directory.

    The proposal is saved as a Markdown file with YAML frontmatter.

    Args:
        proposal_id: The unique proposal ID.
        proposal: The full proposal dict.

    Returns:
        The file path where the proposal was saved.

    Raises:
        OSError: If the file cannot be written.
    """
    _ensure_proposal_dir()

    frontmatter = proposal.get("frontmatter", {})
    body = proposal.get("body", "")

    yaml_str = _yaml_dump(frontmatter)
    file_content = f"{yaml_str}\n\n{body}"

    file_path = os.path.join(PROPOSAL_DIR, f"{proposal_id}.md")

    # Check for forbidden output
    if is_forbidden_output(file_path):
        raise ValueError(f"Cannot write to forbidden path: {file_path}")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(file_content)

    return file_path


def load_proposal(proposal_id: str) -> dict:
    """Load a proposal packet from the buffer vault.

    Args:
        proposal_id: The unique proposal ID.

    Returns:
        A dict with the proposal's frontmatter and body.

    Raises:
        FileNotFoundError: If the proposal file does not exist.
    """
    file_path = os.path.join(PROPOSAL_DIR, f"{proposal_id}.md")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Proposal not found: {proposal_id} (at {file_path})")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse YAML frontmatter and body
    lines = content.splitlines()
    frontmatter = {}
    body_lines = []
    in_frontmatter = False
    end_frontmatter = False

    for line in lines:
        if not in_frontmatter and line.strip() == "---":
            in_frontmatter = True
            continue
        if in_frontmatter and not end_frontmatter:
            if line.strip() == "---":
                end_frontmatter = True
                continue
            if ":" in line:
                key, _, val = line.partition(":")
                frontmatter[key.strip()] = val.strip()
        elif end_frontmatter:
            body_lines.append(line)

    body = '\n'.join(body_lines).strip()

    return {
        "proposal_id": proposal_id,
        "frontmatter": frontmatter,
        "body": body,
        "file_path": file_path,
    }


def update_proposal_status(proposal_id: str, new_status: str,
                           extra_fields: dict = None) -> dict:
    """Update a proposal's frontmatter status and optional extra fields.

    Args:
        proposal_id: The unique proposal ID.
        new_status: The new status (e.g., "approved", "rejected", "revised").
        extra_fields: Optional dict of additional frontmatter fields to set.

    Returns:
        The updated proposal dict.

    Raises:
        FileNotFoundError: If the proposal file does not exist.
    """
    proposal = load_proposal(proposal_id)
    frontmatter = proposal["frontmatter"]
    frontmatter["status"] = new_status
    frontmatter["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if extra_fields:
        for k, v in extra_fields.items():
            frontmatter[k] = v

    # Rewrite the file
    yaml_str = _yaml_dump(frontmatter)
    file_content = f"{yaml_str}\n\n{proposal['body']}"

    file_path = os.path.join(PROPOSAL_DIR, f"{proposal_id}.md")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(file_content)

    return {**proposal, "frontmatter": frontmatter, "status": new_status}


# --- Knowledge Proposal Flow ---

def propose_knowledge(capture_ref: str, dry_run: bool = False,
                      force_new: bool = False) -> dict:
    """Execute the full knowledge proposal flow.

    1. Resolve capture via Action API
    2. Classify with deterministic classifier
    3. If not knowledge, return error (V0 constraint)
    4. Gather MCP context (with graceful fallback)
    5. Curate knowledge note (deterministic, no AI)
    6. Plan import path
    7. Build proposal packet
    8. Save to buffer vault (or return only if dry_run)
    9. Return JSON result

    This orchestrator coordinates only deterministic V0 agents.
    No AI/LLM calls are made at any stage.

    Args:
        capture_ref: Capture reference ("latest", index, or capture_id).
        dry_run: If True, do everything except write to disk.
        force_new: If True, create a new proposal even if one exists.

    Returns:
        A dict with the proposal result, including:
            success: bool
            proposal_id: str (if successful)
            error: str (if failed)
            proposal: dict (the full proposal if dry_run)
    """
    # Step 1: Resolve capture
    try:
        capture_data = resolve_capture(capture_ref)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    capture_text = capture_data.get("content", "")
    if not capture_text:
        return {"success": False, "error": "Capture has no text content."}

    # Step 2: Classify
    from agents.classifier import classify_capture, is_importable as _is_importable
    source = (
        capture_data.get("frontmatter", {}).get("source", "unknown")
        if isinstance(capture_data.get("frontmatter"), dict)
        else "unknown"
    )
    classification = classify_capture(capture_text, source=source)

    # Step 3: V0 only supports knowledge import
    if not _is_importable(classification["classification"]):
        return {
            "success": False,
            "error": (
                f"V0 only supports knowledge imports. "
                f"Classification was '{classification['classification']}' "
                f"with confidence '{classification['confidence']}'. "
                f"Reasons: {classification['reasons']}"
            ),
            "classification": classification,
        }

    # Step 4: Gather MCP context (graceful fallback)
    mcp_context = _gather_mcp_context(capture_data)

    # Step 5: Curate knowledge note
    from agents.knowledge_curator import curate_knowledge
    curated = curate_knowledge(
        capture_text=capture_text,
        capture_metadata=mcp_context["capture_metadata"],
        template_catalog=mcp_context["template_catalog"],
        working_state_summary=mcp_context["working_state_summary"],
    )

    # Step 6: Plan import path
    from agents.import_planner import plan_import_path
    import_path = plan_import_path(curated["title"], capture_text)

    # Step 7: Build proposal packet
    proposal = build_proposal_packet(
        capture_text=capture_text,
        capture_data=capture_data,
        classification=classification,
        curated=curated,
        import_path=import_path,
        mcp_context=mcp_context,
    )

    proposal_id = proposal["proposal_id"]

    # Check for existing proposal with same capture_id
    if not force_new:
        try:
            existing = load_proposal(proposal_id)
            return {
                "success": False,
                "error": (
                    f"A proposal already exists for this capture. "
                    f"Use --force-new to create a new one."
                ),
                "existing_proposal_id": proposal_id,
            }
        except FileNotFoundError:
            pass

    # Step 8: Save to buffer vault
    if dry_run:
        return {
            "success": True,
            "proposal_id": proposal_id,
            "dry_run": True,
            "proposal": proposal,
        }

    try:
        file_path = save_proposal(proposal_id, proposal)
    except (OSError, ValueError) as e:
        return {"success": False, "error": f"Failed to save proposal: {e}"}

    # Step 9: Return JSON result
    return {
        "success": True,
        "proposal_id": proposal_id,
        "file_path": file_path,
        "capture_id": capture_data.get("capture_id"),
        "classification": classification["classification"],
        "confidence": classification["confidence"],
        "proposed_vault_path": import_path,
        "proposed_title": curated.get("title", ""),
    }


# --- CLI ---

def _cmd_propose_knowledge(args):
    """Propose a knowledge import from a capture."""
    result = propose_knowledge(
        capture_ref=args.capture,
        dry_run=args.dry_run,
        force_new=args.force_new,
    )
    _output_result(result, args.output)


def _cmd_view_proposal(args):
    """View a proposal by ID."""
    try:
        proposal = load_proposal(args.proposal_id)
    except FileNotFoundError as e:
        result = {"success": False, "error": str(e)}
        _output_result(result, args.output)
        return

    if args.output == "json":
        _output_result({"success": True, "proposal": proposal}, "json")
    else:
        # Text output
        frontmatter = proposal.get("frontmatter", {})
        body = proposal.get("body", "")
        print(f"Proposal ID: {proposal['proposal_id']}")
        print(f"Status: {frontmatter.get('status', 'unknown')}")
        print(f"Capture ID: {frontmatter.get('capture_id', 'unknown')}")
        print(f"Classification: {frontmatter.get('classification', 'unknown')}")
        print(f"Proposed Path: {frontmatter.get('proposed_vault_path', 'unknown')}")
        print(f"Created: {frontmatter.get('created_at', 'unknown')}")
        print()
        print(body)


def _cmd_reject_proposal(args):
    """Reject a proposal."""
    try:
        updated = update_proposal_status(
            args.proposal_id,
            "rejected",
            extra_fields={
                "rejection_reason": args.reason,
                "rejected_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
    except FileNotFoundError as e:
        result = {"success": False, "error": str(e)}
        _output_result(result, args.output)
        return

    result = {
        "success": True,
        "proposal_id": args.proposal_id,
        "status": "rejected",
        "reason": args.reason,
    }
    _output_result(result, args.output)


def _cmd_revise_proposal(args):
    """Mark a proposal for revision."""
    try:
        updated = update_proposal_status(
            args.proposal_id,
            "revised",
            extra_fields={
                "revision_instruction": args.instruction,
                "revised_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
    except FileNotFoundError as e:
        result = {"success": False, "error": str(e)}
        _output_result(result, args.output)
        return

    result = {
        "success": True,
        "proposal_id": args.proposal_id,
        "status": "revised",
        "instruction": args.instruction,
    }
    _output_result(result, args.output)


def _cmd_approve_import(args):
    """Approve a proposal for import."""
    try:
        proposal = load_proposal(args.proposal_id)
    except FileNotFoundError as e:
        result = {"success": False, "error": str(e)}
        _output_result(result, args.output)
        return

    # load_proposal returns flat dict with no top-level status;
    # lift it from frontmatter so verify_proposal can find it
    proposal["status"] = proposal["frontmatter"].get("status", "")

    # Validate the proposal before approving
    from agents.qa_verifier import verify_proposal
    qa_result = verify_proposal(proposal)

    if qa_result["verdict"] == "fail":
        result = {
            "success": False,
            "error": f"QA verification failed: {qa_result['issues']}",
            "qa_verdict": qa_result["verdict"],
            "issues": qa_result["issues"],
        }
        _output_result(result, args.output)
        return

    # Update status to approved
    try:
        updated = update_proposal_status(
            args.proposal_id,
            "approved_for_import",
            extra_fields={
                "approved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "qa_verdict": qa_result["verdict"],
                "qa_warnings": qa_result.get("warnings", []),
            },
        )
    except FileNotFoundError as e:
        result = {"success": False, "error": str(e)}
        _output_result(result, args.output)
        return

    # Build the import manifest
    frontmatter = proposal.get("frontmatter", {})
    proposed_path = frontmatter.get("proposed_vault_path", "")
    target_path = os.path.join(VAULT_ROOT, proposed_path) if proposed_path else ""

    result = {
        "success": True,
        "proposal_id": args.proposal_id,
        "status": "approved",
        "qa_verdict": qa_result["verdict"],
        "qa_warnings": qa_result.get("warnings", []),
        "import_target": target_path,
        "proposed_vault_path": target_path,
        "action_required": (
            f"To complete the import, create the file at: {target_path}"
            if target_path
            else "Import target path not available."
        ),
        "note": (
            "In V0, the actual vault file creation must be performed manually "
            "or by a future import_exporter processor. The proposal packet "
            "contains the complete note content ready for import."
        ),
    }
    _output_result(result, args.output)


def _output_result(result: dict, fmt: str = "json"):
    """Output a result dict in the requested format."""
    if fmt == "json":
        print(json.dumps(result, indent=2, default=str))
    else:
        if result.get("success"):
            print("OK:", result.get("message", json.dumps(result, default=str)))
        else:
            print("ERROR:", result.get("error", "Unknown error"))


def main():
    """Main CLI entry point for the Capture Review Orchestrator."""
    parser = argparse.ArgumentParser(
        description="LifeOS Capture Review Orchestrator — V0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 capture_review_orchestrator.py propose-knowledge --capture latest
  python3 capture_review_orchestrator.py propose-knowledge --capture 1 --dry-run
  python3 capture_review_orchestrator.py view-proposal --proposal-id prop_xxx
  python3 capture_review_orchestrator.py reject-proposal --proposal-id prop_xxx --reason "Not useful"
  python3 capture_review_orchestrator.py revise-proposal --proposal-id prop_xxx --instruction "Change title"
  python3 capture_review_orchestrator.py approve-import --proposal-id prop_xxx
        """,
    )

    parser.add_argument(
        "--output", choices=["json", "text"], default="json",
        help="Output format (default: json)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # propose-knowledge
    propose_parser = subparsers.add_parser(
        "propose-knowledge",
        help="Propose a knowledge note import from a capture",
    )
    propose_parser.add_argument(
        "--output", choices=["json", "text"], default="json",
        help="Output format (default: json)",
    )
    propose_parser.add_argument(
        "--capture", required=True,
        help="Capture reference: 'latest', numeric index (1-based), or capture_id",
    )
    propose_parser.add_argument(
        "--dry-run", action="store_true",
        help="Run the full pipeline but do not save the proposal to disk",
    )
    propose_parser.add_argument(
        "--force-new", action="store_true",
        help="Create a new proposal even if one already exists",
    )

    # view-proposal
    view_parser = subparsers.add_parser(
        "view-proposal",
        help="View a proposal by ID",
    )
    view_parser.add_argument(
        "--output", choices=["json", "text"], default="json",
        help="Output format (default: json)",
    )
    view_parser.add_argument(
        "--proposal-id", required=True,
        help="The proposal ID to view",
    )

    # reject-proposal
    reject_parser = subparsers.add_parser(
        "reject-proposal",
        help="Reject a proposal",
    )
    reject_parser.add_argument(
        "--output", choices=["json", "text"], default="json",
        help="Output format (default: json)",
    )
    reject_parser.add_argument(
        "--proposal-id", required=True,
        help="The proposal ID to reject",
    )
    reject_parser.add_argument(
        "--reason", required=True,
        help="Reason for rejection",
    )

    # revise-proposal
    revise_parser = subparsers.add_parser(
        "revise-proposal",
        help="Mark a proposal for revision",
    )
    revise_parser.add_argument(
        "--output", choices=["json", "text"], default="json",
        help="Output format (default: json)",
    )
    revise_parser.add_argument(
        "--proposal-id", required=True,
        help="The proposal ID to revise",
    )
    revise_parser.add_argument(
        "--instruction", required=True,
        help="Revision instruction",
    )

    # approve-import
    approve_parser = subparsers.add_parser(
        "approve-import",
        help="Approve a proposal for import into the canonical vault",
    )
    approve_parser.add_argument(
        "--output", choices=["json", "text"], default="json",
        help="Output format (default: json)",
    )
    approve_parser.add_argument(
        "--proposal-id", required=True,
        help="The proposal ID to approve",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    command_map = {
        "propose-knowledge": _cmd_propose_knowledge,
        "view-proposal": _cmd_view_proposal,
        "reject-proposal": _cmd_reject_proposal,
        "revise-proposal": _cmd_revise_proposal,
        "approve-import": _cmd_approve_import,
    }

    handler = command_map.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
