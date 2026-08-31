"""frob.gates._sys -- SYS00x/DOC003/SELFAUDIT001 strata design-conformance
gate family (T-1187).

Split out of `frob.gates.__init__` (T-1072/T-1140/T-1159/T-1170/T-1174/
T-1183/T-1187 one-family-per-land discipline, `_fuzz.py`'s T-1183
precedent) so the parent module can keep dropping toward the large-file
threshold without changing any public behavior. `sys_gate` and
`_load_test_config` are re-exported from `frob.gates` unchanged -- the
names this family is externally imported by (`tests/test_gates.py`,
`_ALL_GATES`'s process-job table, `_load_inputs`'s config loading); every
other symbol here stays private to this module.

One cohesive family: `_load_systems`/`_load_test_config` parse the
`[[system]]`/`[testing]` frob.toml tables; `sys_gate` composes SYS001
(dangling directive), SYS002 (unbound boundary/secret), SYS003
(undeclared cross-component import), SYS004 (design file load failure),
DOC003 (unproved `frob:claims` marker), and SELFAUDIT001 (frob's own
self-conformance/resource-contention/reliability/compliance audit
surface, T-0756/T-1314) -- all opt-in behind a `design/` (or
`[strata].design_dir`) directory
existing, with the `frob.strata` import deferred until after that check
(T-0135: a repo with no design dir must never pay the `strata_core`
native-extension import cost).

The SELFAUDIT001 sub-family itself (`_selfaudit_violations`/
`_compliance_selfaudit_violations`) is split out into
`frob.gates._sys_selfaudit` (T-1420, LARGE001 residue burndown) -- this
module imports and calls both, `sys_gate` is otherwise unchanged.
"""
# frob:ticket T-1187

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from pydantic import ValidationError

from frob.gates._doclink_docanchor import _doclink_config, _obligated_docs
from frob.gates._models import Severity, SystemSpec, TestPolicy, Violation
from frob.gates._sys_selfaudit import (
    _compliance_selfaudit_violations,
    _selfaudit_violations,
)
from frob.graph import Edge, EdgeKind, GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)


def _load_systems(doc: dict) -> tuple[SystemSpec, ...]:
    """Parse the `[[system]]` array from a frob.toml document; bad entries skipped."""
    systems: list[SystemSpec] = []
    for entry in doc.get("system", []):
        try:
            systems.append(
                SystemSpec(
                    id=entry["id"],
                    entrypoint=entry.get("entrypoint", ""),
                    min_e2e=entry.get("min_e2e", 1),
                    paths=tuple(entry.get("paths", ())),
                )
            )
        except (KeyError, ValidationError) as exc:
            _log.warning("_load_test_config: bad [[system]] entry: %s", exc)
    return tuple(systems)


def _load_test_config(root: Path) -> tuple[TestPolicy, tuple[SystemSpec, ...]]:
    """`[testing]` -> `TestPolicy`, `[[system]]` -> `SystemSpec` tuple;
    both optional."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return TestPolicy(), ()
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, ValueError) as exc:
        _log.warning("_load_test_config: could not parse %s: %s", toml_path, exc)
        return TestPolicy(), ()

    testing_tbl = doc.get("testing", {})
    fields = TestPolicy.model_fields
    try:
        policy = TestPolicy(**{k: v for k, v in testing_tbl.items() if k in fields})
    except ValidationError as exc:
        _log.warning("_load_test_config: bad [testing] table: %s", exc)
        policy = TestPolicy()

    return policy, _load_systems(doc)


# ---------------------------------------------------------------------------
# SYS001 / SYS002: strata directive <-> design binding (T-0080)
# ---------------------------------------------------------------------------

_SYS_DIRECTIVE_KINDS: dict[EdgeKind, str] = {
    EdgeKind.CHANNEL: "channels",
    EdgeKind.BOUNDARY: "boundaries",
    EdgeKind.SECRET: "secrets",
}
#: Mirrors `frob.strata._design_load.DEFAULT_DESIGN_DIR`. Duplicated as a
#: bare literal (rather than imported) so `_design_dir` -- called as
#: `sys_gate`'s FIRST statement, before the opt-in existence check below --
#: never touches `frob.strata` for a repo that has no design dir at all
#: (T-0135: `frob.strata` transitively imports `_facts.py`, which needs the
#: `strata_core` native extension, and a standalone tool install must not
#: pay that cost, or risk that import failing, on every single repo).
_DEFAULT_DESIGN_DIR = "design"


def _design_dir(root: Path) -> str:
    """`[strata].design_dir` from frob.toml, defaulting to `_DEFAULT_DESIGN_DIR`."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return _DEFAULT_DESIGN_DIR
    try:
        with toml_path.open("rb") as fh:
            return (
                tomllib.load(fh)
                .get("strata", {})
                .get("design_dir", _DEFAULT_DESIGN_DIR)
            )
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("sys_gate: frob.toml unreadable: %s", exc)
        return _DEFAULT_DESIGN_DIR


