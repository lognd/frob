"""Load and merge every `.strata` design file under a directory (T-0080).

`frob.gates`' SYS family needs one merged view of every id a `.strata`
design declares (Flow ids for `frob:channel`, Boundary ids for
`frob:boundary`, Secret-clearance Node ids for `frob:secret`) to validate
directive bindings in code -- but nothing upstream of this module yet
turns a directory of design files into a single elaborated set of ids.
This module is that one join point: parse each file (`_parse.parse_module`),
elaborate it (`_elaborate.elaborate`), and merge the resulting
`KernelModel`s' id sets. A file that fails to parse or elaborate is
reported, never silently dropped (charter law 1) -- the caller (gates)
decides severity.

`unbound_constructs` is the SYS002 question ("which boundary/secret
constructs have no code binding anywhere") as a neutral, output-agnostic
join -- `frob.gates.sys_gate` (SYS002 `Violation`s) and
`frob.strata.plan_obligations` (the "unbound" frontier's `PlannedTicket`s,
T-0084) both need exactly this detection and previously duplicated it
line-for-line; it lives here once, and each caller renders its own output
shape from the same `(EdgeKind, construct_id)` pairs (T-0084 review
finding 1).
"""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

from frob.excludes import is_excluded, iter_files, load_exclude_globs
from frob.graph import EdgeKind, GraphSnapshot
from frob.logging import get_logger

from ._ast import Module, PolicyDecl, ResourceDecl
from ._errors import StrataError
from ._models import KernelModel
from ._multifile import FileModule, elaborate_merged
from ._parse import parse_module, strata_core_import_error

# T-3529: a second guarded `strata_core` import, mirroring `_parse.py`'s
# own pattern exactly. This module needs it directly (not just through
# `parse_module`) because `_ast.py::Module` does not model the
# entity/architecture/configuration JSON fields `strata_core.parse_source`
# emits (docs/strata/entity_architecture.md's own "Parse-time enforcement,
# not a new gate row" scope note: entities/architectures have no
# `KernelModel` consequence, so nothing upstream of this cross-file join
# point ever needed them modeled). Reaching under `parse_module` here,
# rather than widening `_ast.py::Module`'s surface for one feature, keeps
# this ticket's file scope exactly what it declared.
try:
    strata_core: ModuleType | None = importlib.import_module("strata_core")
except ImportError:  # pragma: no cover - environment-dependent
    strata_core = None

_log = get_logger(__name__)

# frob:doc docs/strata/surface.md#directives-t-0080
#: Construct kinds that require at least one code binding (`frob:boundary`/
#: `frob:secret` directive) -- boundaries and secrets are the enforcement/
#: authority sites the surface language calls out; channels (Flow ids) are
#: left optional since most flows are pure data movement with no single
#: enforcing call site to bind (T-0080 decision, docs/strata/surface.md
#: #directives-t-0080). Shared by `frob.gates`'s SYS002 and
#: `frob.strata.plan_obligations`'s "unbound" frontier (T-0084).
UNBOUND_REQUIRED_KINDS: tuple[EdgeKind, ...] = (EdgeKind.BOUNDARY, EdgeKind.SECRET)

#: Default directory (relative to a repo root) design files live under, when
#: `frob.toml` declares none (`[strata].design_dir`, read by the gates caller).
#: Mirrored as a bare string literal by `frob.gates._DEFAULT_DESIGN_DIR`
#: (src/frob/gates/__init__.py) so `sys_gate`'s design-dir opt-in check
#: never imports `frob.strata` for a repo with no design dir at all
#: (T-0135). The two are locked in sync by
#: `tests/gates_suite/test_sys.py::TestSysGate::
#: test_default_design_dir_mirror_stays_in_sync`.
# frob:doc docs/strata/surface.md#directives-t-0080
DEFAULT_DESIGN_DIR = "design"


