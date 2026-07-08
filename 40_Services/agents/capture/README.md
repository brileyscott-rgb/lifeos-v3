# Capture Agents

Specialized AI agents for the LifeOS Agentic Capture Pipeline. All agents operate on the Headless Capture Buffer Vault (`/home/lifeos/LifeOS_Capture_Buffer/`) and the Media Archive (`/home/lifeos/LifeOS_Media_Archive/`). No agent has access to the canonical LifeOS vault.

## Agent Pipeline

```
Raw Capture → Intake Agent → Source Extraction Agent
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            Knowledge Note   Project Note     Idea Agent
                Agent           Agent
                    │               │               │
                    ├───────────────┴───────────────┤
                    ▼                               ▼
            Reference Agent              Media Transcript Agent
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
                          Metadata Taxonomy Agent
                                    │
                                    ▼
                            QA Verifier Agent
                                    │
                                    ▼
                          Import Planner Agent
                                    │
                                    ▼
                            Review Packet (human approval)
```

## Agent List

| # | Agent | File | Purpose |
|---|---|---|---|
| 1 | Intake Agent | `Intake_Agent.md` | Normalize, classify, route raw captures |
| 2 | Source Extraction Agent | `Source_Extraction_Agent.md` | Extract clean source material from URLs, files |
| 3 | Knowledge Note Agent | `Knowledge_Note_Agent.md` | Draft Knowledge notes per LifeOS standard |
| 4 | Project Note Agent | `Project_Note_Agent.md` | Draft project scaffold files |
| 5 | Idea Agent | `Idea_Agent.md` | Convert vague captures into future idea notes |
| 6 | Reference Agent | `Reference_Agent.md` | Preserve source material without over-processing |
| 7 | Media Transcript Agent | `Media_Transcript_Agent.md` | Handle video/audio/image captures |
| 8 | Metadata Taxonomy Agent | `Metadata_Taxonomy_Agent.md` | Clean YAML, tags, links, folders |
| 9 | QA Verifier Agent | `QA_Verifier_Agent.md` | Validate quality, source trail, compliance |
| 10 | Import Planner Agent | `Import_Planner_Agent.md` | Produce review packets for human approval |

## Safety Boundaries (All Agents)

- **No canonical vault writes** — agents never write to `/home/lifeos/10_Vaults/LifeOS/`
- **No shell execution** — agents describe what should happen; processors execute
- **No Docker socket access** — agents do not control containers
- **No secret generation** — agents do not create API keys, tokens, or credentials
- **No outbound network calls** — agents do not fetch URLs, call APIs, or access the internet (processors handle this)
- **No deletion of captures** — agents may mark for deletion in a proposal; operator decides
- **Idempotent outputs** — re-running an agent with the same input produces the same output
