"""Unity `.asmdef` assemblies as strata component boundaries (T-4512).

Unity organizes C# source into "assembly definition" files (`*.asmdef`,
JSON, one per directory subtree under `Assets/` or `Packages/`) that are
the REAL compilation-unit boundary Unity itself enforces -- code under one
asmdef's directory cannot see another asmdef's internals except through
its declared `references`. That is exactly the shape a strata component
node already models (`code=<glob>` ownership, `depends`/`flow` edges), so
this module turns each discovered `.asmdef` into one node rather than
inventing a parallel concept.

Built on T-4515's Unity-project detection (`frob.lang._project_detect.
detect_unity_project`) and its `Library/Temp/Logs/obj/*.meta` exclude
globs (`frob.excludes`) -- asmdef discovery only ever walks a project
`detect_unity_project` has already confirmed is Unity, and reuses
`frob.excludes.walk_pruned` so the same build-cache/meta noise T-4515
already prunes from the walker is pruned here too.

Three public steps, kept separate since each fails differently (charter
law 1, `frob.strata._code_binding`'s same two-step precedent):

1. `discover_asmdefs` -- walk `Assets/` and `Packages/` for `*.asmdef`
   files and parse each one's JSON into an `AsmdefInfo`. A malformed
   asmdef is a per-file `Err`, never a silently-skipped file.
2. `build_component_nodes` -- one `UnityComponentNode` per discovered
   asmdef (`code=<asmdef dir>/**`), plus exactly one synthetic
   `UNITY_DEFAULT_ASSEMBLY_NODE` catching `.cs` files no asmdef's
   directory subtree covers (Unity's own implicit default-assembly
   behavior: uncovered code compiles, it does not error) -- acceptance
   criterion 3. `references` entries are resolved to the referenced
   node's id, GUID-form references (`GUID:<hex>`) resolved via each
   asmdef's own `.asmdef.meta` file when present; an unresolvable
   reference is recorded, not dropped (`UnresolvedReference`).
3. `render_unity_fragment` -- pure, deterministic text rendering of the
   built nodes into a `.strata` design fragment (mirrors the compact,
   sorted-output convention `_export.py`'s exporters and `_sync_
   interface.py`'s writer both already follow); `write_unity_fragment`
   is the one I/O boundary that runs 1-3 and writes the result to a
   `design/*.strata` path, wired the same generate-and-verify way
   `_sync_interface.py` writes/checks its own generated block (its
   `--check` idempotency contract, not a second parallel mechanism).
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel
from typani import Err, ErrorSet, Ok, Result

from frob.excludes import UNITY_EXCLUDE_GLOBS, load_exclude_globs, walk_pruned
from frob.lang._project_detect import detect_unity_project
from frob.logging import get_logger

_log = get_logger(__name__)

#: Node id for Unity's implicit default assembly (`.cs` files not covered
#: by any discovered `.asmdef`'s directory subtree) -- acceptance
#: criterion 3: uncovered code is assigned here, never dropped or errored.
UNITY_DEFAULT_ASSEMBLY_NODE = "unity_default_assembly"

#: `includePlatforms` value that, alone, marks an asmdef Editor-only
#: (Unity's own convention: an asmdef compiled only inside the Editor,
#: never shipped in a player build).
_EDITOR_ONLY_PLATFORMS = ("Editor",)


# frob:doc docs/strata/surface.md#unity-asmdef-component-boundaries-t-4512
class UnityAsmdefError(ErrorSet):
    """Failure modes for `.asmdef` discovery/parsing -- recoverable, never
    a bare exception (a malformed or unreadable asmdef is one caller-
    visible `Err`, not a crash mid-walk)."""

    NotAUnityProject = "project_root has neither Assets/ nor Packages/"
    ReadFailed = "an .asmdef file could not be read from disk"
    InvalidJson = "an .asmdef file's contents are not valid JSON"
    MissingName = "an .asmdef file's JSON has no 'name' field"
    WriteFailed = "the generated fragment could not be written to disk"


# frob:doc docs/strata/surface.md#unity-asmdef-component-boundaries-t-4512
class AsmdefInfo(BaseModel):
    """One parsed `.asmdef` file: its declared name, the raw `references`
    it names (assembly names or `GUID:<hex>` forms, unresolved), its
    directory (the `code=` glob root), and its Editor-only/platform/
    define-constraint metadata as Unity wrote them."""

    model_config = {}

    name: str
    path: Path
    directory: Path
    references: tuple[str, ...] = ()
    include_platforms: tuple[str, ...] = ()
    define_constraints: tuple[str, ...] = ()
    guid: str | None = None

    @property
    def is_editor_only(self) -> bool:
        """Whether this asmdef compiles only in the Unity Editor -- true
        exactly when `includePlatforms` is the single-element `["Editor"]`
        list, Unity's own convention for an Editor-only assembly."""
        return tuple(self.include_platforms) == _EDITOR_ONLY_PLATFORMS


