# Agent Roles

## Role Definition Format

Every agent role must define:

- role description
- allowed paths
- prohibited paths
- approval ceiling
- input schema
- output schema
- logging requirement
- failure behavior

Direct writes require role permission, path permission, approval-tier permission, and event logging.

## Initial Roles

| Agent | Purpose | Default Tier | Allowed Paths | Prohibited Paths | Logging Required |
|---|---|---:|---|---|---|
| Capture Classifier | Classify raw captures and propose destinations | A1 | `00_Inbox/`, `10_Vaults/LifeOS/01_INBOX/`, `50_Event_Log/` | `40_Services/secrets/`, destructive actions | yes |
| Document Extractor | Extract/OCR/summarize formal documents | A1 | `30_Documents/`, `10_Vaults/LifeOS/05_RESOURCES/`, `50_Event_Log/` | `40_Services/secrets/` | yes |
| Knowledge Curator | Convert approved material into curated notes | A2 | `10_Vaults/LifeOS/04_KNOWLEDGE/`, `10_Vaults/LifeOS/05_RESOURCES/` | raw imports without approval | yes |
| Project Maintainer | Maintain project notes and context | A3 | `10_Vaults/LifeOS/02_PROJECTS/`, `20_Workspaces/` | unrelated projects, secrets | yes |
| Migration Reviewer | Review old content before migration | A2 | `99_Archive/migration-staging/`, `50_Event_Log/migration/` | direct bulk import to vault, deletion without A4 approval | yes |
| Approval Summarizer | Summarize approval requests | A1 | `10_Vaults/LifeOS/01_INBOX/Pending_Approvals/`, `50_Event_Log/approvals/` | approval decisions without user input | yes |
| AI Mirror Observer | Observe patterns and produce reflections | A1 | `10_Vaults/LifeOS/10_AI_UNIVERSE/AI_Mirror/`, `50_Event_Log/` | enforcement, blocking, punitive rules, shame language | yes |
| Semantic Janitor | Detect stale, duplicate, weak, or orphaned knowledge | A2 | `10_Vaults/LifeOS/`, `50_Event_Log/maintenance/` | deletion without A4 approval | yes |
| System Monitor | Observe service and backup health | A1 | `40_Services/`, `50_Event_Log/failures/`, `50_Event_Log/maintenance/` | secrets modification | yes |
| DevOps Assistant | Propose and maintain service automation | A2 | `40_Services/compose/`, `40_Services/config/`, `60_AI_Runtime/` | live credential changes, destructive system actions | yes |
| Codebase Context Builder | Build codebase context packs | A1 | `20_Workspaces/`, `60_AI_Runtime/context-packs/` | private secrets, unrelated archives | yes |

## Initial A3 Policy

Only Project Maintainer and Semantic Janitor begin as A3-capable agents.

All other agents remain A0-A2 until explicitly upgraded.

See [[Policies/A3_Agent_Policy]].