def _sys004_native_hint(root: Path) -> str:
    """Extra SYS004 clause naming `make core` as the likely remedy when a
    declared native is stale against its own source tree (T-0248's
    `frob.strata.stale_natives`), distinguishing a grammar/native version
    mismatch from a genuine syntax error in the `.strata` file itself --
    the original T-0166 incident's fix (2): a design file failed to load
    with a mysterious "unknown construct" error because the built
    `strata_core` predated a landed grammar change, and nothing at the
    SYS004 call site said so. Returns the empty string when no native is
    stale, so callers can unconditionally append it to the base message."""
    from frob.strata import stale_natives

    stale = stale_natives(root)
    if not stale:
        return ""
    names = ", ".join(sorted({s.spec.name for s in stale}))
    return (
        f" -- built extension(s) [{names}] are older than their own source "
        f"tree, which can itself cause a parse failure on a construct the "
        f"grammar added since the last build; run `make core` first and "
        f"re-check before treating this as a genuine `.strata` syntax error"
    )


# frob:tests tests/test_gates.py::TestSysGate.test_sys004_load_failure
# frob:tests tests/test_gates.py::TestSysGate.test_sys004_suppresses_sys001
# frob:tests tests/test_gates.py::TestSysGate.test_sys004_names_stale_native_as_likely_remedy  # noqa: E501
# frob:tests tests/test_gates.py::TestSysGate.test_sys004_names_missing_native_hint_when_genuinely_absent  # noqa: E501
# frob:tests tests/test_gates.py::TestSysGate.test_sys004_names_real_exception_when_strata_core_fails_differently  # noqa: E501
# frob:enforces CHK-GATE-SYS004
def _sys004(design_ids, root: Path) -> list[Violation]:
    """SYS004: a `.strata` design file itself failed to parse/elaborate.

    Reported as its own rule, distinct from SYS001, because a load failure
    and a dangling reference are different problems with different fixes
    (fix the design file vs. fix the directive) -- collapsing them would
    misdirect whoever reads the message (reviewer-caught, T-0080 REJECT
    round 1). Also names a stale native build as a likely cause (T-0248
    follow-up) when one is detected, per the T-0166 incident precedent.

    T-2707: when `error.detail` is set (only possible for a
    `NativeExtensionUnavailable` error), the REAL caught exception is
    appended alongside the friendly not-installed hint rather than
    silently displacing it -- a `strata_core` present-but-failing-to-
    import case (an ABI/symbol mismatch, a failing secondary import
    inside the extension) previously read identically to a genuinely
    absent extension and misdirected diagnosis toward reinstalling."""
    native_hint = _sys004_native_hint(root)
    return [
        Violation(
            rule="SYS004",
            severity=Severity.ERROR,
            file=error.path,
            line=0,
            message=(
                f"SYS004: {error.path} failed to load ({error.error.value}); "
                f"fix the .strata file -- SYS001 dangling-reference checks are "
                f"suppressed while any design file fails to load, since ids are "
                f"merged across all design files and a missing sibling's ids "
                f"cannot be told apart from a genuinely dangling reference"
                f"{native_hint}"
                + (f" -- actual import error: {error.detail}" if error.detail else "")
            ),
        )
        for error in design_ids.errors
    ]


