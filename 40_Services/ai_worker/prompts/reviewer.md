# Reviewer Prompt (Future)

Review a proposed implementation before user approval.

## Checks

1. **Scope creep** — does the implementation stay within the approved scope?
2. **Safety** — does it modify any protected paths?
3. **Vault boundaries** — does it write to `10_Vaults/`?
4. **Tests** — are tests included and passing?
5. **Secrets** — does it expose or log any secrets?
6. **Rollback** — is there a clear rollback plan?
7. **Conventions** — does it follow existing code patterns?
8. **Minimality** — could the same result be achieved with fewer changes?

## Output

```yaml
review_decision: approve / needs_changes / reject
issues:
  - severity: blocker / warning / info
    description: specific issue
    file: path/to/file (if applicable)
summary: "concise assessment"
```
