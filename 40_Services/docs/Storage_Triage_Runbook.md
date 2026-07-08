# LifeOS Storage Triage Runbook V1

> Safe storage triage for the LifeOS host. No Docker volumes, running
> containers, production data, or secrets removed.

## Purpose

Define safe cleanup categories and forbidden actions for LifeOS host
storage emergencies. Created after Observability V2 reported 99% disk
usage on 2026-07-08.

## Current Disk Emergency Summary (2026-07-08)

| Metric | Before | After |
|--------|--------|-------|
| Filesystem | 176G total | 176G total |
| Used | 165G (99%) | 162G (97%) |
| Free | 2.0G | 5.4G |
| Reclaimed | — | ~3.4GB |
| Inodes | 22% used | 22% used |

## What Was Audited

- Filesystem usage at each depth level
- Files over 250MB
- Root-level zip/archive files
- Cache and build artifact directories
- Docker images, containers, volumes, build cache
- Docker restart counts and health status
- Git ignored status for secret files
- Pending capture count (8)
- Event log size (28K)
- Review zip backup directory (936M → 940M after move)

## Safe Cleanup Categories

These actions are safe to perform without separate approval:

### 1. Root-level diagnostic/review zips
Move to `/home/lifeos/70_Backups/review_zips/` instead of deleting.

```bash
mkdir -p /home/lifeos/70_Backups/review_zips
mv /home/lifeos/lifeos_*.zip /home/lifeos/70_Backups/review_zips/ 2>/dev/null
```

### 2. Python __pycache__ directories
Regeneratable on next import. Safe to remove.

```bash
find /home/lifeos/40_Services -xdev -type d -name '__pycache__' -prune -exec rm -rf {} +
```

