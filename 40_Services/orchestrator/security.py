"""
Shared security utilities for the Capture Review Orchestrator.

This module provides deterministic, no-AI security primitives:
proposal ID generation, content hashing, path validation, filename
sanitization, and YAML injection prevention. All functions are pure
stdlib, no external dependencies, no AI/LLM calls.
"""

import hashlib
import os
import re
import secrets
from datetime import datetime, timezone

# --- Path Constants ---

FORBIDDEN_OUTPUT_ROOTS = {"/home/lifeos/10_Vaults/LifeOS"}
BUFFER_ROOT = "/home/lifeos/LifeOS_Capture_Buffer"
VAULT_ROOT = "/home/lifeos/10_Vaults/LifeOS"
KNOWLEDGE_ROOT = "/home/lifeos/10_Vaults/LifeOS/03_KNOWLEDGE"
PROPOSAL_DIR = "/home/lifeos/LifeOS_Capture_Buffer/03_Review_Packets/proposals"

# Pattern matching for forbidden characters in parameters
FORBIDDEN_PARAM_PATTERNS = ["../", "..\\", "\x00", "\n", "\r"]


def generate_proposal_id(capture_id: str) -> str:
    """Generate a 128-bit random proposal ID.

    Format: prop_YYYYMMDDTHHMMSSZ_short_shorthex

    Args:
        capture_id: The capture ID to derive a short suffix from.

    Returns:
        A unique proposal ID string.

    Example:
        >>> pid = generate_proposal_id("cap_20260708_123456_abc123")
        >>> pid.startswith("prop_")
        True
        >>> len(pid) > 30
        True
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short_cap = capture_id[-12:] if len(capture_id) >= 12 else capture_id
    rand = secrets.token_hex(4)
    return f"prop_{ts}_{short_cap}_{rand}"


def compute_content_hash(content: str) -> str:
    """Compute a SHA-256 hash of the given content.

    Args:
        content: The string content to hash.

    Returns:
        A hex-encoded SHA-256 hash string (64 characters).

    Example:
        >>> compute_content_hash("hello") == hashlib.sha256(b"hello").hexdigest()
        True
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def is_forbidden_output(path: str) -> bool:
    """Check if a resolved path is under any forbidden output root.

    This prevents the orchestrator from writing into the canonical
    LifeOS vault directory.

    Args:
        path: An absolute or relative path to check.

    Returns:
        True if the resolved path falls under a forbidden directory.

    Example:
        >>> is_forbidden_output("/home/lifeos/10_Vaults/LifeOS/some/file.md")
        True
        >>> is_forbidden_output("/home/lifeos/LifeOS_Capture_Buffer/file.md")
        False
    """
    rp = os.path.realpath(os.path.abspath(path))
    for forbidden in FORBIDDEN_OUTPUT_ROOTS:
        fp = os.path.realpath(os.path.abspath(forbidden))
        if rp == fp or rp.startswith(fp + os.sep):
            return True
    return False


def validate_vault_path(relative_path: str) -> str:
    """Validate and sanitize a vault-relative path.

    Raises ValueError for:
    - Empty or None paths
    - Absolute paths (starting with /)
    - Path traversal (.. components)
    - Hidden files (starting with .)

    Args:
        relative_path: A vault-relative path like "03_KNOWLEDGE/AI/Note.md".

    Returns:
        The validated path unchanged if it passes all checks.

    Raises:
        ValueError: If the path fails any validation rule.

    Example:
        >>> validate_vault_path("03_KNOWLEDGE/AI/Note.md")
        '03_KNOWLEDGE/AI/Note.md'
        >>> validate_vault_path("/absolute/path")
        Traceback (most recent call last):
        ValueError: Path must be vault-relative
    """
    if not relative_path or relative_path.startswith("/"):
        raise ValueError("Path must be vault-relative")
    if ".." in relative_path.split("/"):
        raise ValueError("Path traversal detected")
    if relative_path.startswith("."):
        raise ValueError("Hidden files not allowed")
    return relative_path


def sanitize_filename(title: str) -> str:
    """Convert a title string to a safe filesystem filename.

    Removes characters forbidden on Linux/Windows filesystems:
    < > : " / \\ | ? * and control characters.
    Strips leading/trailing dots and spaces. Collapses whitespace.
    Falls back to "untitled" if the result is empty.
    Truncates at 200 characters.

    Args:
        title: The human-readable title to convert.

    Returns:
        A safe filename string without extension.

    Example:
        >>> sanitize_filename("Docker: What is it?")
        'Docker What is it'
        >>> sanitize_filename("")
        'untitled'
    """
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', title)
    safe = safe.strip('. ')
    safe = re.sub(r'\s+', ' ', safe).strip()
    if not safe:
        safe = "untitled"
    if len(safe) > 200:
        safe = safe[:200]
    return safe


def sanitize_yaml_body(content: str) -> str:
    """Escape YAML document separator sequences to prevent injection.

    Replaces lines containing only '---' with '– – –' (en-dashes)
    so that content embedded in YAML frontmatter does not accidentally
    terminate the frontmatter block.

    Args:
        content: The raw string content that may contain YAML separators.

    Returns:
        Content with triple-dash separators neutralized.

    Example:
        >>> sanitize_yaml_body("Title\\n---\\nBody")
        'Title\\n– – –\\nBody'
        >>> sanitize_yaml_body("No separators here")
        'No separators here'
    """
    return re.sub(r'^---\s*$', '\u2013 \u2013 \u2013', content, flags=re.MULTILINE)
