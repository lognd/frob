"""PreToolUse Write/Edit/Bash hook: block a `frob:tests` directive written
with pytest's `Class::method` collect-only separator instead of this
graph's own `<file>::<dotted qualname>` convention.

CANONICAL COPY (git-tracked). Materialised into `~/.claude/hooks/` by
`sync-claude-config.py`; never hand-edit the copy.

T-3697: the `frob:tests tests/x.py::TestA::test_b` mistake (should be
`tests/x.py::TestA.test_b` -- a single `::` splitting FILE from SYMBOL,
then a DOTTED qualname inside the symbol half) broke four different
agents' lands this drive, each time surfacing only post-land as a
DRIFT002/DOC007 gate failure -- author-time cost paid, then a second
round-trip to fix it. This hook blocks the exact same recognized-wrong
shape at WRITE time instead, mirroring `src/frob/gates/_docptr.py`'s own
`_DOUBLE_SEP_TESTS_TARGET_RE`/`_tests_target_shape_violations` (DOC007):
a `frob:tests` target containing a SECOND `::` is definitively the wrong
separator, regardless of whether it happens to still resolve to a real
test -- so this hook reuses that exact grammar (a second `::` anywhere in
the target), not a hand-rolled heuristic that could disagree with the
gate it exists to pre-empt.

BLOCK, not nudge: DOC007's own docstring says this shape has zero
legitimate live occurrences and only ever surfaced as an author mistake
-- there is no "maybe you meant it" case to preserve, so this hook denies
outright with the corrected form rather than merely warning.

Scope: `frob:tests` only (the one verb DOC007 itself checks -- see
`_tests_target_shape_violations`'s `if edge.kind != EdgeKind.TESTS`
guard) -- a `path::Class.method`-shaped target is this graph's own
convention on OTHER verbs too (`frob:doc`, `frob:invariant`, ...), but
none of those verbs bind to a pytest-collectible symbol the way `tests`
does, so pytest's `Class::method` separator has no reason to leak into
them the way it does here (author muscle-memory from `pytest path::
Class::method` on the command line).
"""

from __future__ import annotations

import json
import re
import sys

# frob:ticket T-3697
#: T-3697: mirrors `src/frob/gates/_docptr.py::_DOUBLE_SEP_TESTS_TARGET_RE`
#: EXACTLY -- a second `::` anywhere in a `frob:tests` target is the
#: recognized-wrong pytest-collect-only shape, regardless of what comes
#: before or after it. Kept in sync by hand (this hook cannot import
#: `frob.gates` -- it must run standalone with no guarantee `frob` itself
#: is even installed in the invoking shell, same posture as every other
#: hook in this directory); if `_docptr.py`'s grammar ever changes, this
#: constant must change with it.
_DOUBLE_SEP_TESTS_TARGET_RE = re.compile(r"::[^:]*::")

# frob:ticket T-3697
#: T-3697: one `frob:tests` directive line -- `frob:tests` (optionally
#: preceded by a comment delimiter, `#`/`//`/etc, which this hook does not
#: need to recognize since it only anchors on the verb itself, mirroring
#: `frob.graph.dsl._LINE_RE`'s own delimiter-agnostic posture, see that
#: module's docstring: "delimiters are already stripped by the time a
#: RawComment reaches this module") followed by whitespace then the
#: TARGET token (`\S+` -- no whitespace, matching `_LINE_RE`'s own
#: `rest` capture before any ` key="value"` attrs).
_TESTS_DIRECTIVE_RE = re.compile(r"frob:tests\s+(\S+)")


def _corrected_target(target: str) -> str:
    """`target` with every `::` AFTER the first one replaced by `.` -- the
    FILE::SYMBOL boundary (the first `::`) is always valid and left alone;
    only a double-colon INSIDE the symbol half (the `Class::method`
    mistake) is wrong. `tests/x.py::TestA::test_b` -> `tests/x.py::TestA.
    test_b`; a target with three-plus `::` (unlikely, but not this hook's
    business to reject outright) is corrected the same way, left-to-right."""
    file_part, sep, symbol_part = target.partition("::")
    if not sep:
        return target
    return file_part + "::" + symbol_part.replace("::", ".")


def _violating_targets(text: str) -> list[str]:
    """Every `frob:tests` TARGET in `text` that contains the recognized-
    wrong second `::` -- in source-write order, duplicates kept (each is
    its own author-time mistake to report)."""
    return [
        target
        for target in _TESTS_DIRECTIVE_RE.findall(text)
        if _DOUBLE_SEP_TESTS_TARGET_RE.search(target)
    ]


def _reason(targets: list[str]) -> str:
    """The denial message: every offending target alongside its corrected
    form, so the fix is copy-pasteable without a second round-trip."""
    lines = [f'  "{target}" -> "{_corrected_target(target)}"' for target in targets]
    return (
        "BLOCKED by project hook (frob-directive-guard): a `frob:tests` "
        "target uses pytest's `Class::method` collect-only separator "
        "where this graph's convention wants a single `::` splitting "
        "FILE from SYMBOL, then a DOTTED `Class.method` qualname inside "
        "the symbol half (DOC007 -- this exact mistake has broken "
        "multiple agents' lands post-land). Corrected form(s):\n"
        + "\n".join(lines)
        + "\nFix the directive and retry."
    )


# frob:ticket T-3697
def _text_from_tool_input(tool_name: str, tool_input: dict) -> str:
    """Every string this call could WRITE a `frob:tests` directive into,
    joined -- `Write`'s `content`, `Edit`'s `new_string` (never `old_
    string`: the OLD text is not what is being introduced), `NotebookEdit`'s
    `new_source`, and `Bash`'s `command` (a heredoc writing a source file
    is exactly how an agent's own ticket-body or source edit reaches disk
    in this harness's tool surface)."""
    if tool_name == "Write":
        return str(tool_input.get("content") or "")
    if tool_name == "Edit":
        return str(tool_input.get("new_string") or "")
    if tool_name == "NotebookEdit":
        return str(tool_input.get("new_source") or "")
    if tool_name == "Bash":
        return str(tool_input.get("command") or "")
    return ""


# frob:doc docs/guides/claude-hooks.md#frob-directive-guardpy
# frob:ticket T-3697
# frob:tests tests/test_hook_frob_directive_guard.py kind="integration"
def main() -> None:
    """Deny a `Write`/`Edit`/`NotebookEdit`/`Bash` call that would
    introduce a `frob:tests` directive using the wrong `Class::method`
    separator; silently allow everything else (unrecognized tool, no
    directive, or a directive already in the correct form)."""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    text = _text_from_tool_input(tool_name, tool_input)
    if not text:
        return
    targets = _violating_targets(text)
    if not targets:
        return
    # frob:waive RENDER001 reason="standalone hook script (module docstring: run via \
    # python3, never imported), same posture every other hook in this directory takes \
    # -- it must emit the harness's PreToolUse stdin/stdout JSON contract with no \
    # guarantee frob.render (or frob itself) is even importable in the invoking shell; \
    # root-write- guard.py/frob-timeout-guard.py's own identical bare \
    # print(json.dumps(...)) calls predate RENDER001 at their merge-base so this gate \
    # never fires for them, but the underlying reason is the same"
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": _reason(targets),
                }
            }
        )
    )


if __name__ == "__main__":
    main()
