"""PROTO001-005: live verification over the T-0744/T-0745 protocol/typestate
machinery (docs/modules/gates.md#proto001-t-0813,
docs/modules/gates.md#proto002proto003-t-0746,
docs/modules/gates.md#proto005-t-0747).

T-0813, the production wiring the T-0809 reviewer's condition (a) asked
for: `frob.graph.summary.compute_protocol_summaries`'s `UNRESOLVED_CALLEE`
poisoning channel (T-0745, NO-FAIL-SILENT mandate) had no real repo-scan
consumer -- `mark_unresolved=True` was opt-in and production-dead, tested
only against hand-fabricated fixtures. T-0814 hardened every closure
consumer of `frob.graph.callgraph.build_call_graph`'s output against the
non-symref `UNRESOLVED_CALLEE` sentinel; PROTO001 is the first real
caller that turns `mark_unresolved=True` on and lets the poisoning
propagate all the way to a `frob check` finding.

T-0746 adds the two ERROR-tier verification rules the T-0739 umbrella's
child 3 asks for, sharing PROTO001's per-package `build_call_graph`/
`compute_protocol_summaries` scan (one pass, three findings, never three
separate repo walks):

  - PROTO002 (state-requirement violation): a `frob:requires proto="P"
    state="S"` symbol whose protocol summary is poisoned (untrustworthy --
    ERROR, matching the ticket's "Unknown/poisoned summaries at a checked
    call site = ERROR" mandate, stricter than PROTO001's WARN disposition
    for the SAME poisoning signal), or whose required state `S` is never
    ESTABLISHED anywhere in the reachable closure from the tagged
    entrypoints of its package (neither `S == protocol's declared initial
    state` nor any `frob:transition ... to="S"` reachable) -- the
    `*_init-never-called` case the ticket names falls out of this
    directly: an inferred `_init`/`_deinit` pair (T-0744) whose init half
    is never reachable IS exactly "no transition into the active state is
    reachable".
  - PROTO003 (invalid transition): a `frob:transition proto="P" from="S"
    to="T"` symbol whose precondition state `S` is never established by
    the same "initial or reachable transition" test PROTO002 uses -- a
    transition function reached in a state the protocol never
    establishes.

APPROXIMATION, DISCLOSED (not a soundness bug to silently paper over):
`compute_protocol_summaries` (T-0745) summarizes a function's transitive
`requires`/`transitions` as an UNORDERED per-function union, with no
per-call-site statement ordering yet (real path-sensitivity needs an
ordered call graph -- deferred, same posture T-0745 disclosed for its own
`UNRESOLVED_CALLEE` wiring, T-0809). PROTO002/PROTO003 therefore ask an
EXISTENTIAL question -- "is state S established by SOME reachable
transition anywhere in the package's tagged closure" -- rather than a
path-sensitive "is S established on EVERY path reaching this exact call
site". This is deliberately the FALSE-NEGATIVE-biased direction (a real
ordering violation can be missed if some other path in the same closure
happens to establish the state) rather than false-positive (a state
genuinely never reachable by any transition anywhere is unambiguously
wrong on every path, so that direction is sound) -- the crisp, ticket-
named case ("reachable without net_init" -- init never called AT ALL) is
caught exactly; a real cross-path ordering bug that happens to share a
closure with a correct call site is the known gap, filed as T-0840 for a
path-sensitive follow-up once an ordered call graph exists.

LANGUAGE-EXCUSE DISCHARGE (T-0746, wired repo-wide by T-0841): before
either rule reports an ERROR, `frob.arch._protocol_excuse`'s per-language
predicates get a chance to DISCHARGE it -- a runtime guarantee (Python's
`with`, Rust's `Drop`, C++'s RAII destructor, TypeScript's `using`/
`try`-`finally`) the DSL itself cannot see but that provably
re-establishes or maintains the missing state. A discharge is recorded as
a WARN-severity finding (never silently dropped -- NO-FAIL-SILENT),
naming its mechanism, so it stays visible and auditable rather than
vanishing.

T-0841: `build_call_graph`'s callee-privacy resolution now reads
`frob.lang.RawSymbol.public` (each grammar walker's own language-correct
publicness rule -- see `frob.graph.callgraph._short_name_index`) instead
of Python's leading-underscore naming convention, so a real cross-file
call-graph scan already works for every `frob.lang`-supported language,
not just Python -- this gate's own `.py`-only filters are lifted
accordingly (`_package_edges`, `protocol_summary_gate`'s tagged-package
grouping) and `_discharge` now dispatches to
`rust_drop_discharge`/`cpp_raii_discharge`/`typescript_using_discharge`
by the tagged symbol's own file extension, not just
`python_with_discharge`. `gc_finalizer_discharge` has no dispatch entry
here: this repo's `frob.lang` has no GC-language grammar today (Java/
Kotlin/JS-without-TS are not `_SUPPORTED_LANGUAGES`), so there is no file
extension that would ever route to it -- it stays built and unit-tested
for the day a GC-language grammar is added, per its own module's
doctrine. `mark_unresolved`'s own naming heuristic remains Python-
specific (`build_call_graph`'s own T-0841 disclosure) -- a call in a
non-Python file can still fail to be flagged UNRESOLVED_CALLEE even when
genuinely dangling, the same false-negative-biased gap PROTO001 already
carries.

Scope, deliberately narrow (all three rules): only a symbol that ITSELF
carries a `frob:requires`/`frob:transition` directive (i.e. explicitly
opted into the T-0744 protocol DSL) is ever reported here -- not every
private helper with an unresolved call, which would just be `DEAD001`/
general call-graph noise with no protocol stake in it.
`compute_protocol_summaries` still analyzes every function transitively
reachable from those tagged entrypoints (poisoning propagates through
plain helpers too, T-0745's NO-FAIL-SILENT contract) -- this gate only
DECIDES WHICH summaries are worth reporting on, it does not narrow what
the engine itself computes.

PROTO001 stays WARN-only (advisory-but-tracked, matching DEAD001/REF/PERF/
FUZZ's posture) -- `build_call_graph`'s callee resolution is best-effort,
name-based, no scope/overload disambiguation (same caveat every other
consumer of this substrate carries), so a false positive here is
possible; waivable with `frob:waive PROTO001 reason="..."` like every
other advisory rule. PROTO002/PROTO003 default to ERROR (T-0746's own
"enforceable, never fail-silent" user mandate) -- this repo's own source
carries zero real (non-fixture, non-test) `frob:protocol` usage today, so
ERROR-by-default measures clean against main at landing time (disclosed
in the T-0746 Done report); both remain waivable with
`frob:waive PROTO002 reason="..."`/`frob:waive PROTO003 reason="..."` for
a case the engine's coarse approximation gets wrong.

PROTO004, PER-CALL-SITE ORDERING (T-0840): PROTO002/PROTO003 ask an
EXISTENTIAL question over `compute_protocol_summaries`' unordered
transitive closure -- "is state S established by SOME reachable
transition anywhere in the package's tagged closure" -- which can miss a
real ordering bug when some OTHER path in the same closure happens to
establish the state (this module's own APPROXIMATION paragraph above).
PROTO004 narrows that gap using `frob.graph.callgraph.
build_ordered_call_graph`'s source-text-ordered call sequences: for every
caller in the scanned package (not just protocol-tagged entrypoints --
any function that calls into one), it walks that caller's OWN calls in
order, tracking which protocol states are established SO FAR by earlier
calls in THAT SAME caller, and reports a call to a `frob:requires`-tagged
callee whose precondition state is not yet established on that exact
call sequence. This is SEQUENCE-sensitive within one caller's body, not
fully branch-aware (`OrderedCallGraph`'s own docstring): a call inside an
untaken `if`/`else` branch is treated as if it always executes, so a
call genuinely guarded by the right branch can still false-positive here
-- `frob:waive PROTO004 reason="..."` is expected for that case, same as
PROTO002/PROTO003's own engine-approximation waiver posture. PROTO004
gets the same language-excuse discharge chance as PROTO002/PROTO003
before reporting. Filed as T-0840's own follow-up target: real
branch-aware path-sensitivity (distinguishing which calls are mutually
exclusive) is future work, not attempted here -- this is "ordered" not
yet "control-flow-aware".
"""
# frob:waive INV006 reason="T-1023 INV006 burn-down: this file's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim, same \
# INV006 first-turn-on-pool disposition this repo already applies elsewhere (T-0585)"

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path, PurePosixPath

