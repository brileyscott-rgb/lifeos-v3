# LifeOS Storage Triage V2 Approval Packet

> Read-only audit. No files deleted, moved, or modified.
> All actions require explicit user approval before execution.

## Purpose

Identify where the remaining ~150GB of disk space is consumed after Storage
Triage V1 reclaimed ~3.4GB. Generate categorized cleanup recommendations
for user approval.

## Current Disk State (2026-07-08)

| Metric | Value |
|--------|-------|
| Filesystem | 176G total, 162G used, 5.4G free (97%) |
| Inodes | 12M total, 2.3M used (21%) |
| After V1 | Reclaimed ~3.4GB from Docker images, npm, pycache |

## Biggest Storage Areas

### Measurable (non-root)

| Path/Category | Size | Owner | Purpose | Risk | Recommendation |
|---------------|------|-------|---------|------|----------------|
| `/home/lifeos/70_Backups/review_zips/` | 940MB | lifeos | Archived diagnostic zips | Low | Keep 1-2 most recent, remove redundant |
| `/home/lifeos/Downloads/` | 745MB | lifeos | Downloaded installers/AppImages | Low | Remove AppImages (duplicates exist) |
| `/var/log/journal/` | 2.5GB | root | systemd journal logs | Low | Reduce retention to 2-3 days |
| `/home/lifeos/.cache/mozilla/` | 299MB | lifeos | Firefox browser cache | Low | Clear browser cache |
| `/home/lifeos/.local/bin/` | 325MB | lifeos | User binaries (opencode, agy) | Medium | Active — do not remove |
| `/home/lifeos/.opencode/` | 230MB | lifeos | OpenCode runtime + node_modules | Medium | Active — do not remove |
| `/home/lifeos/.config/mozilla/` | 162MB | lifeos | Firefox profile | Medium | Active — limit profile size |
| Docker images | 3.45GB | root | 4 active container images | High | Active — do not remove |
| Docker volumes | 5.8MB | root | 5 volumes (2 active) | High | Active — do not remove |

### Unmeasured (root-owned, estimated)

| Path/Category | Est. Size | Owner | Purpose | Risk | Recommendation |
|---------------|-----------|-------|---------|------|----------------|
| `/timeshift/snapshots/` (6 snapshots) | **100-140GB** | root | System restore points | Medium | Keep 2 most recent, delete 4 oldest |
| `/var/lib/docker/overlay2/` | ~5GB | root | Docker image layer storage | High | Active — do not remove |
| System files (/usr, /lib, /etc) | ~15GB | root | OS installation | High | Do not touch |

## Largest Files

| Size | Path | Classification | Recommendation |
|------|------|---------------|----------------|
| 980MB | `70_Backups/review_zips/lifeos_backup_20260706_220113.zip` | Old full backup | Remove if redundant with git |
| 426MB | `Downloads/GitHub-Copilot-linux-x64.AppImage` | IDE installer | Remove if installed/not needed |
| 244MB | `.local/share/opencode/opencode.db` | OpenCode database | Active — do not remove |
| 176MB | `.opencode/bin/opencode` | OpenCode binary | Active — do not remove |
| 173MB | `.local/bin/agy` | Agency agent binary | Active — do not remove |
| 168MB | `.local/bin/opencode` | OpenCode binary | Active — do not remove |
| 145MB | `Downloads/claude-desktop_amd64.deb` | App installer | Remove if installed/not needed |
| 124MB | `Applications/Obsidian-1.12.7.AppImage` | Obsidian app | KEEP — used daily |
| 124MB | `Downloads/Obsidian-1.12.7.AppImage` | DUPLICATE of Applications/ | Remove — duplicate |
| 86MB | `Downloads/obsidian_1.12.7_amd64.deb` | DUPLICATE of AppImage | Remove — different format, not needed |

## Backup/Downloads Candidates

