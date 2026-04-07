# vanish — Smart Cleanup Tool for Developers

## Project Overview
vanish is a Python CLI tool that scans for stale development artifacts (`node_modules`, `venv`, `__pycache__`, `build`, etc.) and removes them. It uses parallel scanning, smart staleness detection, and supports archive+restore, Git analysis, Docker cleanup, scheduling, and telemetry.

## Package Structure
```
vanish/
├── vanish/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py          # Typer subcommand CLI
│   ├── core.py         # Cleanup engine (Rich output)
│   ├── config.py       # Config management
│   ├── messages.py     # Gen-z meme notification messages
│   ├── notifications.py # Desktop notifications (cross-platform)
│   ├── junk_score.py   # Project junk score analysis
│   ├── health.py       # Full project health report
│   ├── gamification.py # Streaks, milestones, levels
│   ├── plugins.py      # Plugin system for custom targets
│   ├── watch.py        # Watch/daemon mode
│   ├── trash.py        # OS trash integration (send2trash)
│   ├── tui.py          # Interactive TUI (Textual, optional)
│   ├── git_tools.py    # Git repository analysis
│   ├── docker_tools.py # Docker image cleanup
│   ├── telemetry.py    # Anonymous telemetry
│   ├── scheduler.py    # Cron / Task Scheduler
│   ├── restore.py      # Archive restoration
│   └── utils/
│       ├── __init__.py
│       ├── os_compat.py
│       ├── progress.py  # Rich progress bars
│       └── safety.py
├── tests/
├── pyproject.toml
├── setup.py
├── README.md
├── CHANGELOG.md
├── LICENSE
└── requirements.txt
```

## CLI Commands
```
vanish                    # Scan + clean (default action)
vanish scan --dry-run     # Preview what would be deleted
vanish scan --archive     # Archive instead of delete
vanish scan --trash       # Send to OS Trash/Recycle Bin
vanish scan --interactive # Interactive TUI mode
vanish restore            # Restore from last archive
vanish stats              # Dashboard + savings history
vanish stats --json       # Machine-readable JSON
vanish junk-score         # Project junk vs source ratio
vanish doctor             # Full project health report
vanish ci --max-junk 5    # CI mode with threshold exit codes
vanish watch              # Daemon mode with periodic scanning
vanish schedule daily     # Set up recurring cleanup
vanish schedule list      # Show schedules
vanish schedule remove    # Remove schedules
vanish config generate    # Create sample config
vanish config show        # Show current config
vanish telemetry status   # Check telemetry
vanish telemetry on/off   # Toggle telemetry
vanish plugin list        # Show loaded plugins
vanish plugin init        # Create sample plugin
vanish profile            # Gamification stats (level, streak)
```

## Installation
```bash
# Recommended
pipx install vanish

# With all extras (TUI, trash integration, etc.)
pip install vanish[all]
```

## Version History
- v1.0.0: Initial release
  - Typer subcommand CLI (scan, stats, doctor, watch, ci, etc.)
  - Rich terminal output (tables, progress, panels)
  - Gen-z meme notifications
  - Interactive TUI mode (Textual)
  - Junk score analysis
  - OS trash integration (send2trash)
  - Plugin system for custom targets
  - Watch/daemon mode
  - Full project health report (doctor command)
  - CI/CD integration mode
  - Gamification (streaks, milestones, levels)
  - PyInstaller standalone binary support
  - Homebrew formula