from frob.arch import _kotlin, _python, _rust, _typescript
from frob.arch._mayraise import compute_may_raise
from frob.arch._normalized import LanguageAdapter, NormalizedFunction, NormalizedModule
from frob.arch._protocol_excuse import (
    DischargeResult,
    cpp_raii_discharge,
    python_with_discharge,
    rust_drop_discharge,
    typescript_using_discharge,
)
from frob.gates._models import Severity, Violation
from frob.graph import (
    Edge,
    EdgeKind,
    FunctionSummary,
    GraphSnapshot,
    SummaryResult,
    compute_protocol_summaries,
)
from frob.graph.callgraph import build_call_graph, build_ordered_call_graph
from frob.graph.dsl import parse_directives
from frob.lang import raw_tree
from frob.logging import get_logger

_log = get_logger(__name__)

# Directive kinds that mark a symbol as an explicit T-0744 protocol
# participant -- the only symbols this gate ever reports a poisoned
# summary for (see module docstring's scope note). T-0747: EdgeKind.ACQUIRE
# is included too so a package whose ONLY tag is a bare `frob:acquire`
# (no frob:requires/frob:transition at all) still gets scanned -- PROTO005
# (cleanup obligations, below) needs no `compute_protocol_summaries` run of
# its own, but reuses this same package-selection loop rather than walking
# the repo a second time. An acquire-only entrypoint contributes an empty
# requires/transitions summary (harmless) and can still legitimately WARN
# PROTO001 if its own call closure is poisoned -- not a new false-positive
# class, just PROTO001's existing signal reaching a wider symbol set.
_PROTOCOL_TAG_KINDS = frozenset(
    {EdgeKind.REQUIRES, EdgeKind.TRANSITION, EdgeKind.ACQUIRE}
)

#: T-0747: per-language `NormalizedModule` adapter dispatch for the
#: cleanup-obligation gate's intraprocedural exit walk (`_acquiring_
#: function_violations`) -- same four `frob.arch` adapters `analyze_
#: project` already drives, keyed by file suffix like `_DISCHARGE_BY_
#: SUFFIX` below. `.py` is additionally the ONLY suffix the exceptional-
#: exit half consults `frob.arch._mayraise.compute_may_raise` for (that
#: resolver's own module docstring discloses it as Python-specific: its
#: builtin-raiser table and exception hierarchy are Python's, not a
#: generic cross-language shape) -- Rust/TypeScript/Kotlin acquisitions
#: still get the language-agnostic normal-return postdominance check,
#: just not the exceptional-exit half.
#:
#: Built LAZILY (`_normalized_adapter_by_suffix`, below), not as a module-
#: level literal: `frob.gates` (this module's own package) is imported
#: transitively from deep inside `frob.arch.__init__`'s own import chain
#: (`frob.arch -> _async_hazards -> _python -> frob.dup -> frob.gates`),
#: so a module-level `_python.PythonAdapter()` instantiation at THIS
#: module's import time reads `frob.arch._python` before its own class
#: body has finished executing -- a real circular-import `AttributeError`
#: this ticket's own first pass shipped and `tests/unit/test_arch.py`
#: (which imports `frob.arch` directly, triggering that exact order)
#: caught. Constructing the adapters inside a function instead defers
#: that attribute lookup until first CALL, by which point every module in
#: the cycle has finished importing.
_ADAPTER_FACTORY_BY_SUFFIX: dict[str, Callable[[], LanguageAdapter]] = {
    ".py": lambda: _python.PythonAdapter(),
    ".rs": lambda: _rust.RustAdapter(),
    ".ts": lambda: _typescript.TypeScriptAdapter(),
    ".tsx": lambda: _typescript.TypeScriptAdapter(),
    ".kt": lambda: _kotlin.KotlinAdapter(),
}


# frob:ticket T-0747
def _normalized_adapter_for(suffix: str) -> LanguageAdapter | None:
    """The `LanguageAdapter` instance for file extension `suffix` (T-0747),
    constructed on first use via `_ADAPTER_FACTORY_BY_SUFFIX` rather than
    at this module's import time -- see that dict's own comment for the
    circular-import hazard this defers past. `None` for an unregistered
    extension."""
    factory = _ADAPTER_FACTORY_BY_SUFFIX.get(suffix)
    return None if factory is None else factory()


#: Bare callee names (T-0747) treated as PROCESS-TERMINATING calls -- an
#: exit through one of these is only discharged silently when the
#: acquisition's own `cleanup="process-exit-ok"` policy says so (module
#: docstring's per-protocol-policy clause); under the "always"/"on-error"
#: defaults a terminator call is just another exit needing its own
#: release coverage, same as a plain `return`.
_PROCESS_TERMINATORS = frozenset({"exit", "_exit", "quit"})