| Category | Path | Size | Recommendation |
|----------|------|------|----------------|
| Review zips | `70_Backups/review_zips/lifeos_backup_20260706_220113.zip` | 980MB | Remove if git backup is current |
| Review zips | `70_Backups/review_zips/` other 3 zips | 505KB total | Keep — diagnostic archives |
| Downloads | `GitHub-Copilot-linux-x64.AppImage` | 426MB | Remove |
| Downloads | `claude-desktop_amd64.deb` | 145MB | Remove |
| Downloads | `Obsidian-1.12.7.AppImage` | 124MB | Remove (duplicate of Applications/) |
| Downloads | `obsidian_1.12.7_amd64.deb` | 86MB | Remove (not needed, AppImage installed) |
| Old backups | `99_Archive/migration-staging/` | 32KB | Keep — minimal |
| Old backups | `40_Services/backups/` | 4KB | Keep — minimal |

## Docker Storage Findings

| Type | Count | Size | Status |
|------|-------|------|--------|
| Images | 4 | 3.45GB | All active (status, action, n8n, chromadb) |
| Containers | 4 | 63MB | All running, healthy |
| Volumes | 5 | 5.8MB | n8n_data (active), odysseus_* (legacy) |

**Docker is NOT the disk pressure source.** After Storage Triage V1 removed 7 unused images, only active images remain. Docker images are 3.45GB of 162GB (2%).

## Timeshift Findings

**6 snapshots found** spanning Jun 15 to Jul 7, 2026:

| Snapshot | Date | Age |
|----------|------|-----|
| `2026-06-15_11-07-19` | Jun 15 | 23 days |
| `2026-07-02_19-00-01` | Jul 2 | 6 days |
| `2026-07-03_19-00-01` | Jul 3 | 5 days |
| `2026-07-05_20-00-01` | Jul 5 | 3 days |
| `2026-07-06_20-00-01` | Jul 6 | 2 days |
| `2026-07-07_22-00-01` | Jul 7 | 1 day |

**Timeshift uses rsync with hardlinks.** The first snapshot copies the entire
root filesystem. Subsequent snapshots only take space for changed files.
With the root using 162GB and Timeshift being root-owned, the 6 snapshots
collectively account for the majority of the unaccounted ~150GB.

**Actual space is difficult to measure** because Timeshift directories are
root-owned (mode 700). `sudo du` commands timed out on the massive file trees.

**Recommendation:** Keep the 2 most recent snapshots (Jul 6 and Jul 7), delete
the 4 oldest (Jun 15, Jul 2, Jul 3, Jul 5). This should reclaim **30-80GB**.

## Old User / Odysseus Findings

| Path | Size | Status |
|------|------|--------|
| `/home/bdoss08/` | 4KB | Essentially empty — old user home was cleaned up |
| `/home/bdoss08/odysseus/` | 0KB | Not present — project files removed |
| Running ChromaDB | Active container | Tied to `odysseus_chromadb-data` Docker volume |
| ChromaDB volume | In Docker | Data preserved in volume, not in old home |

**Odysseus project files have been removed.** Only the Docker volume
(`odysseus_chromadb-data`) persists. Old user home is not a disk concern.

## Caches / Node Modules / Virtual Environments

| Path | Size | Safe to Clear? |
|------|------|---------------|
| `/home/lifeos/.cache/mozilla/` | 299MB | Yes — browser cache |
| `/home/lifeos/.cache/mintinstall/` | 37MB | Yes — package manager cache |
| `/home/lifeos/.cache/opencode/` | 16MB | Yes — LLM response cache |
| `/home/lifeos/.cache/flatpak/` | 7.3MB | Risky — flatpak runtime cache |
| `/home/lifeos/.cache/mesa_shader_cache/` | 4.7MB | Yes — GPU shader cache |
| `/home/lifeos/.cache/cinnamon/` | 3.8MB | Risky — desktop session cache |
| `/home/lifeos/.cache/wallpaper/` | 2.8MB | Yes — wallpaper cache |
| `/home/lifeos/.cache/fontconfig/` | 1.2MB | Yes — font cache |
| `/home/lifeos/.npm/` | 12KB | Already cleaned in V1 |
| node_modules | 63MB | Active — do not remove (`.opencode/node_modules`) |
| venv/env dirs | None found | N/A |

## Candidate Actions

### A. Safe with Approval (HIGH impact)

