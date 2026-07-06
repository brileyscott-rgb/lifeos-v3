# Service Activation Order

## Recommended Order

```text
Git
→ n8n
→ Telegram bot
→ Paperless-ngx
→ Qdrant
→ monitoring
→ MCP
```

## Reasoning

- Git protects text changes before automation starts.
- n8n becomes the workflow router.
- Telegram provides the approval loop.
- Paperless handles formal documents.
- Qdrant improves retrieval.
- Monitoring protects reliability.
- MCP expands agent tool access only after governance exists.
