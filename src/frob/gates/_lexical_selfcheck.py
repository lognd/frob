"""LEXCHECK001: a gate rule that decides a CODE fact from raw text, with no
symref/AST binding on its own finding, is itself a finding (T-1662/T-2344,
docs/design/gate-semantics-classification.md).

T-1662's own directive #4: "a new gate rule constructed from raw text
without a symref or AST node should itself be a finding, so this class
cannot silently return." T-1663's classification pass fixed every KNOWN
instance of this drive's own lexical-decision defects (REF001/T-1665,
DEAD001-OPAQUE001's symref gap/T-1683, and the addendum's T-2178/T-2201/
T-2187/T-2188/T-2243) -- this module is the guard that stops a NINTH one
from landing silently the same way the first eight did.

Detection shape (v1, module-scanning `src/frob/gates/**/*.py`): a single
FUNCTION that (a) calls a `re.search`/`re.match`/`re.fullmatch`/
`re.findall`/`re.finditer` -- the unambiguous "decide something from a
text pattern" signal -- AND (b) constructs at least one `Violation(...)`
call with no `symref=` keyword, is flagged, UNLESS the (module, function)
pair is in `_ALLOWLIST` with a stated reason.

`_ALLOWLIST` mirrors docs/design/gate-semantics-classification.md's own
"Legitimately lexical (class b)" table -- SEC001-004 (an entropy/pattern
scan over unstructured text has no AST node to bind), EXCL001 (a path-glob
question with no richer semantic model), `_fmt_directives.py` (the SUBJECT
is text: reflowing a directive's own comment string), `_rule_id_scan.py`
(its own job IS "what rule-id string literals exist in source"), TICK011
(free-text disclosure detection has no AST/graph substrate; the actual
pass/fail decision downstream is already semantic), WAIVE004 (directive
parsing is textual by necessity; the decision itself is a set-membership
test). A NEW entry needs a reason for the same reason those six do --
this file's own list is a review artifact, not a rubber stamp.

Known v1 limitation, disclosed rather than silently accepted (same
disclosure convention as RENDER001's shadowed-`print` gap and WALK001's
aliased-traversal gap): detection is PER-FUNCTION, so a module that splits
the regex decision and the Violation construction across two different
functions (e.g. a `_scan_text` loop calling a separate `_foo_violation`
per hit -- the exact shape `_render_lint.py`/`_secrets.py` both use, both
already allowlisted) is not caught by this pass. Raising this to a whole-
module call-graph trace is real future work, not attempted here -- v1
catches the single-function shape RENDER001's own pre-fix incidents and
this epic's addendum items shared, and reports what it did NOT check via
its own scanned-vs-flagged count rather than pretending completeness.
"""

from __future__ import annotations

import ast
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gates._parse_failures import local_parse001_violation
from frob.gates._walk_lint import tracked_python_files_for_gate
from frob.logging import get_logger

_log = get_logger(__name__)

#: This module's own file: it is ABOUT the lexical-decision shape, so its
#: prose/docstrings and its own detection logic (which necessarily calls
#: `re`-shaped AST node names, not `re.search` itself) would otherwise be
#: noise, not signal.
_SELF_EXCLUDED_FILES = frozenset({"src/frob/gates/_lexical_selfcheck.py"})