| # | Action | Est. Reclaim | Command |
|---|--------|-------------|---------|
| 1 | **Delete 4 oldest Timeshift snapshots** | 30-80GB | `sudo timeshift --delete` or `sudo rm -rf /timeshift/snapshots/2026-06-15_11-07-19` etc. |
| 2 | **Remove Download installers** | 781MB | `rm /home/lifeos/Downloads/*.AppImage /home/lifeos/Downloads/*.deb` |
| 3 | **Remove old backup zip** | 980MB | `rm /home/lifeos/70_Backups/review_zips/lifeos_backup_20260706_220113.zip` |
| 4 | **Reduce journal log retention** | 2GB | Set `SystemMaxUse=500M` in `/etc/systemd/journald.conf`, run `sudo journalctl --vacuum-size=500M` |

### B. Needs Backup First (MEDIUM impact)

| # | Action | Est. Reclaim | Notes |
|---|--------|-------------|-------|
| 5 | **Export and remove old Timeshift snapshots** after verifying backup | 30-80GB | Overlaps with #1 |
| 6 | **Review 99_Archive** for redundant files | <1MB | Minimal — 32KB |

### C. Do Not Touch

| Item | Reason |
|------|--------|
| Docker volumes (`n8n_n8n_data`, `odysseus_chromadb-data`, etc.) | Active service data |
| Docker images (4 active) | Running containers depend on them |
| Running containers | Production services |
| `30_Capture/`, `50_Event_Log/` | Production data |
| `10_Vaults/` | Obsidian vault |
| `.env` files | Secrets — never touch |
| `.local/bin/opencode`, `.local/bin/agy` | Active binaries |
| `.opencode/` | OpenCode runtime |
| `.config/mozilla/` | Active Firefox profile |
| `.config/opencode/` | OpenCode config |
| `Applications/Obsidian-1.12.7.AppImage` | Daily-use app |

## Estimated Reclaimable Space

| Category | Conservative | Optimistic |
|----------|-------------|------------|
| Timeshift old snapshots (4 oldest) | 30GB | 80GB |
| Download installers | 781MB | 781MB |
| Old backup zip | 980MB | 980MB |
| Journal logs reduction | 1.5GB | 2GB |
| Browser/system caches | 300MB | 370MB |
| **TOTAL** | **~33GB** | **~84GB** |

Conservative estimate would bring disk from 97% to ~78%. Optimistic to ~49%.

## Recommended Next Command Set (DO NOT EXECUTE — APPROVAL REQUIRED)

```bash
# === STEP 1: Remove Download installers (781MB) ===
rm /home/lifeos/Downloads/GitHub-Copilot-linux-x64.AppImage
rm /home/lifeos/Downloads/claude-desktop_amd64.deb
rm /home/lifeos/Downloads/Obsidian-1.12.7.AppImage
rm /home/lifeos/Downloads/obsidian_1.12.7_amd64.deb

# === STEP 2: Remove old backup zip (980MB) ===
rm /home/lifeos/70_Backups/review_zips/lifeos_backup_20260706_220113.zip

# === STEP 3: Delete old Timeshift snapshots (30-80GB) ===
# VERIFY current snapshots first:
sudo timeshift --list
# Delete oldest 4 (keep Jul 6 and Jul 7):
sudo timeshift --delete --snapshot '2026-06-15_11-07-19'
sudo timeshift --delete --snapshot '2026-07-02_19-00-01'
sudo timeshift --delete --snapshot '2026-07-03_19-00-01'
sudo timeshift --delete --snapshot '2026-07-05_20-00-01'
# OR manually:
# sudo rm -rf /timeshift/snapshots/2026-06-15_11-07-19

# === STEP 4: Reduce journald retention (1.5-2GB) ===
sudo journalctl --vacuum-size=500M

# === STEP 5: Clear browser cache (300MB) ===
rm -rf /home/lifeos/.cache/mozilla/*

# === STEP 6: Verify ===
df -h /
python3 /home/lifeos/40_Services/scripts/lifeos_observability.py --text
```

## Stop Rule

**No cleanup happens until user explicitly approves this packet.**
All commands above are for documentation only. Execute only after explicit
written/signed approval.