def _sys001(snapshot: GraphSnapshot, design_ids) -> list[Violation]:  # noqa: ANN001
    """SYS001: a `frob:channel/boundary/secret` directive names a construct id
    that does not exist in the loaded design model -- a dangling reference,
    same posture as DRIFT002.

    Suppressed entirely when any `.strata` design file failed to load
    (`design_ids.errors`): construct ids are merged across every design
    file with no per-file provenance, so a failed sibling file's would-be
    ids are indistinguishable from a genuinely dangling reference -- fail
    toward the honest `SYS004` diagnostic (`sys_gate`), not a misleading
    SYS001 (reviewer-caught, T-0080 REJECT round 1: a single malformed
    design file was making every directive referencing its ids look
    dangling)."""
    if design_ids.errors:
        _log.debug(
            "SYS001: suppressed, %d design file(s) failed to load",
            len(design_ids.errors),
        )
        return []
    valid = {
        EdgeKind.CHANNEL: design_ids.channels,
        EdgeKind.BOUNDARY: design_ids.boundaries,
        EdgeKind.SECRET: design_ids.secrets,
    }
    return [
        v
        for edge in snapshot.edges
        if edge.kind in _SYS_DIRECTIVE_KINDS
        for v in (_sys001_check_edge(edge, valid),)
        if v is not None
    ]


# frob:enforces CHK-GATE-SYS001
def _sys001_check_edge(
    edge: Edge, valid: dict[EdgeKind, frozenset[str]]
) -> Violation | None:
    """The SYS001 `Violation` for one `frob:channel/boundary/secret` edge,
    or None when its target resolves in the loaded design model."""
    if edge.target in valid[edge.kind]:
        return None
    from frob.gates import _site_from_edge_origin  # local: avoids circularity

    file, line = _site_from_edge_origin(edge.origin)
    _log.debug("SYS001: %s -> %s not in design model", edge.src, edge.target)
    return Violation(
        rule="SYS001",
        severity=Severity.ERROR,
        file=file,
        line=line,
        message=(
            f"SYS001: frob:{edge.kind.value} {edge.target} at {edge.src} "
            f"does not name a {_SYS_DIRECTIVE_KINDS[edge.kind]} construct "
            f"in the loaded design model; fix the id or add it to the "
            f".strata design"
        ),
    )


# frob:enforces CHK-GATE-SYS003
def _sys003_one_model(model, root: Path) -> list[Violation]:  # noqa: ANN001
    """SYS003 violations from one design model's tier-2 code-binding
    conformance check (`bind_code` + `check_import_conformance`); an
    ambiguous binding within this model is logged and skipped, never fatal
    to the whole gate (a model's `code=` globs are scoped to its own
    nodes, so ambiguity here is a design-file bug, not a cross-model
    concern)."""
    from frob.strata import bind_code, check_import_conformance

    bound = bind_code(model, root)
    if bound.is_err:
        _log.warning("SYS003: code binding ambiguous, skipping: %s", bound.danger_err)
        return []
    report = check_import_conformance(model, bound.danger_ok, root)
    return [
        Violation(
            rule="SYS003",
            severity=Severity.ERROR,
            file=violation.file,
            line=violation.line,
            message=(
                f"SYS003: undeclared cross-component import {violation.spec} at "
                f"{violation.file}:{violation.line} ({violation.src_component} -> "
                f"{violation.dst_component}); declare a Flow in that direction or "
                f"remove the import"
            ),
        )
        for violation in report.violations
    ]


def _sys003(design_ids, root: Path) -> list[Violation]:
    """SYS003: an in-repo import crosses two design-bound files with no
    declared `Flow` in that direction (docs/strata/surface.md#code-binding-
    tier-2-v0-implementation's "not yet wired" SYS-gate surfacing, T-0080).
    Runs once per successfully elaborated design model."""
    violations: list[Violation] = []
    for model in design_ids.models:
        violations.extend(_sys003_one_model(model, root))
    return violations


# frob:enforces CHK-GATE-SYS002
def _sys002(snapshot: GraphSnapshot, design_ids) -> list[Violation]:  # noqa: ANN001
    """SYS002: a boundary or secret construct in the design model has no
    `frob:boundary`/`frob:secret` code binding anywhere -- the construct
    exists on paper but nothing in code attests it (docs/strata/surface.md
    #directives-t-0080). Detection is `frob.strata._design_load.
    unbound_constructs`, imported lazily here (not at module top) for the
    same reason `_sys003_one_model` does: a repo with no design dir must
    never pay `frob.strata`'s `strata_core` native-extension import cost
    (T-0135) -- shared with `frob.strata.plan_obligations`'s "unbound"
    frontier so the join lives in exactly one place (T-0084 review
    finding 1)."""
    from frob.strata import unbound_constructs

    violations: list[Violation] = []
    for kind, construct_id in unbound_constructs(design_ids, snapshot):
        _log.debug("SYS002: %s %s has no code binding", kind.value, construct_id)
        violations.append(
            Violation(
                rule="SYS002",
                severity=Severity.WARN,
                file=f"design/{kind.value}/{construct_id}",
                line=0,
                message=(
                    f"SYS002: {kind.value} {construct_id} has no code binding; "
                    f"add: frob:{kind.value} {construct_id} at the enforcing site"
                ),
            )
        )
    return violations


