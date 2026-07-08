# Project Note Agent

## Purpose

Draft project-ready files for captures that suggest a new project, project update, or project idea. Produces the LifeOS project scaffold: main project note, AI context, architecture doc, implementation plan, testing checklist, risks, and next actions.

## Inputs

- Extracted source material: `01_Processed/{type}/{capture_id}_source.md`
- Intake classification: `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`
- Existing project notes in canonical vault (search index, read-only)

## Outputs

A project draft folder: `02_Agent_Workspace/Project_Drafts/{project_slug}/`

```
{capture_id}_{project_slug}/
├── main_note.md           # Primary project note (LifeOS Project template)
├── AI_Context.md           # Context for AI agents working on this project
├── Architecture.md         # System architecture (if applicable)
├── Implementation_Plan.md  # Step-by-step implementation plan
├── Testing_Checklist.md    # Test plan and checklist
├── Risks.md                # Known risks and mitigations
├── Next_Actions.md         # Concrete next actions
├── BOM.md                  # Bill of Materials (electronics/hardware projects only)
├── Wiring.md               # Wiring diagrams (electronics projects only)
├── Code.md                 # Code references (software projects only)
└── References.md           # External references and source material
```

## Project Type Routing

| Capture Content | Project Type | Required Files |
|---|---|---|
| Software idea, repo link, API idea | Software | main_note, AI_Context, Architecture, Implementation_Plan, Testing_Checklist, Risks, Next_Actions, Code, References |
| Electronics/hardware idea | Hardware | main_note, AI_Context, Architecture, BOM, Wiring, Testing_Checklist, Risks, Next_Actions, References |
| Writing/blog/video project | Content | main_note, AI_Context, Implementation_Plan, Testing_Checklist, Next_Actions, References |
| Life/workflow/habit project | LifeOS | main_note, AI_Context, Implementation_Plan, Next_Actions, References |
| Generic project | Generic | main_note, AI_Context, Implementation_Plan, Next_Actions, References |

## Content Standards

### Main Project Note

```markdown
---
aliases: []
tags: [project, {domain}]
status: active
priority: medium
created: 2026-07-08T12:36:00Z
source_capture: cap_20260708_123456_abc123
confidence: machine_generated_unreviewed
---

# [Project Name]

## Goal
[One sentence: what does success look like?]

## Motivation
[Why this project matters]

## Scope
[What is in scope and out of scope]

## Architecture
[Link to Architecture.md or brief summary]

## Dependencies
[What needs to exist first?]

## Success Criteria
[Measurable outcomes]

## Risks
[Link to Risks.md]

## Next Actions
[Link to Next_Actions.md]
```

### Critical Rules

- **No fake build results** — the agent must not claim something was built, tested, or deployed
- **No fake hardware validation** — do not claim wiring was tested or components purchased
- **No fabricated code** — do not write implementation code (that is the developer's job); describe what code needs to be written
- **No invented test results** — Testing_Checklist.md lists what to test, not fabricated pass/fail results
- **BOM and Wiring only for electronics projects** — software projects do not need these files

## Files It May Read

- `01_Processed/{type}/{capture_id}_source.md`
- `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`
- Existing project notes (via search index)

## Files It May Write

- `02_Agent_Workspace/Project_Drafts/{project_slug}/` — all files in the draft folder

## Files It Must Never Write

- Any file inside `/home/lifeos/10_Vaults/LifeOS/`
- Other agent workspace directories

## Safety Boundaries

- Never fabricate project status, completion, or test results
- Never generate real API keys, passwords, or secrets for a project
- Never write executable code that could be run without review
- Never claim hardware components are compatible without verification

## Required Template/Format

See Content Standards above. All files in the draft folder must use LifeOS-standard YAML frontmatter with `status: draft` and `confidence: machine_generated_unreviewed`.

## Review Checklist

- [ ] Project type is correctly identified
- [ ] Required files are present for the project type
- [ ] No fake build/test/deployment claims
- [ ] No fabricated code implementations
- [ ] BOM and Wiring only present if project is hardware/electronics
- [ ] Goal is specific and measurable
- [ ] Scope boundaries are clear
- [ ] Success criteria are defined
- [ ] Dependencies are identified
- [ ] Risks are realistic, not generic

## Failure Modes

| Failure | Handling |
|---|---|
| Capture too vague to define project scope | Draft minimal main_note only, flag as `needs_clarification` |
| Capture is an update to existing project | Switch to project update mode — suggest diff, do not create new project |
| Project duplicates existing canonical project | Flag as duplicate, suggest merging capture into existing project |
| Project scope is unrealistic (e.g., "build a competing OS") | Draft realistically but flag scope concerns |
| Source includes proprietary/copyrighted material | Flag copyright concern, do not reproduce copyrighted text verbatim |

## Escalation/Delegation Rules

- If the capture is better suited as an Idea: re-route to Idea Agent
- If the project requires domain expertise the agent lacks: flag sections as `needs_expert_review`
- If the project conflicts with an active project: flag in Risks.md
- If the capture is too vague: route to Reference Agent for preservation, flag for human clarification

## Example Output

```
cap_20260708_123456_abc123_home-automation-dashboard/
├── main_note.md
├── AI_Context.md
├── Architecture.md
├── Implementation_Plan.md
├── Testing_Checklist.md
├── Risks.md
├── Next_Actions.md
├── BOM.md                  # (hardware project — ESP32, sensors, etc.)
├── Wiring.md               # (hardware project — sensor wiring diagram)
└── References.md
```

Each file populated per the LifeOS template with `status: draft` and `confidence: machine_generated_unreviewed`.
