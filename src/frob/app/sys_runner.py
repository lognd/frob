"""CLI wiring for `frob sys` -- strata design-model applications
(docs/strata/roadmap.md phase 5, docs/commands/sys.md).

Three verbs today: `plan` (T-0084, obligation -> ticket compiler), `doc`
(T-0085, threat-catalog audit matrix), and `export` (T-0086, k8s/seccomp/
IAM config skeletons). `check`/`trace`/`capacity`/`threats` are later
phase-5 tickets, not yet landed -- `run` below should grow one more `if
cfg.sys_command == "..."` branch per verb as they land, never a parallel
dispatch mechanism.

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

# frob:waive TEST005 reason="module line coverage 0.0%, debt T-0160"

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from frob.app.config import AppConfig
from frob.graph import GraphSnapshot, build_graph, load_graph
from frob.logging import get_logger
from frob.logging.quiet import quiet_stdout_logs
from frob.strata import (
    DEFAULT_BENIGN_CAPABILITIES,
    DEFAULT_DESIGN_DIR,
    MARKER_PREFIX,
    AuditReport,
    KernelModel,
    PlannedTicket,
    SelfConformReport,
    check_self_conformance,
    evaluate_exhaustiveness,
    load_design_ids,
    load_repo_benign_capabilities,
    plan_obligations,
    render_audit_matrix,
)
from frob.strata._elaborate import elaborate
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


def _merge_models(models: tuple[KernelModel, ...]) -> KernelModel:
    """Concatenate every loaded design file's facts into one `KernelModel` so
    a multi-file design is planned as a single obligation surface."""
    return KernelModel(
        nodes=tuple(n for m in models for n in m.nodes),
        flows=tuple(f for m in models for f in m.flows),
        boundaries=tuple(b for m in models for b in m.boundaries),
        claims=tuple(c for m in models for c in m.claims),
        scenarios=tuple(s for m in models for s in m.scenarios),
    )


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

    model = _merge_models(ids.models)
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
    `KernelModel`, or None with an error already logged."""
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
        elaborated = elaborate(parsed.danger_ok)
        if elaborated.is_err:
            _log.error("frob sys export: elaborate failed: %s", elaborated.danger_err)
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

    renderer = {
        "k8s": export_k8s_netpol,
        "seccomp": export_seccomp,
        "iam": export_iam,
    }[fmt]
    print(renderer(model))


# ---------------------------------------------------------------------------
# doc (T-0085)
# ---------------------------------------------------------------------------


# frob:ticket T-0085
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

    model = _merge_models(ids.models)
    rendered = render_audit_matrix(model, cfg.sys_view)
    if rendered.is_err:
        _log.error("sys doc: %s", rendered.danger_err)
        sys.exit(1)
    print(rendered.danger_ok, end="")


def _log_waived_gaps(report: AuditReport) -> None:
    """Log every waived gap (T-0174: ALWAYS printed, proved or not -- a
    waiver must never make a run look silent, `_waive.py`'s "loud in
    output" requirement)."""
    for waived in report.waived:
        _log.warning(
            "sys audit: WAIVED family=%s view=%s rule=%s target=%s detail=%s",
            waived.family,
            waived.view,
            waived.rule,
            waived.target,
            waived.detail,
        )


def _log_proved_summary(report: AuditReport) -> None:
    """Log the PROVED summary line, carrying the waived count inline
    (T-0174 REJECT round: a separate WARNING line is lost under grep/
    quiet-mode filtering, so the count must ride the summary itself)."""
    if report.waived:
        _log.info(
            "sys audit: PROVED (%d waived) -- zero UNWAIVED gaps across "
            "every configured view",
            len(report.waived),
        )
    else:
        _log.info("sys audit: PROVED -- zero gaps across every configured view")


def _log_gaps(report: AuditReport) -> None:
    """Log every named gap, one per line (CI-parseable, no ambiguity about
    which conjunction member failed)."""
    _log.error("sys audit: %d gap(s) found", len(report.gaps))
    for gap in report.gaps:
        _log.error(
            "sys audit: GAP family=%s view=%s rule=%s detail=%s",
            gap.family,
            gap.view,
            gap.rule,
            gap.detail,
        )


