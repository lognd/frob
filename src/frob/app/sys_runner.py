"""CLI wiring for `frob sys` -- strata design-model applications
(docs/strata/roadmap.md phase 5, docs/commands/sys.md).

Three verbs today: `plan` (T-0084, obligation -> ticket compiler), `doc`
(T-0085, threat-catalog audit matrix), and `export` (T-0086, k8s/seccomp/
IAM config skeletons). `check`/`trace`/`capacity`/`threats` are later
phase-5 tickets, not yet landed -- `run` below should grow one more `if
cfg.sys_command == "..."` branch per verb as they land, never a parallel
dispatch mechanism.

T-1870: `sync-interface` (T-1150, mechanical `interface=` attr
auto-write) used to be a fourth verb here. Deleted per an explicit owner
directive that no code path may auto-update declared public-symbol
surface -- `interface=` is now purely hand-declared, with no writer
anywhere in this codebase (T-1629 is the follow-up that makes it
ENFORCE that hand-declared intent; this ticket only removed the mirror).

`plan` loads every `.strata` design file under the repo's design dir,
computes the obligation frontier (`frob.strata.plan_obligations`), diffs
it against markers already present in the ticket ledger, and either
prints the would-be tree (default, dry-run) or writes it (`--apply`). The
dry-run/apply split plus the marker-diff idempotency check both live here
rather than in `frob.strata._plan` -- that module stays a pure model ->
tickets compiler with no I/O of its own (T-0084 scope note: `frob.tickets`
is read-only reuse from this runner's point of view, never mutated by
`_plan.py` itself).

`doc` renders the per-family threat-catalog audit matrix
(`frob.strata.render_audit_matrix`) for a chosen view against every
loaded design model and prints it as deterministic markdown (T-0085).

`export` parses+elaborates a single `.strata` file (default
`design/frob.strata`) and renders one of three deterministic
runtime-enforcement config skeletons from its `KernelModel`
(`frob.strata._export`) -- see that module's docstring for the k8s/
seccomp/IAM mapping semantics.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from frob.app._style import style_fail, style_ok, style_rule, style_warn
from frob.app.config import AppConfig
from frob.gates import known_gate_rule_ids
from frob.graph import GraphSnapshot, build_graph, load_graph
from frob.logging import get_logger
from frob.logging.quiet import quiet_stdout_logs
from frob.render import Renderer
from frob.strata import (
    DEFAULT_BENIGN_CAPABILITIES,
    DEFAULT_DESIGN_DIR,
    MARKER_PREFIX,
    AuditReport,
    KernelModel,
    ModeConformanceReport,
    Module,
    PlannedTicket,
    ReliabilityReport,
    ResourceContentionReport,
    SelfConformReport,
    bind_code,
    build_facts,
    check_mode_conformance,
    check_reliability_health,
    check_reliability_timeouts,
    check_resource_contention,
    check_self_conformance,
    evaluate_exhaustiveness,
    evaluate_threats,
    group_gaps_by_view,
    load_design_ids,
    load_repo_benign_capabilities,
    merge_models,
    plan_obligations,
    project_capacity,
    render_audit_matrix,
    threat_violations_for_boundary,
)
from frob.strata._multifile import elaborate_merged
from frob.strata._parse import parse_module
from frob.tickets import load_all, new_ticket
from frob.tickets._models import Origin, TicketSpec
from frob.vet._capability_registry import (
    CAPABILITY_KINDS,
    LANGUAGES,
    capability_matrix,
)

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "cache.db"


def _stdout_color() -> bool:
    """should_color(stdout) for `sys audit`'s INFO-level lines (T-0179)."""
    import sys as _sys

    from frob.logging.color import should_color

    return should_color(_sys.stdout)


def _stderr_color() -> bool:
    """should_color(stderr) for `sys audit`'s WARNING/ERROR-level lines
    (T-0179) -- `frob.logging.config.toml` routes those to stderr, a
    separate stream whose own TTY-ness must be checked independently of
    stdout's."""
    import sys as _sys

    from frob.logging.color import should_color

    return should_color(_sys.stderr)


#: `frob sys export --format` choice -> exporter callable, keyed to avoid a
#: duplicated if/elif chain (charter law "no duplication") and so the
#: CLI's supported format set and the exporter registry can never drift
#: apart.
_EXPORT_FORMATS = ("k8s", "seccomp", "iam")


# ---------------------------------------------------------------------------
# plan (T-0084)
# ---------------------------------------------------------------------------


# frob:ticket T-0163
def _repo_root_for(file_path: Path) -> Path:
    """Best-effort repo root to suggest in `_resolve_design_root`'s error
    message: the nearest ancestor with a `frob.toml`/`.git`, else the
    grandparent of a `design_dir`-named ancestor (e.g. `design/x.strata`
    -> its parent), else just the file's own parent -- advisory text only,
    never used to actually resolve a design load."""
    for ancestor in (file_path.parent, *file_path.parents):
        if (ancestor / "frob.toml").exists() or (ancestor / ".git").exists():
            return ancestor
    for ancestor in file_path.parents:
        if ancestor.name == DEFAULT_DESIGN_DIR:
            return ancestor.parent
    return file_path.parent


# frob:tests tests/system/test_cli_sys_audit.py::TestSysAuditCli.test_file_arg_fails
def _resolve_design_root(cfg: AppConfig, command: str) -> Path:
    """Resolve `cfg.sys_path` (or `.`) to the repo-root directory `plan`/
    `doc`/`audit` walk with `_design_dir`+`load_design_ids` (those two
    callees always append `[strata].design_dir` themselves -- the argument
    here is the repo root, never the design directory or a `.strata` file).

    T-0163: a bare (repo-root) directory is the only invocation those two
    callees understand -- silently joining `design_dir` onto a *file* path
    (e.g. `frob sys audit design/frob.strata`) used to produce a
    nonexistent `<file>/design` path and an unearned "no design models"
    PASS (vacuous-pass doctrine violation). A file argument now fails
    loudly here, naming the expected repo-root invocation, instead of
    being mangled silently downstream."""
    root = (cfg.sys_path or Path(".")).resolve()
    if root.is_file():
        _log.error(
            "sys %s: %s is a file; pass the repo root directory instead "
            "(design files live under its [strata].design_dir, e.g. "
            "`frob sys %s %s`)",
            command,
            root,
            command,
            _repo_root_for(root),
        )
        sys.exit(1)
    return root


