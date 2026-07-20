"""Unit-level coverage for `frob.deploy._generate` (T-0257): manifest walk,
digest, and the three script renderers, against hand-built `KernelModel`s
-- mirrors `tests/unit/strata/test_host.py`'s hand-built-value shape.
"""

from __future__ import annotations

from frob.deploy._generate import (
    generate_all,
    generate_install_script,
    generate_status_script,
    generate_uninstall_script,
    manifest_digest,
    sorted_manifest_entries,
)
from frob.strata._models import KernelModel, Node


def _model_with_host_node() -> KernelModel:
    return KernelModel(
        nodes=(
            Node(
                id="api",
                trust="trusted",
                may=("net.out:x",),
                attrs=(
                    "runs_as=api-svc",
                    "unit",
                    "owns=/etc/api:0644",
                    "listens=8080",
                ),
            ),
            Node(id="db", trust="trusted"),
        )
    )


class TestSorted:
    # frob:tests src/frob/deploy/_generate.py::sorted_manifest_entries kind="unit"
    def test_sorted(self):
        entries = sorted_manifest_entries(_model_with_host_node())
        assert [e.node_id for e in entries] == ["api"]
        assert entries[0].manifest.runs_as == "api-svc"
        # port 8080 is unprivileged (>=1024): T-0281 item 8, CAP_NET_BIND_SERVICE
        # is only granted when a declared listens port actually needs it.
        assert "CAP_NET_BIND_SERVICE" not in entries[0].capabilities

    # frob:tests src/frob/deploy/_generate.py::sorted_manifest_entries kind="unit"
    def test_privileged_port_grants_cap_net_bind(self):
        """T-0281 item 8: a `may net` node binding a PRIVILEGED (<1024)
        port still gets `CAP_NET_BIND_SERVICE` -- the gate narrows the
        over-grant, it does not remove the capability outright."""
        model = KernelModel(
            nodes=(
                Node(
                    id="web",
                    trust="trusted",
                    may=("net.out:x",),
                    attrs=("runs_as=web-svc", "unit", "listens=80"),
                ),
            )
        )
        entries = sorted_manifest_entries(model)
        assert "CAP_NET_BIND_SERVICE" in entries[0].capabilities


class TestDigest:
    # frob:tests src/frob/deploy/_generate.py::manifest_digest kind="unit"
    def test_det(self):
        model = _model_with_host_node()
        assert manifest_digest(model) == manifest_digest(model)

    # frob:tests src/frob/deploy/_generate.py::manifest_digest kind="unit"
    def test_changes_with_model(self):
        base = _model_with_host_node()
        changed = KernelModel(
            nodes=(
                Node(
                    id="api",
                    trust="trusted",
                    attrs=("runs_as=api-svc", "unit", "listens=9090"),
                ),
            )
        )
        assert manifest_digest(base) != manifest_digest(changed)


class TestInstall:
    # frob:tests src/frob/deploy/_generate.py::generate_install_script kind="unit"
    def test_idempotent(self):
        script = generate_install_script(_model_with_host_node())
        assert script.startswith("#!/usr/bin/env bash")
        assert "frob-deploy-manifest-digest:" in script
        # check-then-apply: user creation is gated behind an `id -u` check
        assert 'if ! id -u "api-svc"' in script
        # unit file write is gated behind a hash comparison
        assert "desired_hash=" in script
        assert 'if [ "$current_hash" != "$desired_hash" ]; then' in script
        # owned path chmod is gated behind a leading-zero-stripped compare
        assert 'if [ "${current_mode#0}" != "${desired_mode#0}" ]; then' in script

    # frob:tests src/frob/deploy/_generate.py::generate_install_script kind="unit"
    def test_empty_model(self):
        script = generate_install_script(KernelModel())
        assert "nothing to install" in script

    # frob:tests src/frob/deploy/_generate.py::generate_install_script kind="unit"
    def test_shared_runs_as_useradd_block_rendered_once(self):
        """T-0281 item 5 (malmberg pilot finding): a `runs_as` identity
        shared by two nodes/stores (e.g. media_store+ingest both `runs_as
        "malmberg-ingest"`) must render exactly ONE `useradd` guard block
        in install.sh, not one per sharing entry."""
        model = KernelModel(
            nodes=(
                Node(
                    id="ingest",
                    trust="trusted",
                    attrs=("runs_as=shared-svc", "unit"),
                ),
                Node(
                    id="media_store",
                    trust="trusted",
                    attrs=("runs_as=shared-svc", "owns=/var/media:0644"),
                ),
            )
        )
        script = generate_install_script(model)
        assert script.count('if ! id -u "shared-svc"') == 1
        assert script.count("useradd --system") == 1


