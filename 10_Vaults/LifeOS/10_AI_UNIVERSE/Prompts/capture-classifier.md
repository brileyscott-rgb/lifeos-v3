# Capture Classifier Prompt

## Purpose

Classify raw captures and propose destinations.

## Inputs

- raw capture content
- source metadata
- available destination taxonomy

## Allowed Outputs

- classification
- summary
- recommended destination
- approval requirement
- event-log suggestion

## Approval Behavior

May write A1 summaries and A2 staging files only when permitted by path and tier.

## Logging Requirement

Every meaningful classification action must produce or reference an event.

## Failure Behavior

Leave source untouched, log failure, request review.
