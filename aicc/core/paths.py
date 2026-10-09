"""Path discovery for AICC's optional skill-management CLI."""

from __future__ import annotations

import os
from pathlib import Path


def find_collection_root(start: Path | None = None) -> Path | None:
    """Find the collection containing both procedures/ and tools/."""
    origin = (start or Path(__file__)).resolve()
    for parent in (origin, *origin.parents):
        if (parent / "procedures").is_dir() and (parent / "tools").is_dir():
            return parent
    return None


def collection_root() -> Path:
    """Return the collection containing the running CLI."""
    found = find_collection_root()
    return found or (Path.home() / ".codex" / ".auto-computational-chemist").resolve()


def skill_source_root() -> Path:
    """Return the installed skill collection, honoring explicit overrides."""
    configured = (
        os.environ.get("AICC_COLLECTION")
        or os.environ.get("AICC_SOURCE")
        or os.environ.get("CDX_SKILL_SOURCE")
    )
    return Path(configured).expanduser().resolve() if configured else collection_root()
