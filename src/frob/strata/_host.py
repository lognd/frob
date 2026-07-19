"""`std.host`: OS-layer modeling for the strata kernel (T-0255,
docs/strata/host.md).

Foundation of the deploy epic (T-0254). A node/store may declare `runs_as
"svc-name"` (a dedicated OS service user), `unit` (bare marker: this
node's process is modeled as a systemd unit), `owns "PATH" "MODE"`
(filesystem ownership, repeatable), and `listens PORT` (a bound socket,
repeatable) -- `strata-core/src/parse.rs`'s `parse_node`/`parse_store`.
Charter law 1 (a vocabulary is a pure function surface -> kernel facts):
none of this grows `KernelModel`/`Node` with a new field. Instead, exactly
like `code`/`may`/`carries`/`managed` before it, each clause desugars to a
plain `Node.attrs` string (`_elaborate.py::_elaborate_node`, `_infra.py::
_elaborate_store`) -- `host_attrs` here is the ONE place that encoding is
written, imported by both elaborators so the convention cannot desync
between node and store.

`host_manifest_for` is the read-back half: it reads a `Node`'s attrs (of
EITHER origin, node or store -- a store is a node too, docs/strata/
surface.md#key-construct-semantics) into one typed, platform-tagged
`HostManifest`. This is the manifest T-0256 (generator), T-0257 (flow
proofs over service-user identity), T-0258 (conformance checker), and
T-0259 (VM auditor) all consume -- one parse of the attr convention, not
four. `platform` is a discriminator reserved for T-0261 (windows): only
`HostPlatform.LINUX_SYSTEMD` is produced today (the only grammar and
elaborator this ticket builds), but every downstream consumer must already
branch on `platform`, so adding a second platform later is additive, not a
rewrite of every consumer.

OS users joining the trust lattice: today that participation is exactly
the `runs_as=<name>` attr any of T-0257's flow machinery can already read
off a `Node` like any other attr -- there is no dedicated lattice
plumbing here (no proofs, per this ticket's explicit scope cut). Actually
model-checking flows BETWEEN service users (mapping `runs_as` identities
onto trust-lattice participants with their own crossing obligations) is
T-0257's job, not this manifest's.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

from ._models import Node

_log = get_logger(__name__)

#: `runs_as=<name>` attr prefix -- the SAME per-atom `key=value` attr
#: convention `_code_binding.py::_CODE_PREFIX`/`_pii.py::_PII_PREFIX` use.
_RUNS_AS_PREFIX = "runs_as="

#: `unit` bare-marker attr -- mirrors `_elaborate.py::_MANAGED_ATTR`'s shape.
_UNIT_ATTR = "unit"

#: `owns=<path>:<mode>` attr prefix, one per declared `owns` entry.
_OWNS_PREFIX = "owns="

#: `listens=<port>` attr prefix, one per declared `listens` entry.
_LISTENS_PREFIX = "listens="


# frob:doc docs/strata/host.md#hostmanifest
class HostPlatform(StrEnum):
    """The OS/init-system target a `HostManifest`'s directives are shaped for.

    Reserved discriminator (T-0261 adds `WINDOWS`); only `LINUX_SYSTEMD` is
    produced by this ticket's grammar and elaborator.
    """

    LINUX_SYSTEMD = "linux-systemd"


# frob:doc docs/strata/host.md#hostmanifest
class HostOwns(BaseModel):
    """One `owns=<path>:<mode>` desugared attr, read back as a typed path/mode pair."""

    model_config = ConfigDict(frozen=True)

    path: str
    mode: str


# frob:doc docs/strata/host.md#hostmanifest
class HostManifest(BaseModel):
    """The OS-layer facts `std.host` desugars a node/store's attrs into (T-0255).

    ONE platform-tagged model every deploy-epoch ticket reads instead of
    re-parsing `Node.attrs` itself (module docstring). Manifest only: no
    generator (T-0256), no proofs over `runs_as` identity (T-0257) are
    built here.
    """

    model_config = ConfigDict(frozen=True)

    platform: HostPlatform
    runs_as: str | None = None
    is_unit: bool = False
    owns: tuple[HostOwns, ...] = ()
    listens: tuple[int, ...] = ()


# frob:doc docs/strata/host.md#surface-grammar
# frob:tests tests/unit/strata/test_host.py::TestHostAttrs.test_desugars kind="unit"
def host_attrs(
    *,
    runs_as: str | None,
    is_unit: bool,
    owns: tuple[tuple[str, str], ...],
    listens: tuple[int, ...],
) -> tuple[str, ...]:
    """Desugar parsed std.host clauses into `Node.attrs` strings.

    The ONE encoding both `_elaborate.py::_elaborate_node` (node) and
    `_infra.py::_elaborate_store` (store) call, so the attr convention
    cannot desync between the two callers (charter law 5: no duplication).
    """
    attrs: list[str] = []
    if runs_as is not None:
        attrs.append(f"{_RUNS_AS_PREFIX}{runs_as}")
    if is_unit:
        attrs.append(_UNIT_ATTR)
    attrs.extend(f"{_OWNS_PREFIX}{path}:{mode}" for path, mode in owns)
    attrs.extend(f"{_LISTENS_PREFIX}{port}" for port in listens)
    return tuple(attrs)


# frob:doc docs/strata/host.md#hostmanifest
# frob:tests tests/unit/strata/test_host.py::TestHostManifest.test_reads kind="unit"
def host_manifest_for(node: Node) -> HostManifest | None:
    """Read a `Node`'s std.host attrs back into a typed `HostManifest`.

    Returns `None` when the node declares no std.host construct at all
    (no `runs_as`/`unit`/`owns`/`listens` attr present) -- a node with no
    host-layer facts has no manifest to generate from, distinct from an
    empty-but-present one. Mirrors `_pii.py::node_pii_tags`'s attr
    read-back shape.
    """
    runs_as: str | None = None
    is_unit = False
    owns: list[HostOwns] = []
    listens: list[int] = []
    declared = False
    for attr in node.attrs:
        if attr.startswith(_RUNS_AS_PREFIX):
            runs_as = attr[len(_RUNS_AS_PREFIX) :]
            declared = True
        elif attr == _UNIT_ATTR:
            is_unit = True
            declared = True
        elif attr.startswith(_OWNS_PREFIX):
            path, _, mode = attr[len(_OWNS_PREFIX) :].partition(":")
            owns.append(HostOwns(path=path, mode=mode))
            declared = True
        elif attr.startswith(_LISTENS_PREFIX):
            listens.append(int(attr[len(_LISTENS_PREFIX) :]))
            declared = True
    if not declared:
        return None
    _log.debug(
        "node %s: host manifest runs_as=%r unit=%s owns=%d listens=%d",
        node.id,
        runs_as,
        is_unit,
        len(owns),
        len(listens),
    )
    return HostManifest(
        platform=HostPlatform.LINUX_SYSTEMD,
        runs_as=runs_as,
        is_unit=is_unit,
        owns=tuple(owns),
        listens=tuple(listens),
    )