# frob:ticket T-0813
def _package_files(root: Path, rel_path: str) -> tuple[str, ...]:
    """Every language-supported file beside `rel_path` (same directory),
    repo-root-relative POSIX -- the bounded file set `build_call_graph`
    resolves intra-package private calls over, one package at a time.
    Deliberately duplicated from `frob.gates._dead_symbols`'s identical
    helper rather than imported cross-module: both are private
    (leading-underscore) symbols of a sibling gate module with no shared
    public home yet, and this gate additionally needs `.py`-only files
    filtered out of any non-Python candidate BEFORE `build_call_graph`
    ever sees them (see `_protocol_tagged_symrefs_by_package`'s own
    Python-only note) -- a genuinely different filter than
    `_dead_symbols`'s all-language variant, not a copy-paste of the exact
    same contract."""
    from frob.lang import supported_extensions

    directory = (root / rel_path).parent
    if not directory.is_dir():
        return (rel_path,)
    exts = supported_extensions()
    found = tuple(
        sorted(
            (directory / name).relative_to(root).as_posix()
            for name in (p.name for p in directory.iterdir())
            if (directory / name).is_file()
            and (directory / name).suffix.lower() in exts
        )
    )
    return found or (rel_path,)


def _package_edges(root: Path, files: tuple[str, ...]) -> tuple[Edge, ...]:
    """Every `frob:` directive `Edge` parsed from `files` (skipping any
    that fails to parse, logged) -- the `compute_protocol_summaries`
    `edges` argument, built fresh per package since `frob.graph.dsl` has
    no repo-wide cache of its own.

    T-0746: `parse_file` must be handed an absolute, filesystem-resolvable
    path (`root / rel_path`) to actually read the file, but that makes
    `ParsedFile.path` -- and every `Edge.src`/`origin` `parse_directives`
    derives from it -- absolute too, while `snapshot.edges` (the full
    repo-graph build `protocol_summary_gate`'s `entrypoints` come from)
    always uses repo-root-relative symrefs. PROTO001's own poisoning
    check never needed the two to compare equal (poisoning is purely a
    `CallGraph` structural fact), but PROTO002/PROTO003's requires/
    transition lookups key DIRECTLY off `edge.src == symref` against
    those relative entrypoints -- so every edge's `src`/`origin` gets
    rewritten back to `rel_path`-relative here before being handed back,
    the same convention `frob.graph.callgraph._parse_package` already
    uses for its OWN (relative) dict keys.

    T-0841: no longer `.py`-only -- every `frob.lang.supported_extensions()`
    file `parse_file` can actually turn into directives is scanned, now
    that `build_call_graph`'s callee resolution is language-correct (not
    Python-naming-specific, see `frob.graph.callgraph._short_name_index`)."""
    from frob.lang import parse_file, supported_extensions

    exts = supported_extensions()
    edges: list[Edge] = []
    for rel_path in files:
        if PurePosixPath(rel_path).suffix.lower() not in exts:
            continue
        result = parse_file(root / rel_path)
        if result.is_err:
            _log.warning(
                "protocol_summary_gate: skipping unparsed %s: %s",
                rel_path,
                result.danger_err,
            )
            continue
        file_edges, _malformed = parse_directives(result.danger_ok)
        abs_path = str(root / rel_path)
        for e in file_edges:
            edges.append(
                e.model_copy(
                    update={
                        "src": e.src.replace(abs_path, rel_path, 1),
                        "origin": e.origin.replace(abs_path, rel_path, 1),
                    }
                )
            )
    return tuple(edges)


# frob:ticket T-0746
def _protocol_initial_states(edges: tuple[Edge, ...]) -> dict[str, str]:
    """proto name -> its `frob:protocol`-declared `initial=` state, from
    every `EdgeKind.PROTOCOL` edge in `edges` (`e.target` IS the protocol
    name -- `protocol` is a bare-target verb, like `doc`/`ticket`, unlike
    `requires`/`transition` which bind via their `proto=` attribute)."""
    initials: dict[str, str] = {}
    for e in edges:
        if e.kind is EdgeKind.PROTOCOL and e.attrs.get("initial"):
            initials[e.target] = e.attrs["initial"]
    return initials


# frob:ticket T-0746
def _parse_transition_token(token: str) -> tuple[str, str, str]:
    """Split one `FunctionSummary.transitions` entry (`"proto:from->to"`,
    `frob.graph.summary._own_contribution`'s encoding) back into its
    `(proto, from, to)` parts."""
    proto, _, rest = token.partition(":")
    frm, _, to = rest.partition("->")
    return proto, frm, to


# frob:ticket T-0746
def _established_states(
    edges: tuple[Edge, ...], result: SummaryResult
) -> dict[str, set[str]]:
    """proto -> every state EXISTENTIALLY reachable somewhere in `result`'s
    whole tagged-entrypoint closure: each protocol's declared initial
    state, plus every `to` state any `frob:transition` reachable from ANY
    tagged entrypoint performs. Deliberately existential-over-paths (see
    this module's docstring's APPROXIMATION note) -- a state only needs
    ONE witnessing transition anywhere in the closure to count as
    establishable, never a false-positive-biased per-call-site claim the
    T-0745 engine has no ordering data to actually support yet."""
    established: dict[str, set[str]] = {}
    for proto, initial in _protocol_initial_states(edges).items():
        established.setdefault(proto, set()).add(initial)
    for summary in result.summaries.values():
        for token in summary.transitions:
            proto, _frm, to = _parse_transition_token(token)
            if to:
                established.setdefault(proto, set()).add(to)
    return established


# frob:ticket T-0746
def _own_requires(edges: tuple[Edge, ...], symref: str) -> tuple[tuple[str, str], ...]:
    """Every `(proto, state)` this exact `symref` declares via its OWN
    `frob:requires proto="..." state="..."` directive(s) -- NOT the
    transitive `FunctionSummary.requires` union, since PROTO002's message
    needs to name the declaration actually responsible for the violation."""
    out: list[tuple[str, str]] = []
    for e in edges:
        if e.kind is EdgeKind.REQUIRES and e.src == symref:
            proto = e.attrs.get("proto", e.target)
            state = e.attrs.get("state", "")
            if state:
                out.append((proto, state))
    return tuple(out)


# frob:ticket T-0746
def _own_transitions(
    edges: tuple[Edge, ...], symref: str
) -> tuple[tuple[str, str, str], ...]:
    """Every `(proto, from, to)` this exact `symref` declares via its OWN
    `frob:transition proto="..." from="..." to="..."` directive(s) --
    same "own declaration, not transitive union" reasoning as
    `_own_requires`."""
    out: list[tuple[str, str, str]] = []
    for e in edges:
        if e.kind is EdgeKind.TRANSITION and e.src == symref:
            proto = e.attrs.get("proto", e.target)
            frm = e.attrs.get("from", "")
            to = e.attrs.get("to", "")
            if frm:
                out.append((proto, frm, to))
    return tuple(out)


