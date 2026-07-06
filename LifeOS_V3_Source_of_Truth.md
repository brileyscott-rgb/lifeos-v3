# LifeOS V3 Source of Truth

Status: draft source of truth  
Created: 2026-07-04  
Purpose: define the clean-slate LifeOS architecture, workflows, file structure, AI system model, and migration policy for the next implementation phase.

## 1. Core Intent

LifeOS V3 is a clean personal operating system for knowledge, projects, documents, automation, AI agents, and long-term self-observation.

The system should solve five problems:

1. Capture information from anywhere without losing it.
2. Separate raw inputs from trusted knowledge.
3. Give AI agents enough context and tool access to be useful without letting them drift or pollute the system.
4. Keep projects, documents, decisions, and identity patterns organized over time.
5. Support migration from the old LifeOS without blindly importing old clutter.

The preferred foundation is a fresh Linux user account rather than continuing to patch the current environment.

## 2. Non-Negotiable Design Decisions

### 2.1 Fresh Start

LifeOS V3 should be built in a clean environment.

Preferred option:

```text
new Linux user account
```

Reasons:

1. Clean home directory.
2. Clean shell and tool configuration.
3. Clean Docker/service layout.
4. Lower risk than reinstalling the OS.
5. Old LifeOS remains available as a source archive.
6. Migration can be deliberate instead of automatic.

### 2.2 Separation of Layers

Obsidian is the curated meaning layer. It should not become a dumping ground for raw files, generated artifacts, Docker data, cloned repos, or unreviewed exports.

Execution artifacts belong outside the vault.

Large source documents belong in a document system or filesystem store, with summaries and links in the vault.

### 2.3 Observation Without Enforcement

The AI Mirror may observe patterns, summarize behavior, and offer insight.

It must not enforce life rules, block project creation, lock workflows, shame behavior, or restrict the user's choices.

Allowed:

```text
pattern observation
weekly summaries
identity insights
commitment-to-closure reporting
context-switching reports
suggestions
```

Not allowed:

```text
Focus Locker enforcement
Anti-Escape Valve enforcement
forced behavioral restrictions
mandatory life rules
blocking new projects
punitive friction systems
```

### 2.4 Agent Behavior Model

Agent behavior is permission-based, not universally draft-only.

Default behavior:

```text
agents draft, classify, summarize, route, and propose
```

Permitted exception:

```text
trusted agents may directly write or modify approved files when their role, path permissions, and approval tier allow it
```

Every meaningful agent action must be logged.

### 2.5 Advanced Infrastructure Is Allowed

LifeOS V3 does not need to prefer only boring infrastructure.

Advanced infrastructure is encouraged when it creates leverage and remains governed, observable, and recoverable.

Allowed from the architecture level:

```text
Docker
n8n
MCP
agent frameworks
local AI
remote AI APIs
vector search
ChatOps
document intelligence
monitoring stacks
semantic indexing
workflow queues
local databases
```

The constraint is not simplicity. The constraint is controlled complexity.

## 3. Architecture Overview

LifeOS V3 has seven major layers.

```text
User Interfaces
→ Capture Layer
→ Automation and Orchestration Layer
→ AI Runtime and Agent Layer
→ Storage and Knowledge Layer
→ Observability and Event Log Layer
→ Migration and Archive Layer
```

### 3.1 User Interfaces

Primary interaction points:

```text
Obsidian
terminal/OpenCode
mobile capture
ChatOps bot
file drop folders
web clipper or link capture
document scanner/import folder
```

The user should not need to manually maintain every folder, dashboard, YAML flag, or cross-link.

### 3.2 Capture Layer

The capture layer receives raw inputs from many sources and routes them into processing.

Supported capture sources:

```text
links
PDFs
screenshots
audio notes
voice transcripts
web pages
AI chat exports
terminal logs
error logs
GitHub repos
project ideas
documents
manuals
receipts
medical records
finance records
```

### 3.3 Automation and Orchestration Layer

n8n is the preferred orchestration hub.

Responsibilities:

```text
watch folders
receive webhooks
trigger capture workflows
send ChatOps messages
route approval requests
schedule maintenance jobs
run document ingestion workflows
call local or remote AI services
log workflow events
handle failed workflow alerts
```

### 3.4 AI Runtime and Agent Layer

The AI runtime includes local and external models, agent prompts, MCP servers, context packs, and permission definitions.

Expected capabilities:

```text
classification
summarization
metadata generation
note creation
project context generation
document extraction
semantic search
codebase context retrieval
vault maintenance
migration review
identity pattern observation
approval summarization
```

