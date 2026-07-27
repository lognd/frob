"""DIP (Dependency Inversion Principle) checks (ARCH1xx, T-0620, EPIC T-0330's
SOLID catalog): a `frob.toml`-declared allowed-module-dependency graph
(import-linter style: named layers + an explicit allowed-edge set), and a
per-file no-DI construction smell (a method body directly constructs a
concrete same-file collaborator instead of receiving one via injection).

WHY a separate module, not `_solid.py`: `_solid.py`'s LSP/ISP checks are
written once against a single file's `NormalizedModule` (T-0609) -- the
layering contract instead needs a PROJECT-WIDE import graph (every layered
file's resolved imports, not one file's normalized shape), the same shape
`frob.cycle`/`frob.app.cycle_runner` already build for cycle detection. No
existing project-wide entry point is reused directly (this ticket's scope
is `_layering.py` alone) but the resolution primitives ARE reused:
`frob.lang.extract_imports`/`resolve_local_import` (the same pair
`frob.app.cycle_runner._build_graph` already calls) rather than
re-deriving import resolution a third time.

RESOLVED, NOT SURFACE, IMPORTS (T-0330's adversarial-hardening note): a
raw import edge alone under-counts real coupling in two ways this module
addresses explicitly:
1. Re-export resolution: importing a package `__init__.py` that itself
   re-exports names from a submodule (`from .sub import X`) really
   couples the importer to `.sub`, not just to the package boundary --
   `_resolve_reexports` follows one bounded hop through an `__init__.py`
   target's OWN local imports and adds those as additional edges from the
   original importer.
2. Fail-closed on dynamic indirection: a file matching a declared layer
   that also contains `importlib.import_module(`/`__import__(` cannot
   have its real import set proven from static imports alone -- rather
   than silently passing (imports it does not statically declare are
   invisible to this scan), such a file is flagged as its own violation
   so a layering claim is never silently unverifiable.

Both categories stay on the same unwaivable advisory channel every other
`frob.arch` category is on; no real ARCH1xx gate is wired in this
ticket's scope (`_layering.py`, `frob.toml`, docs, tests only).
"""
# frob:waive INV006 reason="this module's 'only' occurrences are source-level \
# design-rationale/scope-cut prose describing already-implemented resolvability \
# rules (same-file-only class resolution, this ticket's own declared scope cut) \
# verifiable by reading the functions/docstrings they annotate, not a separate \
# cross-module contract needing its own tracked invariant -- the same INV006 \
# first-turn-on-pool disposition frob.arch._solid's own module docstring already \
# carries"

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from frob.arch._models import ArchSuggestion
from frob.arch._normalized import NormalizedModule

#: Substrings (T-0620) whose presence in a layered file's raw source marks
#: it as containing dynamic/reflective import indirection this scan cannot
#: statically resolve -- the fail-closed half of the adversarial-hardening
#: note: rather than silently under-counting the file's real dependency
#: set, the file itself becomes a violation.
_DYNAMIC_IMPORT_MARKERS = ("importlib.import_module(", "__import__(")


# frob:doc docs/modules/arch.md#dip-layering-contract
class LayeringConfig(BaseModel):
    """The `[arch.layering]` `frob.toml` table (T-0620), parsed: `layers`
    maps a declared layer name to the repo-relative path prefixes that
    belong to it (a file belongs to the first layer whose prefix its
    relative path starts with -- see `layer_for`); `allow` maps a layer
    name to the set of OTHER layer names it may import from. An edge
    between two declared layers not present in `allow` is a violation;
    an edge within the SAME layer, or touching a file in no declared
    layer at all, is never a violation (fail-toward-silence for anything
    the config does not explicitly cover)."""

    model_config = {}

    layers: dict[str, list[str]] = {}
    allow: dict[str, list[str]] = {}

    # frob:doc docs/modules/arch.md#dip-layering-contract
    # frob:tests tests/unit/test_arch.py::TestLayeringConfig.test_layer_for_longest_prefix_match  # noqa: E501
    # frob:tests tests/unit/test_arch.py::TestLayeringConfig.test_layer_for_unmatched_path_is_none  # noqa: E501
    def layer_for(self, rel: str) -> str | None:
        """The declared layer `rel` (a repo-relative POSIX path) belongs
        to, or `None` if no declared prefix matches (T-0620). When more
        than one layer's prefix matches, the LONGEST matching prefix wins
        -- a more specific declared subtree overrides a broader parent
        one, matching how `frob.excludes`' own prefix-style matching
        breaks ties."""
        best_layer: str | None = None
        best_len = -1
        for layer_name, prefixes in self.layers.items():
            for prefix in prefixes:
                if rel == prefix or rel.startswith(prefix.rstrip("/") + "/"):
                    if len(prefix) > best_len:
                        best_len = len(prefix)
                        best_layer = layer_name
        return best_layer