def _design_dir(root: Path) -> str:
    """`[strata].design_dir` from frob.toml, defaulting to `DEFAULT_DESIGN_DIR`
    (duplicated from `frob.gates`'s identical helper -- T-0084 scope excludes
    `src/frob/gates`, and this is a two-line frob.toml read, not shared logic
    worth a cross-module import)."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return DEFAULT_DESIGN_DIR
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("sys plan: frob.toml unreadable: %s", exc)
        return DEFAULT_DESIGN_DIR
    return data.get("strata", {}).get("design_dir", DEFAULT_DESIGN_DIR)


# T-0364: dropped the private `_merge_models` duplicate of
# `frob.strata.merge_models` (dup group, identical body) -- `frob.app` may
# import `frob.strata` (the reverse direction is what `merge_models`'s own
# docstring rules out), so the public helper is the one shared home; call
# sites below now use it directly.


def _load_snapshot(root: Path) -> GraphSnapshot | None:
    """Load (building if stale) the graph snapshot the unbound boundary/secret
    check needs; `None` (with a logged warning) if it cannot be produced --
    the rest of the plan still runs without that one obligation kind."""
    cache = root / _CACHE_REL
    loaded = load_graph(cache)
    if loaded.is_err:
        _log.info("sys plan: cache stale/missing, building: %s", loaded.danger_err)
        loaded = build_graph(root, cache)
    if loaded.is_err:
        _log.warning(
            "sys plan: graph unavailable, skipping unbound check: %s",
            loaded.danger_err,
        )
        return None
    return loaded.danger_ok


def _existing_markers(root: Path) -> frozenset[str]:
    """Every `sys-plan:...` marker line already present in some ticket body --
    the idempotency join key (`frob.strata._plan` module docstring)."""
    loaded = load_all(root)
    if loaded.is_err:
        _log.error("sys plan: could not load ticket store: %s", loaded.danger_err)
        sys.exit(1)
    markers: set[str] = set()
    for ticket in loaded.danger_ok.values():
        for line in ticket.body.splitlines():
            stripped = line.strip()
            if stripped.startswith(MARKER_PREFIX):
                markers.add(stripped)
    return frozenset(markers)


def _print_dry_run(new: list[PlannedTicket]) -> None:
    """Print the would-be ticket tree without writing anything (dry-run
    default). Names `--apply` explicitly in the label so the dry-run
    nature of the output -- and how to escape it -- is never ambiguous
    (T-0231: the prior "compiled N obligation ticket(s)" line alone gave
    no indication nothing had been written)."""
    if not new:
        _log.info("sys plan: model unchanged, nothing to plan")
        return
    _log.info(
        "sys plan: DRY RUN (no tickets created; pass --apply to compile) -- "
        "%d obligation ticket(s) would be created",
        len(new),
    )
    for ticket in new:
        indent = "  " if ticket.parent_marker else ""
        _log.info(
            "%s[%s] %s (%s)", indent, ticket.marker, ticket.title, ticket.kind.value
        )


def _spec_for(ticket: PlannedTicket, marker_to_id: dict[str, str]) -> TicketSpec:
    """Build a `TicketSpec` for `ticket`, resolving its marker-keyed
    blocked_by/parent references against ids already created this run."""
    blocked_by = tuple(
        marker_to_id[m] for m in ticket.blocked_by_markers if m in marker_to_id
    )
    parent = marker_to_id.get(ticket.parent_marker) if ticket.parent_marker else None
    return TicketSpec(
        title=ticket.title,
        kind=ticket.kind,
        origin=Origin.AGENT,
        scope=ticket.scope,
        blocked_by=blocked_by,
        parent=parent,
        threat=ticket.threat,
        body=ticket.body,
    )


def _apply(root: Path, new: list[PlannedTicket]) -> None:
    """Write `new` tickets to the store, parents before children, so a
    child's `parent`/`blocked_by` can resolve to the parent's freshly
    allocated id (marker -> ticket id built up as each ticket is created)."""
    marker_to_id: dict[str, str] = {}
    ordered = sorted(new, key=lambda t: t.parent_marker is not None)
    for ticket in ordered:
        spec = _spec_for(ticket, marker_to_id)
        created = new_ticket(root, spec)
        if created.is_err:
            _log.error(
                "sys plan: failed to create ticket for %s: %s",
                ticket.marker,
                created.danger_err,
            )
            sys.exit(1)
        marker_to_id[ticket.marker] = created.danger_ok.id
        _log.info("sys plan: created %s for %s", created.danger_ok.id, ticket.marker)


def _run_plan(cfg: AppConfig) -> None:
    """`frob sys plan`: compile the frontier, diff against the ledger, and
    print (default) or write (`--apply`) exactly the delta."""
    root = _resolve_design_root(cfg, "plan")
    design_dir = _design_dir(root)
    ids = load_design_ids(root, design_dir)
    if ids.errors:
        for error in ids.errors:
            _log.error("sys plan: %s failed to load: %s", error.path, error.error)
        sys.exit(1)
    if not ids.models:
        _log.info("sys plan: no design models under %s/%s", root, design_dir)
        return

    model = merge_models(ids.models)
    snapshot = _load_snapshot(root)
    planned = plan_obligations(model, design_ids=ids, snapshot=snapshot)
    if planned.is_err:
        _log.error("sys plan: %s", planned.danger_err)
        sys.exit(1)

    existing = _existing_markers(root)
    new = [t for t in planned.danger_ok.tickets if t.marker not in existing]

    if not new:
        _log.info("sys plan: model unchanged, nothing to plan")
        return
    if not cfg.sys_apply:
        _print_dry_run(new)
        return
    _apply(root, new)


# ---------------------------------------------------------------------------
# export (T-0086)
# ---------------------------------------------------------------------------


def _load_export_model(design_path: Path) -> KernelModel | None:
    """Parse+elaborate the single `.strata` file at `design_path` into a
    `KernelModel`, or None with an error already logged. Routes through
    `elaborate_merged` (T-1834) rather than calling `elaborate()` directly
    so a flow naming an unknown node fails closed via
    `check_cross_file_references` the same way a design loaded under
    `design/` does, instead of silently producing a `KernelModel` with a
    dangling flow endpoint -- `elaborate()`'s own permissive contract is
    unchanged, only this single-file export path is re-routed."""
    text = design_path.read_text()
    # Parsing/elaborating a design logs at INFO on every construct (LOG
    # EVERYTHING convention); `frob sys export` prints a machine-readable
    # payload to stdout, so those lines are muted for the duration exactly
    # like `check_runner`/`map_runner` already do for their own `--json`
    # paths (docs/modules/logging.md#public-api).
    with quiet_stdout_logs():
        parsed = parse_module(text)
        if parsed.is_err:
            _log.error("frob sys export: parse failed: %s", parsed.danger_err)
            return None
        elaborated = elaborate_merged(((str(design_path), parsed.danger_ok),))
        if elaborated.is_err:
            for cross_error in elaborated.danger_err:
                _log.error(
                    "frob sys export: elaborate failed: %s: %s",
                    cross_error.path,
                    cross_error.message,
                )
            return None
        return elaborated.danger_ok


def _require_export_format(fmt: str | None) -> None:
    """Exit 1 (with a logged reason) unless `fmt` is one of `_EXPORT_FORMATS`."""
    if fmt not in _EXPORT_FORMATS:
        _log.error(
            "frob sys export: --format must be one of %s", ", ".join(_EXPORT_FORMATS)
        )
        sys.exit(1)


def _require_export_design_path(design_path: Path) -> None:
    """Exit 1 (with a logged reason) unless `design_path` is an existing,
    non-directory `.strata` file."""
    if design_path.is_dir():
        _log.error(
            "frob sys export: %s is a directory; pass a single .strata file",
            design_path,
        )
        sys.exit(1)
    if not design_path.exists():
        _log.error("frob sys export: %s does not exist", design_path)
        sys.exit(1)


# frob:ticket T-0562
def _run_export(cfg: AppConfig) -> None:
    """`frob sys export --format k8s|seccomp|iam <design.strata>`: load one
    `.strata` design file, run the matching exporter, print its
    deterministic output."""
    fmt = cfg.sys_export_format
    _require_export_format(fmt)
    assert fmt is not None  # narrows for the type checker; enforced above
    design_path = cfg.sys_export_path or Path(DEFAULT_DESIGN_DIR) / "frob.strata"
    _require_export_design_path(design_path)

    model = _load_export_model(design_path)
    if model is None:
        sys.exit(1)

    from frob.strata._export import export_iam, export_k8s_netpol, export_seccomp

    exporter = {
        "k8s": export_k8s_netpol,
        "seccomp": export_seccomp,
        "iam": export_iam,
    }[fmt]
    Renderer.for_stream(sys.stdout).line(exporter(model))


# ---------------------------------------------------------------------------
# doc (T-0085)
# ---------------------------------------------------------------------------


# frob:ticket T-0085
# frob:ticket T-0562
def _run_doc(cfg: AppConfig) -> None:
    """`frob sys doc`: render the per-family threat-catalog audit matrix
    (docs/strata/threat.md#the-exhaustiveness-proof-the-point) for
    `cfg.sys_view` against every `.strata` design file under the repo's
    design dir, and print it (deterministic markdown, T-0085)."""
    root = _resolve_design_root(cfg, "doc")
    design_dir = _design_dir(root)
    ids = load_design_ids(root, design_dir)
    if ids.errors:
        for error in ids.errors:
            _log.error("sys doc: %s failed to load: %s", error.path, error.error)
        sys.exit(1)
    if not ids.models:
        _log.info("sys doc: no design models under %s/%s", root, design_dir)
        return

    model = merge_models(ids.models)
    rendered = render_audit_matrix(model, cfg.sys_view)
    if rendered.is_err:
        _log.error("sys doc: %s", rendered.danger_err)
        sys.exit(1)
    # frob:ticket T-0461
    # Deliberate output change: the prior `print(..., end="")` suppressed a
    # trailing newline; `Renderer.line` always terminates its line, so `frob
    # sys doc` output now ends with exactly one trailing newline it did not
    # have before (see the T-0461 Done report).
    Renderer.for_stream(sys.stdout).line(rendered.danger_ok.rstrip("\n"))


def _log_waived_gaps(report: AuditReport) -> None:
    """Log every waived gap (T-0174: ALWAYS printed, proved or not -- a
    waiver must never make a run look silent, `_waive.py`'s "loud in
    output" requirement). T-0173: gaps that are verbatim-identical across
    multiple views are grouped by `group_gaps_by_view` and printed ONCE
    with every affected view named, instead of once per view."""
    color = _stderr_color()
    for waived in group_gaps_by_view(report.waived):
        _log.warning(
            "sys audit: %s family=%s views=%s rule=%s target=%s detail=%s",
            style_warn("WAIVED", color),
            waived.family,
            ",".join(waived.views),
            style_rule(waived.rule, color),
            waived.target,
            waived.detail,
        )


def _log_proved_summary(report: AuditReport) -> None:
    """Log the PROVED summary line, carrying the waived count inline
    (T-0174 REJECT round: a separate WARNING line is lost under grep/
    quiet-mode filtering, so the count must ride the summary itself).
    T-0512 (strata audit G6): the narrower-than-baseline disclosure itself
    lives in `_print_audit_report`'s own unconditional warning line
    (fired regardless of proved/gap, charter: no duplication) -- this
    function only needs to avoid ever claiming MORE than "every view this
    run was configured to check held," which "every configured view"
    below already says precisely."""
    color = _stdout_color()
    if report.waived:
        _log.info(
            "sys audit: %s (%d waived) -- zero UNWAIVED gaps across "
            "every configured view",
            style_ok("PROVED", color),
            len(report.waived),
        )
    else:
        _log.info(
            "sys audit: %s -- zero gaps across every configured view",
            style_ok("PROVED", color),
        )


def _log_gaps(report: AuditReport) -> None:
    """Log every named gap, one per line (CI-parseable, no ambiguity about
    which conjunction member failed). T-0173: verbatim-identical gaps that
    fired under multiple views are grouped by `group_gaps_by_view` and
    printed ONCE with every affected view named, instead of once per view
    -- the underlying `report.gaps` count (used for the summary line and
    exit code) is unaffected, only the printed block count changes."""
    color = _stderr_color()
    _log.error("sys audit: %d gap(s) found", len(report.gaps))
    for gap in group_gaps_by_view(report.gaps):
        _log.error(
            "sys audit: %s family=%s views=%s rule=%s detail=%s",
            style_fail("GAP", color),
            gap.family,
            ",".join(gap.views),
            style_rule(gap.rule, color),
            gap.detail,
        )


# frob:ticket T-0115
# frob:ticket T-0512
def _print_audit_report(report: AuditReport) -> None:
    """Print `frob sys audit`'s machine-usable summary: which views were
    checked, then every named gap grouped by family (docs/strata/threat.md
    #the-exhaustiveness-proof-the-point: "every gap named, owned, and
    expiring") -- CI-parseable one-gap-per-line, no ambiguity about which
    conjunction member failed. T-0512 (strata audit G6): when this run's
    security views are narrower than the full catalog baseline
    (`AuditReport.narrower_than_baseline`), that is disclosed on its OWN
    line here too -- not only folded into the PROVED summary -- so a
    caller scanning for gaps (the `not report.proved` branch) sees the
    same disclosure a clean run would."""
    _log.info(
        "sys audit: checked %d view(s): %s",
        len(report.views_checked),
        ", ".join(report.views_checked),
    )
    if report.narrower_than_baseline:
        _log.warning(
            "sys audit: narrower than the full catalog baseline -- NOT "
            "checked against: %s",
            ", ".join(report.narrower_than_baseline),
        )
    _log_waived_gaps(report)
    if report.proved:
        _log_proved_summary(report)
        return
    _log_gaps(report)


# frob:ticket T-0861
def _log_sys_waived_findings(waived) -> None:  # noqa: ANN001
    """Log every waived SYS-family finding (rule/node/detail shape), one
    per line (T-0174: ALWAYS printed). Shared by self-conformance/
    contention/reliability (T-0861 dup group -- these three families
    logged byte-identical WAIVED lines from three separate copies)."""
    color = _stderr_color()
    for item in waived:
        _log.warning(
            "sys audit: %s family=sys rule=%s node=%s detail=%s",
            style_warn("WAIVED", color),
            style_rule(item.rule, color),
            item.node,
            item.detail,
        )


# frob:ticket T-0861
def _log_sys_findings(findings, *, label: str) -> None:  # noqa: ANN001
    """Log `%d <label> gap(s) found` then every finding (rule/node/detail
    shape), one per line. Shared by self-conformance/contention/
    reliability's violation-listing (T-0861 dup group)."""
    color = _stderr_color()
    _log.error("sys audit: %d %s gap(s) found", len(findings), label)
    for item in findings:
        _log.error(
            "sys audit: %s family=sys rule=%s node=%s detail=%s",
            style_fail("GAP", color),
            style_rule(item.rule, color),
            item.node,
            item.detail,
        )


# frob:ticket T-0861
def _log_sys_proved(waived, *, label: str, gap_kind: str) -> None:  # noqa: ANN001
    """Log the `<label> PROVED` summary line, carrying the waived count
    inline (T-0174 REJECT round honesty fix). Shared by self-conformance/
    contention/reliability's proved-summary line (T-0861 dup group)."""
    color = _stdout_color()
    if waived:
        _log.info(
            "sys audit: %s %s (%d waived) -- zero UNWAIVED %s",
            label,
            style_ok("PROVED", color),
            len(waived),
            gap_kind,
        )
    else:
        _log.info(
            "sys audit: %s %s -- zero %s", label, style_ok("PROVED", color), gap_kind
        )


# frob:ticket T-0150
def _log_waived_selfconform(report: SelfConformReport) -> None:
    """Log every waived self-conformance violation (T-0174: ALWAYS printed,
    matching `_print_audit_report`'s "loud in output" WAIVED line)."""
    _log_sys_waived_findings(report.waived)


def _log_selfconform_proved(report: SelfConformReport) -> None:
    """Log the self-conformance PROVED summary line, carrying the waived
    count inline (T-0174 REJECT round: same honesty fix as
    `_print_audit_report`)."""
    _log_sys_proved(report.waived, label="self-conformance", gap_kind="SYS gaps")


def _log_selfconform_violations(report: SelfConformReport) -> None:
    """Log every self-conformance violation, one per line."""
    _log_sys_findings(report.violations, label="self-conformance")


def _print_selfconform_report(report: SelfConformReport) -> None:
    """Print `frob sys audit`'s self-conformance summary (T-0150): every
    SYS100 (undeclared interface)/SYS101 (stale design)/SYS102 (unmodeled
    code) violation, one per line, matching `_print_audit_report`'s
    CI-parseable style."""
    _log_waived_selfconform(report)
    if not report.violations:
        _log_selfconform_proved(report)
        return
    _log_selfconform_violations(report)


# frob:ticket T-0724
def _log_waived_contention(report: ResourceContentionReport) -> None:
    """Log every waived SYS2xx resource-contention finding (T-0174: ALWAYS
    printed, matching `_print_audit_report`/`_log_waived_selfconform`'s
    "loud in output" WAIVED line)."""
    _log_sys_waived_findings(report.waived)


# frob:ticket T-0724
def _log_contention_proved(report: ResourceContentionReport) -> None:
    """Log the SYS2xx resource-contention PROVED summary line, carrying the
    waived count inline (same honesty convention as `_log_selfconform_
    proved`)."""
    _log_sys_proved(report.waived, label="resource-contention", gap_kind="SYS2xx gaps")


# frob:ticket T-0724
def _log_contention_violations(report: ResourceContentionReport) -> None:
    """Log every SYS2xx resource-contention violation, one per line."""
    _log_sys_findings(report.violations, label="resource-contention")


# frob:ticket T-0724
def _print_contention_report(report: ResourceContentionReport) -> None:
    """Print `frob sys audit`'s SYS2xx resource-contention summary (T-0724
    wiring the T-0699 `check_resource_contention` check into production):
    every SYS200 (duplicate port)/SYS201 (overlapping owns/acl)/SYS202
    (shared pipe)/SYS203 (shared store write) violation, one per line,
    matching `_print_selfconform_report`'s CI-parseable style."""
    _log_waived_contention(report)
    if not report.violations:
        _log_contention_proved(report)
        return
    _log_contention_violations(report)


# frob:ticket T-1061
def _log_waived_mode_conformance(report: ModeConformanceReport) -> None:
    """Log every waived SYS205 mode-conformance finding (T-0174: ALWAYS
    printed, matching `_log_waived_contention`'s "loud in output" WAIVED
    line -- `check_mode_conformance` gained real waiver application
    alongside this ticket's CLI wiring, `_mode_conformance.py`'s
    `_apply_mode_conformance_waivers`)."""
    _log_sys_waived_findings(report.waived)


# frob:ticket T-1061
def _log_mode_conformance_proved(report: ModeConformanceReport) -> None:
    """Log the SYS205 mode-conformance PROVED summary line, carrying the
    waived count inline (same honesty convention as `_log_contention_
    proved`)."""
    _log_sys_proved(report.waived, label="mode-conformance", gap_kind="SYS205 gaps")


# frob:ticket T-1061
def _log_mode_conformance_violations(report: ModeConformanceReport) -> None:
    """Log every SYS205 mode-conformance violation, one per line, matching
    `_log_contention_violations`'s CI-parseable style."""
    for v in report.violations:
        _log.error(
            "sys audit: GAP mode-conformance (SYS205): node=%s resource=%s "
            "mode=%s category=%s detail=%s",
            v.node,
            v.resource,
            v.mode.value,
            v.category,
            v.detail,
        )


# frob:ticket T-1061
def _print_mode_conformance_report(report: ModeConformanceReport) -> None:
    """Print `frob sys audit`'s SYS205 mode-conformance summary (T-1061
    wiring the T-0701/T-1060 `check_mode_conformance` check into
    production): every SYS205 violation, one per line, matching
    `_print_contention_report`'s CI-parseable style."""
    _log_waived_mode_conformance(report)
    if not report.violations:
        _log_mode_conformance_proved(report)
        return
    _log_mode_conformance_violations(report)


# frob:ticket T-0640
def _log_waived_reliability(report: ReliabilityReport) -> None:
    """Log every waived REL2xx reliability finding (T-0174: ALWAYS
    printed, matching `_log_waived_contention`'s "loud in output" WAIVED
    line)."""
    _log_sys_waived_findings(report.waived)


# frob:ticket T-0640
def _log_reliability_proved(report: ReliabilityReport) -> None:
    """Log the REL2xx reliability PROVED summary line, carrying the waived
    count inline (same honesty convention as `_log_contention_proved`)."""
    _log_sys_proved(report.waived, label="reliability", gap_kind="REL2xx gaps")


# frob:ticket T-0640
def _log_reliability_violations(report: ReliabilityReport) -> None:
    """Log every REL2xx reliability violation, one per line."""
    _log_sys_findings(report.violations, label="reliability")


# frob:ticket T-0640
# frob:ticket T-0644
def _print_reliability_report(report: ReliabilityReport) -> None:
    """Print `frob sys audit`'s REL2xx reliability summary (T-0640 wiring
    `check_reliability_timeouts` into production, mirroring T-0724's
    contention wiring; T-0644 adds `check_reliability_health`'s findings
    into the SAME combined report `_run_audit` builds): every REL200
    (missing timeout)/REL201 (unproven timeout)/REL210 (missing health)/
    REL211 (unproven health) violation, one per line, matching
    `_print_contention_report`'s CI-parseable style."""
    _log_waived_reliability(report)
    if not report.violations:
        _log_reliability_proved(report)
        return
    _log_reliability_violations(report)


# frob:ticket T-0158
def _print_capability_matrix_report() -> bool:
    """Print the T-0158 capability-coverage proof line beside self-
    conformance: 'capability coverage: N kinds x M languages, K cells
    patterned+proven, J excused with reasons, 0 unexcused' -- makes the
    exhaustiveness claim (every reserved kind provably detected in every
    supported language, or specifically excused) a printed, checkable
    proof rather than folklore. Returns True iff there are zero unexcused
    empty cells (the gate condition `_run_audit` must honor)."""
    cells = capability_matrix()
    patterned = sum(1 for c in cells if c.patterned)
    excused = sum(1 for c in cells if c.excused and not c.patterned)
    unexcused = [c for c in cells if not c.patterned and not c.excused]
    _log.info(
        "sys audit: capability coverage: %d kind(s) x %d language(s), "
        "%d cell(s) patterned+proven, %d excused with reasons, %d unexcused",
        len(CAPABILITY_KINDS),
        len(LANGUAGES),
        patterned,
        excused,
        len(unexcused),
    )
    color = _stderr_color()
    for cell in unexcused:
        _log.error(
            "sys audit: MATRIX %s capability_kind=%s language=%s -- "
            "unpatterned and unexcused",
            style_fail("GAP", color),
            cell.capability_kind,
            cell.language,
        )
    return not unexcused


# frob:ticket T-0115
# frob:ticket T-0150
# frob:ticket T-0724
def _load_audit_model(
    root: Path,
) -> tuple[KernelModel, frozenset[str], Module] | None:
    """Load+merge every `.strata` design file under `root`'s design dir for
    `frob sys audit`, or `None` (already logged) when there are none. Exits
    1 on any load error -- `sys audit` cannot proceed on a partial model.
    Returns `(model, store_ids, resource_module)` -- `store_ids` (T-0724)
    is `DesignIds.store_ids`, the pre-elaboration `Module.stores` id set
    every loaded file declared, threaded through so `check_resource_
    contention`'s SYS203 (shared store write) can actually fire.
    `resource_module` (T-1061) is a throwaway `Module` carrying only
    `DesignIds.resources` (every loaded file's pre-elaboration
    `Module.resources`, merged) -- `check_mode_conformance`'s (and
    `check_resource_contention`'s own optional `module=`) ONLY use for a
    `Module` argument is `.resources`, so a full re-parse/merge of every
    OTHER `Module` field is unnecessary; `Module`'s other fields all
    default to empty."""
    design_dir = _design_dir(root)
    ids = load_design_ids(root, design_dir)
    if ids.errors:
        for error in ids.errors:
            _log.error("sys audit: %s failed to load: %s", error.path, error.error)
        sys.exit(1)
    if not ids.models:
        _log.info("sys audit: no design models under %s/%s", root, design_dir)
        return None
    resource_module = Module(name="sys-audit-resources", resources=ids.resources)
    return merge_models(ids.models), ids.store_ids, resource_module


def _evaluate_audit(model: KernelModel, root: Path):  # noqa: ANN201
    """Run the THREAT001-003/COMPLIANCE001-002 exhaustiveness conjunction
    plus the SYS100-102 self-conformance check against `model`, exiting 1
    (already logged) if either evaluation itself errors. T-0017 (graphite
    adoption): `benign` is `DEFAULT_BENIGN_CAPABILITIES` PLUS whatever this
    repo declares in `frob.toml`'s `[[strata.benign_capabilities]]` -- a
    consuming repo's genuinely-benign, non-tier-2 `may` kind (e.g.
    `html_render`/`client_storage` on a browser-only node) no longer needs a
    `waive "THREAT002:<kind>"` naming a gap frob itself must patch; it can
    declare the excuse in its own frob.toml instead."""
    repo_benign = load_repo_benign_capabilities(root)
    if repo_benign.is_err:
        _log.error("sys audit: %s", repo_benign.danger_err)
        sys.exit(1)
    benign = DEFAULT_BENIGN_CAPABILITIES + repo_benign.danger_ok

    # frob:ticket T-0499
    # Live gate-rule-id set so rule-id-shaped `caught_by` references
    # (THREAT006/COMPLIANCE004) can actually resolve instead of always
    # being treated as unresolved (T-0382 left this defaulting to empty).
    audited = evaluate_exhaustiveness(
        model, benign=benign, known_rule_ids=known_gate_rule_ids()
    )
    if audited.is_err:
        _log.error("sys audit: %s", audited.danger_err)
        sys.exit(1)

    selfconform = check_self_conformance(model, root)
    if selfconform.is_err:
        _log.error("sys audit: self-conformance: %s", selfconform.danger_err)
        sys.exit(1)

    return audited.danger_ok, selfconform.danger_ok


# `frob sys audit` is the CI-ready checking counterpart to `frob sys doc`'s
# human-facing matrix rendering (T-0115): it evaluates the full three-part
# exhaustiveness conjunction (THREAT001-003 for security/quality,
# COMPLIANCE001-002 for compliance, docs/strata/threat.md
# #the-exhaustiveness-proof-the-point) for every `.strata` design file under
# the repo's design dir against EVERY configured baseline view, PLUS the
# SYS100-102 self-conformance check (T-0150: vet's own capability scanner
# pointed at OUR src/ tree, reconciled against `[strata.code_map]`/
# `[strata.capability_map]` in frob.toml).
# frob:ticket T-0640
# frob:ticket T-0644
def _run_audit(cfg: AppConfig) -> None:
    """`frob sys audit`: run the full exhaustiveness + self-conformance +
    SYS2xx resource-contention + SYS205 mode-conformance + REL2xx
    reliability check (see the comment above; T-0724 added the
    resource-contention leg, T-0640 added the REL200/REL201 timeout leg,
    T-0644 added the REL210/REL211 health leg, T-1061 added the SYS205
    mode-conformance leg) and exit nonzero with a named-gap summary when
    any part fails."""
    root = _resolve_design_root(cfg, "audit")
    loaded = _load_audit_model(root)
    if loaded is None:
        return
    model, store_ids, resource_module = loaded

    report, selfconform = _evaluate_audit(model, root)
    # T-1146: `resource_module` (built above for SYS205's `check_mode_
    # conformance` call) is now ALSO passed as `check_resource_contention`'s
    # `module=` -- SYS203/SYS201's arbiter-awareness (T-1025/T-1149) was
    # fully built and tested but never wired into this LIVE `frob sys
    # audit` call site until now (this ticket's own disclosed-gap closure,
    # the T-1061 scope note this comment used to carry).
    contention = check_resource_contention(
        model, store_ids=store_ids, module=resource_module
    )
    binding = bind_code(model, root)
    if binding.is_err:
        _log.error("sys audit: mode-conformance: %s", binding.danger_err)
        sys.exit(1)
    mode_conformance = check_mode_conformance(
        model, resource_module, binding.danger_ok, root
    )
    reliability = check_reliability_timeouts(model, root)
    if reliability.is_err:
        _log.error("sys audit: reliability: %s", reliability.danger_err)
        sys.exit(1)
    health = check_reliability_health(model, root)
    if health.is_err:
        _log.error("sys audit: reliability health: %s", health.danger_err)
        sys.exit(1)
    combined_reliability = ReliabilityReport(
        violations=reliability.danger_ok.violations + health.danger_ok.violations,
        waived=reliability.danger_ok.waived + health.danger_ok.waived,
    )
    _print_audit_report(report)
    _print_selfconform_report(selfconform)
    _print_contention_report(contention)
    _print_mode_conformance_report(mode_conformance)
    _print_reliability_report(combined_reliability)
    matrix_proved = _print_capability_matrix_report()
    if (
        not report.proved
        or selfconform.violations
        or contention.violations
        or mode_conformance.violations
        or combined_reliability.violations
        or not matrix_proved
    ):
        sys.exit(1)


# ---------------------------------------------------------------------------
# trace (T-1480)
# ---------------------------------------------------------------------------


# frob:ticket T-1480
def _print_trace_report(
    paths: dict[str, tuple[str, ...]], *, to: str | None
) -> bool:
    """Print `frob sys trace`'s witness-path report; returns True iff the
    requested destination (or, with no `to`, the closure itself) is
    non-empty -- callers use this to decide the process exit code, the
    same proved/not-proved shape `_print_audit_report` uses."""
    if to is not None:
        witness = paths.get(to)
        if witness is None:
            _log.error("sys trace: %s is not reachable", to)
            return False
        _log.info("sys trace: %s reachable via %s", to, " -> ".join(witness))
        return True
    reached = sorted(node for node in paths if paths[node])
    if not reached:
        _log.info("sys trace: no node reachable")
        return False
    for node in reached:
        _log.info("sys trace: %s via %s", node, " -> ".join(paths[node]))
    return True


# frob:ticket T-1480
# frob:tests tests/unit/test_app_sys_trace.py::TestSysTrace.test_trace_prints_witness_path_to_destination  # noqa: E501
def _run_trace(cfg: AppConfig) -> None:
    """`frob sys trace <from> [to]` (T-1480): load every `.strata` design
    file under the repo's design dir (reusing `_load_audit_model`'s
    parse+merge, same as `audit`), build a `FactBase`, and print the
    influence-closure witness path from `cfg.sys_trace_from` -- to a
    specific `cfg.sys_trace_to` if given, else the whole closure.
    `--through-barriers` threads straight to `FactBase.reachable`'s own
    flag (positive reach claims vs. the default endorsement semantics that
    stop taint at a declared boundary). Exits 1 when the source node is
    unknown, or when the requested destination (or, with no destination,
    the whole closure) is unreachable -- vacuous-pass doctrine, same as
    `_run_audit`."""
    root = _resolve_design_root(cfg, "trace")
    loaded = _load_audit_model(root)
    if loaded is None:
        sys.exit(1)
    model, _store_ids, _resource_module = loaded

    facts = build_facts(model)
    if facts.is_err:
        _log.error("sys trace: %s", facts.danger_err)
        sys.exit(1)
    fact_base = facts.danger_ok
    src = cfg.sys_trace_from
    assert src is not None  # required positional, enforced by argparse
    if src not in fact_base.nodes:
        _log.error("sys trace: %s is not a known node", src)
        sys.exit(1)

    paths = fact_base.reachable(
        src, through_barriers=cfg.sys_trace_through_barriers
    )
    if not _print_trace_report(paths, to=cfg.sys_trace_to):
        sys.exit(1)


# ---------------------------------------------------------------------------
# threats (T-1925)
# ---------------------------------------------------------------------------


# frob:ticket T-1925
# frob:tests tests/unit/test_app_sys_threats.py::TestSysThreats.test_no_boundary_prints_every_violation  # noqa: E501
def _print_threats_report(
    violations: tuple, *, boundary: str | None
) -> bool:
    """Print `frob sys threats`'s violation list; returns True iff the
    result is empty (vacuous-pass doctrine, same as `_print_audit_report`/
    `_print_trace_report`: nothing found is the SUCCESS case here, since
    this prints violations, not witnesses)."""
    if not violations:
        if boundary is not None:
            _log.info("sys threats: no violations scoped to boundary %s", boundary)
        else:
            _log.info("sys threats: no violations")
        return True
    for v in sorted(violations, key=lambda v: (v.rule, v.cwe, v.node or "")):
        _log.error(
            "sys threats: %s%s%s -- %s",
            v.rule,
            f" {v.cwe}" if v.cwe else "",
            f" node={v.node}" if v.node else "",
            v.detail,
        )
    return False


# frob:ticket T-1925
# frob:tests tests/unit/test_app_sys_threats.py::TestSysThreats.test_boundary_scopes_to_its_own_zone_only  # noqa: E501
def _run_threats(cfg: AppConfig) -> None:
    """`frob sys threats [boundary]` (T-1925): load every `.strata` design
    file under the repo's design dir (reusing `_load_audit_model`'s
    parse+merge, same as `audit`/`trace`), evaluate the full THREAT001-005
    conjunction for `cfg.sys_view`, and print either the whole violation
    set (no `boundary` given, matching `sys trace`'s own "no destination =
    whole closure" default) or the subset `threat_violations_for_boundary`
    (T-1925's own node-to-boundary join) attributes to that boundary's
    protected zone. Exits 1 on a load/evaluate error, an unknown boundary
    id, or any violation printed -- vacuous-pass doctrine, same as
    `_run_audit`/`_run_trace`."""
    root = _resolve_design_root(cfg, "threats")
    loaded = _load_audit_model(root)
    if loaded is None:
        return
    model, _store_ids, _resource_module = loaded

    repo_benign = load_repo_benign_capabilities(root)
    if repo_benign.is_err:
        _log.error("sys threats: %s", repo_benign.danger_err)
        sys.exit(1)
    benign = DEFAULT_BENIGN_CAPABILITIES + repo_benign.danger_ok

    binding = bind_code(model, root)
    if binding.is_err:
        _log.error("sys threats: %s", binding.danger_err)
        sys.exit(1)

    report = evaluate_threats(
        model,
        cfg.sys_view,
        benign=benign,
        binding=binding.danger_ok,
        root=root,
    )
    if report.is_err:
        _log.error("sys threats: %s", report.danger_err)
        sys.exit(1)
    violations = report.danger_ok.violations

    boundary = cfg.sys_threats_boundary
    if boundary is not None:
        facts = build_facts(model)
        if facts.is_err:
            _log.error("sys threats: %s", facts.danger_err)
            sys.exit(1)
        scoped = threat_violations_for_boundary(violations, facts.danger_ok, boundary)
        if scoped.is_err:
            _log.error("sys threats: %s", scoped.danger_err)
            sys.exit(1)
        violations = scoped.danger_ok

    if not _print_threats_report(violations, boundary=boundary):
        sys.exit(1)


# ---------------------------------------------------------------------------
# capacity (T-1927)
# ---------------------------------------------------------------------------


# frob:ticket T-1927
# frob:tests tests/unit/test_app_sys_capacity.py::TestSysCapacity.test_no_population_reports_current_violations  # noqa: E501
def _print_capacity_report(report, *, population: float | None) -> bool:
    """Print `frob sys capacity`'s CAP001 findings; returns True iff none
    fired -- vacuous-pass doctrine, same as `_print_threats_report`."""
    if not report.violations:
        if population is not None:
            _log.info(
                "sys capacity: no violations projected at population=%s "
                "(scale=%s, baseline=%s)",
                population,
                report.scale_factor,
                report.baseline_population,
            )
        else:
            _log.info("sys capacity: no violations at current demand")
        return True
    for v in sorted(report.violations, key=lambda v: v.node):
        _log.error(
            "sys capacity: node=%s projected_demand=%s/s capacity=%s/s -- %s",
            v.node,
            v.projected_demand,
            v.capacity,
            v.detail,
        )
    return False


# frob:ticket T-1927
# frob:tests tests/unit/test_app_sys_capacity.py::TestSysCapacity.test_population_scales_and_can_fire  # noqa: E501
def _run_capacity(cfg: AppConfig) -> None:
    """`frob sys capacity [--population N]` (T-1927): load every `.strata`
    design file under the repo's design dir (reusing `_load_audit_model`'s
    parse+merge, same as `audit`/`trace`/`threats`), build a `FactBase`,
    and print `project_capacity`'s CAP001 findings -- optionally scaled to
    `cfg.sys_capacity_population`. Exits 1 on a load/build/project error
    (including `StrataError.UnknownReference` for a `--population` with
    no baseline `users` population to scale against) or any violation
    printed -- vacuous-pass doctrine, same as `_run_audit`/`_run_trace`/
    `_run_threats`."""
    root = _resolve_design_root(cfg, "capacity")
    loaded = _load_audit_model(root)
    if loaded is None:
        return
    model, _store_ids, _resource_module = loaded

    facts = build_facts(model)
    if facts.is_err:
        _log.error("sys capacity: %s", facts.danger_err)
        sys.exit(1)

    report = project_capacity(
        model, facts.danger_ok, population=cfg.sys_capacity_population
    )
    if report.is_err:
        _log.error("sys capacity: %s", report.danger_err)
        sys.exit(1)

    if not _print_capacity_report(
        report.danger_ok, population=cfg.sys_capacity_population
    ):
        sys.exit(1)


# frob:doc docs/modules/app.md#runners
# frob:doc docs/strata/host.md#resource-contention-sys2xx-t-0699
# frob:doc docs/strata/reliability.md#rel2xx-timeout-obligation-t-0640
# frob:waive AFFECT001 reason="the host.md/reliability.md anchors document the SYS2xx \
# resource-contention/REL2xx reliability CHECKS run() dispatches into (audit's own \
# machinery); docs/commands/sys.md's own drift is tracked by a filed follow-up (draft \
# T-draft-84b54204, out of this ticket's declared scope) rather than hand-patched here"
# frob:ticket T-0084
# frob:ticket T-0085
# frob:ticket T-0086
# frob:ticket T-0588
# frob:ticket T-1480
# frob:ticket T-1925
# frob:ticket T-1927
# frob:tests tests/unit/test_app_runners_batch7.py::TestSysRunnerDispatch.test_unknown_command_exits_1  # noqa: E501
def run(cfg: AppConfig) -> None:
    """Dispatch `frob sys <command>`: `plan` (T-0084), `doc` (T-0085),
    `export` (T-0086), `audit` (T-0115), `trace` (T-1480), `threats`
    (T-1925), and `capacity` (T-1927) all exist today -- every roadmap-
    phase-5 verb (docs/strata/roadmap.md "CLI surface (target)") is now
    wired; extend this dispatch with any future verb, never replace it.
    `check` was deliberately dropped from the target CLI surface rather
    than built (T-1926: it would duplicate `audit`). T-1870:
    `sync-interface` (T-1150) used to be a branch here; deleted along with
    its writer, per an explicit owner directive that no code path may
    auto-update declared public-symbol surface."""
    if cfg.sys_command == "plan":
        _run_plan(cfg)
        return
    if cfg.sys_command == "doc":
        _run_doc(cfg)
        return
    if cfg.sys_command == "audit":
        _run_audit(cfg)
        return
    if cfg.sys_command == "export":
        _run_export(cfg)
        return
    if cfg.sys_command == "trace":
        _run_trace(cfg)
        return
    if cfg.sys_command == "threats":
        _run_threats(cfg)
        return
    if cfg.sys_command == "capacity":
        _run_capacity(cfg)
        return
    _log.error(
        "usage: frob sys <plan|doc|export|audit|trace|threats|capacity> ..."
    )
    sys.exit(1)
