# Metadata Taxonomy Agent

## Purpose

Clean, validate, and enrich YAML frontmatter metadata on all agent-generated draft notes. Assign aliases, tags, domains, cross-links, folder suggestions, and detect duplicates and graph clutter risks before notes enter review.

## Inputs

- Any agent-generated draft note (Knowledge, Project, Idea, Reference, Media)
- Intake classification: `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`
- Existing canonical vault metadata (via search index: existing tags, aliases, folder structure)

## Outputs

- Metadata-enriched draft note (same file, updated in-place):
  `02_Agent_Workspace/{Type}_Drafts/{capture_id}_{type}_draft.md`

The agent adds or validates these frontmatter fields:
```yaml
aliases: []          # Alternative names/titles
tags: []             # Consistent, lowercase, kebab-case where possible
domain: ""           # Primary knowledge domain
status: draft        # Unchanged — always draft at this stage
confidence: machine_generated_unreviewed  # Unchanged
created: ""          # ISO 8601 timestamp
source_capture: ""   # Capture ID
source_url: ""       # If applicable
related_notes: []    # Suggested links to existing notes
folder_suggestion: "" # Suggested canonical vault folder path
duplicate_check:     # Results of duplicate detection
  potential_duplicates: []
  similarity_score: 0.0
  recommendation: "none"  # none | warn | merge | reject
```

## Tag Standards

Tags must follow LifeOS conventions:
- Lowercase
- Kebab-case for multi-word tags (`machine-learning`, not `MachineLearning` or `machine_learning`)
- Domain-scoped where applicable (`devops.ci-cd`, `lifeos.agents`)
- No spaces, no special characters except hyphens and dots
- Maximum 10 tags per note (prevent tag sprawl)
- Prefer existing tags over creating new ones

## Alias Rules

- Include the full title as an alias
- Include common abbreviations or alternative names
- Include acronym expansions where relevant
- Maximum 5 aliases per note
- Aliases should be unique across the vault (warn on collision)

## Folder Suggestion Logic

The agent suggests a canonical vault destination based on:

| Note Type | Primary Folder | Fallback |
|---|---|---|
| Knowledge | `20_Knowledge/{domain}/` | `20_Knowledge/Unfiled/` |
| Project | `30_Projects/{status}/{slug}/` | `30_Projects/Incubating/{slug}/` |
| Idea | `40_Ideas/{domain}/` | `40_Ideas/Unfiled/` |
| Reference | `50_References/{domain}/` | `50_References/Unfiled/` |
| Media/Transcript | `50_References/Media/` | `50_References/Media/` |

## Duplicate Detection

The agent checks for:
- Title similarity to existing notes (>80% match = warn)
- Content similarity to existing notes (via vector search or keyword overlap)
- Alias collision with existing note aliases
- Tag cluster overlap suggesting same topic

Recommendations:
- `none` — no similar notes found
- `warn` — similar note exists but likely distinct
- `merge` — high similarity, suggest merging with existing note
- `reject` — exact duplicate, suggest rejecting the capture

## Graph Clutter Prevention

The agent checks for:
- Excessive cross-links (>20 outbound links) — flag for review
- Orphan risk (no links to or from the note) — suggest at least 1-2 links
- Circular references (A → B → A) — flag for review
- Broken links (linking to non-existent notes) — warn or remove
- Deep nesting (folder path > 5 levels) — suggest flatter structure

## Files It May Read

- `02_Agent_Workspace/{Type}_Drafts/{capture_id}_{type}_draft.md` — any agent draft
- `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`
- Existing canonical vault metadata (tags, aliases, folder structure via search index)

## Files It May Write

- `02_Agent_Workspace/{Type}_Drafts/{capture_id}_{type}_draft.md` — enrich in-place
- Duplicate detection report: `02_Agent_Workspace/Import_Plans/{capture_id}_duplicate_report.json`

## Files It Must Never Write

- Any file inside `/home/lifeos/10_Vaults/LifeOS/`
- Agent drafts it did not originally own (only enrich, never replace content)

## Safety Boundaries

- Never modify the body/content of a draft — only enrich frontmatter
- Never change `status` or `confidence` — those are set by the originating agent
- Never remove existing metadata — only add or validate
- Never create new tags without checking existing tag inventory
- Never suggest links to notes that don't exist

## Required Template/Format

The enriched frontmatter must include all fields listed in Outputs. Fields the agent cannot determine should be left as the original value, not overwritten with placeholder.

## Review Checklist

- [ ] All aliases are valid and non-colliding
- [ ] All tags follow LifeOS conventions
- [ ] Domain is assigned and appropriate
- [ ] Folder suggestion is appropriate for note type
- [ ] Duplicate check was performed and recommendation is reasonable
- [ ] No more than 10 tags
- [ ] No broken links suggested
- [ ] No graph clutter issues flagged without recommendation
- [ ] Source trail metadata is preserved

## Failure Modes

| Failure | Handling |
|---|---|
| Cannot determine domain | Leave as empty string, flag for human |
| Note type unclear (mixed content) | Flag for human, do not guess folder |
| Tag already exists with different case | Normalize to existing tag form |
| Alias collision detected | Flag collision, do not auto-resolve |
| Too many similar notes found | Flag for human deduplication review |

## Escalation/Delegation Rules

- If duplicate detection finds a merge candidate: escalate to human in review packet
- If the note type is ambiguous and folder placement is uncertain: flag multiple options, let human decide
- If a broken link is intentional (future note): human must confirm in review

## Example Output

Before (Knowledge Note Agent output):

```yaml
---
aliases: [container hardening]
tags: [containers, Docker, Security]
domain: 
created: 2026-07-08T12:36:00Z
source_capture: cap_20260708_123456_abc123
source_url: https://example.com/article
status: draft
confidence: machine_generated_unreviewed
---
```

After (Metadata Taxonomy Agent enrichment):

```yaml
---
aliases:
  - container hardening
  - Docker security hardening
  - container runtime security
tags:
  - containers
  - docker
  - security
  - devops
  - infrastructure
domain: software-engineering
created: 2026-07-08T12:36:00Z
source_capture: cap_20260708_123456_abc123
source_url: https://example.com/article
status: draft
confidence: machine_generated_unreviewed
related_notes:
  - "[[Docker Compose Best Practices]]"
  - "[[Linux Capabilities]]"
  - "[[LifeOS Service Hardening]]"
folder_suggestion: "20_Knowledge/software-engineering/"
duplicate_check:
  potential_duplicates: []
  similarity_score: 0.35
  recommendation: "none"
---
```