### 3. Test cache directories
`.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `htmlcov` — regeneratable.

```bash
find /home/lifeos -xdev -type d \( -name '.pytest_cache' -o -name '.mypy_cache' -o -name '.ruff_cache' -o -name 'htmlcov' \) -prune -exec rm -rf {} +
```

### 4. Coverage artifacts
`.coverage`, `coverage.xml` — regeneratable.

```bash
find /home/lifeos -xdev -type f \( -name '.coverage' -o -name 'coverage.xml' \) -delete
```

### 5. Stopped Docker containers
Only containers with status "Exited" older than 1 week.

```bash
docker container prune -f
# Or specific: docker rm <name>
```

### 6. Unused Docker images
Images with zero associated containers.

```bash
docker image prune -a -f
# Or specific: docker rmi <image:tag>
```

### 7. npm cache
Regeneratable on next `npm install`.

```bash
npm cache clean --force
```

### 8. Empty user Trash
```bash
rm -rf ~/.local/share/Trash/files/* ~/.local/share/Trash/info/*
```

## Forbidden Cleanup Categories

These actions require separate explicit approval:

| Action | Reason |
|--------|--------|
| `docker system prune --volumes` | Removes Docker volumes with data |
| `docker volume rm <name>` | May contain n8n workflows, ChromaDB data |
| `docker rm` for running containers | Production services |
| `docker rmi` for active images | Needed by running containers |
| Delete `10_Vaults/` | Obsidian vault — critical data |
| Delete `30_Capture/` | Capture files and review queue |
| Delete `50_Event_Log/` | Audit trail |
| Delete `40_Services/config/**/.env` | Service configuration |
| Delete `40_Services/n8n/.env` | n8n configuration |
| Delete `40_Services/*/docker-compose.yml` | Service definitions |
| Delete active source directories | Python source, compose files |
| Delete `.git/` | Git history |
| Delete `70_Backups/review_zips/*` | Archived backups |
| Delete old user home folders | May contain legacy data |

## Docker Cleanup Policy

| Action | Safe | Command |
|--------|------|---------|
| Remove stopped containers | Yes | `docker container prune -f` |
| Remove unused images | Yes | `docker image prune -a -f` |
| Remove build cache | Yes | `docker builder prune -f` |
| Remove volumes | **NO** | Do not run |
| Remove running containers | **NO** | Do not run |
| Remove active images | **NO** | Do not run |

### Current Docker Volumes (DO NOT REMOVE)

| Volume | Used By | Risk |
|--------|---------|------|
| `n8n_n8n_data` | `n8n_n8n_1` | n8n workflows, credentials, database |
| `compose_n8n_data` | (unused, 0B) | Empty side-effect volume from compose adoption |
| `odysseus_chromadb-data` | `odysseus_chromadb_1` | Legacy odysseus vector data |
| `odysseus_ntfy-cache` | (unused, 0B) | Legacy odysseus notification cache |
| `odysseus_searxng-data` | (unused, 0B) | Legacy odysseus search data |

## ChromaDB/Odysseus Handling Policy

ChromaDB runs from legacy odysseus compose (`/home/bdoss08/odysseus`). It is not LifeOS-owned.

**Policy:**
- Do not stop, remove, or modify the ChromaDB container
- Do not remove the `odysseus_chromadb-data` volume
- Do not remove the `odysseus_ntfy-cache` or `odysseus_searxng-data` volumes
- ChromaDB will be decommissioned only when the semantic janitor migration plan is approved

## n8n Data Handling Policy

n8n runs from legacy compose with data in `n8n_n8n_data` volume.

**Policy:**
- Do not remove `n8n_n8n_data` volume
- Do not remove `compose_n8n_data` volume (empty, side-effect of adoption; safe but leave it)
- n8n workflow data must be exported/backed up before any volume removal
- n8n adoption into unified compose is deferred

## Review Zip Handling Policy

Root-level `lifeos_*.zip` files are moved to `70_Backups/review_zips/`, not deleted.

**Policy:**
- Move, do not delete
- `70_Backups/review_zips/` is the canonical archive for diagnostic/review zips
- Do not add `70_Backups/` to git tracking
- These zips are not LifeOS operational data — they are ephemeral snapshots

## Commands Used (2026-07-08)

```bash
# Move root zips
mv lifeos_telegram_review_ux.zip 70_Backups/review_zips/
mv lifeos_safe_diagnostic_20260708T025839Z.zip 70_Backups/review_zips/

# Remove pycache
find 40_Services -xdev -type d -name '__pycache__' -prune -exec rm -rf {} +

# Remove stopped containers
docker rm aiclient2api strange_volhard beautiful_saha

# Remove unused images
docker rmi n8nio/n8n:latest-debian justlikemaki/aiclient-2-api:latest \
  cloudflare/cloudflared:latest python:3.12-alpine \
  n8n_lifeos-action-api:latest status_api_lifeos-status-api:latest \
  hello-world:latest

# Remove dangling images
docker image prune -f

# Clean npm cache
npm cache clean --force
```

## Future Cleanup Candidates Requiring Approval

| Item | Size | Risk | Why Deferred |
|------|------|------|-------------|
| `Downloads/GitHub-Copilot-linux-x64.AppImage` | 425MB | Low | May still be needed |
| `70_Backups/review_zips/` cleanup | 940MB | Medium | Contains backup snapshots |
| `.cache/mozilla` | 298MB | Low | Firefox cache, browser session active |
| `.cache/mintinstall` | 37MB | Low | Mint package manager cache |
| `.cache/opencode` | 16MB | Medium | OpenCode runtime cache |
| `.cache/mesa_shader_cache` | 4.7MB | Low | GPU shader cache |
| `.local/bin` | 325MB | Low | User binaries |
| `.opencode/node_modules` | 63MB | Low | OpenCode dependencies |
| `odysseus_ntfy-cache` volume | 0B | Low | Empty, but odysseus removal is gated |
| `odysseus_searxng-data` volume | 0B | Low | Empty, but odysseus removal is gated |
| `compose_n8n_data` volume | 0B | Low | Empty side-effect; leave for n8n migration |

## Recommended Thresholds

| Level | Usage | Action |
|-------|-------|--------|
| Normal | < 85% | No action |
| Warning | 85–90% | Review large files, plan cleanup |
| High | 90–95% | Execute safe cleanup from this runbook |
| Critical | > 95% | Safe cleanup + defer new service activation |
| Emergency | > 98% | Safe cleanup + escalate non-essential removals for approval |
