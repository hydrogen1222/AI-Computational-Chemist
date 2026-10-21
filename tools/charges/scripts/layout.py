"""Shared output layout for every charge batch.

    ROOT/postprocess_summary/
        report.md      the one file the user opens (all methods, figures embedded)
        figures/       PNG for reading, SVG for editing
        data/          CSV tables and technical notes

Per-run working files stay in <run>/postprocess/<method>/.
Older runs wrote everything flat into postprocess_summary/; readers fall back to
that location so existing results can still be re-reported.
"""
from __future__ import annotations

from pathlib import Path

SUMMARY = "postprocess_summary"
DATA = "data"
FIGURES = "figures"
REPORT = "report.md"


def summary_dir(root: Path, create: bool = False) -> Path:
    out = Path(root) / SUMMARY
    if create:
        (out / DATA).mkdir(parents=True, exist_ok=True)
    return out


def data_dir(summary: Path) -> Path:
    return Path(summary) / DATA


def figures_dir(summary: Path, create: bool = False) -> Path:
    path = Path(summary) / FIGURES
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def find_data(summary: Path, name: str) -> Path:
    """Return data/<name>, or the legacy flat location if only that exists."""
    preferred = data_dir(summary) / name
    legacy = Path(summary) / name
    if not preferred.exists() and legacy.exists():
        return legacy
    return preferred


def figures_for(summary: Path, prefix: str) -> list[Path]:
    folder = figures_dir(summary)
    if not folder.is_dir():
        return []
    return sorted(folder.glob(prefix + "*.png"))