_CLAIMS_RE = re.compile(r"<!--\s*frob:claims\s+(?P<view>\S+)\s*-->")
_FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
_INLINE_CODE_SPAN_RE = re.compile(r"`[^`]*`")


def _strip_inline_code_spans(line: str) -> str:
    """Blank out every inline `code span` on `line` (paired single
    backticks), preserving column positions so line/column reporting
    elsewhere never has to know this ran. A directive quoted inside
    backticks -- the natural way to DOCUMENT the directive in prose --
    must never be mistaken for a live claim (reviewer-caught, T-0085
    round 2)."""
    return _INLINE_CODE_SPAN_RE.sub(lambda m: " " * len(m.group(0)), line)


# frob:ticket T-0085
def _claims_markers(root: Path) -> list[tuple[str, int, str]]:
    """Every `<!-- frob:claims <view> -->` doc marker under the doclink
    doc set (T-0085, docs/strata/threat.md#the-exhaustiveness-proof-the-
    point): `(file, line, view)`, reusing `doclink_gate`'s own `include`/
    `exclude`/`roots` config so the claims scan and the doc-obligation
    scan never disagree about which files are docs (charter: no
    duplication).

    Fence- and inline-code-aware (reviewer-caught, T-0085 round 2): a
    marker written to DOCUMENT the directive -- inside a fenced ```/~~~
    block, or inside inline `backticks` on the same line -- is prose
    ABOUT the directive, not a live claim, and must never be extracted.
    Fence state is a simple line-by-line open/close toggle (a line
    starting with three-or-more backticks or tildes, ignoring leading
    whitespace, flips it); inline spans are blanked out before matching
    so a marker can still be found elsewhere on the same line outside any
    span. A single unmatched inline backtick that never closes on the
    same line does not affect fence state -- CommonMark inline code spans
    never cross a line boundary."""
    include, exclude, roots = _doclink_config(root)
    paths = _obligated_docs(root, include, exclude) | set(roots)
    found: list[tuple[str, int, str]] = []
    for rel in sorted(paths):
        found.extend(_claims_markers_in_file(root, rel))
    return found


# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1056: leaked Unknown traces to \
# _strip_inline_code_spans/_CLAIMS_RE.search/_FENCE_RE.match, plain regex/str \
# operations on the already-caught read_text() result; no further raise path is \
# reachable from this function's locally-visible calls"
def _claims_markers_in_file(root: Path, rel: str) -> list[tuple[str, int, str]]:
    """Every live (non-fenced, non-inline-code) `frob:claims` marker in one
    doc file, as `(rel, line, view)` triples."""
    path = root / rel
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    found: list[tuple[str, int, str]] = []
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _FENCE_RE.match(line) is not None:
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _CLAIMS_RE.search(_strip_inline_code_spans(line))
        if match is not None:
            found.append((rel, lineno, match.group("view")))
    return found


# frob:ticket T-0085
# frob:enforces CHK-GATE-DOC003
def _doc003_violation(rel: str, lineno: int, message: str) -> Violation:
    """Build one DOC003 error `Violation` -- every failure mode is the same shape."""
    return Violation(
        rule="DOC003", severity=Severity.ERROR, file=rel, line=lineno, message=message
    )


# frob:ticket T-0085
def _doc003_one_marker(model, rel: str, lineno: int, view: str) -> Violation | None:  # noqa: ANN001
    """One `frob:claims <view>` marker's DOC003 outcome: `None` (proved),
    an unknown-view error, or a not-proved error naming the failing
    obligations."""
    from frob.strata import audit_claim

    result = audit_claim(model, view)
    if result.is_err:
        return _doc003_violation(
            rel,
            lineno,
            f"DOC003: frob:claims {view!r} names an unknown baseline view "
            f"({result.danger_err.value}); fix the view name",
        )
    audit = result.danger_ok
    if audit.proved:
        return None
    named = "; ".join(
        f"{v.rule} {v.cwe or v.capability or ''}: {v.detail}".strip()
        for v in audit.violations
    )
    return _doc003_violation(
        rel,
        lineno,
        f"DOC003: frob:claims {view!r} is not a PROVED exhaustiveness result "
        f"against the design model -- failing obligation(s): {named}",
    )