# frob:doc docs/strata/surface.md#directives-t-0080
@dataclass(frozen=True)
class DesignLoadError:
    """One `.strata` file that failed to parse or elaborate, kept for reporting.

    `detail` (T-2707) carries the REAL caught exception text when `error`
    is `StrataError.NativeExtensionUnavailable` -- `strata_core`'s own
    guarded import can fail for reasons other than "not installed" (an
    ABI/symbol mismatch, a failing secondary import inside the module),
    and SYS004's fixed-string hint alone previously misattributed all of
    them to the one common cause. `None` for every other `error` kind, or
    when no import error was actually captured."""

    path: str
    error: StrataError
    detail: str | None = None


# frob:doc docs/strata/surface.md#directives-t-0080
@dataclass(frozen=True)
class DesignIds:
    """The merged construct-id surface every `frob:channel/boundary/secret`
    directive is checked against: every Flow id (channel), every Boundary
    id, and every Node id whose `clearance` is `"Secret"` (the kernel has
    no dedicated secret construct yet -- `std.secrets` is T-0082 future
    work -- so a Secret-clearance node is the best-effort standing proxy,
    documented in docs/strata/surface.md#directives-t-0080)."""

    channels: frozenset[str] = frozenset()
    boundaries: frozenset[str] = frozenset()
    secrets: frozenset[str] = frozenset()
    errors: tuple[DesignLoadError, ...] = ()
    #: Every successfully elaborated `KernelModel`, one per `.strata` file --
    #: kept so a caller (e.g. `frob.gates.sys_gate`'s tier-2 conformance
    #: check) can run `bind_code`/`check_import_conformance` per model
    #: without re-parsing (T-0080).
    models: tuple[KernelModel, ...] = ()
    #: T-0724: every `store` id declared by any loaded `.strata` file's
    #: parsed `Module.stores` (pre-elaboration -- a store desugars into a
    #: plain `Node` at elaborate time with no reconstructible marker,
    #: `_contention.py` module docstring), merged across every file. This
    #: is the `store_ids` `frob.strata.check_resource_contention` needs to
    #: evaluate SYS203 (shared store write) -- `models` alone cannot
    #: answer which of its nodes were stores.
    # frob:doc docs/strata/host.md#resource-contention-sys2xx-t-0699
    store_ids: frozenset[str] = frozenset()
    #: T-1061: every `resource ID { arbitrated_by NODE | lock "NAME" }`
    #: declaration (`_ast.py::ResourceDecl`) any loaded `.strata` file's
    #: parsed `Module.resources` declared, pre-elaboration, merged across
    #: every file -- same "not a KernelModel-level fact" limitation
    #: `store_ids` above already documents (a resource has no accessor of
    #: its own to desugar into a node/attr, `_access.py` module
    #: docstring). This is the `module` argument `frob.strata.
    #: check_mode_conformance`/`check_resource_contention` need to
    #: resolve a `lock`/`arbitrated_by` arbiter -- callers build a
    #: throwaway `Module(name=..., resources=ids.resources)` to pass in,
    #: since neither check needs any OTHER `Module` field.
    resources: tuple[ResourceDecl, ...] = ()
    #: T-1843: every `PolicyDecl` (`_ast.py::PolicyDecl`) any loaded `.strata`
    #: file's parsed `Module.policies` declared, pre-elaboration, merged
    #: across every file -- same "not a KernelModel-level fact" limitation
    #: `resources`/`store_ids` above already document (a policy's scope
    #: resolves against the elaborated model, but the decl itself lives
    #: only in the parsed `Module`, which this dataclass otherwise
    #: discards). This is what `frob.gates` INV-051 wiring needs to build
    #: the throwaway `Module(name=..., policies=ids.policies)` that
    #: `frob.strata.compile_policies` takes alongside `models[0]`.
    # frob:doc docs/strata/policy.md#compilation
    policies: tuple[PolicyDecl, ...] = ()


def _strata_files(
    root: Path, design_dir: Path, exclude_globs: tuple[str, ...]
) -> list[Path]:
    """Every `.strata` file under `design_dir`, minus `[graph].exclude` matches,
    in deterministic order. T-0130 excludes `design/litmus/**` (frob's own example
    models) so they carry no obligations; every file-walking surface consults
    `frob.excludes` for this (`frob.graph._walk_source_files`'s posture) --
    a second, un-exclude-aware directory walk here would silently re-impose
    obligations on files the repo explicitly opted out (reviewer-caught gap,
    T-0080 REJECT round 1)."""
    if not design_dir.is_dir():
        return []
    found = []
    for path in sorted(iter_files(design_dir, suffix=".strata")):
        rel = path.relative_to(root).as_posix()
        if exclude_globs and is_excluded(rel, exclude_globs):
            _log.debug("_strata_files: %s excluded by [graph].exclude", rel)
            continue
        found.append(path)
    return found


