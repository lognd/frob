"""Per-language reference-rewrite seam for `frob refactor move-module`
(T-2990 owner directive; T-2996 is the follow-on that will fill in more
languages and audit this axis).

This is the ONE place that decides "what counts as a reference to this
module, and how is it spelled" for a given language -- Python imports,
TypeScript module specifiers, Rust `use` paths, and C/C++ `#include`s
are all spelled differently, so that decision is inherently
per-language. Everything else in the module-move pipeline
(`_operands.py`'s typed operand parsing/destination validation,
`_module_resolve.py`'s file resolution, the `git mv` itself, the
`_commit.py` transaction/rollback shape, and the three Verify-phase
post-conditions in `_verify.py`) is language-agnostic and does not
import anything from this module BY NAME -- they only see the
`ModuleReferenceScanner` shape below, dispatched through `adapter_for`.

Only Python is registered today. A language with no entry in
`_MODULE_LANGUAGE_ADAPTERS` is not silently skipped or partially
handled -- `_module_resolve.resolve_module` refuses it up front with
`RefactorError.UnsupportedLanguage` (PLATFORM001's declare-the-boundary
rule), so a caller sees a named, loud refusal rather than a module move
that quietly did nothing to that language's own import syntax.

Adding a language means writing one function matching
`ModuleReferenceScanner`'s signature and registering it here; nothing
in `_module_transaction.py` changes. Reuses `frob.lang.
language_for_extension` (the canonical extension-to-language table
every other `frob.lang` consumer already shares, per that function's
own docstring) rather than a second per-language table -- and, per the
owner's reuse directive, any future non-Python adapter here should
build on `frob.lang`'s existing grammars/`NormalizedModule` shape
rather than a parallel per-language abstraction invented just for this
package.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

from frob.refactor._models import AliasRecord, RewriteOp

if TYPE_CHECKING:
    from frob.refactor._module_resolve import ResolvedModule
    from frob.refactor._operands import ModuleRef

__all__ = ["ModuleReferenceScanner", "adapter_for", "supported_languages"]

#: `(repo_root, resolved_module, destination) -> (reference_ops, aliases,
#: unresolved)` -- one language adapter's whole contract. Mirrors
#: `frob.refactor._scan.scan_references`'s own `(ops, aliases,
#: unresolved)` return shape so a caller folding this into a
#: `ModulePlan` needs no per-language special-casing.
ModuleReferenceScanner = Callable[
    [Path, "ResolvedModule", "ModuleRef"],
    "tuple[list[RewriteOp], list[AliasRecord], list[str]]",
]


def _python_adapter(
    repo_root: Path, resolved: "ResolvedModule", destination: "ModuleRef"
) -> tuple[list[RewriteOp], list[AliasRecord], list[str]]:
    """Dispatch to the Python module-reference scanner -- imported lazily
    inside the call so importing `_module_lang` alone never pulls in the
    `ast`-based scanner module for a caller that only wants
    `supported_languages`/`adapter_for`."""
    from frob.refactor._module_scan_python import scan_python_module_references

    return scan_python_module_references(repo_root, resolved, destination)


#: The only languages `frob refactor move-module` can rewrite references
#: for today. `_module_resolve.resolve_module` consults this (via
#: `adapter_for`) to refuse anything else loudly rather than silently.
_MODULE_LANGUAGE_ADAPTERS: dict[str, ModuleReferenceScanner] = {
    "python": _python_adapter,
}


# frob:doc docs/commands/refactor.md#adapter_for
# frob:tests tests/test_refactor.py::TestModuleLang.test_python_has_an_adapter
# frob:tests tests/test_refactor.py::TestModuleLang.test_unregistered_language_has_no_adapter  # noqa: E501
def adapter_for(language: str) -> ModuleReferenceScanner | None:
    """The registered `ModuleReferenceScanner` for `language` (a
    `frob.lang.language_for_extension` label), or `None` if this repo's
    `move-module` verb has no adapter for it yet -- the exact signal
    `resolve_module` refuses on."""
    return _MODULE_LANGUAGE_ADAPTERS.get(language)


# frob:doc docs/commands/refactor.md#supported_languages
# frob:tests tests/test_refactor.py::TestModuleLang.test_supported_languages_is_python_only  # noqa: E501
def supported_languages() -> frozenset[str]:
    """Every language with a registered `move-module` adapter today --
    exposed so a caller (a `--help` string, T-2996's matrix) can report
    the boundary without reaching into this module's private registry."""
    return frozenset(_MODULE_LANGUAGE_ADAPTERS)