# frob:ticket T-0085
# DOC003: a `frob:claims <view>` doc marker whose view is not PROVED (zero
# THREAT001/THREAT002/THREAT003 violations) against the current design
# model is an error naming the failing obligations (docs/strata/threat.md
# #the-exhaustiveness-proof-the-point: "a README claiming 'protected
# against the OWASP Top 10' must cite a PROVED exhaustiveness result or it
# fails CI"). DOC002 is already taken (anchor resolution, T-0127), hence
# DOC003 for the claims audit (charter drift noted in docs/strata/threat.md).
def _doc003(root: Path, design_ids) -> list[Violation]:  # noqa: ANN001
    """DOC003: see the comment above. Suppressed when any design file
    failed to load (same posture as SYS001) -- a claim cannot be honestly
    evaluated against a partially loaded model. Runs no doc I/O at all when
    no `frob:claims` marker exists anywhere."""
    markers = _claims_markers(root)
    if not markers:
        return []
    if design_ids.errors:
        _log.debug(
            "DOC003: suppressed, %d design file(s) failed to load",
            len(design_ids.errors),
        )
        return []

    from frob.strata import merge_models

    model = merge_models(design_ids.models)
    violations = [
        v
        for rel, lineno, view in markers
        if (v := _doc003_one_marker(model, rel, lineno, view)) is not None
    ]
    return violations


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0080
# frob:ticket T-0085
# frob:tests tests/test_gates.py::TestSysGate.test_noop_no_design_dir
# frob:tests tests/test_gates.py::TestSysGate.test_sys001_dangling
# frob:tests tests/test_gates.py::TestSysGate.test_sys001_valid
# frob:tests tests/test_gates.py::TestSysGate.test_sys002_unbound
# frob:tests tests/test_gates.py::TestSysGate.test_sys002_bound
# frob:tests tests/test_gates.py::TestSysGate.test_sys003_import
# frob:tests tests/test_gates.py::TestSysGate.test_sys004_load_failure
# frob:tests tests/test_gates.py::TestSysGate.test_sys004_suppresses_sys001
# frob:tests tests/test_gates.py::TestSysGate.test_doc003_proved_claim_passes
# frob:tests tests/test_gates.py::TestSysGate.test_doc003_refutes_names_obligations
# frob:tests tests/test_gates.py::TestSysGate.test_doc003_unclaimed_view_ignored
# frob:tests tests/test_gates.py::TestSysGate.test_doc003_unknown_view
# sys_gate is opt-in via a `design/` (or `[strata].design_dir`) directory of
# `.strata` files existing, same posture as `decisions_gate`: a repo not yet
# using strata sees nothing. The `frob.strata` import is deferred until
# AFTER the directory check (T-0135): `frob.strata` transitively imports
# `_facts.py`, which needs the `strata_core` native extension, so a repo
# with no `design/` dir at all must never pay that import cost -- a
# standalone (`uv tool install frob`, no natives) install must not crash
# `frob check` on every repo, only degrade (T-0134) on repos that actually
# opted into `design/`.
# invariant spec: [INV-041](invariants/INV-041.md)
# frob:doc docs/modules/gates.md#self-audit-at-land-selfaudit001-t-0756
def sys_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """SYS001 (dangling directive), SYS002 (unbound boundary/secret), SYS003
    (undeclared cross-component import, tier-2 conformance), SYS004 (a
    `.strata` design file failed to parse/elaborate -- suppresses SYS001
    for the whole run since ids are merged across files with no per-file
    provenance), SELFAUDIT001 (T-0756: frob's own self-conformance/
    resource-contention/reliability audit surface, see `_selfaudit_
    violations`'s doc), and GATERULE001 (T-2448: see `gate_rule_registry_
    violations`'s doc). See the comment above for the opt-in/deferred-import
    posture.

    T-2448: GATERULE001 runs BEFORE the `design/` early-return below,
    deliberately -- it is a `frob.gates._KNOWN_GATE_RULES` registry
    completeness check, a concept entirely independent of whether this
    repo happens to use the strata design language at all. Gating it
    behind `design/` presence the same way SELFAUDIT001 is (that one
    genuinely needs design ids) would silently skip a real, standing
    check on every repo without a `design/` dir -- exactly the kind of
    hidden precondition this ticket's own body warns against."""
    root = Path(root)
    from frob.gates._rule_id_scan import gate_rule_registry_violations

    gaterule_violations = gate_rule_registry_violations(root)

    design_dir = _design_dir(root)
    if not (root / design_dir).is_dir():
        _log.debug("sys_gate: no %s/ directory, skipping", design_dir)
        return gaterule_violations

    from frob.strata import load_design_ids

    design_ids = load_design_ids(root, design_dir)
    violations = (
        *gaterule_violations,
        *_sys004(design_ids, root),
        *_sys001(snapshot, design_ids),
        *_sys002(snapshot, design_ids),
        *_sys003(design_ids, root),
        *_doc003(root, design_ids),
        *_selfaudit_violations(root, design_ids, design_dir),
        *_compliance_selfaudit_violations(root, design_ids, design_dir),
    )
    _log_sys_gate_summary(design_ids, violations)
    return violations


