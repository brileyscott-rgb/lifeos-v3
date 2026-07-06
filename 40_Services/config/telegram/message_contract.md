# Telegram Message Contract

## Commands

| Command | Purpose | Capture Type | Event Type |
|---|---|---|---|---|
| `/capture <text>` | Quick capture a note | notes | chatops.telegram.capture_received |
| `/link <url> [note]` | Save a link | links | chatops.telegram.link_received |
| `/idea <text>` | Log an idea | ideas | chatops.telegram.idea_received |
| `/project <name>: <update>` | Post a project update | project_updates | chatops.telegram.project_update_received |
| `/p` | List pending captures (numbered, oldest first) | none | chatops.telegram.pending_list_requested |
| `/view <n>` | View full details of pending capture #n | none | — |
| `/a [n\|latest]` | Approve pending capture by number or latest | approved | chatops.telegram.approval_received |
| `/r [n\|latest]` | Reject pending capture by number or latest | rejected | chatops.telegram.rejection_received |
| `/list_pending` | List pending captures awaiting review (legacy) | none | chatops.telegram.pending_list_requested |
| `/approve <capture_id>` | Approve a pending capture by ID (legacy) | approved | chatops.telegram.approval_received |
| `/reject <capture_id>` | Reject a pending capture by ID (legacy) | rejected | chatops.telegram.rejection_received |
| `/status` | Request system status | none | chatops.telegram.status_requested |
| `/help` | Show available commands | none | chatops.telegram.help_requested |

## Examples

### Capture a note
```
/capture Remember to review the Qdrant backup strategy doc
```

### Save a link
```
/link https://github.com/n8n-io/n8n n8n workflow automation docs
```

### Log an idea
```
/idea We should add a weekly digest workflow that summarizes approved captures
```

### Project update
```
/project Foundation Lock-In: Telegram scaffold is done, next is BotFather setup
```

### Approve a capture
```
/approve cap_20260706_143000_telegram_link_opencode_zen_setup
```

## Future Considerations

- File/photo attachments should be accepted and routed to `30_Capture/files/` or `30_Capture/screenshots/`
- Unrecognized commands or raw text without a command prefix should route to `30_Capture/inbox/`
- Commands are case-insensitive
