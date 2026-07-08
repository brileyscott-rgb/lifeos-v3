# Capture-to-Vault Orchestrator — SAFEST V0 Architecture

Status: **Proposed (Design)**
Created: 2026-07-08
Architect: Software Architect Agent
Supersedes: None (new subsystem)
Depends on: Agentic Capture Pipeline V1 (architecture), Headless Capture Buffer Vault Policy, Capture Review Packet Format

## 1. Architecture Overview

### 1.1 Core Invariant

> **Agents propose. MCP informs/refines. Telegram/n8n trigger and route. Only the controlled importer writes to the vault after explicit approval.**

### 1.2 System Boundary Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          TELEGRAM (User)                                 │
│  /kt <n> │ [Proposal] button │ [Approve] button │ [Reject] button       │
│  [Revise] button │ callback_query dispatch                              │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │ calls fixed orchestrator CLI commands ONLY
                            │ (never calls MCP directly, never calls agents directly)
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CAPTURE REVIEW ORCHESTRATOR (CLI)                     │
│                                                                          │
│  orchestrator.py                                                        │
│  ├─ propose-knowledge <target>                                          │
│  ├─ view-proposal <proposal_id>                                         │
│  ├─ reject-proposal <proposal_id> [reason]                              │
│  ├─ revise-proposal <proposal_id> [feedback]                            │
│  └─ approve-import <proposal_id>                                        │
│                                                                          │
│  Internal pipeline:                                                      │
│  1. Resolve capture (latest/index/capture_id)                           │
│  2. Call MCP tools (read-only context) through MCP Client               │
│  3. Call specialist agents (deterministic Python)                        │
│  4. Generate proposal packet in buffer vault ONLY                        │
│  5. On approval: invoke controlled importer                              │
└───────┬───────────────────────────────┬─────────────────────────────────┘
        │                               │
        │ uses                          │ delegates to
        ▼                               ▼
┌───────────────────┐    ┌─────────────────────────────────────────────────┐
│  MCP CLIENT       │    │  SPECIALIST AGENT MODULES (deterministic Python) │
│  (mcp_client.py)  │    │                                                  │
│                   │    │  agents/classifier.py        — type + route      │
│  spawns subprocess│    │  agents/knowledge_curator.py — draft note        │
│  typed helpers    │    │  agents/import_planner.py    — proposal packet   │
│  no arbitrary cmd │    │  agents/qa_verifier.py       — validation report │
└────────┬──────────┘    └─────────────────────────────────────────────────┘
         │ spawns/talks to
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  CUSTOM LifeOS MCP SERVER (lifeos_mcp_server.py)                 │
│  stdio JSON-RPC 2.0, Python stdlib only                          │
│                                                                  │
│  Tools (ALL READ-ONLY):                                          │
│  ├─ lifeos.status                     — system health           │
│  ├─ lifeos.capture_summary            — capture overview        │
│  ├─ lifeos.capture_metadata           — detailed metadata       │
│  ├─ lifeos.template_catalog           — available templates     │
│  └─ lifeos.current_working_state_summary — project context      │
│                                                                  │
│  NEVER: write proposals, mutate captures, write event logs,      │
│  create vault files, run shell commands, manage Docker, git.     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  CONTROLLED IMPORTER (controlled_importer.py)                    │
│                                                                  │
│  Called ONLY by orchestrator after explicit approval.            │
│  Validates: content hash, path traversal protection.             │
│  Writes to canonical vault: /home/lifeos/10_Vaults/LifeOS/       │
│  Logs import event to event log.                                 │
│  Generates rollback manifest.                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 What Each Module Knows

| Module | Knows About | Does NOT Know About |
|--------|------------|-------------------|
| MCP Server | Capture buffer files, event log, templates, system state (all read-only paths) | Orchestrator, agents, importer, Telegram |
| MCP Client | MCP Server process lifecycle, JSON-RPC protocol | Orchestrator logic, agents, captures |
| Orchestrator | MCP Client (interface), specialist agents (interface), controlled importer (interface), proposal packet model | MCP server internals, Telegram bot internals |
| Specialist Agents | Their input data, their output format | MCP, orchestrator, Telegram, importer |
| Controlled Importer | Import manifest, canonical vault paths | MCP, agents, proposal lifecycle, Telegram |
| Telegram Bot | Orchestrator CLI commands (fixed subset), existing button UX | MCP server, MCP client, agent internals, importer |

## 2. Module Boundaries and Interface Contracts

### 2.1 Custom LifeOS MCP Server

**Module path**: `40_Services/capture_orchestrator/lifeos_mcp_server.py`
**Transport**: stdio, JSON-RPC 2.0
**Dependencies**: Python stdlib only (json, sys, os, pathlib, datetime, hashlib)
**Process model**: Stateless per-invocation. Reads filesystem on each request. No in-memory cache beyond single request lifetime.

#### Tool Definitions

```
Tool: lifeos.status
Description: Return current LifeOS system status snapshot.
              Includes capture queue counts, event log status, git dirty state,
              disk usage, Docker container status, service health.
Input schema:
  {}  (no parameters)
Output schema:
  {
    "status": "ok" | "degraded" | "error",
    "pending_captures": int,
    "approved_captures": int,
    "rejected_captures": int,
    "event_log_line_count": int,
    "git_dirty": bool,
    "disk_percent": float,
    "services": { "action_api": "healthy"|"unreachable", "status_api": "healthy"|"unreachable" },
    "timestamp": "ISO8601"
  }
Read paths:
  - /home/lifeos/30_Capture/pending_review/  (count only)
  - /home/lifeos/30_Capture/approved/         (count only)
  - /home/lifeos/30_Capture/rejected/         (count only)
  - /home/lifeos/50_Event_Log/events.jsonl    (line count, last event metadata)
  - git status via subprocess (read-only: git status --porcelain)
  - shutil.disk_usage("/home/lifeos")
  - HTTP GET localhost:8787/health and localhost:8788/health
```

```
Tool: lifeos.capture_summary
Description: Return a summary of a specific capture by ID, index, or "latest".
              Includes capture ID, source type, content preview (first 500 chars),
              metadata, and current status.
Input schema:
  {
    "target": string  // capture_id (cap_*), integer index (1-based), or "latest"
  }
Output schema:
  {
    "capture_id": string,
    "index": int | null,
    "source_type": string,
    "content_preview": string,   // max 500 chars, secrets redacted
    "created_at": "ISO8601",
    "status": "pending_review" | "approved" | "rejected",
    "char_count": int,
    "has_urls": bool,
    "urls_found": [string]
  }
Read paths:
  - /home/lifeos/30_Capture/pending_review/  (directory listing, file read)
  - /home/lifeos/30_Capture/approved/
  - /home/lifeos/30_Capture/rejected/
Note: Only reads capture files. Does not parse frontmatter beyond basic extraction.
```

```
Tool: lifeos.capture_metadata
Description: Return detailed metadata for a capture including full frontmatter
              parsing, content analysis, and related buffer vault artifacts.
Input schema:
  {
    "target": string  // capture_id (cap_*), integer index, or "latest"
  }
Output schema:
  {
    "capture_id": string,
    "index": int | null,
    "source_type": string,
    "frontmatter": { ... },       // parsed YAML frontmatter if present
    "content_hash": string,       // sha256 of content
    "has_buffer_artifacts": bool,
    "buffer_artifacts": [string], // paths to existing artifacts in Capture_Buffer
    "existing_proposals": [string], // related proposal IDs if any
    "created_at": "ISO8601",
    "updated_at": "ISO8601" | null
  }
Read paths:
  - /home/lifeos/30_Capture/ (all subdirs)
  - /home/lifeos/LifeOS_Capture_Buffer/02_Agent_Workspace/ (existence check only)
  - /home/lifeos/LifeOS_Capture_Buffer/03_Review_Packets/proposals/ (list only)
```

```
Tool: lifeos.template_catalog
Description: Return the catalog of available LifeOS note templates and their
              required/optional sections, suitable for agent route selection.
Input schema:
  {
    "note_type": string | null  // optional filter: "knowledge", "project", "idea", "reference", "media"
  }
Output schema:
  {
    "templates": [
      {
        "type": string,           // "knowledge", "project", "idea", "reference", "media", "daily", "decision"
        "category": string,       // "knowledge" | "project" | "capture" | "daily" | "decision"
        "required_sections": [string],
        "optional_sections": [string],
        "frontmatter_fields": [string],
        "destination_pattern": string,  // e.g. "04_KNOWLEDGE/{domain}/{title}.md"
        "template_path": string         // path to template file in vault
      }
    ]
  }
Read paths:
  - /home/lifeos/10_Vaults/LifeOS/08_TEMPLATES/ (read-only directory listing + file reads)
  - /home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Schemas/ (read schema files)
Note: This is the ONLY MCP tool that reads from the canonical vault. It reads templates
      and schemas only — never capture files, project files, or user content.
```