def _log_sys_gate_summary(design_ids, violations: tuple[Violation, ...]) -> None:  # noqa: ANN001
    """Log `sys_gate`'s per-run summary: construct counts, violation count,
    and design load error count."""
    _log.info(
        "sys_gate: %d channel(s)/%d boundary(ies)/%d secret(s) in model, "
        "%d violation(s), %d design load error(s)",
        len(design_ids.channels),
        len(design_ids.boundaries),
        len(design_ids.secrets),
        len(violations),
        len(design_ids.errors),
    )


# frob:ticket T-3324
# frob:doc docs/modules/gates.md#self-audit-at-land-selfaudit001-t-0756
# frob:tests tests/test_gates.py::TestSelfauditFindingsTouching.test_no_design_dir_returns_empty  # noqa: E501
# frob:tests tests/test_gates.py::TestSelfauditFindingsTouching.test_finding_in_touched_file_is_returned  # noqa: E501
# frob:tests tests/test_gates.py::TestSelfauditFindingsTouching.test_finding_in_untouched_file_is_filtered_out  # noqa: E501
# frob:tests tests/test_gates.py::TestSelfauditFindingsTouching.test_clean_model_returns_empty  # noqa: E501
# frob:tests tests/test_gates.py::TestSelfauditFindingsTouching.test_substring_filter_is_exact_regardless_of_native_availability  # noqa: E501
def selfaudit_findings_touching(
    root: Path, files: frozenset[str]
) -> tuple[Violation, ...]:
    """T-3324: the subset of `sys_gate`'s own SELFAUDIT001 (SYS100-107/
    SYS2xx/SYS205/REL2xx) findings whose message text names one of
    `files` -- the diff-scoped land-time enforcement T-3283/T-3324
    diagnosed as missing: a full-repo self-conformance assertion rots
    between lands because no individual land's own diff-scoped `frob
    check` re-checks it, so a land that reintroduces (or newly
    introduces) a violation in a file it itself touched should be
    refused THERE, cheaply, rather than discovered cold by the next
    periodic full-repo run. Reuses `_selfaudit_violations`, the exact
    evaluation `sys_gate` itself calls, so this can never disagree with
    what `frob check` reports for the same tree.

    `files` matching is a plain substring test against each `Violation.
    message` -- `Violation.file` is always the design directory itself
    for every SELFAUDIT001 finding (`_selfaudit_violation`'s own `file=
    design_dir`), never the real offending source file, which instead
    only appears inside the underlying check's own free-text detail
    (e.g. SYS100's `"capability 'fs.read' observed at <path>:<line> but
    not declared"`) -- the same lightweight-text-over-a-second-schema
    convention this repo already accepts elsewhere (`frob.arch._mayraise`'s
    guard-predicate discharges) rather than parsing a structured location
    out of every sub-rule's differently-shaped detail text.

    Fails OPEN (empty tuple) exactly like `sys_gate` itself when `root`
    has no `design/` (or `[strata].design_dir`) directory -- a repo not
    using strata sees nothing, matching every other SELFAUDIT001 caller's
    opt-in posture."""
    root = Path(root)
    design_dir = _design_dir(root)
    if not (root / design_dir).is_dir():
        return ()

    from frob.strata import load_design_ids

    design_ids = load_design_ids(root, design_dir)
    violations = _selfaudit_violations(root, design_ids, design_dir)
    return tuple(v for v in violations if any(f in v.message for f in files))


