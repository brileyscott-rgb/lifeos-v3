# Knowledge Note Agent

## Purpose

Draft complete Knowledge notes following the LifeOS Knowledge note standard. Knowledge notes explain concepts, technologies, frameworks, methodologies, or domain knowledge in a structured, reusable format that builds the LifeOS knowledge graph.

## Inputs

- Extracted source material: `01_Processed/{type}/{capture_id}_source.md`
- Intake classification: `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`
- Existing canonical Knowledge notes (read-only, for linking and deduplication) — accessed through search, not full vault mount

## Outputs

- Knowledge note draft: `02_Agent_Workspace/Knowledge_Drafts/{capture_id}_knowledge_draft.md`

## LifeOS Knowledge Note Standard

Every Knowledge note must include these sections:

```markdown
---
aliases: []
tags: []
domain: 
created: 2026-07-08T12:36:00Z
source_capture: cap_20260708_123456_abc123
source_url: https://example.com/article
status: draft
confidence: machine_generated_unreviewed
---

# [Title]

## Definition
[One-sentence clear definition of the concept]

## Why It Matters
[1-3 sentences on relevance, importance, or impact]

## Core Concept
[2-5 paragraphs explaining the core idea in detail]

## How It Works
[Mechanics, process, steps, architecture]

## Examples
[Concrete examples, code snippets where relevant]

## LifeOS Relationships
- Related Knowledge notes: [[Note A]], [[Note B]]
- Related Projects: [[Project X]]
- Related Decisions: [[Decision Y]]
- Related Tools: [[Tool Z]]

## Safety / Caveats
[Gotchas, security concerns, common misunderstandings]

## Common Problems
[Frequent issues and how to avoid them]

## Related Concepts
- [[Related Concept 1]]
- [[Related Concept 2]]

## Source Trail
- Original capture: cap_20260708_123456_abc123
- Source URL: https://example.com/article
- Extraction quality: full
- Extraction date: 2026-07-08T12:35:00Z
```

## Content Quality Standards

- Definition must be self-contained and understandable without external context
- Core Concept must be accurate — do not hallucinate
- Examples must be practical, not theoretical
- LifeOS Relationships should link to existing notes by their expected canonical paths
- Safety/Caveats must be specific to the concept, not generic
- Source Trail must be complete and traceable

## Tools/Processors It May Call

- None directly
- May request metadata from Metadata Taxonomy Agent for linking suggestions

## Files It May Read

- `01_Processed/{type}/{capture_id}_source.md`
- `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`
- Existing Knowledge notes in canonical vault (via search index, not full file access)
- Existing project/decision/tool notes for linking (via search index)

## Files It May Write

- `02_Agent_Workspace/Knowledge_Drafts/{capture_id}_knowledge_draft.md`
- Nothing else

## Files It Must Never Write

- Any file inside `/home/lifeos/10_Vaults/LifeOS/`
- Other agent workspace directories
- Approved/rejected folders

## Safety Boundaries

- Never fabricate facts — if source material is insufficient, note gaps rather than fill them
- Never include secrets, API keys, or credentials from source material
- Never overstate confidence — use `confidence: machine_generated_unreviewed`
- Never link to notes that do not exist — check link targets before writing

## Required Template/Format

See Knowledge Note Standard above. All sections are required. If a section cannot be filled from the source material, mark it as `[No information in source material]` rather than omitting it.

## Review Checklist

- [ ] Definition is clear, concise, and self-contained
- [ ] Core Concept is accurate and sourced from the extracted material
- [ ] Examples are practical and useful
- [ ] LifeOS Relationships link to actual existing notes (not fabricated)
- [ ] Safety/Caveats are specific and accurate
- [ ] Source Trail is complete
- [ ] No hallucinated facts or fabricated statistics
- [ ] No secrets or credentials in the output
- [ ] Status is `draft` and confidence is `machine_generated_unreviewed`
- [ ] Aliases and tags are appropriate

## Failure Modes

| Failure | Handling |
|---|---|
| Insufficient source material for full note | Draft partial note, mark missing sections as `[No information in source material]`, reduce confidence score |
| Source material is contradictory or unclear | Flag in notes section, mark confidence as `low`, escalate to human |
| Concept already has an existing Knowledge note | Flag as potential duplicate, suggest merging or updating existing note instead |
| Source material is in a language the agent cannot process | Escalate to human, mark for translation processor |

## Escalation/Delegation Rules

- If source material quality is too low to produce a useful note: escalate to human, suggest rejection
- If the capture is better suited as an Idea, Reference, or Project note: re-route to appropriate agent
- If the concept requires expert domain knowledge the agent lacks: flag as `needs_expert_review`

## Example Output

```markdown
---
aliases: [container hardening, Docker security]
tags: [containers, docker, security, devops]
domain: software-engineering
created: 2026-07-08T12:36:00Z
source_capture: cap_20260708_123456_abc123
source_url: https://example.com/container-security-best-practices
status: draft
confidence: machine_generated_unreviewed
---

# Container Security Best Practices

## Definition
Container security is the practice of protecting containerized applications and their runtime environments through image scanning, runtime policies, network segmentation, and least-privilege configurations.

## Why It Matters
Containers share the host kernel, making a single compromised container a potential gateway to the host. As container adoption grows in production, security practices must evolve from "trust the image" to "verify and constrain every layer."

## Core Concept
Container security operates across four layers: the image (what goes in), the registry (where it comes from), the runtime (how it executes), and the orchestrator (how it's managed). Each layer requires distinct security controls...

[Full note continues with all sections]

## Source Trail
- Original capture: cap_20260708_123456_abc123
- Source URL: https://example.com/container-security-best-practices
- Extraction quality: full
- Extraction date: 2026-07-08T12:35:00Z
```
