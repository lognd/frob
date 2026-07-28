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
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/strata/_design_load.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from frob.excludes import is_excluded, iter_files, load_exclude_globs
from frob.graph import EdgeKind, GraphSnapshot
from frob.logging import get_logger

from ._elaborate import elaborate
from ._errors import StrataError
from ._models import KernelModel
from ._parse import parse_module

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
#: `tests/test_gates.py::TestSysGate::test_default_design_dir_mirror_stays_in_sync`.
# frob:doc docs/strata/surface.md#directives-t-0080
DEFAULT_DESIGN_DIR = "design"


# frob:doc docs/strata/surface.md#directives-t-0080
@dataclass(frozen=True)
class DesignLoadError:
    """One `.strata` file that failed to parse or elaborate, kept for reporting."""

    path: str
    error: StrataError


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
    set[str], set[str], set[str], set[str], list[DesignLoadError], list[KernelModel]
]:
    """Load+merge every `.strata` file in `paths`; per-file failures collect
    into the returned errors list rather than aborting the whole load."""
    channels: set[str] = set()
    boundaries: set[str] = set()
    secrets: set[str] = set()
    store_ids: set[str] = set()
    errors: list[DesignLoadError] = []
    models: list[KernelModel] = []
    for path in paths:
        model, file_store_ids, error = _load_one_design_file(root, path)
        if error is not None:
            errors.append(error)
            continue
        assert model is not None
        models.append(model)
        channels.update(flow.id for flow in model.flows)
        boundaries.update(boundary.id for boundary in model.boundaries)
        secrets.update(node.id for node in model.nodes if node.clearance == "Secret")
        store_ids.update(file_store_ids)
    return channels, boundaries, secrets, store_ids, errors, models


def _load_one_design_file(
    root: Path, path: Path
) -> (
    tuple[KernelModel, frozenset[str], None]
    | tuple[None, frozenset[str], DesignLoadError]
):
    """Read+parse+elaborate one `.strata` file; returns `(model, store_ids,
    None)` on success or `(None, frozenset(), error)` on any failure, never
    raising. `store_ids` (T-0724) is read off the PARSED `Module.stores`
    before `elaborate` folds each store into a plain `Node` -- the only
    point at which "this node id came from a `store` construct" is still a
    reconstructible fact (`_contention.py` module docstring)."""
    rel = path.relative_to(root).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning("load_design_ids: could not read %s: %s", rel, exc)
        return (
            None,
            frozenset(),
            DesignLoadError(path=rel, error=StrataError.ParseFailed),
        )
    parsed = parse_module(text)
    if parsed.is_err:
        _log.warning("load_design_ids: %s failed to parse: %s", rel, parsed.danger_err)
        return None, frozenset(), DesignLoadError(path=rel, error=parsed.danger_err)
    store_ids = frozenset(store.id for store in parsed.danger_ok.stores)
    elaborated = elaborate(parsed.danger_ok)
    if elaborated.is_err:
        _log.warning(
            "load_design_ids: %s failed to elaborate: %s",
            rel,
            elaborated.danger_err,
        )
        return None, store_ids, DesignLoadError(path=rel, error=elaborated.danger_err)
    return elaborated.danger_ok, store_ids, None


# frob:doc docs/strata/surface.md#directives-t-0080
# frob:ticket T-0080
# frob:tests tests/unit/strata/test_design_load.py::TestLoadIds.test_merges_ids
# frob:tests tests/unit/strata/test_design_load.py::TestLoadIds.test_no_dir_empty
# frob:tests tests/unit/strata/test_design_load.py::TestLoadIds.test_bad_file_reported
# frob:tests tests/unit/strata/test_design_load.py::TestLoadIds.test_excluded_no_ids
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
    channels, boundaries, secrets, store_ids, errors, models = _load_all_design_files(
        root, paths
    )

    _log.info(
        "load_design_ids: %d channel(s), %d boundary(ies), %d secret(s), "
        "%d store(s), %d error(s)",
        len(channels),
        len(boundaries),
        len(secrets),
        len(store_ids),
        len(errors),
    )
    return DesignIds(
        channels=frozenset(channels),
        boundaries=frozenset(boundaries),
        secrets=frozenset(secrets),
        errors=tuple(errors),
        models=tuple(models),
        store_ids=frozenset(store_ids),
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
        # frob:waive PERF004 reason="ids_by_kind.get(kind, ...) is this loop's own per-kind distinct set, not a shared re-sort"  # noqa: E501
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