def _load_all_design_files(
    root: Path, paths: list[Path]
) -> tuple[
    set[str],
    set[str],
    set[str],
    set[str],
    list[ResourceDecl],
    list[DesignLoadError],
    list[KernelModel],
    list[PolicyDecl],
]:
    """Load+merge every `.strata` file in `paths`. Parsing is per-file
    (a read/parse failure in one file is collected and every OTHER file
    still loads); elaboration is CROSS-FILE (T-1196): every successfully
    parsed `Module` is combined and elaborated ONCE via
    `_multifile.elaborate_merged`, so a `flow`/`boundary` in one file may
    reference a `node`/`flow` declared in another loaded file. A
    cross-file reference or elaboration fault fails the WHOLE load closed
    (reported as one `DesignLoadError` per file named by
    `elaborate_merged`) rather than producing a silent partial model --
    the only per-file-recoverable failure is a parse error.

    T-3529: cross-file entity/architecture resolution runs as a second
    pass after every file has parsed (`_resolve_cross_file_architectures`)
    -- it needs every file's entity registry built before any architecture
    can be judged truly unresolved, the same "whole design known first"
    shape `elaborate_merged` already uses for node/flow references."""
    parsed_files, store_ids, resources, policies, errors, arch_facts = (
        _parse_and_collect_files(root, paths)
    )
    errors = list(errors)
    errors.extend(_resolve_cross_file_architectures(arch_facts))

    channels: set[str] = set()
    boundaries: set[str] = set()
    secrets: set[str] = set()
    models: list[KernelModel] = []
    if parsed_files:
        elaborated = elaborate_merged(tuple(parsed_files))
        if elaborated.is_err:
            for cross_error in elaborated.danger_err:
                _log.warning(
                    "load_design_ids: %s failed to elaborate: %s",
                    cross_error.path,
                    cross_error.message,
                )
                errors.append(
                    DesignLoadError(path=cross_error.path, error=cross_error.error)
                )
        else:
            model = elaborated.danger_ok
            models.append(model)
            channels.update(flow.id for flow in model.flows)
            boundaries.update(boundary.id for boundary in model.boundaries)
            secrets.update(
                node.id for node in model.nodes if node.clearance == "Secret"
            )
    return channels, boundaries, secrets, store_ids, resources, errors, models, policies


def _parse_and_collect_files(
    root: Path, paths: list[Path]
) -> tuple[
    list[FileModule],
    set[str],
    list[ResourceDecl],
    list[PolicyDecl],
    list[DesignLoadError],
    list[_FileArchitectureFacts],
]:
    """The per-file half of `_load_all_design_files` (T-3529 split, ARCH001):
    parse every file in `paths`, collecting each success into a
    `FileModule` plus its store/resource/policy decls and raw
    entity/architecture facts, and each failure into a `DesignLoadError`.
    Never raises -- one bad file's `DesignLoadError` is collected and every
    other file still parses."""
    parsed_files: list[FileModule] = []
    store_ids: set[str] = set()
    resources: list[ResourceDecl] = []
    policies: list[PolicyDecl] = []
    errors: list[DesignLoadError] = []
    arch_facts: list[_FileArchitectureFacts] = []
    for path in paths:
        rel, module, error = _parse_one_design_file(root, path)
        if error is not None:
            errors.append(error)
            continue
        assert module is not None
        parsed_files.append((rel, module))
        store_ids.update(store.id for store in module.stores)
        resources.extend(module.resources)
        policies.extend(module.policies)
        facts = _raw_architecture_facts(rel, path)
        if facts is not None:
            arch_facts.append(facts)
    return parsed_files, store_ids, resources, policies, errors, arch_facts


