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
        # T-0771: "net.out" is not a recognized `net.mode` id (connect/
        # listen are the only defined modes) -- `_may_kind` resolves its
        # kind segment to the coarse family "net", which (now that `net`
        # is in `WIRED_MODE_FAMILIES`) expands to the union of net's
        # modes, same shape as a bare `may "net"` would.
        node = Node(id="n", trust="trusted", may=("net.out:stripe.com", "exec:*"))
        assert node_may_kinds(node) == frozenset({"net.connect", "net.listen", "exec"})

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
        assert kinds == {"net.connect", "fs.write", "exec"}

    # frob:tests src/frob/strata/_effects.py::extract_effects kind="unit"
    def test_foreign_files_are_not_scanned(self, tmp_path: Path):
        _write(tmp_path, "scripts/one_off.py", "subprocess.run(['x'])\n")
        model = KernelModel(nodes=(Node(id="Api", trust="trusted"),))
        binding = bind_code(model, tmp_path).danger_ok
        effects = extract_effects(binding, tmp_path)
        assert effects == ()


class TestCheckCapabilityConformance:
    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
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
        assert v.kind == "net.connect"
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

    # frob:tests src/frob/strata/_effects.py::check_legacy_capability_aliases \
    # kind="unit"
    def test_legacy_alias_in_window_is_a_warning_not_an_error(self):
        model = KernelModel(
            nodes=(Node(id="widget", trust="trusted", may=("fs-write",)),)
        )
        [finding] = check_legacy_capability_aliases(model, today=date(2026, 8, 1))
        assert finding.node == "widget"
        assert finding.target == "fs.write"
        assert finding.is_error is False

    # frob:tests src/frob/strata/_effects.py::check_legacy_capability_aliases \
    # kind="unit"
    def test_legacy_alias_past_sunset_is_an_error(self):
        model = KernelModel(
            nodes=(Node(id="widget", trust="trusted", may=("fs-read",)),)
        )
        [finding] = check_legacy_capability_aliases(model, today=date(2027, 1, 1))
        assert finding.target == "fs.read"
        assert finding.is_error is True

    # frob:tests src/frob/strata/_effects.py::check_legacy_capability_aliases \
    # kind="unit"
    def test_non_legacy_declaration_is_not_flagged(self):
        model = KernelModel(
            nodes=(Node(id="widget", trust="trusted", may=("fs.read", "net")),)
        )
        assert check_legacy_capability_aliases(model) == ()


# T-0440: `deploy`/`serve`/`mutate` split off `core`'s former utility-hub
# node in design/frob.strata into three standalone components with their
# own `may` declarations (docs/strata/roadmap.md#self-hosting-commitments-
# decision-d7). This is the fast, node-scoped regression guard for that
# split: it binds a hand-built model mirroring ONLY those three nodes'
# real `code`/`may` declarations against this repo's OWN real source
# tree and asserts zero undeclared-capability violations -- if a future
# change to `src/frob/deploy/**`/`src/frob/serve/**`/`src/frob/mutate/**`
# starts exercising a net/fs/exec effect these three nodes do not declare
# (or `design/frob.strata`'s declarations silently drift from what the
# real code does), this fails fast without needing the full self-model
# elaboration `tests/system/test_frob_self_model.py::
# TestFrobSelfModel.test_sys_gate_zero_violations` already covers.
class TestDeployServeMutateNodeSplitConformance:
    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    def test_deploy_declares_every_real_effect_it_exercises(self):
        root = Path(__file__).resolve().parents[3]
        model = KernelModel(
            nodes=(
                Node(
                    id="deploy",
                    trust="trusted",
                    attrs=("code=src/frob/deploy/**",),
                    may=("exec", "fs", "fs-read"),
                ),
            )
        )
        binding = bind_code(model, root).danger_ok
        report = check_capability_conformance(model, binding, root)
        assert report.violations == ()

    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    def test_mutate_declares_every_real_effect_it_exercises(self):
        """T-1075: `mutate` also reads `os.environ` (building a child
        process's env for the mutation-test subprocess run) -- `env` joins
        this fixture's declared `may` set now that `env` is wired (was
        invisible to `check_capability_conformance`, THREAT004's core
        join, before this ticket; only ever caught by SYS100-extended)."""
        root = Path(__file__).resolve().parents[3]
        model = KernelModel(
            nodes=(
                Node(
                    id="mutate",
                    trust="trusted",
                    attrs=("code=src/frob/mutate/**",),
                    may=("exec", "fs", "fs-read", "env"),
                ),
            )
        )
        binding = bind_code(model, root).danger_ok
        report = check_capability_conformance(model, binding, root)
        assert report.violations == ()

    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    def test_serve_declares_zero_may_and_exercises_zero_effects(self):
        """T-0440: `serve` is the deliberately zero-`may` node -- every
        net/fs/exec effect a `frob serve` request performs is delegated to
        code bound on ANOTHER node (`core`/`gates`/`graphlang`/
        `tickets_ledger`, modeled as flow edges, not `serve`'s own `may`).
        A future change that starts calling `open`/`subprocess`/an HTTP
        client DIRECTLY from `src/frob/serve/**` (rather than through one
        of those other components) is exactly the drift this guards: it
        would surface as a REAL, non-empty violation here, not a silent
        capability creep.
        """
        root = Path(__file__).resolve().parents[3]
        model = KernelModel(
            nodes=(
                Node(id="serve", trust="trusted", attrs=("code=src/frob/serve/**",)),
            )
        )
        binding = bind_code(model, root).danger_ok
        report = check_capability_conformance(model, binding, root)
        assert report.violations == ()
