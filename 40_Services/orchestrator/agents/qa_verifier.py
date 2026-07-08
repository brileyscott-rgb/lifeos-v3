"""
Deterministic QA Verifier — V0 (no AI/LLM).

This module validates proposal packets before they are presented for
human review. It runs a set of critical and warning checks against
the proposal structure, YAML frontmatter, proposed paths, and content
completeness. All checks are deterministic rule evaluations — no AI/LLM.

Critical check failures result in a "fail" verdict. Warning-only
issues result in "pass_with_warnings". All clear results in "pass".
"""

from typing import Dict, List

try:
    from ..security import is_forbidden_output
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from security import is_forbidden_output

# Checks that must ALL pass for the proposal to be accepted.
# Any failure here produces a "fail" verdict.
CRITICAL_CHECKS = [
    "status_must_be_pending_or_approved",
    "source_trail_present",
    "content_hash_present",
    "proposed_import_path_safe",
    "proposed_import_path_under_knowledge_root",
    "no_overwrite_without_update_mode",
    "required_sections_present",
    "proposal_version_present",
]

# Checks that produce warnings but do not block approval.
WARNING_CHECKS = [
    "uncertainty_section_present",
    "approval_checklist_present",
    "classification_confidence_low",
]

REQUIRED_SECTIONS = [
    "Proposal Summary",
    "Source Capture",
    "Classification",
    "MCP Context Used",
    "Proposed Vault File",
    "Proposed YAML",
    "Proposed Note Body",
    "Uncertainty / Risks",
    "QA Checklist",
    "Human Decision",
    "Revision Instructions",
    "Import Plan",
    "Rollback Plan",
    "Safety Notice",
]


def _check_status(proposal: dict) -> dict:
    """Verify the proposal status is 'pending' or 'approved'."""
    status = proposal.get("status", "")
    if status not in ("pending", "approved"):
        return {
            "passed": False,
            "detail": f"Status must be 'pending' or 'approved', got '{status}'",
        }
    return {"passed": True, "detail": f"Status is valid: {status}"}


def _check_source_trail(proposal: dict) -> dict:
    """Verify the proposal includes source trail information."""
    body = proposal.get("body", "")
    if isinstance(body, str) and "source" in body.lower():
        return {"passed": True, "detail": "Source trail appears present in body."}
    frontmatter = proposal.get("frontmatter", {})
    if frontmatter.get("source_refs") or frontmatter.get("source_capture"):
        return {"passed": True, "detail": "Source references found in frontmatter."}
    return {"passed": False, "detail": "No source trail found in frontmatter or body."}


def _check_content_hash(proposal: dict) -> dict:
    """Verify the proposal contains a content_hash field."""
    frontmatter = proposal.get("frontmatter", {})
    if frontmatter.get("content_hash"):
        return {"passed": True, "detail": f"Content hash present: {frontmatter['content_hash'][:16]}..."}
    return {"passed": False, "detail": "content_hash is missing from proposal frontmatter."}


def _resolve_path(proposal: dict) -> str:
    """Resolve proposed_vault_path from either top-level or frontmatter."""
    path = proposal.get("proposed_vault_path", "")
    if not path:
        fm = proposal.get("frontmatter", {})
        if isinstance(fm, dict):
            path = fm.get("proposed_vault_path", "")
    return path


def _check_path_safe(proposal: dict) -> dict:
    """Verify the proposed import path is syntactically safe (no traversal, not absolute)."""
    path = _resolve_path(proposal)
    if not path:
        return {"passed": False, "detail": "proposed_vault_path is empty."}
    if ".." in path.split("/"):
        return {"passed": False, "detail": "Path traversal detected in proposed_vault_path."}
    if path.startswith("/"):
        return {"passed": False, "detail": "proposed_vault_path is absolute, must be vault-relative."}
    # Hidden files are forbidden
    for component in path.split("/"):
        if component.startswith("."):
            return {"passed": False, "detail": f"Hidden path component detected: '{component}'"}
    return {"passed": True, "detail": f"Proposed path is safe: {path}"}


def _check_knowledge_root(proposal: dict) -> dict:
    """Verify the proposed path is under the Knowledge root directory."""
    path = _resolve_path(proposal)
    if not path:
        return {"passed": False, "detail": "proposed_vault_path is empty."}
    if not path.startswith("04_KNOWLEDGE/"):
        return {
            "passed": False,
            "detail": f"Path must start with '04_KNOWLEDGE/', got '{path}'",
        }
    return {"passed": True, "detail": "Path is under Knowledge root."}


def _check_no_overwrite(proposal: dict) -> dict:
    """Verify the proposal does not claim to overwrite without update mode."""
    mode = proposal.get("mode", "")
    if mode == "update":
        return {"passed": True, "detail": "Update mode explicitly set."}
    # In V0 all imports are new-file creates. Overwrite is not supported.
    if proposal.get("intent", "") == "overwrite":
        return {"passed": False, "detail": "Overwrite intent requires explicit 'update' mode."}
    return {"passed": True, "detail": "No overwrite detected; safe for new-file creation."}


