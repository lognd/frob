"""frob.strata._bootstrap -- `frob sys init`: derive a starting `.strata`
skeleton for a repo with NO existing design model (T-2910, child of the
T-2920 shrink-only ratchet epic).

WHY THIS EXISTS: SYS200-205 (resource contention: duplicate port
bindings, pairwise-overlapping path claims, duplicate pipe names,
multi-writer stores with no arbiter) and SYS003 (undeclared cross-
component import) are strata's most valuable checks -- they catch real
system bugs with no test run at all. But they need a hand-written
`.strata` model first, and nobody adopting frob is going to hand-write
one from scratch the way this repo's own `design/frob.strata` was built
over many sessions. A repo with zero nodes gets zero value from any of
those rules on day one. This module closes that gap with one command.

STRUCTURAL CONSTRAINT (read `docs/commands/sys.md#frob-sys-init-t-2910`
and T-2920's own ticket body before touching this file): a `may=`
capability list is a CEILING whose whole purpose is to forcibly SHRINK a
node's interface below what the code happens to do. Deriving that
ceiling FROM the observed code (the T-2907 proposal T-2920 overturned)
makes it always equal reality -- a rubber stamp with no teeth, exactly
the mistake `_sync_may.py`'s widening writer already made (T-2922 is
unwiring that caller). So `sys init` NEVER emits an observed-capability
`may=` line at all -- not even commented out. It emits only the parts
that are genuinely observational facts about the repo, not a constraint
choice a human should be making: node ids, `code=` ownership globs
derived from the package layout, and the real cross-component import
edges as `flow` declarations. SYS100/SYS103 then tell the adopting human
exactly which `may=` atoms to declare by hand, the same way they would
for any node with a `code=` glob but no declared capability -- that is
the intended day-two step this bootstrap sets up, not something this
module should shortcut.

BOOTSTRAP, NOT SYNC: `derive_bootstrap_model` only ever runs against a
repo with NO `.strata` file anywhere under its design directory --
`frob.app.sys_runner._run_init` refuses (no write) when one already
exists, pointing at `frob sys shrink` (T-2923) for ongoing maintenance
of an existing model. There is no "update"/"regenerate" mode here on
purpose: allowing this module to touch an existing model would turn it
into exactly the auto-widening machinery T-2920 forbids.

DISCLOSED SCOPE: Python only (inherited from `frob.graph.imports`, which
this module's flow-derivation reuses rather than re-implementing import
resolution a second time -- see that module's own docstring for the
exact resolution contract). A repo with no Python source produces a
model with nodes but no flows, and that absence is reported, not
silently implied to be "no cross-component imports exist."
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.gates._tracked_files import tracked_files
from frob.graph.imports import build_import_graph
from frob.logging import get_logger

from ._design_load import DEFAULT_DESIGN_DIR
from ._errors import StrataError

_log = get_logger(__name__)

__all__ = [
    "BootstrapComponent",
    "BootstrapFlow",
    "BootstrapModel",
    "derive_bootstrap_model",
    "existing_design_files",
    "render_bootstrap_text",
    "write_bootstrap_model",
]

#: Top-level directory names never treated as a source component -- test
#: suites, docs, tooling, and generated/vendored trees carry no
#: architectural signal of their own (matches the exclusion posture
#: `frob.excludes`/`_code_binding.py` already apply elsewhere in this
#: package, kept as a small local literal list rather than importing
#: those modules' own repo-specific config, since this module must work
#: against a FOREIGN repo with no frob.toml of its own yet).
_EXCLUDED_TOP_DIRS = frozenset(
    {
        "tests",
        "test",
        "docs",
        "doc",
        "scripts",
        "examples",
        "example",
        DEFAULT_DESIGN_DIR,
        "build",
        "dist",
        "migrations",
        "vendor",
        "node_modules",
        "tools",
        "benchmarks",
        "bench",
        "fixtures",
        "stubs",
        "htmlcov",
    }
)

#: Any path segment that marks a file as non-source wherever it appears
#: (not just at the top), e.g. a nested `tests/` package or a build
#: cache directory.
_EXCLUDED_SEGMENTS = frozenset(
    {"__pycache__", ".venv", "venv", ".git", "tests", "test"}
)

_NON_IDENT_RE = re.compile(r"[^A-Za-z0-9_]+")


def _is_source_python(path: str) -> bool:
    """`True` if `path` (repo-relative, POSIX) is a Python file this
    bootstrap should model as owned by some component -- excludes test
    files/dirs and the other non-architectural top-level dirs listed in
    `_EXCLUDED_TOP_DIRS`/`_EXCLUDED_SEGMENTS` above."""
    if not path.endswith(".py"):
        return False
    segments = path.split("/")
    if segments[0] in _EXCLUDED_TOP_DIRS:
        return False
    if any(seg in _EXCLUDED_SEGMENTS for seg in segments):
        return False
    name = segments[-1]
    if name == "conftest.py" or name.startswith("test_") or name.endswith("_test.py"):
        return False
    return True


def _sanitize_ident(raw: str) -> str:
    """A raw path segment turned into a valid strata identifier: non-
    alnum/underscore runs collapse to one `_`, and a leading digit gets a
    `_` prefix (identifiers cannot start with a digit)."""
    ident = _NON_IDENT_RE.sub("_", raw).strip("_") or "component"
    if ident[0].isdigit():
        ident = f"_{ident}"
    return ident


# frob:doc docs/commands/sys.md#frob-sys-init-t-2910
# frob:tests \
# tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelComponentsAndFlows.test_\
# single_top_package_splits_by_subdirectory kind="unit"
@dataclass(frozen=True)
class BootstrapComponent:
    """One derived node: its id, the `code=` glob(s) backing it, and how
    many tracked Python files those globs cover (purely for the human-
    readable summary `derive_bootstrap_model` logs, not written into the
    `.strata` text itself). Almost always a single `**` directory glob --
    `code_globs` is a tuple, not a bare `str`, only because the loose-
    files-in-a-single-package-root case (`_group_components`'s `<pkg>_
    root` bucket) needs one EXACT path per file instead: `fnmatch`
    (`_code_binding.bind_code`'s own matcher) has no "this segment, not
    below" wildcard -- `*` matches `/` too -- so a would-be `pkg/*.py`
    glob silently ALSO matches `pkg/sub/whatever.py` and collides with
    that subdirectory's own `**` glob (AmbiguousCodeBinding, SYS003
    disabled entirely on that model). Measured against a real repo
    (T-2910's own foreign-repo control) before this was caught."""

    id: str
    code_globs: tuple[str, ...]
    file_count: int


# frob:doc docs/commands/sys.md#frob-sys-init-t-2910
# frob:tests \
# tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelComponentsAndFlows.test_\
# real_import_edge_becomes_a_flow_in_the_right_direction kind="unit"
@dataclass(frozen=True)
class BootstrapFlow:
    """One derived directed component-to-component import edge
    (`src != dst`, always -- a component never gets a flow to itself).
    `edge_count` is how many individual file-level import edges this one
    flow summarizes, again for the summary only."""

    src: str
    dst: str
    edge_count: int


# frob:doc docs/commands/sys.md#frob-sys-init-t-2910
# frob:tests \
# tests/unit/strata/test_bootstrap.py::TestRenderedTextParsesAndElaborates.test_empty_m\
# odel_still_parses kind="unit"
@dataclass(frozen=True)
class BootstrapModel:
    """The full derived skeleton plus its rendered `.strata` text, ready
    for `write_bootstrap_model` to write verbatim. `scanned_file_count`
    is every tracked Python file this bootstrap considered (source +
    excluded), for an honest "nothing to model" report when it is 0."""

    module_name: str
    components: tuple[BootstrapComponent, ...]
    flows: tuple[BootstrapFlow, ...]
    text: str
    scanned_file_count: int


def _module_name_for(root: Path) -> str:
    """The `module <name>` this bootstrap declares: the repo root
    directory's own name, sanitized -- the same "name the model after
    the repo" convention `design/frob.strata`'s own `module frob` line
    follows."""
    return _sanitize_ident(root.resolve().name or "repo")


def _group_components(
    source_files: list[str],
) -> tuple[dict[str, str], dict[str, list[str]]]:
    """`(file -> component id, component id -> code glob(s))` for every
    file in `source_files`. Layout rule: a `src/` prefix is stripped
    first if ANY source file has one (the common src-layout convention).
    Below that, if the repo has more than one distinct top-level
    package/dir, each becomes its own component (`top -> ["<prefix>top/
    **"]`, matching this repo's own `design/frob.strata` per-package
    granularity). If the repo has exactly ONE top-level package (the
    common single-package-project shape, e.g. `src/pkg/**`), a bare
    top-level component would be useless (one node, never any flow) --
    so this rule descends one more level and treats each of THAT
    package's own immediate subdirectories as a component instead.

    Files directly in the package root (no subdirectory) go into one
    `<pkg>_root` component -- as an EXACT per-file glob LIST, never a
    `<pkg>/*.py` wildcard: `fnmatch` (`_code_binding.bind_code`'s own
    matcher) has no "this segment only" wildcard, so `*` would also
    match every file under every subdirectory component and collide
    with its `**` glob (`BootstrapComponent`'s own docstring has the
    measured incident this fixes)."""
    has_src = any(f.startswith("src/") for f in source_files)
    prefix = "src/" if has_src else ""
    rest_of: dict[str, str] = {}
    tops: set[str] = set()
    for f in source_files:
        rest = f[len(prefix) :] if prefix else f
        if prefix and not f.startswith(prefix):
            # A source file living outside src/ in an otherwise src-layout
            # repo (e.g. a top-level conftest-adjacent helper) -- treat
            # its own top segment as a component of its own rather than
            # silently dropping it.
            rest = f
        rest_of[f] = rest
        tops.add(rest.split("/")[0])

    single_top = next(iter(tops)) if len(tops) == 1 else None

    file_component: dict[str, str] = {}
    component_glob: dict[str, list[str]] = {}
    for f, rest in rest_of.items():
        segments = rest.split("/")
        if single_top is not None:
            if len(segments) > 2:
                sub = segments[1]
                comp_id = _sanitize_ident(f"{single_top}_{sub}")
                component_glob.setdefault(comp_id, [f"{prefix}{single_top}/{sub}/**"])
            else:
                comp_id = _sanitize_ident(f"{single_top}_root")
                component_glob.setdefault(comp_id, []).append(f)
        else:
            top = segments[0]
            comp_id = _sanitize_ident(top)
            component_glob.setdefault(comp_id, [f"{prefix}{top}/**"])
        file_component[f] = comp_id
    return file_component, component_glob


def _derive_flows(
    root: Path,
    all_tracked: tuple[str, ...],
    file_component: dict[str, str],
) -> tuple[BootstrapFlow, ...]:
    """Real `src -> dst` component import edges, aggregated from
    `frob.graph.imports.build_import_graph`'s file-level resolved-edge
    substrate (Python only -- see module docstring). An edge is counted
    only when BOTH endpoints are files this bootstrap assigned to a
    component (a resolved import into an excluded/test file, or one
    `build_import_graph` could not resolve at all, contributes nothing
    here -- silently dropping those would misrepresent absence-of-
    evidence as evidence-of-absence, but a flow model has no home for
    "unresolved" either, so it is left to `frob check --only sys`'s own
    SYS003 finding to surface case-by-case once the model exists)."""
    graph = build_import_graph(root, all_tracked)
    counts: dict[tuple[str, str], int] = {}
    for importer, targets in graph.edges.items():
        src_comp = file_component.get(importer)
        if src_comp is None:
            continue
        for target in targets:
            dst_comp = file_component.get(target)
            if dst_comp is None or dst_comp == src_comp:
                continue
            key = (src_comp, dst_comp)
            counts[key] = counts.get(key, 0) + 1
    return tuple(
        BootstrapFlow(src=src, dst=dst, edge_count=n)
        for (src, dst), n in sorted(counts.items())
    )


# frob:doc docs/commands/sys.md#frob-sys-init-t-2910
# frob:tests \
# tests/unit/strata/test_bootstrap.py::TestRenderedTextParsesAndElaborates.test_empty_m\
# odel_still_parses kind="unit"
def render_bootstrap_text(
    module_name: str,
    components: tuple[BootstrapComponent, ...],
    flows: tuple[BootstrapFlow, ...],
) -> str:
    """Render `components`/`flows` as deterministic `.strata` source text.
    Deliberately emits NO `may=` line, commented or otherwise -- see this
    module's own docstring for why a derived capability ceiling would
    defeat the point of a ceiling. Every node is declared `: trusted`
    (this bootstrap has no basis for distinguishing trust tiers from an
    import graph alone -- a human narrows this by hand, the same
    disclosed-default posture `_shrink.py`'s own module docstring takes
    for anything this repo's tooling cannot safely infer)."""
    lines: list[str] = [
        "// Generated by `frob sys init` (T-2910) -- a BOOTSTRAP skeleton,",
        "// not a maintained model. This file was derived once from this",
        "// repo's package layout and Python import graph:",
        "//   - node ids + `code=` globs: real directories in this repo",
        "//   - `flow` declarations: real import edges observed between them",
        "// Deliberately NOT emitted: any `may=` capability line. `may=` is",
        "// a ceiling meant to SHRINK a node's interface below what its code",
        "// does -- deriving it from observation would make it a rubber",
        "// stamp with no teeth. Run `frob check --only sys` and follow its",
        "// SYS100/SYS103 findings to declare `may=` by hand, node by node.",
        "// This file will never be regenerated by `sys init` (it refuses",
        "// once any `.strata` file exists) -- use `frob sys shrink` from",
        "// here on to tighten a stale `may=` declaration; widen by hand.",
        "",
        f"module {module_name}",
        "",
    ]
    for comp in components:
        lines.append(f"node {comp.id} : trusted {{")
        glob_text = " ".join(f'"{g}"' for g in comp.code_globs)
        lines.append(f"    code {glob_text};")
        lines.append("}")
        lines.append("")
    for flow in flows:
        lines.append(
            f"flow f_{flow.src}_{flow.dst} : {flow.src} -> {flow.dst} "
            "{ label Internal; attr local; }"
        )
    if flows:
        lines.append("")
    return "\n".join(lines)


# frob:doc docs/commands/sys.md#frob-sys-init-t-2910
# frob:tests \
# tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelRefusesAnExistingModel.t\
# est_existing_design_files_lists_the_real_files kind="unit"
def existing_design_files(
    root: Path, design_dir: str = DEFAULT_DESIGN_DIR
) -> tuple[Path, ...]:
    """Every `.strata` file already present under `root/design_dir`
    (recursively) -- `derive_bootstrap_model`'s own refuse-if-nonempty
    check, factored out so `frob.app.sys_runner` can print exactly which
    files caused the refusal."""
    design_path = root / design_dir
    if not design_path.is_dir():
        return ()
    # frob:waive WALK001 reason="design_path (e.g. design/) is a small, hand-authored \
    # .strata source subtree with no nested .git/.venv/node_modules/build/dist/target \
    # to prune -- excludes.walk_pruned would add a filter that never fires here, not \
    # change behavior, same posture _shrink.py's own identical design_root.rglob call \
    # already documents"
    return tuple(sorted(design_path.rglob("*.strata")))


# frob:doc docs/commands/sys.md#frob-sys-init-t-2910
# frob:tests \
# tests/unit/strata/test_bootstrap.py::TestDeriveBootstrapModelRefusesAnExistingModel.t\
# est_refuses_when_a_strata_file_already_exists kind="unit"
def derive_bootstrap_model(
    root: Path, design_dir: str = DEFAULT_DESIGN_DIR
) -> Result[BootstrapModel, StrataError]:
    """Derive a `BootstrapModel` for the repo at `root`. Refuses
    (`Err(StrataError.DuplicateId)` -- reusing the closed vocabulary's
    closest existing "something is already there and this would
    collide" member rather than adding a bespoke one-off variant for a
    single caller) when `existing_design_files` is non-empty: this is a
    ONE-TIME bootstrap for a model-less repo, never a sync (module
    docstring). Returns `Ok` with an empty `components`/`flows` and
    `scanned_file_count == 0` -- never a silent crash -- for a repo with
    no tracked Python source at all; the caller decides whether that is
    worth reporting as a no-op."""
    if existing_design_files(root, design_dir):
        return Err(StrataError.DuplicateId)
    all_tracked = tracked_files(root, caller="sys_init")
    source_files = [f for f in all_tracked if _is_source_python(f)]
    module_name = _module_name_for(root)
    if not source_files:
        _log.info(
            "sys init: %s has no trackable Python source; nothing to derive", root
        )
        return Ok(
            BootstrapModel(
                module_name=module_name,
                components=(),
                flows=(),
                text=render_bootstrap_text(module_name, (), ()),
                scanned_file_count=len(all_tracked),
            )
        )
    file_component, component_glob = _group_components(source_files)
    counts: dict[str, int] = {}
    for comp in file_component.values():
        counts[comp] = counts.get(comp, 0) + 1
    components = tuple(
        BootstrapComponent(
            id=cid,
            code_globs=tuple(sorted(component_glob[cid])),
            file_count=counts[cid],
        )
        for cid in sorted(component_glob)
    )
    flows = _derive_flows(root, all_tracked, file_component)
    text = render_bootstrap_text(module_name, components, flows)
    _log.info(
        "sys init: derived %d component(s), %d flow(s) from %d source file(s) "
        "(%d tracked total)",
        len(components),
        len(flows),
        len(source_files),
        len(all_tracked),
    )
    return Ok(
        BootstrapModel(
            module_name=module_name,
            components=components,
            flows=flows,
            text=text,
            scanned_file_count=len(all_tracked),
        )
    )


# frob:doc docs/commands/sys.md#frob-sys-init-t-2910
# frob:tests \
# tests/unit/strata/test_bootstrap.py::TestWriteBootstrapModel.test_writes_module_named\
# _strata_file_under_design_dir kind="unit"
def write_bootstrap_model(
    root: Path, model: BootstrapModel, design_dir: str = DEFAULT_DESIGN_DIR
) -> Path:
    """Write `model.text` to `root/design_dir/<module_name>.strata`,
    creating `design_dir` if needed. Callers MUST have already confirmed
    (via `derive_bootstrap_model` returning `Ok`, which itself refuses on
    an existing model) that this is a genuine first write -- this
    function does not re-check `existing_design_files` itself, so it is
    never called from anywhere but `frob.app.sys_runner._run_init`
    immediately after a successful derive."""
    design_path = root / design_dir
    design_path.mkdir(parents=True, exist_ok=True)
    out_path = design_path / f"{model.module_name}.strata"
    out_path.write_text(model.text, encoding="utf-8")
    _log.info("sys init: wrote %s", out_path)
    return out_path
