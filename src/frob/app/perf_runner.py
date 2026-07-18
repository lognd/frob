"""CLI wiring for `frob perf profile|heat` (docs/modules/perf.md).

# frob:ticket T-0021
"""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.logging.color import BOLD, CYAN, DIM, paint, should_color

_log = get_logger(__name__)

__all__ = ["run"]


# frob:ticket T-0021
# frob:doc docs/modules/app.md#runners
def run(cfg: AppConfig) -> None:
    """Dispatch to `frob perf profile` or `frob perf heat`."""
    match cfg.perf_command:
        case "profile":
            _profile(cfg)
        case "heat":
            _heat(cfg)
        case _:
            _log.error("usage: frob perf <profile|heat> ...")
            sys.exit(1)


# frob:ticket T-0021
def _profile(cfg: AppConfig) -> None:
    """`frob perf profile -- <argv>` / `frob perf profile --tests`."""
    from frob.perf import profile_command

    root = (cfg.perf_path or Path(".")).resolve()

    if cfg.perf_tests:
        argv = ["-m", "pytest", "-q"]
    else:
        argv = list(cfg.perf_argv)
        if argv and argv[0] == "--":
            argv = argv[1:]
        if not argv:
            _log.error("frob perf profile requires -- <argv> or --tests")
            sys.exit(1)

    result = profile_command(argv, root)
    if result.is_err:
        _log.error("profile failed: %s", result.danger_err)
        sys.exit(1)
    artifact = result.danger_ok
    status = "ok" if artifact.exit_code == 0 else f"exit={artifact.exit_code}"
    print(
        f"profiled {' '.join(argv)!r} -> "
        f"sha={artifact.sha} total_s={artifact.total_s:.3f} workload={status}"
    )
    # frob:ticket T-0027 -- propagate the workload's failure to the caller
    # so `frob perf profile -- pytest ...` fails CI when the run failed.
    if artifact.exit_code != 0:
        sys.exit(artifact.exit_code)


# frob:ticket T-0021
def _load_snapshot(root: Path):  # noqa: ANN201
    """Build (or load-cached) the graph snapshot `heat`/`perf_rules` need."""
    from frob.graph import build_graph

    cache_path = root / ".frob" / "cache.db"
    result = build_graph(root, cache_path)
    if result.is_err:
        _log.error("heat: graph build failed: %s", result.danger_err)
        sys.exit(1)
    return result.danger_ok


# frob:ticket T-0021
# frob:ticket T-0125
def _heat(cfg: AppConfig) -> None:
    """`frob perf heat [--json] [--smells] [--top N] [--annotate FILE]`."""
    import contextlib

    if cfg.perf_json:
        from frob.logging import quiet_stdout_logs

        ctx = quiet_stdout_logs()
    else:
        ctx = contextlib.nullcontext()

    with ctx:
        _heat_body(cfg)


# frob:ticket T-0021
def _smell_rules_by_ref(violations, snapshot) -> dict[str, tuple[str, ...]]:
    """`{symref: (rule, ...)}` for perf violations, indexed by (path, line).

    The symbol table is indexed once by location so violations join in
    O(n+m) rather than the O(n*m) scan that pairing each violation against
    every symbol would require.
    """
    location_to_ref: dict[tuple[str, int], str] = {
        (record.id.path, record.span[0]): record.symref
        for record in snapshot.symbols.values()
    }
    by_ref: dict[str, tuple[str, ...]] = {}
    for v in violations:
        symref = location_to_ref.get((v.file, v.line))
        if symref is not None:
            by_ref[symref] = (*by_ref.get(symref, ()), v.rule)
    return by_ref


# frob:ticket T-0021
def _print_heat_table(entries, unattributed_s: float) -> None:
    """Print the heat table (one row per symbol) plus the unattributed total."""
    from frob.perf import render_bar

    color = should_color(sys.stdout)
    max_s = max((e.cum_s for e in entries), default=0.0)
    header = paint(
        f"{'symbol':<50} {'cum_s':>8} {'self_s':>8} {'ncalls':>8}  ", BOLD, color
    )
    print(header + "heat")
    for e in entries:
        bar = render_bar(e.cum_s, max_s, color=color)
        smell_tag = f" [{','.join(e.smells)}]" if e.smells else ""
        print(
            f"{e.ref:<50} {e.cum_s:>8.3f} {e.self_s:>8.3f} {e.ncalls:>8}  "
            f"{bar}{smell_tag}"
        )
    print(paint(f"unattributed: {unattributed_s:.3f}s", DIM, color))


