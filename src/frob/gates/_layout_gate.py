"""LAYOUT gate wiring (docs/modules/webapp-layout-structure.md, T-5767,
frob leaf F-2 of the LAYOUT review gate story T-5747): reuses the "first
leaf of the family owns the one discovery edit" `pkgutil` pattern
`frob.gates._a11y_gate` established for A11Y (T-5323) -- every
`frob.webapp._layout_*` module exposing a module-level
`layout_findings(manifest, manifest_path, root) -> tuple[Violation, ...]`
hook is discovered here, so a future LAYOUT rule module needs zero edits
to this file.

Unlike `_a11y_gate.py` (which parses every html/jsx-family source file
once and hands each hook a parsed tree), this gate walks every
git-tracked `gallery-manifest*.json` file, loads each one exactly once
via `frob.webapp._gallery_schema.load_gallery_manifest` (T-5764's
vendored, crunk-import-free schema), and hands the resulting
`GalleryManifest` to every discovered hook in turn -- one manifest load
per file shared across every hook, not one load per hook per file, same
"parse once, fan out to every hook" discipline `_a11y_gate.py` already
established.

This module does not gate on `frob.webapp._detect.detect_frameworks`
the way A11Y/SEO/WEBPERF do: a repo can have zero web-framework markers
detected and still legitimately carry a `gallery-manifest*.json` file
(crunk's gallery pipeline targets any CSS/JSX component surface, not
specifically a detected framework) -- the presence of a tracked manifest
file IS this gate's own relevance signal, so an empty `git ls-files`
match is what short-circuits to `()`, not an empty `detect_frameworks`.
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable
from pathlib import Path

from frob.gates._models import Violation
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.webapp import (
    _layout_structure as _layout_structure_module,  # noqa: F401 -- ensures the first-party hook module is always importable, T-5767
)
from frob.webapp._gallery_schema import load_gallery_manifest

_log = get_logger(__name__)

__all__ = ["layout_gate"]

# The `layout_findings(manifest, manifest_path, root) -> tuple[Violation, ...]`
# hook shape every discovered `frob.webapp._layout_*` module must expose.
_LayoutHook = Callable[["object", str, Path], "tuple[Violation, ...]"]

# glob crunk's own `schemas/gallery-manifest.v1.json`-style filenames
# follow (`gallery-manifest.v1.json`, a future `gallery-manifest.v2.json`,
# ...) -- matched via a plain prefix/suffix check, not crunk's own
# `SCHEMA_VERSION` (this module never imports crunk).
_MANIFEST_GLOB = "gallery-manifest*.json"

# Every `frob.webapp` submodule whose name starts with this prefix is a
# candidate LAYOUT hook module.
_HOOK_MODULE_PREFIX = "frob.webapp._layout_"

# The hook function name every LAYOUT rule module must expose.
_HOOK_ATTRIBUTE = "layout_findings"


def _tracked_manifest_files(root: Path) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `_MANIFEST_GLOB`,
    root-relative POSIX paths -- same shape `_a11y_gate._tracked_a11y_files`
    already uses for its own extension filter."""
    spawned = run_argv(("git", "-C", str(root), "ls-files", "--", _MANIFEST_GLOB))
    if spawned.is_err:
        _log.warning("layout_gate: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("layout_gate: git ls-files exited %d", result.returncode)
        return ()
    files = tuple(line for line in result.stdout.splitlines() if line.strip())
    _log.debug("layout_gate: %d tracked gallery manifest file(s)", len(files))
    return files


def _discover_hooks() -> tuple[_LayoutHook, ...]:
    """Every `frob.webapp._layout_*` module's `layout_findings` hook,
    found by walking the `frob.webapp` package once with
    `pkgutil.iter_modules` -- a debug log line per discovered hook
    module, a warning per matching module that carries no hook (same
    "catalogued is not enforced" trap `_a11y_gate._discover_hooks`
    already closes for its own family)."""
    import frob.webapp as _webapp_package

    hooks: list[_LayoutHook] = []
    for module_info in pkgutil.iter_modules(
        _webapp_package.__path__, prefix="frob.webapp."
    ):
        if not module_info.name.startswith(_HOOK_MODULE_PREFIX):
            continue
        module = importlib.import_module(module_info.name)
        hook = getattr(module, _HOOK_ATTRIBUTE, None)
        if hook is None:
            _log.warning(
                "layout_gate: %s matches the LAYOUT hook prefix but exposes "
                "no %s -- not wired into the gate",
                module_info.name,
                _HOOK_ATTRIBUTE,
            )
            continue
        _log.debug("layout_gate: discovered hook in %s", module_info.name)
        hooks.append(hook)
    return tuple(hooks)


# frob:doc docs/modules/webapp-layout-structure.md#layout_gate
# frob:ticket T-5767
# tests/unit/test_layout_gate.py::test_gate_returns_empty_with_no_manifest_files  # noqa: E501
def layout_gate(root: Path) -> tuple[Violation, ...]:
    """LAYOUT001-003: every discovered `frob.webapp._layout_*` hook's
    findings over every git-tracked `gallery-manifest*.json` file under
    `root`, each manifest loaded exactly once (module docstring).
    WARN-tier at first turn-on -- same T-0688/T-0973 promotion posture
    `a11y_gate`/`taint_gate`/`opaque_gate` already follow for a
    brand-new structural rule family."""
    root = Path(root)
    manifest_files = _tracked_manifest_files(root)
    if not manifest_files:
        _log.debug("layout_gate: no tracked gallery manifest file(s) under %s", root)
        return ()

    hooks = _discover_hooks()
    if not hooks:
        _log.warning("layout_gate: no LAYOUT hook modules discovered, nothing to run")
        return ()

    violations: list[Violation] = []
    scanned = 0
    for rel_path in manifest_files:
        abs_path = root / rel_path
        loaded = load_gallery_manifest(abs_path)
        if loaded.is_err:
            _log.debug(
                "layout_gate: skipping unloadable manifest %s: %s",
                rel_path,
                loaded.danger_err,
            )
            continue
        manifest = loaded.danger_ok
        scanned += 1
        for hook in hooks:
            violations.extend(hook(manifest, rel_path, root))

    _log.info(
        "layout_gate: scanned %d manifest file(s) with %d hook(s), %d violation(s)",
        scanned,
        len(hooks),
        len(violations),
    )
    return tuple(violations)