# frob:doc docs/strata/surface.md#unity-asmdef-component-boundaries-t-4512
class UnresolvedReference(BaseModel):
    """One `references` entry (`from_node`) that could not be resolved to
    a discovered asmdef's node id -- recorded rather than silently
    dropped, so a dangling reference is visible to the caller."""

    model_config = {}

    from_node: str
    raw_reference: str


# frob:doc docs/strata/surface.md#unity-asmdef-component-boundaries-t-4512
class UnityComponentNode(BaseModel):
    """One strata component node derived from a discovered `.asmdef` (or
    the synthetic default-assembly node): its node id, `code=` glob(s),
    resolved `depends` edges (node ids), and whether it is Editor-only."""

    model_config = {}

    node_id: str
    code_globs: tuple[str, ...]
    depends: tuple[str, ...] = ()
    is_editor_only: bool = False


# frob:doc docs/strata/surface.md#unity-asmdef-component-boundaries-t-4512
class UnityAssemblyModel(BaseModel):
    """The full result of mapping a Unity project's asmdefs onto strata
    component boundaries: every built node plus any reference this
    project's asmdefs named that did not resolve to a discovered node."""

    model_config = {}

    nodes: tuple[UnityComponentNode, ...]
    unresolved_references: tuple[UnresolvedReference, ...] = ()


def _asmdef_node_id(name: str) -> str:
    """The strata node id for an asmdef named `name` -- a stable, lexer-
    safe slug (lowercased, non-alnum runs collapsed to `_`) so an asmdef
    name containing spaces or dots (both legal in Unity) still produces a
    valid strata identifier."""
    slug_chars = [c.lower() if c.isalnum() else "_" for c in name]
    slug = "".join(slug_chars)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return f"unity_{slug.strip('_')}"


def _read_meta_guid(asmdef_path: Path) -> str | None:
    """The GUID Unity's own `<name>.asmdef.meta` sidecar declares for
    `asmdef_path`, or `None` if the sidecar is absent/unparsable -- the
    only mechanism a `GUID:<hex>` reference can be resolved through, since
    the GUID itself is not present in the `.asmdef` file it names."""
    meta_path = asmdef_path.with_name(asmdef_path.name + ".meta")
    if not meta_path.is_file():
        return None
    try:
        text = meta_path.read_text(encoding="utf-8")
    except OSError:
        _log.warning("unity_asmdef.meta_read_failed", extra={"path": str(meta_path)})
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("guid:"):
            return stripped[len("guid:") :].strip()
    return None


def _parse_one_asmdef(path: Path) -> Result[AsmdefInfo, UnityAsmdefError]:
    """Parse a single `.asmdef` file at `path` into an `AsmdefInfo`,
    resolving its `.meta` sidecar's GUID alongside it (both reads live in
    this one function since a GUID with no asmdef, or vice versa, is not a
    state this module needs to represent separately)."""
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError:
        _log.error("unity_asmdef.read_failed", extra={"path": str(path)})
        return Err(UnityAsmdefError.ReadFailed)
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        _log.error("unity_asmdef.invalid_json", extra={"path": str(path)})
        return Err(UnityAsmdefError.InvalidJson)
    name = payload.get("name")
    if not isinstance(name, str) or not name:
        _log.error("unity_asmdef.missing_name", extra={"path": str(path)})
        return Err(UnityAsmdefError.MissingName)
    info = AsmdefInfo(
        name=name,
        path=path,
        directory=path.parent,
        references=tuple(payload.get("references", []) or []),
        include_platforms=tuple(payload.get("includePlatforms", []) or []),
        define_constraints=tuple(payload.get("defineConstraints", []) or []),
        guid=_read_meta_guid(path),
    )
    _log.info(
        "unity_asmdef.parsed",
        extra={
            "path": str(path),
            "asmdef_name": name,
            "editor_only": info.is_editor_only,
        },
    )
    return Ok(info)


