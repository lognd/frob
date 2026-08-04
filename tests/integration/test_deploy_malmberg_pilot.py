"""T-0260 fixture-based pilot: the deploy epic's full chain (T-0255
std.host manifest -> T-0256 movement-impossibility proofs -> T-0257
generate -> T-0258 conformance), run together end to end against a
malmberg-shaped multi-service model
(tests/fixtures/deploy/malmberg_pilot/design/malmberg.strata).

This substitutes for running the pilot against the real malmberg repo,
which is not present in this checkout and not reachable by this agent
(no remote/SSH execution capability was granted for it -- see tickets.md
T-0260's Done report for the recorded re-scope reasoning). Every existing
host-isolation/deploy unit test (tests/unit/strata/test_host*.py,
tests/unit/deploy/test_*.py) exercises ONE gate/stage at a time on a
1-2-node fixture; this file is the first to prove the whole chain agrees
with itself on a model shaped like a real multi-service product, closing
that "each gate proven separately, never proven together" gap honestly.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from frob.deploy import (
    deploy_conformance_violations,
    generate_all,
)
from frob.strata import load_design_ids
from frob.strata._host import host_manifest_for
from frob.strata._host_isolation import (
    evaluate_lateral_isolation,
    evaluate_vertical_isolation,
)
from frob.strata._sysdoc import merge_models

_FIXTURE_ROOT = Path(__file__).parent.parent / "fixtures" / "deploy" / "malmberg_pilot"

_EXPECTED_SERVICE_NODES = frozenset(
    {
        "media_store",
        "server_api",
        "ingest",
        "cloudsync",
        "faces",
        "backup",
        "display",
    }
)


@pytest.fixture
def malmberg_model():
    """Load+merge the malmberg-pilot design fixture into one `KernelModel`."""
    # frob:tests \
    # tests/integration/test_deploy_malmberg_pilot.py::TestMalmbergPilotChain \
    # kind="integration"
    ids = load_design_ids(_FIXTURE_ROOT, "design")
    assert not ids.errors, f"fixture failed to load: {ids.errors}"
    return merge_models(ids.models)


class TestMalmbergPilotChain:
    """The full chain, proven together against the malmberg-shaped model."""

    def test_every_component_declares_a_host_manifest(self, malmberg_model):
        node_ids = {node.id for node in malmberg_model.nodes}
        assert node_ids == _EXPECTED_SERVICE_NODES
        for node in malmberg_model.nodes:
            manifest = host_manifest_for(node)
            assert manifest is not None
            assert manifest.runs_as is not None
            assert manifest.runs_as.startswith("svc-")

    def test_lateral_isolation_discharges_with_no_waivers(self, malmberg_model):
        # HOST001: no two service users share a writable path, a
        # listening port, or an OS group -- media_store is reached only
        # via declared Flow, never a shared owned path.
        result = evaluate_lateral_isolation(malmberg_model)
        assert result.is_ok
        assert result.danger_ok == ()

    def test_vertical_isolation_discharges_with_no_waivers(self, malmberg_model):
        # HOST002: no setuid path, no sudoers grant, no root-run unit
        # writable by a lower-trust user -- the fixture declares none.
        result = evaluate_vertical_isolation(malmberg_model)
        assert result.is_ok
        assert result.danger_ok == ()

    def test_generate_and_conform_round_trip_clean(self, malmberg_model, tmp_path):
        # T-0257: compile the model into install/status/uninstall
        # scripts, write them under a scratch repo root, then T-0258
        # conformance-check those SAME scripts against the SAME model --
        # a fresh generation must always be self-conformant.
        rendered = generate_all(malmberg_model)
        assert set(rendered) == {"install.sh", "status.sh", "uninstall.sh"}

        design_dir = tmp_path / "design"
        design_dir.mkdir()
        shutil.copy(
            _FIXTURE_ROOT / "design" / "malmberg.strata",
            design_dir / "malmberg.strata",
        )
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()
        for filename, content in rendered.items():
            (deploy_dir / filename).write_text(content, encoding="utf-8")
            (deploy_dir / filename).chmod(0o755)

        violations = deploy_conformance_violations(tmp_path)
        assert violations == ()

    def test_every_service_reaches_media_store_only_via_declared_flow(
        self, malmberg_model
    ):
        media_flows = [
            flow for flow in malmberg_model.flows if flow.dst == "media_store"
        ]
        service_ids = _EXPECTED_SERVICE_NODES - {"media_store"}
        assert {flow.src for flow in media_flows} == service_ids