# T-0841: extension -> discharge predicate, the real per-language dispatch.
# `.h`/`.c` (pure C, no grammar-visible RAII/Drop idiom in this repo's
# doctrine) and `.strata` (no discharge doctrine written for it) have no
# entry -- `_language_discharge` falls through to a non-discharging
# `DischargeResult` for those, same as any extension outside
# `frob.lang.supported_extensions()` entirely.
_DISCHARGE_BY_SUFFIX = {
    ".py": python_with_discharge,
    ".rs": rust_drop_discharge,
    ".cpp": cpp_raii_discharge,
    ".hpp": cpp_raii_discharge,
    ".cc": cpp_raii_discharge,
    ".hh": cpp_raii_discharge,
    ".cxx": cpp_raii_discharge,
    ".ts": typescript_using_discharge,
    ".tsx": typescript_using_discharge,
}


# frob:ticket T-0841
def _language_discharge(path: str, source: str, resource: str) -> DischargeResult:
    """T-0841's per-language dispatch: routes to the T-0746 discharge
    predicate matching `path`'s extension (`_DISCHARGE_BY_SUFFIX`) --
    Python's `with`, Rust's `Drop`, C++'s RAII destructor, TypeScript's
    `using`/`try`-`finally`. An extension with no registered predicate
    (pure C, `.strata`, anything `frob.lang` does not parse at all) always
    reports `discharged=False` naming the gap, matching every predicate's
    own NO-FAIL-SILENT contract (`DischargeResult.reason` always explains
    a `False`, never bare)."""
    ext = PurePosixPath(path).suffix.lower()
    predicate = _DISCHARGE_BY_SUFFIX.get(ext)
    if predicate is None:
        return DischargeResult(
            discharged=False,
            mechanism="none",
            reason=f"no T-0746 discharge predicate registered for {ext!r} files",
        )
    return predicate(source, resource)


# frob:ticket T-0840
def _ordered_call_site_violations(
    root: Path,
    edges: tuple[Edge, ...],
    ordered_calls: Mapping[str, tuple[str, ...]],
    summaries: Mapping[str, FunctionSummary],
    protocol_initials: dict[str, str],
) -> list[Violation]:
    """T-0840's per-call-site ordering check (PROTO004, module docstring):
    for each caller in `ordered_calls`, walks its OWN call sequence in
    source-text order, tracking which protocol states are established SO
    FAR (seeded from `protocol_initials`, grown by each earlier callee's
    OWN transitive `FunctionSummary.transitions`) -- reports a call to a
    `frob:requires`-tagged callee whose precondition is not yet
    established on THAT SEQUENCE. Once a callee's own summary is poisoned,
    no further state is added and no LATER call site in that same caller
    is checked either (module docstring's SEQUENCE-sensitive-not-branch-
    aware disclosure; unknowable what a poisoned callee actually
    established). A discharge (module docstring, `_discharge`) is checked
    against the CALLER's own file before an ERROR is reported, same as
    PROTO002/PROTO003."""
    violations: list[Violation] = []
    for caller, callees in ordered_calls.items():
        established: dict[str, set[str]] = {
            proto: {initial} for proto, initial in protocol_initials.items()
        }
        caller_path = caller.split("::", 1)[0]
        for callee in callees:
            summary = summaries.get(callee)
            for proto, state in _own_requires(edges, callee):
                if state in established.get(proto, set()):
                    continue
                discharge = _discharge(root, caller, proto)
                if discharge is not None:
                    violations.append(discharge.model_copy(update={"rule": "PROTO004"}))
                    continue
                violations.append(
                    Violation(
                        rule="PROTO004",
                        severity=Severity.ERROR,
                        file=caller_path,
                        line=0,
                        message=(
                            f"PROTO004: {caller} calls {callee}, which requires "
                            f"{proto}:{state}, but nothing earlier in {caller}'s "
                            "own call sequence establishes it -- ordering "
                            "violation on this path; "
                            'frob:waive PROTO004 reason="..." if a branch this '
                            "sequential scan cannot distinguish makes this call "
                            "unreachable without the state"
                        ),
                    )
                )
            if summary is None or summary.poisoned:
                break
            for token in summary.transitions:
                proto, _frm, to = _parse_transition_token(token)
                if to:
                    established.setdefault(proto, set()).add(to)
    return violations


# frob:ticket T-0747
def _bare_name(text: str) -> str:
    """The trailing identifier of a possibly-dotted call/symref text
    (T-0747) -- `"self.close"`/`"conn.close"`/`"close"` all resolve to
    `"close"`; `"path::Class.method"` resolves to `"method"`. Same
    convention `frob.arch._mayraise._bare_callee_name` already uses,
    deliberately duplicated rather than imported cross-module (this
    module's own `_package_files`/`_qualname`-style precedent: two small
    private siblings, no shared public home yet)."""
    return text.rsplit(".", 1)[-1].rsplit("::", 1)[-1]


# frob:ticket T-0747
def _cleanup_policy(edges: tuple[Edge, ...], symref: str, path: str) -> str:
    """The `cleanup=` policy governing `symref`'s acquisition (T-0747):
    the `frob:protocol cleanup="..."` attribute of whichever `PROTOCOL`
    edge binds to `symref` itself, or (T-0744's own "or, for a name-
    pattern-inferred protocol, at the enclosing file" convention) to
    `path` as a whole, falling back to the DSL's own `"on-error"` default
    when no `frob:protocol` declaration governs this acquisition at all."""
    for e in edges:
        if e.kind is EdgeKind.PROTOCOL and e.src == symref:
            return e.attrs.get("cleanup", "on-error")
    for e in edges:
        if e.kind is EdgeKind.PROTOCOL and e.src == path:
            return e.attrs.get("cleanup", "on-error")
    return "on-error"


# frob:ticket T-0747
def _normalized_module_for(root: Path, path: str) -> NormalizedModule | None:
    """`path`'s whole-file `NormalizedModule` (T-0747) via whichever
    `_ADAPTER_FACTORY_BY_SUFFIX` entry matches its extension -- `None`
    when the file cannot be parsed (`raw_tree` error) or the extension has
    no registered adapter (same disclosed language-coverage gap every
    other `frob.arch` normalized-model check already carries)."""
    adapter = _normalized_adapter_for(PurePosixPath(path).suffix.lower())
    if adapter is None:
        return None
    result = raw_tree(root / path)
    if result.is_err:
        _log.warning(
            "protocol_summary_gate: PROTO005 skipping unparsed %s: %s",
            path,
            result.danger_err,
        )
        return None
    tree, _source, _language = result.danger_ok
    return adapter.adapt(tree, b"", path)


# frob:ticket T-0747
def _find_function(
    module: NormalizedModule, qualname: str
) -> NormalizedFunction | None:
    """The `NormalizedFunction` in `module` matching `qualname` (`"func"`
    or `"Class.method"`, T-0747) -- a bare top-level function name looks
    only at `module.functions`; a dotted `Class.method` name looks only at
    that class's own `methods`. `None` when no exact match exists (a
    nested function/method this shallow lookup does not walk into, or a
    symref this module's own snapshot build produced that no longer
    matches its current source -- the caller treats this the same as "no
    body to analyze", never a crash)."""
    if "." not in qualname:
        for f in module.functions:
            if f.name == qualname:
                return f
        return None
    cls_name, _dot, method_name = qualname.rpartition(".")
    for c in module.classes:
        if c.name == cls_name:
            for m in c.methods:
                if m.name == method_name:
                    return m
    return None


