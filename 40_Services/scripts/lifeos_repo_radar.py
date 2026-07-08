#!/usr/bin/env python3
"""LifeOS Repo Radar — CLI utility for exploring the candidate registry.

Reads a local JSON candidate registry and prints text or JSON summaries.
Supports filtering by risk tier, recommendation, and category.

Stdlib-only. Read-only. No internet, no secrets, no file mutation.
"""

import argparse
import json
import sys
from pathlib import Path

DEFAULT_REGISTRY = Path(__file__).resolve().parent / "lifeos_repo_radar_registry.json"


def load_registry(path):
    with open(path, "r") as f:
        return json.load(f)


def filter_candidates(candidates, risk_tier=None, recommendation=None, category=None):
    result = []
    for c in candidates:
        if risk_tier and risk_tier.upper() not in c["risk_tier"].upper():
            continue
        if recommendation and recommendation.lower() != c["recommendation"].lower():
            continue
        if category and category.lower() != c["category"].lower():
            continue
        result.append(c)
    return result


def format_text_summary(candidates):
    lines = []
    lines.append(f"{'Name':<40} {'Category':<22} {'Risk':<14} {'Rec':<22}")
    lines.append("-" * 101)
    for c in candidates:
        name = c["name"][:38]
        cat = c["category"][:20]
        risk = c["risk_tier"][:12]
        rec = c["recommendation"][:20]
        lines.append(f"{name:<40} {cat:<22} {risk:<14} {rec:<22}")
    lines.append("-" * 101)
    lines.append(f"Total: {len(candidates)} candidate(s)")
    return "\n".join(lines)


def format_text_detail(candidate):
    lines = []
    lines.append(f"Name:               {candidate['name']}")
    lines.append(f"URL:                {candidate['url']}")
    lines.append(f"Category:           {candidate['category']}")
    lines.append(f"Risk Tier:          {candidate['risk_tier']}")
    lines.append(f"Recommendation:     {candidate['recommendation']}")
    lines.append(f"Install Status:     {candidate['install_status']}")
    lines.append(f"Activation Status:  {candidate['activation_status']}")
    lines.append(f"Secrets Required:   {candidate['secrets_required']}")
    lines.append(f"Docker Socket:      {candidate['docker_socket_required']}")
    lines.append(f"Filesystem Access:  {candidate['filesystem_access']}")
    lines.append(f"Network Exposure:   {candidate['network_exposure']}")
    lines.append(f"Browser Automation: {candidate['browser_automation']}")
    lines.append(f"Shell Execution:    {candidate['shell_execution']}")
    lines.append(f"Tests Available:    {candidate['tests_available']}")
    lines.append(f"Recent Maintenance: {candidate['recent_maintenance']}")
    lines.append(f"Clear License:      {candidate['clear_license']}")
    lines.append(f"Read-Only Mode:     {candidate['read_only_mode']}")
    lines.append(f"Sandboxable:        {candidate['sandboxable']}")
    lines.append(f"Clean Removal:      {candidate['clean_removal']}")
    lines.append(f"Why Interesting:    {candidate['why_interesting']}")
    lines.append(f"Proposed Use:       {candidate['proposed_use']}")
    lines.append(f"Reality Check:      {candidate['reality_check_notes']}")
    return "\n".join(lines)


def print_catalog_summary(registry):
    groups = registry.get("catalog_groups", {})
    print("LifeOS MCP Catalog Summary")
    print("===========================")
    for group_name, entries in groups.items():
        label = group_name.replace("_", " ").title()
        print(f"\n{label}:")
        for entry in entries:
            print(f"  - {entry}")
    print(f"\nGroups: {len(groups)}")
    print(f"Candidates in radar: {len(registry.get('candidates', []))}")


def main():
    parser = argparse.ArgumentParser(
        description="LifeOS Repo Radar — candidate registry explorer"
    )
    parser.add_argument(
        "--registry",
        type=str,
        default=str(DEFAULT_REGISTRY),
        help="Path to candidate registry JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output as JSON instead of text",
    )
    parser.add_argument(
        "--risk-tier",
        type=str,
        default=None,
        help="Filter by risk tier (e.g. A0, A3, A5-critical)",
    )
    parser.add_argument(
        "--recommendation",
        type=str,
        default=None,
        help="Filter by recommendation (sandbox, defer, reject, reclassify, discovery_reference)",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Filter by category (mcp-server, proxy, agent-platform, etc.)",
    )
    parser.add_argument(
        "--detail",
        type=str,
        default=None,
        help="Show detailed view for candidate matching this substring (case-insensitive)",
    )
    parser.add_argument(
        "--catalog",
        action="store_true",
        help="Print catalog group summary instead of candidate list",
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List available categories",
    )
    parser.add_argument(
        "--list-recommendations",
        action="store_true",
        help="List available recommendation values",
    )
    parser.add_argument(
        "--list-risk-tiers",
        action="store_true",
        help="List available risk tiers",
    )

    args = parser.parse_args()

    try:
        registry = load_registry(args.registry)
    except FileNotFoundError:
        print(f"Registry not found: {args.registry}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in registry: {e}", file=sys.stderr)
        sys.exit(1)

    candidates = registry.get("candidates", [])

    if args.catalog:
        print_catalog_summary(registry)
        return

    if args.list_categories:
        cats = sorted(set(c["category"] for c in candidates))
        print("\n".join(cats))
        return

    if args.list_recommendations:
        recs = sorted(set(c["recommendation"] for c in candidates))
        print("\n".join(recs))
        return

    if args.list_risk_tiers:
        tiers = sorted(set(c["risk_tier"] for c in candidates))
        print("\n".join(tiers))
        return

    filtered = filter_candidates(
        candidates,
        risk_tier=args.risk_tier,
        recommendation=args.recommendation,
        category=args.category,
    )

    if args.detail:
        detail_candidates = [
            c for c in filtered if args.detail.lower() in c["name"].lower()
        ]
        if not detail_candidates:
            print(f"No candidate matching '{args.detail}'", file=sys.stderr)
            sys.exit(1)
        for c in detail_candidates:
            print(format_text_detail(c))
            print()
        return

    if args.json_output:
        output = {"candidates": filtered, "count": len(filtered)}
        meta = registry.get("meta", {})
        if meta:
            output["meta"] = {
                "version": meta.get("version"),
                "registry_path": args.registry,
            }
        print(json.dumps(output, indent=2))
    else:
        print(format_text_summary(filtered))


if __name__ == "__main__":
    main()
