"""vanish - poof. your dev junk vanished."""

__version__ = "1.0.3"
__author__ = "Atul Anand"
__description__ = "Smart cleanup tool for developers — removes unused venv, node_modules, Docker images, scans Git repos, and more"

from .config import Config
from .core import CleanupEngine
from .cli import main
from .scheduler import Scheduler

__all__ = ['Config', 'CleanupEngine', 'Scheduler', 'main', '__version__']
