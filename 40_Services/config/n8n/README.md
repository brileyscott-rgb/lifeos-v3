# n8n Config Scaffold

This directory is reserved for LifeOS n8n configuration notes, exported workflow JSON, and future reviewed settings.

Current status:

- No n8n service has been started.
- No image has been pulled or built.
- No real credentials have been configured.
- Off-machine Git backup is deferred by explicit user decision, not completed.

Future real secret files belong under `/home/lifeos/40_Services/secrets/` with restrictive permissions and must remain ignored by Git.

Before activation, the reviewed compose example values should be copied into `/home/lifeos/40_Services/secrets/n8n.env` and filled manually outside Git. The n8n image tag must also be pinned to a reviewed version or digest before any image pull or service start.

Planned workflow groups:

- watch-folder capture intake
- webhook capture intake
- approval routing
- failed workflow alerts
- event-log integration
- daily and weekly digest messages
