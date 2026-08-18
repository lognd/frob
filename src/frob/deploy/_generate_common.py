"""Shared manifest-walk primitives for `frob.deploy._generate` (Linux/bash)
and `frob.deploy._generate_windows` (PowerShell) -- split out (T-2358) so
neither renderer module has to import FROM the other. Before this split,
`_generate_windows.py` imported `DIGEST_HEADER_PREFIX`/`ManifestEntry`/
`manifest_digest`/`sorted_manifest_entries` from `_generate.py`, while
`_generate.py::generate_all` needed `_generate_windows.py`'s own
Windows-specific renderers -- a genuine two-module import cycle, worked
around with a function-local deferred import (`generate_all`'s own
docstring used to document it) rather than fixed at the root. `frob
check --only cycle` still reported the cycle despite the deferred
import (a deferred import hides a cycle from a NAIVE top-level-only
scanner, but this repo's detector walks into function bodies too, so it
correctly kept flagging the real coupling) -- moving the shared pieces
here, with both renderer modules depending on this common module and
neither depending on the other, is the structural fix the cycle gate's
own guidance recommends (a shared helper wanting its own module), not a
second attempt to hide the same coupling."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger
from frob.strata import (
    HostManifest,
    KernelModel,
    Node,
    node_allowed_syscalls,
    node_may_kinds,
)
from frob.strata._host import host_manifest_for

_log = get_logger(__name__)

# frob:doc docs/strata/host.md#the-deploy-generator
#: Header line every generated script carries. `_drift.py`'s DEPLOY001
#: check does not grep for this prefix specifically -- it compares full
#: script bodies -- but every generated script's header opens with it, so
#: it is documented as part of that generated-script shape.
DIGEST_HEADER_PREFIX = "# frob-deploy-manifest-digest: "

#: `may` capability KIND -> Linux capability name(s) a generated unit's
#: `CapabilityBoundingSet=` grants. Deliberately coarse (same honesty
#: posture `_export.py::_SECCOMP_KIND_MAP` documents for syscalls): a
#: `may` kind names a capability CLASS, not an exact Linux capability,
#: until the surface grammar can express finer atoms. Kinds with no entry
#: grant nothing beyond the empty (most restrictive) bounding set.
_CAP_KIND_MAP: dict[str, tuple[str, ...]] = {
    "net": ("CAP_NET_BIND_SERVICE",),
}

#: Ports below this number require `CAP_NET_BIND_SERVICE` on Linux (the
#: kernel's own privileged-port cutoff, `ip_unprivileged_port_start`'s
#: default). T-0281 item 8 (malmberg pilot finding): a node's `may net`
#: previously granted `CAP_NET_BIND_SERVICE` unconditionally, even when
#: every declared `listens` port is unprivileged -- an over-grant
#: `_node_capabilities` below now gates on this cutoff instead.
_PRIVILEGED_PORT_CUTOFF = 1024


# frob:doc docs/strata/host.md#the-deploy-generator
# frob:tests tests/unit/deploy/test_generate.py::TestSorted.test_sorted kind="unit"
class ManifestEntry(BaseModel):
    """One node id's `HostManifest`, paired for deterministic iteration
    (`sorted_manifest_entries`) -- the one shape every renderer walks
    instead of re-deriving node-id -> manifest pairs itself."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    manifest: HostManifest
    capabilities: tuple[str, ...]
    syscalls: tuple[str, ...]


def _node_capabilities(node: Node, manifest: HostManifest) -> frozenset[str]:
    """`CapabilityBoundingSet=` members for `node`, derived from the SAME
    `may`-kind join `node_allowed_syscalls` uses for `SystemCallFilter=`
    (`_CAP_KIND_MAP`, module docstring) -- never a second, independently
    maintained kind mapping.

    T-0281 item 8 (malmberg pilot finding): `CAP_NET_BIND_SERVICE` is only
    a real requirement when the manifest actually binds a PRIVILEGED port
    (`_PRIVILEGED_PORT_CUTOFF`) -- a `may net` node whose every declared
    `listens` port is >=1024 (or that declares no `listens` at all) never
    needs it, so granting it unconditionally was an over-grant. Other
    `_CAP_KIND_MAP` kinds (should the map grow) are unaffected by this
    port gate -- it applies to `CAP_NET_BIND_SERVICE` specifically, the
    one Linux capability whose need is itself port-dependent.

    T-1006: `node_may_kinds` returns T-0717 mode-qualified `family.mode`
    ids (e.g. `"net.out"`), not the bare coarse family `_CAP_KIND_MAP` is
    keyed by (`"net"`) -- a node declaring only a precise mode-qualified
    `may` atom used to silently match nothing here and lose its
    capability grant entirely. Look up `_CAP_KIND_MAP` by the family
    prefix (the segment before the first `.`, `_mode_qualified`'s own
    join character) so both a bare coarse declaration and a precise
    mode-qualified one resolve to the same capability grant."""
    needs_privileged_bind = any(
        port < _PRIVILEGED_PORT_CUTOFF for port in manifest.listens
    )
    caps: set[str] = set()
    for kind in node_may_kinds(node):
        family = kind.split(".", 1)[0]
        for cap in _CAP_KIND_MAP.get(family, ()):
            if cap == "CAP_NET_BIND_SERVICE" and not needs_privileged_bind:
                continue
            caps.add(cap)
    return frozenset(caps)


# frob:doc docs/strata/host.md#the-deploy-generator
# frob:tests tests/unit/deploy/test_generate.py::TestSorted.test_sorted kind="unit"
def sorted_manifest_entries(model: KernelModel) -> tuple[ManifestEntry, ...]:
    """Every node/store in `model` with a declared `std.host` manifest,
    sorted by node id -- the ONE deterministic walk `manifest_digest` and
    every script renderer share, so two calls over the same model always
    see facts in the same order (determinism is what makes the digest
    and the generated bash/PowerShell byte-for-byte reproducible)."""
    entries: list[ManifestEntry] = []
    # frob:waive PERF004 reason="sorted() is this loop's own iterable, not repeated"
    for node in sorted(model.nodes, key=lambda n: n.id):
        manifest = host_manifest_for(node)
        if manifest is None:
            continue
        entries.append(
            ManifestEntry(
                node_id=node.id,
                manifest=manifest,
                capabilities=tuple(
                    sorted(_node_capabilities(node, manifest)),
                ),
                syscalls=tuple(sorted(node_allowed_syscalls(node))),
            )
        )
    return tuple(entries)


# frob:doc docs/strata/host.md#the-deploy-generator
# frob:tests tests/unit/deploy/test_generate.py::TestDigest.test_det kind="unit"
def manifest_digest(model: KernelModel) -> str:
    """sha256 over a deterministic JSON serialization of every declared
    `HostManifest`, keyed by node id -- the DEPLOY001 drift lock's join
    key (`_drift.py`). Two `KernelModel`s with identical host facts,
    built in any order, always produce the same digest; anything else
    (a manifest added/removed/changed) always produces a different one."""
    entries = sorted_manifest_entries(model)
    payload = {
        entry.node_id: {
            "manifest": entry.manifest.model_dump(mode="json"),
            "capabilities": list(entry.capabilities),
            "syscalls": list(entry.syscalls),
        }
        for entry in entries
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
