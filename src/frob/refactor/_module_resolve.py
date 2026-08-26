"""Resolve phase for `frob refactor move-module` (T-2990): pin a
`ModuleRef` to a real file and its language, refusing before any write
if the file does not exist or its language has no registered
move-module adapter (`frob.refactor._module_lang`).

The language check here is the whole point of the per-language seam
(owner directive on T-2990, T-2996 follow-on): `frob refactor` today
assumes Python throughout with no language branch anywhere in the
package. This module is that branch's first and only home -- a module
in a language `frob.lang.language_for_extension` cannot name, or one
with no adapter registered in `_module_lang`, is refused with a typed
`RefactorError.UnsupportedLanguage` rather than silently doing nothing
or partially rewriting (PLATFORM001's declare-the-boundary rule)."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani import Err, Ok
from typani.result import Result

from frob.lang import language_for_extension, supported_extensions
from frob.logging import get_logger
from frob.refactor._models import RefactorError
from frob.refactor._module_lang import adapter_for
from frob.refactor._operands import ModuleRef
from frob.refactor._resolve import module_to_path

_log = get_logger(__name__)

__all__ = ["ResolvedModule", "resolve_module"]


# frob:doc docs/commands/refactor.md#resolvedmodule
# frob:tests tests/test_refactor.py::TestResolveModule.test_resolves_python_module
class ResolvedModule(BaseModel):
    """The module-verb Resolve phase's output: a `ModuleRef` pinned to a
    real file and the language `frob.lang.language_for_extension`
    reports for it -- `move_module`'s Plan/Apply/Verify phases never
    re-check either."""

    model_config = ConfigDict(frozen=True)

    ref: ModuleRef
    file_path: str
    language: str


def _find_module_file(repo_root: Path, module: str) -> Path | None:
    """`module_to_path`'s own `.py`-suffixed path if it exists, else the
    same dotted path under every OTHER extension `frob.lang` knows
    about, in sorted order -- `None` if none exist. `module_to_path`
    (shared with the symbol engine) always assumes `.py`; a dotted
    module operand naming a same-path file in a different language
    (`pkg.mod` where `pkg/mod.ts` exists, say) would otherwise never be
    found at all, making `RefactorError.UnsupportedLanguage` dead code
    no real operand could ever reach. This is `move-module`-only
    resolution logic -- `module_to_path` itself is untouched."""
    py_path = module_to_path(repo_root, module)
    if py_path.is_file():
        return py_path
    base = py_path.with_suffix("")
    for ext in sorted(supported_extensions()):
        if ext == ".py":
            continue
        candidate = base.with_suffix(ext)
        if candidate.is_file():
            return candidate
    return None


# frob:doc docs/commands/refactor.md#resolve_module
# frob:tests tests/test_refactor.py::TestResolveModule.test_resolves_python_module
# frob:tests tests/test_refactor.py::TestResolveModule.test_refuses_missing_module
# frob:tests tests/test_refactor.py::TestResolveModule.test_refuses_unsupported_language  # noqa: E501
def resolve_module(
    repo_root: Path, ref: ModuleRef
) -> Result[ResolvedModule, RefactorError]:
    """Resolve phase entry point: map `ref.module` to a file (via
    `_find_module_file`, `.py` first, other known extensions as a
    fallback), confirm the file exists, and confirm its language has a
    registered `move-module` adapter
    (`frob.refactor._module_lang.adapter_for`) -- `Err(TargetNotFound)`
    for a missing file, `Err(UnsupportedLanguage)` for a language with no
    adapter (today: everything except Python)."""
    file_path = _find_module_file(repo_root, ref.module)
    if file_path is None:
        _log.warning(
            "refactor.module_resolve: module file missing for any known extension: %s",
            ref.module,
        )
        return Err(RefactorError.TargetNotFound)

    language = language_for_extension(file_path.suffix)
    if language is None or adapter_for(language) is None:
        _log.info(
            "refactor.module_resolve: %s (%s) has no move-module adapter registered",
            ref.module,
            language or file_path.suffix,
        )
        return Err(RefactorError.UnsupportedLanguage)

    return Ok(ResolvedModule(ref=ref, file_path=str(file_path), language=language))