# frob:ticket T-3575
# frob:doc docs/modules/gates.md#self-audit-at-land-selfaudit001-t-0756
# frob:tests tests/test_gates.py::TestSys111FindingsTouching.test_no_design_dir_returns_empty  # noqa: E501
# frob:tests tests/test_gates.py::TestSys111FindingsTouching.test_ratchet_trip_in_declaring_file_is_returned  # noqa: E501
# frob:tests tests/test_gates.py::TestSys111FindingsTouching.test_ratchet_trip_in_untouched_file_is_filtered_out  # noqa: E501
def sys111_findings_touching(
    root: Path, files: frozenset[str]
) -> tuple[Violation, ...]:
    """T-3575: the subset of `capability_ratchet_violations`'s (SYS111,
    T-1628) findings attributable to `files` -- `selfaudit_findings_
    touching`'s substring-over-`Violation.message` filter can NEVER match
    a SYS111 finding (T-3574's own root-cause): each finding's message is
    an AGGREGATE count keyed by `node::atom` ('exec via-list on testsuite
    grew to 235 site(s)...') with no source file path anywhere in the
    text, because `capability_via_site_counts` counts the LENGTH of each
    `MayGrant.via` tuple -- a count of declared globs/symbols in the
    node's OWN `.strata` declaration, not a scan of real source sites.
    Ratchet growth therefore always originates in an edit to the `.strata`
    file that DECLARES (or, T-2502, `extend`s) the tripped node, so this
    resolves each violation's `node` id back to its declaring file(s) by
    re-parsing every `.strata` file under the design dir (the SAME per-
    file walk `_strata_files` already performs, since `load_design_ids`'s
    OWN `DesignIds.models` only keeps the cross-file-ELABORATED merge,
    which has no node-to-file provenance left to read -- `frob.strata.
    _models.Node` carries no `source_file` field) and filtering on that
    file, not the message text.

    Fails OPEN (empty tuple) under the exact same conditions
    `selfaudit_findings_touching` does: no design dir, a design-load
    error, or (here also) no ratchet violations at all -- each checked
    before the per-file re-parse to keep the common (clean) case cheap."""
    root = Path(root)
    design_dir = _design_dir(root)
    if not (root / design_dir).is_dir():
        return ()

    from frob.strata import (
        capability_ratchet_violations,
        load_design_ids,
        merge_models,
        parse_module,
    )
    from frob.strata._design_load import _strata_files

    design_ids = load_design_ids(root, design_dir)
    if design_ids.errors or not design_ids.models:
        return ()

    model = merge_models(design_ids.models)
    ratchet = capability_ratchet_violations(model, root)
    if not ratchet:
        return ()

    from frob.gates._sys_selfaudit import _selfaudit_violation

    node_files = _node_declaring_files(root, design_dir, parse_module, _strata_files)
    found = []
    for v in ratchet:
        declaring_files = node_files.get(v.node, set())
        if declaring_files & files:
            found.append(
                _selfaudit_violation("SYS111", v.node, v.detail, design_dir, root)
            )
    return tuple(found)


def _node_declaring_files(
    root: Path, design_dir: str, parse_module, strata_files
) -> dict[str, set[str]]:
    """`sys111_findings_touching`'s own per-file re-parse, split out to
    keep that function under ARCH001's threshold (T-3575): `{node_id:
    {every .strata file whose top-level `node ID { ... }` or `extend node
    ID { ... }` declares it}}`, built fresh (never cached -- this runs
    once per land, not a hot path) since `load_design_ids`'s own merged
    model has no node-to-file provenance left to read (see caller's
    docstring). `parse_module`/`strata_files` are passed in rather than
    imported here purely so this stays a plain helper the caller's own
    deferred imports already resolved, not a second import site."""
    from frob.excludes import load_exclude_globs

    exclude_globs = load_exclude_globs(root)
    node_files: dict[str, set[str]] = {}
    for path in strata_files(root, root / design_dir, exclude_globs):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        parsed = parse_module(text)
        if parsed.is_err:
            continue
        raw_module = parsed.danger_ok
        for node in raw_module.nodes:
            node_files.setdefault(node.id, set()).add(rel)
        for extend in raw_module.extends:
            node_files.setdefault(extend.id, set()).add(rel)
    return node_files


