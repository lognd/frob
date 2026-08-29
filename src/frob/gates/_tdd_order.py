"""TDD001 (T-3009, T-3004 section 7): a verifying test's introducing
commit must PRECEDE the artifact/implementation it verifies, checked from
git history.

GENERALISES, does not reinvent: `frob.gates._bug_repro`'s BUG002 already
proves this exact discipline for one special case (a bug ticket's
designated repro test must FAIL AT THE PARENT COMMIT -- proof the test
existed and genuinely failed before the fix). This module lifts the same
"a claim about git history is a checkable fact, not prose" posture from
one designated repro to every `frob:tests` edge (T-3004 section 1's
"generalise an existing one-level binding to N levels", applied to its
git-history half first). Reused directly: `frob.gitio.run_argv` for every
git spawn (same primitive `_bug_repro.py`'s own `_resolve_sha` uses), and
the `Severity.UNRESOLVED` doctrine (T-1664, already load-bearing across
the T-2390 config-schema gate family) for "this check could not determine
an answer" -- never a silently empty, falsely-clean violation list.

SYMBOL-LEVEL, NOT LEXICAL (design-audit finding, corrected before this
ticket's first land attempt): the standing "checks must parse and compare
SYMBOLS, never substring/regex" directive rules out `git log -S<name>`
pickaxe search here -- it fires inside comments/docstrings that merely
MENTION a name, and misses nothing about renames only by accident.
`resolve_symbol_introduction` instead walks the symbol's file's own
commit history OLDEST-FIRST, parsing each revision's content with the
stdlib `ast` module and checking REAL membership in that revision's
function/class qualname set (`_ast_qualnames`) -- the first commit where
the qualname is actually a defined symbol (not merely textually present)
is the introduction. Python-only for now (`ast.parse`); a non-Python
symref's `resolve_symbol_introduction` call degrades to `None`
(`Severity.UNRESOLVED`) rather than falling back to a lexical
approximation -- an honest "cannot resolve non-Python symbols yet" beats
a silent substring substitute.

WHERE THIS RUNS, AND WHY (the placement BUG002's own docs already settled
for the identical constraint, T-2019/T-2025): pre-land, against a
ticket's OWN worktree branch commit sequence -- never post-land against
main. `frob ticket land` squashes a ticket's commits into one, so a
`frob:tests` pair checked against `main` would see identical introducing
commits for nearly every binding -- running this only pre-land, while the
worktree branch's real commit-by-commit history still exists, is the one
placement that can actually see the ordering fact this rule is about.

SAME COMMIT IS A DETERMINATE VIOLATION, NOT AN UNKNOWN (design-audit
finding, corrected before this ticket's first land attempt): T-3004
section 7 requires the test's commit to PRECEDE the artifact's -- "the
test and the code were committed together" is a fact git ancestry proves
outright (the two shas are equal), not a case where ordering could not be
determined. Collapsing it into `Severity.UNRESOLVED` would make TDD001
structurally unable to ever fire against the one workflow shape (commit
everything at once) it exists to police, while still LOOKING like a
completed, passing check -- exactly the silent-zero shape T-1664's
doctrine exists to rule out. `classify_order` therefore reports
`TDDOrder.IMPLEMENTATION_FIRST` (fires) for the identical-commit case;
`TDDOrder.UNRESOLVED` is reserved for a GENUINELY indeterminate pair: an
unresolvable commit on either side, or two resolved commits whose
histories have diverged (neither a git ancestor of the other) -- ancestry
itself cannot order those, and committer timestamp is deliberately never
used as a tiebreak (trivially wrong under clock skew or a rebase)."""

from __future__ import annotations

import ast
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gitio import run_argv
from frob.graph._models import Edge, EdgeKind
from frob.logging import get_logger

_log = get_logger(__name__)

#: TDD001's own rule id -- named ONCE here so every emitter/message below
#: shares it rather than re-typing the literal.
# frob:doc docs/modules/gates.md#tdd001-t-3009
RULE_TDD001 = "TDD001"


