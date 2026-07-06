# Identity Observation Schema

## Required Fields

- `type`
- `observed_at`
- `observation`
- `evidence_refs`
- `interpretation`
- `confidence`
- `suggested_reflection`

## Required Distinctions

- observation
- evidence
- interpretation
- suggested reflection
- confidence / uncertainty
- correction path

## Prohibited Content

- enforcement rules
- restrictions
- shame language
- blocking behavior
- mandatory life rules
- diagnosis
- punitive friction

## Example YAML

```yaml
type: identity_observation
observed_at: 2026-07-04T00:00:00Z
observation: "No observation recorded yet."
evidence_refs: []
interpretation: "None."
confidence: low
suggested_reflection: "Review when evidence exists."
```