@dataclass(frozen=True)
class _FileArchitectureFacts:
    """T-3529: one file's raw entity/architecture JSON (straight off
    `strata_core.parse_source`, `_ast.py::Module` does not model these --
    see the guarded `strata_core` import comment above), enough to resolve
    an `entity_resolved: false` architecture (`grammar_core.rs::
    parse_architecture`) against a SIBLING file's entity declaration."""

    path: str
    #: entity name -> its `may` ceiling (`frozenset`), one entry per
    #: entity this file declares.
    entities: dict[str, frozenset[str]] = field(default_factory=dict)
    #: every architecture this file declares, as the raw parser JSON
    #: (`name`/`of_entity`/`binds`/`entity_resolved`).
    architectures: tuple[dict, ...] = ()
    #: every node id -> its `may` atoms, straight off this file's raw
    #: parsed `nodes` list (pre-elaboration) -- SYS302's ceiling check
    #: (`binds` stays single-file, T-3529) reads THIS file's own nodes,
    #: same as the Rust parser's original same-file check did.
    node_may: dict[str, frozenset[str]] = field(default_factory=dict)


def _raw_architecture_facts(rel: str, path: Path) -> _FileArchitectureFacts | None:
    """One file's `_FileArchitectureFacts`, reading+re-parsing `path`
    directly through `strata_core.parse_source` (T-3529) since
    `_ast.py::Module` (built by `_parse.py::parse_module`, already called
    successfully for this same file by `_parse_one_design_file`) does not
    carry entity/architecture JSON. Reads the file a second time rather
    than growing `_parse_one_design_file`'s return shape, which
    `frob.gates._coverage_sites` also calls directly outside this
    ticket's declared scope. Returns `None` when `strata_core` is
    unavailable or this second read/parse somehow fails -- unreachable in
    practice since the first parse (by `_parse_one_design_file`) already
    succeeded on this same file moments earlier, but never raises either
    way (T-0134's guarded-native-extension posture, applied here)."""
    if strata_core is None:
        return None
    try:
        text = path.read_text(encoding="utf-8")
        payload = json.loads(strata_core.parse_source(text))
    except (OSError, ValueError, TypeError) as exc:  # pragma: no cover - defensive
        _log.warning("_raw_architecture_facts: %s re-parse failed: %s", rel, exc)
        return None
    ok = payload.get("ok")
    if ok is None:
        return None
    entities: dict[str, frozenset[str]] = {
        str(e["name"]): frozenset(e.get("may") or ()) for e in ok.get("entities", ())
    }
    node_may: dict[str, frozenset[str]] = {
        str(n["id"]): frozenset(n.get("may") or ()) for n in ok.get("nodes", ())
    }
    return _FileArchitectureFacts(
        path=rel,
        entities=entities,
        architectures=tuple(ok.get("architectures", ())),
        node_may=node_may,
    )


def _build_entity_registry(
    files: list[_FileArchitectureFacts],
) -> tuple[dict[str, frozenset[str]], set[str]]:
    """T-3529: one global entity name -> `may` ceiling registry across
    EVERY loaded file (mirroring `elaborate_merged`'s "whole design known
    before any cross-file reference is judged" order). Returns the
    registry plus the set of entity names declared in more than one
    file -- a brand-new cross-file question with no single-file
    precedent, so BOTH declarations are refused (deny-by-default) rather
    than silently picking whichever file loaded first; a duplicate name
    is popped from the registry too, so `entity_name in duplicate_names`
    is `_check_one_architecture`'s only reason to special-case it."""
    registry: dict[str, frozenset[str]] = {}
    declared_in: dict[str, str] = {}
    duplicate_names: set[str] = set()
    for f in files:
        for entity_name, ceiling in f.entities.items():
            if entity_name in declared_in and declared_in[entity_name] != f.path:
                duplicate_names.add(entity_name)
                _log.error(
                    "_build_entity_registry: entity %r declared in both %s and "
                    "%s -- ambiguous, refusing both",
                    entity_name,
                    declared_in[entity_name],
                    f.path,
                )
                continue
            declared_in[entity_name] = f.path
            registry[entity_name] = ceiling
    for entity_name in duplicate_names:
        registry.pop(entity_name, None)
    return registry, duplicate_names


