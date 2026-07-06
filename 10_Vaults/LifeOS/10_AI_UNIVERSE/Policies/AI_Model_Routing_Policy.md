# AI Model Routing Policy

## Strategy

Use hybrid local plus cloud AI.

## Local First

Use local models for:

- classification
- simple summarization
- tagging
- routing suggestions
- daily cleanup
- privacy-sensitive first pass
- offline work

## Cloud Assisted

Use cloud models for:

- complex reasoning
- architecture design
- migration judgment
- code review
- difficult debugging
- long synthesis
- final quality pass

## Routing Rules

- A0/A1 routine classification: local first.
- A1/A2 summaries: local first, cloud optional.
- A2/A3 project reasoning: cloud allowed when useful.
- A4 decisions: human approval required; AI may assist but cannot decide.
- medical/finance/legal: local first unless explicitly approved.
