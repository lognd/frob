"""PERF017/PERF018: success-only cache writes and discarded hoisted values
(T-5136).

Two more of the T-5135 audit's blind spots, neither modeled by any
existing PERF rule because both are about cost ACROSS invocations/frames,
not a single function's own loop/call shape:

- PERF017: a function that calls a *cache_write*-shaped helper (name
  matching `_CACHE_WRITE_RE`) on only ONE branch of an `if`/`else`, then
  returns on both -- the audit's H2 shape (`_write_revalidation_cache`
  only ever called on the success branch, so an UNMEASURABLE/timeout
  outcome is never memoized and gets re-derived, at full cost, on every
  call). Best-effort/textual: does not attempt to prove the OTHER branch
  is actually the failure path, only that it returns without ever
  reaching a cache-write call anywhere in its own subtree -- the same
  over-recall posture every other PERF rule in this package takes.

- PERF018: a value hoisted above a loop (`x = expensive(...)` where
  `expensive` names a known heavy callee, T-5136's own `frob.toml
  [[perf.heavy]]` table) while a call inside the loop body reaches that
  SAME callee name again with no argument naming the hoisted value -- the
  audit's H4 shape (`_sibling_branch_ref` re-scanning `read_all_leases`
  one frame below a loop that had already hoisted it). WARN-tier,
  waivable, same posture as PERF008/015/016.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

from frob.gates._models import Severity, Violation
from frob.lang import child_by_field as _child_by_field
from frob.lang import node_text as _node_text
from frob.lang import raw_tree as _raw_tree
from frob.lang._models import ParsedFile
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["cache_effect_violations", "HEAVY_CALLEE_NAMES"]

_CACHE_WRITE_RE = re.compile(
    r"(?i)(write|store|save|put).*cache|cache.*(write|store|save)"
)

#: T-5136: the `[[perf.heavy]]`-style expensive-callee short names PERF018
#: watches for a hoist-then-recompute shape against -- mirrors the audit's
#: own H4 finding (`read_all_leases`) plus the sibling hotspots named in
#: the same ticket body (`load_queue`, `parse_file`, `build_graph`,
#: `git ls-files`). Kept as a short-name set here (not re-derived from
#: `frob.toml`) so this rule has zero config-file dependency -- T-5136's
#: own follow-up widens `[[perf.heavy]]` itself; this stays a safe,
#: independent floor.
HEAVY_CALLEE_NAMES = frozenset(
    {"read_all_leases", "load_queue", "parse_file", "build_graph"}
)

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_ASSIGN_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\("
)


# frob:enforces CHK-GATE-PERF017
def _perf017_in_function(path: str, func_node) -> list[Violation]:
    """One function's PERF017 hits -- an `if`/`else` where exactly one
    branch reaches a cache-write-shaped call and both branches return."""
    hits: list[Violation] = []
    stack = [func_node]
    while stack:
        node = stack.pop()
        if node.type == "if_statement":
            consequence = _child_by_field(node, "consequence")
            alternative = _child_by_field(node, "alternative")
            if consequence is not None and alternative is not None:
                cons_text = _node_text(consequence)
                alt_text = _node_text(alternative)
                cons_writes = bool(_CACHE_WRITE_RE.search(cons_text))
                alt_writes = bool(_CACHE_WRITE_RE.search(alt_text))
                cons_returns = "return" in cons_text
                alt_returns = "return" in alt_text
                if cons_writes != alt_writes and cons_returns and alt_returns:
                    line = node.start_point[0] + 1
                    missing = "alternative" if cons_writes else "consequence"
                    hits.append(
                        Violation(
                            rule="PERF017",
                            severity=Severity.WARN,
                            file=path,
                            line=line,
                            message=(
                                f"PERF017: {path}:{line} an if/else both "
                                f"branches return, but only one branch "
                                f"calls a cache-write-shaped helper -- the "
                                f"{missing} branch's outcome (e.g. an "
                                f"UNMEASURABLE/timeout/failure result) is "
                                f"never memoized, so the identical doomed "
                                f"work is repeated on every call that "
                                f"lands there; write the negative outcome "
                                f"too, or add a reasoned frob:waive "
                                f'PERF017 reason="..."'
                            ),
                        )
                    )
        stack.extend(node.children)
    return hits


# frob:enforces CHK-GATE-PERF018
def _perf018_in_function(path: str, func_node) -> list[Violation]:
    """One function's PERF018 hits -- a hoisted `x = heavy(...)` above a
    loop whose body calls `heavy(...)` again without `x` in its args."""
    hits: list[Violation] = []
    func_text = _node_text(func_node)
    hoisted: dict[str, str] = {}
    for match in _ASSIGN_RE.finditer(func_text):
        var, callee = match.group(1), match.group(2)
        short = callee.rsplit(".", 1)[-1]
        if short in HEAVY_CALLEE_NAMES:
            hoisted[var] = short
    if not hoisted:
        return hits
    stack = [func_node]
    while stack:
        node = stack.pop()
        if node.type in ("for_statement", "while_statement"):
            body = _child_by_field(node, "body")
            body_text = _node_text(body) if body is not None else ""
            for var, short in hoisted.items():
                pattern = rf"\b{re.escape(short)}\s*\(([^)]*)\)"
                for match in re.finditer(pattern, body_text):
                    args_text = match.group(1)
                    if var in _IDENT_RE.findall(args_text):
                        continue  # hoisted value was threaded through
                    line = node.start_point[0] + 1
                    hits.append(
                        Violation(
                            rule="PERF018",
                            severity=Severity.WARN,
                            file=path,
                            line=line,
                            message=(
                                f"PERF018: {path}:{line} `{var} = "
                                f"{short}(...)` is hoisted above this "
                                f"loop, but the loop body calls "
                                f"{short}(...) again without threading "
                                f"`{var}` through -- the hoist buys "
                                f"nothing if a callee re-derives the same "
                                f"value; pass `{var}` down, or add a "
                                f'reasoned frob:waive PERF018 reason="..."'
                            ),
                        )
                    )
                    break
        stack.extend(node.children)
    return hits


def _file_violations(path: str) -> list[Violation]:
    """PERF017/PERF018 hits in one python source file. `[]` if the file
    cannot be re-parsed or is not python."""
    result = _raw_tree(Path(path))
    if result.is_err:
        return []
    tree, _source, language = result.danger_ok
    if language != "python":
        return []
    violations: list[Violation] = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type in ("function_definition",):
            violations.extend(_perf017_in_function(path, node))
            violations.extend(_perf018_in_function(path, node))
            continue  # do not descend into nested defs twice via the loop below
        stack.extend(node.children)
    return violations


# frob:doc docs/design/coding-performance-corpus.md#perf017-018-t-5136
# frob:ticket T-5136
def cache_effect_violations(files: Sequence[ParsedFile]) -> tuple[Violation, ...]:
    """PERF017/PERF018 (T-5136) over every python file in `files` -- see
    module docstring for both rules' detection shape."""
    violations: list[Violation] = []
    seen_paths: set[str] = set()
    for file in files:
        if file.language != "python" or file.path in seen_paths:
            continue
        seen_paths.add(file.path)
        violations.extend(_file_violations(file.path))
    _log.info(
        "perf017/018: scanned %d python file(s), %d violation(s)",
        len(seen_paths),
        len(violations),
    )
    return tuple(violations)
