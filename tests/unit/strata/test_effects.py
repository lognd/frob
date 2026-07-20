"""Unit tests for strata tier-2 effect extraction: net/fs/exec facts vs
`may` capabilities (docs/strata/surface.md#code-binding-tier-2-v0-implementation,
T-0079).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import (
    KernelModel,
    Node,
    bind_code,
    check_capability_conformance,
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
        assert kinds == {"net", "fs", "exec"}

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
