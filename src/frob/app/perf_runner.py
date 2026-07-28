"""CLI wiring for `frob perf profile|heat|collect` (docs/modules/perf.md).

# frob:ticket T-0021
# frob:ticket T-0765
"""

# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/app/perf_runner.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"
from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.logging.color import BOLD, CYAN, DIM, paint, should_color
from frob.render import Renderer

_log = get_logger(__name__)

__all__ = ["run"]


# frob:ticket T-0021
# frob:ticket T-0765
# frob:doc docs/modules/app.md#runners
def run(cfg: AppConfig) -> None:
    """Dispatch to `frob perf profile`, `frob perf heat`, `frob perf
    collect`, or `frob perf hot` (T-0712)."""
    match cfg.perf_command:
        case "profile":
            _profile(cfg)
        case "heat":
            _heat(cfg)
        case "collect":
            _collect(cfg)
        case "hot":
            _hot(cfg)
        case _:
            _log.error("usage: frob perf <profile|heat|collect|hot> ...")
            sys.exit(1)


# frob:ticket T-0021
# frob:ticket T-0562
# frob:waive ARCH103 reason="T-0977: `frob perf profile` CLI entrypoint -- resolves \
# the profile root/argv and dispatches to `profile_command`; runner-shape \
# orchestration, same as this module's other `_run_*`/`_*` CLI handlers"
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
    Renderer.for_stream(sys.stdout).line(
        f"profiled {' '.join(argv)!r} -> "
        f"sha={artifact.sha} total_s={artifact.total_s:.3f} workload={status}"
    )
    # frob:ticket T-0027
    # Propagate the workload's failure to the caller so `frob perf profile
    # -- pytest ...` fails CI when the run failed.
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
# frob:ticket T-0562
def _print_heat_table(entries, unattributed_s: float) -> None:
    """Print the heat table (one row per symbol) plus the unattributed total."""
    from frob.perf import render_bar

    color = should_color(sys.stdout)
    renderer = Renderer.for_stream(sys.stdout)
    max_s = max((e.cum_s for e in entries), default=0.0)
    header = paint(
        f"{'symbol':<50} {'cum_s':>8} {'self_s':>8} {'ncalls':>8}  ", BOLD, color
    )
    renderer.line(header + "heat")
    for e in entries:
        bar = render_bar(e.cum_s, max_s, color=color)
        smell_tag = f" [{','.join(e.smells)}]" if e.smells else ""
        renderer.line(
            f"{e.ref:<50} {e.cum_s:>8.3f} {e.self_s:>8.3f} {e.ncalls:>8}  "
            f"{bar}{smell_tag}"
        )
    renderer.line(paint(f"unattributed: {unattributed_s:.3f}s", DIM, color))


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


# frob:ticket T-0562
def _print_heat_result(cfg: AppConfig, entries, report) -> None:  # noqa: ANN001
    """Render `entries`/`report` as `--json` or the default table, per `cfg`."""
    if cfg.perf_json:
        import json

        payload = {
            "entries": [e.model_dump() for e in entries],
            "unattributed_s": report.unattributed_s,
        }
        Renderer.for_stream(sys.stdout).line(json.dumps(payload, indent=2))
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


