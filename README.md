# 🧹 jhadoo — one command to reclaim disk space

Smart cleanup for **any** unused files/folders in your projects. Works with Python, Node.js, Rust, Go, Java, C++, or anything you throw at it — safely.

[![PyPI version](https://badge.fury.io/py/jhadoo.svg)](https://badge.fury.io/py/jhadoo) [![Total Downloads](https://static.pepy.tech/badge/jhadoo?style=flat&units=international_system)](https://pepy.tech/projects/jhadoo) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> If this saved you GBs, please ⭐️ the repo to help others discover it.

## TL;DR

```bash
# Best UX: pipx (isolated)
pipx install jhadoo

# Preview (safe)
jhadoo --dry-run

# Clean now
jhadoo
```

## Quick Start

```bash
# Install with pip (alternative)
pip install jhadoo

# Preview (safe)
jhadoo --dry-run

# Run standard cleanup (folders)
jhadoo

# Run with Docker cleanup
jhadoo --docker

# Analyze Git Repositories
jhadoo --git-check

# Restore archived items
jhadoo --restore

# Schedule daily cleanup
jhadoo --schedule daily --archive
```

## Why jhadoo?
- **Instant value**: Runs in seconds; preview first.
- **Universal**: venv, node_modules, build/dist, caches, or custom names.
- **Safe by default**: Dry‑run, size caps, confirmations, archive/restore.
- **Fast**: Prunes heavy dirs during scan (e.g., `.git`, `node_modules`, `.venv`, `.cache`, `Library`, etc.).
- **Cross‑platform**: macOS, Windows, Linux.
- **Private**: Anonymous, opt‑out‑anytime telemetry (details below).

## What’s new (v1.2.0)
- Default scan pruning for speed (skips heavyweight dirs unless they are the target).
- Safer cross‑platform archive paths; reliable restore.
- Robust scheduling (quoted commands) on Unix/Windows.
- Telemetry hardened (no URL in code; HTTPS enforced; optional API key/HMAC).
- Git analysis and Docker cleanup are now opt‑in (off by default).

## Dashboard
View your personal savings and trends:
```bash
jhadoo --dashboard
```

## Features

- **Universal**: Works with ANY file/folder name (venv, node_modules, build, dist, target, or custom)
- **Git Analysis (opt‑in)**: Detect stale branches and large files
- **Docker Cleanup (opt‑in)**: Prune unused images (>60 days)
- **Undo/Restore**: Instantly restore archived items
- **Safe**: Dry-run mode, size caps, confirmations, archive mode
- **Scheduled**: Built-in cron/Task Scheduler integration
- **Cross-platform**: macOS, Windows, Linux
- **Smart**: Dashboard with trends, progress bars, notifications

## Configuration

```bash
# Generate config (optional)
jhadoo --generate-config

# Use a custom config
jhadoo --config jhadoo_config.json
```

## Scheduling

```bash
# Daily at 2 AM
jhadoo --schedule daily

# Weekly (Sunday 2 AM)
jhadoo --schedule weekly

# Custom cron
jhadoo --cron "0 3 * * 1"  # Monday 3 AM

# Manage
jhadoo --list-schedules
jhadoo --remove-schedule
```

## Optional features
```bash
# Git analysis (opt‑in)
jhadoo --git-check

# Docker cleanup (opt‑in)
jhadoo --docker

# Archive and later restore
jhadoo --archive
jhadoo --restore
```

## Python API

```python
from jhadoo import Config, CleanupEngine, Scheduler

# Run cleanup
config = Config()
engine = CleanupEngine(config, dry_run=True)
result = engine.run()

# Schedule
scheduler = Scheduler()
scheduler.schedule('daily', archive=True)
```

## Command Reference

```
jhadoo [OPTIONS]

Options:
  -c, --config FILE     Custom config file
  -n, --dry-run        Preview without deleting
  -a, --archive        Move to archive instead of delete
  -d, --dashboard      Show statistics
  
  --schedule FREQ     Schedule cleanup (daily/weekly/monthly/hourly)
  --cron EXPR         Custom cron expression
  --list-schedules    List scheduled tasks
  --remove-schedule   Remove scheduled tasks
  
  --generate-config   Create sample config
  -v, --version       Show version
```

## Safety

- **Size warnings**: Alerts if deletion exceeds 5GB
- **Confirmations**: Asks before deleting >500MB  
- **Exclusions**: Protect critical folders
- **System protection**: Never touches OS directories
- **Deletion manifest**: JSON log for recovery

## Privacy & Telemetry
Anonymous telemetry helps compute global space savings.
- **We collect**: Random User ID, bytes saved, OS type, jhadoo version.
- **We do NOT collect**: IPs, file names, paths, or personal data.
- **Control**:
  - Check: `jhadoo --telemetry-status`
  - Disable: `jhadoo --telemetry-off`
  - Enable: `jhadoo --telemetry-on`
- **Backend (optional, for maintainers)**:
  - Set at runtime (not in code): `TELEMETRY_URL` (HTTPS), optional `TELEMETRY_TOKEN`, `TELEMETRY_SIGNING_KEY`.
  - HTTPS enforced (http allowed only for localhost).

## File Locations

- Logs: `~/.jhadoo/cleanup_log.csv`
- Manifest: `~/.jhadoo/deletion_manifest.json`
- Archive: `~/.jhadoo_archive/`

## Install
```bash
# Recommended
pipx install jhadoo

# Or with pip
pip install jhadoo
```

## License

MIT License - see [LICENSE](LICENSE)

---

**[Examples](examples/) • [Technical Docs](jhadoo.md)**