### 3.5 Storage and Knowledge Layer

Primary stores:

```text
Obsidian vault for curated meaning
filesystem for raw capture and working files
Paperless-ngx for formal documents
Git repos for code and versioned text
SQLite/Postgres for events and workflow state
vector database or embedding store for semantic retrieval
Docker volumes for service data
```

### 3.6 Observability and Event Log Layer

All meaningful system actions should be visible later.

The event log is the factual spine of the system.

Events should be structured and append-only where possible.

### 3.7 Migration and Archive Layer

Old LifeOS content is not imported blindly.

It is staged, classified, reviewed, amended, summarized, archived, or deleted based on usefulness.

## 4. Target Filesystem Structure

Recommended home directory layout for the fresh account:

```text
/home/lifeos/
├── 00_Inbox/
│   ├── quick-capture/
│   ├── links/
│   ├── files/
│   ├── screenshots/
│   ├── audio/
│   ├── mobile/
│   └── pending-review/
│
├── 10_Vaults/
│   └── LifeOS/
│       ├── 00_HOME/
│       ├── 01_INBOX/
│       ├── 02_PROJECTS/
│       ├── 03_AREAS/
│       ├── 04_KNOWLEDGE/
│       ├── 05_RESOURCES/
│       ├── 06_ARCHIVE/
│       ├── 07_DAILY/
│       ├── 08_TEMPLATES/
│       ├── 09_DASHBOARDS/
│       └── 10_AI_UNIVERSE/
│
├── 20_Workspaces/
│   ├── Engineering/
│   ├── AI_Systems/
│   ├── Hardware/
│   ├── Writing/
│   └── Experiments/
│
├── 30_Documents/
│   ├── paperless-import/
│   ├── manuals/
│   ├── receipts/
│   ├── medical/
│   ├── finance/
│   └── legal/
│
├── 40_Services/
│   ├── compose/
│   │   ├── automation/
│   │   ├── documents/
│   │   ├── ai/
│   │   ├── monitoring/
│   │   ├── chatops/
│   │   └── databases/
│   ├── config/
│   ├── data/
│   ├── secrets/
│   └── backups/
│
├── 50_Event_Log/
│   ├── events.jsonl
│   ├── agent-runs/
│   ├── approvals/
│   ├── failures/
│   └── maintenance/
│
├── 60_AI_Runtime/
│   ├── prompts/
│   ├── agents/
│   ├── mcp/
│   ├── schemas/
│   ├── context-packs/
│   ├── evals/
│   └── memory/
│
├── 70_Backups/
│   ├── vault/
│   ├── services/
│   ├── documents/
│   └── system/
│
└── 99_Archive/
    ├── old-user-imports/
    ├── deprecated-workflows/
    └── migration-staging/
```

## 5. Target Obsidian Vault Structure

```text
LifeOS/
├── 00_HOME/
│   ├── Command_Center.md
│   ├── Current_Focus.md
│   ├── Weekly_Review.md
│   └── System_Status.md
│
├── 01_INBOX/
│   ├── Captures/
│   ├── Pending_Approvals/
│   ├── Processing_Errors/
│   └── Triage.md
│
├── 02_PROJECTS/
│   ├── _Project_Index.md
│   └── Example_Project/
│       ├── index.md
│       ├── AI_Context.md
│       ├── Decisions.md
│       ├── Tasks.md
│       ├── Logs.md
│       └── References.md
│
├── 03_AREAS/
│   ├── Health/
│   ├── Finance/
│   ├── Career/
│   ├── Learning/
│   ├── Home/
│   └── Relationships/
│
├── 04_KNOWLEDGE/
│   ├── AI/
│   ├── Systems/
│   ├── Electronics/
│   ├── Programming/
│   ├── Supply_Chain/
│   └── Personal_Development/
│
├── 05_RESOURCES/
│   ├── Books/
│   ├── Courses/
│   ├── Articles/
│   ├── Tools/
│   └── Repos/
│
├── 06_ARCHIVE/
│   ├── Completed_Projects/
│   ├── Dormant_Projects/
│   └── Old_Notes/
│
├── 07_DAILY/
│   ├── Daily/
│   ├── Weekly/
│   ├── Monthly/
│   └── Reviews/
│
├── 08_TEMPLATES/
│   ├── Project.md
│   ├── AI_Context.md
│   ├── Decision.md
│   ├── Capture.md
│   ├── Knowledge_Note.md
│   ├── Area.md
│   ├── Daily.md
│   └── Approval_Request.md
│
├── 09_DASHBOARDS/
│   ├── Projects.md
│   ├── Commitments.md
│   ├── Knowledge_Gaps.md
│   ├── Capture_Queue.md
│   ├── Agent_Activity.md
│   └── Identity_Matrix.md
│
└── 10_AI_UNIVERSE/
    ├── README.md
    ├── Runtime_Loadout.md
    ├── System_Registry.md
    ├── Approval_Tiers.md
    ├── Agent_Roles.md
    ├── Workflow_Governor.md
    ├── AI_Mirror/
    │   ├── Who_Am_I_AI_Observed.md
    │   ├── Behavioral_Patterns.md
    │   ├── Commitment_To_Closure.md
    │   ├── Avoidance_Fingerprints.md
    │   ├── Identity_Insights.md
    │   └── Observations.md
    ├── Schemas/
    │   ├── capture.schema.md
    │   ├── project.schema.md
    │   ├── decision.schema.md
    │   ├── approval.schema.md
    │   ├── agent-run.schema.md
    │   └── identity-observation.schema.md
    ├── Prompts/
    │   ├── capture-classifier.md
    │   ├── knowledge-curator.md
    │   ├── project-maintainer.md
    │   ├── ai-mirror.md
    │   ├── approval-summarizer.md
    │   └── migration-reviewer.md
    └── Logs/
        ├── Agent_Runs.md
        ├── Maintenance_Log.md
        └── System_Changes.md
```

