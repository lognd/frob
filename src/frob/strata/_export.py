"""Kernel-model -> runtime-enforcement config exporters (T-0086).

Phase 5 applications (docs/strata/roadmap.md): the model is not just a
proof artifact, it compiles to config three different enforcement planes
already understand, so a static proof over the declared architecture is
backed by defense-in-depth that cannot silently diverge from it. Three
exporters, one `KernelModel` in, deterministic text out:

- `export_k8s_netpol`: one `NetworkPolicy` per component `Node`, ingress
  restricted to nodes with a declared `Flow` into it and egress to
  declared `Flow` targets only -- deny-by-default, the same posture
  kernel law 2 (`docs/strata/kernel.md`) already requires of the model
  itself. A `Flow` whose `src`/`dst` is a foreign-trust node has no pod
  to select in-cluster; that peer is annotated, not silently dropped
  (charter law 1) -- see `_FOREIGN_NOTE`.
- `export_seccomp`: one seccomp profile skeleton per `Node`, syscalls
  allowed only for the syscall families a declared `may` capability KIND
  maps to (`_SECCOMP_KIND_MAP`). This is a coarse v0 mapping (documented
  honestly below, not a real syscall-level audit) -- a `may` kind names a
  capability class, not an exact syscall list, so the mapping is
  necessarily approximate until the surface grammar can express finer
  atoms (same deferral `_effects.py` notes for capability targets).
- `export_iam`: one IAM statement per `Flow`, a generic, provider-agnostic
  JSON shape (no AWS/GCP/Azure-specific grammar; that translation is a
  follow-up, not this ticket's scope).

Every exporter is pure and total over its `KernelModel` input: no I/O, no
`Result` wrapping (same posture as `_report.py` -- there is no fallible
step in turning already-elaborated facts into text). Determinism (sorted
keys, stable ordering) is the whole point: two exports of the same model
byte-for-byte identical is what makes the output diffable and therefore
reviewable.
"""

from __future__ import annotations

import json

import yaml

from frob.logging import get_logger

from ._effects import _may_kind
from ._models import KernelModel, Node

_log = get_logger(__name__)

#: Annotation key placed on a k8s ingress/egress peer that names a
#: foreign-trust node -- there is no in-cluster pod to select for it, so the
#: rule is recorded rather than silently dropped.
_FOREIGN_NOTE = "frob.strata/foreign-peer"

#: `may` capability KIND -> allowed syscall family (v0, deliberately coarse:
#: a capability KIND is a class, not a syscall list -- see module docstring).
#: Kinds with no entry here allow nothing beyond the profile's baseline.
_SECCOMP_KIND_MAP: dict[str, tuple[str, ...]] = {
    "exec": ("execve", "execveat", "fork", "vfork", "clone"),
    "net": ("socket", "connect", "bind", "listen", "accept", "sendto", "recvfrom"),
}

#: Baseline syscalls every profile allows regardless of `may` capabilities --
#: a process cannot even start or exit cleanly without these.
_SECCOMP_BASELINE: tuple[str, ...] = (
    "exit",
    "exit_group",
    "read",
    "write",
    "close",
    "brk",
    "mmap",
    "munmap",
    "rt_sigreturn",
)


def _sorted_node_ids(model: KernelModel) -> list[str]:
    """Every node id in `model`, sorted -- the stable iteration order every
    exporter below builds its output in."""
    return sorted(node.id for node in model.nodes)


# frob:doc docs/commands/sys.md#frob-sys-export
# frob:tests tests/unit/strata/test_export.py::TestNodeSyscalls.test_base kind="unit"
def node_allowed_syscalls(node: Node) -> frozenset[str]:
    """Baseline + may-capability-derived allowed syscall set for one node
    (`_SECCOMP_KIND_MAP`) -- the ONE computation `export_seccomp` and
    `frob.deploy`'s systemd `SystemCallFilter` derivation (T-0257) both
    reuse, so a generated seccomp profile and a generated unit's
    `SystemCallFilter` can never desync (charter law: no duplication)."""
    kinds = {_may_kind(atom) for atom in node.may}
    allowed = set(_SECCOMP_BASELINE)
    for kind in kinds:
        allowed |= set(_SECCOMP_KIND_MAP.get(kind, ()))
    return frozenset(allowed)


def _node_by_id(model: KernelModel) -> dict[str, Node]:
    """`Node.id -> Node` lookup, built once per export call."""
    return {node.id: node for node in model.nodes}


def _flows_into(model: KernelModel, node_id: str) -> list[str]:
    """Sorted, de-duplicated `src` ids of every declared `Flow` into `node_id`."""
    return sorted({flow.src for flow in model.flows if flow.dst == node_id})