# frob:ticket T-0747
def _acquiring_function_violations(
    root: Path,
    edges: tuple[Edge, ...],
    symref: str,
    resource: str,
    release_bare_names: frozenset[str],
) -> list[Violation]:
    """T-0747's intraprocedural cleanup-obligation check for one
    `symref` that directly `frob:acquire`s `resource` (its caller has
    already discharged the escape-transfer and self-contained-release
    cases): release-postdominance-on-all-exits, using T-0686's
    `compute_may_raise` for the exceptional edge, per-protocol `cleanup=`
    policy for a process-terminating exit (module docstring).

    NORMAL EXITS: every `return` in `symref`'s own body (or, with none, one
    implicit fallthrough exit at the body's last line) must have a call to
    a `release_bare_names` member at or before its own line -- a `return`
    reached with no such call yet on ANY earlier line in this SAME
    function is the crisp "early-error return skips cleanup" case (module
    docstring's acceptance example), reported by name at that exact line.
    A `cleanup="process-exit-ok"` policy additionally discharges a `return`
    silently (no finding at all) once a process-terminating call
    (`_PROCESS_TERMINATORS`) precedes it -- ANY other policy still requires
    that exit's own release coverage exactly like a plain `return`.

    EXCEPTIONAL EXIT: existential, false-negative-biased on purpose
    (matching PROTO002/003/004's own disclosed approximation posture, not
    a new one) -- rather than pinpoint which exact raise/propagating call
    a release call may or may not precede, this only fires when
    `symref`'s OWN may-raise set (T-0686, already function-wide catch-
    subtracted) is non-empty AND `release_bare_names` never appears
    anywhere in this body at all (zero release calls full stop): a
    function that releases on ANY exit at least demonstrates it knows to,
    and a real path-sensitive exceptional-exit gap is deferred exactly
    like PROTO002/003's own `T-0840`-class follow-up, not attempted here.
    Python-only (`compute_may_raise`'s own disclosed scope)."""
    path = symref.split("::", 1)[0]
    module = _normalized_module_for(root, path)
    if module is None:
        return []
    qualname = symref.split("::", 1)[1]
    func = _find_function(module, qualname)
    if func is None:
        return []

    discharge = _discharge(root, symref, resource)
    if discharge is not None:
        return [discharge.model_copy(update={"rule": "PROTO005"})]

    release_lines = sorted(
        c.line for c in func.calls if _bare_name(c.callee) in release_bare_names
    )
    terminator_lines = sorted(
        c.line for c in func.calls if _bare_name(c.callee) in _PROCESS_TERMINATORS
    )
    policy = _cleanup_policy(edges, symref, path)

    violations = _normal_exit_release_violations(
        func, symref, resource, path, release_lines, terminator_lines, policy
    )
    if not release_lines and PurePosixPath(path).suffix.lower() == ".py":
        exceptional = _exceptional_exit_release_violation(
            module, func, symref, resource, path, policy
        )
        if exceptional is not None:
            violations.append(exceptional)
    return violations


# frob:ticket T-0976
def _normal_exit_release_violations(
    func,  # noqa: ANN001
    symref: str,
    resource: str,
    path: str,
    release_lines: list[int],
    terminator_lines: list[int],
    policy: str,
) -> list[Violation]:
    """PROTO005's NORMAL-EXIT half (`_acquiring_function_violations`'s
    docstring): one finding per `return` (or, with none, one implicit
    fallthrough exit) not postdominated by an earlier release call, unless
    a `process-exit-ok` policy's terminator call already discharges it."""
    exits: list[tuple[int, str]] = [(r.line, "return") for r in func.returns]
    if not exits:
        exits = [(func.line + max(func.body_line_count - 1, 0), "fallthrough")]

    violations: list[Violation] = []
    for line, kind in exits:
        if any(rl <= line for rl in release_lines):
            continue
        if policy == "process-exit-ok" and any(tl <= line for tl in terminator_lines):
            continue
        violations.append(
            Violation(
                rule="PROTO005",
                severity=Severity.ERROR,
                file=path,
                line=line,
                message=(
                    f"PROTO005: {symref} acquires {resource!r} but its "
                    f"{kind} at line {line} is not postdominated by any "
                    "release call reachable earlier in this same function "
                    "-- cleanup-obligation violation on this exit path; "
                    'frob:waive PROTO005 reason="..." if a discharge this '
                    "check cannot see (a language excuse, or a release "
                    "genuinely performed by a different function on this "
                    "exact path) makes this exit safe"
                ),
            )
        )
    return violations


# frob:ticket T-0976
def _exceptional_exit_release_violation(
    module,
    func,
    symref: str,
    resource: str,
    path: str,
    policy: str,  # noqa: ANN001
) -> Violation | None:
    """PROTO005's EXCEPTIONAL-EXIT half (`_acquiring_function_violations`'s
    docstring, existential/false-negative-biased): fires only when
    `symref`'s own may-raise set is non-empty and no release call appears
    anywhere in its body at all, unless a `process-exit-ok` policy's
    raises are entirely `SystemExit`."""
    mayraise = compute_may_raise(module)
    summary = mayraise.get(symref)
    if summary is None or not summary.raises:
        return None
    if policy == "process-exit-ok" and summary.raises <= {"SystemExit"}:
        return None
    return Violation(
        rule="PROTO005",
        severity=Severity.ERROR,
        file=path,
        line=func.line,
        message=(
            f"PROTO005: {symref} acquires {resource!r} and "
            f"may raise {sorted(summary.raises)}, but no "
            "release call appears anywhere in its body -- "
            "an exceptional exit skips cleanup; "
            'frob:waive PROTO005 reason="..." if a '
            "discharge this check cannot see makes this "
            "safe"
        ),
    )