# frob:doc docs/modules/arch.md#dip-layering-contract
# frob:tests tests/unit/test_arch.py::TestLoadLayeringConfig.test_missing_frob_toml_returns_none  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestLoadLayeringConfig.test_parses_declared_layers_and_allow_table  # noqa: E501
def load_layering_config(root: Path) -> LayeringConfig | None:
    """Read the `[arch.layering]` table from `root/frob.toml` (T-0620), or
    `None` if the file/table is absent or malformed -- same posture as
    every other per-section `frob.toml` reader in this codebase (e.g.
    `frob.app.config.load_arch_config`): a missing config means "this
    check has nothing declared to enforce", not an error."""
    path = root / "frob.toml"
    if not path.exists():
        return None
    import tomllib

    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    layering = data.get("arch", {}).get("layering")
    if not isinstance(layering, dict):
        return None
    try:
        return LayeringConfig.model_validate(layering)
    except Exception:  # noqa: BLE001 -- malformed config, same fail-quiet posture
        return None


def _resolve_reexports(target: str, language: str, *, root: Path) -> list[str]:
    """One bounded hop of re-export resolution (T-0620): if `target`
    (a `resolve_local_import`-resolved, `root`-relative path) is a python
    package `__init__.py`, read ITS OWN local imports and resolve those
    too -- the modules `target` re-exports from, which a straight import
    edge to the package alone would otherwise hide. Bounded to one hop
    (an `__init__.py` re-exporting from another `__init__.py` is not
    chased further) to keep this a cheap, terminating scan rather than a
    full transitive closure."""
    if language != "python" or not target.endswith("__init__.py"):
        return []
    from frob.lang import extract_imports, resolve_local_import

    result = extract_imports(root / target)
    if result.is_err:
        return []
    file_dir = (root / target).parent
    out: list[str] = []
    for spec in result.danger_ok:
        resolved = resolve_local_import(spec, language, file_dir=file_dir, root=root)
        if resolved is not None and resolved != target:
            out.append(resolved)
    return out