def _flows_out_of(model: KernelModel, node_id: str) -> list[str]:
    """Sorted, de-duplicated `dst` ids of every declared `Flow` out of `node_id`."""
    return sorted({flow.dst for flow in model.flows if flow.src == node_id})


def _netpol_peer(nodes: dict[str, Node], peer_id: str) -> dict:
    """One k8s `NetworkPolicyPeer` for `peer_id`: a pod selector in-cluster,
    or a `_FOREIGN_NOTE`-annotated stand-in when `peer_id` is foreign-trust
    (there is no pod to select in-cluster for it)."""
    peer = nodes.get(peer_id)
    if peer is not None and peer.trust == "foreign":
        return {_FOREIGN_NOTE: peer_id}
    return {"podSelector": {"matchLabels": {"app": peer_id}}}


# frob:doc docs/commands/sys.md#frob-sys-export
# frob:doc docs/guides/extending/sys-export-formats.md#sys-export-formats
def export_k8s_netpol(model: KernelModel) -> str:
    """Render one deny-by-default k8s `NetworkPolicy` YAML document per
    component `Node`: ingress only from nodes with a declared `Flow` into
    it, egress only to declared `Flow` targets (kernel law 2, no path the
    model does not declare). Deterministic (sorted node/peer order) so two
    exports of the same model are byte-identical."""
    nodes = _node_by_id(model)
    docs: list[dict] = []
    for node_id in _sorted_node_ids(model):
        ingress_from = _flows_into(model, node_id)
        egress_to = _flows_out_of(model, node_id)
        docs.append(
            {
                "apiVersion": "networking.k8s.io/v1",
                "kind": "NetworkPolicy",
                "metadata": {"name": f"frob-strata-{node_id}"},
                "spec": {
                    "podSelector": {"matchLabels": {"app": node_id}},
                    "policyTypes": ["Ingress", "Egress"],
                    "ingress": [
                        {"from": [_netpol_peer(nodes, src)]} for src in ingress_from
                    ],
                    "egress": [{"to": [_netpol_peer(nodes, dst)]} for dst in egress_to],
                },
            }
        )
    # yaml.safe_dump with sort_keys=True gives stable, diffable output;
    # multiple documents joined with the standard "---" separator.
    return "---\n".join(
        yaml.safe_dump(doc, sort_keys=True, default_flow_style=False) for doc in docs
    )


# frob:doc docs/commands/sys.md#frob-sys-export
def export_seccomp(model: KernelModel) -> str:
    """Render one seccomp profile skeleton (Docker/OCI default-action-errno
    shape) per component `Node`, JSON with sorted keys. Allowed syscalls are
    the baseline plus every family `_SECCOMP_KIND_MAP` maps a declared `may`
    capability KIND to; a node with no matching `may` kind gets only the
    baseline (deny by default, kernel law 2). v0's kind->syscall mapping is
    coarse -- documented in the module docstring, not a real syscall audit."""
    profiles: dict[str, dict] = {}
    for node in sorted(model.nodes, key=lambda n: n.id):
        allowed = node_allowed_syscalls(node)
        # frob:waive PERF004 reason="distinct allowed set per node, cannot hoist"
        profiles[node.id] = {
            "defaultAction": "SCMP_ACT_ERRNO",
            "syscalls": [
                {
                    "names": sorted(allowed),
                    "action": "SCMP_ACT_ALLOW",
                }
            ],
        }
    return json.dumps(profiles, indent=2, sort_keys=True)


# frob:doc docs/commands/sys.md#frob-sys-export
def export_iam(model: KernelModel) -> str:
    """Render one generic, provider-agnostic IAM policy document (JSON, sorted
    keys): two statements per declared `Flow` -- `src` gets a `write`
    statement on `dst` (the flow changes the destination's state) and a
    `read` statement on `dst` (the flow's caller reads whatever response the
    destination returns). This is the coarsest honest mapping: flow
    direction is the only signal the kernel model carries for IAM action
    inference today (a real read-vs-write split needs an explicit flow
    attribute the surface grammar does not yet have -- follow-up work, not
    this ticket's scope, see the Done report)."""
    statements: list[dict] = []
    # frob:waive PERF004 reason="sorted() is the loop's iterable, called once"
    for flow in sorted(model.flows, key=lambda f: f.id):
        statements.append(
            {
                "sid": f"{flow.id}-write",
                "effect": "Allow",
                "principal": flow.src,
                "action": "write",
                "resource": flow.dst,
            }
        )
        statements.append(
            {
                "sid": f"{flow.id}-read",
                "effect": "Allow",
                "principal": flow.src,
                "action": "read",
                "resource": flow.dst,
            }
        )
    document = {
        "version": "2026-07-18",
        "statements": sorted(statements, key=lambda s: s["sid"]),
    }
    return json.dumps(document, indent=2, sort_keys=True)
