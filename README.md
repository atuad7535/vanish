# 🧹 jhadoo — one command to reclaim disk space

[![PyPI version](https://badge.fury.io/py/jhadoo.svg)](https://badge.fury.io/py/jhadoo) [![Total Downloads](https://static.pepy.tech/badge/jhadoo?style=flat&units=international_system)](https://pepy.tech/projects/jhadoo) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

```bash
pipx install jhadoo && jhadoo --dry-run
```

## Features

- **Universal** — cleans venv, node_modules, build, dist, target, caches, or any custom folder name
- **Safe** — dry‑run, size caps, confirmations, archive with one‑click restore
- **Fast** — prunes heavy dirs (.git, .cache, Library, etc.) during scan
- **Scheduled** — built‑in cron / Task Scheduler support
- **Git Analysis** — detect stale branches & large files (`--git-check`)
- **Docker Cleanup** — prune unused images (`--docker`)
- **Dashboard** — track your savings over time (`--dashboard`)
- **Cross‑platform** — macOS, Windows, Linux
- **Private** — anonymous opt‑out‑anytime telemetry; no IPs, paths, or file names collected

## Usage

```bash
jhadoo                # clean now
jhadoo --dry-run      # safe preview
jhadoo --archive      # move instead of delete
jhadoo --restore      # undo last archive
jhadoo --dashboard    # view savings & trends
```

See [`examples/`](examples/) for config, scheduling, Python API, and more.

## Install

```bash
# Recommended
pipx install jhadoo

# Or
pip install jhadoo
```

## Privacy & Telemetry

Anonymous telemetry tracks global space savings (random ID, bytes saved, OS, version — nothing else).
- Disable: `jhadoo --telemetry-off`
- Status: `jhadoo --telemetry-status`

## License

MIT — see [LICENSE](LICENSE)

---

If this saved you GBs, please ⭐️ the repo.
