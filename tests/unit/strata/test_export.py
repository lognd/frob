"""Unit tests for strata kernel-model exporters (docs/commands/sys.md#export,
T-0086): k8s NetworkPolicy, seccomp profile skeletons, IAM policy skeletons.
"""

from __future__ import annotations

import json

import yaml

from frob.strata import Flow, KernelModel, Node
from frob.strata._export import (
    export_iam,
    export_k8s_netpol,
    export_seccomp,
    node_allowed_syscalls,
)


def _node(nid: str, trust: str = "trusted", **kw) -> Node:
    return Node(id=nid, trust=trust, **kw)


def _flow(fid: str, src: str, dst: str, **kw) -> Flow:
    return Flow(id=fid, src=src, dst=dst, **kw)


class TestExportK8sNetpol:
    """k8s NetworkPolicy exporter tests."""

    def test_deny_by_default(self) -> None:
        """A node with no declared flows gets empty ingress/egress lists,
        never an omitted (implicitly allow-all) rule set."""
        model = KernelModel(nodes=(_node("solo"),))
        docs = list(yaml.safe_load_all(export_k8s_netpol(model)))
        assert len(docs) == 1
        spec = docs[0]["spec"]
        assert spec["ingress"] == []
        assert spec["egress"] == []
        assert spec["policyTypes"] == ["Ingress", "Egress"]

    # frob:waive DUP001 reason="parallel test methods within test_export.py \
    # (2 sites) sharing an arrange-act scaffold typical of exhaustive \
    # per-case coverage; extracting would obscure per-case intent"
    def test_ingress_from_src(self) -> None:
        """dst's NetworkPolicy allows ingress only from src, matching the
        one declared Flow -- no other peer is ever implicitly allowed."""
        model = KernelModel(
            nodes=(_node("web"), _node("db")),
            flows=(_flow("f1", "web", "db"),),
        )
        docs = {
            d["metadata"]["name"]: d
            for d in yaml.safe_load_all(export_k8s_netpol(model))
        }
        db_ingress = docs["frob-strata-db"]["spec"]["ingress"]
        assert db_ingress == [
            {"from": [{"podSelector": {"matchLabels": {"app": "web"}}}]}
        ]

    # frob:waive DUP001 reason="parallel test methods within test_export.py \
    # (2 sites) sharing an arrange-act scaffold typical of exhaustive \
    # per-case coverage; extracting would obscure per-case intent"
    def test_egress_to_dst(self) -> None:
        """src's NetworkPolicy allows egress only to dst, matching the one
        declared Flow."""
        model = KernelModel(
            nodes=(_node("web"), _node("db")),
            flows=(_flow("f1", "web", "db"),),
        )
        docs = {
            d["metadata"]["name"]: d
            for d in yaml.safe_load_all(export_k8s_netpol(model))
        }
        web_egress = docs["frob-strata-web"]["spec"]["egress"]
        assert web_egress == [{"to": [{"podSelector": {"matchLabels": {"app": "db"}}}]}]

    def test_foreign_peer(self) -> None:
        """A flow whose src is a foreign-trust node has no in-cluster pod to
        select; the peer is annotated (not silently omitted)."""
        model = KernelModel(
            nodes=(_node("registry", trust="foreign"), _node("vet")),
            flows=(_flow("f1", "registry", "vet"),),
        )
        docs = {
            d["metadata"]["name"]: d
            for d in yaml.safe_load_all(export_k8s_netpol(model))
        }
        vet_ingress = docs["frob-strata-vet"]["spec"]["ingress"]
        assert vet_ingress == [{"from": [{"frob.strata/foreign-peer": "registry"}]}]

    def test_stable(self) -> None:
        """Two exports of the same model are byte-for-byte identical."""
        # frob:tests src/frob/strata/_export.py::export_k8s_netpol kind="unit"
        model = KernelModel(
            nodes=(_node("a"), _node("b"), _node("c")),
            flows=(_flow("f1", "a", "b"), _flow("f2", "b", "c")),
        )
        assert export_k8s_netpol(model) == export_k8s_netpol(model)


