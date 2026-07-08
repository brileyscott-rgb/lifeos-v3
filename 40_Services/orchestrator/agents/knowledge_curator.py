"""
Deterministic Knowledge Curator — V0 (no AI/LLM).

This module builds a proposed Knowledge note from capture content using
deterministic text extraction and template assembly only. No external
API calls. No machine learning. No AI/LLM.

The curator extracts definitional sentences, technical terms, and
structural elements from raw capture text, then assembles them into
a standardized Knowledge note format with YAML frontmatter.

V0 output requires human review before any vault import.
"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

try:
    from ..security import sanitize_filename, sanitize_yaml_body
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from security import sanitize_filename, sanitize_yaml_body

# Patterns for extracting definitional sentences
DEFINITIONAL_SENTENCE_PATTERNS = [
    r'[^.!?]*(?:\bis\s+an?\b)[^.!?]*[.!?]',
    r'[^.!?]*(?:\brefers?\s+to\b)[^.!?]*[.!?]',
    r'[^.!?]*(?:\bdefined\s+as\b)[^.!?]*[.!?]',
    r'[^.!?]*(?:\bmeans?\s+that\b)[^.!?]*[.!?]',
    r'[^.!?]*(?:\bstands?\s+for\b)[^.!?]*[.!?]',
]

# Technical term patterns for key detail extraction
TECHNICAL_TERMS = [
    "docker", "kubernetes", "python", "api", "database",
    "network", "security", "linux", "algorithm", "compiler",
    "protocol", "encryption", "container", "microservice",
    "distributed", "server", "client", "framework", "library",
    "runtime", "deployment", "ci/cd", "pipeline", "observability",
    "architecture", "design pattern", "testing", "debugging",
    "performance", "optimization", "concurrency", "parallelism",
    "machine learning", "neural network", "deep learning", "llm",
    "gpt", "transformer", "embedding", "vector", "semantic",
    "backend", "frontend", "full stack", "devops", "sre",
    "infrastructure", "cloud", "aws", "azure", "gcp",
    "terraform", "ansible", "prometheus", "grafana",
    "kafka", "rabbitmq", "redis", "postgresql", "mongodb",
    "graphql", "rest", "grpc", "websocket", "mqtt",
    "firmware", "embedded", "iot", "sensor", "microcontroller",
    "operating system", "kernel", "filesystem", "memory",
    "scheduler", "virtualization", "hypervisor", "sandbox",
    "data structure", "binary", "tree", "graph", "hash",
    "sorting", "search", "complexity", "big o", "recursion",
    "functional", "object oriented", "procedural", "declarative",
]


def _extract_sentences(text: str) -> List[str]:
    """Split text into rough sentences without external NLP."""
    if not text:
        return []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def _extract_definitional(paragraphs: List[str]) -> str:
    """Extract sentences containing definitional language patterns."""
    found = []
    for para in paragraphs:
        for pat in DEFINITIONAL_SENTENCE_PATTERNS:
            matches = re.findall(pat, para, re.IGNORECASE)
            for m in matches:
                cleaned = m.strip().rstrip('.!?')
                if cleaned and len(cleaned) > 10:
                    found.append(cleaned)
    if not found:
        return "No definitional sentences identified in the capture text."
    return " ".join(dict.fromkeys(found))  # deduplicate preserving order


def _extract_key_details(paragraphs: List[str]) -> str:
    """Extract sentences containing technical terms or bullet-like structures."""
    details = []
    for para in paragraphs:
        for term in TECHNICAL_TERMS:
            if re.search(r'\b' + re.escape(term) + r'\b', para, re.IGNORECASE):
                sentence_match = re.search(
                    r'[^.!?\n]*\b' + re.escape(term) + r'\b[^.!?\n]*[.!?\n]?',
                    para, re.IGNORECASE,
                )
                if sentence_match:
                    cleaned = sentence_match.group(0).strip().rstrip('.!?')
                    if cleaned and len(cleaned) > 10:
                        details.append(cleaned)
                        break
    if not details:
        lines = [l.strip() for l in '\n'.join(paragraphs).splitlines()
                 if l.strip().startswith(('-', '*', '+', '1.', '2.'))]
        if lines:
            return '\n'.join(lines[:10])
        return "No specific technical details extracted."
    return '\n'.join(dict.fromkeys(details[:8]))


def _extract_related_concepts(paragraphs: List[str]) -> str:
    """Extract capitalized phrases and technical terms as concepts."""
    concepts = set()
    full_text = ' '.join(paragraphs)

    # Capitalized multi-word phrases
    capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', full_text)
    for c in capitalized:
        if len(c) > 3 and c.lower() not in {'the', 'and', 'for', 'with', 'this'}:
            concepts.add(c)

    # Technical terms found in text
    for term in TECHNICAL_TERMS:
        if re.search(r'\b' + re.escape(term) + r'\b', full_text, re.IGNORECASE):
            concepts.add(term.title())

    if not concepts:
        return "No specific related concepts identified."
    return ', '.join(sorted(concepts)[:20])


def curate_knowledge(
    capture_text: str,
    capture_metadata: dict,
    template_catalog: list = None,
    working_state_summary: str = None,
) -> dict:
    """Build a proposed Knowledge note from capture content.

    This is a deterministic V0 Knowledge curator module. No AI/LLM
    was used. All extraction is done via regex pattern matching and
    simple heuristics. Human review is required before import.

    Args:
        capture_text: The raw capture text content.
        capture_metadata: Dict with capture_id, source, created_at, etc.
        template_catalog: Optional list of template names (unused in V0).
        working_state_summary: Optional summary of current LifeOS state.

    Returns:
        A dict with:
            title: str — proposed note title
            yaml_frontmatter: dict — metadata for the note
            body_sections: dict — structured content sections

    Example:
        >>> result = curate_knowledge(
        ...     "Kubernetes is a container orchestration platform. It manages deployments.",
        ...     {"capture_id": "cap_test_123", "source": "telegram"},
        ... )
        >>> result["title"]
        'Kubernetes is a container orchestration platform'
    """
    if not capture_text or not isinstance(capture_text, str):
        capture_text = ""
    if not isinstance(capture_metadata, dict):
        capture_metadata = {}

    lines = capture_text.strip().splitlines()
    first_line = lines[0].strip() if lines else ""

    # Title: first line (cleaned) or first 80 chars
    title = sanitize_filename(first_line[:80] if first_line else "Untitled Capture")
    if not title.strip() or title.strip().lower() == "untitled":
        if len(capture_text.strip()) > 0:
            title = sanitize_filename(capture_text.strip()[:80])
        else:
            title = "Untitled Capture"

    # Summary: first 200 chars
    summary = capture_text.strip()[:200]
    if len(capture_text.strip()) > 200:
        summary += "..."

    # Paragraphs for extraction
    paragraphs = [p.strip() for p in capture_text.split('\n') if p.strip()]

    # Extract definitional context
    definition_context = _extract_definitional(paragraphs)

    # Extract key details
    key_details = _extract_key_details(paragraphs)

    # Why it matters (generic V0 message)
    why_it_matters = (
        "This capture was classified as knowledge worth preserving "
        "in the LifeOS vault. It contains educational or definitional "
        "content that may contribute to the knowledge graph."
    )

    # How it connects
    if working_state_summary:
        how_it_connects = (
            f"Based on the current LifeOS working state: {working_state_summary}\n\n"
            "This knowledge may relate to active LifeOS domains. "
            "Review the proposed vault path for proper placement."
        )
    else:
        how_it_connects = (
            "No working state summary was available during curation. "
            "Review the proposed vault path for alignment with existing "
            "LifeOS knowledge domains."
        )

    # Source trail
    source_entries = []
    if capture_metadata.get("capture_id"):
        source_entries.append(f"- Capture ID: {capture_metadata['capture_id']}")
    if capture_metadata.get("source"):
        source_entries.append(f"- Source: {capture_metadata['source']}")
    if capture_metadata.get("created_at"):
        source_entries.append(f"- Captured: {capture_metadata['created_at']}")
    if capture_metadata.get("source_url"):
        source_entries.append(f"- Source URL: {capture_metadata['source_url']}")
    source_trail = '\n'.join(source_entries) if source_entries else "No source metadata available."

    # Related concepts
    related_concepts = _extract_related_concepts(paragraphs)

    # Review notes
    review_notes = (
        "This is a deterministic V0 Knowledge curator module. "
        "No AI/LLM was used to generate this content. All sections "
        "were produced by regex pattern matching and heuristic text "
        "extraction. Human review is required before any vault import."
    )

    # YAML frontmatter
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    capture_id = capture_metadata.get("capture_id", "unknown")
    tags = ["knowledge"]
    if capture_metadata.get("classification"):
        tags.append(capture_metadata["classification"])

    yaml_frontmatter = {
        "type": "knowledge",
        "status": "draft",
        "domain": "knowledge",
        "created": now_ts,
        "source_refs": [capture_id],
        "tags": tags,
        "approval_required": True,
    }

    body_sections = {
        "summary": summary,
        "definition_context": definition_context,
        "key_details": key_details,
        "why_it_matters": why_it_matters,
        "how_it_connects": how_it_connects,
        "source_trail": source_trail,
        "related_concepts": related_concepts,
        "review_notes": review_notes,
    }

    return {
        "title": title,
        "yaml_frontmatter": yaml_frontmatter,
        "body_sections": body_sections,
    }