def _has_dynamic_import(path: Path) -> bool:
    """Whether `path`'s raw source text contains a dynamic/reflective
    import marker (T-0620's fail-closed half) -- a plain substring scan
    (not a parse) since the whole point is to catch indirection a static
    import-edge scan would otherwise miss entirely."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return any(marker in text for marker in _DYNAMIC_IMPORT_MARKERS)


# frob:doc docs/modules/arch.md#dip-layering-contract
# frob:tests tests/unit/test_arch.py::TestLayeringViolations.test_disallowed_cross_layer_edge_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestLayeringViolations.test_allowed_cross_layer_edge_not_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestLayeringViolations.test_dynamic_import_in_layered_file_flagged  # noqa: E501
def check_layering_violations(
    root: Path, config: LayeringConfig
) -> list[ArchSuggestion]:
    """ARCHxxx (T-0620): walk every python file under `root` that belongs
    to a `config`-declared layer (`LayeringConfig.layer_for`), resolve its
    imports (`frob.lang.extract_imports`/`resolve_local_import`, the same
    pair `frob.app.cycle_runner` already uses for cycle detection --
    RESOLVED against the filesystem, not left as raw specifier text), and
    flag every edge whose target ALSO belongs to a declared layer that is
    not in the source layer's `config.allow` list (and is not the same
    layer). Re-export edges (`_resolve_reexports`) are checked the same
    way. A layered file containing dynamic-import indirection
    (`_has_dynamic_import`) is flagged on its own -- this scan cannot
    prove its real dependency set, so it fails closed instead of silently
    passing. Written directly against the filesystem (not `NormalizedModule`
    -- this check needs the WHOLE project's import graph, not one file's
    shape)."""
    from frob.excludes import (
        is_excluded,
        is_skipped_dir,
        iter_files,
        load_exclude_globs,
    )

    exclude_globs = load_exclude_globs(root)
    out: list[ArchSuggestion] = []

    for path in iter_files(root, suffix=".py"):
        try:
            rel_path = path.relative_to(root)
        except ValueError:
            continue
        if any(is_skipped_dir(part) for part in rel_path.parts):
            continue
        rel = rel_path.as_posix()
        if exclude_globs and is_excluded(rel, exclude_globs):
            continue
        source_layer = config.layer_for(rel)
        if source_layer is None:
            continue
        _layering_violations_for_file(path, rel, root, source_layer, config, out)
    return out


# frob:ticket T-0970
def _layering_violations_for_file(
    path: Path,
    rel: str,
    root: Path,
    source_layer: str,
    config: LayeringConfig,
    out: list[ArchSuggestion],
) -> None:
    """One layered file's contribution to `check_layering_violations`:
    the dynamic-import fail-closed flag, then every resolved cross-layer
    import edge not present in `config.allow[source_layer]`; appends
    findings onto `out` in place."""
    from frob.lang import extract_imports, resolve_local_import

    if _has_dynamic_import(path):
        out.append(
            ArchSuggestion(
                file=rel,
                line=None,
                category="dip-layering-violation",
                severity="warning",
                message=(
                    f"`{rel}` (layer `{source_layer}`) uses dynamic import"
                    " indirection this scan cannot statically resolve"
                ),
                detail=(
                    "importlib.import_module()/__import__() can reach any"
                    " module at runtime, defeating a static layering"
                    " check -- replace with a static import, or move the"
                    " dynamic dispatch behind a declared registration"
                    " point this check can see"
                ),
                symref=rel,
            )
        )

    result = extract_imports(path)
    if result.is_err:
        return
    targets: set[str] = set()
    for spec in result.danger_ok:
        resolved = resolve_local_import(spec, "python", file_dir=path.parent, root=root)
        if resolved is None:
            continue
        targets.add(resolved)
        targets.update(_resolve_reexports(resolved, "python", root=root))

    for target in sorted(targets):
        target_layer = config.layer_for(target)
        if target_layer is None or target_layer == source_layer:
            continue
        if target_layer in config.allow.get(source_layer, []):
            continue
        out.append(
            ArchSuggestion(
                file=rel,
                line=None,
                category="dip-layering-violation",
                severity="warning",
                message=(
                    f"`{rel}` (layer `{source_layer}`) imports `{target}`"
                    f" (layer `{target_layer}`) -- not a declared allowed"
                    " dependency"
                ),
                detail=(
                    f"add `{target_layer}` to `[arch.layering.allow]"
                    f".{source_layer}` in frob.toml if this dependency is"
                    " intentional, or remove the import and depend on an"
                    " abstraction instead"
                ),
                symref=rel,
            )
        )


# ---------------------------------------------------------------------------
# ARCHxxx: no-DI concrete-collaborator construction smell (T-0620)
# ---------------------------------------------------------------------------

#: Function-name prefixes (T-0620) that mark a function as an intentional
#: construction site (a factory) -- concrete construction inside one of
#: these is the factory's whole job, not a no-DI smell.
_FACTORY_NAME_PREFIXES = ("make_", "create_", "build_", "new_")

#: Method names (T-0620) where constructing a concrete collaborator is the
#: normal, expected shape (the constructor itself, or python's allocator
#: hook) -- not flagged.
_CONSTRUCTOR_METHOD_NAMES = frozenset({"__init__", "__new__"})


def _is_constructor_call(callee: str, class_names: frozenset[str]) -> str | None:
    """The bare class name `callee` (a `NormalizedCall.callee`) names, if
    `callee` is a bare (non-dotted) identifier matching a same-file class
    in `class_names` -- `None` for a dotted/attribute call (`self.foo()`,
    `pkg.Class()`) or any name not in the corpus (T-0620: only a same-file
    concrete class construction is resolvable enough to flag)."""
    if "." in callee:
        return None
    return callee if callee in class_names else None


# frob:doc docs/modules/arch.md#no-di-construction-smell
# frob:tests tests/unit/test_arch.py::TestNoDiConstructionSmell.test_inline_construction_outside_init_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestNoDiConstructionSmell.test_construction_inside_init_not_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestNoDiConstructionSmell.test_construction_inside_factory_function_not_flagged  # noqa: E501
def check_no_di_construction(module: NormalizedModule) -> list[ArchSuggestion]:
    """ARCHxxx (T-0620): flag every method whose OWN body (not counting
    nested functions) constructs a same-file concrete class inline
    (`_is_constructor_call`) -- EXCLUDING `__init__`/`__new__`
    (`_CONSTRUCTOR_METHOD_NAMES`, where accepting the collaborator as a
    constructor param IS the fix this check is pointing at, so
    constructing it there is not itself the smell) and excluding factory-
    named functions (`_FACTORY_NAME_PREFIXES`, construction IS the job).
    A regular method reaching for `Concrete(...)` mid-body instead of
    using an already-injected collaborator is the no-DI smell: the
    dependency is hidden inside the method instead of visible at the
    class's construction boundary. Written once against `NormalizedModule`,
    so it fires for every `LanguageAdapter`."""
    class_names = frozenset(c.name for c in module.classes)
    out: list[ArchSuggestion] = []
    for cls in module.classes:
        for m in cls.methods:
            if m.name in _CONSTRUCTOR_METHOD_NAMES:
                continue
            if m.name.startswith(_FACTORY_NAME_PREFIXES):
                continue
            _append_no_di_findings(
                module,
                out,
                calls=m.calls,
                class_names=class_names,
                line=m.line,
                symref=f"{module.path}::{cls.name}.{m.name}",
                display_name=f"{cls.name}.{m.name}",
                self_name=cls.name,
                site_kind="method",
            )
    for f in module.functions:
        if f.name.startswith(_FACTORY_NAME_PREFIXES):
            continue
        _append_no_di_findings(
            module,
            out,
            calls=f.calls,
            class_names=class_names,
            line=f.line,
            symref=f"{module.path}::{f.name}",
            display_name=f.name,
            self_name=None,
            site_kind="function",
        )
    return out


# frob:ticket T-0970
def _append_no_di_findings(
    module: NormalizedModule,
    out: list[ArchSuggestion],
    *,
    calls: list,
    class_names: frozenset[str],
    line: int,
    symref: str,
    display_name: str,
    self_name: str | None,
    site_kind: str,
) -> None:
    """Shared body for `check_no_di_construction`'s method and bare-function
    loops: find every same-file class `calls` constructs inline (excluding
    the enclosing class itself for a method site) and append one
    `no-di-construction` suggestion per constructed name, in place onto
    `out`."""
    constructed: set[str] = set()
    for call in calls:
        name = _is_constructor_call(call.callee, class_names)
        if name is not None and name != self_name:
            constructed.add(name)
    boundary = "constructor/param" if site_kind == "method" else "parameter"
    hidden_from = (
        "the class's construction boundary" if site_kind == "method" else "the caller"
    )
    for name in sorted(constructed):
        out.append(
            ArchSuggestion(
                file=module.path,
                line=line,
                category="no-di-construction",
                severity="suggestion",
                message=(
                    f"`{display_name}` directly constructs `{name}` instead"
                    " of receiving it via injection"
                ),
                detail=(
                    f"a concrete collaborator built mid-{site_kind} hides"
                    f" the dependency from {hidden_from} -- accept it as a"
                    f" {boundary} instead"
                ),
                symref=symref,
            )
        )
