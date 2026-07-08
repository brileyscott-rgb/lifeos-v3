# LifeOS OpenHands Sandbox Workspace

> This directory holds isolated workspaces for OpenHands sandboxed agent experiments.
> OpenHands may read and write within `workspaces/` but has no access to
> production LifeOS data paths, the vault, secrets, SSH keys, or the Docker socket.

## Directory Structure

```
60_Sandboxes/OpenHands/
├── README.md          # This file
├── workspaces/        # Per-experiment isolated workspaces
│   └── .gitkeep
└── exports/           # Reviewed output ready for LifeOS integration
    └── .gitkeep
```

## Workspace Rules

1. Each experiment gets its own subdirectory under `workspaces/`.
2. Workspaces may contain cloned repos, generated code, test files, reports.
3. No LifeOS production data may be copied into workspaces.
4. No secrets, API keys, tokens, or credentials in workspaces.
5. Workspaces are disposable — export valuable output to `exports/` before deleting.

## Export Process

Before any output enters LifeOS production:

1. Generate a patch (`git diff`), report (Markdown), or artifact file.
2. Save to `exports/<experiment>/`.
3. Review with human or OpenCode.
4. Apply to production only after review and tests pass.

## Files to Ignore

Add to `.gitignore`:
```
60_Sandboxes/OpenHands/workspaces/*
!60_Sandboxes/OpenHands/workspaces/.gitkeep
60_Sandboxes/OpenHands/exports/*
!60_Sandboxes/OpenHands/exports/.gitkeep
```
