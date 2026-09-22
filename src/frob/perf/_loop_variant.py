"""PERF015/PERF016: loop-VARIANT effectful call detectors (T-5136).

`frob.perf._loop_effects` (PERF008) fires only when EVERY argument at an
effect-reaching call site inside a loop is loop-INVARIANT -- by
construction it is silent on the opposite, far more common shape the
2026-09-20 audit (T-5135) found: a call whose argv carries the loop's own
variable (a ticket id, a file path, a commit sha) as a pathspec/revision,
spawning once per iteration with NO shared, batched alternative visible
to any existing PERF rule (PERF012's duplicate-spawn check needs the SAME
argument shape across two call paths in one function; a loop-variant
argument is never the same shape twice).

Two rules, sharing this module's call-site walk:

- PERF016 (WARN, unconditional): a call reaching a `"spawn"` effect
  (never `"fs-walk"` -- a directory walk has no pathspec/revision
  argument to batch the same way `git cat-file --batch`/`git log --
  <dir>`/`git grep -l <rev>` do) inside a loop, with at least one
  argument referencing the loop's own bound variable or a name derived
  from it. Narrower and higher-confidence than PERF015: every git-spawn
  shape T-5135's H2-H5/M7 fixes addressed is exactly this pattern.

- PERF015 (WARN, advisory/high-volume): the general negation of PERF008
  -- any loop-variant effect-reaching call (spawn OR fs-walk), gated by a
  cheap textual threshold on the variant argument text (matching a
  known "iteration source" name -- ticket/file/path/commit/sha/branch --
  T-5135's own audit table) so this does not fire on every trivial
  loop-variant call in the tree (the ~106-candidate-site volume the audit
  measured), only ones whose variant argument LOOKS like it scales with
  repo size. Every PERF016 hit is also a PERF015 hit; PERF015 additionally
  covers `"fs-walk"` effects and non-git spawns PERF016 excludes.

Both are WARN-tier and waivable (`frob:waive PERF015/PERF016 reason="..."`)
-- re-spawning per iteration can be deliberate (freshness under
concurrency, an iteration count too small to matter), same posture as
PERF008.
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
from frob.perf._effect_summaries import EffectGraph as _EffectGraph
from frob.perf._loop_effects import (
    _assigned_in_body,
    _call_site_effect,
    _iter_loop_call_sites,
    _loop_bound_names,
)

_log = get_logger(__name__)

__all__ = ["loop_variant_effect_violations"]

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

#: T-5136 (PERF015's threshold): a variant argument naming one of these
#: is presumed to scale with repo/queue size (the audit's own "loop
#: variable" table: ticket ids, file paths, commit shas, branch names) --
#: the cheap heuristic that keeps PERF015 from firing on every trivial
#: loop-variant call in the tree.
_ITERATION_SOURCE_RE = re.compile(
    r"(?i)\b(ticket|path|file|commit|sha|branch|line|lease|worktree)\w*\b"
)


def _variant_names_used(
    call_node, loop_vars: frozenset[str], derived: frozenset[str]
) -> frozenset[str]:
    """The subset of `loop_vars | derived` that `call_node`'s own argument
    list actually references -- `()` when the call is loop-invariant (the
    PERF008 case, never a PERF015/016 hit)."""
    variant_names = loop_vars | derived
    if not variant_names:
        return frozenset()
    args = _child_by_field(call_node, "arguments")
    if args is None:
        return frozenset()
    used = frozenset(_IDENT_RE.findall(_node_text(args)))
    return used & variant_names


def _call_site_violations(
    path: str, call_node, loop, source: str | bytes, graph: _EffectGraph
) -> list[Violation]:
    """PERF015/PERF016 verdicts for ONE loop call site -- `_file_
    violations`'s own ARCH001 split (T-5136)."""
    resolved = _call_site_effect(call_node, source, graph)
    if resolved is None:
        return []
    effect, effect_name = resolved
    body = _child_by_field(loop, "body")
    body_text = _node_text(body) if body is not None else ""
    loop_vars = _loop_bound_names(loop)
    derived = _assigned_in_body(body_text) - loop_vars
    variant_used = _variant_names_used(call_node, loop_vars, derived)
    if not variant_used:
        return []  # PERF008's own territory, not ours.
    func = _child_by_field(call_node, "function")
    call_text = _node_text(func) if func is not None else "?"
    line = call_node.start_point[0] + 1
    variant_text = ", ".join(sorted(variant_used))
    hits: list[Violation] = []
    if effect == "spawn":
        hits.append(
            Violation(
                rule="PERF016",
                severity=Severity.WARN,
                file=path,
                line=line,
                message=(
                    f"PERF016: {path}:{line} calls {call_text}(...) "
                    f"inside a loop, reaching {effect_name} (a spawn "
                    f"effect) with loop-variant argument(s) "
                    f"({variant_text}) -- this spawns once per "
                    f"iteration with no batching; replace with one "
                    f"batched form (e.g. `git cat-file --batch`, one "
                    f"`git log -- <dir>`, `git grep -l <rev>`) or add "
                    f'a reasoned frob:waive PERF016 reason="..."'
                ),
            )
        )
    if _ITERATION_SOURCE_RE.search(variant_text):
        hits.append(
            Violation(
                rule="PERF015",
                severity=Severity.WARN,
                file=path,
                line=line,
                message=(
                    f"PERF015: {path}:{line} calls {call_text}(...) "
                    f"inside a loop, transitively reaching "
                    f"{effect_name} (a {effect} effect) with "
                    f"loop-variant argument(s) ({variant_text}) that "
                    f"look like they scale with repo/queue size -- "
                    f"advisory: consider a batched form, or add a "
                    f'reasoned frob:waive PERF015 reason="..."'
                ),
            )
        )
    return hits


def _file_violations(path: str, graph: _EffectGraph) -> list[Violation]:
    """PERF015/PERF016 hits in one python source file -- see module
    docstring. `[]` if the file cannot be re-parsed or is not python."""
    result = _raw_tree(Path(path))
    if result.is_err:
        return []
    tree, source, language = result.danger_ok
    if language != "python":
        return []
    violations: list[Violation] = []
    for call_node, loop in _iter_loop_call_sites(tree.root_node):
        violations.extend(_call_site_violations(path, call_node, loop, source, graph))
    return violations


# frob:doc docs/design/coding-performance-corpus.md#perf015-016-t-5136
# frob:ticket T-5136
def loop_variant_effect_violations(
    files: Sequence[ParsedFile],
    graph: _EffectGraph | None = None,
) -> tuple[Violation, ...]:
    """PERF015/PERF016 (T-5136): the negation of PERF008 -- a loop-body
    call site reaching a spawn/fs-walk effect whose arguments reference
    the loop's own bound variable (or a name derived from it inside the
    loop body). See module docstring for the PERF015 (advisory, threshold-
    gated) vs PERF016 (WARN, spawn-only, unconditional) split.

    `graph`: an optional pre-built `EffectGraph` to share with a sibling
    PERF008/PERF012 run in the same `perf_rules` pass (same T-0919
    precedent those rules already established); builds its own if not
    given."""
    if graph is None:
        graph = _EffectGraph(files)
    violations: list[Violation] = []
    seen_paths: set[str] = set()
    for file in files:
        if file.language != "python" or file.path in seen_paths:
            continue
        seen_paths.add(file.path)
        violations.extend(_file_violations(file.path, graph))
    _log.info(
        "perf015/016: scanned %d python file(s), %d violation(s)",
        len(seen_paths),
        len(violations),
    )
    return tuple(violations)
