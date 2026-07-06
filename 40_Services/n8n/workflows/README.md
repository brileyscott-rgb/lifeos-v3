# n8n Workflows

## Status

No active workflows. All workflows listed here are **documented plans only**.

## Structure

```text
workflows/
├── README.md
├── exported/       # Future n8n workflow JSON exports (manual export + review)
└── planned/        # Documented workflow plans (not active)
```

## Activation Policy

1. Review planned workflow document.
2. Export workflow JSON from n8n editor.
3. Review JSON for secrets before committing.
4. Store credentials in n8n credential store (not in workflow JSON).
5. Test with dry-run mode first.
6. Get user approval before enabling schedule or webhook triggers.