#: (module relpath, function name) pairs already reviewed and judged
#: legitimately textual -- docs/design/gate-semantics-classification.md's
#: "Legitimately lexical (class b)" table is the source of truth this
#: mirrors; keep the two in sync by hand (T-2344 v1 -- no cross-check
#: exists yet between this literal and that doc's table).
_ALLOWLIST: frozenset[tuple[str, str]] = frozenset(
    {
        # INV003/INV004: a whole-DOC-FILE exclusivity/normative-language
        # claim with no bound `frob:invariant` marker -- file-granularity
        # by design (own docstring), no code symbol to bind a symref to.
        # Same documented exception T-1662's own epic body carves out for
        # a whole-file rule like LARGE001.
        ("src/frob/gates/_inv.py", "_inv003_doc_violations"),
        ("src/frob/gates/_inv.py", "_inv004_doc_violations"),
        # TICK011: free-text Done-report disclosure detection has no AST/
        # graph substrate; the trigger is explicitly heuristic (WARN-tier
        # by design), the real pass/fail decision (ticket-id ledger
        # resolution) is class (a) and lives downstream of this same
        # function -- docs/design/gate-semantics-classification.md's own
        # table already carries this exact reasoning.
        ("src/frob/gates/_tickets_gate.py", "_tick011_first_uncited_disclosure"),
        # TODO001: deciding whether a comment LINE is a bare TODO/FIXME
        # marker vs a `frob:`-prefixed directive is a directive-vs-prose
        # text question by nature (same class as SEC004/`frob fmt`'s own
        # directive-wrap reasoning) -- the comment node itself is already
        # AST-resolved via `frob.lang.parse_file` upstream; only the
        # marker-vs-prose call inside it is textual.
        ("src/frob/gates/_todo_fmt.py", "_todo001_bare_comment"),
        # WIRE001 case 2: a new `rule=<literal>` string is definitionally
        # textual -- it is not aliased or computed, the literal itself IS
        # the ground truth, same reasoning `_rule_id_scan.py`'s own
        # generator already carries (both decide "what rule-id string
        # literals exist in source", a text-authority question by
        # construction).
        ("src/frob/gates/_wire.py", "_wire001_rule_id_violations"),
        # SEC004: a `frob:secret-fake` marker with no `reason=` -- the
        # marker's OWN staleness (is it still needed to suppress a real
        # hit) is decided by re-scanning the surrounding text for what the
        # marker was silencing; the subject genuinely IS unstructured
        # text, same reasoning as SEC001's own entropy scan.
        ("src/frob/gates/_secrets.py", "_stale_fake_marker_violations"),
    }
)


def _calls_re_decision(node: ast.AST) -> bool:
    """Whether `node`'s subtree contains a `re.search`/`re.match`/
    `re.fullmatch`/`re.findall`/`re.finditer` call, OR the same method on a
    module-level compiled pattern (this codebase's own `_FOO_RE`/`_FOO_
    PATTERN` naming convention, e.g. `_TICK011_NO_TICKET_NEEDED_RE.search
    (...)`) -- the unambiguous "decide something from a text pattern"
    signal this gate flags on. Deliberately narrow: matching ANY
    `.search`/`.findall`-named method regardless of base would fire on
    unrelated APIs (dict/graph lookups); requiring the `re` module or a
    name ending `_RE`/`_PATTERN` keeps this to the regex idiom this
    epic's own incidents actually used."""
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call) or not isinstance(sub.func, ast.Attribute):
            continue
        if sub.func.attr not in ("search", "match", "fullmatch", "findall", "finditer"):
            continue
        base = sub.func.value
        if not isinstance(base, ast.Name):
            continue
        if base.id == "re" or base.id.endswith(("_RE", "_PATTERN")):
            return True
    return False


def _violation_call_lacks_symref(call: ast.Call) -> bool:
    """Whether a `Violation(...)`-shaped call carries no `symref=` keyword."""
    return not any(kw.arg == "symref" for kw in call.keywords)


def _symref_less_violation_calls(node: ast.AST) -> list[ast.Call]:
    """Every `Violation(...)` call in `node`'s subtree with no `symref=`
    keyword -- matched by call-target name ending in `Violation` (covers
    the bare `Violation(...)` constructor and any `XyzViolation(...)`
    dataclass this repo's gate modules use for a typed intermediate)."""
    hits: list[ast.Call] = []
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        name = sub.func.id if isinstance(sub.func, ast.Name) else None
        name = name or (sub.func.attr if isinstance(sub.func, ast.Attribute) else None)
        if name and name.endswith("Violation") and _violation_call_lacks_symref(sub):
            hits.append(sub)
    return hits


