"""A11Y gate wiring (docs/modules/webapp-a11y-structure.md, T-5323): the
"first leaf of the family owns the one discovery edit" convention T-5311's
`_taint_gate.py` WEBSEC wiring already set (SUBSTRATE-FANOUT lessons) --
every `frob.webapp._a11y_*` module that exposes a module-level
`a11y_findings(ctx, frameworks) -> tuple[Violation, ...]` hook is
discovered here via `pkgutil.iter_modules` + `importlib`, so a future
A11Y rule module (a second WCAG chunk, say) needs zero edits to this file
to start contributing violations -- it only has to exist under
`frob.webapp._a11y_*` and expose the hook.

Unlike `_taint_gate.py`'s direct-import fold-in (a single WEBSEC sink
module folded into an existing SEC005 gate), A11Y is this family's FIRST
gate: this module walks every git-tracked html-family/jsx-family file
once, parses it once via `frob.lang.raw_tree` (T-5313's own module
docstring: no individual rule module re-parses), and hands the resulting
`frob.webapp._a11y_structure.A11yFileContext` to every discovered hook in
turn -- one parse per file shared across every hook, not one parse per
hook per file.

FRAMEWORK GATING (T-5302): `frob.webapp._detect.detect_frameworks` is
still the entry point that decides whether `root` is a web surface worth
scanning at all -- an empty result short-circuits this gate to `()`
before it even discovers hook modules, the same posture
`websec_sink_findings`/every other WEBSEC/COMPLY/A11Y/SEO/WEBPERF rule
family takes (its own docstring).
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable
from pathlib import Path

from frob import lang as _frob_lang
from frob.gates._models import Violation
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.webapp import (
    _a11y_structure as _a11y_structure_module,  # noqa: F401 -- ensures the first-party hook module is always importable, T-5323
)
from frob.webapp._a11y_structure import A11yFileContext
from frob.webapp._detect import FrameworkKind, detect_frameworks

_log = get_logger(__name__)

# The `a11y_findings(ctx, frameworks) -> tuple[Violation, ...]` hook shape
# every discovered `frob.webapp._a11y_*` module must expose -- typed as a
# real `Callable`, not `object`, so a discovered hook stays callable under
# static analysis (ty/mypy), not just at runtime.
_A11yHook = Callable[
    [A11yFileContext, "frozenset[FrameworkKind]"], "tuple[Violation, ...]"
]

__all__ = ["a11y_gate"]

# Extensions this gate's own file walk covers -- the html-family/jsx-family
# grammars `frob.webapp._a11y_substrate` supports (its own module
# docstring: html, vue's `<template>` block, jsx embedded in js/ts).
_A11Y_EXTENSIONS = (".html", ".htm", ".vue", ".jsx", ".tsx")

# Every `frob.webapp` submodule whose name starts with this prefix is a
# candidate A11Y hook module -- `_a11y_substrate` itself matches the
# prefix too but exposes no `a11y_findings` hook, so it is discovered,
# logged at WARNING, and skipped (module docstring: catalogued is not
# the same as consumed).
_HOOK_MODULE_PREFIX = "frob.webapp._a11y_"

# The hook function name every A11Y rule module must expose.
_HOOK_ATTRIBUTE = "a11y_findings"


def _tracked_a11y_files(root: Path) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `_A11Y_EXTENSIONS`,
    root-relative POSIX paths -- same `_tracked_python_files` shape
    `frob.gates._taint_gate` already uses, generalized to several
    extensions in one `git ls-files` call."""
    spawned = run_argv(
        (
            "git",
            "-C",
            str(root),
            "ls-files",
            "--",
            *(f"*{ext}" for ext in _A11Y_EXTENSIONS),
        )
    )
    if spawned.is_err:
        _log.warning("a11y_gate: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("a11y_gate: git ls-files exited %d", result.returncode)
        return ()
    files = tuple(line for line in result.stdout.splitlines() if line.strip())
    _log.debug("a11y_gate: %d tracked a11y-scannable file(s)", len(files))
    return files


def _discover_hooks() -> tuple[_A11yHook, ...]:
    """Every `frob.webapp._a11y_*` module's `a11y_findings` hook, found
    by walking the `frob.webapp` package once with `pkgutil.iter_modules`
    (module docstring) -- a debug log line per discovered hook module, a
    warning per matching module that carries no hook (the
    "catalogued is not enforced" trap this discovery exists to close)."""
    import frob.webapp as _webapp_package

    hooks: list[_A11yHook] = []
    for module_info in pkgutil.iter_modules(
        _webapp_package.__path__, prefix="frob.webapp."
    ):
        if not module_info.name.startswith(_HOOK_MODULE_PREFIX):
            continue
        module = importlib.import_module(module_info.name)
        hook = getattr(module, _HOOK_ATTRIBUTE, None)
        if hook is None:
            _log.warning(
                "a11y_gate: %s matches the A11Y hook prefix but exposes no "
                "%s -- not wired into the gate",
                module_info.name,
                _HOOK_ATTRIBUTE,
            )
            continue
        _log.debug("a11y_gate: discovered hook in %s", module_info.name)
        hooks.append(hook)
    return tuple(hooks)


# frob:doc docs/modules/webapp-a11y-structure.md#a11y_gate
# frob:ticket T-5323
# frob:enforces CHK-GATE-A11Y101
def a11y_gate(root: Path) -> tuple[Violation, ...]:
    """A11Y101-...: every discovered `frob.webapp._a11y_*` hook's findings
    over every git-tracked html-family/jsx-family file under `root`, each
    file parsed exactly once (module docstring). WARN-tier at first
    turn-on -- same T-0688/T-0973 promotion posture `taint_gate`/
    `opaque_gate` already follow for a brand-new structural rule family."""
    root = Path(root)
    frameworks = detect_frameworks(root)
    if not frameworks:
        _log.debug("a11y_gate: no framework detected at %s, skipping scan", root)
        return ()

    hooks = _discover_hooks()
    if not hooks:
        _log.warning("a11y_gate: no A11Y hook modules discovered, nothing to run")
        return ()

    violations: list[Violation] = []
    scanned = 0
    for rel_path in _tracked_a11y_files(root):
        abs_path = root / rel_path
        parsed = _frob_lang.raw_tree(abs_path, expect_heterogeneous=True)
        if parsed.is_err:
            _log.debug(
                "a11y_gate: skipping unparsed %s: %s", rel_path, parsed.danger_err
            )
            continue
        tree, source, language = parsed.danger_ok
        scanned += 1
        ctx = A11yFileContext(
            file=rel_path, language=language, source=source, root=tree.root_node
        )
        for hook in hooks:
            violations.extend(hook(ctx, frameworks))

    _log.info(
        "a11y_gate: scanned %d file(s) with %d hook(s), %d violation(s)",
        scanned,
        len(hooks),
        len(violations),
    )
    return tuple(violations)