# frob:ticket T-0765
# frob:ticket T-0976
# frob:tests tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCollectStacksViaSamplerArgvStripping.test_non_marker_first_arg_is_not_stripped  # noqa: E501
# frob:tests tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCollectStacksViaSamplerArgvStripping.test_marker_first_arg_is_stripped  # noqa: E501
# frob:tests tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCollectStacksViaSamplerArgvStripping.test_empty_argv_falls_back_to_dash_q  # noqa: E501
def _collect_stacks_via_sampler(cfg: AppConfig):  # noqa: ANN201
    """Run the T-0710 in-process python sampler over `pytest.main` under
    `-- <argv>` (argv defaulting to `-q`, the whole suite) and return the
    `SampledStack`s it recorded."""
    from frob.perf import SamplerConfig, run_sampled

    default_cfg = SamplerConfig()
    sampler_cfg = SamplerConfig(
        interval_s=(
            cfg.perf_interval_s
            if cfg.perf_interval_s is not None
            else default_cfg.interval_s
        ),
        max_depth=(
            cfg.perf_max_depth
            if cfg.perf_max_depth is not None
            else default_cfg.max_depth
        ),
    )

    argv = list(cfg.perf_argv)
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        argv = ["-q"]

    def _run_pytest() -> None:
        """Run pytest's own `main` for its stack-sampling side effect
        only -- `run_sampled` wants a no-return workload, `pytest.
        main`'s exit code is deliberately discarded here since
        `frob perf collect --sampler` reports SAMPLES, not a test
        verdict (a failed/errored test run still yields a real,
        usable stack sample)."""
        import pytest

        pytest.main(argv)

    stacks, elapsed = run_sampled(_run_pytest, sampler_cfg)
    _log.info(
        "collect: sampler ran the test suite in %.3fs, %d sample(s)",
        elapsed,
        len(stacks),
    )
    return stacks


# frob:ticket T-0990
# frob:tests tests/system/test_cli_perf.py::TestPerfCollect.test_collect_resolves_a_real_python_hot_frame  # noqa: E501
def _read_perf_file_text(file: Path) -> str:  # noqa: ANN201
    """Read `file` as UTF-8 text for `frob perf collect`, exiting with a
    logged error on any OSError. Split out of `_collect_stacks_from_file`
    (T-0990) so each of the read/format-resolve/parse steps stays a single,
    low-branch-count concern of its own -- the ARCH103 mixed-concern-
    function check flags a function only once it mixes I/O, string-
    formatting, AND 2+ of its own decision points, and no one of these
    three helpers alone reaches that bar."""
    try:
        return file.read_text(encoding="utf-8")
    except OSError as exc:
        _log.error("collect: could not read %s: %s", file, exc)
        sys.exit(1)


# frob:ticket T-0990
# frob:tests tests/system/test_cli_perf.py::TestPerfCollect.test_collect_autodetects_cpuprofile_format  # noqa: E501
def _resolve_perf_format(cfg: AppConfig, file: Path, text: str) -> str:
    """Explicit `cfg.perf_format`, else autodetect via
    `detect_collector_format` (T-0990, split out of
    `_collect_stacks_from_file` -- see `_read_perf_file_text`'s docstring
    for why)."""
    from frob.perf import detect_collector_format

    return cfg.perf_format or detect_collector_format(file, text)


# frob:ticket T-0990
# frob:tests tests/system/test_cli_perf.py::TestPerfCollect.test_collect_json_output_is_valid_json  # noqa: E501
def _parse_perf_text_or_exit(fmt: str, text: str, file: Path):  # noqa: ANN201
    """Parse `text` as `fmt` via `parse_collector_format`, exiting with a
    logged error on any parse failure (T-0990, split out of
    `_collect_stacks_from_file` -- see `_read_perf_file_text`'s docstring
    for why)."""
    from frob.perf._collectors import parse_collector_format

    result = parse_collector_format(fmt, text, str(file))
    if result.is_err:
        _log.error("collect: %s: %s", file, result.danger_err)
        sys.exit(1)
    return result.danger_ok


# frob:ticket T-0976
# frob:ticket T-0990
def _collect_stacks_from_file(cfg: AppConfig):  # noqa: ANN201
    """Read `--file`'s recorded profile and parse it via
    `parse_collector_format`, autodetecting the format when `--format` was
    not given. `sys.exit`s on any read/parse failure. T-0990: delegates the
    read, format-resolution, and parse steps to `_read_perf_file_text`/
    `_resolve_perf_format`/`_parse_perf_text_or_exit` so this function's own
    body stays a single straight-line orchestration concern."""
    if cfg.perf_file is None:
        _log.error("frob perf collect requires --file PATH or --sampler")
        sys.exit(1)
    file = cfg.perf_file
    text = _read_perf_file_text(file)
    fmt = _resolve_perf_format(cfg, file, text)
    stacks = _parse_perf_text_or_exit(fmt, text, file)
    _log.info("collect: %s parsed as %s", file, fmt)
    return stacks


