"""
Deterministic Capture Classifier — V0 (no AI/LLM).

This module provides pure-function classification of capture text into
one of several predefined categories using rule-based heuristics only.
No external API calls. No machine learning. No state.

V0 classification is the first step in the capture review pipeline.
Only captures classified as "knowledge" are importable in V0.
"""

import re
from typing import List, Dict

VALID_CLASSIFICATIONS = [
    "knowledge",
    "idea",
    "project_update",
    "task",
    "reference",
    "source_capture",
    "tool_repo_candidate",
    "unknown",
]

# Technical terms used for knowledge detection (rule 7)
TECHNICAL_TERMS = [
    "docker", "kubernetes", "python", "api", "database",
    "network", "security", "linux", "algorithm", "compiler",
    "protocol", "encryption", "container", "microservice",
    "distributed", "server", "client", "framework", "library",
    "runtime", "deployment", "ci/cd", "pipeline", "observability",
    "monitoring", "scaling", "load balancer", "proxy", "dns",
    "http", "tcp", "udp", "tls", "ssl", "ssh", "git",
    "sql", "nosql", "cache", "message queue", "event driven",
    "architecture", "design pattern", "testing", "debugging",
    "performance", "optimization", "concurrency", "parallelism",
    "machine learning", "neural network", "deep learning", "llm",
    "gpt", "transformer", "embedding", "vector", "semantic",
    "backend", "frontend", "full stack", "devops", "sre",
    "infrastructure", "cloud", "aws", "azure", "gcp",
    "terraform", "ansible", "prometheus", "grafana", "elasticsearch",
    "kafka", "rabbitmq", "redis", "postgresql", "mongodb",
    "graphql", "rest", "grpc", "websocket", "mqtt",
    "firmware", "embedded", "iot", "sensor", "microcontroller",
    "esp32", "arduino", "raspberry", "fpga", "asic",
    "operating system", "kernel", "filesystem", "memory management",
    "scheduler", "virtualization", "hypervisor", "sandbox",
]

# Definitional patterns for knowledge detection (rule 6)
DEFINITIONAL_PATTERNS = [
    r'\bis\s+an?\b',          # "X is a ..."
    r'\bare\b',               # "X are ..."
    r'\bdefined\s+as\b',      # "defined as"
    r'\brefers?\s+to\b',      # "refers to"
    r'\bmeans?\s+that\b',     # "means that"
    r'\bstands?\s+for\b',     # "stands for"
    r'\bconsists?\s+of\b',    # "consists of"
    r'\bis\s+short\s+for\b',  # "is short for"
    r'\bcan\s+be\s+defined\b',# "can be defined"
    r'\bin\s+other\s+words\b',# "in other words"
]

# GitHub repo pattern (rule 2)
GITHUB_REPO_PATTERN = re.compile(
    r'github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+',
    re.IGNORECASE,
)


def classify_capture(text: str, source: str = "unknown") -> dict:
    """Classify a capture text into one of the valid classifications.

    This is a deterministic, rule-based classifier. It uses no AI,
    no LLM, no external API calls, and no machine learning. All
    classification is done via simple pattern matching heuristics.

    Classification rules are evaluated in priority order. The first
    matching rule sets the classification.

    Args:
        text: The raw capture text to classify.
        source: The source channel of the capture (e.g., "telegram").

    Returns:
        A dict with keys:
            classification: str — one of VALID_CLASSIFICATIONS
            confidence: str — "high", "medium", or "low"
            reasons: List[str] — human-readable explanation of the match

    Example:
        >>> result = classify_capture("idea: build a new monitoring dashboard")
        >>> result["classification"]
        'idea'
        >>> result["confidence"]
        'medium'
    """
    if not text or not isinstance(text, str):
        return {
            "classification": "unknown",
            "confidence": "low",
            "reasons": ["Empty or invalid input text"],
        }

    text_stripped = text.strip()
    text_lower = text_stripped.lower()

    # Rule 1: URL detection -> source_capture
    if text_stripped.startswith("http://") or text_stripped.startswith("https://"):
        return {
            "classification": "source_capture",
            "confidence": "medium",
            "reasons": ["Text starts with http:// or https:// — treated as source capture"],
        }

    # Rule 2: GitHub repo pattern -> tool_repo_candidate
    if GITHUB_REPO_PATTERN.search(text_stripped):
        return {
            "classification": "tool_repo_candidate",
            "confidence": "high",
            "reasons": ["Text matches github.com repository URL pattern"],
        }

    # Rule 3: "idea:" prefix or mention -> idea
    if text_lower.startswith("idea:") or re.search(r'\bidea\b', text_lower):
        return {
            "classification": "idea",
            "confidence": "medium",
            "reasons": ["Text starts with 'idea:' or mentions 'idea'"],
        }

    # Rule 4: "task:" or "todo:" prefix -> task
    if text_lower.startswith("task:") or text_lower.startswith("todo:"):
        return {
            "classification": "task",
            "confidence": "high",
            "reasons": ["Text starts with 'task:' or 'todo:'"],
        }

    # Rule 5: Project-related keywords -> project_update
    project_patterns = [
        r'\bproject\b', r'\bprogress\b', r'\bmilestone\b',
        r'\bdeliverable\b', r'\bsprint\b', r'\bdone\b',
        r'\bcompleted\b', r'\bfinished\b', r'\bstatus\s+update\b',
    ]
    for pat in project_patterns:
        if re.search(pat, text_lower):
            return {
                "classification": "project_update",
                "confidence": "medium",
                "reasons": ["Text contains project-related keywords (project, progress, milestone)"],
            }

    # Rule 6: Definitional patterns -> knowledge
    for pat in DEFINITIONAL_PATTERNS:
        if re.search(pat, text_lower):
            return {
                "classification": "knowledge",
                "confidence": "medium",
                "reasons": ["Text contains definitional language pattern"],
            }

    # Rule 7: Technical terms -> knowledge
    for term in TECHNICAL_TERMS:
        if re.search(r'\b' + re.escape(term) + r'\b', text_lower):
            return {
                "classification": "knowledge",
                "confidence": "medium",
                "reasons": [f"Text contains technical term: '{term}'"],
            }

    # Rule 8: "ref:" or "reference:" prefix -> reference
    if text_lower.startswith("ref:") or text_lower.startswith("reference:"):
        return {
            "classification": "reference",
            "confidence": "medium",
            "reasons": ["Text starts with 'ref:' or 'reference:'"],
        }

    # Rule 9: Short text without matches -> unknown
    if len(text_stripped) < 140:
        return {
            "classification": "unknown",
            "confidence": "low",
            "reasons": ["Short text (< 140 chars) with no matching classification patterns"],
        }

    # Rule 10: Default -> knowledge (low confidence)
    return {
        "classification": "knowledge",
        "confidence": "low",
        "reasons": ["Default classification — no specific pattern matched"],
    }


def is_importable(classification: str) -> bool:
    """Check whether a classification is importable into the vault.

    In V0, only "knowledge" classified captures are importable.
    All other classifications require future agent support.

    This is a deterministic function with no AI/LLM involvement.

    Args:
        classification: One of the VALID_CLASSIFICATIONS strings.

    Returns:
        True if the classification is importable in V0, False otherwise.

    Example:
        >>> is_importable("knowledge")
        True
        >>> is_importable("idea")
        False
        >>> is_importable("unknown")
        False
    """
    return classification == "knowledge"
