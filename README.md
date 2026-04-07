# vanish — poof. your dev junk vanished.

[![PyPI version](https://badge.fury.io/py/vanish.svg)](https://badge.fury.io/py/vanish) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Every AI-assisted coding session spins up a fresh `venv`, `node_modules`, or build cache. Multiply that by dozens of projects and your disk is quietly eaten alive. **vanish** finds every stale environment across your entire machine and reclaims the space in seconds — so you can keep vibe coding without ever worrying about storage.

```bash
pipx install vanish && vanish scan --dry-run
```

## Why vanish?

Vibe coding with Cursor, Copilot, Bolt, Windsurf, or any AI tool is incredibly productive — but it leaves behind a trail of heavyweight folders that pile up fast:

| Folder | Typical size | Created by |
|---|---|---|
| `venv` / `.venv` | 200 MB – 2 GB | Every Python project |
| `node_modules` | 300 MB – 1 GB+ | Every JS/TS project |
| `__pycache__` | 1 – 50 MB | Python runtime |
| `build` / `dist` | varies | Every build cycle |

A few weeks of vibe coding can silently consume **20–50 GB**. vanish scans your entire home directory, identifies projects you haven't touched in a while, and cleans up their heavy folders — automatically, safely, and in parallel.

## Features

- **Universal** — cleans venv, node_modules, build, dist, target, caches, or any custom folder via plugins
- **Smart staleness detection** — only cleans folders whose parent project is genuinely inactive
- **Safe** — dry-run, size caps, confirmations, archive with one-click restore, OS Trash support
- **Fast** — single-pass parallel scan; prunes heavy dirs (.git, .cache, Library, $RECYCLE.BIN, etc.)
- **Beautiful** — Rich terminal output with colored tables, progress bars, and gen-z meme notifications
- **Interactive** — optional TUI mode for visual multi-select cleanup
- **Junk Score** — see how much of each project is regenerable junk vs. source code
- **Doctor** — full project health report (disk, Git, Docker, dependency staleness)
- **Scheduled** — built-in cron / Task Scheduler support + watch/daemon mode
- **Gamified** — streaks, milestones, and levels to keep you coming back
- **CI-ready** — JSON output mode with threshold-based exit codes
- **Extensible** — plugin system for custom cleanup targets
- **Cross-platform** — macOS, Windows, Linux

## Quick Start

```bash
vanish                        # Just works. Scan + clean.
vanish scan --dry-run         # Preview what would be deleted
vanish scan --archive         # Archive instead of delete
vanish scan --trash           # Send to OS Trash (needs: pip install vanish[trash])
vanish scan --interactive     # TUI mode (needs: pip install vanish[tui])
vanish restore                # Restore from last archive
vanish stats                  # Dashboard + savings history
vanish stats --json           # Machine-readable for scripts
vanish junk-score             # Project junk vs source ratio
vanish doctor                 # Full project health report
vanish ci --max-junk 5        # CI mode: exit 1 if junk > 5 GB
vanish watch                  # Daemon mode (periodic scan)
vanish schedule daily         # Set up recurring cleanup
vanish profile                # Your gamification stats
vanish plugin list            # Show loaded plugins
vanish config generate        # Create sample config
vanish telemetry status       # Check telemetry
```

## Install

### macOS

```bash
brew install pipx
pipx ensurepath
source ~/.zshrc
pipx install "vanish[all]"
vanish scan --dry-run
```

### Windows (PowerShell)

```powershell
pip install pipx
pipx ensurepath
# Restart your terminal, then:
pipx install "vanish[all]"
vanish scan --dry-run
```

### Linux

```bash
sudo apt install pipx   # or: pip install pipx
pipx ensurepath
source ~/.bashrc
pipx install "vanish[all]"
vanish scan --dry-run
```

### Alternative (pip)

```bash
pip install "vanish[all]"
# If 'vanish' command not found, add pip's bin to PATH:
# macOS/Linux: export PATH="$HOME/.local/bin:$PATH"
# Then run: vanish scan --dry-run
```

## Privacy & Telemetry

Anonymous telemetry tracks global space savings (random ID, bytes saved, OS, version — nothing else).
- Disable: `vanish telemetry off`
- Status: `vanish telemetry status`

## License

MIT — see [LICENSE](LICENSE)

---

If this saved you GBs, please star the repo.
