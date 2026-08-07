"""WIRE001/WIRE002: a newly-added symbol nothing outside its own tests can
reach, and a ticket that claims a rule id no gate actually enforces
(T-1420, split out of `frob.gates._dead_symbols`).

Split for the same LARGE001 residue-burndown reason `_sys.py`/
`_sys_selfaudit.py` were split (T-1420's own ticket): `_dead_symbols.py`
held two independent gate families sharing only a module (DEAD001, still
there, and this one) -- WIRE001 (a diff-added symbol reachable only from
its own added test file, `_wire001_unwired_symbol_violations` and its
`_wire001_rule_id_violations`/`_wire001_cli_dest_violations`/
`_wire001_new_kwonly_param_violations` sibling sub-checks) and WIRE002 (a
ticket's Done report cites a `frob:enforces CHK-...` id no live gate
registers, `_wire002_violations`). `wire_gate` composes both, unchanged
from its pre-split behavior; `frob.gates.__init__` imports `wire_gate`
from here now instead of `_dead_symbols`.
"""
# frob:ticket T-1420
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import ast
import re
import tempfile
from pathlib import Path

from frob.gates._dead_symbols import (
    _CALLABLE_KINDS,
    _is_autouse_pytest_fixture,
    _is_dunder,
    _is_test_symbol,
)
from frob.gates._models import Severity, Violation
from frob.gates._waive import known_gate_rule_ids
from frob.gitio import Diff, run_argv
from frob.graph import Edge, EdgeKind, GraphSnapshot
from frob.graph.callgraph import _WRAPPER_MARKER_NAMES
from frob.graph.digest import compute_digests
from frob.lang import SymbolKind, parse_file
from frob.logging import get_logger
from frob.tickets import TicketQueue

_log = get_logger(__name__)


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
# All four real-instance shapes this ticket names are implemented:
#   1. a new function/method/class with no non-test caller (T-1421)
#   2. a new gate rule id literal absent from `_KNOWN_GATE_RULES` (T-1421's
#      BUG002)
#   3. a new CLI flag `dest=` absent from `_config_external.py`'s copy
#      lists (T-1422) -- the "string in a list" shape, handled by a
#      TARGETED check, not the call graph (see module docstring on that
#      function)
#   4. a new keyword-only parameter added to an EXISTING function's
#      signature that no call site passes (T-1384/T-1399/T-1391, T-1430)
#      -- `_wire001_new_kwonly_param_violations` diffs the function's
#      keyword-only parameter set at the diff's merge-base against its
#      current set (stdlib `ast`, not the token-stream digest machinery
#      T-1431's relocation check uses -- a plain name-set diff is exact
#      here, no false-positive-from-body-rewrite risk to guard against).

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


# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to \
# Path.read_text/str.splitlines and dict.setdefault, plain pathlib/str/dict operations \
# the resolver cannot statically bound; the one real raise path (a deleted/unreadable \
# file) is caught below"
# frob:waive EXHAUST002 reason="T-1371: same resolver artifact as EXHAUST003 above -- \
# every dict access below is dict.setdefault (never raises KeyError by construction), \
# not a bare subscript; a false positive from the gate's syntactic scan"
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
    root: Path,
    snapshot: GraphSnapshot,
    hunks_by_file: dict[str, list[tuple[int, int]]],
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
    genuine false positive. T-1510: also excludes an autouse pytest fixture
    (`_is_autouse_pytest_fixture`) -- pytest's own injection machinery
    reaches it for every test in scope, not a caller this gate's text scan
    can ever see."""
    found = []
    for record in snapshot.symbols.values():
        if record.kind not in _CALLABLE_KINDS or not record.id.path.endswith(".py"):
            continue
        qualname = record.id.qualname
        if _is_dunder(qualname) or _is_test_symbol(qualname):
            continue
        if _is_autouse_pytest_fixture(root, record):
            continue
        spans = hunks_by_file.get(record.id.path, ())
        if any(h[0] <= record.span[0] and record.span[1] <= h[1] for h in spans):
            found.append(record)
    return found


# T-1532: a gate function registered into the process job table as a bare
# FIRST POSITIONAL ARGUMENT -- e.g. "cache": _ProcessJob(cache_gate, (...))
# in src/frob/gates/__init__.py -- is genuinely wired (the job table
# invokes it) but never appears text-adjacent to its own opening paren,
# the exact same "passed by reference, not called" shape T-0583/T-1502
# already teach `_WRAPPER_MARKER_NAMES` to recognize. Reused via the same
# combined alternation rather than a second regex, since the text shape
# (`Marker(short, ...)`) is identical either way.
# frob:ticket T-1532
_JOB_TABLE_MARKER_NAMES = frozenset({"_ProcessJob"})


# frob:ticket T-1502
def _wire_reach_patterns(
    short: str, kind: SymbolKind
) -> tuple[re.Pattern[str], re.Pattern[str], re.Pattern[str] | None]:
    """The three "reached" regexes `_is_reached_outside_diff_tests` scans
    with: a plain call-shaped token, the T-1502/T-1532/T-1684
    bare-name-argument shape (decorator/memoization wrapper markers, job-
    table constructors, PLUS dict-table values -- all three pass the
    symbol BY REFERENCE, not as a call),
    and (CLASS records only, T-1527) the ErrorSet bare-member-access
    shape -- split out purely to keep the scanning function itself under
    ARCH001's line threshold, no behavior change from inlining."""
    call_pattern = re.compile(rf"(?<![A-Za-z0-9_.]){re.escape(short)}\s*\(")
    marker_names = "|".join(
        re.escape(name) for name in (*_WRAPPER_MARKER_NAMES, *_JOB_TABLE_MARKER_NAMES)
    )
    # T-1684: a DICT-TABLE entry (`"sweep-async": _sweep_async,` in
    # `_ticket_dispatch_table`) is the third by-reference wiring shape in
    # this repo, alongside the wrapper-marker and job-table ones above --
    # every `frob ticket <verb>` handler is wired exactly this way and
    # nothing else ever calls it by name. Without this, every new CLI
    # subcommand handler is a WIRE001 false positive whose only remedy is
    # a waiver, which is how a gate teaches people to waive it.
    wrapper_pattern = re.compile(
        rf"(?<![A-Za-z0-9_.])(?:{marker_names})\s*\(\s*{re.escape(short)}\s*[,)]"
        rf"|:\s*{re.escape(short)}\s*[,}}]"
    )
    member_access_pattern = None
    if kind == SymbolKind.CLASS:
        member_access_pattern = re.compile(
            rf"(?<![A-Za-z0-9_.]){re.escape(short)}\.[A-Za-z_][A-Za-z0-9_]*"
        )
    return call_pattern, wrapper_pattern, member_access_pattern


# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to re.compile/ \
# Path.read_text/str.splitlines, stdlib/pathlib calls the resolver cannot statically \
# bound; a malformed short-name cannot reach re.compile since it is always \
# re.escape()'d first, and file-read failure is caught below"
# frob:waive EXHAUST002 reason="T-1371: same resolver artifact as EXHAUST003 above -- \
# snapshot.file_hashes iteration and enumerate(lines, 1) are plain iteration, not \
# dict/list subscripting that can raise KeyError; a false positive from the gate's \
# syntactic scan"
# frob:ticket T-1558
def _wire_test_path_excluded(candidate_path: str, record_path: str) -> bool:
    """True if `candidate_path` must NOT count as a "reached" caller for a
    symbol defined at `record_path` -- a production symbol (`record_path`
    outside `tests/`) excludes every test path (a test-only caller does
    not wire code that ships); a test-tree symbol excludes only its OWN
    defining file (same-file usage stays genuinely unwired, T-1592's
    precedent), so a call from a DIFFERENT test file now counts as
    reached (T-1558: the module-local test-fixture false-positive class,
    16 waivers accumulated against this exact gap before this landed)."""
    from frob.gates import _is_test_path

    if not _is_test_path(candidate_path):
        return False
    if not _is_test_path(record_path):
        return True
    return candidate_path == record_path