## 6. Core Features

### 6.1 Universal Capture Pipeline

All raw inputs enter a capture location first.

Standard flow:

```text
raw input
→ capture inbox
→ extraction/OCR/transcription when needed
→ classification
→ metadata generation
→ destination proposal
→ approval or direct action based on tier
→ final location
→ event log
```

### 6.2 ChatOps Approval and Notification Layer

Agents and services should send updates through a single primary communication channel.

Recommended options:

```text
Telegram
Discord
Slack
Matrix
ntfy
Gotify
```

ChatOps message types:

```text
approval request
agent completed task
agent failed task
capture needs review
document imported
project status changed
maintenance suggestion
stack health warning
daily digest
weekly review digest
```

Standard response actions:

```text
approve
reject
revise
defer
archive
escalate
commit
rerun
```

### 6.3 Approval Tiers

Approval tiers govern what agents and workflows can do.

```text
A0 = read, observe, index, summarize existing accessible content
A1 = write logs, summaries, and low-risk generated notes in designated locations
A2 = create new files in approved inboxes, staging areas, or generated-output folders
A3 = modify approved vault or project files according to role and path permissions
A4 = destructive actions, credential changes, external publishing, financial actions, system-level changes, or permanent deletion
```

A4 always requires explicit human approval.

### 6.4 Agent Roles

Initial agent roles:

```text
Capture Classifier
Document Extractor
Knowledge Curator
Project Maintainer
Migration Reviewer
Approval Summarizer
AI Mirror Observer
Semantic Janitor
System Monitor
DevOps Assistant
Codebase Context Builder
```

Each agent needs:

```text
role description
allowed paths
prohibited paths
approval ceiling
input schema
output schema
logging requirement
failure behavior
```

### 6.5 MCP Tool Layer

MCP should provide controlled tool access to AI systems.

Candidate MCP servers:

```text
filesystem MCP
git MCP
sqlite/postgres MCP
browser/search MCP
Docker MCP or controlled Docker wrapper
Obsidian/local vault MCP
memory MCP
sequential-thinking MCP
```

MCP access must be path-bounded and role-aware.

### 6.6 Document Intelligence

Paperless-ngx should manage formal documents.

Document types:

```text
bills
receipts
tax documents
medical records
manuals
datasheets
legal documents
financial records
warranties
```

Vault notes should contain summaries, decisions, reminders, and links to source documents rather than duplicating every raw document.

### 6.7 Project System

Every active project should have both a workspace folder and a vault folder.

Workspace:

```text
/home/lifeos/20_Workspaces/<domain>/<project>/
```

Vault:

```text
/home/lifeos/10_Vaults/LifeOS/02_PROJECTS/<project>/
```

Required project files:

```text
index.md
AI_Context.md
Decisions.md
Tasks.md
Logs.md
References.md
```

### 6.8 AI Context Files

Each project must include an `AI_Context.md` file.

Purpose:

```text
give agents the correct project scope
define allowed and prohibited paths
record current project state
document known constraints
reduce hallucinated context
prevent wandering edits
```

### 6.9 Event Log

The event log records system activity.

Primary file:

```text
/home/lifeos/50_Event_Log/events.jsonl
```