def _lexcheck001_violation(rel_path: str, func_name: str, lineno: int) -> Violation:
    """The LEXCHECK001 `Violation` for one flagged (module, function)."""
    _log.warning(
        "LEXCHECK001: %s:%d %s decides from re.search/match/fullmatch/"
        "findall/finditer and builds a symref-less Violation",
        rel_path,
        lineno,
        func_name,
    )
    return Violation(
        rule="LEXCHECK001",
        severity=Severity.ERROR,
        file=rel_path,
        line=lineno,
        message=(
            f"LEXCHECK001: {rel_path}:{lineno} {func_name} decides a code "
            f"fact from a regex match over raw text and constructs a "
            f"Violation with no symref -- per T-1662 (docs/design/"
            f"gate-semantics-classification.md), a gate must decide from a "
            f"resolved symbol/AST node/graph edge, not a text pattern. If "
            f"this really is legitimately textual (the SUBJECT is text, "
            f"not code -- an entropy scan, a directive/DSL parse, a path-"
            f"glob match), add (rel_path, function name) to "
            f"frob.gates._lexical_selfcheck._ALLOWLIST with a one-line "
            f"reason, mirroring the classification doc's own table -- "
            f"never silently"
        ),
    )


def _parse001_violation(rel_path: str, reason: str) -> Violation:
    """PARSE001 for a file this gate's own `ast.parse` could not get
    through -- shares the drive-wide convention, never a silent drop."""
    return local_parse001_violation(
        rel_path, reason, "LEXCHECK001 cannot inspect it for a lexical decision"
    )


def _tracked_gate_files(root: Path) -> tuple[str, ...]:
    """Every git-tracked `.py` file under `src/frob/gates/`, reusing WALK001/
    RENDER001's shared tracked-file helper (T-0861) rather than a third
    private copy, filtered to this gate's own narrower scope."""
    return tuple(
        rel
        for rel in tracked_python_files_for_gate(root, log_prefix="lexcheck_gate")
        if rel.startswith("src/frob/gates/")
    )


# frob:doc docs/modules/gates.md#lexcheck001-t-2344
# frob:tests tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001.test_new_lexical_decider_is_flagged  # noqa: E501
# frob:tests tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001.test_allowlisted_function_is_silent  # noqa: E501
# frob:tests tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001.test_semantic_function_with_incidental_regex_is_silent  # noqa: E501
# frob:tests tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001.test_non_gate_code_never_scanned  # noqa: E501
# frob:tests tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001.test_every_known_gates_module_module_stays_clean  # noqa: E501
# frob:ticket T-2344
def lexical_selfcheck_gate(root: Path) -> tuple[Violation, ...]:
    """LEXCHECK001: every git-tracked `src/frob/gates/**/*.py` function that
    both decides from a `re.search`/`re.match`/`re.fullmatch`/`re.findall`/
    `re.finditer` call AND constructs a symref-less `Violation`, unless the
    (module, function) pair is in `_ALLOWLIST` with a stated reason (see
    module docstring for the v1 per-function detection scope and its known
    cross-function limitation). A file this gate cannot read/parse fires
    PARSE001 instead of silently dropping out of the scan, matching
    RENDER001's own convention."""
    root = Path(root)
    violations: list[Violation] = []
    for rel_path in _tracked_gate_files(root):
        if rel_path in _SELF_EXCLUDED_FILES:
            continue
        try:
            text = (root / rel_path).read_text(encoding="utf-8", errors="strict")
            tree = ast.parse(text, filename=rel_path)
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            violations.append(_parse001_violation(rel_path, str(exc)))
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if (rel_path, node.name) in _ALLOWLIST:
                continue
            if not _calls_re_decision(node):
                continue
            symref_less = _symref_less_violation_calls(node)
            if symref_less:
                violations.append(
                    _lexcheck001_violation(rel_path, node.name, node.lineno)
                )
    return tuple(violations)


__all__ = ["lexical_selfcheck_gate"]
