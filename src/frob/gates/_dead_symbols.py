"""DEAD001: an unreferenced private symbol is dead code
(docs/modules/gates.md#rule-catalog, T-0422).

Motivating case (T-0418): `_arch_violations_from_suggestions` was written
to fix a real bug but never wired -- zero callers, dead code, and no gate
flagged it. This is the SYMBOL-level analog of the anti-orphan FILE gate
(REF001/T-0396, `frob.gates._refs`): a file with no inbound reference is
an orphan file; a private (leading-underscore, `SymbolRecord.public is
False`) function/class/method with no inbound reference is an orphan
symbol.

Two independent "wired" signals, either one exempts a symbol:

1. REFERENCED: the symbol's symref appears in its own package's
   intra-package reference graph (`frob.graph.callgraph.
   build_reference_graph`, T-0422's broadened sibling of the shared
   `build_call_graph` substrate `frob.dup` and the COV006 reachability
   check already use -- no bespoke third parser here, and no whole-repo
   re-walk: exactly the bounded, per-package file set `build_call_graph`
   was designed for, one package at a time). Broadened, not just a call
   token (`name(...)`), to also catch a dispatch-table/registry entry
   (`COMMANDS = {"new": _new}`) or a decorator target -- `build_call_
   graph` alone measured a large false-positive rate on this repo's own
   `app/*_runner.py` dispatch tables (see this module's Done report).
2. DECLARED: an existing graph edge (`GraphSnapshot.edges`, already
   computed by `frob.graph.build_graph` in the SAME pass that produced
   `snapshot.symbols` -- no second traversal for this half) of kind
   TESTS, DESCRIBES, or INVARIANT targets the symbol directly. A bare
   `frob:ticket` tag does NOT count (every symbol in this repo carries
   one; treating it as "wired" would make this gate fire on nothing).

False-positive guards (T-0422's acceptance criteria): dunder methods
(`__init__`, `__post_init__`, ...), pytest `test_*` functions/`Test*`
classes, and anything a caller waives with `frob:waive DEAD001
reason="..."` (the standard mechanism every other advisory-tier gate in
this repo already uses for a case this best-effort token scan cannot
see -- e.g. a handler reached only via `getattr(obj, "_name")` string
dispatch, which never appears as a bare identifier token at all).

WARN-only (advisory-but-tracked, matching REF/PERF/FUZZ's posture) --
never blocks a build on its own, but every finding must eventually be
fixed (wire it or delete it) or waived with an honest reason.

Python (`.py`) files ONLY in this pass -- see `dead_symbol_gate`'s
docstring for why Rust/TypeScript/C are excluded (a real soundness gap
in the shared `frob.graph.callgraph` substrate's privacy detection, not
a scope choice of convenience).
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from frob.gates._models import Severity, Violation
from frob.gates._waive import known_gate_rule_ids
from frob.gitio import Diff
from frob.graph import EdgeKind, GraphSnapshot, build_reference_graph
from frob.lang import SymbolKind, supported_extensions
from frob.logging import get_logger
from frob.tickets import TicketQueue

_log = get_logger(__name__)

# Kinds this gate reasons about -- CONST/TYPE are data declarations, not
# "wired by being called", and would be pure noise under a call-graph
# reachability check.
_CALLABLE_KINDS = frozenset({SymbolKind.FUNCTION, SymbolKind.METHOD, SymbolKind.CLASS})

# Edge kinds -- other than DESCRIBES, handled separately for its reversed
# src/target direction -- that count as an explicit DECLARED reference to
# a symbol via `Edge.src` (the code symbol the directive lives above).
# Deliberately excludes TICKET (near-universal in this repo, so treating
# it as "wired" would silence this gate entirely) and WAIVE/TODO/DEBT
# (bookkeeping about the symbol, not evidence something else consumes it).
_DECLARED_REFERENCE_KINDS = frozenset({"tests", "invariant"})


def _is_dunder(qualname: str) -> bool:
    """True for a `__name__`-shaped final qualname component (`__init__`,
    `Foo.__post_init__`, ...) -- never flagged, these are protocol hooks
    the language runtime calls, not something any tracked caller invokes
    by name."""
    short = qualname.rsplit(".", 1)[-1]
    return short.startswith("__") and short.endswith("__")


def _is_test_symbol(qualname: str) -> bool:
    """True for a `test_*`/`Test*`-named function/method/class (leading
    underscores stripped first, so a PRIVATE test helper like
    `_test_setup` still counts) -- called by the test RUNNER via naming
    convention or by pytest fixture/setup discovery, never by another
    tracked symbol's call token, so a call-graph reachability check would
    otherwise flag every test as dead (same class of false positive
    `frob.gates._refs`'s file-level gate already exempts)."""
    parts = qualname.split(".")
    return any(p.lstrip("_").startswith(("test_", "Test")) for p in parts)


# frob:ticket T-0422
def _package_files(root: Path, rel_path: str) -> tuple[str, ...]:
    """Every language-supported file beside `rel_path` (same directory),
    repo-root-relative POSIX -- the bounded file set `build_reference_graph`
    resolves intra-package private calls over, one package at a time."""
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


def _declared_referenced_symrefs(snapshot: GraphSnapshot) -> frozenset[str]:
    """Every symref an existing TESTS/DESCRIBES/INVARIANT edge already
    binds to a code symbol (`_DECLARED_REFERENCE_KINDS`) -- pure lookup
    over `snapshot.edges`, already computed by `build_graph`'s single
    pass, no re-derivation.

    Direction differs by kind: a `frob:tests`/`frob:invariant` comment
    lives ABOVE the code symbol it binds (`Edge.src` is that code
    symbol's own symref, `Edge.target` is the test id / invariant id); a
    markdown `frob:describes` anchor lives in the DOC file instead
    (`Edge.src` is the doc anchor, `Edge.target` is the code symbol) --
    so TESTS/INVARIANT contribute `edge.src` here, DESCRIBES contributes
    `edge.target`."""
    referenced: set[str] = set()
    for edge in snapshot.edges:
        if edge.kind is EdgeKind.DESCRIBES:
            referenced.add(edge.target.split("#", 1)[0])
        elif edge.kind.value in _DECLARED_REFERENCE_KINDS:
            referenced.add(edge.src.split("#", 1)[0])
    return frozenset(referenced)


# frob:doc docs/modules/gates.md#rule-catalog
# frob:ticket T-0422
# frob:tests tests/test_gates.py::TestDeadSymbolGate.test_unwired_private_function_is_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestDeadSymbolGate.test_called_private_helper_is_not_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestDeadSymbolGate.test_dunder_method_is_not_flagged
# frob:tests tests/test_gates.py::TestDeadSymbolGate.test_test_function_is_not_flagged
# frob:tests tests/test_gates.py::TestDeadSymbolGate.test_tests_edge_target_is_not_flagged  # noqa: E501
# frob:enforces CHK-GATE-DEAD001
# frob:waive ARCH001 reason="the per-package reference-graph cache (called_by_package) is built lazily inside the loop and keyed by the record being examined; splitting the per-record body into a helper would require passing the mutable cache dict and root/package derivation across a new boundary for no reduction in branching, the same shape already accepted for this module's sibling gates"  # noqa: E501
def dead_symbol_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DEAD001: a private (leading-underscore) function/class/method with
    no call-graph caller and no TESTS/DESCRIBES/INVARIANT edge is
    unreferenced -- written but never wired, or genuinely dead. Every
    package's own `build_reference_graph` result is built once and reused for
    every private symbol declared in that package (never rebuilt per
    symbol).

    Python files ONLY (`.py`): `build_reference_graph`'s callee-privacy check
    (`callgraph._short_name_index`) hardcodes the leading-underscore
    convention `SymbolRecord.public` uses for Python
    (`frob.lang._walk_python`) -- but Rust (`pub`), TypeScript
    (`export`), and C (`static`) each compute `public` from a completely
    different marker, one the call graph never consults. Running this
    check against those languages measured a ~100% false-positive rate
    on this repo's own `frob-core`/`strata-core` Rust sources (every
    `Parser.advance`-style heavily-called method came back "uncalled"
    because the call graph never even attempts to resolve a callee whose
    short name lacks a leading underscore) -- a soundness gap in the
    shared substrate, not something this gate should paper over with a
    per-language guess. See this ticket's Done report for the filed
    follow-up."""
    referenced = _declared_referenced_symrefs(snapshot)
    called_by_package: dict[str, frozenset[str]] = {}
    violations: list[Violation] = []

    for record in snapshot.symbols.values():
        if record.public or record.kind not in _CALLABLE_KINDS:
            continue
        if not record.id.path.endswith(".py"):
            continue
        qualname = record.id.qualname
        if _is_dunder(qualname) or _is_test_symbol(qualname):
            continue
        symref = record.symref
        if symref in referenced:
            continue
        package = str(PurePosixPath(record.id.path).parent)
        called = called_by_package.get(package)
        if called is None:
            files = _package_files(root, record.id.path)
            graph = build_reference_graph(root, files)
            called = frozenset(
                callee for callees in graph.calls.values() for callee in callees
            )
            called_by_package[package] = called
        if symref in called:
            continue
        violations.append(
            Violation(
                rule="DEAD001",
                severity=Severity.WARN,
                file=record.id.path,
                line=record.span[0],
                message=(
                    f"DEAD001: {symref} is a private symbol with no call-graph "
                    "caller and no frob:tests/frob:describes/frob:invariant edge "
                    "-- wire it, delete it, or "
                    'frob:waive DEAD001 reason="..." if it is reached only '
                    "dynamically"
                ),
            )
        )
    _log.info(
        "dead_symbol_gate: %d package(s) scanned, %d violation(s)",
        len(called_by_package),
        len(violations),
    )
    return tuple(violations)


# ---------------------------------------------------------------------------
# WIRE001/WIRE002 (T-1428): a ticket's own diff adds code nothing outside its
# own tests can reach.
# ---------------------------------------------------------------------------
#
# DEAD001 above asks "does ANY private symbol in the tree have a caller".
# WIRE001 asks a narrower, diff-scoped question that DEAD001 structurally
# cannot answer: "does the symbol/rule-id/CLI-flag this DIFF just added have
# a caller/registration OUTSIDE the diff's own test files" -- catching
# PUBLIC additions too (DEAD001 exempts every public symbol by design), and
# catching the "string in a list" wiring shape (a new gate rule id, a new
# CLI flag's argparse `dest`) that never appears as a call token at all and
# so is invisible to call-graph analysis of any kind, per this module's own
# `build_reference_graph`/`build_call_graph` substrate (see
# `_is_reached_outside_diff_tests`'s docstring for why a text scan, not the
# call graph, is used here).
#
# Three of the four real-instance shapes this ticket names are implemented:
#   1. a new function/method/class with no non-test caller (T-1421)
#   2. a new gate rule id literal absent from `_KNOWN_GATE_RULES` (T-1421's
#      BUG002)
#   3. a new CLI flag `dest=` absent from `_config_external.py`'s copy
#      lists (T-1422) -- the "string in a list" shape, handled by a
#      TARGETED check, not the call graph (see module docstring on that
#      function)
# The fourth shape -- a new keyword-only parameter no call site passes
# (T-1384/T-1399/T-1391) -- needs a signature-level before/after AST diff
# this ticket does not build; disclosed in this ticket's Done report with a
# follow-up ticket, per the acceptance note that regression tests need
# reconstruct only two of the four shapes.

_RULE_ID_LITERAL_RE = re.compile(r'rule\s*=\s*"([A-Z][A-Z0-9]{1,9}\d{3})"')
_CLI_DEST_LITERAL_RE = re.compile(r'\bdest\s*=\s*"([a-z][a-z0-9_]*)"')
_CLI_PARSER_DIR_PREFIX = "src/frob/_cli_parsers/"
_CONFIG_EXTERNAL_PATH = "src/frob/app/_config_external.py"


def _short_name(qualname: str) -> str:
    """The final dotted component of a qualname (`Foo.bar` -> `bar`) --
    what a bare call token in another file's source actually spells,
    mirroring `frob.graph.callgraph._short_name`'s own definition (not
    imported: that helper is private to a module this file does not
    otherwise depend on, and the rule is a one-line string operation)."""
    return qualname.rsplit(".", 1)[-1]


def _hunks_by_file(diff: Diff) -> dict[str, list[tuple[int, int]]]:
    """`diff.hunks` grouped by file -- the shared shape every WIRE001 sub-
    check below indexes into, computed once per gate run."""
    by_file: dict[str, list[tuple[int, int]]] = {}
    for hunk in diff.hunks:
        by_file.setdefault(hunk.file, []).append(hunk.span)
    return by_file


def _added_lines(
    root: Path, hunks_by_file: dict[str, list[tuple[int, int]]]
) -> dict[str, list[tuple[int, str]]]:
    """Exact `(line_no, text)` pairs for every line inside one of this
    diff's hunks, read from the CURRENT working-tree file content --
    `Diff.hunks` records only new-file line SPANS (no text), so this
    recovers what those spans cover without a second diff/text parser.
    Skips a file the working tree no longer has (deleted since the diff
    was computed) rather than raising."""
    by_file: dict[str, list[tuple[int, str]]] = {}
    for file, spans in hunks_by_file.items():
        try:
            lines = (root / file).read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for start, end in spans:
            for lineno in range(start, end + 1):
                if 1 <= lineno <= len(lines):
                    by_file.setdefault(file, []).append((lineno, lines[lineno - 1]))
    return by_file


def _new_callable_records(
    snapshot: GraphSnapshot, hunks_by_file: dict[str, list[tuple[int, int]]]
) -> list:
    """Every function/method/class whose ENTIRE span sits inside one of
    this diff's added-line hunks -- the proxy this gate uses for "this
    diff DEFINED this symbol" (as opposed to merely touching an existing
    one, e.g. adding one line to an existing function body). A whole-body
    rewrite of a pre-existing symbol would also match this proxy (a false
    positive DEAD001 does not have, since DEAD001 asks about every private
    symbol unconditionally rather than trying to tell "new" from
    "rewritten") -- accepted because the alternative (a full parse-at-base-
    revision diff) is materially more machinery for a WARN-adjacent-to-
    ERROR gate that already has a `frob:waive WIRE001` escape hatch for a
    genuine false positive."""
    found = []
    for record in snapshot.symbols.values():
        if record.kind not in _CALLABLE_KINDS or not record.id.path.endswith(".py"):
            continue
        qualname = record.id.qualname
        if _is_dunder(qualname) or _is_test_symbol(qualname):
            continue
        spans = hunks_by_file.get(record.id.path, ())
        if any(h[0] <= record.span[0] and record.span[1] <= h[1] for h in spans):
            found.append(record)
    return found


def _is_reached_outside_diff_tests(
    root: Path, snapshot: GraphSnapshot, record, def_lines: frozenset[int]
) -> bool:
    """True if `record`'s short name appears, call-shaped, in any non-test
    file in the snapshot other than on one of its own definition lines.

    DELIBERATELY a text scan, not `build_reference_graph`/`build_call_graph`
    (this module's own DEAD001 substrate): both of those resolve an edge
    ONLY when the callee is PRIVATE (`_resolve_edges`'s "never a public
    symbol" rule, `frob.graph.callgraph`) -- exactly backwards for WIRE001,
    whose motivating instances (T-1384's `own_obligations_clean`, T-1421's
    `bug_repro_violations`) are PUBLIC symbols DEAD001 exempts by design.
    A bare short-name-plus-paren scan is strictly MORE permissive than a
    real call-graph match (an unrelated same-named function elsewhere
    counts as "reached" here), which is the correct bias for a gate that
    must not over-fire: a false "reached" verdict costs nothing (WIRE001
    just does not fire), a false "unreached" verdict wrongly blocks a
    build. This mirrors `build_reference_graph`'s own module docstring
    logic (broader recall over precision) rather than inventing a new
    tradeoff."""
    short = _short_name(record.id.qualname)
    call_pattern = re.compile(rf"(?<![A-Za-z0-9_.]){re.escape(short)}\s*\(")
    def_pattern = re.compile(rf"^\s*(async\s+def|def|class)\s+{re.escape(short)}\b")
    for path in snapshot.file_hashes:
        if not path.endswith(".py"):
            continue
        from frob.gates import _is_test_path

        if _is_test_path(path):
            continue
        try:
            lines = (root / path).read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        own_def_lines = def_lines if path == record.id.path else frozenset()
        for lineno, text in enumerate(lines, 1):
            if lineno in own_def_lines:
                continue
            if def_pattern.match(text):
                continue
            if call_pattern.search(text):
                return True
    return False


def _wire001_unwired_symbol_violations(
    root: Path,
    snapshot: GraphSnapshot,
    hunks_by_file: dict[str, list[tuple[int, int]]],
) -> list[Violation]:
    """WIRE001 case 1: a new function/method/class this diff defines with
    no non-test caller anywhere in the tree (see `_is_reached_outside_
    diff_tests`)."""
    violations: list[Violation] = []
    for record in _new_callable_records(snapshot, hunks_by_file):
        def_lines = frozenset(range(record.span[0], record.span[1] + 1))
        if _is_reached_outside_diff_tests(root, snapshot, record, def_lines):
            continue
        violations.append(
            Violation(
                rule="WIRE001",
                severity=Severity.ERROR,
                file=record.id.path,
                line=record.span[0],
                symref=record.symref,
                message=(
                    f"WIRE001: {record.symref} is new in this diff and has no "
                    "caller outside its own tests -- wire it, delete it, or "
                    'frob:waive WIRE001 reason="..." follow_up="T-####" naming '
                    "the open ticket that will wire it"
                ),
            )
        )
    return violations


def _wire001_rule_id_violations(
    added_lines: dict[str, list[tuple[int, str]]],
) -> list[Violation]:
    """WIRE001 case 2: a new `rule=<literal>` construction (a gate/check
    emitting a fresh rule id) whose id is absent from `_KNOWN_GATE_RULES`
    -- the gate fires findings under an id `frob:waive`/`WAIVE002`/tooling
    has never heard of, T-1421's BUG002 shape."""
    known = known_gate_rule_ids()
    violations: list[Violation] = []
    for file, lines in added_lines.items():
        if not file.endswith(".py"):
            continue
        for lineno, text in lines:
            match = _RULE_ID_LITERAL_RE.search(text)
            if match is None:
                continue
            rule_id = match.group(1)
            if rule_id in known:
                continue
            violations.append(
                Violation(
                    rule="WIRE001",
                    severity=Severity.ERROR,
                    file=file,
                    line=lineno,
                    message=(
                        f"WIRE001: {file}:{lineno} emits rule={rule_id!r}, which "
                        "is not in _KNOWN_GATE_RULES (src/frob/gates/_waive.py) "
                        "-- add it there in the same diff, or "
                        'frob:waive WIRE001 reason="..." follow_up="T-####" '
                        "naming the open ticket that will register it"
                    ),
                )
            )
    return violations


def _wire001_cli_dest_violations(
    root: Path, added_lines: dict[str, list[tuple[int, str]]]
) -> list[Violation]:
    """WIRE001 case 3: a new CLI `add_argument(..., dest="foo")` under
    `src/frob/_cli_parsers/**` whose `dest` string never appears in
    `_config_external.py` -- T-1422's shape, and the one the ticket brief
    calls out as invisible to the call graph entirely: the wiring is a
    quoted string landing inside one of `_build_external_config_kwargs`'s
    field-name tuples, never a call token. A targeted string-membership
    check over `_config_external.py`'s CURRENT text (not a per-tuple
    parse) is deliberately used instead of trying to locate the exact
    copy-loop tuple -- the six tuples are an implementation detail of one
    function this gate should not have to keep in lockstep with; "the dest
    string appears anywhere in that file's source" is the same signal
    `config.py`'s own in-file warning describes (a field is either copied
    somewhere in that file, or it is silently dropped)."""
    try:
        config_external_text = (root / _CONFIG_EXTERNAL_PATH).read_text(
            encoding="utf-8"
        )
    except (OSError, UnicodeDecodeError):
        config_external_text = None
    violations: list[Violation] = []
    for file, lines in added_lines.items():
        if not file.startswith(_CLI_PARSER_DIR_PREFIX) or not file.endswith(".py"):
            continue
        for lineno, text in lines:
            match = _CLI_DEST_LITERAL_RE.search(text)
            if match is None:
                continue
            dest = match.group(1)
            if config_external_text is not None and f'"{dest}"' in config_external_text:
                continue
            violations.append(
                Violation(
                    rule="WIRE001",
                    severity=Severity.ERROR,
                    file=file,
                    line=lineno,
                    message=(
                        f"WIRE001: {file}:{lineno} adds CLI dest={dest!r}, which "
                        f"never appears in {_CONFIG_EXTERNAL_PATH} -- argparse "
                        "parses it and AppConfig.from_external silently drops "
                        "it before AppConfig(**d) (T-1422's shape); copy it "
                        "into the matching field-name tuple there, or "
                        'frob:waive WIRE001 reason="..." follow_up="T-####" '
                        "naming the open ticket that will wire it"
                    ),
                )
            )
    return violations


def _wire002_violations(snapshot: GraphSnapshot, queue: TicketQueue) -> list[Violation]:
    """WIRE002: a `frob:waive WIRE001` present without a `follow_up="T-####"`
    attribute naming a real, still-open ticket -- the escape hatch this
    ticket's brief demands ("require naming WHO is expected to call it and
    BY WHEN") turned into a checkable fact rather than free-text prose. A
    missing `follow_up=`, an id that resolves to no ticket, or a ticket
    already `done`/`dropped` all count -- an obligation that names nobody
    accountable is not an obligation."""
    from frob.gates import _OPEN_STATES, _edges_of_kind, _site_from_edge_origin

    violations: list[Violation] = []
    for edge in _edges_of_kind(snapshot, EdgeKind.WAIVE):
        if edge.target != "WIRE001":
            continue
        follow_up = edge.attrs.get("follow_up")
        ticket = queue.tickets.get(follow_up) if follow_up else None
        if ticket is not None and ticket.state in _OPEN_STATES:
            continue
        file, line = _site_from_edge_origin(edge.origin)
        if follow_up is None:
            detail = 'is missing a follow_up="T-####" attribute'
        elif ticket is None:
            detail = f"names {follow_up!r}, which is not a real ticket id"
        else:
            detail = f"names {follow_up!r}, which is already {ticket.state.value}"
        violations.append(
            Violation(
                rule="WIRE002",
                severity=Severity.ERROR,
                file=file,
                line=line,
                message=(
                    f"WIRE002: frob:waive WIRE001 at {edge.src} {detail} -- a "
                    "WIRE001 waiver must bind to a real, open follow-up ticket"
                ),
            )
        )
    return violations


# frob:doc docs/modules/gates.md#rule-catalog
# frob:ticket T-1428
# frob:tests tests/test_gates.py::TestWireGate.test_new_public_function_with_no_caller_is_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestWireGate.test_new_function_called_from_non_test_code_is_not_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestWireGate.test_new_cli_dest_missing_from_config_external_is_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestWireGate.test_new_cli_dest_present_in_config_external_is_not_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestWireGate.test_new_rule_id_missing_from_known_gate_rules_is_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestWireGate.test_new_rule_id_present_in_known_gate_rules_is_not_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestWireGate.test_wire002_fires_when_follow_up_ticket_missing  # noqa: E501
# frob:tests tests/test_gates.py::TestWireGate.test_wire002_fires_when_follow_up_ticket_is_closed  # noqa: E501
# frob:tests tests/test_gates.py::TestWireGate.test_wire002_clean_when_follow_up_ticket_is_open  # noqa: E501
# frob:enforces CHK-GATE-WIRE001
# frob:enforces CHK-GATE-WIRE002
def wire_gate(
    root: Path, snapshot: GraphSnapshot, diff: Diff, queue: TicketQueue
) -> tuple[Violation, ...]:
    """WIRE001/WIRE002 (T-1428): refuse a ticket's own diff when it adds a
    function/method/class, a gate rule id, or a CLI flag `dest` that
    nothing outside the diff's own tests can reach -- the repeated "landed,
    passed every gate, did nothing" defect this repo's own history names
    (T-1384, T-1399, T-1391, T-1421, T-1422). ERROR-tier (unlike DEAD001's
    advisory WARN): a diff-scoped inert addition is exactly the shape a
    ticket close should refuse, not merely flag."""
    hunks_by_file = _hunks_by_file(diff)
    added_lines = _added_lines(root, hunks_by_file)
    violations = [
        *_wire001_unwired_symbol_violations(root, snapshot, hunks_by_file),
        *_wire001_rule_id_violations(added_lines),
        *_wire001_cli_dest_violations(root, added_lines),
        *_wire002_violations(snapshot, queue),
    ]
    _log.info("wire_gate: %d violation(s)", len(violations))
    return tuple(violations)