Example event types:

```text
capture.created
capture.classified
capture.routed
document.ingested
note.created
note.updated
project.created
project.updated
project.completed
approval.requested
approval.granted
approval.rejected
agent.started
agent.completed
agent.failed
maintenance.suggested
migration.item.reviewed
migration.item.revised
migration.item.archived
migration.item.deleted
```

### 6.10 Semantic Janitor

The Semantic Janitor maintains vault and knowledge quality.

Responsibilities:

```text
detect duplicate notes
detect weak metadata
find stale projects
find orphaned captures
suggest cross-links
detect similar topics
identify consolidation candidates
flag broken links
surface processing errors
```

The Semantic Janitor may create suggestions, modify files within its approval tier, or request approval depending on the action risk.

### 6.11 AI Mirror

The AI Mirror observes patterns and generates perspective.

It may track:

```text
commitment-to-closure
project initiation vs completion
planning vs execution signals
context switching
recurring blockers
recurring domains of interest
areas of growth
tooling patterns
unfinished loops
energy and attention patterns when evidence exists
```

The AI Mirror must distinguish evidence from interpretation.

Example format:

```text
Observation: 5 project folders were created this week and 0 were closed.
Evidence: project.created events in events.jsonl, no project.completed events.
Interpretation: project initiation is outpacing closure this week.
Suggested reflection: choose whether any open project should be closed, merged, or archived.
```

The AI Mirror does not enforce restrictions.

### 6.12 Monitoring and Reliability

Monitoring stack should include:

```text
Uptime Kuma
Glances
Docker health checks
disk usage alerts
failed workflow alerts
backup status alerts
service restart alerts
CPU/GPU pressure alerts
```

Alerts should route through ChatOps.

### 6.13 Backups and Recovery

Backup targets:

```text
Obsidian vault
event log
n8n workflows
Docker compose files
service configs
Paperless documents and metadata
AI runtime prompts/schemas
project context files
```

Backups should be versioned and periodically verified.

### 6.14 Migration Review System

Old LifeOS content must pass through a migration review workflow.

Every old file gets one of these outcomes:

```text
keep as-is
revise/amend into new structure
summarize into a new canonical note
merge into an existing note
archive only
delete if truly unnecessary
defer for later review
```

The migration system should create an audit trail before deletion or major rewrite.

## 7. Recommended Tools and Repositories

### 7.1 Core Tools

```text
Obsidian
Git
Docker Compose
n8n
Paperless-ngx
Uptime Kuma
Glances
Ollama
OpenCode
MCP servers
SQLite or Postgres
```

### 7.2 AI and Context Tools

```text
AnythingLLM
Open Notebook-style local research tools
modelcontextprotocol/servers
zilliztech/claude-context or equivalent codebase indexer
Memstate or equivalent structured memory system
OpenHands for sandboxed autonomous software engineering
```

### 7.3 Communication Tools

```text
Telegram bot
Discord bot
Slack app
Matrix/Synapse
ntfy
Gotify
```

The final choice should prioritize reliability, mobile usability, webhook support, and ease of self-hosting.

## 8. Workflow Definitions

### 8.1 Link Capture Workflow

```text
user sends link
→ n8n receives webhook/message
→ fetch page content
→ summarize and classify
→ create capture note or route to resource/project
→ send approval if needed
→ log event
```

### 8.2 PDF/Document Workflow

```text
file lands in paperless-import
→ Paperless OCR/import
→ document tagged/classified
→ AI generates summary note
→ note links back to Paperless document
→ approval or direct routing based on tier
→ log event
```

### 8.3 Project Creation Workflow

```text
user requests new project
→ project workspace created
→ matching vault folder created
→ templates instantiated
→ AI_Context.md generated
→ project index updated
→ event logged
→ ChatOps confirmation sent
```

### 8.4 Agent Task Workflow

```text
task requested
→ agent role selected
→ context pack generated
→ allowed paths loaded
→ action performed or approval requested
→ output validated
→ event logged
→ user notified
```

### 8.5 Maintenance Workflow

```text
scheduled trigger
→ scan vault/workspaces/event log
→ detect stale, duplicate, weak, or conflicting items
→ generate maintenance actions
→ perform low-risk approved actions
→ request approval for higher-risk changes
→ log results
```

### 8.6 Migration Workflow

```text
old LifeOS file discovered
→ inventory record created
→ classify content type
→ detect duplicates or conflicts
→ recommend keep/revise/summarize/merge/archive/delete/defer
→ apply approved action
→ log migration event
```

## 9. Migration Plan

