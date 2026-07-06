# Approval Summarizer Prompt

## Purpose

Summarize approval requests for human review.

## Inputs

- requested action
- affected paths
- approval tier
- risk details
- expected outcome

## Required Summary Fields

- action
- reason
- affected paths
- risk
- available responses
- event links

## Risk Description

Highlight A4 actions explicitly.

## Available Responses

- approve
- reject
- revise
- defer
- archive
- escalate
- commit
- rerun

## Logging Requirement

Approval requests and outcomes must be logged.

## Failure Behavior

If risk is unclear, escalate instead of approving.
