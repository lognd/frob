"""`.frob/vet.db` verdict cache: content-addressed by artifact hash
(docs/modules/vet.md "Verdict cache" + "Mechanics"). Reused for VET003 escalation
diffs, which need the MOST RECENTLY STORED verdict for a (ecosystem, name)
regardless of hash -- a version bump changes the hash on purpose.

sqlite, same posture as `_registry.py`'s publish-date cache: unreadable db
never crashes the scan, it just means "no prior verdict" (cold cache).
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from frob.logging import get_logger
from frob.vet._models import PackageVerdict

_log = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS verdicts (
    ecosystem TEXT NOT NULL,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    artifact_hash TEXT NOT NULL,
    capabilities TEXT NOT NULL,
    signals TEXT NOT NULL,
    stored_at REAL NOT NULL,
    PRIMARY KEY (ecosystem, name, artifact_hash)
)
"""


def _connect(db_path: Path) -> sqlite3.Connection | None:
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.execute(_SCHEMA)
        return conn
    except sqlite3.Error as exc:
        _log.warning("vet: cache %s unreadable/uninitializable: %s", db_path, exc)
        return None


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
def _store_verdict(db_path: Path, verdict: PackageVerdict) -> None:
    """Persist `verdict`, content-addressed by (ecosystem, name, artifact_hash).
    Best-effort: a write failure is logged, never raised (the scan already
    has its answer in memory)."""
    if not verdict.artifact_hash:
        _log.debug("vet: skipping cache store for %s (no artifact hash)", verdict.name)
        return
    conn = _connect(db_path)
    if conn is None:
        return
    try:
        _insert_verdict(conn, verdict)
        conn.commit()
        _log.debug(
            "vet: stored verdict for %s/%s@%s",
            verdict.ecosystem,
            verdict.name,
            verdict.version,
        )
    except sqlite3.Error as exc:
        _log.warning("vet: could not store verdict for %s: %s", verdict.name, exc)
    finally:
        conn.close()


def _insert_verdict(conn: sqlite3.Connection, verdict: PackageVerdict) -> None:
    """Content-addressed INSERT OR REPLACE of one verdict row (no commit)."""
    conn.execute(
        "INSERT OR REPLACE INTO verdicts "
        "(ecosystem, name, version, artifact_hash, capabilities, "
        "signals, stored_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            verdict.ecosystem,
            verdict.name,
            verdict.version,
            verdict.artifact_hash,
            json.dumps(sorted(verdict.capabilities)),
            json.dumps(list(verdict.signals)),
            time.time(),
        ),
    )


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
def _latest_verdict(db_path: Path, ecosystem: str, name: str) -> PackageVerdict | None:
    """The most recently stored verdict for (ecosystem, name), any hash --
    used as the "previous version" baseline for VET003 escalation diffs."""
    if not db_path.exists():
        return None
    conn = _connect(db_path)
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT name, version, ecosystem, artifact_hash, capabilities, signals "
            "FROM verdicts WHERE ecosystem = ? AND name = ? "
            "ORDER BY stored_at DESC LIMIT 1",
            (ecosystem, name),
        ).fetchone()
    except sqlite3.Error as exc:
        _log.warning("vet: cache read failed for %s/%s: %s", ecosystem, name, exc)
        return None
    finally:
        conn.close()
    if row is None:
        return None
    db_name, version, db_ecosystem, artifact_hash, capabilities_json, signals_json = row
    return PackageVerdict(
        name=db_name,
        version=version,
        ecosystem=db_ecosystem,
        artifact_hash=artifact_hash,
        capabilities=frozenset(json.loads(capabilities_json)),
        signals=tuple(json.loads(signals_json)),
    )


__all__ = ["_latest_verdict", "_store_verdict"]
