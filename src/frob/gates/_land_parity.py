"""frob.gates._land_parity -- LANDPARITY001/LANDPARITY002 (T-3456/T-3467).

T-3302's investigation (F-032/F-051) found three land-only checks with no
`frob.gates` rule behind them at all: the T-2114 new-public-symbol doc/
test-edge check, the diff-scoped ARCH001 (new-or-worsened long function)
check, and CrossTicketLeakage. Each is an ad-hoc CLI-side assertion in
`frob.app.ticket_runner._land_cmd`/`frob.tickets._land` that logs and
calls `sys.exit(1)` -- never a `Violation`-producing gate function
`run_gates` dispatches -- so `frob check --ticket <id>`/`frob ticket
close` structurally cannot see any of the three: there is no rule for
either command's gate loop to run. A ticket could pass `frob check`
clean and still get refused at land time for a finding it had no way to
see coming.

THIS MODULE covers the first two (LANDPARITY001 for T-2114,
LANDPARITY002 for the diff-scoped ARCH001 variant) -- both are pure
functions of `(worktree, merge_base, touched_paths)` with no worktree-
vs-main comparison beyond an ordinary `working_diff`, so wiring them into
`frob check` needs nothing `frob check` cannot already provide.
CrossTicketLeakage is NOT here: `frob.tickets._land._check_cross_ticket_
leakage` needs `worktree`/`base_ref` context specifically about the LAND
being performed (which other ticket's lease overlaps THIS one's touched
files), not a property of `root`'s tree alone the way every other
`frob.gates` rule is -- exposing it needs `frob check` to thread
worktree-vs-main comparison context through generically, which it does
not do today (T-3466).

T-3467: THIS MODULE now OWNS the pure detection logic
(`_new_public_symbols_missing_doc_or_test_edge`/`_new_or_worsened_long_
functions_in_diff` and their shared helpers `_is_generated_or_test_path`/
`_public_top_level_defs`/`_frob_directive_block`/`_DOC_TEST_EDGE_
FAMILIES`) -- moved here for real from `frob.app.ticket_runner._land_cmd`
now that `_land_cmd.py`'s exclusive scope lease (held by T-2642 for
T-3456's entire session) is free. `_land_cmd.py`'s own `_assert_new_
public_symbols_have_doc_and_test_edge_pre_land`/`_assert_diff_does_not_
worsen_long_functions_pre_land` now IMPORT these from here (the direction
the T-3456 docstring always pointed at) instead of defining them --
unchanged sys.exit(1) call-site behavior, one shared implementation. This
also fixes the layering direction `[arch.layering]` (frob.toml) declares
but does not yet enforce (T-0620): `frob.gates` no longer imports
`frob.app.ticket_runner` in either direction, deferred or not.
"""

# frob:ticket T-3456
# frob:ticket T-3467

from __future__ import annotations

import ast
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gitio import run_argv, working_diff
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:ticket T-2114
def _is_generated_or_test_path(worktree: Path, rel_path: str) -> bool:
    """`True` if `rel_path` is test code (doc/test-edge obligations do not
    apply -- mirrors `frob.gates.__init__._is_test_path`'s own convention,
    reimplemented here rather than imported cross-module since it is a
    3-line check) or carries a recognized generated-file marker
    (`frob.graph._generated.is_generated_source`, T-0234 -- nobody hand-
    documents machine-generated code)."""
    from pathlib import PurePosixPath

    parts = PurePosixPath(rel_path).parts
    name = PurePosixPath(rel_path).name
    if "tests" in parts or name.startswith("test_") or name.endswith("_test.py"):
        return True
    from frob.graph._generated import is_generated_source

    return is_generated_source(worktree, rel_path)