# frob:doc docs/strata/surface.md#unity-asmdef-component-boundaries-t-4512
def discover_asmdefs(
    project_root: Path,
) -> Result[tuple[AsmdefInfo, ...], UnityAsmdefError]:
    """Walk `project_root`'s `Assets/` and `Packages/` subtrees (via
    `frob.excludes.walk_pruned`, so `Library/Temp/Logs/obj/*.meta` are
    already pruned per T-4515) for every `*.asmdef` file and parse each
    one; the first unparsable asmdef fails the whole discovery closed
    (charter law 1) rather than silently dropping it."""
    detected = detect_unity_project(project_root)
    if detected.is_err:
        _log.error("unity_asmdef.not_unity_project", extra={"root": str(project_root)})
        return Err(UnityAsmdefError.NotAUnityProject)
    exclude_globs = UNITY_EXCLUDE_GLOBS + load_exclude_globs(project_root)
    asmdef_paths: list[Path] = []
    for scan_root in (project_root / "Assets", project_root / "Packages"):
        if not scan_root.is_dir():
            continue
        for file_path in walk_pruned(scan_root, exclude_globs=exclude_globs):
            if file_path.suffix == ".asmdef":
                asmdef_paths.append(file_path)
    _log.info(
        "unity_asmdef.discovery_scanned",
        extra={"root": str(project_root), "count": len(asmdef_paths)},
    )
    infos: list[AsmdefInfo] = []
    for asmdef_path in sorted(asmdef_paths):
        parsed = _parse_one_asmdef(asmdef_path)
        if parsed.is_err:
            return Err(parsed.danger_err)
        infos.append(parsed.danger_ok)
    return Ok(tuple(infos))


def _resolve_reference(
    raw_reference: str,
    name_to_node: dict[str, str],
    guid_to_node: dict[str, str],
) -> str | None:
    """The node id `raw_reference` (an asmdef `references` entry -- either
    a plain assembly name or a `GUID:<hex>` form) resolves to, or `None`
    if neither lookup table names it."""
    if raw_reference.startswith("GUID:"):
        return guid_to_node.get(raw_reference[len("GUID:") :])
    return name_to_node.get(raw_reference)


def _code_glob(directory: Path, project_root: Path) -> str:
    """The `code=` glob for `directory`, relative to `project_root` -- an
    asmdef owns its own directory subtree, mirroring `_code_binding.py`'s
    `code=<glob>` convention (a trailing `/**` matches every file under
    it, including the asmdef's own directory)."""
    try:
        rel = directory.relative_to(project_root)
    except ValueError:
        rel = directory
    rel_str = str(rel).replace("\\", "/")
    return f"{rel_str}/**" if rel_str not in ("", ".") else "**"