### 9.1 Migration Principles

1. Do not bulk import old vault content into the new trusted vault.
2. Preserve the old system as an archive until migration is complete.
3. Stage old content before moving it.
4. Prefer canonical notes over duplicated historical clutter.
5. Delete only when content is clearly obsolete, duplicated, or harmful to clarity.
6. Keep an audit trail for migrated, rewritten, archived, or deleted files.

### 9.2 Migration Staging Areas

```text
/home/lifeos/99_Archive/old-user-imports/
/home/lifeos/99_Archive/migration-staging/
/home/lifeos/50_Event_Log/migration/
```

### 9.3 Migration Decision Matrix

```text
Keep as-is:
  content is already clean, accurate, current, and fits the new structure

Revise/amend:
  content is valuable but needs updated metadata, better structure, or corrected claims

Summarize:
  content is too long, messy, duplicated, or raw but contains useful meaning

Merge:
  content overlaps with an existing canonical note

Archive:
  content may have historical value but should not live in the active vault

Delete:
  content is obsolete, duplicated, generated junk, temporary, or actively misleading

Defer:
  content requires human judgment later
```

### 9.4 Migration Record Schema

Each migrated item should have a record like:

```yaml
source_path: "old/path/file.md"
destination_path: "new/path/file.md"
decision: "revise"
reason: "Useful project context but old metadata and duplicated sections"
reviewed_by: "human|agent|human+agent"
date: "2026-07-04"
event_id: "migration.item.revised:<id>"
```

## 10. Metadata Standards

### 10.1 Project Note

```yaml
type: project
status: active
domain: Systems
priority: P1
created: 2026-07-04
updated: 2026-07-04
workspace_path: "/home/lifeos/20_Workspaces/Engineering/example"
approval_tier: A3
```

### 10.2 Capture Note

```yaml
type: capture
status: unprocessed
source_type: link
captured_at: 2026-07-04T00:00:00
classification: pending
recommended_destination: pending
approval_required: true
```

### 10.3 Decision Note

```yaml
type: decision
project: Example_Project
status: accepted
date: 2026-07-04
decision_owner: user
supersedes: null
```

### 10.4 Agent Run Record

```yaml
type: agent_run
agent: Knowledge Curator
approval_tier: A2
started: 2026-07-04T00:00:00
completed: 2026-07-04T00:01:00
status: completed
input_refs: []
output_refs: []
event_ids: []
```

## 11. Implementation Phases

### Phase 0: Fresh Environment

Create the new account, base directories, shell baseline, Git identity decision, backup target, and initial vault location.

### Phase 1: Control Plane Foundation

Create the vault structure, `10_AI_UNIVERSE`, system registry, approval tiers, workflow governor, agent role definitions, templates, and schemas.

### Phase 2: Capture Pipeline

Create capture folders, basic n8n workflows, link/file intake, capture templates, and event logging.

### Phase 3: ChatOps Layer

Create the bot/channel, approval message format, webhook callbacks, notification routing, and status digest.

### Phase 4: Document Intelligence

Deploy Paperless-ngx, import folders, document tags, summary note workflow, and document-to-vault linking.

### Phase 5: Project System

Create project scaffolding workflow, project templates, `AI_Context.md`, project dashboards, and Git integration.

### Phase 6: AI Runtime and MCP

Configure AI runtime folders, prompts, MCP servers, context packs, and role-bound permissions.

### Phase 7: Maintenance Agents

Add Semantic Janitor, metadata validator, duplicate detector, stale project detector, and maintenance notification workflow.

### Phase 8: AI Mirror

Add observation logs, identity summaries, commitment-to-closure tracking, pattern reports, and evidence-based insight generation.

### Phase 9: Monitoring and Backup Reliability

Deploy Uptime Kuma, Glances, Docker health checks, backup jobs, and alert routing.

### Phase 10: Migration

Inventory old LifeOS, classify files, run staged migration, revise useful content, archive historical material, and delete truly unnecessary content only after review.

## 12. Open Design Choices

These should be decided before implementation.

1. Fresh account name.
2. Primary ChatOps channel.
3. Local-only AI vs local plus cloud APIs.
4. Preferred vector database or embedding store.
5. Whether Obsidian sync, Git, Syncthing, or another method handles vault synchronization.
6. Whether deletion during migration requires manual approval every time or only above a risk threshold.
7. Which agents are allowed direct A3 vault modification.

## 13. Source-of-Truth Rule

This document is the planning source of truth until replaced by a more formal implementation spec.

If a future plan conflicts with this document, the future plan must explicitly say what is changing and why.
