"""Core cleanup functionality with all safety features."""

import os
import shutil
import csv
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional

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

# Configure logging
logging.basicConfig(
    format='%(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class CleanupEngine:
    """Main cleanup engine with safety features."""
    
    def __init__(self, config: Config, dry_run: bool = False, archive_mode: bool = False):
        """Initialize cleanup engine.
        
        Args:
            config: Configuration object
            dry_run: If True, only preview without deleting
            archive_mode: If True, move to archive instead of deleting
        """
        self.config = config
        self.dry_run = dry_run or config.get("safety", {}).get("dry_run", False)
        self.archive_mode = archive_mode or config.get("safety", {}).get("backup_mode", False)
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
                            except:
                                pass  # Skip files we can't access
        except Exception as e:
            logger.debug(f"Error calculating size for {path}: {e}")
        return total_size
    
    # OS/editor metadata FILES that get auto-updated and should never
    # count as real developer activity when checking staleness.
    _IGNORE_NAMES_FOR_MTIME = frozenset({
        '.DS_Store',                                # macOS Finder metadata
        'Thumbs.db', 'ehthumbs.db',                 # Windows thumbnail caches
        'ehthumbs_vista.db',                        # older Windows
        'desktop.ini',                              # Windows folder config
        '.directory',                               # KDE folder metadata
        'Icon\r',                                   # macOS custom folder icon
    })
    _IGNORE_EXTENSIONS_FOR_MTIME = frozenset({
        '.pyc', '.pyo',                             # Python bytecode
    })

    # Subdirectories that should NOT be checked when looking one level
    # deeper for recent source-file activity (they are either targets
    # themselves, VCS internals, or tool-generated caches).
    _SKIP_SUBDIRS_FOR_MTIME = frozenset({
        'venv', '.venv', 'env', '.env',
        'node_modules', '__pycache__', '.eggs', '*.egg-info',
        '.git', '.hg', '.svn',
        '.tox', '.nox', '.mypy_cache', '.pytest_cache', '.ruff_cache',
        '.next', '.nuxt', 'dist', 'build',
        '.idea', '.vscode',
    })

    @classmethod
    def _should_ignore_file(cls, name: str) -> bool:
        """True if *name* is an OS/editor metadata artifact."""
        if name in cls._IGNORE_NAMES_FOR_MTIME:
            return True
        _, ext = os.path.splitext(name)
        return ext.lower() in cls._IGNORE_EXTENSIONS_FOR_MTIME

    @classmethod
    def get_last_modified_time(cls, folder_path: str) -> datetime:
        """Most recent mtime of *source* files in a folder.

        Phase 1: checks immediate children (files only, ignoring OS
        metadata like .DS_Store and bytecode .pyc).
        Phase 2 (fallback): if Phase 1 found nothing, scans one level
        deeper into visible, non-artifact subdirectories.  This handles
        projects whose root has no files — only dirs like ``src/``.
        Phase 3 (final fallback): if still nothing, returns epoch so the
        target is always considered stale.

        The previous approach fell back to ``os.path.getmtime(folder)``
        which is unreliable: on macOS it is bumped by .DS_Store creation,
        on Windows by thumbnail cache writes, and on Linux by Tracker/
        Baloo indexing touching directory entries.
        """
        try:
            latest = 0.0
            found = False

            # --- Phase 1: immediate files ---
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

            # --- Phase 2: one level deeper into visible subdirs ---
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

            # --- Phase 3: nothing found → treat as stale (epoch) ---
            return datetime.fromtimestamp(latest)
        except Exception:
            return datetime.fromtimestamp(0)
    
    def _scan_all_targets(self, main_folder: str, targets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Single filesystem walk that discovers ALL target types at once.

        Instead of walking the entire tree N times (once per target), this
        walks once and checks every directory name against all enabled targets.
        Size calculations are then parallelized across threads.
        """
        target_map = {t["name"]: timedelta(days=t["days_threshold"]) for t in targets}
        target_names = set(target_map.keys())
        exclusions = self.config.get("exclusions", [])
        now = datetime.now()

        # Directories that are always pruned during walk (unless they are a target).
        # Covers macOS, Windows, and Linux system/cache dirs that are heavy and
        # will never contain developer project targets.
        always_prune = {
            '.git', '.hg', '.svn',                          # VCS internals
            '.cache', '.m2', '.gradle',                     # build caches
            '.next', '.nuxt',                               # JS framework outputs
            'Library', '.Trash',                            # macOS
            '$RECYCLE.BIN', 'System Volume Information',    # Windows
            'lost+found',                                   # Linux / ext4
            'AppData',                                      # Windows user cache
        }
        prune_set = (always_prune | target_names) - target_names.intersection(always_prune)

        logger.info(f"\n🔍 Scanning {main_folder} for all targets in a single pass...")
        spinner = Spinner(message="Scanning filesystem...")
        scanned = 0

        # Phase 1: walk once, collect raw hits (path + target_name + parent)
        raw_hits: List[Tuple[str, str, str]] = []

        for root, dirs, _files in os.walk(main_folder, topdown=True, followlinks=False):
            pruned = []
            for d in list(dirs):
                full = os.path.join(root, d)
                if os.path.islink(full):
                    pruned.append(d)
                    continue
                # Prune heavy dirs, but NOT if they are a target we're scanning for
                if d in prune_set and d not in target_names:
                    pruned.append(d)
            for d in pruned:
                try:
                    dirs.remove(d)
                except ValueError:
                    pass

            # Check every target in one shot
            found_in_this_dir = target_names.intersection(dirs)
            for tname in found_in_this_dir:
                target_path = os.path.join(root, tname)
                if is_protected_path(target_path):
                    continue
                if is_path_excluded(target_path, exclusions):
                    continue
                raw_hits.append((target_path, tname, root))
                # Don't descend into the matched target directory
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

        # Phase 2: check parent staleness + compute sizes in parallel
        logger.info(f"⚡ Evaluating {len(raw_hits)} candidates (parallel)...")
        spinner = Spinner(message="Evaluating staleness & sizes...")
        candidates: List[Dict[str, Any]] = []

        # Cache parent mtime so we don't re-walk the same parent for venv + .venv
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

        # Per-target summary
        from collections import Counter
        counts = Counter(c["target_name"] for c in candidates)
        for tname, cnt in sorted(counts.items()):
            logger.info(f"   ✓ {tname}: {cnt} folder(s)")

        return candidates

    def delete_or_archive_item(self, item: Dict[str, Any]) -> bool:
        """Delete or archive a single item.
        
        Returns:
            True if successful, False otherwise
        """
        path = item["path"]
        
        is_safe, error_msg = validate_path_safety(path)
        if not is_safe:
            logger.warning(f"⚠️  Skipped unsafe path: {error_msg}")
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
                logger.info(f"📦 Archived: {path} → {archive_path}")
            else:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                logger.info(f"🗑️  Deleted: {path} ({bytes_to_human_readable(item['size'])})")
            
            return True
        except Exception as e:
            error_msg = f"Failed to process {path}: {e}"
            logger.error(f"❌ {error_msg}")
            self.stats["errors"].append(error_msg)
            return False
    
    def cleanup_targets(self) -> int:
        """Clean up all enabled target folders.

        Scans the filesystem once for all targets, evaluates eligibility
        and sizes in parallel, then performs deletions in parallel.
        """
        targets = self.config.get_enabled_targets()
        main_folder = self.config.get("main_folder")

        all_candidates = self._scan_all_targets(main_folder, targets)
        
        if not all_candidates:
            logger.info("\n✓ No folders to clean up!")
            return 0
        
        total_size = sum(item["size"] for item in all_candidates)
        
        safety_config = self.config.get("safety", {})
        exceeds_threshold, warning_msg = check_size_threshold(
            total_size,
            safety_config.get("size_threshold_mb", 5000)
        )
        
        if exceeds_threshold:
            logger.warning(f"\n{warning_msg}")
        
        logger.info(f"\n📊 Summary:")
        logger.info(f"   Items to process: {len(all_candidates)}")
        logger.info(f"   Total size: {bytes_to_human_readable(total_size)}")
        logger.info(f"   Mode: {'DRY RUN' if self.dry_run else ('ARCHIVE' if self.archive_mode else 'DELETE')}")
        
        if self.dry_run:
            logger.info(f"\n{'='*60}")
            logger.info("DRY RUN - No actual deletions will be performed")
            logger.info(f"{'='*60}")
            for item in all_candidates:
                logger.info(f"  Would delete: {item['path']} ({bytes_to_human_readable(item['size'])})")
            
            if self.config.get("notifications", {}).get("enabled"):
                notify_dry_run_complete(len(all_candidates), total_size / (1024 * 1024))
            
            return 0
        
        confirmation_threshold = safety_config.get("require_confirmation_above_mb", 500)
        if total_size > confirmation_threshold * 1024 * 1024:
            if not confirm_deletion(
                f"\n⚠️  About to {'archive' if self.archive_mode else 'delete'} "
                f"{len(all_candidates)} items ({bytes_to_human_readable(total_size)}). Continue?",
                default=False
            ):
                logger.info("❌ Operation cancelled by user.")
                return 0
        
        # Parallel deletion
        logger.info(f"\n🚀 Starting cleanup ({min(4, len(all_candidates))} workers)...")
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
        
        logger.info(f"\n✅ Cleanup complete!")
        logger.info(f"   Successfully processed: {successful}/{len(all_candidates)}")
        if self.stats["errors"]:
            logger.info(f"   Errors: {len(self.stats['errors'])}")
        
        return self.stats["folders_size"]
    
    def clean_bin_folder(self) -> int:
        """Clean the bin/trash folder.
        
        Returns:
            Total size deleted in bytes
        """
        bin_folder = self.config.get("bin_folder")
        
        if not os.path.exists(bin_folder):
            logger.info(f"\n📁 Bin folder not found: {bin_folder}")
            logger.info("Creating bin folder for future use...")
            try:
                os.makedirs(bin_folder, exist_ok=True)
                logger.info(f"✓ Created: {bin_folder}")
            except Exception as e:
                logger.error(f"❌ Could not create bin folder: {e}")
            return 0
        
        logger.info(f"\n🗑️  Cleaning bin folder: {bin_folder}")
        
        try:
            items = os.listdir(bin_folder)
            if not items:
                logger.info("✓ Bin folder is already empty")
                return 0
            
            # Calculate total size first
            total_size = 0
            for item in items:
                item_path = os.path.join(bin_folder, item)
                total_size += self.get_size(item_path)
            
            if self.dry_run:
                logger.info(f"DRY RUN: Would delete {len(items)} items ({bytes_to_human_readable(total_size)})")
                return 0
            
            # Delete items
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
                    error_msg = f"Failed to delete {item}: {e}"
                    self.stats["errors"].append(error_msg)
                    progress.update(suffix="(error)")
            
            progress.finish()
            logger.info(f"✅ Bin cleanup complete: {self.stats['bin_deleted']} items, "
                  f"{bytes_to_human_readable(self.stats['bin_size'])}")
            
        except PermissionError:
            logger.error("❌ Permission denied: Cannot access bin folder")
            logger.error("Note: Some system trash folders have restricted access.")
            return 0
        except Exception as e:
            logger.error(f"❌ Error accessing bin folder: {e}")
            return 0
        
        return self.stats["bin_size"]

    def _compute_archive_path(self, archive_root: str, src_path: str) -> str:
        """Compute a safe archive destination path across platforms.
        
        On Windows, avoid using '/' root; drop drive letter and prefix a short hash to prevent collisions.
        On Unix, build relative to '/' without leading slash.
        """
        try:
            from hashlib import sha1
            p = Path(src_path)
            # Normalize absolute path
            abs_path = str(p.resolve())
            # Drive handling (Windows)
            drive, tail = os.path.splitdrive(abs_path)
            tail = tail.lstrip("\\/")  # remove leading separators
            # Short hash prefix for uniqueness and to avoid very long paths
            prefix = sha1(abs_path.encode("utf-8")).hexdigest()[:8]
            rel = os.path.join(prefix, tail) if tail else prefix
            return os.path.join(archive_root, rel)
        except Exception:
            # Fallback: join filename with hash
            base = os.path.basename(src_path) or "item"
            return os.path.join(archive_root, base)

    def analyze_git_repositories(self):
        """Analyze git repositories for health issues."""
        if not self.config.get("git", {}).get("enabled", True):
            return

        logger.info(f"\n🌿 Analyzing Git repositories in {self.config.get('main_folder')}...")
        main_folder = self.config.get("main_folder")
        found_repos = False
        
        for root, dirs, _ in os.walk(main_folder):
            if '.git' in dirs:
                found_repos = True
                analyzer = GitAnalyzer(root)
                health = analyzer.check_health()
                
                # Report findings
                stale = health.get("stale_branches", [])
                large = health.get("large_files", [])
                
                if stale or large:
                    logger.info(f"\nRepo: {root}")
                    if stale:
                        logger.info(f"  ⚠️  {len(stale)} stale branches found (merged into main/master)")
                        for b in stale[:3]: # Show first 3
                            logger.info(f"     - {b['name']} (last commit: {b['last_commit']})")
                        if len(stale) > 3:
                            logger.info(f"     ...and {len(stale)-3} more")
                            
                    if large:
                        logger.info(f"  ⚠️  {len(large)} large files found")
                        for f in large[:3]:
                            logger.info(f"     - {f['rel_path']} ({f['size_mb']:.1f} MB)")

        if not found_repos:
            logger.info("No git repositories found.")

    def cleanup_docker(self):
        """Cleanup unused docker images."""
        if not self.config.get("docker", {}).get("enabled", True):
            return
            
        cleaner = DockerCleaner()
        if not cleaner.is_docker_available():
            return
            
        days = self.config.get("docker", {}).get("unused_image_days", 60)
        logger.info(f"\n🐳 Checking for Docker images unused for >{days} days...")
        
        unused = cleaner.find_unused_images(days_threshold=days)
        if not unused:
            logger.info("✓ No old unused images found.")
            return
            
        logger.info(f"Found {len(unused)} unused images:")
        for img in unused:
            logger.info(f"  - {img['repo']}:{img['tag']} (Created: {img['created']})")
            
        if self.dry_run:
            logger.info("DRY RUN: Would prune these images.")
        else:
            if confirm_deletion(f"Prune {len(unused)} docker images?", default=False):
                deleted = cleaner.prune_images(unused)
                logger.info(f"🗑️  Pruned {len(deleted)} images.")
    
    def save_deletion_manifest(self):
        """Save manifest of deleted items for potential undo."""
        if not self.deleted_items:
            return
        
        manifest_file = self.config.get("logging", {}).get("manifest_file")
        manifest = create_deletion_manifest(self.deleted_items)
        
        try:
            os.makedirs(os.path.dirname(manifest_file), exist_ok=True)
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            logger.info(f"\n📝 Deletion manifest saved: {manifest_file}")
        except Exception as e:
            logger.warning(f"⚠️  Could not save deletion manifest: {e}")
    
    def log_to_csv(self):
        """Log the deletion stats to CSV."""
        log_file = self.config.get("logging", {}).get("log_file")
        file_exists = os.path.exists(log_file)
        
        folders_size_mb = self.stats["folders_size"] / (1024 * 1024)
        bin_size_mb = self.stats["bin_size"] / (1024 * 1024)
        
        # Get previous cumulative totals
        prev_folders_total, prev_bin_total = self._read_cumulative_totals(log_file)
        
        # Calculate new cumulative totals
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
            
            logger.info(f"\n📊 Log updated: {log_file}")
            logger.info(f"   Cumulative totals:")
            logger.info(f"   • Folders: {round(new_folders_total, 2)} MB")
            logger.info(f"   • Bin: {round(new_bin_total, 2)} MB")
            logger.info(f"   • Total: {round(cumulative_total, 2)} MB")
            
        except Exception as e:
            logger.warning(f"⚠️  Error writing to log file: {e}")
    
    def _read_cumulative_totals(self, log_file: str) -> Tuple[float, float]:
        """Read the last cumulative totals from the CSV."""
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
        """Run the complete cleanup process.
        
        Returns:
            Dictionary with cleanup statistics
        """
        start_time = datetime.now()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🧹 jhadoo - Smart Cleanup Tool")
        logger.info(f"{'='*60}")
        logger.info(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else ('ARCHIVE' if self.archive_mode else 'DELETE')}")
        logger.info(f"Scan root: {self.config.get('main_folder')}")
        targets = self.config.get_enabled_targets()
        target_summary = ", ".join(f"{t['name']} (>{t['days_threshold']}d)" for t in targets)
        logger.info(f"Targets: {target_summary}")
        logger.info(f"Git analysis: {'ON' if self.config.get('git', {}).get('enabled', False) else 'OFF'}  |  Docker cleanup: {'ON' if self.config.get('docker', {}).get('enabled', False) else 'OFF'}")
        
        try:
            # Ensure directories exist
            self.config.ensure_directories()
            
            # Task 1: Clean up target folders
            folders_size = self.cleanup_targets()
            
            # Task 2: Clean bin folder
            bin_size = self.clean_bin_folder()
            
            # Task 3: Git Analysis (Info only)
            self.analyze_git_repositories()
            
            # Task 4: Docker Cleanup
            self.cleanup_docker()
            
            # Save deletion manifest
            if not self.dry_run:
                self.save_deletion_manifest()
                self.log_to_csv()
            
            # Send notification
            if self.config.get("notifications", {}).get("enabled") and not self.dry_run:
                total_mb = (folders_size + bin_size) / (1024 * 1024)
                total_items = self.stats["folders_deleted"] + self.stats["bin_deleted"]
                notify_completion(total_mb, total_items)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            total_bytes = folders_size + bin_size

            # Send anonymous telemetry
            if not self.dry_run:
                try:
                    if total_bytes > 0:
                        self.telemetry.send_stats(total_bytes, duration)
                except Exception:
                    pass

            # Wait for telemetry to finish before process exits
            try:
                self.telemetry.flush()
            except Exception:
                pass

            logger.info(f"\n{'='*60}")
            logger.info(f"✅ Cleanup completed in {duration:.1f} seconds  |  Space saved: {bytes_to_human_readable(total_bytes)}")
            logger.info(f"{'='*60}")
            logger.info(f"\n📈 Insights:")
            logger.info(f"   • Total freed this run: {bytes_to_human_readable(total_bytes)}")
            logger.info(f"   • Items processed: {self.stats['folders_deleted']} folders, {self.stats['bin_deleted']} bin entries")
            if self.config.get('telemetry', {}).get('enabled', True):
                logger.info("   • Anonymous telemetry: ENABLED (use `jhadoo --telemetry-off` to disable)")
            else:
                logger.info("   • Anonymous telemetry: DISABLED (enable with `jhadoo --telemetry-on`)")
            
            return {
                "success": True,
                "stats": self.stats,
                "duration_seconds": duration
            }
            
        except Exception as e:
            error_msg = f"Cleanup failed: {e}"
            logger.error(f"\n❌ {error_msg}")
            
            if self.config.get("notifications", {}).get("on_error"):
                notify_error(str(e))
            
            return {
                "success": False,
                "error": error_msg,
                "stats": self.stats
            }



