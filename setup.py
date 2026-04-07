"""Setup script for vanish package."""

from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="vanish",
    version="1.0.2",
    author="Atul Anand",
    description="poof. your dev junk vanished. Smart cleanup for developers.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/atuad7535/vanish",
    project_urls={
        "Bug Tracker": "https://github.com/atuad7535/vanish/issues",
        "Documentation": "https://github.com/atuad7535/vanish#readme",
        "Source Code": "https://github.com/atuad7535/vanish",
    },
    packages=find_packages(exclude=["tests", "tests.*"]),
    package_data={"vanish": ["assets/*.mp3", "assets/*.png", "assets/*.jpg"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: System :: Filesystems",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.10",
    install_requires=[],
    extras_require={
        "tui": ["textual>=0.40"],
        "trash": ["send2trash>=1.8"],
        "notifications": [
            "winotify>=1.1; platform_system=='Windows'",
        ],
        "all": [
            "textual>=0.40",
            "send2trash>=1.8",
            "winotify>=1.1; platform_system=='Windows'",
        ],
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "flake8>=6.0",
            "mypy>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "vanish=vanish.cli:main",
        ],
    },
    keywords=[
        "cleanup", "disk-space", "file-management", "folder-cleanup",
        "development-tools", "build-cleanup", "cache-cleanup",
        "automation", "devops", "node-modules", "venv",
    ],
    include_package_data=True,
    zip_safe=False,
)
