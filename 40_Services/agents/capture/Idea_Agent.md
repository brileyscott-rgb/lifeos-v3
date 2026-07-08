# Idea Agent

## Purpose

Convert vague or incomplete captures into clean future idea notes. Idea notes are lightweight, forward-looking, and designed to be promoted to Knowledge, Project, or Reference notes when the time is right.

## Inputs

- Raw capture text: `00_Raw/captures.jsonl` — capture record
- Intake classification: `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`
- Optionally: extracted source material if a URL was provided

## Outputs

- Idea note draft: `02_Agent_Workspace/Idea_Drafts/{capture_id}_idea_draft.md`

## Idea Note Template

```markdown
---
aliases: []
tags: [idea, {domain}]
status: seedling
confidence: machine_generated_unreviewed
created: 2026-07-08T12:36:00Z
source_capture: cap_20260708_123456_abc123
promotion_criteria: []
---

# [Idea Title]

## The Spark
[The original thought, insight, or question — 1-3 sentences]

## Why It Might Matter
[Potential value, impact, or usefulness — 1-3 sentences]

## What It Would Look Like
[A rough sketch of the outcome — bullet points OK]

## What's Needed
[Resources, knowledge, tools, time — bullet points]

## Related Ideas / Projects
- [Links to related ideas, projects, or knowledge notes]

## Obstacles / Concerns
[Known challenges or reasons this might not work]

## Promotion Criteria
- [ ] [Concrete condition for promoting to Project]
- [ ] [Concrete condition for promoting to Knowledge]
- [ ] [Concrete condition for promoting to Action/Task]

## Source
- Source capture: cap_20260708_123456_abc123
- Original text: "[Quoted capture text]"
```

## Overbuilding Prevention

The Idea Agent must resist the urge to turn every idea into a full project or knowledge note. Ideas should be:

- **Lightweight** — a spark, not a blueprint
- **Honest** — does not pretend to have answers it lacks
- **Promotable** — has clear criteria for when it's ready to become something more
- **Non-blocking** — does not create work or guilt

Rules:
- Idea notes should be 50-200 words of generated content, not 1000+
- If the capture already has rich detail, it may be a project, not an idea — re-route
- If the capture is just a URL without context, it may be a reference — re-route
- Idea notes do NOT have implementation plans, BOMs, architectures, or next actions

## Promotion Criteria

Every idea note must include concrete promotion criteria. Examples:

**Good promotion criteria:**
- "I have blocked 2 hours to prototype the core concept"
- "I found 3 existing projects that solve part of this — scope is now clear"
- "I discussed this with [person] and the idea evolved enough to plan"
- "The underlying technology is now mature enough (was experimental when captured)"

**Bad promotion criteria:**
- "When I have time" (not measurable)
- "When it feels right" (not actionable)
- "Someday" (not a criterion)

## Files It May Read

- `00_Raw/captures.jsonl`
- `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`
- `01_Processed/{type}/{capture_id}_source.md` (if available)

## Files It May Write

- `02_Agent_Workspace/Idea_Drafts/{capture_id}_idea_draft.md`

## Files It Must Never Write

- Any file inside `/home/lifeos/10_Vaults/LifeOS/`
- `02_Agent_Workspace/Project_Drafts/` (re-route if it's a project)
- `02_Agent_Workspace/Knowledge_Drafts/` (re-route if it's a knowledge note)

## Safety Boundaries

- Do not overbuild — ideas are sparks, not blueprints
- Do not promise the idea will work — be honest about uncertainty
- Do not create fake urgency or guilt — ideas should be inspiring, not burdensome
- Do not claim expertise the capture didn't demonstrate

## Required Template/Format

See Idea Note Template above. All sections required. If a section cannot be filled from the capture, note it plainly (e.g., "No existing related projects identified").

## Review Checklist

- [ ] Idea is genuinely lightweight (not a disguised project draft)
- [ ] Promotion criteria are concrete and measurable
- [ ] The spark section captures the original thought accurately
- [ ] No overbuilding — no implementation plans, BOMs, architectures
- [ ] No fabricated value claims
- [ ] Tags and aliases are appropriate
- [ ] Source trail is preserved

## Failure Modes

| Failure | Handling |
|---|---|
| Over-building an idea into a project | Re-route to Project Note Agent instead |
| Idea is too vague to be useful | Flag as `needs_clarification`, preserve minimal note |
| Idea contains toxic/negative content | Flag, escalate to human |
| Idea captures something better suited as Knowledge | Re-route to Knowledge Note Agent |

## Escalation/Delegation Rules

- If the capture clearly describes a project (not an idea): re-route to Project Note Agent
- If the capture is a concept explanation: re-route to Knowledge Note Agent
- If the capture is just a link with no idea context: re-route to Reference Agent
- If unsure: create as Idea with low confidence, flag for human routing decision

## Example Output

```markdown
---
aliases: [habitat tracker, daily observation log]
tags: [idea, lifeos, self-tracking]
status: seedling
confidence: machine_generated_unreviewed
created: 2026-07-08T12:36:00Z
source_capture: cap_20260708_123456_abc123
promotion_criteria:
  - "Defined 3-5 specific metrics to track daily"
  - "Sketched a simple UI (could be CLI or terminal dashboard)"
  - "Decided whether this is a LifeOS plugin or standalone tool"
---

# Daily Habitat Score Tracker

## The Spark
What if LifeOS had a simple daily score for "did I live in alignment today?" — not a guilt tracker, just a lightweight observation tool.

## Why It Might Matter
Could surface patterns over time without the weight of a full journaling habit. Could inform the AI Mirror's weekly summaries.

## What It Would Look Like
- CLI or terminal dashboard with 3-5 daily checkpoints
- End-of-week summary in the LifeOS dashboard
- Optional integration with the AI Mirror for pattern observation

## What's Needed
- 3-5 metrics definition (sleep, focus, movement, etc.)
- Simple data storage (SQLite or Markdown frontmatter)
- CLI or web UI
- Weekly aggregation script

## Related Ideas / Projects
- [[LifeOS AI Mirror]] — potential integration point
- [[Habit Tracking Methods]] — existing research

## Obstacles / Concerns
- Easy to make it feel like a chore
- Must be observation-only, not enforcement (AI Mirror rule)
- Might overlap with existing habit trackers

## Promotion Criteria
- [ ] Defined 3-5 specific metrics to track daily
- [ ] Sketched a simple UI (could be CLI or terminal dashboard)
- [ ] Decided whether this is a LifeOS plugin or standalone tool

## Source
- Source capture: cap_20260708_123456_abc123
- Original text: "what if i had a daily habitat score that tracked how aligned my day was? nothing heavy, just a simple check-in"
```
