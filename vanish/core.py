"""Core cleanup engine for vanish."""

import os
import shutil
import csv
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .config import Config
from .utils import (
    ProgressBar,
    Spinner,
    confirm_deletion,
    bytes_to_human_readable,
    check_size_threshold,
    is_path_excluded,
    create_deletion_manifest,
    validate_path_safety,
    normalize_path,
    is_protected_path
)
from .notifications import notify_completion, notify_error, notify_dry_run_complete
from .git_tools import GitAnalyzer
from .docker_tools import DockerCleaner
from .telemetry import TelemetryClient
from . import messages

console = Console()
logger = logging.getLogger(__name__)


class CleanupEngine:
    """Main cleanup engine with safety features."""

    def __init__(self, config: Config, dry_run: bool = False, archive_mode: bool = False,
                 use_trash: bool = False, sound: bool = False):
        self.config = config
        self.dry_run = dry_run or config.get("safety", {}).get("dry_run", False)
        self.archive_mode = archive_mode or config.get("safety", {}).get("backup_mode", False)
        self.use_trash = use_trash
        self.sound = sound
        self.telemetry = TelemetryClient(config)
        self.deleted_items: List[Dict[str, Any]] = []
        self.stats = {
            "folders_deleted": 0,
            "folders_size": 0,
            "bin_deleted": 0,
            "bin_size": 0,
            "errors": []
        }

    def get_size(self, path: str) -> int:
        """Calculate total size of a file or folder in bytes."""
        total_size = 0
        try:
            if os.path.isfile(path):
                total_size = os.path.getsize(path)
            elif os.path.isdir(path):
                for dirpath, dirnames, filenames in os.walk(path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        if os.path.exists(filepath):
                            try:
                                total_size += os.path.getsize(filepath)
                            except Exception:
                                pass
        except Exception as e:
            logger.debug(f"Error calculating size for {path}: {e}")
        return total_size

    _IGNORE_NAMES_FOR_MTIME = frozenset({
        '.DS_Store', 'Thumbs.db', 'ehthumbs.db',
        'ehthumbs_vista.db', 'desktop.ini', '.directory', 'Icon\r',
    })
    _IGNORE_EXTENSIONS_FOR_MTIME = frozenset({'.pyc', '.pyo'})
    _SKIP_SUBDIRS_FOR_MTIME = frozenset({
        'venv', '.venv', 'env', '.env',
        'node_modules', '__pycache__', '.eggs', '*.egg-info',
        '.git', '.hg', '.svn',
        '.tox', '.nox', '.mypy_cache', '.pytest_cache', '.ruff_cache',
        '.next', '.nuxt', 'dist', 'build', '.idea', '.vscode',
    })

    @classmethod
    def _should_ignore_file(cls, name: str) -> bool:
        if name in cls._IGNORE_NAMES_FOR_MTIME:
            return True
        _, ext = os.path.splitext(name)
        return ext.lower() in cls._IGNORE_EXTENSIONS_FOR_MTIME

    @classmethod
    def get_last_modified_time(cls, folder_path: str) -> datetime:
        """Most recent mtime of source files in a folder."""
        try:
            latest = 0.0
            found = False

            try:
                for entry in os.scandir(folder_path):
                    if entry.is_file(follow_symlinks=False):
                        if cls._should_ignore_file(entry.name):
                            continue
                        try:
                            latest = max(latest, entry.stat().st_mtime)
                            found = True
                        except OSError:
                            pass
            except PermissionError:
                pass

            if not found:
                try:
                    for entry in os.scandir(folder_path):
                        if not entry.is_dir(follow_symlinks=False):
                            continue
                        if entry.name.startswith('.') or entry.name in cls._SKIP_SUBDIRS_FOR_MTIME:
                            continue
                        try:
                            for sub in os.scandir(entry.path):
                                if sub.is_file(follow_symlinks=False):
                                    if cls._should_ignore_file(sub.name):
                                        continue
                                    try:
                                        latest = max(latest, sub.stat().st_mtime)
                                        found = True
                                    except OSError:
                                        pass
                        except PermissionError:
                            pass
                except PermissionError:
                    pass

            return datetime.fromtimestamp(latest)
        except Exception:
            return datetime.fromtimestamp(0)

    def _scan_all_targets(self, main_folder: str, targets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Single filesystem walk that discovers ALL target types at once."""
        target_map = {t["name"]: timedelta(days=t["days_threshold"]) for t in targets}
        target_names = set(target_map.keys())
        exclusions = self.config.get("exclusions", [])
        now = datetime.now()

        always_prune = {
            '.git', '.hg', '.svn', '.cache', '.m2', '.gradle',
            '.next', '.nuxt', 'Library', '.Trash',
            '$RECYCLE.BIN', 'System Volume Information',
            'lost+found', 'AppData',
        }
        prune_set = (always_prune | target_names) - target_names.intersection(always_prune)

        console.print(f"\n[bold cyan]Scanning[/bold cyan] {main_folder} for all targets...")
        spinner = Spinner(message="Scanning filesystem...")
        scanned = 0

        raw_hits: List[Tuple[str, str, str]] = []

        for root, dirs, _files in os.walk(main_folder, topdown=True, followlinks=False):
            pruned = []
            for d in list(dirs):
                full = os.path.join(root, d)
                if os.path.islink(full):
                    pruned.append(d)
                    continue
                if d in prune_set and d not in target_names:
                    pruned.append(d)
            for d in pruned:
                try:
                    dirs.remove(d)
                except ValueError:
                    pass

            found_in_this_dir = target_names.intersection(dirs)
            for tname in found_in_this_dir:
                target_path = os.path.join(root, tname)
                if is_protected_path(target_path):
                    continue
                if is_path_excluded(target_path, exclusions):
                    continue
                raw_hits.append((target_path, tname, root))
                try:
                    dirs.remove(tname)
                except ValueError:
                    pass

            scanned += 1
            if scanned % 200 == 0:
                spinner.spin()

        spinner.finish(f"Scan complete — {len(raw_hits)} potential targets found")

        if not raw_hits:
            return []

        console.print(f"[bold]Evaluating[/bold] {len(raw_hits)} candidates (parallel)...")
        spinner = Spinner(message="Evaluating staleness & sizes...")
        candidates: List[Dict[str, Any]] = []
        parent_mtime_cache: Dict[str, datetime] = {}

        def _evaluate(hit: Tuple[str, str, str]) -> Optional[Dict[str, Any]]:
            target_path, tname, parent = hit
            threshold = target_map[tname]
            cutoff = now - threshold

            if parent not in parent_mtime_cache:
                parent_mtime_cache[parent] = self.get_last_modified_time(parent)
            last_mod = parent_mtime_cache[parent]

            if last_mod >= cutoff:
                return None

            size = self.get_size(target_path)
            return {
                "path": target_path,
                "size": size,
                "last_modified": last_mod.isoformat(),
                "type": "folder",
                "target_name": tname,
            }

        workers = min(8, os.cpu_count() or 4)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_evaluate, h): h for h in raw_hits}
            done = 0
            for fut in as_completed(futures):
                done += 1
                if done % 10 == 0:
                    spinner.spin()
                result = fut.result()
                if result is not None:
                    candidates.append(result)

        spinner.finish(f"{len(candidates)} folders eligible for cleanup")

        from collections import Counter
        counts = Counter(c["target_name"] for c in candidates)
        for tname, cnt in sorted(counts.items()):
            console.print(f"   [green]✓[/green] {tname}: {cnt} folder(s)")

        return candidates

    def delete_or_archive_item(self, item: Dict[str, Any]) -> bool:
        """Delete or archive a single item."""
        path = item["path"]

        is_safe, error_msg = validate_path_safety(path)
        if not is_safe:
            console.print(f"[yellow]⚠ Skipped unsafe path:[/yellow] {error_msg}")
            self.stats["errors"].append(error_msg)
            return False

        try:
            if self.archive_mode:
                archive_folder = self.config.get("safety", {}).get("archive_folder")
                os.makedirs(archive_folder, exist_ok=True)
                archive_path = self._compute_archive_path(archive_folder, path)
                os.makedirs(os.path.dirname(archive_path), exist_ok=True)
                shutil.move(path, archive_path)
                item["archived_to"] = archive_path
                console.print(f"[blue]📦 Archived:[/blue] {path}")
            elif self.use_trash:
                from .trash import send_to_trash, is_trash_available
                if is_trash_available():
                    if send_to_trash(path):
                        console.print(f"[magenta]🗑  Trashed:[/magenta] {path} ({bytes_to_human_readable(item['size'])})")
                    else:
                        return False
                else:
                    console.print("[yellow]send2trash not installed, falling back to delete[/yellow]")
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    console.print(f"[red]🗑  Deleted:[/red] {path} ({bytes_to_human_readable(item['size'])})")
            else:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                console.print(f"[red]🗑  Deleted:[/red] {path} ({bytes_to_human_readable(item['size'])})")

            return True
        except Exception as e:
            error_msg = f"Failed to process {path}: {e}"
            console.print(f"[red]✗ {error_msg}[/red]")
            self.stats["errors"].append(error_msg)
            return False

    def cleanup_targets(self) -> int:
        """Clean up all enabled target folders."""
        targets = self.config.get_enabled_targets()
        main_folder = self.config.get("main_folder")

        all_candidates = self._scan_all_targets(main_folder, targets)

        if not all_candidates:
            console.print(f"\n{messages.get_zero_result_message()}")
            return 0

        total_size = sum(item["size"] for item in all_candidates)

        safety_config = self.config.get("safety", {})
        exceeds_threshold, warning_msg = check_size_threshold(
            total_size,
            safety_config.get("size_threshold_mb", 5000)
        )

        if exceeds_threshold:
            console.print(f"\n[yellow]{warning_msg}[/yellow]")

        mode = 'DRY RUN' if self.dry_run else ('ARCHIVE' if self.archive_mode else 'DELETE')
        table = Table(title="Scan Summary", border_style="cyan")
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")
        table.add_row("Items to process", str(len(all_candidates)))
        table.add_row("Total size", bytes_to_human_readable(total_size))
        table.add_row("Mode", mode)
        console.print(table)

        if self.dry_run:
            console.print(Panel("[bold yellow]DRY RUN[/bold yellow] — No actual deletions",
                                border_style="yellow"))
            dry_table = Table(border_style="dim")
            dry_table.add_column("Path")
            dry_table.add_column("Size", justify="right")
            for item in all_candidates:
                dry_table.add_row(item['path'], bytes_to_human_readable(item['size']))
            console.print(dry_table)

            msg = messages.get_dry_run_message(total_size / (1024 * 1024), len(all_candidates))
            console.print(f"\n{msg}")

            if self.config.get("notifications", {}).get("enabled"):
                notify_dry_run_complete(len(all_candidates), total_size / (1024 * 1024),
                                        speak_aloud=self.sound)
            elif self.sound:
                from .sounds import speak, play_fahhh
                play_fahhh()
                speak(msg)

            return 0

        confirmation_threshold = safety_config.get("require_confirmation_above_mb", 500)
        if total_size > confirmation_threshold * 1024 * 1024:
            if not confirm_deletion(
                f"\n⚠  About to {'archive' if self.archive_mode else 'delete'} "
                f"{len(all_candidates)} items ({bytes_to_human_readable(total_size)}). Continue?",
                default=False
            ):
                console.print("[yellow]Operation cancelled.[/yellow]")
                return 0

        console.print(f"\n[bold]Starting cleanup[/bold] ({min(4, len(all_candidates))} workers)...")
        progress = ProgressBar(len(all_candidates), prefix="Processing", width=40)

        successful = 0
        workers = min(4, len(all_candidates))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self.delete_or_archive_item, item): item
                       for item in all_candidates}
            for fut in as_completed(futures):
                item = futures[fut]
                try:
                    if fut.result():
                        self.deleted_items.append(item)
                        successful += 1
                        self.stats["folders_deleted"] += 1
                        self.stats["folders_size"] += item["size"]
                except Exception:
                    pass
                progress.update()

        progress.finish()

        console.print(f"\n[green]✓ Cleanup complete![/green]")
        console.print(f"   Successfully processed: {successful}/{len(all_candidates)}")
        if self.stats["errors"]:
            console.print(f"   [yellow]Errors: {len(self.stats['errors'])}[/yellow]")

        return self.stats["folders_size"]

    def clean_bin_folder(self) -> int:
        """Clean the bin/trash folder."""
        bin_folder = self.config.get("bin_folder")

        if not os.path.exists(bin_folder):
            console.print(f"\n[dim]Bin folder not found: {bin_folder}[/dim]")
            try:
                os.makedirs(bin_folder, exist_ok=True)
            except Exception:
                pass
            return 0

        console.print(f"\n[bold]Cleaning bin folder:[/bold] {bin_folder}")

        try:
            items = os.listdir(bin_folder)
            if not items:
                console.print("[green]✓ Bin folder is already empty[/green]")
                return 0

            total_size = 0
            for item in items:
                item_path = os.path.join(bin_folder, item)
                total_size += self.get_size(item_path)

            if self.dry_run:
                console.print(f"[yellow]DRY RUN:[/yellow] Would delete {len(items)} items "
                              f"({bytes_to_human_readable(total_size)})")
                return 0

            progress = ProgressBar(len(items), prefix="Cleaning bin", width=40)

            for item in items:
                item_path = os.path.join(bin_folder, item)
                try:
                    item_size = self.get_size(item_path)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    self.stats["bin_deleted"] += 1
                    self.stats["bin_size"] += item_size
                    progress.update(suffix=f"({bytes_to_human_readable(item_size)})")
                except Exception as e:
                    self.stats["errors"].append(f"Failed to delete {item}: {e}")
                    progress.update(suffix="(error)")

            progress.finish()
            console.print(f"[green]✓ Bin cleanup: {self.stats['bin_deleted']} items, "
                          f"{bytes_to_human_readable(self.stats['bin_size'])}[/green]")

        except PermissionError:
            console.print("[red]✗ Permission denied: Cannot access bin folder[/red]")
            return 0
        except Exception as e:
            console.print(f"[red]✗ Error accessing bin folder: {e}[/red]")
            return 0

        return self.stats["bin_size"]

    def _compute_archive_path(self, archive_root: str, src_path: str) -> str:
        try:
            from hashlib import sha1
            p = Path(src_path)
            abs_path = str(p.resolve())
            drive, tail = os.path.splitdrive(abs_path)
            tail = tail.lstrip("\\/")
            prefix = sha1(abs_path.encode("utf-8")).hexdigest()[:8]
            rel = os.path.join(prefix, tail) if tail else prefix
            return os.path.join(archive_root, rel)
        except Exception:
            base = os.path.basename(src_path) or "item"
            return os.path.join(archive_root, base)

    def analyze_git_repositories(self):
        """Analyze git repositories for health issues."""
        if not self.config.get("git", {}).get("enabled", True):
            return

        console.print(f"\n[bold green]Git Analysis[/bold green] — {self.config.get('main_folder')}")
        main_folder = self.config.get("main_folder")
        found_repos = False

        for root, dirs, _ in os.walk(main_folder):
            if '.git' in dirs:
                found_repos = True
                analyzer = GitAnalyzer(root)
                health = analyzer.check_health()

                stale = health.get("stale_branches", [])
                large = health.get("large_files", [])

                if stale or large:
                    console.print(f"\n[bold]Repo:[/bold] {root}")
                    if stale:
                        console.print(f"  [yellow]⚠ {len(stale)} stale branches[/yellow] (merged)")
                        for b in stale[:3]:
                            console.print(f"     - {b['name']} (last: {b['last_commit']})")
                        if len(stale) > 3:
                            console.print(f"     ...and {len(stale) - 3} more")
                    if large:
                        console.print(f"  [yellow]⚠ {len(large)} large files[/yellow]")
                        for f in large[:3]:
                            console.print(f"     - {f['rel_path']} ({f['size_mb']:.1f} MB)")

        if not found_repos:
            console.print("[dim]No git repositories found.[/dim]")

    def cleanup_docker(self):
        """Cleanup unused docker images."""
        if not self.config.get("docker", {}).get("enabled", True):
            return

        cleaner = DockerCleaner()
        if not cleaner.is_docker_available():
            return

        days = self.config.get("docker", {}).get("unused_image_days", 60)
        console.print(f"\n[bold blue]Docker[/bold blue] — images unused >{days} days")

        unused = cleaner.find_unused_images(days_threshold=days)
        if not unused:
            console.print("[green]✓ No old unused images found.[/green]")
            return

        console.print(f"Found {len(unused)} unused images:")
        for img in unused:
            console.print(f"  - {img['repo']}:{img['tag']} (Created: {img['created']})")

        if self.dry_run:
            console.print("[yellow]DRY RUN: Would prune these images.[/yellow]")
        else:
            if confirm_deletion(f"Prune {len(unused)} docker images?", default=False):
                deleted = cleaner.prune_images(unused)
                console.print(f"[green]Pruned {len(deleted)} images.[/green]")

    def save_deletion_manifest(self):
        if not self.deleted_items:
            return
        manifest_file = self.config.get("logging", {}).get("manifest_file")
        manifest = create_deletion_manifest(self.deleted_items)
        try:
            os.makedirs(os.path.dirname(manifest_file), exist_ok=True)
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            console.print(f"\n[dim]Manifest saved: {manifest_file}[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠ Could not save manifest: {e}[/yellow]")

    def log_to_csv(self):
        log_file = self.config.get("logging", {}).get("log_file")
        file_exists = os.path.exists(log_file)

        folders_size_mb = self.stats["folders_size"] / (1024 * 1024)
        bin_size_mb = self.stats["bin_size"] / (1024 * 1024)
        prev_folders_total, prev_bin_total = self._read_cumulative_totals(log_file)

        new_folders_total = prev_folders_total + folders_size_mb
        new_bin_total = prev_bin_total + bin_size_mb
        total_deleted = folders_size_mb + bin_size_mb
        cumulative_total = new_folders_total + new_bin_total

        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, 'a', newline='') as file:
                fieldnames = ['datetime', 'folders_deleted_mb', 'bin_deleted_mb', 'total_deleted_mb',
                              'cumulative_folders_mb', 'cumulative_bin_mb', 'cumulative_total_mb']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow({
                    'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'folders_deleted_mb': round(folders_size_mb, 2),
                    'bin_deleted_mb': round(bin_size_mb, 2),
                    'total_deleted_mb': round(total_deleted, 2),
                    'cumulative_folders_mb': round(new_folders_total, 2),
                    'cumulative_bin_mb': round(new_bin_total, 2),
                    'cumulative_total_mb': round(cumulative_total, 2)
                })
        except Exception as e:
            console.print(f"[yellow]⚠ Error writing to log: {e}[/yellow]")

    def _read_cumulative_totals(self, log_file: str) -> Tuple[float, float]:
        if not os.path.exists(log_file):
            return 0.0, 0.0
        try:
            with open(log_file, 'r') as file:
                reader = list(csv.DictReader(file))
                if reader:
                    last_row = reader[-1]
                    return float(last_row['cumulative_folders_mb']), float(last_row['cumulative_bin_mb'])
        except Exception:
            pass
        return 0.0, 0.0

    def run(self) -> Dict[str, Any]:
        """Run the complete cleanup process."""
        start_time = datetime.now()
        mode = 'DRY RUN' if self.dry_run else ('ARCHIVE' if self.archive_mode else 'DELETE')

        console.print(Panel(
            f"[bold]vanish[/bold] — poof. your dev junk vanished.\n"
            f"Mode: [cyan]{mode}[/cyan]  |  Root: {self.config.get('main_folder')}",
            border_style="cyan",
        ))

        targets = self.config.get_enabled_targets()
        target_summary = ", ".join(f"{t['name']} (>{t['days_threshold']}d)" for t in targets)
        console.print(f"[dim]Targets: {target_summary}[/dim]")

        try:
            self.config.ensure_directories()
            folders_size = self.cleanup_targets()
            bin_size = self.clean_bin_folder()
            self.analyze_git_repositories()
            self.cleanup_docker()

            if not self.dry_run:
                self.save_deletion_manifest()
                self.log_to_csv()

            if self.config.get("notifications", {}).get("enabled") and not self.dry_run:
                total_mb = (folders_size + bin_size) / (1024 * 1024)
                total_items = self.stats["folders_deleted"] + self.stats["bin_deleted"]
                notify_completion(total_mb, total_items, speak_aloud=self.sound)
            elif self.sound and not self.dry_run:
                total_mb = (folders_size + bin_size) / (1024 * 1024)
                total_items = self.stats["folders_deleted"] + self.stats["bin_deleted"]
                from .sounds import speak, play_fahhh
                msg = messages.get_completion_message(total_mb, total_items)
                play_fahhh()
                speak(msg)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            total_bytes = folders_size + bin_size

            if not self.dry_run:
                if total_bytes > 0:
                    try:
                        from .gamification import record_run
                        record_run(total_bytes)
                    except Exception:
                        pass
                try:
                    if total_bytes > 0:
                        self.telemetry.send_stats(total_bytes, duration)
                except Exception:
                    pass
                try:
                    self.telemetry.flush()
                except Exception:
                    pass

            total_mb = total_bytes / (1024 * 1024)
            if total_bytes > 0 and not self.dry_run:
                msg = messages.get_completion_message(total_mb,
                                                     self.stats['folders_deleted'] + self.stats['bin_deleted'],
                                                     duration)
            elif self.dry_run:
                msg = f"Dry run completed in {duration:.1f}s"
            else:
                msg = messages.get_zero_result_message()

            console.print(Panel(
                f"{msg}\n[dim]Completed in {duration:.1f}s  |  "
                f"{bytes_to_human_readable(total_bytes)} freed[/dim]",
                border_style="green" if total_bytes > 0 else "cyan",
            ))

            return {
                "success": True,
                "stats": self.stats,
                "duration_seconds": duration
            }

        except Exception as e:
            error_msg = f"Cleanup failed: {e}"
            console.print(f"\n[red bold]✗ {error_msg}[/red bold]")
            console.print(messages.get_error_message(str(e)))

            if self.config.get("notifications", {}).get("on_error"):
                notify_error(str(e), speak_aloud=self.sound)

            return {
                "success": False,
                "error": error_msg,
                "stats": self.stats
            }
