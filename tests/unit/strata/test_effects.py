"""Unit tests for strata tier-2 effect extraction: net/fs/exec facts vs
`may` capabilities (docs/strata/surface.md#code-binding-tier-2-v0-implementation,
T-0079).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.strata import (
    KernelModel,
    Node,
    bind_code,
    check_capability_conformance,
    check_legacy_capability_aliases,
    extract_effects,
    node_may_kinds,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestNodeMayKinds:
    # frob:tests src/frob/strata/_effects.py::node_may_kinds kind="unit"
    def test_kinds(self):
        node = Node(id="n", trust="trusted", may=("net.out:stripe.com", "exec:*"))
        assert node_may_kinds(node) == frozenset({"net", "exec"})

    # frob:tests src/frob/strata/_effects.py::node_may_kinds kind="unit"
    def test_no_may_atoms_is_empty(self):
        node = Node(id="n", trust="trusted")
        assert node_may_kinds(node) == frozenset()


class TestExtractEffects:
    # frob:tests src/frob/strata/_effects.py::extract_effects kind="unit"
    def test_observes_net_fs_exec_effects_in_bound_code(self, tmp_path: Path):
        _write(
            tmp_path,
            "api/handler.py",
            "import subprocess\n"
            "import requests\n"
            "subprocess.run(['x'])\n"
            "requests.get('https://x')\n"
            "open('f').write('x')\n",
        )
        model = KernelModel(
            nodes=(Node(id="Api", trust="trusted", attrs=("code=api/**",)),)
        )
        binding = bind_code(model, tmp_path).danger_ok
        effects = extract_effects(binding, tmp_path)
        kinds = {e.kind for e in effects}
        # T-0717: fs-write observations are now the precise, mode-qualified
        # "fs.write" spelling (frob.vet._capability_modes) rather than the
        # old ambiguous bare "fs".
        assert kinds == {"net", "fs.write", "exec"}

    # frob:tests src/frob/strata/_effects.py::extract_effects kind="unit"
    def test_foreign_files_are_not_scanned(self, tmp_path: Path):
        _write(tmp_path, "scripts/one_off.py", "subprocess.run(['x'])\n")
        model = KernelModel(nodes=(Node(id="Api", trust="trusted"),))
        binding = bind_code(model, tmp_path).danger_ok
        effects = extract_effects(binding, tmp_path)
        assert effects == ()


class TestCheckCapabilityConformance:
    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    # frob:waive DUP001 reason="parallel test methods within \
    # test_effects.py (2 sites) sharing an arrange-act scaffold typical of \
    # exhaustive per-case coverage; extracting would obscure per-case \
    # intent"
    def test_declared_may_capability_silences_matching_effect(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "requests.get('https://stripe.com')\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="Api",
                    trust="trusted",
                    attrs=("code=api/**",),
                    may=("net.out:stripe.com",),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_capability_conformance(model, binding, tmp_path)
        assert report.violations == ()

    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    def test_effect_with_no_matching_may_is_a_violation(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "x = 1\nrequests.get('https://x')\n")
        model = KernelModel(
            nodes=(Node(id="Api", trust="trusted", attrs=("code=api/**",)),)
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_capability_conformance(model, binding, tmp_path)
        assert len(report.violations) == 1
        v = report.violations[0]
        assert v.file == "api/handler.py"
        assert v.line == 2
        assert v.kind == "net"
        assert v.component == "Api"
        assert v.needle == "requests."

    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    def test_declared_may_of_different_kind_does_not_cover_effect(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "subprocess.run(['x'])\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="Api",
                    trust="trusted",
                    attrs=("code=api/**",),
                    may=("net.out:stripe.com",),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_capability_conformance(model, binding, tmp_path)
        assert len(report.violations) == 1
        assert report.violations[0].kind == "exec"

    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    def test_foreign_code_is_not_checked(self, tmp_path: Path):
        _write(tmp_path, "scripts/one_off.py", "subprocess.run(['x'])\n")
        model = KernelModel(nodes=(Node(id="Api", trust="trusted"),))
        binding = bind_code(model, tmp_path).danger_ok
        report = check_capability_conformance(model, binding, tmp_path)
        assert report.violations == ()

    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    # frob:waive DUP001 reason="parallel test methods within \
    # test_effects.py (2 sites) sharing an arrange-act scaffold typical of \
    # exhaustive per-case coverage; extracting would obscure per-case \
    # intent"
    def test_fs_write_effect_needs_fs_kind_declaration(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "open('f').write('x')\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="Api",
                    trust="trusted",
                    attrs=("code=api/**",),
                    may=("fs.write:/tmp",),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_capability_conformance(model, binding, tmp_path)
        assert report.violations == ()


class TestModeQualifiedFsConformance:
    """T-0717 acceptance clause 1: a node whose code only reads files,
    declaring precisely `may "fs.read"`, discharges narrowly -- and a real
    write observation on that same node fails conformance."""

    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    def test_fs_read_declaration_discharges_read_only_code(self, tmp_path: Path):
        _write(
            tmp_path,
            "api/handler.py",
            "from pathlib import Path\nPath('f').read_text()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="Api",
                    trust="trusted",
                    attrs=("code=api/**",),
                    may=("fs.read",),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_capability_conformance(model, binding, tmp_path)
        assert report.violations == ()

    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    def test_fs_read_declaration_fails_conformance_on_a_write(self, tmp_path: Path):
        _write(
            tmp_path,
            "api/handler.py",
            "from pathlib import Path\nPath('f').write_text('y')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="Api",
                    trust="trusted",
                    attrs=("code=api/**",),
                    may=("fs.read",),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_capability_conformance(model, binding, tmp_path)
        assert len(report.violations) == 1
        assert report.violations[0].kind == "fs.write"


class TestLegacyCapabilityAliases:
    """T-0717 acceptance clauses 2/3: `fs-write`/`fs-read` are deprecated
    aliases of `fs.write`/`fs.read` -- they keep working (WARN) inside
    their sunset window and become gate errors past it."""

    # frob:tests src/frob/strata/_effects.py::check_legacy_capability_aliases kind="unit"
    def test_legacy_alias_in_window_is_a_warning_not_an_error(self):
        model = KernelModel(
            nodes=(Node(id="widget", trust="trusted", may=("fs-write",)),)
        )
        [finding] = check_legacy_capability_aliases(model, today=date(2026, 8, 1))
        assert finding.node == "widget"
        assert finding.target == "fs.write"
        assert finding.is_error is False

    # frob:tests src/frob/strata/_effects.py::check_legacy_capability_aliases kind="unit"
    def test_legacy_alias_past_sunset_is_an_error(self):
        model = KernelModel(
            nodes=(Node(id="widget", trust="trusted", may=("fs-read",)),)
        )
        [finding] = check_legacy_capability_aliases(model, today=date(2027, 1, 1))
        assert finding.target == "fs.read"
        assert finding.is_error is True

    # frob:tests src/frob/strata/_effects.py::check_legacy_capability_aliases kind="unit"
    def test_non_legacy_declaration_is_not_flagged(self):
        model = KernelModel(
            nodes=(Node(id="widget", trust="trusted", may=("fs.read", "net")),)
        )
        assert check_legacy_capability_aliases(model) == ()