# frob:doc docs/strata/surface.md#unity-asmdef-component-boundaries-t-4512
def build_component_nodes(
    asmdefs: tuple[AsmdefInfo, ...], project_root: Path
) -> UnityAssemblyModel:
    """Map every discovered `AsmdefInfo` onto one `UnityComponentNode`
    (acceptance criterion 1: two asmdefs in, two distinct nodes out),
    resolve each one's `references` into `depends` edges by name or GUID
    (criterion 2), and always append `UNITY_DEFAULT_ASSEMBLY_NODE` with no
    `references` of its own -- Unity's implicit default assembly catches
    every `.cs` file no asmdef claims (criterion 3), so it always exists
    even when every discovered asmdef's `code=` glob happens to cover the
    whole project."""
    name_to_node = {info.name: _asmdef_node_id(info.name) for info in asmdefs}
    guid_to_node = {
        info.guid: _asmdef_node_id(info.name) for info in asmdefs if info.guid
    }

    nodes: list[UnityComponentNode] = []
    unresolved: list[UnresolvedReference] = []
    for info in asmdefs:
        node_id = name_to_node[info.name]
        depends: list[str] = []
        for raw_reference in info.references:
            resolved = _resolve_reference(raw_reference, name_to_node, guid_to_node)
            if resolved is None:
                unresolved.append(
                    UnresolvedReference(from_node=node_id, raw_reference=raw_reference)
                )
                _log.warning(
                    "unity_asmdef.unresolved_reference",
                    extra={"node_id": node_id, "raw_reference": raw_reference},
                )
            else:
                depends.append(resolved)
        nodes.append(
            UnityComponentNode(
                node_id=node_id,
                code_globs=(_code_glob(info.directory, project_root),),
                depends=tuple(depends),
                is_editor_only=info.is_editor_only,
            )
        )

    nodes.append(
        UnityComponentNode(
            node_id=UNITY_DEFAULT_ASSEMBLY_NODE,
            code_globs=("**/*.cs",),
            depends=(),
            is_editor_only=False,
        )
    )
    _log.info(
        "unity_asmdef.nodes_built",
        extra={"node_count": len(nodes), "unresolved_count": len(unresolved)},
    )
    return UnityAssemblyModel(
        nodes=tuple(nodes), unresolved_references=tuple(unresolved)
    )


#: Header comment stamped on every generated fragment -- matches the
#: "clearly generated, do not hand-edit" convention `_sync_interface.py`'s
#: writer already establishes for a machine-maintained `.strata` block.
_FRAGMENT_HEADER = (
    "// GENERATED by `frob.strata._unity_asmdef.write_unity_fragment` (T-4512).\n"
    "// Do not hand-edit -- re-run the generator to refresh this file.\n"
)


# frob:doc docs/strata/surface.md#unity-asmdef-component-boundaries-t-4512
def render_unity_fragment(model: UnityAssemblyModel) -> str:
    """Pure, deterministic `.strata` text for `model` -- one `node` block
    per `UnityComponentNode` (sorted by id for a diffable, byte-stable
    output, matching `_export.py`'s exporters and `_sorted_node_ids`'s own
    documented rationale), plus one `flow` line per resolved `depends`
    edge. No I/O; `write_unity_fragment` is the sole caller that touches
    disk."""
    lines = [_FRAGMENT_HEADER]
    nodes_by_id = {node.node_id: node for node in model.nodes}
    for node_id in sorted(nodes_by_id):
        node = nodes_by_id[node_id]
        globs = ", ".join(f'"{glob}"' for glob in node.code_globs)
        lines.append(f"node {node.node_id} : trusted {{")
        lines.append(f"    code {globs};")
        if node.is_editor_only:
            lines.append("    attr editor;")
        lines.append("    clearance Internal;")
        lines.append("}")
        lines.append("")
    for node_id in sorted(nodes_by_id):
        node = nodes_by_id[node_id]
        for dep in sorted(node.depends):
            flow_id = f"f_{node_id}_{dep}"
            lines.append(
                f"flow {flow_id} : {node_id} -> {dep} {{ label Internal; attr local; }}"
            )
    return "\n".join(lines).rstrip() + "\n"


# frob:doc docs/strata/surface.md#unity-asmdef-component-boundaries-t-4512
def write_unity_fragment(
    project_root: Path, output_path: Path
) -> Result[UnityAssemblyModel, UnityAsmdefError]:
    """Discover+build+render a Unity project's asmdef component model and
    write it to `output_path` (the one I/O boundary this module owns,
    mirroring `_sync_interface.py`'s own generate-and-verify writer --
    a repeat call with an unchanged project produces byte-identical
    output, the idempotency contract that mechanism already established
    for a generated `.strata` fragment)."""
    discovered = discover_asmdefs(project_root)
    if discovered.is_err:
        return Err(discovered.danger_err)
    model = build_component_nodes(discovered.danger_ok, project_root)
    fragment_text = render_unity_fragment(model)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(fragment_text, encoding="utf-8")
    except OSError:
        _log.error("unity_asmdef.write_failed", extra={"path": str(output_path)})
        return Err(UnityAsmdefError.WriteFailed)
    _log.info(
        "unity_asmdef.fragment_written",
        extra={"path": str(output_path), "node_count": len(model.nodes)},
    )
    return Ok(model)