# frob:doc docs/modules/gates.md#tdd001-t-3009
# frob:tests tests/gates/test_tdd_order.py::TestClassifyOrder.test_fires_when_implementation_precedes_test  # noqa: E501
# frob:tests tests/gates/test_tdd_order.py::TestClassifyOrder.test_stays_quiet_when_test_precedes_implementation  # noqa: E501
# frob:tests tests/gates/test_tdd_order.py::TestClassifyOrder.test_fires_when_commits_are_identical  # noqa: E501
class TDDOrder(StrEnum):
    """The three possible outcomes of comparing a `verifies`/`frob:tests`
    pair's two introducing commits -- three, not two, because "cannot
    tell" is a distinct outcome from "test-first" and "code-first", never
    collapsed into either (T-1664's `Severity.UNRESOLVED` doctrine)."""

    #: The test's introducing commit is a STRICT git ancestor of the
    #: artifact's -- test written first, then the code. Silent: this is
    #: T-3004 section 2's "structurally closed" bar, nothing about
    #: ceremony.
    TEST_FIRST = "test_first"
    #: The artifact's introducing commit is a git ancestor of (or IDENTICAL
    #: to) the test's -- code written first (or committed together with
    #: its test in one commit, a determinate non-test-first fact, not an
    #: unknown). The one TDDOrder outcome TDD001 actually fires on.
    IMPLEMENTATION_FIRST = "implementation_first"
    #: Either commit could not be resolved at all, or the two (distinct)
    #: commits' histories have diverged (neither is a git ancestor of the
    #: other) -- ordering genuinely cannot be determined. Never rendered
    #: as a pass.
    UNRESOLVED = "unresolved"


# frob:doc docs/modules/gates.md#tdd001-t-3009
# frob:tests tests/gates/test_tdd_order.py::TestSymrefHelpers.test_symref_path_splits_on_double_colon  # noqa: E501
def symref_path(symref: str) -> str:
    """The repo-relative path half of a `path::qualname` symref -- the
    half git operates on. A bare path (no `::`) is returned unchanged."""
    path, _, _ = symref.partition("::")
    return path


# frob:doc docs/modules/gates.md#tdd001-t-3009
# frob:tests tests/gates/test_tdd_order.py::TestSymrefHelpers.test_symref_qualname_keeps_the_full_dotted_path  # noqa: E501
def symref_qualname(symref: str) -> str | None:
    """The dotted qualname half of a `path::qualname` symref (`frob:
    tests`' own convention, e.g. `TestFoo.test_bar`, or a plain
    `v_pairing`), or `None` for a bare path -- `resolve_symbol_
    introduction` matches this against `_ast_qualnames`' REAL per-
    revision symbol set, never against raw text."""
    _, sep, qualname = symref.partition("::")
    if not sep:
        return None
    return qualname.replace("::", ".")