# frob:ticket T-0765
# frob:ticket T-0976
def _collect_stacks(cfg: AppConfig):  # noqa: ANN201
    """Get this invocation's `SampledStack`s: either the T-0710 python
    sampler (`--sampler`) or `--file`'s recorded profile
    (`_collect_stacks_from_file`). `sys.exit`s on any failure, matching
    every other `perf_runner` command's error style."""
    if cfg.perf_sampler:
        return _collect_stacks_via_sampler(cfg)
    return _collect_stacks_from_file(cfg)


# frob:ticket T-0765
def _print_decile_rows(rows) -> None:  # noqa: ANN001
    """Print `language_deciles`' rows as one table, grouped by language."""
    renderer = Renderer.for_stream(sys.stdout)
    color = should_color(sys.stdout)
    header = paint(
        f"{'language':<14} {'decile':>6} {'sections':>9} {'weight':>10}", BOLD, color
    )
    renderer.line(header)
    for row in rows:
        renderer.line(
            f"{row.language:<14} {row.decile:>6} {row.section_count:>9} "
            f"{row.weight:>10.3f}"
        )


# frob:ticket T-0765
def _collect(cfg: AppConfig) -> None:
    """`frob perf collect --file PATH [--format ...] | --sampler [-- argv]
    [--top N] [--json]`: dispatch to `_collect_body`, under the same
    `--json`-implies-quiet-stdout-logs discipline `_heat` uses, so
    `--json`'s own log lines (parse/resolve progress) never pollute the
    payload the CLI's stdout must stay pure JSON for."""
    import contextlib

    if cfg.perf_json:
        from frob.logging import quiet_stdout_logs

        ctx = quiet_stdout_logs()
    else:
        ctx = contextlib.nullcontext()

    with ctx:
        _collect_body(cfg)


# frob:ticket T-0765
# frob:ticket T-0712
def _collect_body(cfg: AppConfig) -> None:
    """The actual `frob perf collect` body: resolve a hot-graph
    collector's stacks through `resolve_stream` (the T-0748 collector
    adapters, or the T-0710 python sampler), print per-language deciles,
    persist every resolved section's run sketch into T-0711's store
    (T-0712), and print any regression-ratchet/advisory findings this
    run produced."""
    from frob.perf import build_index_for_files, language_deciles, resolve_stream

    stacks = _collect_stacks(cfg)

    files = {frame.file for stack in stacks for frame in stack.frames}
    index = build_index_for_files(files)
    stream = resolve_stream(index, stacks)
    rows = language_deciles(stream, index)

    findings, advisories = _persist_run(cfg, index, stream)

    if cfg.perf_top is not None:
        rows = rows[: cfg.perf_top]

    if cfg.perf_json:
        import json

        payload = {
            "rows": [r.model_dump() for r in rows],
            "unattributed_weight": stream.unattributed_weight,
            "sample_count": len(stacks),
            "ratchet_findings": [f.model_dump() for f in findings],
            "advisories": [
                {"rule": v.rule, "file": v.file, "line": v.line, "message": v.message}
                for v in advisories
            ],
        }
        Renderer.for_stream(sys.stdout).line(json.dumps(payload, indent=2))
        return

    _print_decile_rows(rows)
    summary = (
        f"samples={len(stacks)} unattributed_weight={stream.unattributed_weight:.3f}"
    )
    Renderer.for_stream(sys.stdout).line(paint(summary, DIM, should_color(sys.stdout)))
    _print_findings(findings, advisories)