```
Tool: lifeos.current_working_state_summary
Description: Return a summary of the current working state including active projects,
              recent decisions, and system configuration relevant for context-aware
              agent routing.
Input schema:
  {}  (no parameters)
Output schema:
  {
    "active_milestone": string,
    "recent_decisions": [string],       // last 5 decision titles
    "active_projects": [string],        // project folders detected
    "vault_structure_version": string,
    "agent_policies_active": [string],  // e.g. ["A3_Agent_Policy", "Migration_Deletion_Policy"]
    "timestamp": "ISO8601"
  }
Read paths:
  - /home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Current_Working_State.md (read-only)
  - /home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Decisions/ (directory listing only)
  - /home/lifeos/10_Vaults/LifeOS/02_PROJECTS/ (directory listing only)
Note: Lists project names and decision titles only. Does not read file contents.
```

#### MCP Server Safety Enforcements (internal)

```python
# Hardcoded read-only path allowlist
READ_ONLY_PATHS = {
    "/home/lifeos/30_Capture",
    "/home/lifeos/LifeOS_Capture_Buffer",
    "/home/lifeos/50_Event_Log",
    "/home/lifeos/10_Vaults/LifeOS/08_TEMPLATES",
    "/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Schemas",
    "/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Current_Working_State.md",
    "/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Decisions",
    "/home/lifeos/10_Vaults/LifeOS/02_PROJECTS",
}

# All file operations go through a single gate function that:
# 1. Resolves the real path (symlink-safe)
# 2. Checks it starts with an allowlisted prefix
# 3. Enforces mode='r' only — any write attempt raises PermissionError
# 4. Blocks execution of any subprocess except git status --porcelain
# 5. Never imports subprocess beyond the explicit git allowlist
```

#### Error Protocol

All MCP tool errors return structured JSON-RPC error responses:

```json
{
  "jsonrpc": "2.0",
  "id": "<request_id>",
  "error": {
    "code": -32000,
    "message": "Capture not found: cap_20260708_123456_abc123",
    "data": { "target": "cap_20260708_123456_abc123", "reason": "no_such_capture" }
  }
}
```

Error codes:
- `-32000`: Resource not found (capture, template, etc.)
- `-32001`: Invalid parameter (bad target format, etc.)
- `-32002`: Path access denied (attempted read outside allowlist)
- `-32003`: Internal error (unexpected filesystem error)
- `-32602`: Invalid params (JSON-RPC standard)

### 2.2 MCP Client Helper

**Module path**: `40_Services/capture_orchestrator/mcp_client.py`
**Dependencies**: Python stdlib only (subprocess, json, sys, os, threading, queue)
**Process model**: Spawns MCP server as subprocess. Manages stdin/stdout JSON-RPC communication.

#### Public Interface

```python
from dataclasses import dataclass, field
from typing import Optional
import subprocess
import json
import threading
import queue
import os
import time

# ── Response dataclasses (typed, not raw JSON) ──

@dataclass
class StatusResult:
    status: str                    # "ok" | "degraded" | "error"
    pending_captures: int
    approved_captures: int
    rejected_captures: int
    event_log_line_count: int
    git_dirty: bool
    disk_percent: float
    services: dict                 # { "action_api": "healthy"|"unreachable", ... }
    timestamp: str

@dataclass
class CaptureSummaryResult:
    capture_id: str
    index: Optional[int]
    source_type: str
    content_preview: str
    created_at: str
    status: str
    char_count: int
    has_urls: bool
    urls_found: list

@dataclass
class CaptureMetadataResult:
    capture_id: str
    index: Optional[int]
    source_type: str
    frontmatter: dict
    content_hash: str
    has_buffer_artifacts: bool
    buffer_artifacts: list
    existing_proposals: list
    created_at: str
    updated_at: Optional[str]

@dataclass
class TemplateInfo:
    type: str
    category: str
    required_sections: list
    optional_sections: list
    frontmatter_fields: list
    destination_pattern: str
    template_path: str

@dataclass
class TemplateCatalogResult:
    templates: list  # list[TemplateInfo]

@dataclass
class WorkingStateResult:
    active_milestone: str
    recent_decisions: list
    active_projects: list
    vault_structure_version: str
    agent_policies_active: list
    timestamp: str


# ── Exceptions ──

class MCPClientError(Exception):
    """Base exception for MCP client errors."""

class MCPServerUnavailableError(MCPClientError):
    """MCP server process could not be started or died."""

class MCPTimeoutError(MCPClientError):
    """MCP tool call timed out."""

class MCPToolError(MCPClientError):
    """MCP tool returned an error response."""
    def __init__(self, code: int, message: str, data: Optional[dict] = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


# ── MCP Client Class ──

class LifeOSMCPClient:
    """Typed client for the LifeOS MCP server.
    
    Spawns the MCP server as a subprocess. Provides one typed method per
    MCP tool. No arbitrary tool invocation — methods are fixed and typed.
    """

    def __init__(self, server_script: str = None, timeout: float = 10.0):
        """
        Args:
            server_script: Path to lifeos_mcp_server.py. 
                           Defaults to sibling file relative to this module.
            timeout: Seconds to wait for each tool call response.
        """
        ...

    def start(self) -> None:
        """Spawn the MCP server subprocess and perform initialize handshake.
        
        Raises:
            MCPServerUnavailableError: if server cannot start or handshake fails.
        """
        ...

    def stop(self) -> None:
        """Terminate the MCP server subprocess cleanly."""
        ...

    def is_alive(self) -> bool:
        """Return True if the server subprocess is running."""
        ...

    # ── Typed tool methods (one per MCP tool) ──

    def get_status(self) -> StatusResult:
        """Call lifeos.status tool. Returns typed StatusResult.
        
        Raises:
            MCPTimeoutError: on timeout.
            MCPToolError: if tool returns error.
            MCPServerUnavailableError: if server is dead.
        """
        ...

    def get_capture_summary(self, target: str) -> CaptureSummaryResult:
        """Call lifeos.capture_summary tool.
        
        Args:
            target: capture_id (cap_*), integer index as string (e.g. "3"), or "latest".
        
        Raises:
            MCPTimeoutError, MCPToolError (e.g. not found), MCPServerUnavailableError.
        """
        ...

    def get_capture_metadata(self, target: str) -> CaptureMetadataResult:
        """Call lifeos.capture_metadata tool.
        
        Args:
            target: capture_id (cap_*), integer index as string, or "latest".
        
        Raises:
            MCPTimeoutError, MCPToolError, MCPServerUnavailableError.
        """
        ...

    def get_template_catalog(self, note_type: Optional[str] = None) -> TemplateCatalogResult:
        """Call lifeos.template_catalog tool.
        
        Args:
            note_type: Optional filter. One of "knowledge", "project", "idea", 
                       "reference", "media", "daily", "decision", or None for all.
        
        Raises:
            MCPTimeoutError, MCPToolError, MCPServerUnavailableError.
        """
        ...

    def get_current_working_state(self) -> WorkingStateResult:
        """Call lifeos.current_working_state_summary tool.
        
        Raises:
            MCPTimeoutError, MCPToolError, MCPServerUnavailableError.
        """
        ...

    # ── Context manager ──

    def __enter__(self): ...
    def __exit__(self, exc_type, exc_val, exc_tb): ...


# ── Factory function ──

def create_mcp_client(server_script: str = None, timeout: float = 10.0) -> LifeOSMCPClient:
    """Create and start an MCP client. Returns a ready-to-use client.
    
    Convenience: calls __init__ + start().
    Raises MCPServerUnavailableError if server cannot start.
    """
    ...
```

#### Safety Enforcements in MCP Client

1. **No arbitrary tool calling**: No generic `call_tool(name, args)` method. Only the 5 typed methods above.
2. **Subprocess isolation**: Server runs as child process. If the client dies, the server gets SIGPIPE/SIGTERM.
3. **Timeout on every call**: Default 10s per tool. Prevents hung processes.
4. **No stdin passthrough**: Client never forwards user input to the server beyond typed arguments.
5. **Response validation**: Every response is validated against the expected schema before returning. Unexpected fields are dropped; missing required fields raise `MCPToolError`.

### 2.3 Capture Review Orchestrator CLI