def _check_one_architecture(
    path: str,
    arch: dict,
    node_may: dict[str, frozenset[str]],
    registry: dict[str, frozenset[str]],
    duplicate_names: set[str],
) -> DesignLoadError | None:
    """T-3529: SYS300/SYS302 for one `entity_resolved: false` architecture,
    now that `registry` (`_build_entity_registry`) knows every file's
    entities. `None` when the architecture resolves cleanly."""
    entity_name = arch["of_entity"]
    arch_name = arch["name"]
    if entity_name in duplicate_names:
        return DesignLoadError(
            path=path,
            error=StrataError.DuplicateId,
            detail=(
                f"architecture {arch_name!r} references entity {entity_name!r}, "
                f"which is declared in more than one file -- ambiguous, cannot "
                f"resolve cross-file"
            ),
        )
    ceiling = registry.get(entity_name)
    if ceiling is None:
        return DesignLoadError(
            path=path,
            error=StrataError.UnknownReference,
            detail=(
                f"architecture {arch_name!r} references undeclared entity "
                f"{entity_name!r} -- not declared in this file or any other "
                f"loaded design file (SYS300)"
            ),
        )
    for node_id, atoms in node_may.items():
        exceeded = atoms - ceiling
        if exceeded:
            return DesignLoadError(
                path=path,
                error=StrataError.UnknownReference,
                detail=(
                    f"architecture {arch_name!r} (binding module "
                    f"{arch.get('binds')!r}) grants may {sorted(exceeded)!r} on "
                    f"node {node_id!r}, which exceeds entity {entity_name!r}'s "
                    f"may ceiling {sorted(ceiling)!r} -- an architecture may only "
                    f"realize a SUBSET of its entity's ceiling, never widen it "
                    f"(SYS302)"
                ),
            )
    return None


# frob:ticket T-3529
def _resolve_cross_file_architectures(
    files: list[_FileArchitectureFacts],
) -> list[DesignLoadError]:
    """T-3529: cross-file SYS300/SYS302 for every architecture the Rust
    parser left `entity_resolved: false` (its own entity name is not
    declared in its own file) -- `_build_entity_registry` first, then
    `_check_one_architecture` per unresolved architecture, once every
    file's entities are known. No more specific `StrataError` enum member
    than `UnknownReference` exists in this ticket's declared scope
    (`src/frob/strata/_errors.py`); the `detail` field on each returned
    `DesignLoadError` names the real SYS300/SYS302 violation."""
    registry, duplicate_names = _build_entity_registry(files)
    errors: list[DesignLoadError] = []
    for f in files:
        for arch in f.architectures:
            if arch.get("entity_resolved"):
                continue  # already validated locally by the Rust parser
            error = _check_one_architecture(
                f.path, arch, f.node_may, registry, duplicate_names
            )
            if error is not None:
                errors.append(error)
    return errors


def _parse_one_design_file(
    root: Path, path: Path
) -> tuple[str, Module, None] | tuple[str, None, DesignLoadError]:
    """Read+parse (no elaboration) one `.strata` file; returns `(rel_path,
    module, None)` on success or `(rel_path, None, error)` on any failure,
    never raising. Elaboration is deferred to `elaborate_merged` (T-1196)
    since it now runs once across every parsed file, not per file.

    Signature UNCHANGED by T-3529 on purpose: `frob.gates._coverage_sites`
    also calls this directly, outside this ticket's declared scope --
    `_raw_architecture_facts` (T-3529) reads its own file text separately
    rather than growing this return tuple, so every existing caller keeps
    working unmodified."""
    rel = path.relative_to(root).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning("load_design_ids: could not read %s: %s", rel, exc)
        return rel, None, DesignLoadError(path=rel, error=StrataError.ParseFailed)
    parsed = parse_module(text)
    if parsed.is_err:
        _log.warning("load_design_ids: %s failed to parse: %s", rel, parsed.danger_err)
        detail = (
            strata_core_import_error()
            if parsed.danger_err is StrataError.NativeExtensionUnavailable
            else None
        )
        return (
            rel,
            None,
            DesignLoadError(path=rel, error=parsed.danger_err, detail=detail),
        )
    return rel, parsed.danger_ok, None