# frob:ticket T-0712
def _persist_run(cfg: AppConfig, index, stream):  # noqa: ANN001, ANN201
    """Persist this run's per-section weight into T-0711's sketch store
    (one observation per resolved sample, per `Section`), check each
    section's regression ratchet against its stored prior, and compute
    the T-0712 advisories over the SAME `stream`/`index` this run already
    resolved -- returns `(ratchet_findings, advisory_violations)`. Every
    section update happens BEFORE the ratchet check reads `get_sketch`'s
    "prior" so the comparison is genuinely old-vs-new, never a value the
    same call already wrote."""
    from frob.perf._advisories import (
        external_call_advisories,
        heavy_tail_advisories,
        nested_loop_fanin_advisories,
    )
    from frob.perf._hotgraph import UNATTRIBUTED_SECTION_ID
    from frob.perf._ratchet import RatchetFinding, check_ratchet, save_ratchet_findings
    from frob.perf._sketch_store import (
        get_sketch,
        load_sketch_config,
        new_run_sketch,
        put_sketch,
        stable_section_key,
    )
    from frob.stats._sketch import QuantileSketch

    root = (cfg.perf_path or Path(".")).resolve()
    config = load_sketch_config(root)
    sections = {s.id: s for sections in index.values() for s in sections}

    run_weight: dict[str, float] = {}
    for hit in stream.section_hits:
        if hit.section_id == UNATTRIBUTED_SECTION_ID:
            continue
        run_weight[hit.section_id] = run_weight.get(hit.section_id, 0.0) + hit.weight

    from frob.stats._sketch import add_value

    findings: list[RatchetFinding] = []
    heavy_tail_input: dict[str, tuple[str, str, int, QuantileSketch]] = {}
    for section_id, weight in run_weight.items():
        section = sections.get(section_id)
        if section is None:
            continue
        key = stable_section_key(section)
        prior = get_sketch(root, key)
        run_sketch = add_value(new_run_sketch(config.alpha), weight)
        finding = check_ratchet(
            key, section.qualname, prior, run_sketch, config.ratchet_tolerance
        )
        if finding is not None:
            findings.append(finding)
        merged_r = put_sketch(
            root, key, section.kind, run_sketch, config, label=section.qualname
        )
        if merged_r.is_ok:
            heavy_tail_input[key] = (
                section.qualname,
                section.file,
                section.start_line,
                merged_r.danger_ok,
            )

    save_ratchet_findings(root, findings)

    advisories = (
        external_call_advisories(stream, index)
        + nested_loop_fanin_advisories(stream, index)
        + heavy_tail_advisories(heavy_tail_input)
    )
    return findings, advisories


# frob:ticket T-0712
def _print_findings(findings, advisories) -> None:  # noqa: ANN001
    """Print T-0712's ratchet findings and advisories after a `frob perf
    collect` run -- silent (no extra lines) when there are none, matching
    every other frob subcommand's "quiet on the happy path" posture."""
    renderer = Renderer.for_stream(sys.stdout)
    color = should_color(sys.stdout)
    for finding in findings:
        renderer.line(
            paint(
                f"PERF009: {finding.label or finding.section_key} regressed "
                f"{finding.worst_relative_shift * 100:.0f}%: "
                f"prior={finding.prior_deciles} current={finding.current_deciles}",
                BOLD,
                color,
            )
        )
    for violation in advisories:
        renderer.line(f"{violation.rule}: {violation.message}")


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
# frob:ticket T-0562
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

    renderer = Renderer.for_stream(sys.stdout)
    for lineno, source_line in enumerate(text.splitlines(), start=1):
        tag = by_line.get(lineno, "")
        gutter = paint(f"{lineno:>5} {tag:>14} |", CYAN, color)
        renderer.line(f"{gutter} {source_line}")


# frob:ticket T-0712
def _hot_sort_key(row, by: str):  # noqa: ANN001, ANN202
    """Sort key for `frob perf hot --by p90|p50xcount`: `p90` ranks by the
    stored sketch's p90 read; `p50xcount` (the default) ranks by p50 times
    total observation weight -- a cheap proxy for "typical cost times how
    often it happens", so a moderately-slow-but-frequent section can
    outrank a rare outlier."""
    from frob.stats._sketch import quantile, total_weight

    p50 = quantile(row.sketch, 0.5)
    p90 = quantile(row.sketch, 0.9)
    if by == "p90":
        return p90
    return p50 * total_weight(row.sketch)