**Module path**: `40_Services/capture_orchestrator/orchestrator.py`
**Dependencies**: Python stdlib, mcp_client, agents/*, proposal_packet, controlled_importer
**Process model**: Short-lived CLI. Each command starts, does work, and exits.

#### CLI Commands

```bash
# ── Knowledge Proposal Pipeline ──

python orchestrator.py propose-knowledge <target>
  # target: capture_id (cap_*), integer index, "latest"
  # Pipeline: resolve capture → MCP context → classifier → knowledge_curator 
  #           → qa_verifier → import_planner → write proposal packet
  # Output to stdout: {"proposal_id": "prop_...", "status": "pending_human_review", "path": "..."}
  # Exit codes: 0=success, 1=capture not found, 2=proposal generation failed, 
  #             3=MCP unavailable (fallback used), 4=QA blocked

python orchestrator.py view-proposal <proposal_id>
  # proposal_id: prop_YYYYMMDDTHHMMSSZ_short_capture_id_short_hash
  # Output to stdout: proposal packet content as formatted text
  # Exit codes: 0=success, 1=not found

python orchestrator.py reject-proposal <proposal_id> [reason]
  # Moves proposal to rejected state. Archives proposal packet.
  # Output to stdout: {"proposal_id": "...", "status": "rejected", "reason": "..."}
  # Exit codes: 0=success, 1=not found, 2=invalid transition (already imported/rejected)

python orchestrator.py revise-proposal <proposal_id> [feedback]
  # Marks proposal as revision_requested. Agent re-generates with feedback.
  # Re-runs: knowledge_curator → qa_verifier → import_planner
  # Output to stdout: {"proposal_id": "...", "status": "pending_human_review", "revision": int}
  # Exit codes: 0=success, 1=not found, 2=revision generation failed

python orchestrator.py approve-import <proposal_id>
  # Validates proposal is in approved_for_import state.
  # Calls controlled importer to write to canonical vault.
  # Output to stdout: {"proposal_id": "...", "status": "imported", "import_manifest": {...}}
  # Exit codes: 0=success, 1=not found, 2=not yet approved, 3=import failed, 
  #             4=content hash mismatch, 5=path traversal blocked
```

#### Internal Pipeline (`propose-knowledge`)

```python
def cmd_propose_knowledge(target: str) -> dict:
    """
    Pipeline:
    1. RESOLVE: Find capture by target (index, capture_id, or latest).
       Uses filesystem walk (not MCP — MCP is supplementary).
    2. CONTEXT: Call MCP tools for enrichment (fallback/empty if MCP unavailable).
       - lifeos.capture_metadata(target)
       - lifeos.template_catalog("knowledge")
       - lifeos.current_working_state_summary()
    3. CLASSIFY: classifier.classify(text, mcp_context)
       → ClassificationResult(type, route, confidence, flags)
    4. CURATE: knowledge_curator.draft(capture, classification, mcp_context)
       → DraftNote(content, frontmatter, warnings)
    5. VERIFY: qa_verifier.validate(draft, classification, template_catalog)
       → QAResult(verdict, issues, warnings, block)
    6. If QA blocks: exit with error, proposed_id=None, reason in stdout.
    7. PLAN: import_planner.plan(capture, classification, draft, qa_result, mcp_context)
       → ProposalPacket + ImportManifest
    8. WRITE: Write proposal packet to buffer vault.
       Path: LifeOS_Capture_Buffer/03_Review_Packets/proposals/{proposal_id}.md
    9. RETURN: proposal_id, status, path to stdout as JSON.
    """
    ...
```

#### Proposal ID Generation

```python
def generate_proposal_id(capture_id: str, content_hash: str) -> str:
    """
    Format: prop_YYYYMMDDTHHMMSSZ_short_capture_id_short_hash
    
    Example:
      capture_id: cap_20260708_123456_abc123def456
      content_hash: sha256 first 8 chars = "a1b2c3d4"
      → prop_20260708T123456Z_cap_abc123_a1b2c3d4
    
    Components:
      - prop_  (fixed prefix)
      - YYYYMMDDTHHMMSSZ  (UTC timestamp of proposal generation)
      - short_capture_id: first 3 segments of capture_id joined (cap_YYYYMMDD_HHMMSS → cap_YYYYMMDD_HHMMSS)
        then truncated to 16 chars max
      - short_hash: first 8 chars of sha256(content)
    """
    ...
```

#### MCP Fallback Behavior

```python
def resolve_capture(target: str, mcp_client: Optional[LifeOSMCPClient]) -> dict:
    """
    Primary resolution: filesystem walk in 30_Capture/pending_review/.
    MCP provides enrichment, not primary data access.
    
    If MCP client is None or calls fail:
      - classification still works (text-based only, no template catalog context)
      - knowledge_curator drafts without working state context (may miss cross-links)
      - qa_verifier validates against built-in template schemas (not catalog)
      - import_planner works with reduced context
    
    MCP failure is non-blocking for proposal generation.
    Proposal quality degrades gracefully, not catastrophically.
    """
    ...
```

### 2.4 Specialist Agent Modules

**Parent path**: `40_Services/capture_orchestrator/agents/`
**Design**: Each agent is a single-file Python module with a pure function interface. No classes unless internal state is complex. No AI/LLM calls. Deterministic, testable, fast.

#### 2.4.1 Classifier (`agents/classifier.py`)

```python
"""
Classifier Agent: Determines capture type and suggests processing route.
Deterministic rule-based classification. No AI/ML.
"""

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ClassificationResult:
    capture_id: str
    detected_type: str           # "url_article"|"url_video"|"url_github"|"text"|"idea"|
                                 # "task"|"note"|"project_idea"|"link"|"unknown"
    suggested_route: str         # "knowledge_note"|"reference"|"idea"|"project"|"inbox"
    confidence: float            # 0.0 - 1.0
    subtype: Optional[str]       # e.g. "blog", "documentation", "youtube", "github_repo"
    flags: list                  # e.g. ["has_urls", "has_code_blocks", "short_text"]
    requires_processors: list    # e.g. ["article_processor"]
    language_hint: str           # "en" default
    notes: str


def classify(text: str, capture_id: str = "",
             mcp_context: Optional[dict] = None,
             frontmatter: Optional[dict] = None) -> ClassificationResult:
    """
    Classify a capture's text content to determine its type and processing route.
    
    Args:
        text: Raw capture text content.
        capture_id: Capture identifier (for result linking).
        mcp_context: Optional enrichment from MCP (template catalog, working state).
        frontmatter: Optional pre-parsed frontmatter from capture file.
    
    Returns:
        ClassificationResult with detected_type and suggested_route.
    
    Classification rules (priority order):
    1. URL detection by pattern → classify URL type (article/video/github/other)
    2. Idea markers: starts with "idea:", contains "what if", contains "maybe I should"
    3. Task markers: starts with "todo:", "task:", contains "[ ]", contains "action:"
    4. Project markers: contains "project:", "build a", "create a", multi-paragraph
    5. Length heuristic: < 140 chars → note; >= 140 chars → potential knowledge
    6. Fallback: unknown
    
    The classifier is intentionally conservative — low confidence for ambiguous
    captures so the human has final say.
    """
    ...


# ── Internal helpers (not exported) ──

def _detect_url_type(url: str) -> tuple:
    """Classify a URL into article/video/audio/github/other."""
    ...

def _detect_idea_markers(text: str) -> float:
    """Return confidence that text is an idea (0.0-1.0)."""
    ...

def _detect_task_markers(text: str) -> float:
    """Return confidence that text is a task (0.0-1.0)."""
    ...

def _detect_project_markers(text: str) -> float:
    """Return confidence that text is a project idea (0.0-1.0)."""
    ...
```

#### 2.4.2 Knowledge Curator (`agents/knowledge_curator.py`)

```python
"""
Knowledge Curator Agent: Drafts a LifeOS Knowledge note from a capture.
Deterministic template-based generation. No AI/LLM.
Extracts key information from source text and formats into the Knowledge template.
"""

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class DraftNote:
    capture_id: str
    note_type: str               # "knowledge"
    title: str
    frontmatter: dict            # YAML-ready dict
    content: str                 # Full note body in Markdown
    sections_present: list       # Which template sections were filled
    sections_missing: list       # Which template sections could not be filled
    warnings: list               # e.g. "source material thin for Core Concept"
    content_hash: str            # sha256 of content


def draft(capture: dict,                          # capture_id, content, source_type, urls
          classification: ClassificationResult,
          mcp_context: Optional[dict] = None,
          template_catalog: Optional[list] = None) -> DraftNote:
    """
    Draft a Knowledge note from a capture.
    
    Args:
        capture: Dict with keys: capture_id, content (str), source_type, 
                 created_at, urls (list).
        classification: Output from classifier.classify().
        mcp_context: Optional working state for cross-linking suggestions.
        template_catalog: Optional template catalog for section requirements.
    
    Returns:
        DraftNote with populated frontmatter and content.
    
    Drafting strategy (deterministic):
    1. Extract title from content (first line heuristic, URL path, or "Untitled")
    2. Build frontmatter: aliases, tags (from content keyword extraction), 
       domain (from classifier + content analysis), timestamps, 
       confidence: "machine_generated_unreviewed"
    3. Definition section: extract first substantive sentence or synthesize from title
    4. Why It Matters: from content context + domain keywords
    5. Core Concept: restructure content into paragraphs, preserving factual claims
    6. How It Works: extract process/step descriptions if present
    7. Examples: extract code blocks, numbered lists, or cited examples
    8. LifeOS Relationships: suggest links based on mcp_context projects/decisions
    9. Safety/Caveats: static per-domain warnings + content-specific flags
    10. Common Problems: only if content mentions problems/issues
    11. Related Concepts: keyword-based suggestions
    12. Source Trail: capture_id, source_url, extraction_quality
    
    If a section cannot be filled, mark as "[No information in source material.]"
    rather than fabricating content.
    """
    ...


# ── Internal helpers ──

def _extract_title(text: str, url: Optional[str]) -> str: ...

def _extract_keywords(text: str, max_keywords: int = 5) -> list: ...

def _infer_domain(text: str, classification: ClassificationResult) -> str: ...

def _extract_definition(text: str, title: str) -> str: ...

def _extract_why_it_matters(text: str, domain: str) -> str: ...

def _restructure_core_concept(text: str) -> str: ...

def _extract_examples(text: str) -> str: ...

def _suggest_links(keywords: list, mcp_context: dict) -> list: ...

def _domain_safety_caveats(domain: str) -> str: ...

def _generate_frontmatter(title: str, capture_id: str, source_url: Optional[str],
                          domain: str, keywords: list, created_at: str) -> dict: ...
```

#### 2.4.3 Import Planner (`agents/import_planner.py`)

```python
"""
Import Planner Agent: Assembles proposal packet and import manifest from
agent outputs. Does NOT create content — only assembles.
"""

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ProposalPacket:
    proposal_id: str             # prop_YYYYMMDDTHHMMSSZ_short_capture_id_short_hash
    capture_id: str
    status: str                  # "pending_human_review"
    title: str
    capture_summary: dict        # source, type, timestamps, preview
    proposed_changes: dict       # files_to_create, files_to_update, files_not_touched
    agent_outputs: dict          # {agent_name: output_summary}
    summary_of_changes: str      # human-readable 2-5 sentence summary
    source_trail: dict           # capture chain, URLs, extraction quality
    risks: list                  # {risk, severity, description, mitigation}
    qa_result: dict              # QA report summary
    approval_checklist: list     # human checklist items
    import_command: str          # CLI command to execute import
    rollback_procedure: str      # CLI command + description
    revision_count: int          # starts at 0
    created_at: str              # ISO8601
    updated_at: str              # ISO8601

@dataclass
class ImportManifest:
    proposal_id: str
    capture_id: str
    status: str                  # "pending_approval" | "approved" | "imported"
    files_to_create: list        # [{source, destination, type, action: "create"}]
    files_to_update: list        # [{path, change_description}]
    files_to_not_touch: list     # ["*"] or specific paths
    dependencies: list
    rollback_actions: list       # [{action: "delete"|"revert", path: str}]
    qa_report_ref: str           # path to QA report in buffer vault
    content_hash: str            # sha256 of the combined draft content
    approved_by: Optional[str]
    approved_at: Optional[str]


def plan(capture: dict,
         classification: ClassificationResult,
         draft: DraftNote,
         qa_result: dict,                    # from qa_verifier
         mcp_context: Optional[dict] = None,
         template_catalog: Optional[list] = None) -> tuple:
    """
    Assemble a ProposalPacket and ImportManifest from agent outputs.
    
    Args:
        capture: Raw capture data.
        classification: Classifier output.
        draft: Knowledge curator output.
        qa_result: QA verifier output.
        mcp_context: Optional working state for destination path suggestions.
        template_catalog: Optional for destination pattern selection.
    
    Returns:
        (ProposalPacket, ImportManifest) tuple.
    
    Assembly logic:
    1. Generate proposal_id from capture_id + draft.content_hash
    2. Determine destination path from template_catalog destination_pattern
       paired with draft's domain and title.
       Example: "04_KNOWLEDGE/software-engineering/Container Security.md"
    3. Build files_to_create: source in buffer vault → destination in canonical vault
    4. Build files_to_update: empty for new knowledge notes
    5. Build files_not_touched: ["*"] — all other vault files
    6. Generate summary_of_changes from draft + classification
    7. Collect risks from classification.flags + qa_result.warnings + 
       static risk catalog
    8. Build approval_checklist specific to note type
    9. Generate import_command: "python orchestrator.py approve-import {proposal_id}"
    10. Generate rollback_procedure with exact paths
    11. Set status: "pending_approval"
    """
    ...


# ── Helpers ──

def _determine_destination(draft: DraftNote, template_catalog: list) -> str:
    """Map draft to a canonical vault path."""
    ...

def _generate_summary(draft: DraftNote, classification: ClassificationResult) -> str:
    """Generate a 2-5 sentence human-readable summary."""
    ...

def _collect_risks(classification: ClassificationResult, qa_result: dict,
                   draft: DraftNote) -> list:
    """Collect all risks from agent outputs."""
    ...

def _build_checklist(note_type: str) -> list:
    """Return type-specific human approval checklist items."""
    ...

def _build_rollback_actions(files_to_create: list) -> list:
    """Generate rollback manifest from files_to_create."""
    ...
```

#### 2.4.4 QA Verifier (`agents/qa_verifier.py`)

```python
"""
QA Verifier Agent: Validates draft notes before proposal generation.
Checks template compliance, secret leakage, content quality, link validity.
Deterministic, fast, blocking on critical failures.
"""

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class QAResult:
    capture_id: str
    overall_verdict: str         # "pass" | "fail" | "pass_with_warnings"
    block_import: bool           # True if overall_verdict == "fail"
    checks: dict                 # Per-check results {check_name: {status, details, ...}}
    warnings: list               # Human-readable warning strings
    recommendations: list        # Actionable recommendations
    timestamp: str               # ISO8601


def validate(draft: DraftNote,
             classification: ClassificationResult,
             template_catalog: Optional[list] = None,
             source_text: Optional[str] = None) -> QAResult:
    """
    Validate a draft note against quality and safety standards.
    
    Args:
        draft: DraftNote from knowledge_curator.
        classification: Classifier output (for cross-reference).
        template_catalog: Optional template catalog for section validation.
        source_text: Optional raw source text for hallucination cross-check.
    
    Returns:
        QAResult with overall verdict and detailed check results.
    
    Checks performed (in order, short-circuit on blocking):
    1. SECRET_LEAKAGE (BLOCKING):
       - Regex patterns for API keys, tokens, passwords, private keys
       - High-entropy string detection (base64-looking strings > 32 chars)
       - Email addresses in content body (privacy concern)
    2. TEMPLATE_COMPLIANCE (BLOCKING if missing required sections):
       - All required sections present per template_catalog or built-in knowledge
       - No section is placeholder-only ("[No information...]" is acceptable)
    3. YAML_FRONTMATTER (BLOCKING if malformed or missing required fields):
       - Required fields: aliases, tags, domain, created, source_capture, 
         status, confidence
       - Status must be "draft"
       - Confidence must be "machine_generated_unreviewed"
    4. SOURCE_TRAIL (BLOCKING if missing capture_id or source_url):
       - Capture ID present
       - Source URL or "personal capture" noted
       - Extraction quality field present
    5. CONTENT_QUALITY (NON-BLOCKING):
       - Core Concept section contains substantive content (>100 chars)
       - Definition is self-contained (not just a title repetition)
       - No obviously fabricated statistics ("According to a 2025 study..." 
         without source attribution)
    6. FOLDER_CORRECTNESS (NON-BLOCKING):
       - Destination folder suggestion is appropriate for note type
       - Path does not conflict with existing vault structure conventions
    7. GRAPH_CLUTTER (NON-BLOCKING):
       - Link count is reasonable (<15 outbound per note)
       - No self-links
    8. HALLUCINATION_CHECK (NON-BLOCKING if source_text provided):
       - Claims in draft that don't appear in source_text are flagged
       - Number mismatches between source and draft
    """
    ...


# ── Internal check functions ──

def _check_secret_leakage(content: str) -> dict:
    """
    Scan for secrets using regex patterns.
    Patterns: API keys (sk-*, pk-*, AIza*, gh*_*, etc.), 
    AWS keys (AKIA*, ABIA*, etc.), private keys (BEGIN PRIVATE KEY),
    JWT tokens (eyJ*), connection strings, passwords in key=value patterns.
    
    Returns: {status, details, findings: [{pattern, location_preview}]}
    Location preview must NOT include the actual secret — only the pattern type
    and approximate position.
    """
    ...

def _check_template_compliance(sections_present: list, sections_missing: list,
                                template_catalog: list) -> dict: ...

def _check_yaml_frontmatter(frontmatter: dict) -> dict: ...

def _check_source_trail(frontmatter: dict, capture_id: str) -> dict: ...

def _check_content_quality(draft_content: str, sections_present: list) -> dict: ...

def _check_folder_correctness(destination: str, note_type: str) -> dict: ...

def _check_graph_clutter(draft_content: str) -> dict: ...

def _check_hallucination(draft_content: str, source_text: str) -> dict: ...
```

### 2.5 Proposal Packet Lifecycle

**Data model**: `40_Services/capture_orchestrator/proposal_packet.py`

```python
"""
Proposal Packet data model and lifecycle state machine.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum
import json
import os
import hashlib
from datetime import datetime, timezone


class ProposalStatus(Enum):
    PENDING_HUMAN_REVIEW = "pending_human_review"
    REVISION_REQUESTED = "revision_requested"
    APPROVED_FOR_IMPORT = "approved_for_import"
    IMPORTED = "imported"
    REJECTED = "rejected"


# Valid transitions
TRANSITIONS = {
    ProposalStatus.PENDING_HUMAN_REVIEW: {
        ProposalStatus.REVISION_REQUESTED,
        ProposalStatus.APPROVED_FOR_IMPORT,
        ProposalStatus.REJECTED,
    },
    ProposalStatus.REVISION_REQUESTED: {
        ProposalStatus.PENDING_HUMAN_REVIEW,  # after revision
        ProposalStatus.REJECTED,
    },
    ProposalStatus.APPROVED_FOR_IMPORT: {
        ProposalStatus.IMPORTED,
        ProposalStatus.REJECTED,  # last-minute rejection
    },
    ProposalStatus.IMPORTED: set(),      # terminal
    ProposalStatus.REJECTED: set(),      # terminal
}


@dataclass
class ProposalPacket:
    proposal_id: str
    capture_id: str
    status: str                              # matches ProposalStatus values
    title: str
    capture_summary: dict
    proposed_changes: dict
    agent_outputs: dict
    summary_of_changes: str
    source_trail: dict
    risks: list
    qa_result: dict
    approval_checklist: list
    import_command: str
    rollback_procedure: str
    import_manifest: dict
    revision_count: int = 0
    revision_history: list = field(default_factory=list)  # [{timestamp, feedback, revisor}]
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if not self.updated_at:
            self.updated_at = self.created_at


# ── Proposal ID generation ──

def generate_proposal_id(capture_id: str, content: str,
                         timestamp: Optional[str] = None) -> str:
    """
    Generate a unique proposal ID.
    
    Format: prop_YYYYMMDDTHHMMSSZ_short_capture_id_short_hash
    
    short_capture_id: first portion of capture_id, truncated to 16 chars.
      cap_20260708_123456_abc123 → cap_20260708_1234 (16 chars)
    short_hash: first 8 chars of sha256(content)
    
    Example: prop_20260708T143021Z_cap_20260708_1234_a1b2c3d4
    """
    ts = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short_cid = capture_id[:16] if len(capture_id) > 16 else capture_id
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:8]
    return f"prop_{ts}_{short_cid}_{content_hash}"


# ── Storage paths ──

PROPOSALS_DIR = "/home/lifeos/LifeOS_Capture_Buffer/03_Review_Packets/proposals"

def proposal_path(proposal_id: str) -> str:
    """Return the file path for a proposal packet."""
    return os.path.join(PROPOSALS_DIR, f"{proposal_id}.json")

def proposal_markdown_path(proposal_id: str) -> str:
    """Return the file path for the human-readable proposal."""
    return os.path.join(PROPOSALS_DIR, f"{proposal_id}.md")


# ── Load/Save with hash verification ──

def save_proposal(packet: ProposalPacket) -> str:
    """Serialize and write proposal to buffer vault. Returns file path."""
    ...

def load_proposal(proposal_id: str) -> ProposalPacket:
    """Load and deserialize a proposal from buffer vault. Raises FileNotFoundError."""
    ...

def update_status(proposal_id: str, new_status: ProposalStatus,
                  metadata: Optional[dict] = None) -> ProposalPacket:
    """
    Atomically update proposal status with transition validation.
    Raises ValueError if transition is invalid.
    """
    ...

def list_proposals(status_filter: Optional[ProposalStatus] = None) -> list:
    """List all proposals, optionally filtered by status."""
    ...
```

#### Lifecycle State Diagram

```
                      ┌──────────────┐
                      │   CAPTURE    │
                      │  (in queue)  │
                      └──────┬───────┘
                             │ propose-knowledge
                             ▼
                ┌────────────────────────────┐
                │  PENDING_HUMAN_REVIEW      │
                │  (proposal packet written   │
                │   to buffer vault)          │
                └────┬───────┬───────┬───────┘
                     │       │       │
        ┌────────────┘       │       └────────────┐
        ▼                    ▼                    ▼
┌───────────────┐  ┌──────────────────┐  ┌──────────────┐
│ REVISION_     │  │ APPROVED_FOR_    │  │  REJECTED    │
│ REQUESTED     │  │ IMPORT           │  │  (terminal)  │
│ (feedback     │  │ (human signed    │  └──────────────┘
│  recorded)    │  │  off on import)  │
└───┬───────┬───┘  └────────┬─────────┘
    │       │               │
    │       └──────────┐    │ approve-import
    │                  ▼    ▼
    │          ┌──────────────┐     ┌──────────────┐
    │          │  REJECTED    │     │  IMPORTED    │
    │          │  (terminal)  │     │  (terminal)  │
    │          └──────────────┘     └──────────────┘
    │
    │ revise-proposal (agent re-runs with feedback)
    ▼
    (back to PENDING_HUMAN_REVIEW with incremented revision_count)
```

### 2.6 Controlled Importer

**Module path**: `40_Services/capture_orchestrator/controlled_importer.py`
**Dependencies**: Python stdlib only (os, shutil, hashlib, json, pathlib)

```python
"""
Controlled Importer: The ONLY module that writes to the canonical LifeOS vault.
Called exclusively by the orchestrator after explicit human approval.
"""

from dataclasses import dataclass
from typing import Optional
import hashlib
import shutil
import os
import json
from pathlib import Path
from datetime import datetime, timezone


# ── Constants ──

CANONICAL_VAULT_ROOT = "/home/lifeos/10_Vaults/LifeOS"
EVENT_LOG_PATH = "/home/lifeos/50_Event_Log/events.jsonl"

# Deny-list of destinations that must never be written to
# (even if somehow appearing in an import manifest)
DESTINATION_DENY_LIST = [
    "10_AI_UNIVERSE/System_Registry.md",
    "10_AI_UNIVERSE/Approval_Tiers.md",
    "10_AI_UNIVERSE/Workflow_Governor.md",
    ".git/",
    ".obsidian/workspace",
]


class ImportError(Exception): pass
class ContentHashMismatchError(ImportError): pass
class PathTraversalBlockedError(ImportError): pass
class DestinationDeniedError(ImportError): pass
class ImportConflictError(ImportError): pass


@dataclass
class ImportResult:
    proposal_id: str
    status: str                  # "imported" | "failed"
    files_created: list          # paths relative to vault root
    files_updated: list
    files_skipped: list
    rollback_manifest: dict      # for reversing this import
    event_id: str
    imported_at: str


def execute_import(proposal_id: str, import_manifest: dict) -> ImportResult:
    """
    Execute a controlled import into the canonical vault.
    
    Args:
        proposal_id: The approved proposal ID.
        import_manifest: The ImportManifest dict from the proposal packet.
                        Must include: files_to_create, files_to_update,
                        files_to_not_touch, content_hash.
    
    Returns:
        ImportResult with details of what was imported.
    
    Raises:
        ContentHashMismatchError: if the live content hash doesn't match the manifest.
        PathTraversalBlockedError: if any destination path escapes the vault root.
        DestinationDeniedError: if destination is in the deny list.
        ImportConflictError: if a file_to_create already exists.
    
    Safety enforcement (in order):
    1. CONTENT HASH VALIDATION:
       - Re-compute sha256 of the draft source file(s).
       - Compare against content_hash in manifest.
       - Reject on mismatch → prevents tampering between approval and import.
    
    2. PATH TRAVERSAL PROTECTION:
       - Resolve all destination paths with os.path.realpath().
       - Verify every resolved path starts with CANONICAL_VAULT_ROOT.
       - Reject any path containing ".." or symlink escapes.
    
    3. DESTINATION DENY LIST:
       - Check every destination against DESTINATION_DENY_LIST.
       - Reject if any destination is in the deny list.
    
    4. CONFLICT DETECTION:
       - For files_to_create: check if file already exists.
       - For files_to_update: check if file exists (required for update).
       - Reject on unexpected conflicts.
    
    5. ATOMIC WRITE:
       - Write to a .tmp file first.
       - On success, rename to final path.
       - On any failure, clean up .tmp files.
    
    6. EVENT LOGGING:
       - Append import event to events.jsonl.
       - Include: proposal_id, capture_id, files created/updated, 
         content_hash, timestamp.
    
    7. ROLLBACK MANIFEST:
       - Record exact paths created/updated.
       - Store in buffer vault for potential rollback.
    """
    ...


def validate_path(destination: str) -> str:
    """
    Validate a destination path and return its resolved absolute path.
    
    Checks:
    - No null bytes
    - No ".." segments that escape vault root
    - Realpath resolves within CANONICAL_VAULT_ROOT
    - Not in DESTINATION_DENY_LIST
    
    Returns: resolved absolute path.
    Raises: PathTraversalBlockedError, DestinationDeniedError.
    """
    ...


def validate_content_hash(source_path: str, expected_hash: str) -> None:
    """
    Compute sha256 of file at source_path and compare to expected_hash.
    Raises ContentHashMismatchError on mismatch.
    """
    ...


def write_atomic(destination: str, content: str) -> None:
    """
    Write content to destination atomically:
    1. Write to {destination}.tmp.{pid}
    2. fsync the tmp file
    3. os.rename to destination
    4. On failure: clean up tmp file
    """
    ...


def append_import_event(proposal_id: str, capture_id: str, 
                        result: ImportResult) -> str:
    """
    Append an import event to the event log.
    Returns the event_id.
    """
    ...


def generate_rollback_manifest(proposal_id: str, files_created: list,
                                files_updated: list) -> dict:
    """
    Generate a rollback manifest that can be used to reverse this import.
    Stored in LifeOS_Capture_Buffer/04_Approved_For_Import/{proposal_id}_rollback.json
    """
    ...


def execute_rollback(proposal_id: str) -> ImportResult:
    """
    Execute a rollback for a previously imported proposal.
    Reads the rollback manifest, deletes created files, reverts updated files.
    Must be explicitly called — not automatic.
    """
    ...
```

### 2.7 Telegram Command Flow

#### Existing Telegram Bot Integration

The Telegram bot (`telegram_capture_bot.py`) already has:
- HMAC-signed callback tokens for button actions
- Action API integration for capture CRUD
- Inline button keyboard ([View Full] [Proposal] [Approve] [Reject])
- `/proposal` command (current V1: template-based only)

#### SAFEST V0 Changes to Telegram Bot

```python
# ── New /kt command (Knowledge Transform) ──

# The /kt command replaces /proposal's current behavior with the orchestrator.
# Existing /proposal continues to work as the lightweight, no-AI, template-based
# preview. /kt is the full orchestrator pipeline.

def handle_kt(text: str, chat_id: int):
    """
    Usage: /kt <n|latest|capture_id>
    
    Calls the orchestrator CLI:
      python orchestrator.py propose-knowledge <target>
    
    Flow:
    1. Parse target from /kt command
    2. Call subprocess: orchestrator.py propose-knowledge <target>
       - Capture stdout as JSON
       - Capture stderr for error messages
    3. Parse response:
       - Success: {"proposal_id": "...", "status": "pending_human_review", "path": "..."}
         → Send formatted proposal card to Telegram
         → Store proposal_id in callback token for future button actions
       - Error (exit code != 0): 
         → Send safe error card (no traceback, no raw stderr to user)
         → Log full error to event log
    """
    ...


# ── Updated button handlers ──

def _handle_proposal_button(chat_id: int, cap_ref: str, sender_id: int):
    """
    Updated: for captures that have a KT proposal, show the proposal.
    For captures without KT proposal, show the legacy template-based proposal.
    """
    ...


def _handle_approve_button(chat_id: int, cap_ref: str, sender_id: int):
    """
    Updated: after approving a capture that has a KT proposal,
    automatically call: orchestrator.py approve-import <proposal_id>
    if the proposal exists and is in pending_human_review state.
    
    Other captures (without KT proposal) use legacy approve flow.
    """
    ...


def _handle_reject_button(chat_id: int, cap_ref: str, sender_id: int):
    """
    Updated: after rejecting a capture that has a KT proposal,
    automatically call: orchestrator.py reject-proposal <proposal_id>
    if the proposal exists.
    """
    ...


def _handle_kt_approve(chat_id: int, proposal_id: str):
    """
    Called from approve confirmation flow for KT proposals.
    Steps:
    1. Call orchestrator.py approve-import <proposal_id>
    2. On success: send "Import complete" receipt with event_id
    3. On failure: send safe error card with reason
    """
    ...


def _handle_kt_reject(chat_id: int, proposal_id: str, reason: str = ""):
    """
    Called from reject confirmation flow for KT proposals.
    Steps:
    1. Call orchestrator.py reject-proposal <proposal_id> [reason]
    2. On success: send "Proposal rejected" receipt
    3. Also reject the underlying capture through Action API
    """
    ...


def _handle_kt_revise(chat_id: int, proposal_id: str, feedback: str = ""):
    """
    Called from revise button for KT proposals.
    Steps:
    1. Call orchestrator.py revise-proposal <proposal_id> [feedback]
    2. On success: send revised proposal card
    3. On failure: send safe error card
    """
    ...
```

#### Error Handling in Telegram

```python
# ── Safe error formatting (no traceback exposure) ──

def _orchestrator_error_to_telegram(exit_code: int, stderr: str, 
                                     proposal_id: str = None) -> str:
    """
    Map orchestrator exit codes to safe, user-friendly Telegram messages.
    Never expose raw stderr or Python tracebacks to the user.
    
    Exit code mapping:
      0 → success (not an error)
      1 → "Could not find that capture. Check the index with /p."
      2 → "Could not generate a proposal for this capture. 
           The content may be too short or unclear."
      3 → "MCP services unavailable. Generated proposal with reduced context. 
           Review carefully."
      4 → "QA checks blocked this proposal. Common reasons: 
           potential secrets in content, missing required sections, 
           or content quality too low. Check the capture with /view."
      5 → "Import blocked: content hash mismatch. 
           The proposal may have been modified. Re-generate with /kt."
      6 → "Import blocked: path safety violation. 
           This is a system-level safety block."
    """
    mapping = {
        1: "Could not find that capture. Check the index with /p.",
        2: "Could not generate a proposal. The content may be too short or unclear.",
        3: "MCP unavailable. Proposal generated with reduced context. Review carefully.",
        4: "QA checks blocked this proposal. Check the capture with /view.",
        5: "Import blocked: content mismatch. Regenerate with /kt.",
        6: "Import blocked: path safety violation.",
    }
    msg = mapping.get(exit_code, f"Orchestrator error (code {exit_code}).")
    
    # Log full details to event log (NOT to Telegram)
    _log_orchestrator_error(exit_code, stderr, proposal_id)
    
    return msg


def _log_orchestrator_error(exit_code: int, stderr: str, proposal_id: str = None):
    """Log full orchestrator error to event log for debugging."""
    # Append to 50_Event_Log/events.jsonl
    # Include: timestamp, exit_code, stderr (sanitized for secrets), proposal_id
    ...
```

## 3. Data Flow Diagrams

### 3.1 Full Knowledge Transform Flow

```
USER              TELEGRAM BOT           ORCHESTRATOR CLI         MCP CLIENT
 │                     │                       │                      │
 │  /kt 3              │                       │                      │
 │────────────────────>│                       │                      │
 │                     │                       │                      │
 │                     │  subprocess.run(      │                      │
 │                     │    "orchestrator.py   │                      │
 │                     │     propose-knowledge │                      │
 │                     │     3")               │                      │
 │                     │──────────────────────>│                      │
 │                     │                       │                      │
 │                     │                       │  resolve capture     │
 │                     │                       │  (filesystem walk)   │
 │                     │                       │                      │
 │                     │                       │  mcp.get_capture_    │
 │                     │                       │  metadata("3")       │
 │                     │                       │─────────────────────>│
 │                     │                       │                      │──> MCP SERVER
 │                     │                       │                      │<── CaptureMetadata
 │                     │                       │<─────────────────────│
 │                     │                       │                      │
 │                     │                       │  mcp.get_template_   │
 │                     │                       │  catalog("knowledge")│
 │                     │                       │─────────────────────>│
 │                     │                       │                      │──> MCP SERVER
 │                     │                       │                      │<── TemplateCatalog
 │                     │                       │<─────────────────────│
 │                     │                       │                      │
 │                     │                       │  mcp.get_current_    │
 │                     │                       │  working_state()     │
 │                     │                       │─────────────────────>│
 │                     │                       │                      │──> MCP SERVER
 │                     │                       │                      │<── WorkingState
 │                     │                       │<─────────────────────│
 │                     │                       │                      │
 │                     │                       │  classifier.classify()         │
 │                     │                       │  → ClassificationResult         │
 │                     │                       │                      │
 │                     │                       │  knowledge_curator.draft()      │
 │                     │                       │  → DraftNote                    │
 │                     │                       │                      │
 │                     │                       │  qa_verifier.validate()         │
 │                     │                       │  → QAResult                     │
 │                     │                       │  (if block → exit 4)            │
 │                     │                       │                      │
 │                     │                       │  import_planner.plan()          │
 │                     │                       │  → ProposalPacket + Manifest    │
 │                     │                       │                      │
 │                     │                       │  write to:                     │
 │                     │                       │  Buffer/03_Review_   │
 │                     │                       │  Packets/proposals/  │
 │                     │                       │  {proposal_id}.json  │
 │                     │                       │  {proposal_id}.md    │
 │                     │                       │                      │
 │                     │  stdout JSON:         │                      │
 │                     │  {"proposal_id":      │                      │
 │                     │   "prop_...",         │                      │
 │                     │   "status":           │                      │
 │                     │   "pending_human_     │                      │
 │                     │    review", ...}      │                      │
 │                     │<──────────────────────│                      │
 │                     │                       │                      │
 │  Proposal card      │                       │                      │
 │  with buttons       │                       │                      │
 │<────────────────────│                       │                      │
 │                     │                       │                      │
 │  [Approve]          │                       │                      │
 │────────────────────>│                       │                      │
 │                     │                       │                      │
 │                     │  confirm intent       │                      │
 │<────────────────────│                       │                      │
 │                     │                       │                      │
 │  [Confirm Approve]  │                       │                      │
 │────────────────────>│                       │                      │
 │                     │                       │                      │
 │                     │  subprocess.run(      │                      │
 │                     │    "orchestrator.py   │                      │
 │                     │     approve-import    │                      │
 │                     │     prop_...")        │                      │
 │                     │──────────────────────>│                      │
 │                     │                       │                      │
 │                     │                       │  load proposal       │
 │                     │                       │  validate status     │
 │                     │                       │                      │
 │                     │                       │  controlled_importer │
 │                     │                       │  .execute_import()   │
 │                     │                       │  → hash check        │
 │                     │                       │  → path traversal    │
 │                     │                       │  → atomic write      │
 │                     │                       │  → event log         │
 │                     │                       │                      │
 │                     │  stdout JSON:         │                      │
 │                     │  {"status":           │                      │
 │                     │   "imported",         │                      │
 │                     │   "event_id": "..."}  │                      │
 │                     │<──────────────────────│                      │
 │                     │                       │                      │
 │  Import receipt     │                       │                      │
 │  "Vault updated.    │                       │                      │
 │   Obsidian sync     │                       │                      │
 │   pending."         │                       │                      │
 │<────────────────────│                       │                      │
```

### 3.2 MCP Failure Flow

```
ORCHESTRATOR                         MCP CLIENT                    MCP SERVER
     │                                     │                            │
     │  mcp.get_capture_metadata("3")      │                            │
     │────────────────────────────────────>│                            │
     │                                     │  JSON-RPC request          │
     │                                     │───────────────────────────>│
     │                                     │                            │
     │                                     │  (timeout / broken pipe)   │
     │                                     │<─────── NO RESPONSE ───────│
     │                                     │                            │
     │  MCPServerUnavailableError          │                            │
     │<────────────────────────────────────│                            │
     │                                     │                            │
     │  Log warning: "MCP unavailable,      │                            │
     │  proceeding with fallback context."  │                            │
     │                                     │                            │
     │  classifier.classify(text,           │                            │
     │    mcp_context=None)  ← fallback     │                            │
     │  → ClassificationResult              │                            │
     │  (still works, reduced confidence    │                            │
     │   on domain/template suggestions)    │                            │
     │                                     │                            │
     │  knowledge_curator.draft(            │                            │
     │    capture, classification,          │                            │
     │    mcp_context=None)  ← fallback     │                            │
     │  → DraftNote                         │                            │
     │  (no cross-links, no working-state   │                            │
     │   awareness, but valid draft)        │                            │
     │                                     │                            │
     │  qa_verifier.validate()              │                            │
     │  → QAResult (uses built-in templates)│                            │
     │                                     │                            │
     │  import_planner.plan()               │                            │
     │  → ProposalPacket                    │                            │
     │  (default destination: Inbox)        │                            │
     │                                     │                            │
     │  stdout: {"proposal_id": "...",      │                            │
     │   "status": "pending_human_review",  │                            │
     │   "mcp_status": "unavailable",       │                            │
     │   "warnings": ["MCP unavailable,     │                            │
     │    reduced context"]}                │                            │
```

## 4. Directory Structure

```
/home/lifeos/40_Services/capture_orchestrator/
├── __init__.py                          # Package marker
├── lifeos_mcp_server.py                 # MCP Server (stdio JSON-RPC, read-only)
├── mcp_client.py                        # MCP Client Helper (subprocess + typed methods)
├── orchestrator.py                      # CLI Orchestrator (propose-knowledge, view-proposal, etc.)
├── proposal_packet.py                   # Proposal data model, lifecycle, storage
├── controlled_importer.py               # Controlled Importer (hash check, path safety, atomic write)
├── agents/
│   ├── __init__.py
│   ├── classifier.py                    # Capture Classifier (deterministic, rule-based)
│   ├── knowledge_curator.py             # Knowledge Curator (draft generation)
│   ├── import_planner.py                # Import Planner (proposal assembly)
│   └── qa_verifier.py                   # QA Verifier (validation)
├── templates/
│   └── builtin_templates.json           # Fallback template definitions (when MCP unavailable)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Shared fixtures (tmp paths, sample captures)
│   ├── test_mcp_server.py               # MCP server unit tests
│   ├── test_mcp_client.py               # MCP client unit tests
│   ├── test_orchestrator.py             # Orchestrator integration tests
│   ├── test_classifier.py               # Classifier unit tests
│   ├── test_knowledge_curator.py         # Knowledge curator unit tests
│   ├── test_import_planner.py           # Import planner unit tests
│   ├── test_qa_verifier.py              # QA verifier unit tests
│   ├── test_proposal_packet.py          # Proposal lifecycle tests
│   ├── test_controlled_importer.py      # Controlled importer tests
│   └── fixtures/
│       ├── sample_captures.json         # Test capture data
│       ├── sample_templates.json        # Test template catalog
│       └── sample_drafts/               # Draft fixtures for importer tests
└── README.md                            # Module README
```

## 5. Failure Mode Catalog

### 5.1 MCP Server Failures

| Failure | Orchestrator Behavior | User-Facing Behavior |
|---------|----------------------|---------------------|
| Server won't start (script missing) | Log warning, proceed with mcp_context=None | Proposal generated with "reduced context" warning |
| Server crashes mid-call | Retry once, then fallback to None context | Proposal generated with "reduced context" warning |
| Tool returns error (e.g., capture not found) | Propagate error to capture resolution layer | "Capture not found" error card |
| Tool times out (>10s) | Abort that tool call, proceed with None for that context piece | Proposal with partial context |
| Server returns malformed JSON | Log error, fallback to None | Proposal with warning |
| Path access denied by server | Treat as "resource not found" | Same as capture not found |

### 5.2 Classifier Failures

| Failure | Behavior | User-Facing |
|---------|----------|-------------|
| Empty capture text | ClassificationResult with type="unknown", confidence=0.0 | Proposal blocked: "Content too short" |
| Text is all URLs with no description | type="link", route="reference" | Normal proposal |
| Text contains only non-text (binary, base64) | type="unknown", confidence=0.0, flags=["non_text"] | Proposal blocked |
| Very long text (>100KB) | Process first 10KB for classification, flag rest | Proposal with "partial analysis" warning |

### 5.3 Knowledge Curator Failures

| Failure | Behavior | User-Facing |
|---------|----------|-------------|
| Cannot extract title | Use "Untitled Capture" | Proposal with "Untitled" title (human should rename) |
| Source text too thin for definition | Mark section as "[No information in source material.]" | QA may flag as low quality |
| Domain inference fails | Default to "general" | Proposal with domain="general" |
| Cannot suggest any cross-links | Skip LifeOS Relationships section | QA notes missing relationships |

### 5.4 QA Verifier Failures

| Failure (BLOCKING) | Exit Code | User-Facing |
|-------------------|-----------|-------------|
| Secret detected in content | 4 | "QA blocked: potential sensitive information detected" |
| Missing required template sections | 4 | "QA blocked: incomplete template" |
| Malformed YAML frontmatter | 4 | "QA blocked: metadata error" |
| Missing source trail | 4 | "QA blocked: missing source attribution" |

| Failure (NON-BLOCKING) | Warning in Proposal | User-Facing |
|------------------------|-------------------|-------------|
| Thin content | "Content quality: low" | Warning card in proposal |
| Unverifiable links | "1 unverifiable link" | Warning in QA section |
| High link count | "Graph clutter: 18 links" | Warning in QA section |

### 5.5 Import Planner Failures

| Failure | Behavior | User-Facing |
|---------|----------|-------------|
| Cannot determine destination folder | Default to "01_INBOX/Captures/" | Proposal shows Inbox destination |
| Destination path too long | Truncate filename, preserve extension | Normal proposal |
| Template catalog unavailable | Use built-in fallback templates | Proposal with "fallback template" note |

### 5.6 Controlled Importer Failures

| Failure | Exit Code | Behavior | User-Facing |
|---------|-----------|----------|-------------|
| Content hash mismatch | 5 | Abort import, log event, preserve buffer artifacts | "Import blocked: content mismatch. Regenerate proposal." |
| Path traversal detected | 6 | Abort import, log security event, quarantine manifest | "Import blocked: path safety violation." |
| Destination in deny list | 6 | Abort import, log security event | "Import blocked: path safety violation." |
| Destination file already exists | 7 | Abort, log conflict, suggest resolution | "Import blocked: file already exists at destination." |
| Disk full during write | 8 | Abort, clean up .tmp files, log error | "Import failed: disk space."
| Permission denied on vault | 8 | Abort, log error | "Import failed: system error." |
| Event log append fails | Import proceeds, event logged to buffer vault fallback | Import succeeds but "Event log write failed" warning |

### 5.7 General Orchestrator Failures

| Failure | Exit Code | User-Facing |
|---------|-----------|-------------|
| Capture not found | 1 | "Could not find that capture. Check the index with /p." |
| Proposal generation failed (agent exception) | 2 | "Could not generate a proposal. The content may be too short or unclear." |
| MCP unavailable (non-blocking) | 0 + warning | "MCP unavailable. Proposal with reduced context. Review carefully." |
| Invalid proposal ID format | 1 | "Invalid proposal ID." |
| Proposal not in correct state for operation | 2 | "This proposal cannot be approved/rejected in its current state." |
| Revision generation failed | 2 | "Could not revise the proposal. Try again or reject." |

## 6. Testability

### 6.1 Per-Module Testability

| Module | Test Isolation | Key Test Categories |
|--------|---------------|-------------------|
| MCP Server | Mock filesystem. No subprocess needed for tool logic. | Tool schema validation, path allowlist enforcement, error formatting, read-only enforcement |
| MCP Client | Mock subprocess (capture stdin/stdout). | JSON-RPC framing, response parsing, timeout handling, typed result coercion, server death detection |
| Classifier | Pure function. Text in, ClassificationResult out. | Type detection accuracy (URL, idea, task, project, note), edge cases (empty, binary, very long), confidence thresholds |
| Knowledge Curator | Pure function. Dict in, DraftNote out. | Section population, title extraction, frontmatter generation, "no info" placeholder, keyword extraction |
| QA Verifier | Pure function. Draft in, QAResult out. | Secret detection regex, template compliance, blocking vs non-blocking, false positive rate |
| Import Planner | Pure function. Agent outputs in, ProposalPacket + Manifest out. | Destination path generation, manifest schema, risk collection, checklist generation |
| Controlled Importer | Temp directory as vault. Real filesystem ops. | Path traversal attempts, hash validation, atomic write, conflict detection, deny list enforcement, rollback |
| Orchestrator | Integration. Mock MCP client, real agents. | End-to-end pipeline, MCP fallback, error propagation, exit codes, proposal file output |
| Proposal Packet | Pure functions + temp files. | ID generation format, state transitions, save/load round-trip, list/filter |

### 6.2 Test Fixture Strategy

```python
# conftest.py shared fixtures

@pytest.fixture
def tmp_buffer_vault(tmp_path):
    """Create a minimal buffer vault structure."""
    ...

@pytest.fixture
def tmp_canonical_vault(tmp_path):
    """Create a minimal canonical vault structure."""
    ...

@pytest.fixture
def sample_capture():
    """Return a dict representing a typical capture."""
    return {
        "capture_id": "cap_20260708_123456_abc123",
        "content": "Check out this article: https://example.com/container-security",
        "source_type": "telegram",
        "created_at": "2026-07-08T12:34:00Z",
        "status": "pending_review",
        "index": 1,
    }

@pytest.fixture
def sample_classification():
    """Return a typical ClassificationResult."""
    ...

@pytest.fixture
def sample_draft():
    """Return a typical DraftNote."""
    ...

@pytest.fixture
def mock_mcp_client(mocker):
    """Return a mock LifeOSMCPClient with configurable return values."""
    ...
```

## 7. Implementation Sequencing

### V0 (SAFEST — this design)
1. `proposal_packet.py` — data model + lifecycle (no dependencies)
2. `agents/classifier.py` — deterministic classification (no dependencies)
3. `agents/knowledge_curator.py` — draft generation (depends on classifier)
4. `agents/qa_verifier.py` — validation (depends on DraftNote model)
5. `agents/import_planner.py` — assembly (depends on all above)
6. `builtin_templates.json` — fallback templates (no dependencies)
7. `lifeos_mcp_server.py` — read-only MCP server (no dependencies)
8. `mcp_client.py` — typed client (depends on MCP server path)
9. `controlled_importer.py` — safe vault writer (no dependencies)
10. `orchestrator.py` — CLI pipeline (depends on all above)
11. `tests/` — parallel with each module (TDD)

### V0 → Telegram Integration
12. Update `telegram_capture_bot.py`: add `/kt` command, update button handlers
13. Update `message_cards.py`: add KT proposal card format
14. Integration tests: Telegram bot + orchestrator CLI

### Post-V0 (explicitly deferred)
- AI/LLM-enhanced classification (current deterministic classifier is V0)
- AI/LLM-enhanced content curation (current knowledge_curator is template-based)
- Vector similarity for duplicate detection
- Batch proposal generation
- Auto-approve for low-risk captures
- Dashboard-based review (beyond Telegram)

## 8. ADR: Architecture Decisions

### ADR-001: MCP Server is Read-Only, Stateless, and Non-Essential

**Status**: Proposed

**Context**: The MCP server provides context enrichment for the orchestrator. Some MCP tools read from the canonical vault (templates, working state). The orchestrator must not depend on MCP for correctness — only for quality enhancement.

**Decision**: The MCP server is an optional enrichment layer. Every tool has a deterministic fallback. The orchestrator treats MCP unavailability as a warning, not a failure. MCP tools are strictly read-only with a path allowlist enforced inside the server.

**Consequences**:
- Easier: Safe to run MCP server with minimal permissions. Safe to restart/stop without breaking the pipeline. Safe to grant read access to templates without risking vault content.
- Harder: Proposal quality degrades without MCP (fewer cross-links, less domain awareness, default destinations). Operator must review more carefully when MCP is unavailable.

### ADR-002: Specialist Agents are Deterministic Python, Not AI/LLM

**Status**: Proposed

**Context**: The four specialist agents (classifier, knowledge_curator, import_planner, qa_verifier) could be implemented as AI/LLM calls or as deterministic Python code.

**Decision**: V0 agents are deterministic Python modules. No AI/LLM calls. Classification uses regex and heuristics. Curation uses template-based extraction. QA uses pattern matching.

**Consequences**:
- Easier: Predictable, testable, fast, no API costs, no model dependencies, no prompt injection risks.
- Harder: Lower quality drafts than AI-generated ones. Less sophisticated classification. No semantic understanding. Operator review burden is higher.
- Future: AI-enhanced agents are the obvious V1 upgrade path, but the deterministic pipeline is the safety baseline that AI proposals can be compared against.

### ADR-003: Telegram Calls Orchestrator CLI via Subprocess, Not Library Import

**Status**: Proposed

**Context**: The Telegram bot and orchestrator could communicate via Python import, HTTP API, or subprocess CLI.

**Decision**: Telegram bot calls orchestrator as a subprocess CLI. `subprocess.run(["python", "orchestrator.py", "propose-knowledge", target])`. Communication is stdout JSON + exit codes.

**Consequences**:
- Easier: Process isolation (orchestrator crash doesn't crash the bot). Language-agnostic (future n8n can call the same CLI). Simple error handling via exit codes. Easy to test independently.
- Harder: Subprocess overhead per command. JSON parsing required on both sides. No shared in-memory state (but this is desired — orchestrator is stateless per command).

### ADR-004: Proposal Packets are JSON + Markdown, Stored in Buffer Vault

**Status**: Proposed

**Context**: Proposal packets need to be stored for review, revision, and audit. They could be in the event log, in a database, or as files.

**Decision**: Each proposal is stored as two files in `LifeOS_Capture_Buffer/03_Review_Packets/proposals/`:
- `{proposal_id}.json` — machine-readable complete packet
- `{proposal_id}.md` — human-readable review document

**Consequences**:
- Easier: Git-diffable (both JSON and Markdown). Human-readable without tools. Self-contained (all context in the files). Simple lifecycle management (file rename/move on status change).
- Harder: No query capability (must list directory and parse files). No concurrent access protection (but single-user system makes this acceptable). File-based state machine requires careful atomic writes.

### ADR-005: Controlled Importer is the Sole Vault Writer

**Status**: Proposed

**Context**: Multiple components could write to the canonical vault (orchestrator, agents, Telegram bot, MCP tools, n8n workflows). The safety invariant requires a single writing module.

**Decision**: Only `controlled_importer.py` may write to `/home/lifeos/10_Vaults/LifeOS/`. It is called exclusively by the orchestrator after explicit human approval. All other modules (MCP, agents, Telegram bot, n8n) have zero write access to the canonical vault path.

**Consequences**:
- Easier: Single audit point for all vault mutations. Single enforcement point for hash validation, path safety, and deny lists. Easy to add pre-import hooks (backup, notification). Easy to disable all imports by renaming one module.
- Harder: Every import must go through the importer — no shortcuts. Import manifest format is a coupling point. Import failure recovery is all-or-nothing (atomicity constraint).

## 9. Summary of Safety Guarantees

| Guarantee | Enforced By | Verified By |
|-----------|------------|-------------|
| MCP tools are read-only | Path allowlist + mode='r' gate inside MCP server | Unit tests for all read paths, test asserting write raises error |
| MCP server has no write access | Docker/process permissions + internal gate | Integration test attempting write through MCP |
| Telegram never calls MCP directly | Telegram bot only calls orchestrator CLI (fixed commands) | Code review: no MCP import in telegram_capture_bot.py |
| Agents never write to canonical vault | Agents only produce in-memory objects; importer is sole writer | Code review: no vault paths in agent modules |
| Importer validates content hash | sha256 comparison before write | Unit tests with tampered content |
| Importer blocks path traversal | os.path.realpath() + prefix check + deny list | Unit tests with "../" attacks, symlink attacks |
| No traceback exposure to Telegram | Exit code → user-friendly message mapping | Unit tests for all exit codes |
| Proposals are buffer-only | Proposal path is outside canonical vault | Path assertion in proposal_packet.py |
| MCP failure is non-blocking | Try/except with fallback to None context | Integration test with MCP server killed |
| Proposal state transitions are validated | TRANSITIONS dict + update_status() gate | Unit tests for all valid/invalid transitions |
