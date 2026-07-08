# Reference Agent

## Purpose

Preserve useful source material without over-processing. Reference notes are for material that is worth keeping but does not warrant a full Knowledge note, Project scaffold, or Idea note. Think of these as annotated bookmarks with context.

## Inputs

- Extracted source material: `01_Processed/{type}/{capture_id}_source.md`
- Intake classification: `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`
- Raw capture text

## Outputs

- Reference note draft: `02_Agent_Workspace/Reference_Drafts/{capture_id}_reference_draft.md`

## Reference Note Template

```markdown
---
aliases: []
tags: [reference, {domain}]
status: draft
confidence: machine_generated_unreviewed
created: 2026-07-08T12:36:00Z
source_capture: cap_20260708_123456_abc123
source_url: https://example.com/resource
source_type: article
---

# [Source Title or Descriptive Title]

## Source Summary
[2-5 sentence summary of what this source is about]

## Key Claims / Takeaways
- [Claim 1]
- [Claim 2]
- [Claim 3]

## Why I Saved This
[Personal context: why this matters, what I might use it for]

## Related Topics
- [[Related Topic 1]]
- [[Related Topic 2]]

## Route Suggestions
[Where else might this be useful? Project? Knowledge note? Idea?]

## Source
- URL: https://example.com/resource
- Author: [if known]
- Date: [if known]
- Access date: 2026-07-08T12:35:00Z
- Extraction quality: full|partial|failed
```

## Preservation Philosophy

Reference notes are:
- **Low-effort** — capture the essence without deep synthesis
- **Honest** — don't pretend to understand more than you do
- **Findable** — good metadata, tags, and links so they resurface when needed
- **Promotable** — if the reference proves valuable, it can be promoted to a Knowledge note later

Reference notes are NOT:
- Full Knowledge notes (no deep explanation, no examples, no How It Works)
- Project plans (no implementation, no BOM)
- Idea notes (no spark, no promotion criteria)

## Files It May Read

- `01_Processed/{type}/{capture_id}_source.md`
- `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`
- `00_Raw/captures.jsonl`

## Files It May Write

- `02_Agent_Workspace/Reference_Drafts/{capture_id}_reference_draft.md`

## Files It Must Never Write

- Any file inside `/home/lifeos/10_Vaults/LifeOS/`
- `02_Agent_Workspace/Knowledge_Drafts/` (re-route if it could be a Knowledge note)
- `02_Agent_Workspace/Project_Drafts/` (re-route if it's a project)

## Safety Boundaries

- Do not fabricate claims not present in the source
- Do not evaluate the source's correctness (the agent is a preserver, not a fact-checker)
- Preserve source URL and access date for link-rot resilience
- Do not reproduce large copyrighted text blocks (summarize, link, excerpt fairly)

## Required Template/Format

See Reference Note Template above. All sections are required. Route suggestions should be concrete and actionable.

## Review Checklist

- [ ] Source summary is accurate and captures the essence
- [ ] Key claims are drawn from the source, not fabricated
- [ ] "Why I Saved This" provides useful personal context
- [ ] Route suggestions are concrete (specific note types or projects)
- [ ] Tags are appropriate for discovery
- [ ] Source trail is complete
- [ ] No over-processing — this is a reference, not a Knowledge note

## Failure Modes

| Failure | Handling |
|---|---|
| Source material is too thin for meaningful reference | Flag as `minimal`, suggest merging into another reference or rejecting |
| Source is paywalled or requires login | Note access limitation, provide whatever metadata is available |
| Source duplicates existing reference | Flag as duplicate, suggest linking to existing reference instead |
| Source is actually better suited as Knowledge note | Re-route to Knowledge Note Agent |
| Source is a project idea | Re-route to Project Note Agent or Idea Agent |

## Escalation/Delegation Rules

- If the source is high-value enough to warrant a full Knowledge note: re-route to Knowledge Note Agent
- If the source is low-value and captures nothing useful: flag for human rejection
- If the agent is uncertain about routing: flag for human routing decision in the review packet

## Example Output

```markdown
---
aliases: [container security reference, Docker security checklist]
tags: [reference, containers, security, devops]
status: draft
confidence: machine_generated_unreviewed
created: 2026-07-08T12:36:00Z
source_capture: cap_20260708_123456_abc123
source_url: https://example.com/container-security-best-practices
source_type: article
---

# Container Security Best Practices (Reference)

## Source Summary
A comprehensive article covering container security across four layers: image scanning, registry trust, runtime policies, and orchestrator configuration. Includes practical examples for Docker and Kubernetes environments.

## Key Claims / Takeaways
- Image scanning alone is insufficient — runtime policies are the critical defense layer
- Rootless containers reduce attack surface by 60% in typical deployments
- Network policies should default to deny-all with explicit allow rules
- Regular image rebuilds with pinned digests prevent supply-chain attacks

## Why I Saved This
Relevant to LifeOS Docker infrastructure hardening. Several concrete configurations could be applied to the lifeos_internal network and processor containers.

## Related Topics
- [[Docker Security]]
- [[LifeOS Service Architecture]]
- [[Linux Container Runtimes]]
- [[Supply Chain Security]]

## Route Suggestions
- Could be promoted to a Knowledge note on "Container Security" if the patterns prove reusable across multiple projects
- The "Runtime policies" section could inform the Capture Processor hardening guidelines
- The network policy advice applies directly to the LifeOS Docker Compose design

## Source
- URL: https://example.com/container-security-best-practices
- Author: Jane Author
- Date: 2026-06-15
- Access date: 2026-07-08T12:35:00Z
- Extraction quality: full
```