# frob:tests tests/gates/test_tdd_order.py::TestAstQualnames.test_collects_nested_dotted_qualnames  # noqa: E501
def _ast_qualnames(source: str) -> set[str]:
    """Every function/class qualname `source` actually DEFINES, dotted by
    enclosing class (`TestFoo.test_bar`) the same way `frob:tests`
    directives name a method -- built by walking the real `ast` parse
    tree, never by scanning text, so a qualname mentioned only in a
    comment, docstring, or string literal is never counted as defined.
    An unparseable buffer (a revision that is not valid Python, or is a
    non-Python file entirely) yields an empty set rather than raising --
    the caller treats that revision as not containing the symbol, same as
    a genuine absence."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return set()
    names: set[str] = set()

    def _walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qual = f"{prefix}{child.name}" if prefix else child.name
                names.add(qual)
                _walk(child, f"{qual}.")
            else:
                _walk(child, prefix)

    _walk(tree, "")
    return names


def _revisions_oldest_first(root: Path, path: str) -> list[str]:
    """Every commit sha touching `path`, OLDEST first -- the sequence
    `resolve_symbol_introduction` scans forward over looking for the
    qualname's first real appearance. `git log` itself lists newest-
    first, so this just reverses it."""
    spawned = run_argv(("git", "-C", str(root), "log", "--format=%H", "--", path))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return []
    shas = [ln.strip() for ln in spawned.danger_ok.stdout.splitlines() if ln.strip()]
    shas.reverse()
    return shas


# frob:waive DUP001 reason="structurally resembles frob.tickets._unlanded._blob_text \
# (both are a bare 'git show <ref>:<path>' read) but the two modules are different \
# strata components (frob.gates vs frob.tickets) -- importing across that boundary for \
# one one-line git spawn would introduce an undeclared cross-component Flow (the same \
# T-2429 lesson ARCHSCHEMA001's own docstring already cites), so this stays a small, \
# independently-evolving duplicate rather than a coupling"
def _show_file_at_revision(root: Path, rev: str, path: str) -> str | None:
    """`git show <rev>:<path>`'s content, or `None` if that path did not
    exist at `rev` (renamed away, not yet added, or any other spawn/exit
    failure) -- `_ast_qualnames` never sees a nonexistent-file sentinel
    mistaken for real (empty) source."""
    spawned = run_argv(("git", "-C", str(root), "show", f"{rev}:{path}"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    return spawned.danger_ok.stdout


# frob:doc docs/modules/gates.md#tdd001-t-3009
# frob:tests tests/gates/test_tdd_order.py::TestResolveSymbolIntroduction.test_resolves_the_commit_that_added_the_symbol  # noqa: E501
# frob:tests tests/gates/test_tdd_order.py::TestResolveSymbolIntroduction.test_returns_none_for_a_symbol_never_added  # noqa: E501
def resolve_symbol_introduction(root: Path, symref: str) -> str | None:
    """The sha of the commit that FIRST introduced `symref` (a
    `path::qualname` string, the same shape `frob:tests`/`frob:doc`
    directives already bind) in `root`'s git history, or `None` if it
    cannot be determined -- the caller degrades that to `Severity.
    UNRESOLVED`, never a guessed verdict.

    SYMBOL-LEVEL: scans `path`'s own commit history oldest-first and, for
    a dotted qualname, returns the first revision whose REAL `ast`-parsed
    function/class qualname set (`_ast_qualnames`) contains it -- never a
    text search. A bare path (no `::` in `symref`) instead returns that
    history's OLDEST commit directly (the file's own first-tracked
    revision) since there is no qualname to locate within it."""
    path = symref_path(symref)
    qualname = symref_qualname(symref)
    revisions = _revisions_oldest_first(root, path)
    if not revisions:
        _log.warning(
            "TDD001: could not resolve introducing commit for %s (no history for %s)",
            symref,
            path,
        )
        return None
    if qualname is None:
        return revisions[0]
    for rev in revisions:
        source = _show_file_at_revision(root, rev, path)
        if source is None:
            continue
        if qualname in _ast_qualnames(source):
            return rev
    _log.warning(
        "TDD001: %s never appears as a real ast-defined symbol in %s's history "
        "-- no introducing commit",
        symref,
        path,
    )
    return None


def _is_ancestor(root: Path, maybe_ancestor: str, maybe_descendant: str) -> bool:
    """`True` iff `maybe_ancestor` is a git ancestor of (or identical to)
    `maybe_descendant`, via `git merge-base --is-ancestor` -- a commit IS
    its own ancestor, which is deliberate here: the identical-commit case
    is meant to read as "artifact at or before test", the same-or-earlier
    half of `IMPLEMENTATION_FIRST`'s determinate-violation classification
    (see this module's own docstring)."""
    spawned = run_argv(
        (
            "git",
            "-C",
            str(root),
            "merge-base",
            "--is-ancestor",
            maybe_ancestor,
            maybe_descendant,
        )
    )
    if spawned.is_err:
        return False
    return spawned.danger_ok.returncode == 0


# frob:tests tests/gates/test_tdd_order.py::TestClassifyOrder.test_fires_when_implementation_precedes_test  # noqa: E501
# frob:tests tests/gates/test_tdd_order.py::TestClassifyOrder.test_stays_quiet_when_test_precedes_implementation  # noqa: E501
# frob:tests tests/gates/test_tdd_order.py::TestClassifyOrder.test_fires_when_commits_are_identical  # noqa: E501
# frob:tests tests/gates/test_tdd_order.py::TestClassifyOrder.test_reports_unresolved_when_either_commit_is_unresolvable  # noqa: E501
# frob:doc docs/modules/gates.md#tdd001-t-3009
# frob:tests tests/gates/test_tdd_order.py::TestClassifyOrder.test_reports_unresolved_on_diverged_history  # noqa: E501
def classify_order(
    root: Path, *, artifact_commit: str | None, test_commit: str | None
) -> TDDOrder:
    """Compare two introducing commits by git ANCESTRY (never by
    committer timestamp -- trivially wrong under clock skew or a rebase;
    ancestry is the fact git itself can prove) and classify the pair per
    `TDDOrder`'s three outcomes. `None` for either commit is `UNRESOLVED`
    immediately -- genuinely unresolvable, not a same-commit fact. The
    two commits being IDENTICAL is instead `IMPLEMENTATION_FIRST`: a
    determinate "not test-first" fact (this module's own docstring),
    never folded into UNRESOLVED."""
    if artifact_commit is None or test_commit is None:
        return TDDOrder.UNRESOLVED
    if artifact_commit == test_commit:
        return TDDOrder.IMPLEMENTATION_FIRST
    if _is_ancestor(root, test_commit, artifact_commit):
        return TDDOrder.TEST_FIRST
    if _is_ancestor(root, artifact_commit, test_commit):
        return TDDOrder.IMPLEMENTATION_FIRST
    return TDDOrder.UNRESOLVED


def _tdd001_message(artifact_symref: str, test_symref: str) -> str:
    """TDD001's fire message: names both symbols and the remedy (write
    the test, watch it fail, THEN implement -- T-3004 section 7's own
    framing) rather than only the bare rule id."""
    return (
        f"TDD001: {artifact_symref} was not committed strictly after its "
        f"verifying test {test_symref} -- either implementation-first, "
        f"or committed in the SAME commit as its test, neither of which is "
        f"test-first. Write the test before the implementation it "
        f"verifies (T-3004 section 7), or if this pair genuinely cannot "
        f"be reordered (a pre-existing symbol newly bound to a test), say "
        f'so via `frob:waive TDD001 reason="..."` on the ticket.'
    )


def _tdd001_unresolved_message(artifact_symref: str, test_symref: str) -> str:
    """TDD001's `Severity.UNRESOLVED` message -- names the pair and the
    reason ordering could not be determined, so this reads as "could not
    check", never as a silent pass."""
    return (
        f"TDD001: could not determine commit order for {artifact_symref} "
        f"/ {test_symref} -- one or both introducing commits are "
        f"unresolvable (no ast-defined revision found), or the two "
        f"commits' histories have diverged."
    )


# frob:doc docs/modules/gates.md#tdd001-t-3009
# frob:tests tests/gates/test_tdd_order.py::TestTddOrderViolations.test_fires_on_a_planted_implementation_first_pair  # noqa: E501
# frob:tests tests/gates/test_tdd_order.py::TestTddOrderViolations.test_fires_when_test_and_implementation_share_a_commit  # noqa: E501
# frob:tests tests/gates/test_tdd_order.py::TestTddOrderViolations.test_stays_quiet_on_a_genuine_test_first_pair  # noqa: E501
# frob:tests tests/gates/test_tdd_order.py::TestTddOrderViolations.test_reports_unresolved_rather_than_passing_on_an_unresolvable_pair  # noqa: E501
# frob:tests tests/gates/test_tdd_order.py::TestTddOrderViolations.test_ignores_non_tests_edges  # noqa: E501
# frob:waive WIRE001 reason="T-3009's own scope is the ordering check and its rule, \
# not the land-time call site -- mirrors bug_repro_violations, which is likewise \
# called from frob.tickets._land rather than from within this module; T-3057 wired the \
# call site (frob.tickets._land._check_tdd_order), closing the follow-up this waiver \
# used to point at" follow_up="T-3381"
# frob:enforces CHK-GATE-TDD001
def tdd_order_violations(root: Path, edges: Sequence[Edge]) -> list[Violation]:
    """TDD001's whole surface: every `EdgeKind.TESTS` edge (`src` = the
    artifact/implementation symbol the directive sits on, `target` = the
    test it names -- the existing one-level `frob:tests` binding T-3004
    section 1 identifies as the thing to generalise) is checked for
    commit order. Fires `Severity.ERROR` for a proven non-test-first pair
    (implementation-first OR same-commit, both determinate violations of
    "the test's commit must precede"), `Severity.UNRESOLVED` for a pair
    whose order genuinely cannot be determined, and emits nothing for a
    genuine test-first pair -- the three outcomes this rule's own docs
    (and T-3004 section 2's both-directions doctrine) require. MUST be
    called pre-land against a ticket's own worktree branch -- see this
    module's own docstring for why a post-land call against `main` cannot
    observe the fact this rule checks."""
    out: list[Violation] = []
    for edge in edges:
        if edge.kind is not EdgeKind.TESTS:
            continue
        artifact_symref = edge.src
        test_symref = edge.target
        artifact_commit = resolve_symbol_introduction(root, artifact_symref)
        test_commit = resolve_symbol_introduction(root, test_symref)
        order = classify_order(
            root, artifact_commit=artifact_commit, test_commit=test_commit
        )
        if order is TDDOrder.IMPLEMENTATION_FIRST:
            out.append(
                Violation(
                    rule=RULE_TDD001,
                    severity=Severity.ERROR,
                    file=symref_path(artifact_symref),
                    line=0,
                    message=_tdd001_message(artifact_symref, test_symref),
                )
            )
        elif order is TDDOrder.UNRESOLVED:
            out.append(
                Violation(
                    rule=RULE_TDD001,
                    severity=Severity.UNRESOLVED,
                    file=symref_path(artifact_symref),
                    line=0,
                    message=_tdd001_unresolved_message(artifact_symref, test_symref),
                )
            )
        # TDDOrder.TEST_FIRST: silent, per T-3004 section 2.
    return out
