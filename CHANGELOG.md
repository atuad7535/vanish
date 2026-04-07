# Changelog

## [1.0.0] - 2026-04-07

### Added
- **Typer subcommand CLI** — `vanish scan`, `vanish stats`, `vanish doctor`, etc.
- **Rich terminal output** — colored tables, progress bars, panels, styled errors
- **Gen-z meme notifications** — personality-driven messages that rotate randomly
- **Interactive TUI** (`vanish scan --interactive`) — Textual-based, included in `vanish[all]`
- **Junk score analysis** (`vanish junk-score`) — regenerable vs source code ratio
- **OS Trash integration** (`vanish scan --trash`) — send2trash, included in `vanish[all]`
- **Plugin system** (`vanish plugin list/init`) — user-defined cleanup targets in `~/.vanish/plugins/`
- **Watch/daemon mode** (`vanish watch`) — periodic scanning with auto-clean option
- **Full project health report** (`vanish doctor`) — disk, Git, Docker, dependency staleness
- **CI/CD mode** (`vanish ci`) — JSON output, threshold-based exit codes
- **Gamification** (`vanish profile`) — streaks, milestones, levels
- **Shell completions** — `vanish --install-completion` (Bash, Zsh, Fish, PowerShell)
- **PyInstaller binary builds** — standalone binaries for macOS, Windows, Linux
- **Homebrew formula** — `brew install vanish`
- **Cross-platform** — macOS, Windows, Linux with CI matrix testing
- Archive + restore, Git branch analysis, Docker image pruning
- CSV dashboard with cumulative stats and trends
- Cron / Task Scheduler support
- Anonymous opt-out telemetry