# frob:ticket T-0747
def _cleanup_obligation_violations(
    root: Path, edges: tuple[Edge, ...]
) -> list[Violation]:
    """T-0747's per-package cleanup-obligation scan over `edges`' own
    `ACQUIRE`/`RELEASE`/`ESCAPES` directives (docs/modules/graph.md#
    resource-tracking-dsl): a symbol that directly `frob:escapes` its
    acquired resource transfers the obligation to its caller (discharged,
    no check at all -- ESCAPE TRANSFER); one that also directly
    `frob:release`s the SAME resource itself is trusted at function
    granularity (no statement-level attachment exists in this DSL to
    subdivide a single function's own body further -- see
    `docs/modules/graph.md`'s resource-tracking section); every other
    acquisition gets `_acquiring_function_violations`'s real
    intraprocedural postdominance check, restricted to the SAME file
    (`RELEASE` edges from a different file are never wired to a bare-name
    call site this scan can see -- a cross-file release is exactly the
    T-0809/T-0745 "escaped resources" shape and belongs behind an explicit
    `frob:escapes`, not an implicit cross-file guess)."""
    own_acquire: dict[str, set[str]] = {}
    own_release: dict[str, set[str]] = {}
    own_escapes: dict[str, set[str]] = {}
    for e in edges:
        if e.kind is EdgeKind.ACQUIRE:
            own_acquire.setdefault(e.src, set()).add(e.target)
        elif e.kind is EdgeKind.RELEASE:
            own_release.setdefault(e.src, set()).add(e.target)
        elif e.kind is EdgeKind.ESCAPES:
            own_escapes.setdefault(e.src, set()).add(e.target)

    violations: list[Violation] = []
    for symref, resources in own_acquire.items():
        path = symref.split("::", 1)[0]
        for resource in resources:
            if resource in own_escapes.get(symref, set()):
                continue  # escape transfer: obligation moves to the receiver
            if resource in own_release.get(symref, set()):
                continue  # self-contained acquire+release, trusted whole
            release_bare_names = frozenset(
                _bare_name(other)
                for other, released in own_release.items()
                if resource in released and other.split("::", 1)[0] == path
            )
            violations.extend(
                _acquiring_function_violations(
                    root, edges, symref, resource, release_bare_names
                )
            )
    return violations


# frob:ticket T-0976
def _collect_protocol_metadata(
    edges: tuple[Edge, ...],
) -> tuple[dict[str, str], dict[str, str | None], dict[str, str]]:
    """`(cleanup, terminal, origin)` per declared protocol from `edges`'
    own `PROTOCOL` edges -- `_cleanup_always_violations`'s metadata-
    collection half, split from its per-protocol violation check."""
    protocol_cleanup: dict[str, str] = {}
    protocol_terminal: dict[str, str | None] = {}
    protocol_origin: dict[str, str] = {}
    for e in edges:
        if e.kind is EdgeKind.PROTOCOL:
            proto = e.target
            protocol_cleanup[proto] = e.attrs.get("cleanup", "on-error")
            states = [
                s.strip() for s in e.attrs.get("states", "").split(",") if s.strip()
            ]
            protocol_terminal[proto] = states[-1] if states else None
            protocol_origin[proto] = e.src.split("::", 1)[0]
    return protocol_cleanup, protocol_terminal, protocol_origin


# frob:ticket T-0747
def _cleanup_always_violations(
    edges: tuple[Edge, ...],
    established: dict[str, set[str]],
    protocol_initials: dict[str, str],
) -> list[Violation]:
    """T-0747's protocol-level cleanup check, the `*_deinit-never-called`
    class named in the ticket's own framing: a `frob:protocol
    cleanup="always"` protocol that HAS been entered somewhere in this
    package's reachable closure (`established` holds some state other than
    its own declared initial one) but whose terminal state (see below) is
    never itself `established`, meaning no reachable transition ever
    closes it back out. `cleanup="on-error"` (the DSL
    default) and `cleanup="process-exit-ok"` protocols are deliberately
    OUT of this check's scope -- the former's cleanup obligation is
    conditional on an error path this existential, non-path-sensitive
    established-state view cannot distinguish from a clean one (same
    approximation limit `_established_states`' own docstring already
    discloses), and the latter explicitly waives a reachable close
    altogether; only `cleanup="always"` makes "never closed" unconditional
    enough to report without a path-sensitive engine.

    TERMINAL STATE, BY DECLARATION ORDER, not by graph shape: the LAST
    entry in `frob:protocol`'s own comma-separated `states=` list (the
    same "uninitialized, active, closed" ordering T-0744's own zero-
    declaration init/deinit inference always emits) -- deliberately NOT
    "any state with zero outgoing frob:transition", which would also
    (wrongly) call a mid-chain state like `active` "terminal" the moment
    no further transition out of it happens to be declared yet, and so
    would trivially satisfy this check the instant `active` itself is
    established, defeating its entire purpose."""
    protocol_cleanup, protocol_terminal, protocol_origin = _collect_protocol_metadata(
        edges
    )

    violations: list[Violation] = []
    for proto, cleanup in protocol_cleanup.items():
        if cleanup != "always":
            continue
        initial = protocol_initials.get(proto)
        terminal = protocol_terminal.get(proto)
        if terminal is None or terminal == initial:
            continue
        reached = established.get(proto, set()) - ({initial} if initial else set())
        if not reached:
            continue  # never entered at all -- nothing to have cleaned up yet
        if terminal in established.get(proto, set()):
            continue
        violations.append(
            Violation(
                rule="PROTO005",
                severity=Severity.ERROR,
                file=protocol_origin.get(proto, ""),
                line=0,
                message=(
                    f"PROTO005: protocol {proto!r} declares "
                    'cleanup="always" and is entered (a non-initial state '
                    f"is established), but its terminal state {terminal!r} "
                    "is never established by any reachable frob:transition "
                    "-- deinit-never-called; frob:waive PROTO005 "
                    'reason="..." if this is a false positive of the '
                    "engine's existential approximation"
                ),
            )
        )
    return violations


# frob:ticket T-0746
# frob:ticket T-0841
def _discharge(root: Path, symref: str, resource: str) -> Violation | None:
    """A `_language_discharge` recorded discharge for `symref`'s file,
    keyed loosely on `resource` (the protocol name -- best-effort,
    textual, same caveat every discharge predicate's own docstring
    already carries) -- `None` when no discharge applies (the caller
    reports its ERROR unchanged); a `Violation` (always `Severity.WARN`,
    NO-FAIL-SILENT: recorded, never silently dropped) naming the
    mechanism when one does."""
    path = symref.split("::", 1)[0]
    try:
        source = (root / path).read_text(encoding="utf-8")
    except OSError:
        return None
    result = _language_discharge(path, source, resource)
    if not result.discharged:
        return None
    return Violation(
        rule="PROTO002",
        severity=Severity.WARN,
        file=path,
        line=0,
        message=(
            f"PROTO002: {symref}'s state requirement on {resource!r} is "
            f"discharged via {result.mechanism} -- {result.reason}"
        ),
    )


