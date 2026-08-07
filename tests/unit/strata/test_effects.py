"""Unit tests for strata tier-2 effect extraction: net/fs/exec facts vs
`may` capabilities (docs/strata/surface.md#code-binding-tier-2-v0-implementation,
T-0079).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.strata import (
    KernelModel,
    MayGrant,
    Node,
    bind_code,
    check_capability_conformance,
    check_legacy_capability_aliases,
    elaborate,
    extract_effects,
    node_may_kinds,
    parse_module,
)
from frob.strata._effects import StaleViaSymbolViolation, check_stale_via_symbols


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


# frob:doc docs/strata/surface.md#may-scope
class TestScopedMayViaConformance:
    """T-1440: per-file SYS100 join -- a `may` grant with a `via` glob
    covers only the files it names, not the whole node."""

    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    def test_observation_outside_via_surface_is_a_violation(self, tmp_path: Path):
        # acceptance clause 0: a node with `may X via glob` still fires
        # SYS100 for a file the glob does not cover, even though the node
        # nominally holds capability X.
        _write(tmp_path, "api/net.py", "requests.get('https://x')\n")
        _write(tmp_path, "api/other.py", "requests.get('https://x')\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="Api",
                    trust="trusted",
                    attrs=("code=api/**",),
                    may=("net.out",),
                    may_grants=(MayGrant(atom="net.out", via=("api/net.py",)),),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_capability_conformance(model, binding, tmp_path)
        assert [v.file for v in report.violations] == ["api/other.py"]

    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    def test_observation_inside_every_via_surface_is_clean(self, tmp_path: Path):
        # acceptance clause 1: only files inside the via glob observe the
        # kind -> the audit is green.
        _write(tmp_path, "api/net.py", "requests.get('https://x')\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="Api",
                    trust="trusted",
                    attrs=("code=api/**",),
                    may=("net.out",),
                    may_grants=(MayGrant(atom="net.out", via=("api/net.py",)),),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_capability_conformance(model, binding, tmp_path)
        assert report.violations == ()

    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    def test_via_less_grant_still_covers_the_whole_node(self, tmp_path: Path):
        # migration semantics: a via-less `may` (via=()) keeps pre-T-1440
        # whole-node meaning.
        _write(tmp_path, "api/anywhere.py", "requests.get('https://x')\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="Api",
                    trust="trusted",
                    attrs=("code=api/**",),
                    may=("net.out",),
                    may_grants=(MayGrant(atom="net.out", via=()),),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_capability_conformance(model, binding, tmp_path)
        assert report.violations == ()

    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    def test_legacy_node_with_no_may_grants_falls_back_to_whole_node(
        self, tmp_path: Path
    ):
        # a `Node` built directly (no `may_grants` populated at all, the
        # shape every pre-T-1440 fixture/caller still uses) must behave
        # exactly as before -- kind-only, whole-node join.
        _write(tmp_path, "api/anywhere.py", "requests.get('https://x')\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="Api",
                    trust="trusted",
                    attrs=("code=api/**",),
                    may=("net.out",),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_capability_conformance(model, binding, tmp_path)
        assert report.violations == ()

    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    def test_scoped_and_via_less_grants_of_different_kinds_compose(
        self, tmp_path: Path
    ):
        # one scoped grant + one via-less grant of a DIFFERENT kind on the
        # same node: the scoped grant's file-level narrowing must not
        # leak into (or shrink) the via-less grant's whole-node coverage.
        _write(tmp_path, "api/net.py", "requests.get('https://x')\n")
        _write(tmp_path, "api/writer.py", "open('f').write('x')\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="Api",
                    trust="trusted",
                    attrs=("code=api/**",),
                    may=("net.out", "fs.write"),
                    may_grants=(
                        MayGrant(atom="net.out", via=("api/net.py",)),
                        MayGrant(atom="fs.write", via=()),
                    ),
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
        """T-0440 established `serve` as a deliberately zero-`may` node --
        every net/fs/exec effect a `frob serve` request performed was
        delegated to code bound on ANOTHER node (`core`/`gates`/
        `graphlang`/`tickets_ledger`), never called directly from
        `src/frob/serve/**`.

        T-1166 (capability-boundary disposition, T-1094's FS-watch push
        invalidation + T-1096's subscribe/push event stream): the daemon
        now legitimately OWNS its own socket and watch-file effects --
        `_socketd.py` opens/writes/unlinks its own pidfile and lease-state
        files and calls `socket.connect` for its own idle-monitor
        self-wake, `_events.py` writes to and connects its own event-bus
        socket -- these are the daemon's OWN process boundary, not a
        delegated call into another node's owned resource, so widening
        `serve`'s `may` to include `fs`/`net` (matching design/frob.
        strata's own `serve` node, which already declares both) is the
        honest disposition (option (a) from T-1166's ticket body), not a
        silent capability creep: this fixture's `may=` now mirrors the
        real design model exactly, so a FUTURE effect outside fs/net (an
        `exec` call, for instance) still surfaces here as a real
        violation, preserving the guard's original purpose for every
        capability serve has NOT been granted.
        """
        root = Path(__file__).resolve().parents[3]
        model = KernelModel(
            nodes=(
                Node(
                    id="serve",
                    trust="trusted",
                    attrs=("code=src/frob/serve/**",),
                    may=("fs", "net"),
                ),
            )
        )
        binding = bind_code(model, root).danger_ok
        report = check_capability_conformance(model, binding, root)
        assert report.violations == ()


class TestSymbolFormViaConformance:
    """T-1627: a symbol-form `via "glob::qualname"` entry narrows the SYS100
    join down to one enclosing symbol, not the whole file."""

    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    def test_effect_inside_granted_symbol_is_clean(self, tmp_path: Path):
        _write(tmp_path, "app/site.py", "def run(cmd):\n    subprocess.run(cmd)\n")
        module = parse_module(
            'module m\nnode app: trusted { code "app/site.py"; '
            + 'may "exec" via "app/site.py::run";'
            + " }\n"
        ).danger_ok
        model = elaborate(module).danger_ok
        binding = bind_code(model, tmp_path).danger_ok
        report = check_capability_conformance(model, binding, tmp_path)
        assert report.violations == ()

    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    def test_effect_outside_granted_symbol_in_same_file_is_a_violation(
        self, tmp_path: Path
    ):
        _write(
            tmp_path,
            "app/site.py",
            "def run(cmd):\n"
            "    subprocess.run(cmd)\n"
            "\n\n"
            "def other(cmd):\n"
            "    subprocess.run(cmd)\n",
        )
        module = parse_module(
            'module m\nnode app: trusted { code "app/site.py"; '
            + 'may "exec" via "app/site.py::run";'
            + " }\n"
        ).danger_ok
        model = elaborate(module).danger_ok
        binding = bind_code(model, tmp_path).danger_ok
        report = check_capability_conformance(model, binding, tmp_path)
        assert [v.line for v in report.violations] == [6]

    # frob:tests src/frob/strata/_effects.py::check_capability_conformance kind="unit"
    def test_exclusive_grant_still_flags_a_second_site(self, tmp_path: Path):
        _write(
            tmp_path,
            "app/site.py",
            "def run(cmd):\n"
            "    subprocess.run(cmd)\n"
            "\n\n"
            "def sneaky(cmd):\n"
            "    subprocess.run(cmd)\n",
        )
        module = parse_module(
            'module m\nnode app: trusted { code "app/site.py"; '
            + 'may "exec" via "app/site.py::run" exclusive;'
            + " }\n"
        ).danger_ok
        model = elaborate(module).danger_ok
        binding = bind_code(model, tmp_path).danger_ok
        report = check_capability_conformance(model, binding, tmp_path)
        assert [v.line for v in report.violations] == [6]


class TestExclusiveGrammar:
    """T-1627: `exclusive` is only accepted on a single symbol-form `via`
    entry -- everything else is a parse-time error, not a later gate
    finding."""

    # frob:tests strata_core.parse_source kind="unit"
    def test_exclusive_with_symbol_form_via_parses(self):
        src = (
            "module m\n"
            'node app: trusted { code "app/site.py"; '
            'may "exec" via "app/site.py::run" exclusive; }\n'
        )
        result = parse_module(src)
        assert result.is_ok
        grant = result.danger_ok.nodes[0].may_grants[0]
        assert grant.exclusive is True
        assert grant.via == ("app/site.py::run",)

    # frob:tests strata_core.parse_source kind="unit"
    def test_exclusive_with_file_form_via_is_a_parse_error(self):
        src = (
            "module m\n"
            'node app: trusted { code "app/site.py"; '
            'may "exec" via "app/site.py" exclusive; }\n'
        )
        assert parse_module(src).is_err

    # frob:tests strata_core.parse_source kind="unit"
    def test_exclusive_with_multiple_via_entries_is_a_parse_error(self):
        src = (
            "module m\n"
            'node app: trusted { code "app/site.py", "app/other.py"; '
            'may "exec" via "app/site.py::run", "app/other.py::run" exclusive; }\n'
        )
        assert parse_module(src).is_err

    # frob:tests strata_core.parse_source kind="unit"
    def test_exclusive_with_bare_via_less_may_is_a_parse_error(self):
        src = 'module m\nnode app: trusted { code "app/site.py"; may "exec" exclusive; }\n'
        assert parse_module(src).is_err


class TestStaleViaSymbol:
    """T-1627: a symbol-form `via` entry naming a symbol that resolves to
    nothing is its own loud, distinct finding (`StaleViaSymbolViolation`,
    SYS109) -- never a silent pass and never folded into the ordinary
    undeclared-capability `CapabilityViolation`."""

    # frob:tests src/frob/strata/_effects.py::check_stale_via_symbols kind="unit"
    def test_resolvable_symbol_is_not_flagged(self, tmp_path: Path):
        _write(tmp_path, "app/site.py", "def run(cmd):\n    pass\n")
        module = parse_module(
            'module m\nnode app: trusted { code "app/site.py"; '
            + 'may "exec" via "app/site.py::run";'
            + " }\n"
        ).danger_ok
        model = elaborate(module).danger_ok
        binding = bind_code(model, tmp_path).danger_ok
        assert check_stale_via_symbols(model, binding, tmp_path) == ()

    # frob:tests src/frob/strata/_effects.py::check_stale_via_symbols kind="unit"
    def test_unresolvable_symbol_is_flagged(self, tmp_path: Path):
        _write(tmp_path, "app/site.py", "def run(cmd):\n    pass\n")
        module = parse_module(
            'module m\nnode app: trusted { code "app/site.py"; '
            + 'may "exec" via "app/site.py::gone";'
            + " }\n"
        ).danger_ok
        model = elaborate(module).danger_ok
        binding = bind_code(model, tmp_path).danger_ok
        found = check_stale_via_symbols(model, binding, tmp_path)
        assert found == (
            StaleViaSymbolViolation(node="app", atom="exec", via="app/site.py::gone"),
        )

    # frob:tests src/frob/strata/_effects.py::check_stale_via_symbols kind="unit"
    def test_symbol_matching_a_nested_qualname_resolves(self, tmp_path: Path):
        # `_via_matches_site`'s containment rule: a via entry naming the
        # OUTER symbol resolves as long as ANY declaration under it
        # exists -- resolution mirrors coverage exactly, so a class-level
        # via entry is not spuriously flagged stale just because the
        # class itself has no direct body statement matching its own name.
        _write(
            tmp_path,
            "app/site.py",
            "class Runner:\n    def run(self, cmd):\n        pass\n",
        )
        module = parse_module(
            'module m\nnode app: trusted { code "app/site.py"; '
            + 'may "exec" via "app/site.py::Runner";'
            + " }\n"
        ).danger_ok
        model = elaborate(module).danger_ok
        binding = bind_code(model, tmp_path).danger_ok
        assert check_stale_via_symbols(model, binding, tmp_path) == ()

    # frob:tests src/frob/strata/_effects.py::check_stale_via_symbols kind="unit"
    def test_file_form_via_entries_are_never_checked(self, tmp_path: Path):
        # file-form via has no symbol to resolve -- check_stale_via_symbols
        # only ever inspects entries containing "::".
        _write(tmp_path, "app/site.py", "pass\n")
        module = parse_module(
            'module m\nnode app: trusted { code "app/site.py"; '
            + 'may "exec" via "app/site.py";'
            + " }\n"
        ).danger_ok
        model = elaborate(module).danger_ok
        binding = bind_code(model, tmp_path).danger_ok
        assert check_stale_via_symbols(model, binding, tmp_path) == ()
