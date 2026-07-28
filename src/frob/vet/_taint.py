"""SEC005: intra-function/intra-module taint rule -- a value parsed from a
repo-writable state file (anything under `.git/` or `.frob/`, both
peer-writable by any agent/worktree of this clone, T-0781) reaching a
`subprocess`/`frob.gitio` argv position without passing through a
recognized validator call or a preceding literal `"--"` terminator.

T-0781 (Audit M1 gate-direction finding): the existing SEC family
(`frob.gates._secrets`'s SEC001-004/SEC002, `frob.gates._pii_structural`'s
SEC110) catches `shell=True` and f-string-into-argv construction shapes,
but not this TRUST-BOUNDARY shape -- a value that originated from a peer-
writable file (any worktree/agent of this clone can write `.git/`- or
`.frob/`-relative JSON/text state) flowing unvalidated into a subprocess
argv position is a command-injection-adjacent risk distinct from the
literal-interpolation shapes SEC001-004/SEC110 already cover: the value
here is not a hardcoded secret or an env read, it is state ANOTHER PROCESS
in this repo already controls.

SCOPE (disclosed, not silently narrowed): this is an INTRA-FUNCTION/
INTRA-MODULE flow analysis over Python source only (T-0781's own body:
"scope it honestly as intra-module flow first, interprocedural later").
It tracks:

- SOURCE: an assignment whose right-hand side is a read-like call
  (`.read_text()`/`.read_bytes()`/`json.load(...)`/`json.loads(...)`/
  `tomllib.load(...)`/`yaml.safe_load(...)`) whose own source text
  mentions `.git`/`.frob` (a path literal, or a variable/attribute chain
  visibly built from one within the same statement) -- `_looks_like_repo_
  state_read`.
- VALIDATION: a call whose function name matches `_VALIDATOR_NAME_RE`
  (`validate`/`sanitize`/`assert_safe`/`confine`/`quote`-shaped names)
  clears taint for its result and, conservatively, for any of its
  argument names too (T-1004: a validator that re-binds its input to a
  new name should not still count as tainted under the new name either).
- SINK: a `subprocess.run`/`.Popen`/`.call`/`.check_call`/`.check_output`
  or `frob.gitio.run_argv`-shaped call whose first positional argument is
  a `List`/`Tuple` LITERAL (not an opaque `Name` -- a dynamically-built
  argv list is a separate, harder-to-see-through shape this pass does not
  attempt; that gap is disclosed, not silently assumed safe) -- each
  element checked left-to-right, a bare `"--"` string literal clears every
  tainted name for elements AFTER it in the same call.

A tainted `Name` reaching a sink element with no intervening validator
call and no preceding `"--"` is a finding. Interprocedural flow (taint
crossing a function boundary via a parameter or return value) is NOT
attempted here -- a disclosed phase-2 gap, matching T-0781's own body.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/vet/_taint.py's \
# exclusivity-vocabulary hit is source-level design-rationale prose (a \
# docstring or comment describing already-implemented internal behavior, \
# verifiable by reading the code it annotates) rather than a separate \
# cross-module contract needing its own tracked invariant; disposed as a \
# calibration batch, not claim-by-claim -- first-turn-on prose of \
# the T-0781 taint module"

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["TaintFinding", "taint_findings"]

#: Repo-writable state directories this rule treats as a trust boundary --
#: `.git/` (refs, worktree metadata, hooks) and `.frob/` (ticket/lease/
#: cache state) are both writable by any worktree/agent sharing this
#: clone, not just the process reading them.
_STATE_DIR_MARKERS: tuple[str, ...] = (".git", ".frob")

#: Read-like method/function name suffixes this rule treats as a taint
#: SOURCE when the call's own source text also mentions a state-dir
#: marker (see `_looks_like_repo_state_read`).
_READ_CALL_NAMES: frozenset[str] = frozenset(
    {"read_text", "read_bytes", "load", "loads", "safe_load"}
)

#: Sink call shapes: `subprocess.<name>`/`Popen`/bare `run_argv` (frob's
#: own `frob.gitio.run_argv` seam, docs/modules/gitio.md) -- every one of
#: these accepts an argv-shaped first positional argument.
_SINK_CALL_NAMES: frozenset[str] = frozenset(
    {"run", "Popen", "call", "check_call", "check_output", "run_argv"}
)

_VALIDATOR_NAME_RE = re.compile(
    r"(validate|sanitize|assert_safe|confine|quote)", re.IGNORECASE
)


@dataclass(frozen=True)
class TaintFinding:
    """One SEC005 finding: a repo-state-sourced value reaching an argv sink
    with no validator hop or `--` terminator between source and sink."""

    source_line: int
    sink_line: int
    var_name: str
    sink_call: str


def _looks_like_repo_state_read(node: ast.expr) -> bool:
    """True if unparsing `node` (the assignment's RHS) yields text naming
    both a read-like call (`_READ_CALL_NAMES`) and a `.git`/`.frob` marker
    -- a cheap, honest textual proxy for "this call's target path is
    plausibly under a repo-writable state directory", not a resolved
    path (T-0781: intra-statement flow only, no cross-statement path
    reconstruction)."""
    try:
        text = ast.unparse(node)
    except (ValueError, TypeError):
        return False
    if not any(f".{name}(" in text or f"{name}(" in text for name in _READ_CALL_NAMES):
        return False
    return any(marker in text for marker in _STATE_DIR_MARKERS)


def _call_func_name(node: ast.expr) -> str | None:
    """The bare trailing name of a `Call`'s function (e.g. `run` for
    `subprocess.run(...)`, `read_text` for `p.read_text()`), or `None` for
    a non-`Call`/non-`Name`/`Attribute` func expression."""
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _assigned_names(target: ast.expr) -> list[str]:
    """Every plain `Name` target `target` binds -- handles a bare `Name`
    and `Tuple`/`List` unpacking, skips subscript/attribute targets (which
    do not introduce a new tainted binding under this rule)."""
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for elt in target.elts:
            names.extend(_assigned_names(elt))
        return names
    return []


def _iter_calls(node: ast.AST) -> Iterator[ast.Call]:
    """Every `Call` node anywhere inside `node`, including nested
    subexpressions -- used to find validator/sink calls inside a
    statement without needing a second dedicated visitor per shape."""
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            yield child


# frob:waive DUP001 reason="frob.gates._walk_lint._first_arg_literal matches the same \
# 'guard on call.args, inspect call.args[0]' boilerplate shape but returns a single \
# string literal for a different rule (WALK001's glob-recursion check); this helper \
# returns the argv LIST's element sequence for taint tracking -- same shape, different \
# semantics/return type, not a real duplicate to extract"
def _sink_argv_elements(call: ast.Call) -> list[ast.expr] | None:
    """The element list of `call`'s first positional argument, if that
    argument is a `List`/`Tuple` literal (the only argv shape this pass
    can see through statically) -- `None` for a non-literal (dynamically
    built) argv argument, a disclosed gap, not a silent all-clear."""
    if not call.args:
        return None
    first = call.args[0]
    if isinstance(first, (ast.List, ast.Tuple)):
        return list(first.elts)
    return None


def _validated_names(call: ast.Call) -> list[str]:
    """Every plain `Name` this validator-shaped `call` touches (its
    argument names) -- cleared from the tainted set alongside whatever
    name the call's own result gets assigned to, so a validator's INPUT
    name cannot keep firing after the call either."""
    names: list[str] = []
    for arg in call.args:
        if isinstance(arg, ast.Name):
            names.append(arg.id)
    return names


def _scan_statements(stmts: list[ast.stmt], rel_path: str) -> list[TaintFinding]:
    """One linear top-to-bottom pass over a function/module body's direct
    statement list: tracks `tainted: dict[name, source_line]`, clears an
    entry on a validator call or a plain reassignment, and reports every
    sink-argv element still tainted at the point it is read, honoring a
    preceding literal `"--"` in the SAME argv list as a terminator that
    clears every later element (T-0781's acceptance criterion)."""
    findings: list[TaintFinding] = []
    tainted: dict[str, int] = {}

    for stmt in stmts:
        # Validator/sink calls can appear inside the assignment's own RHS
        # too (e.g. `x = validate(y)`), so scan calls before applying the
        # assignment's own taint/clear effect below.
        for call in _iter_calls(stmt):
            func_name = _call_func_name(call)
            if func_name and _VALIDATOR_NAME_RE.search(func_name):
                for name in _validated_names(call):
                    tainted.pop(name, None)
            if func_name in _SINK_CALL_NAMES:
                elements = _sink_argv_elements(call)
                if elements is None:
                    continue
                cleared = False
                for elt in elements:
                    if (
                        isinstance(elt, ast.Constant)
                        and isinstance(elt.value, str)
                        and elt.value == "--"
                    ):
                        cleared = True
                        continue
                    if cleared:
                        continue
                    if isinstance(elt, ast.Name) and elt.id in tainted:
                        findings.append(
                            TaintFinding(
                                source_line=tainted[elt.id],
                                sink_line=call.lineno,
                                var_name=elt.id,
                                sink_call=func_name or "<unknown>",
                            )
                        )

        if isinstance(stmt, (ast.Assign, ast.AnnAssign)) and stmt.value is not None:
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            names: list[str] = []
            for target in targets:
                names.extend(_assigned_names(target))
            if _looks_like_repo_state_read(stmt.value):
                for name in names:
                    tainted[name] = stmt.lineno
            else:
                # A plain reassignment (not itself a validator call, already
                # handled above) breaks the flow -- the name no longer
                # holds the tainted value from an earlier statement.
                is_validator_result = False
                for call in _iter_calls(stmt.value):
                    func_name = _call_func_name(call)
                    if func_name and _VALIDATOR_NAME_RE.search(func_name):
                        is_validator_result = True
                if not is_validator_result:
                    for name in names:
                        tainted.pop(name, None)

    return findings


# frob:tests tests/unit/vet/test_taint.py::TestTaintFindings.test_unvalidated_state_read_reaching_argv_fires  # noqa: E501
# frob:tests tests/unit/vet/test_taint.py::TestTaintFindings.test_validated_value_does_not_fire  # noqa: E501
def taint_findings(path: Path) -> tuple[TaintFinding, ...]:
    """SEC005 findings for the Python source file at `path`: every
    function body (`FunctionDef`/`AsyncFunctionDef`) and the module's own
    top-level body, each scanned independently as its own linear
    statement sequence (T-0781: intra-function/intra-module scope, no
    cross-function taint propagation). Returns `()` on any parse failure
    -- a syntax-broken file is PARSE001's problem, not this rule's."""
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except OSError as exc:
        _log.debug("taint_findings: unreadable %s: %s", path, exc)
        return ()
    try:
        tree = ast.parse(text, filename=str(path))
    except (SyntaxError, ValueError) as exc:
        _log.debug("taint_findings: unparseable %s: %s", path, exc)
        return ()

    findings: list[TaintFinding] = []
    findings.extend(_scan_statements(list(tree.body), str(path)))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            findings.extend(_scan_statements(list(node.body), str(path)))

    if findings:
        _log.warning("taint_findings: %d SEC005 finding(s) in %s", len(findings), path)
    return tuple(findings)