# frob:ticket T-2114
# frob:ticket T-2609
def _public_top_level_defs(source: str) -> dict[str, int]:
    """Name -> 1-indexed directive-search line number for every PUBLIC
    (does not start with `_`) top-level `def`/`async def`/`class` in
    `source`, or `{}` if `source` does not parse as Python at all (a
    syntax error is someone else's problem to catch -- this check
    degrades to a no-op, never a crash, matching every other touched-set
    guard's fail-open posture in this module).

    T-2609: for a DECORATED def/class, the line returned is the FIRST
    decorator's own `lineno`, not `node.lineno` (which `ast` always sets
    to the `def`/`class` keyword's own line, one or more lines BELOW the
    decorator(s)) -- `_frob_directive_block` walks upward from this line
    looking for a contiguous comment run, and for a decorated symbol the
    line directly above `def`/`class` is the decorator itself, not a
    comment, so the walk always stopped immediately regardless of what
    directives sat above the decorator. This mirrors `frob.lang`'s own
    `_walk_python._effective_node`, which peels a tree-sitter
    `decorated_definition` node the identical way for the identical
    reason (directive-to-symbol binding must start at the decorator, not
    the keyword) -- same fix shape, ported to this module's separate
    `ast`-based text scan rather than sharing `frob.lang`'s tree-sitter
    substrate.

    Deliberately TOP-LEVEL ONLY, not a full symbol walk: a small, cheap,
    diff-scoped check (T-2114 generalizes T-1907's touched-file shape, not
    the full repo-wide `coverage_gate`/`GraphSnapshot` COV001/TEST001
    machinery, which the deferred rapid sweep still runs and which this is
    not meant to replace) -- nested/private helpers are exactly the shape
    the deferred sweep is still relied on to eventually catch."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    defs: dict[str, int] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            if not node.name.startswith("_"):
                lineno = node.lineno
                if node.decorator_list:
                    lineno = node.decorator_list[0].lineno
                defs[node.name] = lineno
    return defs


# frob:ticket T-2114
# frob:ticket T-2201
def _frob_directive_block(
    lines: list[str],
    def_lineno: int,
    genuine_comment_lines: frozenset[int] | None = None,
) -> list[str]:
    """Every contiguous `#`-prefixed line immediately above `lines[def_
    lineno - 1]` (1-indexed, matching `ast`'s own `lineno` convention),
    stopping at the first blank or non-comment line -- the exact
    convention `frob:doc`/`frob:tests`/`frob:ticket`/`frob:waive`
    directives already use throughout this codebase (directly above the
    `def`/`class` line, no intervening blank line, per `frob fmt`'s own
    canonicalization). Empty if `def_lineno` is out of range or nothing
    precedes it.

    T-2201: a line that merely LOOKS like a comment (`.strip().startswith
    ("#")`) is not necessarily one -- a multi-line string literal (a
    docstring belonging to an earlier statement, or any other triple-
    quoted string) can contain a line that starts with `#` in its own
    right, and that line sits at a real 1-based line number identical to
    a genuine comment's. When `genuine_comment_lines` is given (1-based
    line numbers `frob.tickets._land._genuine_comment_lines` places
    inside a real grammar COMMENT node, the same T-2183 machinery
    `_directive_ticket_ids_in_diff` already uses for the identical
    question), the walk stops the instant it reaches a `#`-looking line
    that is NOT in that set -- exactly like reaching a blank/non-comment
    line, since a directive block is grammar-comment lines only. `None`
    (the default) preserves the old text-only behavior for callers that
    have not resolved a comment-line set."""
    if def_lineno < 2 or def_lineno > len(lines) + 1:
        return []
    block: list[str] = []
    idx = def_lineno - 2  # 0-indexed line immediately above the def
    while idx >= 0 and lines[idx].strip().startswith("#"):
        if genuine_comment_lines is not None and (idx + 1) not in genuine_comment_lines:
            break
        block.append(lines[idx])
        idx -= 1
    return block


# frob:ticket T-2114
# frob:ticket T-2201
#: T-2201: the doc/test-edge families this gate demands, as a data table
#: instead of a hand-written boolean pair per family -- T-1907 gated the
#: `ty` family on its own bespoke path, T-2114 then hardcoded a SECOND,
#: near-identical `has_doc`/`has_tests` pair for COV001/TEST001, and the
#: ticket that added this table exists specifically so a THIRD family
#: (any future `frob:waive RULE-ID`-shaped edge this same diff-scoped
#: gate should demand) is a one-line append here, not a third copy of
#: the same two-line pattern. `label` is the human-readable family name
#: used in the refusal message; `directive` is the `frob:` directive
#: prefix that alone satisfies the family; `waive_rule` is the
#: `frob:waive <RULE-ID>` id that also satisfies it.
_DOC_TEST_EDGE_FAMILIES: tuple[tuple[str, str, str], ...] = (
    ("frob:doc", "frob:doc", "COV001"),
    ("frob:tests", "frob:tests", "TEST001"),
)


# frob:ticket T-2322
def _new_public_symbols_in_file_missing_doc_or_test_edge(
    worktree: Path, merge_base: str, rel_path: str
) -> list[tuple[str, str, int, list[str]]]:
    """Per-file body of `_new_public_symbols_missing_doc_or_test_edge`
    (T-2322 ARCH001 split, zero behavior change): every (file, name,
    lineno, missing_families) finding for ONE already-filtered `.py`
    `rel_path` -- reads `rel_path`'s current content plus its content at
    `merge_base`, diffs the public top-level def names, and checks each
    NEW one's preceding comment block for the doc/test-edge directive
    pair. Returns `[]` (never an error) for a file that no longer exists,
    fails to read, or introduces no new public symbols."""
    from frob.tickets._land import _genuine_comment_lines

    full = worktree / rel_path
    if not full.is_file():
        return []
    try:
        source = full.read_text(encoding="utf-8")
    except OSError:
        return []
    new_defs = _public_top_level_defs(source)
    if not new_defs:
        return []
    old = run_argv(["git", "-C", str(worktree), "show", f"{merge_base}:{rel_path}"])
    old_names: set[str] = set()
    if old.is_ok and old.danger_ok.returncode == 0:
        old_names = set(_public_top_level_defs(old.danger_ok.stdout))
    lines = source.splitlines()
    genuine_lines = _genuine_comment_lines(worktree, None, rel_path)
    findings: list[tuple[str, str, int, list[str]]] = []
    # frob:waive PERF004 reason="new_defs is recomputed fresh from THIS file's own \
    # source a few lines above (_public_top_level_defs(source)) on every call to this \
    # function, one call per touched file -- there is no shared/invariant collection \
    # to hoist the sort of; each call genuinely sorts different data (T-2321, T-2322)"
    for name, lineno in sorted(new_defs.items(), key=lambda kv: kv[1]):
        if name in old_names:
            continue
        block = _frob_directive_block(lines, lineno, genuine_lines)
        block_text = "\n".join(block)
        missing = [
            label
            for label, directive, waive_rule in _DOC_TEST_EDGE_FAMILIES
            if directive not in block_text
            and f"frob:waive {waive_rule}" not in block_text
        ]
        if missing:
            findings.append((rel_path, name, lineno, missing))
    return findings


def _new_public_symbols_missing_doc_or_test_edge(
    worktree: Path, merge_base: str, touched_paths: frozenset[str]
) -> list[tuple[str, str, int, list[str]]]:
    """Every (file, name, lineno, missing_families) for a PUBLIC top-level
    symbol that is NEW in this diff (absent by name from the SAME file at
    `merge_base` -- a name-based diff, not a hunk-span one, so it is exact
    regardless of how git chose to break the hunks up) and whose
    immediately-preceding comment block (`_frob_directive_block`) is
    missing one or more of `_DOC_TEST_EDGE_FAMILIES`'s directive/waive
    pair -- `missing_families` names each missing family's `label`, in
    `_DOC_TEST_EDGE_FAMILIES` order.

    This is the diff-derived, bounded check T-2114 asks for: two small
    `ast.parse` calls per touched `.py` file (current worktree content,
    and the SAME file's content at `merge_base` via `git show`), never a
    full-repo `GraphSnapshot`/`coverage_gate` build -- the ~208s cost
    T-1684 deliberately took off the land critical path stays off it.

    T-2201: the candidate block's lines are further filtered to only
    those `frob.tickets._land._genuine_comment_lines` places inside a
    real grammar COMMENT node of the CURRENT worktree file -- a `frob:`-
    looking line inside a docstring/string literal that merely happens to
    start with `#` and sit directly above the def no longer satisfies
    this gate (the exact substring-matching gap T-2183 already fixed for
    the passenger-ticket check; this reuses the same machinery rather
    than inventing a second answer to "is this line a genuine
    directive?")."""
    findings: list[tuple[str, str, int, list[str]]] = []
    for rel_path in sorted(touched_paths):
        if not rel_path.endswith(".py"):
            continue
        if _is_generated_or_test_path(worktree, rel_path):
            continue
        findings.extend(
            _new_public_symbols_in_file_missing_doc_or_test_edge(
                worktree, merge_base, rel_path
            )
        )
    return findings


# frob:ticket T-2214
def _long_function_symrefs_over_threshold(
    path: Path, rel: str
) -> dict[str, tuple[int, int]]:
    """`{symref: (line, n_lines)}` for every python function in the file at
    `path` that `frob.arch`'s own long-function check (ARCH001) would flag
    RIGHT NOW -- long AND structurally complex, at this repo's own
    `[arch].max_function_lines` threshold (`frob.repo_meta.
    load_arch_config`, the same knob `arch_gate` itself reads, T-0373).
    `{}` for a non-python file, an unparseable one, or one with no
    over-threshold function -- never a crash (matches every other diff-
    scoped land-time check's fail-open posture in this module).

    Reuses `frob.arch._python._check_long_functions` (the SAME complexity-
    aware detector `arch_gate` dispatches, not a reimplementation) against
    a single file's own parse tree -- no repo-wide `analyze_project` walk,
    keeping this the same "two small parses per touched file" cost T-2114's
    doc/test-edge check already pays, not the ~208s T-1684 took off the
    land critical path."""
    from frob.arch import _python as arch_python
    from frob.lang import raw_tree
    from frob.repo_meta import load_arch_config

    parsed = raw_tree(path)
    if parsed.is_err:
        return {}
    tree, _source, language = parsed.danger_ok
    if language != "python":
        return {}
    limits = load_arch_config(path.parent)
    suggestions: list = []
    arch_python._check_long_functions(
        tree, rel, limits["max_function_lines"], suggestions
    )
    return {s.symref: (s.line or 0, s.metric or 0) for s in suggestions if s.symref}


# frob:ticket T-2214
# frob:ticket T-2322
def _long_function_symrefs_over_threshold_in_content(
    content: str, rel_path: str
) -> set[str]:
    """Writes `content` to a scratch `.py` file and returns the symrefs
    `_long_function_symrefs_over_threshold` would flag for it (T-2322
    ARCH103 split of `_long_function_symrefs_over_threshold_at_merge_
    base`, zero behavior change) -- isolates the tempfile-write/parse/
    cleanup mechanics from the git-show call that produces `content`."""
    import tempfile

    with tempfile.NamedTemporaryFile(
        suffix=".py", mode="w", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        return set(_long_function_symrefs_over_threshold(tmp_path, rel_path))
    finally:
        tmp_path.unlink(missing_ok=True)


def _long_function_symrefs_over_threshold_at_merge_base(
    worktree: Path, merge_base: str, rel_path: str
) -> set[str]:
    """Symrefs `_long_function_symrefs_over_threshold` would flag for
    `rel_path` AS IT EXISTED at `merge_base` -- `git show`n to a scratch
    `.py` file so `raw_tree` can parse it identically to the current
    worktree content (T-2214, ARCH001 split of `_new_or_worsened_long_
    functions_in_diff`). Empty on a `git show` failure (file did not
    exist at `merge_base` -- everything in it is new by construction)."""
    old = run_argv(["git", "-C", str(worktree), "show", f"{merge_base}:{rel_path}"])
    if not (old.is_ok and old.danger_ok.returncode == 0):
        return set()
    return _long_function_symrefs_over_threshold_in_content(
        old.danger_ok.stdout, rel_path
    )


def _new_or_worsened_long_functions_in_file(
    worktree: Path, merge_base: str, rel_path: str
) -> list[tuple[str, str, int, int]]:
    """`_new_or_worsened_long_functions_in_diff`'s own per-file body
    (T-2214, ARCH001 split): every `(rel_path, symref, line, n_lines)`
    this ONE file's diff pushes past ARCH001's long-AND-complex threshold
    that was not already past it at `merge_base`, skipping any symref
    carrying `frob:waive ARCH001` directly above its `def` in the CURRENT
    file -- the same reasoned-waiver escape hatch `arch_gate`/`frob.
    gates._match_waiver` already honor for this exact rule, not a second,
    weaker one invented here."""
    from frob.tickets._land import _genuine_comment_lines

    full = worktree / rel_path
    current = _long_function_symrefs_over_threshold(full, rel_path)
    if not current:
        return []
    old_over = _long_function_symrefs_over_threshold_at_merge_base(
        worktree, merge_base, rel_path
    )
    lines = full.read_text(encoding="utf-8").splitlines()
    genuine_lines = _genuine_comment_lines(worktree, None, rel_path)
    findings: list[tuple[str, str, int, int]] = []
    for symref, (line, n_lines) in sorted(current.items(), key=lambda kv: kv[1][0]):
        if symref in old_over:
            continue
        block_text = "\n".join(_frob_directive_block(lines, line, genuine_lines))
        if "frob:waive ARCH001" in block_text:
            continue
        findings.append((rel_path, symref, line, n_lines))
    return findings


def _new_or_worsened_long_functions_in_diff(
    worktree: Path, merge_base: str, touched_paths: frozenset[str]
) -> list[tuple[str, str, int, int]]:
    """Every `(rel_path, symref, line, n_lines)` for a function this diff
    ADDS or MODIFIES that crosses ARCH001's long-AND-complex threshold in
    the CURRENT worktree content but did NOT already cross it in the SAME
    file's content at `merge_base` -- the diff-scoped, attributable-only
    ARCH001 check T-2214 asks for, mirroring T-2114's `_new_public_
    symbols_missing_doc_or_test_edge` shape exactly: two small parses per
    touched file (current worktree, and `git show <merge_base>:<path>`
    written to a scratch file so `raw_tree` can parse it the same way),
    never a full-repo `analyze_project`/`GraphSnapshot` build.

    T-2214's own acceptance criteria: a function ALREADY over threshold
    before this diff and merely touched must NOT be blamed on this land
    (the global-vs-attributable distinction T-2198 already fixed for the
    TICK gate) -- `_new_or_worsened_long_functions_in_file`'s `symref in
    old_over` check is exactly that, keyed by symref so a function that
    moves within the file (line changes, symref does not) is still
    correctly recognized as pre-existing debt, not a new finding."""
    findings: list[tuple[str, str, int, int]] = []
    for rel_path in sorted(touched_paths):
        if not rel_path.endswith(".py"):
            continue
        if not (worktree / rel_path).is_file():
            continue
        if _is_generated_or_test_path(worktree, rel_path):
            continue
        findings.extend(
            _new_or_worsened_long_functions_in_file(worktree, merge_base, rel_path)
        )
    return findings


def _land_parity_diff(root: Path) -> tuple[str, frozenset[str]] | None:
    """`(merge_base, touched_paths)` from `working_diff(root, "main")` --
    the SAME diff source `frob.app.ticket_runner._land_cmd.
    _land_touched_paths` uses at land time (T-1404), computed ONCE per
    gate call so a `frob check` run in a ticket's own worktree sees the
    identical touched-file set the eventual land will diff against.
    `None` when the diff cannot be computed (no merge-base, detached
    HEAD, a `git` spawn failure) -- both gate functions below degrade to
    `()` (no finding) rather than guess at a touched set they cannot
    verify, matching every diff-scoped land-time check's own fail-open
    posture."""
    diff_result = working_diff(root, "main")
    if diff_result.is_err:
        _log.debug(
            "land_parity: could not compute the working diff (%s) -- "
            "skipping (unmeasured, not zero)",
            diff_result.danger_err,
        )
        return None
    touched = frozenset(hunk.file for hunk in diff_result.danger_ok.hunks)
    if not touched:
        return None
    return diff_result.danger_ok.base, touched


# frob:ticket T-3456
# frob:doc docs/modules/gates.md#land-parity-landparity001landparity002-t-3456
# frob:enforces CHK-GATE-LANDPARITY001
# frob:tests tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate.test_new_public_symbol_missing_both_directives_fires  # noqa: E501
# frob:tests tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate.test_new_public_symbol_with_both_directives_is_quiet  # noqa: E501
# frob:tests tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate.test_no_diff_is_quiet  # noqa: E501
def land_parity_doc_test_gate(root: Path) -> tuple[Violation, ...]:
    """LANDPARITY001 (T-3456): `frob check`-callable wrapper around
    `_new_public_symbols_missing_doc_or_test_edge` (T-2114, moved into
    this module for real by T-3467) -- a new public top-level symbol in
    this diff with no `frob:doc`/`frob:tests` directive (or matching
    `frob:waive`) directly above it. `()` when the touched-file set
    cannot be computed (`_land_parity_diff` returned `None`) or is
    empty."""
    diff = _land_parity_diff(root)
    if diff is None:
        return ()
    merge_base, touched_paths = diff

    findings = _new_public_symbols_missing_doc_or_test_edge(
        root, merge_base, touched_paths
    )
    violations: list[Violation] = []
    for rel_path, name, lineno, missing_families in findings:
        missing = ", ".join(missing_families)
        violations.append(
            Violation(
                rule="LANDPARITY001",
                severity=Severity.ERROR,
                file=rel_path,
                line=lineno,
                message=(
                    f"LANDPARITY001: {rel_path}:{lineno} new public symbol "
                    f"{name!r} has no {missing} directive above it (T-2114) "
                    f"-- add the missing directive(s), or a matching "
                    f"`frob:waive` if intentionally undocumented/untested"
                ),
            )
        )
    return tuple(violations)


# frob:ticket T-3456
# frob:doc docs/modules/gates.md#land-parity-landparity001landparity002-t-3456
# frob:enforces CHK-GATE-LANDPARITY002
# frob:tests tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate.test_new_over_threshold_function_fires  # noqa: E501
# frob:tests tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate.test_pre_existing_over_threshold_function_merely_touched_is_quiet  # noqa: E501
# frob:tests tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate.test_no_diff_is_quiet  # noqa: E501
def land_parity_long_function_gate(root: Path) -> tuple[Violation, ...]:
    """LANDPARITY002 (T-3456): `frob check`-callable wrapper around
    `_new_or_worsened_long_functions_in_diff` (T-2214, moved into this
    module for real by T-3467) -- a function this diff adds or modifies
    that crosses ARCH001's long-AND-complex threshold in the current
    worktree content but was NOT already over it at `merge_base` (a
    function already over threshold before this diff and merely touched
    is NOT blamed on this ticket, T-2214's own acceptance criterion). A
    distinct rule id from plain `ARCH001` deliberately (not a re-fire of
    that repo-wide rule): `ARCH001` reports EVERY over-threshold function
    found by an unscoped walk, new or pre-existing; `LANDPARITY002`
    reports only what THIS diff newly pushed over the line, the narrower,
    attributable-only claim T-2214 actually makes -- collapsing the two
    into one rule id would either double-report a pre-existing ARCH001
    finding under a second name, or silently narrow what plain ARCH001
    already covers."""
    diff = _land_parity_diff(root)
    if diff is None:
        return ()
    merge_base, touched_paths = diff

    findings = _new_or_worsened_long_functions_in_diff(root, merge_base, touched_paths)
    violations: list[Violation] = []
    for rel_path, symref, lineno, n_lines in findings:
        violations.append(
            Violation(
                rule="LANDPARITY002",
                severity=Severity.ERROR,
                file=rel_path,
                line=lineno,
                message=(
                    f"LANDPARITY002: {rel_path}:{lineno} {symref} is now "
                    f"{n_lines} line(s), past ARCH001's long-AND-complex "
                    f"threshold, and was NOT already over it before this "
                    f"diff (T-2214) -- split the function, or add "
                    f'`frob:waive ARCH001 reason="..."` above the def if it '
                    f"genuinely does not need to shrink"
                ),
            )
        )
    return tuple(violations)


__all__ = ["land_parity_doc_test_gate", "land_parity_long_function_gate"]