def _ranked_heat_entries(cfg: AppConfig, root: Path, report, snapshot):  # noqa: ANN001, ANN201
    """`report`'s entries, smell-joined/sorted and top-N'd per `cfg`; report is
    replaced in place with the smell-joined version when `--smells` is set."""
    from frob.perf import join_smells

    if cfg.perf_smells:
        from frob.gates import perf_gate

        by_ref = _smell_rules_by_ref(perf_gate(root, snapshot), snapshot)
        report = join_smells(report, by_ref)
        entries = sorted(report.entries, key=lambda e: (not e.smells, -e.cum_s))
    else:
        entries = list(report.entries)

    if cfg.perf_top is not None:
        entries = entries[: cfg.perf_top]
    return report, entries


def _print_heat_result(cfg: AppConfig, entries, report) -> None:  # noqa: ANN001
    """Render `entries`/`report` as `--json` or the default table, per `cfg`."""
    if cfg.perf_json:
        import json

        payload = {
            "entries": [e.model_dump() for e in entries],
            "unattributed_s": report.unattributed_s,
        }
        print(json.dumps(payload, indent=2))
        return
    _print_heat_table(entries, report.unattributed_s)


# frob:ticket T-0021
def _heat_body(cfg: AppConfig) -> None:
    """The actual `frob perf heat` body, run inside `_heat`'s optional
    quiet-stdout-logs context so `--json` stays pure JSON on stdout."""
    from frob.perf import HeatReport, heat, load_artifact

    root = (cfg.perf_path or Path(".")).resolve()

    artifact_result = load_artifact(root, cfg.perf_ref)
    if artifact_result.is_err:
        _log.error("heat: %s", artifact_result.danger_err)
        sys.exit(1)
    artifact = artifact_result.danger_ok

    snapshot = _load_snapshot(root)
    report: HeatReport = heat(artifact, snapshot)
    report, entries = _ranked_heat_entries(cfg, root, report, snapshot)

    if cfg.perf_annotate is not None:
        _annotate(root, cfg.perf_annotate, report, snapshot)
        return

    _print_heat_result(cfg, entries, report)


def _annotate_gutters(rel: str, report, snapshot) -> dict[int, str]:  # noqa: ANN001
    """`{line: "cum_s/ncalls"}` for every heat entry whose symbol lives in `rel`."""
    by_line: dict[int, str] = {}
    for entry in report.entries:
        symbol_file, _, _qualname = entry.ref.partition("::")
        if symbol_file != rel:
            continue
        record = snapshot.symbols.get(entry.ref)
        if record is None:
            continue
        by_line[record.span[0]] = f"{entry.cum_s:.3f}s/{entry.ncalls}x"
    return by_line


# frob:ticket T-0021
def _annotate(root: Path, file: Path, report, snapshot) -> None:  # noqa: ANN001
    """`--annotate <file>`: print `file` with a per-line hit/time gutter.

    cProfile is function-granularity, not line-granularity (unlike
    line_profiler) -- there is no real per-line hit count available. The
    honest rendering here is a gutter on each symbol's *definition* line
    carrying that symbol's cum_s/ncalls, and a blank gutter on every other
    line; a documented cut, not a fabricated per-line number."""
    color = should_color(sys.stdout)
    try:
        rel = file.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = file.as_posix()

    by_line = _annotate_gutters(rel, report, snapshot)

    try:
        text = file.read_text(encoding="utf-8")
    except OSError as exc:
        _log.error("annotate: could not read %s: %s", file, exc)
        sys.exit(1)

    for lineno, source_line in enumerate(text.splitlines(), start=1):
        tag = by_line.get(lineno, "")
        gutter = paint(f"{lineno:>5} {tag:>14} |", CYAN, color)
        print(f"{gutter} {source_line}")
