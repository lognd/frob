"""Unit-level coverage for `std.host`'s attr-desugar/read-back pair
(T-0255, `src/frob/strata/_host.py`): `host_attrs` (desugar) and
`host_manifest_for` (read-back) against hand-built values, mirroring the
`_pii.py::node_pii_tags` precedent's unit-test shape. End-to-end
parse -> elaborate coverage lives in `test_litmus_host.py`.
"""

from __future__ import annotations

from frob.strata._host import (
    HostOwns,
    HostPlatform,
    host_attrs,
    host_manifest_for,
)
from frob.strata._models import Node


class TestHostAttrs:
    # frob:tests src/frob/strata/_host.py::host_attrs kind="unit"
    def test_desugars(self):
        attrs = host_attrs(
            runs_as="api-svc",
            is_unit=True,
            owns=(("/etc/api", "0644"), ("/var/lib/api", "0750")),
            listens=(8080, 8443),
        )
        assert attrs == (
            "runs_as=api-svc",
            "unit",
            "owns=/etc/api:0644",
            "owns=/var/lib/api:0750",
            "listens=8080",
            "listens=8443",
        )

    # frob:tests src/frob/strata/_host.py::host_attrs kind="unit"
    def test_no_clauses_desugars_to_empty(self):
        attrs = host_attrs(runs_as=None, is_unit=False, owns=(), listens=())
        assert attrs == ()


class TestHostManifest:
    # frob:tests src/frob/strata/_host.py::host_manifest_for kind="unit"
    def test_reads(self):
        node = Node(
            id="api",
            trust="trusted",
            attrs=(
                "runs_as=api-svc",
                "unit",
                "owns=/etc/api:0644",
                "listens=8080",
            ),
        )
        manifest = host_manifest_for(node)
        assert manifest is not None
        assert manifest.platform is HostPlatform.LINUX_SYSTEMD
        assert manifest.runs_as == "api-svc"
        assert manifest.is_unit is True
        assert manifest.owns == (HostOwns(path="/etc/api", mode="0644"),)
        assert manifest.listens == (8080,)

    # frob:tests src/frob/strata/_host.py::host_manifest_for kind="unit"
    def test_node_with_no_host_attrs_returns_none(self):
        node = Node(id="api", trust="trusted", attrs=("code=src/**",))
        assert host_manifest_for(node) is None