def _check_required_sections(proposal: dict) -> dict:
    """Verify all required proposal body sections are present."""
    body = proposal.get("body", "")
    if not isinstance(body, str):
        return {"passed": False, "detail": "Body is missing or not a string."}
    missing = []
    for section in REQUIRED_SECTIONS:
        if section.lower() not in body.lower():
            missing.append(section)
    if missing:
        return {
            "passed": False,
            "detail": f"Missing required sections: {', '.join(missing)}",
        }
    return {"passed": True, "detail": "All required sections present."}


def _check_proposal_version(proposal: dict) -> dict:
    """Verify the proposal has a version or schema_version field."""
    fm = proposal.get("frontmatter", {})
    version = fm.get("version") or fm.get("schema_version")
    if version:
        return {"passed": True, "detail": f"Proposal version: {version}"}
    return {"passed": False, "detail": "proposal_version is missing from frontmatter."}


def _check_uncertainty_section(proposal: dict) -> dict:
    """Warn if no 'Uncertainty / Risks' section appears in the body."""
    body = proposal.get("body", "")
    if isinstance(body, str) and "uncertainty" in body.lower():
        return {"passed": True, "detail": "Uncertainty section appears present."}
    return {
        "passed": False,
        "detail": "Uncertainty / Risks section not detected in body.",
    }


def _check_approval_checklist(proposal: dict) -> dict:
    """Warn if no approval checklist is present."""
    body = proposal.get("body", "")
    if isinstance(body, str) and "- [ ]" in body:
        return {"passed": True, "detail": "Approval checklist items detected."}
    return {
        "passed": False,
        "detail": "No approval checklist (checkbox items) found in body.",
    }


def _check_classification_confidence(proposal: dict) -> dict:
    """Warn if the classification confidence is low."""
    classification = proposal.get("classification", {})
    if isinstance(classification, dict):
        confidence = classification.get("confidence", "unknown")
        if confidence == "low":
            return {
                "passed": False,
                "detail": "Classification confidence is 'low' — review recommended.",
            }
        return {"passed": True, "detail": f"Classification confidence: {confidence}"}
    return {"passed": True, "detail": "No classification confidence info available."}


# Mapping of check names to handler functions
_CHECK_HANDLERS = {
    "status_must_be_pending_or_approved": _check_status,
    "source_trail_present": _check_source_trail,
    "content_hash_present": _check_content_hash,
    "proposed_import_path_safe": _check_path_safe,
    "proposed_import_path_under_knowledge_root": _check_knowledge_root,
    "no_overwrite_without_update_mode": _check_no_overwrite,
    "required_sections_present": _check_required_sections,
    "proposal_version_present": _check_proposal_version,
    "uncertainty_section_present": _check_uncertainty_section,
    "approval_checklist_present": _check_approval_checklist,
    "classification_confidence_low": _check_classification_confidence,
}


def verify_proposal(proposal: dict) -> dict:
    """Validate a proposal packet against critical and warning checks.

    This is a deterministic V0 QA verifier. No AI/LLM is used.
    All checks are rule-based evaluations of proposal structure,
    metadata, and path safety.

    Args:
        proposal: The full proposal dict with 'frontmatter', 'body',
                  'proposed_vault_path', 'status', 'classification', etc.

    Returns:
        A dict with:
            verdict: "pass" | "pass_with_warnings" | "fail"
            issues: List[str] — descriptions of critical failures
            warnings: List[str] — descriptions of non-critical issues
            checks: dict — detailed per-check results

    Example:
        >>> result = verify_proposal({
        ...     "status": "pending",
        ...     "frontmatter": {"content_hash": "abc123", "version": "1.0"},
        ...     "body": "Proposal Summary\\nSource Capture\\nClassification\\n...",
        ...     "proposed_vault_path": "04_KNOWLEDGE/AI/Note.md",
        ... })
        >>> result["verdict"] in ("pass", "pass_with_warnings", "fail")
        True
    """
    if not isinstance(proposal, dict):
        return {
            "verdict": "fail",
            "issues": ["Proposal is not a valid dict."],
            "warnings": [],
            "checks": {},
        }

    issues = []
    warnings = []
    checks = {}

    for check_name in CRITICAL_CHECKS:
        handler = _CHECK_HANDLERS.get(check_name)
        if handler is None:
            continue
        try:
            result = handler(proposal)
        except Exception as e:
            result = {"passed": False, "detail": f"Check error: {e}"}
        checks[check_name] = result
        if not result.get("passed"):
            issues.append(f"[{check_name}] {result.get('detail', 'failed')}")

    for check_name in WARNING_CHECKS:
        handler = _CHECK_HANDLERS.get(check_name)
        if handler is None:
            continue
        try:
            result = handler(proposal)
        except Exception as e:
            result = {"passed": False, "detail": f"Check error: {e}"}
        checks[check_name] = result
        if not result.get("passed"):
            warnings.append(f"[{check_name}] {result.get('detail', 'warning')}")

    if issues:
        verdict = "fail"
    elif warnings:
        verdict = "pass_with_warnings"
    else:
        verdict = "pass"

    return {
        "verdict": verdict,
        "issues": issues,
        "warnings": warnings,
        "checks": checks,
    }