# frob:doc docs/modules/gates.md#proto001-t-0813
# frob:enforces CHK-GATE-PROTO001
# frob:ticket T-0813
# frob:tests tests/test_gates.py::TestProtocolSummaryGate.test_unresolved_callee_poisons_a_protocol_tagged_symbol  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolSummaryGate.test_clean_protocol_tagged_symbol_is_not_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolSummaryGate.test_untagged_symbol_with_unresolved_call_is_not_flagged  # noqa: E501
# frob:doc docs/modules/gates.md#proto002proto003-t-0746
# frob:enforces CHK-GATE-PROTO002
# frob:enforces CHK-GATE-PROTO003
# frob:ticket T-0746
# frob:tests tests/test_gates.py::TestProtocolVerificationGate.test_state_never_established_is_an_error  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolVerificationGate.test_state_established_by_a_reachable_transition_is_not_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolVerificationGate.test_state_equal_to_initial_is_not_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolVerificationGate.test_poisoned_summary_at_a_requires_symbol_is_an_error  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolVerificationGate.test_invalid_transition_precondition_never_established_is_an_error  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolVerificationGate.test_valid_transition_chain_is_not_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolVerificationGate.test_python_with_block_discharges_the_requirement  # noqa: E501
# frob:ticket T-0841
# frob:tests tests/test_gates.py::TestProtocolVerificationGate.test_rust_file_state_never_established_is_an_error  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolVerificationGate.test_rust_drop_impl_discharges_the_requirement  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolVerificationGate.test_typescript_using_discharges_the_requirement  # noqa: E501
# frob:ticket T-0840
# frob:tests tests/test_gates.py::TestProtocolOrderingGate.test_call_before_establishing_transition_is_an_ordering_error  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolOrderingGate.test_call_after_establishing_transition_is_not_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolOrderingGate.test_python_with_block_discharges_the_ordering_violation  # noqa: E501
# frob:doc docs/modules/gates.md#proto005-t-0747
# frob:enforces CHK-GATE-PROTO005
# frob:ticket T-0747
# frob:tests tests/test_gates.py::TestCleanupObligationGate.test_early_return_before_release_call_is_an_error  # noqa: E501
# frob:tests tests/test_gates.py::TestCleanupObligationGate.test_release_before_return_is_not_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestCleanupObligationGate.test_escape_transfer_discharges_the_obligation  # noqa: E501
# frob:tests tests/test_gates.py::TestCleanupObligationGate.test_self_contained_acquire_and_release_is_trusted  # noqa: E501
# frob:tests tests/test_gates.py::TestCleanupObligationGate.test_python_with_block_discharges_the_acquisition  # noqa: E501
# frob:tests tests/test_gates.py::TestCleanupObligationGate.test_process_exit_ok_policy_discharges_a_terminator_guarded_return  # noqa: E501
# frob:tests tests/test_gates.py::TestCleanupObligationGate.test_exceptional_exit_with_no_release_anywhere_is_an_error  # noqa: E501
# frob:tests tests/test_gates.py::TestCleanupObligationGate.test_deinit_never_called_for_cleanup_always_protocol_is_an_error  # noqa: E501
# frob:tests tests/test_gates.py::TestCleanupObligationGate.test_deinit_reachable_for_cleanup_always_protocol_is_not_flagged  # noqa: E501
# frob:ticket T-0972
# frob:enforces CHK-GATE-PROTO004
def protocol_summary_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """PROTO001: the real `mark_unresolved=True` production entrypoint into
    `frob.graph.summary.compute_protocol_summaries` (T-0813) -- every
    symbol carrying a `frob:requires`/`frob:transition` directive gets a
    real, repo-scanned protocol summary; one whose summary comes back
    `poisoned` (an unresolved callee somewhere in its transitive call
    closure) is reported.

    T-0841: every `frob.lang.supported_extensions()` file, not just `.py`
    -- `build_call_graph`'s callee-privacy check now reads each grammar
    walker's own `RawSymbol.public` (see
    `frob.graph.callgraph._short_name_index`) instead of hardcoding
    Python's leading-underscore convention, so Rust/C++/TypeScript
    protocol-tagged symbols get the same real repo-scan PROTO001/002/003
    coverage Python symbols already had. `mark_unresolved`'s own naming
    heuristic (which NAMES look unresolved, not which symbols resolve) is
    still Python-specific -- see `build_call_graph`'s T-0841 disclosure --
    so a genuinely dangling call in a non-Python file can still go
    unflagged; a narrower, disclosed gap than the one this ticket closes,
    not the `DEAD001`-class blanket Python-only scope this docstring
    described before T-0841.

    Grouped and cached per package (same directory), mirroring `DEAD001`'s
    posture -- `build_call_graph`/`_package_edges` run at most once per
    package regardless of how many protocol-tagged symbols it contains.

    T-0746: the SAME per-package scan also emits PROTO002 (a `frob:requires`
    symbol whose required state is never established anywhere in the
    reachable closure, or whose summary is poisoned) and PROTO003 (a
    `frob:transition` symbol whose precondition state is never established)
    -- both ERROR by default, with PROTO002 first checking for a language-
    excuse discharge (module docstring) before reporting."""
    from frob.lang import supported_extensions

    exts = supported_extensions()
    tagged_by_package = _tagged_symbols_by_package(snapshot, exts)

    violations: list[Violation] = []
    for package, symrefs in tagged_by_package.items():
        violations.extend(
            _package_protocol_violations(root, snapshot, package, symrefs)
        )
    _log.info(
        "protocol_summary_gate: %d package(s) scanned, %d protocol-tagged "
        "symbol(s), %d violation(s)",
        len(tagged_by_package),
        sum(len(v) for v in tagged_by_package.values()),
        len(violations),
    )
    return tuple(violations)


# frob:ticket T-0976
def _tagged_symbols_by_package(
    snapshot: GraphSnapshot, exts: frozenset
) -> dict[str, list[str]]:
    """Every protocol-tagged symbol in `snapshot`, grouped by package
    (same directory) -- `protocol_summary_gate`'s package-grouping half,
    split from its per-package violation computation."""
    tagged_by_package: dict[str, list[str]] = {}
    for edge in snapshot.edges:
        if edge.kind not in _PROTOCOL_TAG_KINDS:
            continue
        symref = edge.src
        path = symref.split("::", 1)[0]
        if PurePosixPath(path).suffix.lower() not in exts:
            continue
        package = str(PurePosixPath(path).parent)
        tagged_by_package.setdefault(package, []).append(symref)
    return tagged_by_package