class TestNodeSyscalls:
    # frob:tests src/frob/strata/_export.py::node_allowed_syscalls kind="unit"
    def test_base(self) -> None:
        node = _node("worker", may=("exec",))
        allowed = node_allowed_syscalls(node)
        assert "execve" in allowed
        assert "read" in allowed  # baseline
        assert "socket" not in allowed


class TestExportSeccomp:
    """seccomp profile exporter tests."""

    def test_no_may_baseline(self) -> None:
        """A node with no `may` atoms allows only the fixed baseline
        syscalls -- deny by default."""
        model = KernelModel(nodes=(_node("quiet"),))
        profiles = json.loads(export_seccomp(model))
        names = profiles["quiet"]["syscalls"][0]["names"]
        assert "execve" not in names
        assert "socket" not in names
        assert "read" in names  # baseline

    # frob:waive DUP001 reason="parallel test methods within test_export.py \
    # (2 sites) sharing an arrange-act scaffold typical of exhaustive \
    # per-case coverage; extracting would obscure per-case intent"
    def test_exec_allows_exec(self) -> None:
        """A `may=("exec",)` node's profile allows the exec syscall family."""
        model = KernelModel(nodes=(_node("worker", may=("exec",)),))
        profiles = json.loads(export_seccomp(model))
        names = profiles["worker"]["syscalls"][0]["names"]
        assert "execve" in names
        assert "socket" not in names

    # frob:waive DUP001 reason="parallel test methods within test_export.py \
    # (2 sites) sharing an arrange-act scaffold typical of exhaustive \
    # per-case coverage; extracting would obscure per-case intent"
    def test_net_allows_socket(self) -> None:
        """A `may=("net.out:stripe.com",)` node's profile allows the socket
        syscall family (kind extracted before the first `.`/`:`)."""
        model = KernelModel(nodes=(_node("payer", may=("net.out:stripe.com",)),))
        profiles = json.loads(export_seccomp(model))
        names = profiles["payer"]["syscalls"][0]["names"]
        assert "socket" in names
        assert "execve" not in names

    def test_default_errno(self) -> None:
        """Every profile denies unlisted syscalls (SCMP_ACT_ERRNO default)."""
        model = KernelModel(nodes=(_node("solo"),))
        profiles = json.loads(export_seccomp(model))
        assert profiles["solo"]["defaultAction"] == "SCMP_ACT_ERRNO"

    def test_stable(self) -> None:
        """Two exports of the same model are byte-for-byte identical."""
        # frob:tests src/frob/strata/_export.py::export_seccomp kind="unit"
        model = KernelModel(nodes=(_node("a", may=("exec", "net")), _node("b")))
        assert export_seccomp(model) == export_seccomp(model)


class TestExportIam:
    """IAM policy exporter tests."""

    def test_flow_statements(self) -> None:
        """One declared Flow yields one read and one write statement, src as
        principal and dst as resource."""
        model = KernelModel(
            nodes=(_node("web"), _node("db")),
            flows=(_flow("f1", "web", "db"),),
        )
        doc = json.loads(export_iam(model))
        sids = {s["sid"] for s in doc["statements"]}
        assert sids == {"f1-read", "f1-write"}
        for s in doc["statements"]:
            assert s["principal"] == "web"
            assert s["resource"] == "db"
            assert s["effect"] == "Allow"

    def test_no_flows_empty(self) -> None:
        """A model with no flows yields an empty statement list, not an
        implicit allow-all."""
        model = KernelModel(nodes=(_node("solo"),))
        doc = json.loads(export_iam(model))
        assert doc["statements"] == []

    def test_stable(self) -> None:
        """Two exports of the same model are byte-for-byte identical."""
        # frob:tests src/frob/strata/_export.py::export_iam kind="unit"
        model = KernelModel(
            nodes=(_node("a"), _node("b")),
            flows=(_flow("f1", "a", "b"), _flow("f2", "b", "a")),
        )
        assert export_iam(model) == export_iam(model)
