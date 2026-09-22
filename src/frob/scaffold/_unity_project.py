"""`unity-project` scaffold type (T-4503): unlike every type in `project.
py`'s `_MANIFESTS`, this one scaffolds ONTO an EXISTING Unity project
directory (one that already has `Assets/`/`Packages/`) rather than
creating a fresh `<output_dir>/<name>/` tree -- a starter `frob.toml`
with Unity's build-cache/meta excludes pre-populated (T-4515's
`UNITY_EXCLUDE_GLOBS`), plus one `design/<node_id>.strata` file per
detected `.asmdef` (T-4512's `discover_asmdefs`/`build_component_nodes`,
reused unchanged -- this module adds no second asmdef reader).

Split out of `project.py` (T-4503 follow-up: that module was already at
exactly `LARGE001`'s 800-line threshold before this type's own logic was
added, the same LARGE001-driven-split precedent T-4443's `_native_
staleness_digest.py` and T-4508's `_dotnet_runner.py` both already set)
rather than folded into `render_project`'s uniform name+output_dir
contract, because neither this type's onto-an-existing-directory
semantics nor its variable design/*.strata file COUNT fit that contract
(`project.py`'s own `test_render_project_all_registered_types_succeed`
assumes every `_MANIFESTS` entry does)."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from typani import Err, Ok
from typani.result import Result

from frob.excludes import UNITY_EXCLUDE_GLOBS
from frob.logging import get_logger
from frob.scaffold.project import (
    _DATA_DIR,
    ScaffoldError,
    _ManifestEntry,
    _resolve_manifest_paths,
    _to_import_name,
    _write_manifest_entries,
)
from frob.strata._unity_asmdef import (
    UnityAsmdefError,
    UnityAssemblyModel,
    UnityComponentNode,
    build_component_nodes,
    discover_asmdefs,
    render_unity_fragment,
)

_log = get_logger(__name__)

# frob:ticket T-4503
# `unity-project`'s manifest, deliberately kept out of `project.py`'s
# `_MANIFESTS`: see this module's own docstring for why. This one entry
# (the static `frob.toml`) still goes through the same `_resolve_
# manifest_paths`/`_write_manifest_entries` machinery every other type
# uses -- only the dynamic `design/*.strata` files need bespoke handling.
_UNITY_PROJECT_MANIFEST: list[_ManifestEntry] = [
    _ManifestEntry("types/unity-project/frob.toml.j2", "frob.toml"),
]


# frob:ticket T-4503
def _unity_project_ctx(root: Path) -> dict:
    """The Jinja `ctx` for `unity-project`'s `frob.toml.j2` -- `project.name`
    derives from `root`'s own directory name (there is no separate `name`
    argument the way `render_project`'s fresh-scaffold types take one,
    since this type renders ONTO an existing directory), and
    `unity.exclude_globs` hands the template `frob.excludes.
    UNITY_EXCLUDE_GLOBS` LIVE rather than duplicating those glob strings
    into the template literally -- a future change to that constant
    (T-4515's own module) then needs no matching edit here."""
    name = root.name
    return {
        "project": {
            "name": name,
            "dist_name": name,
            "import_name": _to_import_name(name),
            "type": "unity-project",
        },
        "unity": {"exclude_globs": UNITY_EXCLUDE_GLOBS},
    }


# frob:ticket T-4503
def _unity_fragment_paths(
    model: UnityAssemblyModel, root: Path
) -> list[tuple[UnityComponentNode, Path]]:
    """One `design/<node_id>.strata` output path per node `build_
    component_nodes` produced (every discovered asmdef, plus the always-
    present default-assembly node) -- T-4503's acceptance criterion 1
    ("one design/*.strata file per asmdef"), computed up front so `
    render_unity_project` can run its OutputExists check before writing
    anything."""
    return [(node, root / "design" / f"{node.node_id}.strata") for node in model.nodes]


# frob:ticket T-4503
# frob:callee-raises OSError
def _write_unity_fragments(
    paths: list[tuple[UnityComponentNode, Path]],
) -> Result[list[Path], ScaffoldError]:
    """Render and write one `.strata` fragment per `(node, path)` pair --
    each fragment covers only that ONE node (`render_unity_fragment`,
    T-4512, reused unchanged: it renders whatever `UnityAssemblyModel` it
    is given, so a one-node model here produces exactly this node's own
    `node {...}` block plus its `flow` lines to whatever it depends on,
    even when that dependency's own node block lives in a sibling
    `design/*.strata` file -- cross-file node references are how every
    other multi-file `design/` directory in this repo already works)."""
    written: list[Path] = []
    for node, out_path in paths:
        single_node_model = UnityAssemblyModel(nodes=(node,))
        fragment_text = render_unity_fragment(single_node_model)
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(fragment_text, encoding="utf-8")
        except OSError:
            _log.error("render_unity_project: could not write %s", out_path)
            return Err(ScaffoldError.RenderFailed)
        written.append(out_path)
    return Ok(written)


# frob:doc docs/commands/scaffold.md#public-api
# frob:ticket T-4503
def render_unity_project(
    root: Path, *, force: bool = False
) -> Result[list[Path], ScaffoldError]:
    """Scaffold the `unity-project` type ONTO an existing Unity project
    directory at `root` (unlike `render_project`'s other types, which
    create a fresh `<output_dir>/<name>/` tree, `root` here already has
    `Assets/`/`Packages/` and this only adds frob's own config alongside
    it): a starter `frob.toml` with Unity's build-cache/meta excludes
    pre-populated (T-4515's `UNITY_EXCLUDE_GLOBS`), plus one `design/
    <node_id>.strata` file per detected `.asmdef` (T-4512's `discover_
    asmdefs`/`build_component_nodes`, reused unchanged -- this module
    adds no second asmdef reader).

    `Err(NotAUnityProject)` when `root` has neither `Assets/` nor
    `Packages/` (acceptance criterion 3: a clear, specific error, never a
    bogus config written for a non-Unity directory). `Err(OutputExists)`
    when `frob.toml` or any of the computed `design/*.strata` paths
    already exists and `force` is not set (criterion 2) -- checked BEFORE
    any file is written, so a refusal never leaves a partial scaffold
    behind."""
    discovered = discover_asmdefs(root)
    if discovered.is_err:
        asmdef_err = discovered.danger_err
        if asmdef_err == UnityAsmdefError.NotAUnityProject:
            return Err(ScaffoldError.NotAUnityProject)
        _log.error(
            "render_unity_project: asmdef discovery failed: %s", asmdef_err.value
        )
        return Err(ScaffoldError.RenderFailed)
    model = build_component_nodes(discovered.danger_ok, root)
    fragment_paths = _unity_fragment_paths(model, root)

    env = Environment(
        loader=FileSystemLoader(str(_DATA_DIR)),
        keep_trailing_newline=True,
    )
    ctx = _unity_project_ctx(root)
    resolved_result = _resolve_manifest_paths(_UNITY_PROJECT_MANIFEST, env, ctx, root)
    if resolved_result.is_err:
        return Err(resolved_result.danger_err)
    resolved = resolved_result.danger_ok

    if not force:
        for _, out_path in resolved:
            if out_path.exists():
                return Err(ScaffoldError.OutputExists)
        for _, frag_path in fragment_paths:
            if frag_path.exists():
                return Err(ScaffoldError.OutputExists)

    written_result = _write_manifest_entries(resolved, env, ctx)
    if written_result.is_err:
        return Err(written_result.danger_err)
    fragments_result = _write_unity_fragments(fragment_paths)
    if fragments_result.is_err:
        return Err(fragments_result.danger_err)
    return Ok(written_result.danger_ok + fragments_result.danger_ok)


__all__ = ["render_unity_project"]