# frob:ticket T-0976
def _package_protocol_violations(
    root: Path, snapshot: GraphSnapshot, package: str, symrefs: list[str]
) -> list[Violation]:
    """One package's full PROTO001-005 contribution: builds its call
    graph/summaries/established-states once, then delegates PROTO004/5
    to their own dedicated checks and PROTO001-003 to
    `_entrypoint_protocol_violations` per tagged entrypoint --
    `protocol_summary_gate`'s per-package half, split from its top-level
    package-iteration loop."""
    entrypoints = sorted(set(symrefs))
    sample_symref = entrypoints[0]
    sample_path = sample_symref.split("::", 1)[0]
    files = _package_files(root, sample_path)
    callgraph = build_call_graph(root, files, mark_unresolved=True)
    edges = _package_edges(root, files)
    # T-0840: PROTO004's ordering check needs a summary for every CALLEE
    # any plain (untagged) function in the package calls, not just what is
    # transitively reachable from the tagged entrypoints -- an ordinary
    # caller sitting between two tagged functions is itself untagged and
    # would otherwise never become a root. Every caller
    # `build_ordered_call_graph` found is added as its own summary root
    # alongside the tagged entrypoints; this only WIDENS
    # `result.summaries`' coverage (more roots feeding the same bottom-up
    # fixpoint), it does not change any existing entry's computed value.
    ordered_graph = build_ordered_call_graph(root, files)
    summary_roots = sorted(set(entrypoints) | set(ordered_graph.calls))
    result = compute_protocol_summaries(callgraph, edges, summary_roots)
    established = _established_states(edges, result)
    protocol_initials = _protocol_initial_states(edges)

    violations: list[Violation] = []
    violations.extend(
        _ordered_call_site_violations(
            root, edges, ordered_graph.calls, result.summaries, protocol_initials
        )
    )
    # T-0747: PROTO005, cleanup obligations -- needs neither the callgraph
    # nor compute_protocol_summaries above (a pure intraprocedural +
    # declaration-level scan over this SAME package's edges), reusing this
    # loop's package selection rather than walking the repo a second time
    # for acquire-tagged packages.
    violations.extend(_cleanup_obligation_violations(root, edges))
    violations.extend(_cleanup_always_violations(edges, established, protocol_initials))
    for symref in entrypoints:
        violations.extend(
            _entrypoint_protocol_violations(
                root, snapshot, edges, result, established, package, symref
            )
        )
    return violations


# frob:ticket T-0976
def _entrypoint_protocol_violations(
    root: Path,
    snapshot: GraphSnapshot,
    edges: tuple[Edge, ...],
    result,  # noqa: ANN001
    established: dict[str, set[str]],
    package: str,
    symref: str,
) -> list[Violation]:
    """One tagged `symref`'s PROTO001 (poisoned summary), PROTO002
    (`frob:requires` state-requirement), and PROTO003 (`frob:transition`
    precondition) findings -- `_package_protocol_violations`'s per-
    entrypoint half."""
    summary = result.summaries.get(symref)
    if summary is None:
        return []
    record = snapshot.symbols.get(symref)
    file = symref.split("::", 1)[0]
    line = record.span[0] if record is not None else 0
    violations: list[Violation] = []
    if summary.poisoned:
        violations.append(
            Violation(
                rule="PROTO001",
                severity=Severity.WARN,
                file=file,
                line=line,
                message=(
                    f"PROTO001: {symref}'s protocol summary is poisoned "
                    f"({summary.poison_reason}) -- an unresolved callee "
                    "somewhere in its transitive call closure makes its "
                    "requires/transitions untrustworthy; fix the call, "
                    'or frob:waive PROTO001 reason="..." if the callee '
                    "resolves dynamically"
                ),
            )
        )
    violations.extend(
        _proto002_requires_violations(
            root, edges, symref, summary, established, file, line, package
        )
    )
    violations.extend(
        _proto003_transition_violations(
            root, edges, symref, summary, established, file, line, package
        )
    )
    return violations


# frob:ticket T-0976
def _proto002_requires_violations(
    root: Path,
    edges: tuple[Edge, ...],
    symref: str,
    summary,  # noqa: ANN001
    established: dict[str, set[str]],
    file: str,
    line: int,
    package: str,
) -> list[Violation]:
    """PROTO002, state-requirement verification (T-0746) --
    `_entrypoint_protocol_violations`'s own half, split out. A poisoned
    summary cannot be trusted to have gathered every reachable transition,
    so it is ALSO an ERROR here (stricter than PROTO001's WARN for the
    identical signal) rather than silently skipping the requires check."""
    violations: list[Violation] = []
    for proto, state in _own_requires(edges, symref):
        if summary.poisoned:
            violations.append(
                Violation(
                    rule="PROTO002",
                    severity=Severity.ERROR,
                    file=file,
                    line=line,
                    message=(
                        f"PROTO002: {symref} requires {proto}:{state} but "
                        "its protocol summary is poisoned "
                        f"({summary.poison_reason}) -- cannot verify; "
                        'fix the call or frob:waive PROTO002 reason="..."'
                    ),
                )
            )
            continue
        if state in established.get(proto, set()):
            continue
        discharge = _discharge(root, symref, proto)
        if discharge is not None:
            violations.append(discharge)
            continue
        violations.append(
            Violation(
                rule="PROTO002",
                severity=Severity.ERROR,
                file=file,
                line=line,
                message=(
                    f"PROTO002: {symref} requires {proto}:{state}, but no "
                    "reachable frob:transition establishes it (and it is "
                    "not the protocol's declared initial state) -- state-"
                    "requirement violation, call path rooted at "
                    f"{symref} in package {package}; "
                    'frob:waive PROTO002 reason="..." if this is a false '
                    "positive of the engine's existential approximation"
                ),
            )
        )
    return violations


# frob:ticket T-0976
def _proto003_transition_violations(
    root: Path,
    edges: tuple[Edge, ...],
    symref: str,
    summary,  # noqa: ANN001
    established: dict[str, set[str]],
    file: str,
    line: int,
    package: str,
) -> list[Violation]:
    """PROTO003, invalid-transition verification (T-0746) -- same
    established-state test as PROTO002 applied to a transition's OWN
    precondition (`from=`) rather than a requires directive's declared
    state; `_entrypoint_protocol_violations`'s own half, split out."""
    violations: list[Violation] = []
    for proto, frm, to in _own_transitions(edges, symref):
        if summary.poisoned:
            violations.append(
                Violation(
                    rule="PROTO003",
                    severity=Severity.ERROR,
                    file=file,
                    line=line,
                    message=(
                        f"PROTO003: {symref} transitions {proto}:"
                        f"{frm}->{to} but its protocol summary is "
                        f"poisoned ({summary.poison_reason}) -- cannot "
                        "verify; fix the call or frob:waive PROTO003 "
                        'reason="..."'
                    ),
                )
            )
            continue
        if frm in established.get(proto, set()):
            continue
        discharge = _discharge(root, symref, proto)
        if discharge is not None:
            violations.append(discharge.model_copy(update={"rule": "PROTO003"}))
            continue
        violations.append(
            Violation(
                rule="PROTO003",
                severity=Severity.ERROR,
                file=file,
                line=line,
                message=(
                    f"PROTO003: {symref} transitions {proto}:{frm}->{to}, "
                    f"but precondition state {frm!r} is never established "
                    "(not the protocol's declared initial state, and no "
                    "reachable frob:transition reaches it) -- invalid "
                    "transition, call path rooted at "
                    f"{symref} in package {package}; "
                    'frob:waive PROTO003 reason="..." if this is a false '
                    "positive of the engine's existential approximation"
                ),
            )
        )
    return violations