# frob:doc docs/strata/surface.md#directives-t-0080
# frob:doc \
# docs/strata/entity_architecture.md#scope-of-this-first-slice-deliberately-narrow
# frob:ticket T-0080
# frob:ticket T-3529
# frob:tests tests/unit/strata/test_design_load.py::TestLoadIds.test_merges_ids
# frob:tests tests/unit/strata/test_design_load.py::TestLoadIds.test_no_dir_empty
# frob:tests tests/unit/strata/test_design_load.py::TestLoadIds.test_bad_file_reported
# frob:tests tests/unit/strata/test_design_load.py::TestLoadIds.test_excluded_no_ids
# frob:tests tests/unit/strata/test_design_load.py::TestCrossFileArchitectureResolution.test_architecture_resolves_against_a_sibling_files_entity  # noqa: E501
def load_design_ids(root: Path, design_dir: str = DEFAULT_DESIGN_DIR) -> DesignIds:
    """Parse+elaborate every `.strata` file under `root/design_dir` and merge
    their Flow/Boundary/Secret-clearance-Node ids into one `DesignIds`.

    A per-file parse/elaborate failure is collected into `.errors` rather
    than aborting the whole load -- one malformed design file must not hide
    every other file's valid constructs from the gate.
    """
    root = Path(root)
    exclude_globs = load_exclude_globs(root)
    paths = _strata_files(root, root / design_dir, exclude_globs)
    channels, boundaries, secrets, store_ids, resources, errors, models, policies = (
        _load_all_design_files(root, paths)
    )

    _log.info(
        "load_design_ids: %d channel(s), %d boundary(ies), %d secret(s), "
        "%d store(s), %d resource(s), %d error(s)",
        len(channels),
        len(boundaries),
        len(secrets),
        len(store_ids),
        len(resources),
        len(errors),
    )
    return DesignIds(
        channels=frozenset(channels),
        boundaries=frozenset(boundaries),
        secrets=frozenset(secrets),
        errors=tuple(errors),
        models=tuple(models),
        store_ids=frozenset(store_ids),
        resources=tuple(resources),
        policies=tuple(policies),
    )


# frob:doc docs/strata/surface.md#directives-t-0080
# frob:ticket T-0084
# frob:ticket T-0972
# frob:tests tests/unit/strata/test_design_load.py::TestUnbound.test_unbound_pair
# frob:tests tests/unit/strata/test_design_load.py::TestUnbound.test_bound_excluded
def unbound_constructs(
    design_ids: DesignIds,
    snapshot: GraphSnapshot,
    kinds: tuple[EdgeKind, ...] = UNBOUND_REQUIRED_KINDS,
) -> tuple[tuple[EdgeKind, str], ...]:
    """Every `(kind, construct_id)` in `kinds` (boundary/secret by default)
    with no `frob:<kind>` directive edge anywhere in `snapshot` -- the raw
    SYS002 join, shared by `frob.gates.sys_gate` (renders `Violation`s) and
    `frob.strata.plan_obligations` (renders `PlannedTicket`s), in
    construct-id order within each kind so both callers get a stable,
    deterministic sequence."""
    bound: dict[EdgeKind, set[str]] = {kind: set() for kind in kinds}
    for edge in snapshot.edges:
        if edge.kind in bound:
            bound[edge.kind].add(edge.target)
    ids_by_kind = {
        EdgeKind.BOUNDARY: design_ids.boundaries,
        EdgeKind.SECRET: design_ids.secrets,
    }
    unbound: list[tuple[EdgeKind, str]] = []
    for kind in kinds:
        # frob:waive PERF004 reason="ids_by_kind.get(kind, ...) is this loop's own \
        # per-kind distinct set, not a shared re-sort"
        for construct_id in sorted(ids_by_kind.get(kind, frozenset())):
            if construct_id not in bound[kind]:
                unbound.append((kind, construct_id))
    return tuple(unbound)


__all__ = [
    "DEFAULT_DESIGN_DIR",
    "UNBOUND_REQUIRED_KINDS",
    "DesignIds",
    "DesignLoadError",
    "load_design_ids",
    "unbound_constructs",
]
