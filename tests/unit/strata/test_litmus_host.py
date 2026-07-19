"""`std.host` litmus fixture coverage (T-0255, mirroring `test_litmus_pii.py`'s
parse -> elaborate round-trip discipline): the declared/undeclared pair
round-trips through the real `strata_core` parser, proving `host_attrs`'s
attr-desugar convention and `host_manifest_for`'s read-back survive real
source text, not just a hand-built `KernelModel`. T-0255 is manifest-only
(no generator, no proofs), so there is no vuln/hardened firing pair to
litmus here -- the pair instead covers "host declared" vs "host absent",
the one behavioral fork `host_manifest_for` has (module docstring).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, elaborate, parse_module
from frob.strata._host import HostPlatform, host_manifest_for

_LITMUS_DIR = Path(__file__).resolve().parent / "litmus"


def _load_model(filename: str) -> KernelModel:
    """Parse+elaborate one `.strata` fixture under `litmus/` end to end."""
    text = (_LITMUS_DIR / filename).read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    return elaborate(module).danger_ok


class TestHostDeclaredLitmus:
    # frob:tests src/frob/strata/_host.py::host_manifest_for kind="unit"
    def test_declared_manifest_round_trips_every_field(self):
        model = _load_model("host_declared.strata")
        node = next(n for n in model.nodes if n.id == "api")
        manifest = host_manifest_for(node)
        assert manifest is not None
        assert manifest.platform is HostPlatform.LINUX_SYSTEMD
        assert manifest.runs_as == "api-svc"
        assert manifest.is_unit is True
        assert [(o.path, o.mode) for o in manifest.owns] == [
            ("/etc/api", "0644"),
            ("/var/lib/api", "0750"),
        ]
        assert manifest.listens == (8080, 8443)


class TestHostUndeclaredLitmus:
    # frob:tests src/frob/strata/_host.py::host_manifest_for kind="unit"
    def test_undeclared_node_has_no_manifest(self):
        model = _load_model("host_undeclared.strata")
        node = next(n for n in model.nodes if n.id == "api")
        assert host_manifest_for(node) is None
