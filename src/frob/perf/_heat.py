"""`heat`: pure(-ish) join of pstats rows onto symbol spans (docs/perf.md's
Heat-map piece), plus the ASCII bar renderer `frob perf heat` prints with.

`heat` reads the artifact's `.pstats` file via the stdlib `pstats` module --
the one piece of IO this module performs, mirroring `frob.policy._pattern_
violations`' own "reads source text, otherwise pure" posture. Everything
after that read is a value-level join: pstats rows carry `(file, line,
function)`; `GraphSnapshot.symbols` carries `(path, qualname) -> span`;
a row is attributed to the tightest-spanning symbol whose file matches and
whose span contains the row's line. Anything that does not resolve --
stdlib frames, C extension frames, or files outside the repo -- accumulates
into `unattributed_s` rather than being silently dropped.
"""

from __future__ import annotations

import pstats
from pathlib import Path, PurePosixPath

from frob.graph import GraphSnapshot, SymbolRecord
from frob.logging import get_logger
from frob.logging.color import YELLOW, paint, should_color
from frob.perf._models import HeatEntry, HeatReport, ProfileArtifact

_log = get_logger(__name__)

__all__ = ["heat", "join_smells", "render_bar"]

_BAR_WIDTH = 30


# frob:ticket T-0021
def _relativize(root: Path, raw_file: str) -> str | None:
    """Best-effort repo-relative POSIX path for a pstats row's raw filename,
    or `None` when it plainly falls outside `root` (stdlib, site-packages).

    cProfile records `co_filename` verbatim: an absolute path for most
    frames, but exactly the argv token (often relative to the profiled
    process's cwd, i.e. `root`) for the profiled script's own module. A
    bare `Path(raw_file).resolve()` would instead resolve against *this*
    process's cwd, which is wrong whenever the two differ (every test)."""
    raw_path = Path(raw_file)
    resolved_root = root.resolve()
    candidate = raw_path if raw_path.is_absolute() else (root / raw_path)
    try:
        resolved = candidate.resolve()
        rel = resolved.relative_to(resolved_root)
    except (OSError, ValueError):
        return None
    return PurePosixPath(rel).as_posix()


# frob:ticket T-0021
def _enclosing_symbol(
    by_path: dict[str, list[SymbolRecord]], rel_path: str, line: int
) -> SymbolRecord | None:
    """The tightest-spanning symbol in `rel_path` whose span contains `line`."""
    candidates = [
        record
        for record in by_path.get(rel_path, ())
        if record.span[0] <= line <= record.span[1]
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda r: r.span[1] - r.span[0])


# frob:doc docs/perf.md#public-api
# frob:ticket T-0021
def heat(artifact: ProfileArtifact, snapshot: GraphSnapshot) -> HeatReport:
    """Join `artifact`'s pstats rows onto `snapshot`'s symbol spans, ranked
    by cumulative time desc. `HeatEntry.smells` is always empty here --
    `join_smells` is the separate step `--smells` uses to attach PERF
    findings, since that requires a parsed-file pass `heat` does not take."""
    root = Path(snapshot.root)
    pstats_path = root / ".frob" / "perf" / f"{artifact.sha}.pstats"
    try:
        stats = pstats.Stats(str(pstats_path))
    except (OSError, TypeError, ValueError) as exc:
        _log.error("heat: could not load pstats at %s: %s", pstats_path, exc)
        return HeatReport(entries=(), unattributed_s=0.0)

    by_path: dict[str, list[SymbolRecord]] = {}
    for record in snapshot.symbols.values():
        by_path.setdefault(record.id.path, []).append(record)

    totals: dict[str, dict[str, float | int]] = {}
    unattributed_s = 0.0

    stats_dict = stats.stats  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
    for (raw_file, line, _funcname), row in stats_dict.items():
        _cc, ncalls, self_t, cum_t, _callers = row
        rel_path = _relativize(root, raw_file)
        record = _enclosing_symbol(by_path, rel_path, line) if rel_path else None
        if record is None:
            unattributed_s += self_t
            continue
        bucket = totals.setdefault(
            record.symref, {"cum_s": 0.0, "self_s": 0.0, "ncalls": 0}
        )
        bucket["cum_s"] = float(bucket["cum_s"]) + cum_t
        bucket["self_s"] = float(bucket["self_s"]) + self_t
        bucket["ncalls"] = int(bucket["ncalls"]) + ncalls

    entries = tuple(
        HeatEntry(
            ref=ref,
            cum_s=float(bucket["cum_s"]),
            self_s=float(bucket["self_s"]),
            ncalls=int(bucket["ncalls"]),
        )
        for ref, bucket in totals.items()
    )
    ranked = tuple(sorted(entries, key=lambda e: e.cum_s, reverse=True))
    _log.info(
        "heat: %d symbol(s) attributed, %.3fs unattributed", len(ranked), unattributed_s
    )
    return HeatReport(entries=ranked, unattributed_s=unattributed_s)


# frob:ticket T-0021
def join_smells(
    report: HeatReport, violations_by_ref: dict[str, tuple[str, ...]]
) -> HeatReport:
    """Attach PERF rule ids from `violations_by_ref` (symref -> rule ids)
    onto each entry -- the `--smells` step docs/perf.md calls "the killer
    join": hot AND quadratic."""
    updated = tuple(
        entry.model_copy(update={"smells": violations_by_ref.get(entry.ref, ())})
        for entry in report.entries
    )
    return report.model_copy(update={"entries": updated})


# frob:ticket T-0021
def render_bar(cum_s: float, max_s: float, *, color: bool | None = None) -> str:
    """An ASCII `#`-block bar sized to `cum_s / max_s`, painted yellow when
    `color` (or `should_color()` when `color` is `None`)."""
    enabled = should_color() if color is None else color
    if max_s <= 0:
        filled = 0
    else:
        filled = max(0, min(_BAR_WIDTH, round(_BAR_WIDTH * cum_s / max_s)))
    bar = "#" * filled + "-" * (_BAR_WIDTH - filled)
    return paint(bar, YELLOW, enabled)