class TestStatus:
    # frob:tests src/frob/deploy/_generate.py::generate_status_script kind="unit"
    def test_one_line(self):
        script = generate_status_script(_model_with_host_node())
        assert "frob-deploy-api.service" in script
        assert "port=8080" in script

    # frob:tests src/frob/deploy/_generate.py::generate_status_script kind="unit"
    def test_no_units_declared(self):
        """No manifests at all -> `unit_entries` is empty -> the
        "no units declared" short-circuit branch."""
        script = generate_status_script(KernelModel())
        assert "no units declared" in script

    # frob:tests src/frob/deploy/_generate.py::generate_status_script kind="unit"
    def test_manifest_present_but_not_a_unit(self):
        """A manifest exists (non-empty `entries`) but declares no `unit`
        clause, so `unit_entries` still ends up empty -- a DIFFERENT path
        to the same short-circuit than the fully-empty-model case above."""
        model = KernelModel(
            nodes=(Node(id="cfg", trust="trusted", attrs=("owns=/etc/cfg:0644",)),)
        )
        script = generate_status_script(model)
        assert "no units declared" in script

    # frob:tests src/frob/deploy/_generate.py::generate_status_script kind="unit"
    def test_unit_with_no_listens_ports(self):
        """A unit with no `listens` ports skips the port-probe loop body
        entirely -- covers the empty-`listens` branch distinctly from
        `test_one_line`'s port-bearing case."""
        model = KernelModel(
            nodes=(
                Node(
                    id="worker", trust="trusted", attrs=("runs_as=worker-svc", "unit")
                ),
            )
        )
        script = generate_status_script(model)
        assert "frob-deploy-worker.service" in script
        assert "port" not in script


class TestUninstall:
    # frob:tests src/frob/deploy/_generate.py::generate_uninstall_script kind="unit"
    def test_removes(self):
        script = generate_uninstall_script(_model_with_host_node())
        assert 'systemctl stop "frob-deploy-api.service"' in script
        assert 'rm -rf "/etc/api"' in script
        assert 'userdel "api-svc"' in script
        # nothing outside the declared node's own paths/users appears
        # (checked by header, not raw substring: "db" happens to also be
        # valid lowercase hex and can appear inside the manifest digest)
        assert "--- db ---" not in script

    # frob:tests src/frob/deploy/_generate.py::generate_uninstall_script kind="unit"
    def test_empty_model(self):
        """No host manifests declared at all -> the "nothing to
        uninstall" short-circuit branch."""
        script = generate_uninstall_script(KernelModel())
        assert "nothing to uninstall" in script

    # frob:tests src/frob/deploy/_generate.py::generate_uninstall_script kind="unit"
    def test_node_with_no_unit_no_owns_no_runs_as(self):
        """A declared manifest with none of unit/owns/runs_as set exercises
        the false branch of every per-block `if` in
        `_uninstall_unit_block`/`_uninstall_owns_block`/
        `_uninstall_user_block` -- each block renders to an empty string."""
        model = KernelModel(
            nodes=(Node(id="bare", trust="trusted", attrs=("listens=9999",)),)
        )
        script = generate_uninstall_script(model)
        assert "--- bare ---" in script
        assert "systemctl stop" not in script
        assert "userdel" not in script
        assert "rm -rf" not in script

    # frob:tests src/frob/deploy/_generate.py::generate_uninstall_script kind="unit"
    def test_shared_runs_as_userdel_block_rendered_once(self):
        """T-0281 item 5 (malmberg pilot finding): a `runs_as` identity
        shared by two nodes/stores must render exactly ONE `userdel`
        guard block in uninstall.sh, not one per sharing entry."""
        model = KernelModel(
            nodes=(
                Node(
                    id="ingest",
                    trust="trusted",
                    attrs=("runs_as=shared-svc", "unit"),
                ),
                Node(
                    id="media_store",
                    trust="trusted",
                    attrs=("runs_as=shared-svc", "owns=/var/media:0644"),
                ),
            )
        )
        script = generate_uninstall_script(model)
        assert script.count('userdel "shared-svc"') == 1


class TestAll:
    # frob:tests src/frob/deploy/_generate.py::generate_all kind="unit"
    def test_returns_all(self):
        rendered = generate_all(_model_with_host_node())
        assert set(rendered) == {"install.sh", "status.sh", "uninstall.sh"}
        for content in rendered.values():
            assert content.startswith("#!/usr/bin/env bash")
