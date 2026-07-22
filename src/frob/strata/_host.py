"""`std.host`: OS-layer modeling for the strata kernel (T-0255,
docs/strata/host.md).

Foundation of the deploy epic (T-0254). A node/store may declare `runs_as
"svc-name"` (a dedicated OS service user), `unit` (bare marker: this
node's process is modeled as a systemd unit), `owns "PATH" "MODE"`
(filesystem ownership, repeatable), `listens PORT` (a bound socket,
repeatable), `group "NAME"` (OS-group membership, repeatable, T-0272),
and `sudoers "RULE"` (a sudoers grant line, repeatable, T-0272) --
`strata-core/src/parse.rs`'s `parse_node`/`parse_store`. `group`/
`sudoers` close the honest gap `_host_isolation.py`'s module docstring
documented: HOST001's shared-group and HOST002's sudoers sub-targets can
now derive real findings from `HostManifest.group`/`HostManifest.
sudoers` instead of always firing.
Charter law 1 (a vocabulary is a pure function surface -> kernel facts):
none of this grows `KernelModel`/`Node` with a new field. Instead, exactly
like `code`/`may`/`carries`/`managed` before it, each clause desugars to a
plain `Node.attrs` string (`_elaborate.py::_elaborate_node`, `_infra.py::
_elaborate_store`) -- `_host_attrs` here is the ONE place that encoding is
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
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/strata/_host.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator

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

#: `group=<name>` attr prefix, one per declared `group` entry (T-0272) --
#: the SAME per-atom `key=value` attr convention `_OWNS_PREFIX`/
#: `_LISTENS_PREFIX` use, owns-adjacent per the ticket's grammar shape.
_GROUP_PREFIX = "group="

#: `sudoers=<rule>` attr prefix, one per declared `sudoers` entry (T-0272).
_SUDOERS_PREFIX = "sudoers="

#: Well-formed LINUX_SYSTEMD `owns` MODE: 3-4 octal digits (0-7), matching
#: `chmod`'s own permission-string shape -- a 4th digit carries setuid/
#: setgid/sticky (docs/strata/host.md#the-honest-gap: a 4-digit
#: `owns "PATH" "4755"` mode is how HOST002 sees a setuid path, with no
#: separate grammar needed). T-0270 (deferred from T-0255): a MODE that
#: does not match this is rejected at `HostOwns` construction time, not
#: silently stored.
_MODE_RE = re.compile(r"[0-7]{3,4}")

#: Valid TCP/UDP port range a `listens` PORT must fall in. T-0270
#: (deferred from T-0255): out-of-range or non-numeric PORTs are rejected
#: at `HostManifest` construction time, not silently stored.
_MIN_PORT = 1
_MAX_PORT = 65535


# frob:doc docs/strata/host.md#hostmanifest
class HostPlatform(StrEnum):
    """The OS/init-system target a `HostManifest`'s directives are shaped for.

    Reserved discriminator (T-0261 adds `WINDOWS`); only `LINUX_SYSTEMD` is
    produced by this ticket's grammar and elaborator.
    """

    LINUX_SYSTEMD = "linux-systemd"


# frob:doc docs/strata/host.md#hostmanifest
class HostOwns(BaseModel):
    """One `owns=<path>:<mode>` desugared attr, read back as a typed path/mode pair.

    `mode` stays a bare string, not a stricter octal-int type: it is
    platform-opaque by design (POSIX octal today, e.g. `"0644"`; a Windows
    ACL/SDDL string once T-0261 lands), so the generic string type here is
    deliberate genericity, not an oversight. T-0270: on `HostPlatform.
    LINUX_SYSTEMD` (the only platform this module elaborates today), the
    STRING'S SHAPE is still validated -- 3-4 octal digits, `_MODE_RE` --
    at construction time, so a bogus mode (`"999"`, `"rwx"`) fails closed
    instead of being stored raw. A future Windows SDDL string gets its own
    platform-tagged validator when T-0261 lands, not a relaxation of this
    one.
    """

    model_config = ConfigDict(frozen=True)

    path: str
    mode: str

    # frob:ticket T-0565
    # frob:tests tests/unit/strata/test_host.py::TestHostOwnsModeValidation.test_valid_octal_mode_accepted  # noqa: E501
    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, value: str) -> str:
        """Reject an `owns` MODE that is not 3-4 well-formed octal digits
        (e.g. `0644`, `0755`, or 4-digit `4755` for a setuid bit) -- a
        non-octal (`rwx`) or out-of-range (`999`) mode is a malformed
        manifest, not a silently-accepted one (T-0270, deferred from
        T-0255)."""
        if _MODE_RE.fullmatch(value) is None:
            raise ValueError(
                f"owns MODE {value!r} is not well-formed octal permissions "
                "(expected 3-4 digits, each 0-7, e.g. '0644' or '0755')"
            )
        return value


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
    # T-0270 (deferred from T-0255): each PORT is validated to fall in
    # 1-65535 at construction time (`_validate_listens` below). Still
    # open, deliberately NOT this ticket's scope: a privileged-port
    # (<1024, CAP_NET_BIND_SERVICE) check, and a duplicate-port check
    # across nodes sharing a host -- both are cross-manifest concerns,
    # not a single manifest's well-formedness.
    listens: tuple[int, ...] = ()
    # T-0272: OS groups this manifest's `runs_as` user is a member of,
    # and sudoers grants held by that user -- the grammar HOST001's
    # shared-group and HOST002's sudoers sub-targets needed to stop
    # always-firing (docs/strata/host.md#the-honest-gap, module docstring
    # of `_host_isolation.py`). Both plain string tuples, same "opaque
    # atom" shape `owns`'s mode/`listens`'s port neighbors use -- a group
    # name and a sudoers rule line are free-form platform text, not
    # structured data this manifest needs to interpret further.
    group: tuple[str, ...] = ()
    sudoers: tuple[str, ...] = ()

    # frob:ticket T-0565
    # frob:tests tests/unit/strata/test_host.py::TestHostManifestListensValidation.test_valid_port_accepted  # noqa: E501
    @field_validator("listens")
    @classmethod
    def _validate_listens(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        """Reject any `listens` PORT outside the valid TCP/UDP range
        1-65535 -- an out-of-range port (e.g. `70000`) is a malformed
        manifest, not a silently-accepted one (T-0270, deferred from
        T-0255)."""
        for port in value:
            if not _MIN_PORT <= port <= _MAX_PORT:
                raise ValueError(
                    f"listens PORT {port} is out of range {_MIN_PORT}-{_MAX_PORT}"
                )
        return value


# frob:tests tests/unit/strata/test_host.py::TestHostAttrs.test_desugars kind="unit"
def _host_attrs(
    *,
    runs_as: str | None,
    is_unit: bool,
    owns: tuple[tuple[str, str], ...],
    listens: tuple[int, ...],
    group: tuple[str, ...] = (),
    sudoers: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """Desugar parsed std.host clauses into `Node.attrs` strings.

    The ONE encoding both `_elaborate.py::_elaborate_node` (node) and
    `_infra.py::_elaborate_store` (store) call, so the attr convention
    cannot desync between the two callers (charter law 5: no duplication).
    `group`/`sudoers` (T-0272) default to empty so existing callers built
    against the pre-T-0272 four-argument shape keep working unchanged.
    """
    attrs: list[str] = []
    if runs_as is not None:
        attrs.append(f"{_RUNS_AS_PREFIX}{runs_as}")
    if is_unit:
        attrs.append(_UNIT_ATTR)
    attrs.extend(f"{_OWNS_PREFIX}{path}:{mode}" for path, mode in owns)
    attrs.extend(f"{_LISTENS_PREFIX}{port}" for port in listens)
    attrs.extend(f"{_GROUP_PREFIX}{name}" for name in group)
    attrs.extend(f"{_SUDOERS_PREFIX}{rule}" for rule in sudoers)
    return tuple(attrs)


class _ParsedHostAttrs:
    """Mutable accumulator for `_parse_host_attrs` -- one pass over
    `node.attrs`, fields filled in the same order the attrs are read."""

    def __init__(self) -> None:
        self.runs_as: str | None = None
        self.is_unit = False
        self.owns: list[HostOwns] = []
        self.listens: list[int] = []
        self.group: list[str] = []
        self.sudoers: list[str] = []
        self.declared = False


def _parse_host_attrs(node: Node) -> _ParsedHostAttrs:
    """Single pass over `node.attrs`, splitting each std.host-prefixed attr
    into `_ParsedHostAttrs` fields -- the parse step `host_manifest_for`
    reads back into a typed `HostManifest`."""
    parsed = _ParsedHostAttrs()
    for attr in node.attrs:
        if attr.startswith(_RUNS_AS_PREFIX):
            parsed.runs_as = attr[len(_RUNS_AS_PREFIX) :]
            parsed.declared = True
        elif attr == _UNIT_ATTR:
            parsed.is_unit = True
            parsed.declared = True
        elif attr.startswith(_OWNS_PREFIX):
            path, _, mode = attr[len(_OWNS_PREFIX) :].partition(":")
            parsed.owns.append(HostOwns(path=path, mode=mode))
            parsed.declared = True
        elif attr.startswith(_LISTENS_PREFIX):
            port_str = attr[len(_LISTENS_PREFIX) :]
            try:
                port = int(port_str)
            except ValueError as exc:
                # T-0270: a non-numeric PORT (e.g. "abc") fails closed with
                # a clear message, not a raw int()-parse traceback.
                raise ValueError(
                    f"listens PORT {port_str!r} is not a valid integer"
                ) from exc
            parsed.listens.append(port)
            parsed.declared = True
        elif attr.startswith(_GROUP_PREFIX):
            parsed.group.append(attr[len(_GROUP_PREFIX) :])
            parsed.declared = True
        elif attr.startswith(_SUDOERS_PREFIX):
            parsed.sudoers.append(attr[len(_SUDOERS_PREFIX) :])
            parsed.declared = True
    return parsed


# frob:doc docs/strata/host.md#hostmanifest
# frob:tests tests/unit/strata/test_host.py::TestHostManifest.test_reads kind="unit"
def host_manifest_for(node: Node) -> HostManifest | None:
    """Read a `Node`'s std.host attrs back into a typed `HostManifest`.

    Returns `None` when the node declares no std.host construct at all
    (no `runs_as`/`unit`/`owns`/`listens` attr present) -- a node with no
    host-layer facts has no manifest to generate from, distinct from an
    empty-but-present one. Mirrors `_pii.py::node_pii_tags`'s attr
    read-back shape.

    T-0270 (deferred from T-0255): this is elaborate/read-back time, not
    `strata-core/src/parse.rs`'s grammar-parse time -- MODE/PORT stay
    platform-agnostic atoms through the grammar, and are only validated
    here where the platform (`HostPlatform.LINUX_SYSTEMD`) is known.
    Raises `pydantic.ValidationError` (via `HostOwns`/`HostManifest`'s
    field validators) or a plain `ValueError` (non-numeric PORT) for a
    malformed MODE/PORT -- fails closed rather than silently storing
    bogus OS-layer facts a downstream consumer (T-0256/T-0257/T-0258/
    T-0259) would otherwise trust.
    """
    parsed = _parse_host_attrs(node)
    if not parsed.declared:
        return None
    _log.debug(
        "node %s: host manifest runs_as=%r unit=%s owns=%d listens=%d "
        "group=%d sudoers=%d",
        node.id,
        parsed.runs_as,
        parsed.is_unit,
        len(parsed.owns),
        len(parsed.listens),
        len(parsed.group),
        len(parsed.sudoers),
    )
    return HostManifest(
        platform=HostPlatform.LINUX_SYSTEMD,
        runs_as=parsed.runs_as,
        is_unit=parsed.is_unit,
        owns=tuple(parsed.owns),
        listens=tuple(parsed.listens),
        group=tuple(parsed.group),
        sudoers=tuple(parsed.sudoers),
    )
