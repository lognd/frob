"""Golden-file determinism test for the strata exporters (T-0086): exporting
frob's own self-hosting model (`design/frob.strata`, T-0081) must reproduce
the exact bytes committed under `tests/golden/`, both across two in-process
calls and against the checked-in fixture. A change to exporter ordering,
key sorting, or the kind->syscall mapping that alters output must update
the golden file deliberately, not drift silently.
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import elaborate, parse_module
from frob.strata._export import export_iam, export_k8s_netpol, export_seccomp

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MODEL_PATH = _REPO_ROOT / "design" / "frob.strata"
_GOLDEN_DIR = _REPO_ROOT / "tests" / "golden"


def _model():
    """Parse + elaborate `design/frob.strata` into a `KernelModel`."""
    text = _MODEL_PATH.read_text(encoding="utf-8")
    parsed = parse_module(text)
    assert parsed.is_ok, f"design/frob.strata failed to parse: {parsed.err}"
    elaborated = elaborate(parsed.danger_ok)
    assert elaborated.is_ok, f"design/frob.strata failed to elaborate: {elaborated.err}"
    return elaborated.danger_ok


class TestExportGolden:
    """frob:tests test_export_golden.py::TestExportGolden"""

    def test_k8s(self) -> None:
        """`export_k8s_netpol(design/frob.strata)` matches the committed
        golden byte-for-byte, and re-running produces the same bytes."""
        model = _model()
        rendered = export_k8s_netpol(model)
        assert rendered == export_k8s_netpol(model)
        golden = (_GOLDEN_DIR / "frob_export_k8s.yaml").read_text()
        assert rendered == golden

    def test_seccomp(self) -> None:
        """`export_seccomp(design/frob.strata)` matches the committed
        golden byte-for-byte, and re-running produces the same bytes."""
        model = _model()
        rendered = export_seccomp(model)
        assert rendered == export_seccomp(model)
        golden = (_GOLDEN_DIR / "frob_export_seccomp.json").read_text()
        assert rendered == golden

    def test_iam(self) -> None:
        """`export_iam(design/frob.strata)` matches the committed golden
        byte-for-byte, and re-running produces the same bytes."""
        model = _model()
        rendered = export_iam(model)
        assert rendered == export_iam(model)
        golden = (_GOLDEN_DIR / "frob_export_iam.json").read_text()
        assert rendered == golden