# frob:ticket T-1502
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
    tradeoff.

    T-1502/T-1527: `_wire_reach_patterns` ALSO builds a wrapper-marker-
    argument pattern (`memoize_per_run(_target)`, passed BY REFERENCE,
    never `_target(`-shaped -- reuses `frob.graph.callgraph`'s own
    `_WRAPPER_MARKER_NAMES`) and, for a CLASS record only, a bare
    `ClassName.Member` attribute-access pattern (the shape a typani
    `ErrorSet` subclass is actually referenced by -- never `ClassName(`,
    since an ErrorSet is never instantiated by calling the class). See
    that helper's own docstring for the full rationale of each shape.

    T-1558: a symbol DEFINED under `tests/` is reachable from ANOTHER test
    file, not just from non-test code -- a shared test-fixture helper
    (`tests/_cache_transparency.py::git_init`) is genuinely wired, just
    entirely within the test tree (see `_wire_test_path_excluded` below
    for the exact rule)."""
    short = _short_name(record.id.qualname)
    call_pattern, wrapper_pattern, member_access_pattern = _wire_reach_patterns(
        short, record.kind
    )
    def_pattern = re.compile(rf"^\s*(async\s+def|def|class)\s+{re.escape(short)}\b")
    for path in snapshot.file_hashes:
        if not path.endswith(".py"):
            continue
        if _wire_test_path_excluded(path, record.id.path):
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
            if call_pattern.search(text) or wrapper_pattern.search(text):
                return True
            if member_access_pattern is not None and member_access_pattern.search(text):
                return True
    return False


def _base_name_match_paths(root: Path, base: str, short: str) -> frozenset[str]:
    """Paths at revision `base` whose text defines a `def`/`class` named
    `short`, via one `git grep -l` (cheap, no parse) -- empty on grep
    failure or no match (rc=1 is git grep's "no match", not an error)."""
    pattern = rf"^[[:space:]]*(async[[:space:]]+def|def|class)[[:space:]]+{short}\b"
    grep = run_argv(
        ("git", "-C", str(root), "grep", "-lE", pattern, base, "--", "*.py")
    )
    if grep.is_err or grep.danger_ok.returncode not in (0, 1):
        return frozenset()
    paths: set[str] = set()
    for line in grep.danger_ok.stdout.splitlines():
        # git grep -l on a revision spec prints "<rev>:<path>".
        _, _, path = line.partition(":")
        if path:
            paths.add(path)
    return frozenset(paths)


def _parsed_scratch_symbols(text: str, suffix: str) -> tuple:
    """Symbols of `text` parsed through a scratch temp file (since
    `frob.lang.parse_file` only reads a real `Path`) -- empty on parse
    failure (the caller treats that as "no match", never an exemption)."""
    with tempfile.NamedTemporaryFile(
        suffix=suffix, mode="w", encoding="utf-8", delete=False
    ) as handle:
        handle.write(text)
        tmp_path = Path(handle.name)
    try:
        parsed = parse_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    return () if parsed.is_err else tuple(parsed.danger_ok.symbols)


def _base_blob_symbol_digests(
    root: Path, base: str, path: str, short: str
) -> tuple[str, ...]:
    """Body (or, body-less, signature) digests of every symbol named
    `short` in blob `base:path` -- one `git show` read fed through
    `_parsed_scratch_symbols`. Empty on any show/parse failure."""
    show = run_argv(("git", "-C", str(root), "show", f"{base}:{path}"))
    if show.is_err or show.danger_ok.returncode != 0:
        return ()
    suffix = Path(path).suffix or ".py"
    return tuple(
        digests.body or digests.sig
        for symbol in _parsed_scratch_symbols(show.danger_ok.stdout, suffix)
        if _short_name(symbol.qualname) == short
        for digests in (compute_digests(symbol),)
    )


def _merge_base_body_match(
    root: Path, base: str, short: str, target_digest: str
) -> bool:
    """True if a `def`/`class` named `short` existed ANYWHERE in the tree at
    `base` (the diff's merge-base sha) whose body (or, for a body-less
    symbol, signature) digest equals `target_digest` -- the T-1431
    relocation check. `_base_name_match_paths` finds candidate paths by
    name (cheap, no parse needed for the common "no prior symbol by this
    name at all" case); only a name-match candidate pays for
    `_base_blob_symbol_digests`'s blob read + parse. Digest equality, not
    just a name match, is required -- two unrelated symbols can share a
    short name."""
    return any(
        target_digest in _base_blob_symbol_digests(root, base, path, short)
        for path in _base_name_match_paths(root, base, short)
    )


def _wire001_unwired_symbol_violations(
    root: Path,
    snapshot: GraphSnapshot,
    hunks_by_file: dict[str, list[tuple[int, int]]],
    diff: Diff,
) -> list[Violation]:
    """WIRE001 case 1: a new function/method/class this diff defines with
    no non-test caller anywhere in the tree (see `_is_reached_outside_
    diff_tests`), EXCLUDING a symbol this diff merely RELOCATED (T-1431):
    a file split (LARGE001) moves an existing symbol verbatim into a new
    file, which makes it look "new" to the diff-scoped hunk proxy
    (`_new_callable_records`) even though its reachability is unchanged.
    `_merge_base_body_match` asks whether a same-named symbol with the
    SAME body/sig digest already existed anywhere in the tree at the
    diff's merge-base -- if so, this is a move, not an introduction, and
    WIRE001 must stay silent about it (case 2/3, a genuinely NEW symbol
    with no prior existence anywhere, still fires exactly as before)."""
    violations: list[Violation] = []
    for record in _new_callable_records(root, snapshot, hunks_by_file):
        def_lines = frozenset(range(record.span[0], record.span[1] + 1))
        if _is_reached_outside_diff_tests(root, snapshot, record, def_lines):
            continue
        target_digest = record.digests.body or record.digests.sig
        short = _short_name(record.id.qualname)
        if _merge_base_body_match(root, diff.base, short, target_digest):
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


# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to \
# Path.read_text/re.search/dict.items iteration, plain pathlib/re/dict operations the \
# resolver cannot statically bound; the one real raise path (config_external.py \
# missing/unreadable) is caught above"
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


def _touched_callable_records(
    root: Path,
    snapshot: GraphSnapshot,
    hunks_by_file: dict[str, list[tuple[int, int]]],
) -> list:
    """Every function/method this diff TOUCHES (a hunk overlaps its span)
    but did NOT wholly define (that is `_new_callable_records`'s own
    proxy) -- the search space for WIRE001 case 4 (T-1430): a diff that
    adds a new keyword-only PARAMETER to an EXISTING function's signature,
    where the function itself already has callers so case 1's "no
    non-test caller" check never fires, but the new parameter specifically
    is never passed anywhere."""
    new_ids = {
        record.id for record in _new_callable_records(root, snapshot, hunks_by_file)
    }
    found = []
    for record in snapshot.symbols.values():
        if record.kind not in _CALLABLE_KINDS or not record.id.path.endswith(".py"):
            continue
        if record.kind is SymbolKind.CLASS:
            continue
        qualname = record.id.qualname
        if _is_dunder(qualname) or _is_test_symbol(qualname):
            continue
        if record.id in new_ids:
            continue
        spans = hunks_by_file.get(record.id.path, ())
        overlaps = any(
            not (h[1] < record.span[0] or h[0] > record.span[1]) for h in spans
        )
        if overlaps:
            found.append(record)
    return found


# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to ast.walk/ \
# ast.FunctionDef attribute access, stdlib ast calls the resolver cannot statically \
# bound; the one real raise path (ast.parse on malformed source) is caught below"
def _kwonly_param_names(source: str, short_name: str) -> frozenset[str] | None:
    """Keyword-only parameter names of the first `def`/`async def` named
    `short_name` in `source`, via the stdlib `ast` module (simpler and
    more precise for this one question than re-deriving parameter
    boundaries from `frob.lang`'s flat token streams). `None` if `source`
    does not parse or defines no such function -- the caller treats that
    as "no baseline to compare against", never a violation (this gate's
    standing bias: a false "no new parameter" costs nothing, a false
    positive wrongly blocks a build)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == short_name
        ):
            return frozenset(arg.arg for arg in node.args.kwonlyargs)
    return None


_KEYWORD_ARG_RE_CACHE: dict[str, re.Pattern[str]] = {}


def _keyword_arg_pattern(name: str) -> re.Pattern[str]:
    """`name=` as a call-site keyword argument (or a default in a
    DIFFERENT function's signature -- accepted false-negative-shaped
    noise per this gate's broad-recall bias), never `==`/`!=`/`<=`/`>=`.
    Cached per name: the case-4 loop below re-checks the same handful of
    parameter names across every file in the tree."""
    cached = _KEYWORD_ARG_RE_CACHE.get(name)
    if cached is None:
        cached = re.compile(rf"(?<![=!<>]){re.escape(name)}\s*=(?!=)")
        _KEYWORD_ARG_RE_CACHE[name] = cached
    return cached


# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to _keyword_arg_pattern \
# (a module-local cached-regex helper the resolver cannot see through) and \
# Path.read_text/str.splitlines; the one real raise path (a deleted/ unreadable file) \
# is caught below"
# frob:waive EXHAUST002 reason="T-1371: same resolver artifact as EXHAUST003 above -- \
# _keyword_arg_pattern's own dict.get lookup on the module-level cache is never a bare \
# subscript; no KeyError-raising call is reachable from this function's own source"
def _keyword_passed_outside_def(
    root: Path, snapshot: GraphSnapshot, record, def_lines: frozenset[int], name: str
) -> bool:
    """True if `name=` appears, keyword-argument-shaped, anywhere in the
    tree OUTSIDE `record`'s own definition lines (which would otherwise
    self-match the new parameter's own `def foo(*, name=...)` clause).
    Mirrors `_is_reached_outside_diff_tests`'s whole-tree text-scan shape
    and bias (broader recall over precision -- an unrelated same-named
    keyword elsewhere in the tree counts as "passed", which is the safe
    direction for a gate that must not over-fire)."""
    pattern = _keyword_arg_pattern(name)
    for path in snapshot.file_hashes:
        if not path.endswith(".py"):
            continue
        try:
            lines = (root / path).read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        own_def_lines = def_lines if path == record.id.path else frozenset()
        for lineno, text in enumerate(lines, 1):
            if lineno in own_def_lines:
                continue
            if pattern.search(text):
                return True
    return False


# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to \
# _touched_callable_records/_kwonly_param_names/_keyword_passed_outside_def, \
# module-local helpers the resolver cannot see through, and run_argv, a cross-module \
# Result-returning wrapper it likewise cannot see through; the one real raise path \
# (Path.read_text on a deleted/unreadable file) is caught above"
# frob:waive EXHAUST002 reason="T-1371: same resolver artifact as EXHAUST003 above -- \
# every operation below is a frozenset/set difference or plain iteration, not a bare \
# subscript that can raise KeyError; a false positive from the gate's syntactic scan"
def _wire001_new_kwonly_param_violations(
    root: Path,
    diff: Diff,
    snapshot: GraphSnapshot,
    hunks_by_file: dict[str, list[tuple[int, int]]],
) -> list[Violation]:
    """WIRE001 case 4 (T-1430): a diff adds a new keyword-only parameter to
    an EXISTING function/method's signature that no call site anywhere in
    the tree passes -- the shape case 1 cannot see (the function itself
    already has a caller, so "no non-test caller" never fires) and that
    T-1384/T-1399/T-1391 each shipped for real. Compares the function's
    keyword-only parameter set at the diff's merge-base (`diff.base`) --
    read via `git show`, same mechanism as `_merge_base_body_match`'s
    relocation check (T-1431) -- against its CURRENT set; any name present
    now but absent at the base is a candidate, and fires only if
    `_keyword_passed_outside_def` finds no call site passing it."""
    violations: list[Violation] = []
    for record in _touched_callable_records(root, snapshot, hunks_by_file):
        short = _short_name(record.id.qualname)
        try:
            current_source = (root / record.id.path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        current_kwonly = _kwonly_param_names(current_source, short)
        if not current_kwonly:
            continue
        show = run_argv(
            ("git", "-C", str(root), "show", f"{diff.base}:{record.id.path}")
        )
        if show.is_err or show.danger_ok.returncode != 0:
            continue
        base_kwonly = _kwonly_param_names(show.danger_ok.stdout, short)
        if base_kwonly is None:
            continue
        new_names = current_kwonly - base_kwonly
        if not new_names:
            continue
        def_lines = frozenset(range(record.span[0], record.span[1] + 1))
        for name in new_names:
            if _keyword_passed_outside_def(root, snapshot, record, def_lines, name):
                continue
            violations.append(
                Violation(
                    rule="WIRE001",
                    severity=Severity.ERROR,
                    file=record.id.path,
                    line=record.span[0],
                    symref=record.symref,
                    message=(
                        f"WIRE001: {record.symref} adds keyword-only parameter "
                        f"{name!r}, which no call site outside its own tests "
                        "passes -- wire it, delete it, or "
                        'frob:waive WIRE001 reason="..." follow_up="T-####" '
                        "naming the open ticket that will wire it"
                    ),
                )
            )
    # One deterministic sort AFTER the loop (PERF004: never sort per
    # iteration) -- set iteration order above is arbitrary, output must
    # not be.
    violations.sort(key=lambda v: (v.file, v.line, v.message))
    return violations


def _wire002_is_permanent_test_helper_waiver(edge: Edge) -> bool:
    """True when a `frob:waive WIRE001` legitimately has no follow-up ticket
    to name: `permanent="true"` on a private symbol (leaf name starting
    with `_`) whose enclosing file lives under `tests/`. Restricted to the
    test tree so production code cannot use this to dodge real wiring --
    a private test-seed helper called only by its own file's test methods
    has no production caller BY DESIGN, not "not yet" (T-1592's live
    instance: `tests/unit/test_mutation_sweep_queue.py::_make_ticket`,
    which kept re-orphaning WIRE002 every time its placeholder follow_up
    ticket closed, because the condition it waives is permanent, not
    pending)."""
    if edge.attrs.get("permanent") != "true":
        return False
    file_part = edge.src.partition("::")[0]
    if not file_part.startswith("tests/"):
        return False
    leaf = edge.src.rsplit(".", 1)[-1].rsplit("::", 1)[-1]
    return leaf.startswith("_")


def _wire002_violations(snapshot: GraphSnapshot, queue: TicketQueue) -> list[Violation]:
    """WIRE002: a `frob:waive WIRE001` present without a `follow_up="T-####"`
    attribute naming a real, still-open ticket -- the escape hatch this
    ticket's brief demands ("require naming WHO is expected to call it and
    BY WHEN") turned into a checkable fact rather than free-text prose. A
    missing `follow_up=`, an id that resolves to no ticket, or a ticket
    already `done`/`dropped` all count -- an obligation that names nobody
    accountable is not an obligation. EXCEPT (T-1592) a waiver that instead
    declares `permanent="true"` on a private test-tree helper: such a
    waiver has no real follow-up work to point at (the no-caller condition
    is the intended, permanent design, not a pending TODO), so requiring
    one just forces a placeholder ticket id that turns into a fresh
    WIRE002 orphan the moment that placeholder closes."""
    from frob.gates import _OPEN_STATES, _edges_of_kind, _site_from_edge_origin

    violations: list[Violation] = []
    for edge in _edges_of_kind(snapshot, EdgeKind.WAIVE):
        if edge.target != "WIRE001":
            continue
        if _wire002_is_permanent_test_helper_waiver(edge):
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
# frob:tests tests/test_gates.py::TestWireGate.test_relocated_symbol_via_file_split_is_not_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestWireGate.test_genuinely_new_symbol_in_a_split_sibling_file_is_still_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestWireGate.test_new_kwonly_param_never_passed_is_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestWireGate.test_new_kwonly_param_passed_at_call_site_is_not_flagged  # noqa: E501
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
        *_wire001_unwired_symbol_violations(root, snapshot, hunks_by_file, diff),
        *_wire001_rule_id_violations(added_lines),
        *_wire001_cli_dest_violations(root, added_lines),
        *_wire001_new_kwonly_param_violations(root, diff, snapshot, hunks_by_file),
        *_wire002_violations(snapshot, queue),
    ]
    _log.info("wire_gate: %d violation(s)", len(violations))
    return tuple(violations)
