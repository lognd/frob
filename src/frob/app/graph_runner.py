"""CLI wiring for `frob graph build|query|why` (docs/modules/graph.md)."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "cache.db"


# frob:doc docs/modules/app.md#runners
def run(cfg: AppConfig) -> None:
    """Dispatch to build/query/why based on `cfg.graph_command`."""
    root = (cfg.graph_path or Path(".")).resolve()
    cache = root / _CACHE_REL

    if cfg.graph_command == "build":
        _run_build(root, cache)
    elif cfg.graph_command == "query":
        _run_query(root, cache, cfg)
    elif cfg.graph_command == "why":
        _run_why(root, cache, cfg)
    else:
        _log.error("usage: frob graph <build|query|why> ...")
        sys.exit(1)


def _run_build(root: Path, cache: Path) -> None:
    from frob.graph import build_graph

    result = build_graph(root, cache)
    if result.is_err:
        _log.error("graph build failed: %s", result.danger_err)
        sys.exit(1)
    snapshot = result.danger_ok
    _log.info(
        "graph build: files parsed=%d cache_hits=%d symbols=%d edges=%d malformed=%d",
        snapshot.stats.parsed,
        snapshot.stats.cache_hits,
        len(snapshot.symbols),
        len(snapshot.edges),
        len(snapshot.malformed),
    )


def _load_snapshot(root: Path, cache: Path):
    from frob.graph import build_graph, load_graph

    loaded = load_graph(cache)
    if loaded.is_ok:
        return loaded
    _log.info("graph: cache stale/missing, building: %s", loaded.danger_err)
    return build_graph(root, cache)


def _query_json_payload(ref: str, record, outgoing, incoming) -> dict:  # noqa: ANN001
    """The `--json` payload for `frob graph query`."""
    return {
        "ref": ref,
        "kind": record.kind.value,
        "public": record.public,
        "span": list(record.span),
        "digests": record.digests.model_dump(),
        "edges_from": [e.model_dump() for e in outgoing],
        "edges_to": [e.model_dump() for e in incoming],
    }


def _render_query_lines(ref: str, record, outgoing, incoming) -> list[str]:  # noqa: ANN001
    """Human-readable `frob graph query` report lines."""
    lines = [
        f"{ref}  kind={record.kind.value} public={record.public} "
        f"span={record.span[0]}-{record.span[1]}",
        f"  sig={record.digests.sig[:12]} body={record.digests.body[:12]} "
        f"doc={record.digests.doc[:12]}",
        "edges from:",
    ]
    for e in outgoing:
        lines.append(f"  {e.kind.value} -> {e.target}  ({e.origin})")
    lines.append("edges to:")
    for e in incoming:
        lines.append(f"  {e.src} -> {e.kind.value}  ({e.origin})")
    return lines


def _run_query(root: Path, cache: Path, cfg: AppConfig) -> None:
    from frob.graph import edges_from, edges_to, resolve

    if cfg.graph_ref is None:
        _log.error("frob graph query requires <ref>")
        sys.exit(1)

    loaded = _load_snapshot(root, cache)
    if loaded.is_err:
        _log.error("graph unavailable: %s", loaded.danger_err)
        sys.exit(1)
    snapshot = loaded.danger_ok

    resolved = resolve(snapshot, cfg.graph_ref)
    if resolved.is_err:
        _log.error("graph query: %s: %s", cfg.graph_ref, resolved.danger_err)
        sys.exit(1)
    record = resolved.danger_ok
    outgoing = edges_from(snapshot, cfg.graph_ref)
    incoming = edges_to(snapshot, cfg.graph_ref)

    if cfg.graph_json:
        import json

        payload = _query_json_payload(cfg.graph_ref, record, outgoing, incoming)
        _log.info(json.dumps(payload, indent=2))
        return

    _log.info("\n".join(_render_query_lines(cfg.graph_ref, record, outgoing, incoming)))


def _acked_for(lock, ref: str) -> list:
    """Lock entries acknowledging `ref`."""
    return [e for e in lock.entries if e.ref == ref]


def _stale_for(report, ref: str) -> list:
    """Drift-report stale entries whose acked ref is `ref`."""
    return [s for s in report.stale if s.entry.ref == ref]


def _dangling_for(report, ref: str) -> list:
    """Dangling edges with `ref` at either endpoint."""
    return [d for d in report.dangling if ref in (d.edge.src, d.edge.target)]


def _is_endpoint(snapshot, ref: str) -> bool:
    """Whether `ref` is the endpoint of any incoming or outgoing edge."""
    from frob.graph import edges_from, edges_to

    incoming = any(e.target == ref for e in edges_to(snapshot, ref))
    return incoming or bool(edges_from(snapshot, ref))


def _render_why_lines(ref: str, acked: list, stale: list, dangling: list) -> list[str]:
    """Human-readable `graph why` report lines for the gathered drift facts."""
    lines = [f"why: {ref}"]
    if not acked:
        lines.append(
            f"  not acked -- no frob.lock entry for this ref (remedy: frob ack {ref})"
        )
    for e in acked:
        lines.append(f"  acked facet={e.facet} digest={e.digest[:12]}")
    for s in stale:
        lines.append(
            f"  STALE facet={s.entry.facet} was={s.entry.digest[:12]} "
            f"now={s.current[:12]} affects={list(s.dependents)} "
            f"(remedy: frob ack {ref} --facet {s.entry.facet})"
        )
    for d in dangling:
        lines.append(
            f"  DANGLING edge {d.edge.src} -> {d.edge.target} "
            f"candidates={list(d.candidates)} "
            "(remedy: fix the directive target or rename)"
        )
    if not stale and not dangling and acked:
        lines.append("  clean -- no drift detected")
    return lines


def _why_json_payload(snapshot, ref: str, acked, stale, dangling) -> dict:  # noqa: ANN001
    """The `--json` payload for `frob graph why`."""
    return {
        "ref": ref,
        "acked_facets": [e.facet for e in acked],
        "stale": [s.model_dump() for s in stale],
        "dangling": [d.model_dump() for d in dangling],
        "is_edge_endpoint": _is_endpoint(snapshot, ref),
    }


def _why_drift_facts(root: Path, snapshot, ref: str):  # noqa: ANN201
    """Load `frob.lock`, compute drift, and gather the acked/stale/dangling facts
    for `ref`; exit(1) if the lock cannot be loaded."""
    from frob.graph.lock import drift, load_lock

    lock_result = load_lock(root / "frob.lock")
    if lock_result.is_err:
        _log.error("graph why: frob.lock: %s", lock_result.danger_err)
        sys.exit(1)
    lock = lock_result.danger_ok
    report = drift(lock, snapshot)
    return (
        lock,
        _acked_for(lock, ref),
        _stale_for(report, ref),
        _dangling_for(report, ref),
    )


def _run_why(root: Path, cache: Path, cfg: AppConfig) -> None:
    from frob.graph import resolve

    if cfg.graph_ref is None:
        _log.error("frob graph why requires <ref>")
        sys.exit(1)

    loaded = _load_snapshot(root, cache)
    if loaded.is_err:
        _log.error("graph unavailable: %s", loaded.danger_err)
        sys.exit(1)
    snapshot = loaded.danger_ok

    resolved = resolve(snapshot, cfg.graph_ref)
    if resolved.is_err:
        _log.error("graph why: %s: %s", cfg.graph_ref, resolved.danger_err)
        sys.exit(1)

    ref = cfg.graph_ref
    _lock, acked, stale, dangling = _why_drift_facts(root, snapshot, ref)

    if cfg.graph_json:
        import json

        payload = _why_json_payload(snapshot, ref, acked, stale, dangling)
        _log.info(json.dumps(payload, indent=2))
        return

    _log.info("\n".join(_render_why_lines(ref, acked, stale, dangling)))