# frob:ticket T-3575
# frob:doc docs/modules/gates.md#self-audit-at-land-selfaudit001-t-0756
# frob:tests tests/test_gates.py::TestDocptrFindingsTouching.test_finding_in_touched_doc_is_returned  # noqa: E501
# frob:tests tests/test_gates.py::TestDocptrFindingsTouching.test_finding_naming_a_touched_target_is_returned  # noqa: E501
# frob:tests tests/test_gates.py::TestDocptrFindingsTouching.test_finding_in_untouched_files_is_filtered_out  # noqa: E501
def docptr_findings_touching(
    root: Path, files: frozenset[str]
) -> tuple[Violation, ...]:
    """T-3575: the subset of `frob.gates._docblocks.doc004_gate`/
    `frob.gates._docptr.doc006_gate` (DOC004/DOC006, dangling/unresolved
    doc-pointer) findings attributable to `files` -- T-3324's original
    land-time check (`selfaudit_findings_touching`) never evaluated this
    gate family at all (T-3574's own root-cause): it lives in a wholly
    separate module (`frob.gates._docblocks`/`_docptr`, not `frob.gates.
    _sys`/`_sys_selfaudit`), so a doc-pointer break a land itself
    introduces (or a land that deletes/renames a file some OTHER doc's
    pointer still names) went undetected here even though `frob check`
    itself already reports it -- exactly the gap the T-1691-shaped
    incident T-3324 closed for SELFAUDIT001 left open for this family.

    Builds a fresh `GraphSnapshot` over `root` (a throwaway cache db, not
    the repo's own -- this runs against the staged post-squash tree, a
    different tree than whatever the caller's own cache was last built
    against) and applies waivers the same way `frob check` itself does,
    so a legitimately waived DOC004/DOC006 finding here agrees with what
    `frob check` would report. A finding matches `files` if EITHER its
    own `Violation.file` (the doc carrying the pointer) is in `files`, or
    `files` contains the specific path/anchor text the finding's message
    names (the target the pointer names, e.g. a file this land deleted or
    renamed) -- catching both "this land broke its own doc" and "this
    land broke someone else's doc's pointer at it".

    Fails OPEN (empty tuple) on any `OSError` building the graph
    (`build_graph` acquires `frob.process._lock.derived_state_write_
    lock`, a HOME-keyed lock this land-time context has no guarantee is
    writable in -- e.g. a sandboxed/isolated test HOME) rather than
    letting an infra fault crash the whole land: this check is a diff-
    scoped ADDITION to land-time enforcement, and a land must not start
    failing on a check that cannot even run, on top of whatever it was
    already refusing before this ticket."""
    kept = _docptr_kept_violations(Path(root))
    return tuple(
        v
        for v in kept
        if v.rule in ("DOC004", "DOC006")
        and (v.file in files or any(f in v.message for f in files))
    )


def _docptr_kept_violations(root: Path) -> tuple[Violation, ...]:
    """`docptr_findings_touching`'s own graph-build/gate-run step, split
    out to keep that function under ARCH001's threshold (T-3575): builds
    a throwaway `GraphSnapshot` over `root`, runs `doc004_gate`/
    `doc006_gate`, and applies waivers -- see the caller's own docstring
    for why a throwaway snapshot and why this fails OPEN on `OSError`."""
    import tempfile

    from frob.gates import _apply_waivers, doc004_gate
    from frob.gates._docptr import doc006_gate
    from frob.graph import build_graph

    try:
        with tempfile.TemporaryDirectory() as tmp:
            built = build_graph(root, Path(tmp) / "cache.db")
            if built.is_err:
                return ()
            snapshot = built.danger_ok
            raw = tuple(doc004_gate(root, snapshot)) + tuple(
                doc006_gate(root, snapshot)
            )
            kept, _waived = _apply_waivers(raw, snapshot)
            return kept
    except OSError:
        _log.warning(
            "docptr_findings_touching: could not build a graph snapshot for "
            "%s, skipping this land-time check (T-3575: fails open on infra "
            "faults)",
            root,
        )
        return ()
