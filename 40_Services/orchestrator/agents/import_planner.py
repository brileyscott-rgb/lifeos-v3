"""
Deterministic Import Planner — V0 (no AI/LLM).

This module proposes a vault-relative destination path under the
Knowledge root for a given capture. It uses keyword matching against
predefined category mappings to select the most appropriate Knowledge
subdirectory. All decisions are deterministic — no AI/LLM calls.

Paths are validated and filenames sanitized using the shared security
module before being returned.
"""

try:
    from ..security import sanitize_filename, validate_vault_path
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from security import sanitize_filename, validate_vault_path

# Knowledge categories mapped to their keyword triggers.
# Categories are ordered by specificity — more specific categories
# are checked first to avoid false matches on generic terms.
KNOWLEDGE_CATEGORIES = {
    "AI": [
        "ai", "machine learning", "llm", "gpt", "neural",
        "deep learning", "transformer", "nlp", "artificial intelligence",
        "model", "training", "inference", "prompt", "embedding",
        "fine-tuning", "rag", "generative", "diffusion", "chatgpt",
        "copilot", "openai", "anthropic", "claude", "gemini",
    ],
    "Software": [
        "software", "code", "programming", "app", "algorithm",
        "web", "api", "framework", "library", "language",
        "compiler", "interpreter", "debugging", "refactoring",
        "testing", "tdd", "ci/cd", "git", "version control",
        "dependency", "package", "module", "script", "sdk",
        "javascript", "typescript", "rust", "go", "java",
        "c++", "ruby", "php", "swift", "kotlin",
    ],
    "Systems": [
        "system", "os", "linux", "docker", "kubernetes",
        "container", "server", "virtualization", "hypervisor",
        "kernel", "process", "scheduler", "filesystem", "boot",
        "distribution", "ubuntu", "debian", "fedora", "arch",
        "systemd", "service", "daemon", "cron", "init",
        "ansible", "terraform", "infrastructure as code",
    ],
    "Networking": [
        "network", "tcp", "http", "dns", "proxy", "firewall",
        "ip", "subnet", "routing", "switch", "router",
        "vpn", "gateway", "nat", "dhcp", "ethernet",
        "wifi", "bluetooth", "zigbee", "mesh", "tunnel",
        "load balancer", "latency", "bandwidth", "throughputs",
    ],
    "Hardware": [
        "hardware", "cpu", "gpu", "memory", "device", "sensor",
        "microcontroller", "esp32", "arduino", "raspberry pi",
        "fpga", "asic", "soc", "pcb", "circuit",
        "embedded", "firmware", "iot", "actuator", "motor",
        "power", "battery", "voltage", "current", "bus",
    ],
    "LifeOS": [
        "lifeos", "vault", "capture", "mcp", "orchestrat",
        "agent", "pipeline", "buffer", "chatops", "telegram bot",
        "n8n", "monitoring", "observability", "semantic",
        "approval tier", "backup", "migration", "sync",
    ],
    "Reference": [],
}


def plan_import_path(title: str, capture_text: str) -> str:
    """Propose a vault-relative path under the Knowledge root.

    Scores each knowledge category by keyword match count in the
    capture text. Picks the highest-scoring category. Falls back
    to "03_KNOWLEDGE/Reference/" if no keywords match.

    The filename is sanitized via the security module. The returned
    path is always vault-relative and safe for use in vault operations.

    This is a fully deterministic function — no AI/LLM calls.

    Args:
        title: The proposed note title (used for the filename).
        capture_text: The raw capture text for category matching.

    Returns:
        A vault-relative path like:
        "03_KNOWLEDGE/AI/Some_Title.md"

        Never returns absolute paths or paths containing "../".

    Example:
        >>> plan_import_path("What is Docker", "Docker is a container runtime")
        '03_KNOWLEDGE/Systems/What_is_Docker.md'
        >>> plan_import_path("Cool thought", "no matching keywords here")
        '03_KNOWLEDGE/Reference/Cool_thought.md'
    """
    text_lower = capture_text.lower() if capture_text else ""

    # Score each category by keyword match count
    scores = {}
    for category, keywords in KNOWLEDGE_CATEGORIES.items():
        score = 0
        for kw in keywords:
            count = text_lower.count(kw.lower())
            if count > 0:
                # Longer keywords get more weight to prefer specificity
                score += count * len(kw)
        scores[category] = score

    # Pick highest-scoring category; fallback to Reference
    best_category = "Reference"
    best_score = 0
    for category, score in scores.items():
        if score > best_score:
            best_score = score
            best_category = category

    # Sanitize the title into a safe filename with .md extension
    safe_name = sanitize_filename(title)
    filename = safe_name + ".md"

    # Build the vault-relative path
    relative_path = f"03_KNOWLEDGE/{best_category}/{filename}"

    # Validate (raises ValueError on path traversal or other issues)
    validate_vault_path(relative_path)

    return relative_path