# frob:ticket T-0115
def _print_audit_report(report: AuditReport) -> None:
    """Print `frob sys audit`'s machine-usable summary: which views were
    checked, then every named gap grouped by family (docs/strata/threat.md
    #the-exhaustiveness-proof-the-point: "every gap named, owned, and
    expiring") -- CI-parseable one-gap-per-line, no ambiguity about which
    conjunction member failed."""
    _log.info(
        "sys audit: checked %d view(s): %s",
        len(report.views_checked),
        ", ".join(report.views_checked),
    )
    _log_waived_gaps(report)
    if report.proved:
        _log_proved_summary(report)
        return
    _log_gaps(report)


# frob:ticket T-0150
def _log_waived_selfconform(report: SelfConformReport) -> None:
    """Log every waived self-conformance violation (T-0174: ALWAYS printed,
    matching `_print_audit_report`'s "loud in output" WAIVED line)."""
    for waived in report.waived:
        _log.warning(
            "sys audit: WAIVED family=sys rule=%s node=%s detail=%s",
            waived.rule,
            waived.node,
            waived.detail,
        )


def _log_selfconform_proved(report: SelfConformReport) -> None:
    """Log the self-conformance PROVED summary line, carrying the waived
    count inline (T-0174 REJECT round: same honesty fix as
    `_print_audit_report`)."""
    if report.waived:
        _log.info(
            "sys audit: self-conformance PROVED (%d waived) -- zero UNWAIVED SYS gaps",
            len(report.waived),
        )
    else:
        _log.info("sys audit: self-conformance PROVED -- zero SYS gaps")


def _log_selfconform_violations(report: SelfConformReport) -> None:
    """Log every self-conformance violation, one per line."""
    _log.error("sys audit: %d self-conformance gap(s) found", len(report.violations))
    for violation in report.violations:
        _log.error(
            "sys audit: GAP family=sys rule=%s node=%s detail=%s",
            violation.rule,
            violation.node,
            violation.detail,
        )


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
    for cell in unexcused:
        _log.error(
            "sys audit: MATRIX GAP capability_kind=%s language=%s -- "
            "unpatterned and unexcused",
            cell.capability_kind,
            cell.language,
        )
    return not unexcused


# frob:ticket T-0115
# frob:ticket T-0150
def _load_audit_model(root: Path) -> KernelModel | None:
    """Load+merge every `.strata` design file under `root`'s design dir for
    `frob sys audit`, or `None` (already logged) when there are none. Exits
    1 on any load error -- `sys audit` cannot proceed on a partial model."""
    design_dir = _design_dir(root)
    ids = load_design_ids(root, design_dir)
    if ids.errors:
        for error in ids.errors:
            _log.error("sys audit: %s failed to load: %s", error.path, error.error)
        sys.exit(1)
    if not ids.models:
        _log.info("sys audit: no design models under %s/%s", root, design_dir)
        return None
    return _merge_models(ids.models)


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

    audited = evaluate_exhaustiveness(model, benign=benign)
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
def _run_audit(cfg: AppConfig) -> None:
    """`frob sys audit`: run the full exhaustiveness + self-conformance
    check (see the comment above) and exit nonzero with a named-gap
    summary when any part fails."""
    root = _resolve_design_root(cfg, "audit")
    model = _load_audit_model(root)
    if model is None:
        return

    report, selfconform = _evaluate_audit(model, root)
    _print_audit_report(report)
    _print_selfconform_report(selfconform)
    matrix_proved = _print_capability_matrix_report()
    if not report.proved or selfconform.violations or not matrix_proved:
        sys.exit(1)


# frob:doc docs/modules/app.md#runners
# frob:ticket T-0084
# frob:ticket T-0085
# frob:ticket T-0086
# frob:waive TEST005 reason="run 0.0% branch cover, debt T-0160"
def run(cfg: AppConfig) -> None:
    """Dispatch `frob sys <command>`: `plan` (T-0084), `doc` (T-0085), and
    `export` (T-0086) exist today; roadmap phase 5's `check`/`trace`/
    `capacity`/`threats` are later tickets -- extend this dispatch, never
    replace it."""
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
    _log.error("usage: frob sys <plan|doc|export> ...")
    sys.exit(1)