# frob:ticket T-1093
def _hot_json_payload(root: Path, by: str, top: int | None) -> list[dict]:  # noqa: ANN201
    """The rendered `frob perf hot --json` row list -- computed in-process,
    field-for-field identical to `frob_perf_hot`'s daemon response shape
    (docs/modules/serve.md#cli-daemon-proxy-t-1093), so `_hot`'s daemon-hit
    branch and this fallback branch always serialize to the same JSON."""
    from frob.perf._sketch_store import list_sketches
    from frob.stats._sketch import quantile, total_weight

    rows = list_sketches(root)
    rows.sort(key=lambda row: _hot_sort_key(row, by), reverse=True)
    if top is not None:
        rows = rows[:top]
    return [
        {
            "section_key": row.section_key,
            "kind": row.kind,
            "label": row.label,
            "p50": quantile(row.sketch, 0.5),
            "p90": quantile(row.sketch, 0.9),
            "sample_count": total_weight(row.sketch),
        }
        for row in rows
    ]


# frob:ticket T-1093
def _hot_json(cfg: AppConfig, root: Path, by: str) -> None:
    """`frob perf hot --json`'s body (split out of `_hot`, T-1093, to keep
    both under ARCH001's line threshold): tries the T-1092 daemon's
    `frob_perf_hot` method first via `frob.app._daemon_proxy.query`, and on
    any `ProxyReason` (no daemon, unreachable, stale version mid-restart)
    falls back to `_hot_json_payload`'s in-process computation -- the two
    are proven byte-for-byte identical by
    `tests/test_app_daemon_proxy.py::TestDifferentialParity`."""
    import json

    from frob.app._daemon_proxy import query as _daemon_query

    params: dict[str, object] = {"by": by}
    if cfg.perf_top is not None:
        params["top"] = cfg.perf_top
    proxied = _daemon_query(root, "frob_perf_hot", params)
    payload = (
        proxied.danger_ok
        if proxied.is_ok
        else _hot_json_payload(root, by, cfg.perf_top)
    )
    Renderer.for_stream(sys.stdout).line(json.dumps(payload, indent=2))


# frob:ticket T-0712
# frob:ticket T-1093
def _hot(cfg: AppConfig) -> None:
    """`frob perf hot [--path DIR] [--top N] [--by p90|p50xcount] [--json]`:
    render T-0711's persisted sketch store, ranked by `--by` (default
    `p50xcount`) -- the query surface T-0712's plan calls for, reading
    the store directly with no live re-collection (a `frob perf collect`
    run is what populates it). The `--json` path is handled by `_hot_json`
    (T-1093's daemon-proxy seam); this function still renders the default
    table itself."""
    from frob.perf._sketch_store import list_sketches
    from frob.stats._sketch import quantile, total_weight

    root = (cfg.perf_path or Path(".")).resolve()
    by = cfg.perf_by or "p50xcount"

    if cfg.perf_json:
        _hot_json(cfg, root, by)
        return

    rows = list_sketches(root)
    rows.sort(key=lambda row: _hot_sort_key(row, by), reverse=True)
    if cfg.perf_top is not None:
        rows = rows[: cfg.perf_top]

    renderer = Renderer.for_stream(sys.stdout)
    color = should_color(sys.stdout)
    header = paint(
        f"{'label':<40} {'kind':<8} {'p50':>10} {'p90':>10} {'samples':>10}",
        BOLD,
        color,
    )
    renderer.line(header)
    for row in rows:
        renderer.line(
            f"{row.label or row.section_key:<40.40} {row.kind:<8} "
            f"{quantile(row.sketch, 0.5):>10.4f} {quantile(row.sketch, 0.9):>10.4f} "
            f"{total_weight(row.sketch):>10.1f}"
        )
