"""Tests for T-4663: wiring `[arch.layering]` into `frob check` (ARCH104,
`frob.gates._arch.arch_gate` + `frob.arch._layering.check_layering_edges`).

T-0620 shipped the layering schema and checker real but never invoked from
`frob check` -- a planted upward-import violation used to be reported by
NOTHING (a silent zero). This module's positive controls fail on dev
today and pass once `arch_gate` calls `check_layering_edges`."""

from __future__ import annotations

from pathlib import Path

from frob.findings import Severity


def _write(root: Path, rel: str, text: str) -> Path:
    """Test helper: write `text` to `root/rel`, creating parent dirs."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _write_layering_frob_toml(root: Path) -> None:
    """A minimal, real `frob.toml` declaring a two-layer `ledger < land`
    contract -- `ledger` may import nothing, `land` may import `ledger`."""
    _write(
        root,
        "frob.toml",
        """
[arch.layering.layers]
ledger = ["pkg/ledger"]
land = ["pkg/land"]

[arch.layering.allow]
ledger = []
land = ["ledger"]
""",
    )


# frob:tests tests/unit/test_layering_gate.py::test_upward_import_is_arch10x_red
# frob:tests src/frob/gates/_arch.py::arch_gate
# frob:tests src/frob/arch/_layering.py::check_layering_violations
def test_upward_import_is_arch10x_red(tmp_path: Path) -> None:
    """POSITIVE CONTROL (T-4663 acceptance [2]): plant an import from the
    `ledger` layer back UP into `land` -- an edge nothing in `ledger.
    allow` permits. `arch_gate` must report it as ARCH104 at
    `Severity.ERROR` (RED), naming both endpoints. This fails on dev
    today: the layering checker is real but never invoked by `frob
    check`, so a planted violation is reported by nothing."""
    from frob.gates._arch import arch_gate

    _write_layering_frob_toml(tmp_path)
    _write(tmp_path, "pkg/land/__init__.py", "")
    _write(tmp_path, "pkg/land/thing.py", "X = 1\n")
    _write(tmp_path, "pkg/ledger/__init__.py", "")
    _write(
        tmp_path,
        "pkg/ledger/core.py",
        "from pkg.land.thing import X  # upward import: ledger -> land\n",
    )

    violations = arch_gate(tmp_path)
    hits = [v for v in violations if v.rule == "ARCH104"]
    assert hits, "expected an ARCH104 finding for the planted upward import"
    assert all(v.severity == Severity.ERROR for v in hits)
    assert any(
        v.file == "pkg/ledger/core.py" and "land" in v.message and "ledger" in v.message
        for v in hits
    ), f"expected the finding to name both endpoints, got: {[v.message for v in hits]}"


# frob:tests src/frob/gates/_arch.py::arch_gate
# frob:tests tests/unit/test_layering_gate.py::test_layering_job_reports_edges_checked
# frob:tests src/frob/arch/_layering.py::check_layering_edges
def test_layering_job_reports_edges_checked(tmp_path: Path) -> None:
    """POSITIVE CONTROL (T-4663 acceptance [3]): given NO violation, the
    layering scan still reports a NONZERO edges-checked count -- proof the
    job actually ran a real scan, not a silent zero indistinguishable
    from "the job never fired". Calls `check_layering_edges` directly
    (the same function `arch_gate` wires in) since `edges_checked` is not
    itself part of `arch_gate`'s `tuple[Violation, ...]` return shape."""
    from frob.arch._layering import check_layering_edges, load_layering_config

    _write_layering_frob_toml(tmp_path)
    _write(tmp_path, "pkg/land/__init__.py", "")
    _write(tmp_path, "pkg/ledger/__init__.py", "")
    _write(
        tmp_path,
        "pkg/land/thing.py",
        "from pkg.ledger import core  # allowed: land -> ledger\n",
    )
    _write(tmp_path, "pkg/ledger/core.py", "VALUE = 1\n")

    config = load_layering_config(tmp_path)
    assert config is not None
    violations, edges_checked = check_layering_edges(tmp_path, config)

    assert not violations, f"expected a clean scan, got: {violations}"
    assert edges_checked > 0, (
        "a clean run reporting edges_checked == 0 is a silent zero -- "
        "indistinguishable from the scan never having run at all"
    )


# frob:tests src/frob/gates/_arch.py::arch_gate
# frob:tests \
# tests/unit/test_layering_gate.py::test_no_declared_layering_config_is_not_a_violation
def test_no_declared_layering_config_is_not_a_violation(tmp_path: Path) -> None:
    """No `frob.toml` (or no `[arch.layering]` table) means "nothing
    declared" -- `arch_gate` must not fire ARCH104 and must not crash;
    same fail-quiet posture every other per-section `frob.toml` reader in
    this codebase uses (`load_layering_config`'s own docstring)."""
    from frob.gates._arch import arch_gate

    _write(tmp_path, "pkg/anything.py", "import os\n")

    violations = arch_gate(tmp_path)
    assert not [v for v in violations if v.rule == "ARCH104"]


# frob:tests \
# tests/unit/test_layering_gate.py::test_allowed_edge_across_declared_layers_is_not_arch104  # noqa: E501
def test_allowed_edge_across_declared_layers_is_not_arch104(tmp_path: Path) -> None:
    """A cross-layer import explicitly listed in `[arch.layering.allow]`
    is not a violation -- `arch_gate` must not flag it, mirroring
    `frob.arch._layering`'s own `test_allowed_cross_layer_edge_not_
    flagged` at the gate-wiring level this ticket adds."""
    from frob.gates._arch import arch_gate

    _write_layering_frob_toml(tmp_path)
    _write(tmp_path, "pkg/ledger/__init__.py", "")
    _write(tmp_path, "pkg/ledger/core.py", "VALUE = 1\n")
    _write(
        tmp_path,
        "pkg/land/__init__.py",
        "from pkg.ledger.core import VALUE  # allowed: land -> ledger\n",
    )

    violations = arch_gate(tmp_path)
    assert not [v for v in violations if v.rule == "ARCH104"]
