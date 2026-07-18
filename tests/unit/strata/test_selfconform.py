"""Unit tests for T-0150 self-conformance: SYS100/SYS101/SYS102 reconciled
against `design/frob.strata`'s `code`/`may` declarations
(docs/strata/selfconform.md).

POST-REVIEW REWORK: the reviewed mechanism is `Node.attrs`'s `code=<glob>`
convention (`bind_code`, T-0078) + `Node.may` (T-0079/T-0113), the SAME
kernel-level fields `test_code_binding.py`/`test_effects.py` already
exercise -- no `frob.toml` table, matching `_selfconform.py`'s rework.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.strata import (
    SYS_STALE_DESIGN,
    SYS_UNDECLARED_INTERFACE,
    SYS_UNMODELED_CODE,
    KernelModel,
    Node,
    check_self_conformance,
)
from frob.strata._effects import _KIND_MAP
from frob.strata._selfconform import _EXTENDED_KINDS
from frob.vet._capability import _PATTERNS


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestUndeclaredInterfaceCore:
    """SYS100 for net/fs-write/exec -- delegated verbatim to THREAT004's
    `check_capability_conformance` (docs/strata/selfconform.md#the-three-rules)."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    # frob:waive PERF003 reason="fixture-building tuple literals plus assertion generators over check results, not a nested join (covers all sites in this file)"
    def test_core_undeclared_interface_fires(self, tmp_path: Path):
        _write(
            tmp_path, "src/frob/widget/_io.py", "import requests\nrequests.get('x')\n"
        )
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [
            v for v in result.danger_ok.violations if v.rule == SYS_UNDECLARED_INTERFACE
        ]
        assert any(v.node == "widget" and "net" in v.detail for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_core_undeclared_interface_discharges_once_declared(self, tmp_path: Path):
        _write(
            tmp_path, "src/frob/widget/_io.py", "import requests\nrequests.get('x')\n"
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTERFACE for v in result.danger_ok.violations
        )


class TestUndeclaredInterfaceExtended:
    """SYS100 for eval/env/ffi/install-hook -- the slice THREAT004
    structurally cannot see (docs/strata/selfconform.md#the-three-rules)."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_extended_undeclared_interface_fires(self, tmp_path: Path):
        _write(tmp_path, "src/frob/widget/_io.py", "x = compile('1', '<s>', 'eval')\n")
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [
            v for v in result.danger_ok.violations if v.rule == SYS_UNDECLARED_INTERFACE
        ]
        assert any(v.node == "widget" and "eval" in v.detail for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_extended_undeclared_interface_discharges_once_declared(
        self, tmp_path: Path
    ):
        _write(tmp_path, "src/frob/widget/_io.py", "x = compile('1', '<s>', 'eval')\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("eval",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTERFACE for v in result.danger_ok.violations
        )


class TestStaleDesign:
    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_stale_design_fires(self, tmp_path: Path):
        """A `may` capability declared for a node never observed in its
        `code=`-bound files is SYS101."""
        _write(tmp_path, "src/frob/widget/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [v for v in result.danger_ok.violations if v.rule == SYS_STALE_DESIGN]
        assert any(v.node == "widget" and "net" in v.detail for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_stale_design_discharges_once_observed(self, tmp_path: Path):
        _write(
            tmp_path, "src/frob/widget/_io.py", "import requests\nrequests.get('x')\n"
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(v.rule == SYS_STALE_DESIGN for v in result.danger_ok.violations)


class TestUnmodeledCode:
    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_unmodeled_code_fires(self, tmp_path: Path):
        """A `src/frob/` directory claimed by no node's `code=` glob at
        all is SYS102, even with zero observable capabilities."""
        _write(tmp_path, "src/frob/widget/_io.py", "x = 1\n")
        _write(tmp_path, "src/frob/orphan/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [v for v in result.danger_ok.violations if v.rule == SYS_UNMODELED_CODE]
        assert any(v.node == "orphan" for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_unmodeled_code_discharges_once_mapped(self, tmp_path: Path):
        _write(tmp_path, "src/frob/widget/_io.py", "x = 1\n")
        _write(tmp_path, "src/frob/orphan/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
                Node(id="other", trust="trusted", attrs=("code=src/frob/orphan/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNMODELED_CODE for v in result.danger_ok.violations
        )


class TestExtendedKindsDriftLock:
    # frob:tests src/frob/strata/_selfconform.py::_EXTENDED_KINDS kind="drift"
    def test_extended_kinds_is_disjoint_from_kind_map(self):
        """`_EXTENDED_KINDS` (SYS100's new-code slice) and `_KIND_MAP`'s keys
        (THREAT004's delegated slice) must never overlap -- a shared kind
        would double-count SYS100 for it. Also must union to EVERY kind
        `vet._capability._PATTERNS` defines (docs/strata/selfconform.md
        #kind-space-drift-lock): if `_KIND_MAP` or `_PATTERNS` ever grows a
        kind neither set accounts for, this test fails first, loudly."""
        assert _EXTENDED_KINDS.isdisjoint(_KIND_MAP.keys())
        all_pattern_kinds = frozenset(
            kind for table in _PATTERNS.values() for kind in table
        )
        assert _EXTENDED_KINDS | frozenset(_KIND_MAP.keys()) == all_pattern_kinds


class TestRealGateGreen:
    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="integration"
    def test_repo_design_and_declarations_are_self_conformant(self):
        """`design/frob.strata`'s real `code`/`may` declarations, run
        against the REAL `src/frob/` tree, produce zero SYS100/SYS101/
        SYS102 violations -- the T-0150 gate-green assertion. Skips (does
        not xfail) when the native strata_core extension isn't installed,
        matching every other `.strata`-parsing test's guard in this suite."""
        pytest.importorskip("strata_core")
        from frob.strata._design_load import load_design_ids
        from frob.strata._sysdoc import merge_models

        root = Path(__file__).resolve().parents[3]
        ids = load_design_ids(root, "design")
        assert not ids.errors, f"design load failed: {ids.errors}"
        model = merge_models(ids.models)

        result = check_self_conformance(model, root)
        assert result.is_ok, result.err
        violations = result.danger_ok.violations
        assert violations == (), [(v.rule, v.node, v.detail) for v in violations]
