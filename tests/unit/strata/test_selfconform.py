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
    SYS_BINDING_TOTALITY,
    SYS_COVERAGE_TOTALITY,
    SYS_DUPLICATE_INTERFACE,
    SYS_PURPOSE_CONTRACT,
    SYS_STALE_DESIGN,
    SYS_UNDECLARED_INTENDED_SURFACE,
    SYS_UNDECLARED_INTERFACE,
    SYS_UNMODELED_CODE,
    SYS110_UNAUDITED_NODES,
    KernelModel,
    MayGrant,
    Node,
    Waiver,
    check_self_conformance,
)
from frob.strata._code_binding import CodeBinding
from frob.strata._effects import _KIND_MAP
from frob.strata._errors import StrataError
from frob.strata._selfconform import (
    _EXTENDED_KINDS,
    _dedupe_sys100_extended_against_core,
    _observed_all_kinds_by_node,
    _observed_extended_kinds_by_node,
    _sorted_capability_files,
)
from frob.strata._selfconform import SelfConformViolation as _SCV
from frob.strata._waive import CONFORMANCE_WAIVER_EXPIRED_RULE, STALE_WAIVER_RULE
from frob.vet._capability import _PATTERNS, SCANNED_LANGUAGES, language_for
from frob.vet._capability_registry import LANGUAGES


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestUndeclaredInterfaceCore:
    """SYS100 for net/fs-write/exec -- delegated verbatim to THREAT004's
    `check_capability_conformance` (docs/strata/selfconform.md#the-three-rules)."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
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
    """SYS100 for eval/ffi/install-hook -- the slice THREAT004
    structurally cannot see (docs/strata/selfconform.md#the-three-rules).
    T-1075: `env` moved OUT of this extended slice into THREAT004's own
    core delegated join (`env-read`/`env-write` -> `env.read`/`env.write`
    via `_effects.py::_KIND_MAP`), same as `fs-read`'s own T-0717
    promotion."""

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


class TestUndeclaredInterfaceCrossPassDedup:
    """T-0266: `_core_undeclared_violations` and `_extended_kind_violations`
    are independent SYS100 producers joined against the same `(node,
    capability)` space -- a capability observed by BOTH passes must
    surface as ONE finding, not two."""

    def test_dedupe_helper_drops_extended_when_core_already_reports_same_site(self):
        """Unit-level: the merge helper itself, isolated from any real
        scan -- two `SelfConformViolation`s sharing `(node, capability)`,
        one from each pass, collapse to zero surviving extended entries
        (core is kept whole by the caller, `_collect_sys_violations`)."""
        core = [
            _SCV(
                rule=SYS_UNDECLARED_INTERFACE,
                node="widget",
                detail="capability 'net' observed at src/frob/widget/_io.py:2 "
                "but not declared",
                capability="net",
            )
        ]
        extended = [
            _SCV(
                rule=SYS_UNDECLARED_INTERFACE,
                node="widget",
                detail="capability 'net' observed but not declared",
                capability="net",
            )
        ]
        assert _dedupe_sys100_extended_against_core(core, extended) == []

    def test_dedupe_helper_keeps_distinct_node_or_capability_sites(self):
        """A distinct `(node, capability)` pair on the extended side is
        never dropped -- only an exact `(node, capability)` match against
        core is filtered."""
        core = [
            _SCV(
                rule=SYS_UNDECLARED_INTERFACE,
                node="widget",
                detail="capability 'net' observed but not declared",
                capability="net",
            )
        ]
        extended = [
            _SCV(
                rule=SYS_UNDECLARED_INTERFACE,
                node="widget",
                detail="capability 'eval' observed but not declared",
                capability="eval",
            ),
            _SCV(
                rule=SYS_UNDECLARED_INTERFACE,
                node="other",
                detail="capability 'net' observed but not declared",
                capability="net",
            ),
        ]
        assert _dedupe_sys100_extended_against_core(core, extended) == extended

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_same_site_observed_by_both_passes_yields_one_finding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """End-to-end via `check_self_conformance`: widen `_EXTENDED_KINDS`
        to also cover `exec` (simulating the kind-vocabulary drift the
        helper's docstring warns about -- `_KIND_MAP`/`_EXTENDED_KINDS`
        are not today statically enforced disjoint) so ONE real
        `subprocess.run` site is genuinely observed by BOTH
        `_core_undeclared_violations` (THREAT004 delegate) and
        `_extended_kind_violations` for the SAME `(node, capability)`.
        `exec` (unlike T-0771's `net-connect`/`net-listen`, which
        `_KIND_MAP` renormalizes to the dotted `net.connect`/`net.listen`
        spelling) is the one `_KIND_MAP` entry that maps to itself, so it
        is still the kind whose raw and THREAT004-normalized spellings are
        identical -- the exact collision this test needs to reproduce.
        Asserts exactly one SYS100 finding survives, not two."""
        import frob.strata._selfconform as selfconform_mod

        monkeypatch.setattr(
            selfconform_mod, "_EXTENDED_KINDS", frozenset({"exec", *_EXTENDED_KINDS})
        )
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import subprocess\nsubprocess.run(['ls'])\n",
        )
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hits = [
            v
            for v in result.danger_ok.violations
            if v.rule == SYS_UNDECLARED_INTERFACE
            and v.node == "widget"
            and v.capability == "exec"
        ]
        assert len(hits) == 1


class TestUndeclaredInterfaceFsReadAlias:
    """T-0304 follow-up: the `fs`/`fs-read` backward-compat alias only
    covered SYS101 (stale design); SYS100 (undeclared interface) still
    fired for a broader `may "fs"` declaration against a read-only
    observation, since `fs-read` is only ever matched against `_EXTENDED_
    KINDS & declared` and a bare `fs` declaration is not itself an
    extended kind. This class exercises the SYS100 direction directly
    (docs/strata/selfconform.md#fs-read-fs-write)."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_broad_fs_declaration_discharges_read_only_observation(
        self, tmp_path: Path
    ):
        """A node that declares the legacy, broader `may "fs"` must not
        fire SYS100 for a real read-only observation: `fs` is a superset
        of `fs-read` and already covers it (live repro: lithos's
        rust_core/regolith_py/stdlib_records/tooling/demos/vscode_ext all
        declare `may "fs"` and all six fired SYS100 for `fs-read` before
        this fix)."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').read_text()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fs",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTERFACE and v.capability == "fs-read"
            for v in result.danger_ok.violations
        )

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_narrow_fs_read_declaration_does_not_cover_fs_read(self, tmp_path: Path):
        """A node that already declares `may "fs-read"` directly is
        unaffected by the alias (it never needed it): a read-only
        observation is discharged with no SYS100 finding, same as
        before this fix."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').read_text()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fs-read",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTERFACE and v.capability == "fs-read"
            for v in result.danger_ok.violations
        )

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_fs_read_only_declaration_still_fires_on_fs_write_observation(
        self, tmp_path: Path
    ):
        """Asymmetry check (the point of the split, module docstring):
        a node declaring ONLY the narrower `may "fs-read"` must still
        fire (via THREAT004's core delegate) when a real fs-write-class
        effect is observed -- narrower declarations never cover broader
        observations, only the reverse."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').write_text('y')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fs-read",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [
            v for v in result.danger_ok.violations if v.rule == SYS_UNDECLARED_INTERFACE
        ]
        # T-0717: a fs-write-class observation now reports the precise
        # "fs.write" spelling, not the old ambiguous bare "fs".
        assert any(v.node == "widget" and v.capability == "fs.write" for v in hit)


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

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_legacy_fs_declaration_discharges_on_read_only_observation(
        self, tmp_path: Path
    ):
        """T-0018 (graphite adoption): graphite's `node core` declares
        `may "fs"` for genuinely-real read-only filesystem access
        (`Path.read_text()`/`json.loads()`, no writes anywhere) and SYS101
        fired "declared but never observed" because the scanner only ever
        emitted the write-derived `fs` kind. A pre-existing bare `may "fs"`
        declaration must be backward-compatibly satisfied by a read-only
        observation now that `fs-read` is a distinct, real kind."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').read_text()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fs",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(v.rule == SYS_STALE_DESIGN for v in result.danger_ok.violations)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_fs_read_declaration_discharges_on_read_only_observation(
        self, tmp_path: Path
    ):
        """A node that declares the new, more honest `may "fs-read"` (rather
        than the legacy bare `fs`) is satisfied directly by a read-only
        observation too."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').read_text()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fs-read",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(v.rule == SYS_STALE_DESIGN for v in result.danger_ok.violations)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_fs_read_declaration_stays_stale_when_only_writes_observed(
        self, tmp_path: Path
    ):
        """The alias is one-directional: `fs-read` declared but only a
        write observed must still be stale (a real distinction, not a
        blanket merge of the two kinds)."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').write_text('y')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fs-read",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [v for v in result.danger_ok.violations if v.rule == SYS_STALE_DESIGN]
        assert any(v.node == "widget" and "fs-read" in v.detail for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    # invariant spec: [INV-026](invariants/INV-026.md)
    def test_stale_design_skips_node_fully_within_graph_exclude(self, tmp_path: Path):
        """T-0310: a node whose ENTIRE `code=` glob resolves only to
        `[graph].exclude`'d paths (aprog-public's activities/slidegen/
        content shape) has no file capability observation could ever see --
        SYS101 'declared but never observed' is a category error for it,
        not real design drift, and must NOT fire no matter what `may` it
        declares."""
        _write(tmp_path, "src/frob/widget/excluded/_io.py", "x = 1\n")
        (tmp_path / "frob.toml").write_text(
            '[graph]\nexclude = ["src/frob/widget/excluded/**"]\n', encoding="utf-8"
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/excluded/**",),
                    may=("net",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(v.rule == SYS_STALE_DESIGN for v in result.danger_ok.violations)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_stale_design_still_fires_when_node_has_non_excluded_file(
        self, tmp_path: Path
    ):
        """The T-0310 skip must NOT weaken SYS101 for a node that has at
        least one observable (non-excluded) file: a genuinely-undeclared-
        vs-observed mismatch on that file must still fire, exactly as
        before -- only the fully-excluded case is skipped."""
        _write(tmp_path, "src/frob/widget/excluded/_io.py", "x = 1\n")
        _write(tmp_path, "src/frob/widget/_main.py", "x = 1\n")
        (tmp_path / "frob.toml").write_text(
            '[graph]\nexclude = ["src/frob/widget/excluded/**"]\n', encoding="utf-8"
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
        hit = [v for v in result.danger_ok.violations if v.rule == SYS_STALE_DESIGN]
        assert any(v.node == "widget" and "net" in v.detail for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    # invariant spec: [INV-026](invariants/INV-026.md)
    def test_via_scoped_grant_stale_while_other_surface_uses_same_kind(
        self, tmp_path: Path
    ):
        """T-1450: SYS101 must judge staleness PER may-via SURFACE, not per
        whole-node kind -- a grant scoped to `_net_a.py` that is never
        exercised there is stale even though `_net_b.py` (a different file
        on the same node) legitimately uses the same `net` kind, because
        that observation cannot discharge a grant whose `via` never covers
        it."""
        _write(tmp_path, "src/frob/widget/_net_a.py", "x = 1\n")
        _write(
            tmp_path,
            "src/frob/widget/_net_b.py",
            "import requests\nrequests.get('x')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net", "net"),
                    may_grants=(
                        MayGrant(atom="net", via=("src/frob/widget/_net_a.py",)),
                        MayGrant(atom="net", via=("src/frob/widget/_net_b.py",)),
                    ),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [v for v in result.danger_ok.violations if v.rule == SYS_STALE_DESIGN]
        assert any(
            v.node == "widget" and "net" in v.detail and "_net_a.py" in v.detail
            for v in hit
        )
        assert not any("_net_b.py" in v.detail for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_via_less_grant_alongside_via_grant_still_discharges_whole_node(
        self, tmp_path: Path
    ):
        """A via-LESS grant on the same node/kind keeps the pre-T-1450
        whole-node join -- it discharges on ANY file's observation,
        exactly like a legacy node with no `may_grants` at all."""
        _write(
            tmp_path,
            "src/frob/widget/_net_b.py",
            "import requests\nrequests.get('x')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net",),
                    may_grants=(MayGrant(atom="net", via=()),),
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


class TestUnmodeledCodeForeignFileGranularity:
    """G4 (docs/audits/strata.md): a FOREIGN file in an already-modeled
    directory (or a loose file directly under `src/frob/`) used to escape
    SYS102 entirely, since the OLD grain marked a whole directory 'owned'
    the moment ANY file in it was non-FOREIGN, and `_top_level_dirs` never
    even iterated files (only directories). Confirmed as a live gap before
    this ticket's fix (a `frob.strata._selfconform.check_self_conformance`
    call against such a fixture returned zero violations)."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_foreign_file_in_otherwise_owned_directory_fires(self, tmp_path: Path):
        """A directory with ONE globbed file and one un-globbed sibling
        must fire SYS102 for the un-globbed file specifically -- the
        directory being "otherwise modeled" must not hide it."""
        _write(tmp_path, "src/frob/widget/_io.py", "x = 1\n")
        _write(tmp_path, "src/frob/widget/backdoor.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/_io.py",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [v for v in result.danger_ok.violations if v.rule == SYS_UNMODELED_CODE]
        assert any(v.node == "src/frob/widget/backdoor.py" for v in hit)
        # The directory as a whole must NOT also fire (it IS partially
        # modeled) -- only the specific unbound file.
        assert not any(v.node == "widget" for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_loose_top_level_file_fires(self, tmp_path: Path):
        """A `.py` file placed directly under `src/frob/` (no
        subdirectory at all) with no node's `code=` glob binding it must
        fire SYS102 -- `_top_level_dirs` only ever walked directories, so
        this file was invisible to every SYS10x rule before the fix."""
        _write(tmp_path, "src/frob/loose_module.py", "x = 1\n")
        _write(tmp_path, "src/frob/widget/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [v for v in result.danger_ok.violations if v.rule == SYS_UNMODELED_CODE]
        assert any(v.node == "src/frob/loose_module.py" for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_loose_top_level_file_discharges_once_globbed(self, tmp_path: Path):
        """The same loose file, once a node's `code=` glob actually binds
        it, produces no SYS102."""
        _write(tmp_path, "src/frob/loose_module.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="loose",
                    trust="trusted",
                    attrs=("code=src/frob/loose_module.py",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNMODELED_CODE for v in result.danger_ok.violations
        )


class TestUnmodeledCodeMissingPackageRoot:
    """T-0211: `_PACKAGE_ROOT` ("src/frob") is frob's own layout -- a repo
    with no `src/frob/` at all (i.e. every non-frob repo) must not have
    SYS102 fire, and must not emit a WARNING-level log about it (sibling-
    repo pilot P2 found this warning firing on every audit run of every
    non-frob repo, reading as "the self-conformance proof is vacuous" even
    though the other checks genuinely ran)."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_missing_package_root_produces_no_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ):
        """A repo with no `src/frob/` directory at all gets zero SYS102
        violations and zero WARNING-level selfconform log records --
        frob's package-root assumption must not leak into generic repos.
        Uses a PRIVATE assignment target (`_x`, not `x`) so T-1113's now-
        mandatory SYS104 has no real public surface to fire on here --
        this test is about SYS102/the package-root leak, not SYS104."""
        _write(tmp_path, "src/other/_io.py", "_x = 1\n")
        model = KernelModel(
            nodes=(Node(id="other", trust="trusted", attrs=("code=src/other/**",)),)
        )
        with caplog.at_level("DEBUG", logger="frob"):
            result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNMODELED_CODE for v in result.danger_ok.violations
        )
        warnings = [r for r in caplog.records if r.levelno >= 30]
        assert not any("selfconform" in r.getMessage() for r in warnings), warnings


class TestNonPythonLanguageWiring:
    """T-0169: the logand.app pilot found `frob sys audit` never scanned
    TS/JS at all -- `bind_code` walks only `.py` (T-0078, correctly, since
    it also backs Python-import conformance), and self-conformance used to
    hand that same `.py`-only binding straight to the capability scan, so
    a TS/JS (or Rust/C-C++) file was invisible to SYS100/SYS101 no matter
    what it did. `_capability_binding` closes that gap; these tests prove
    it end to end through the real `check_self_conformance` entrypoint,
    not just at the binding-helper level."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_typescript_undeclared_capability_fires(self, tmp_path: Path):
        """A `.ts` file with an obvious browser capability (fetch +
        localStorage) bound by a node's `code=` glob is SYS100 -- the exact
        repro that was silently missed before T-0169 (bind_code never even
        saw the file, so `check_self_conformance` returned zero
        violations for an ambient node)."""
        _write(
            tmp_path,
            "src/frob/widget/app.ts",
            "fetch('https://evil.example/x');\nlocalStorage.setItem('a', 'b');\n",
        )
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = {
            v.detail
            for v in result.danger_ok.violations
            if v.rule == SYS_UNDECLARED_INTERFACE and v.node == "widget"
        }
        assert any("fetch_url" in detail for detail in hit)
        assert any("client_storage" in detail for detail in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_typescript_undeclared_capability_discharges_once_declared(
        self, tmp_path: Path
    ):
        """The same TS fixture with `may=("fetch_url", "client_storage")`
        declared produces no SYS100 for those kinds -- proves the TS scan
        result actually reaches the declared/observed join, not just the
        raw scanner."""
        _write(
            tmp_path,
            "src/frob/widget/app.ts",
            "fetch('https://evil.example/x');\nlocalStorage.setItem('a', 'b');\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fetch_url", "client_storage"),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTERFACE and v.node == "widget"
            for v in result.danger_ok.violations
        )

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_typescript_stale_design_fires(self, tmp_path: Path):
        """`may=("fetch_url",)` declared on a node whose `code=`-bound `.ts`
        file never calls `fetch`/etc. is SYS101 for a non-Python language,
        the same drift check Python already had."""
        _write(tmp_path, "src/frob/widget/app.ts", "console.log('noop');\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fetch_url",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [v for v in result.danger_ok.violations if v.rule == SYS_STALE_DESIGN]
        assert any(v.node == "widget" and "fetch_url" in v.detail for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::_sorted_capability_files kind="unit"
    def test_sorted_capability_files_includes_typescript(self, tmp_path: Path):
        """Direct proof `_sorted_capability_files` (the file walk feeding
        `_capability_binding`) actually yields a `.ts` path, not just that
        the end-to-end violation happens to appear for some other reason."""
        _write(tmp_path, "src/frob/widget/app.ts", "fetch('x');\n")
        found = _sorted_capability_files(tmp_path)
        assert any(p.suffix == ".ts" for p in found)

    # frob:tests src/frob/strata/_selfconform.py::_sorted_capability_files kind="unit"
    def test_sorted_capability_files_honors_graph_exclude(self, tmp_path: Path):
        """T-0274: a [graph].exclude dir (e.g. bundled frontend build
        output) must be pruned the same way bind_code's walk is, not just
        the built-in skip-dir set -- graphite FROBLEMS.md 2026-07-18 #1."""
        _write(tmp_path, "server/static/bundle.js", "fetch('x');\n")
        _write(tmp_path, "server/routes.ts", "fetch('x');\n")
        (tmp_path / "frob.toml").write_text(
            '[graph]\nexclude = ["server/static/**"]\n', encoding="utf-8"
        )
        found = _sorted_capability_files(tmp_path)
        rels = {p.relative_to(tmp_path).as_posix() for p in found}
        assert "server/routes.ts" in rels
        assert "server/static/bundle.js" not in rels


class TestCoreUndeclaredInterfaceNonPython:
    """REVIEWER-CAUGHT REJECT ROUND (T-0169): the extended-kinds/SYS101
    fix above still left `_core_undeclared_violations` (net/fs-write/exec,
    delegated to THREAT004's `check_capability_conformance`) on the raw
    Python-only `bind_code` binding -- so a `.ts` `axios.get(...)` or a
    `.rs` `Command::new(...).spawn()` under a `code=` glob produced ZERO
    SYS100 and a SPURIOUS SYS102 instead, exactly reproducing the original
    bug for the raw net/exec/fs-write kinds the pilot most needs caught.
    `check_capability_conformance` is language-generic (`_effects.py::
    _line_effects` uses `language_for`/`_PATTERNS`, no Python-specific
    parsing) so this was purely a wiring omission, not a real scope
    boundary -- `check_self_conformance` now hands `_core_undeclared_
    violations` and `_unmodeled_violations` the SAME `_capability_binding`
    superset as SYS100-extended/SYS101."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_typescript_core_net_undeclared_fires(self, tmp_path: Path):
        """A `.ts` file calling `axios.get(...)` (raw `net`, THREAT004's
        core delegated kind) with no `may` declaration is SYS100, and NOT
        also a spurious SYS102 for the same directory."""
        _write(
            tmp_path,
            "src/frob/widget/app.ts",
            "import axios from 'axios';\naxios.get('https://evil.example/x');\n",
        )
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        violations = result.danger_ok.violations
        assert any(
            v.rule == SYS_UNDECLARED_INTERFACE
            and v.node == "widget"
            and "net" in v.detail
            for v in violations
        )
        assert not any(v.rule == SYS_UNMODELED_CODE for v in violations)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_typescript_core_net_discharges_once_declared(self, tmp_path: Path):
        """The same `axios.get(...)` fixture with `may=("net",)` declared
        produces no SYS100 for `net` -- proves the TS core-kind scan
        actually reaches the declared/observed join, not just the raw
        scanner."""
        _write(
            tmp_path,
            "src/frob/widget/app.ts",
            "import axios from 'axios';\naxios.get('https://evil.example/x');\n",
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
            v.rule == SYS_UNDECLARED_INTERFACE and v.node == "widget"
            for v in result.danger_ok.violations
        )

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_rust_core_exec_undeclared_fires(self, tmp_path: Path):
        """A `.rs` file calling `Command::new(...).spawn()` (raw `exec`)
        with no `may` declaration is SYS100, and NOT also a spurious
        SYS102 for the same directory."""
        _write(
            tmp_path,
            "src/frob/widget/main.rs",
            'use std::process::Command;\nfn f() { Command::new("ls").spawn(); }\n',
        )
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        violations = result.danger_ok.violations
        assert any(
            v.rule == SYS_UNDECLARED_INTERFACE
            and v.node == "widget"
            and "exec" in v.detail
            for v in violations
        )
        assert not any(v.rule == SYS_UNMODELED_CODE for v in violations)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_rust_core_exec_discharges_once_declared(self, tmp_path: Path):
        """The same `Command::new(...).spawn()` fixture with
        `may=("exec",)` declared produces no SYS100 for `exec`."""
        _write(
            tmp_path,
            "src/frob/widget/main.rs",
            'use std::process::Command;\nfn f() { Command::new("ls").spawn(); }\n',
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("exec",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTERFACE and v.node == "widget"
            for v in result.danger_ok.violations
        )


class TestLanguageCoverageDriftLock:
    # frob:tests src/frob/strata/_selfconform.py::_sorted_capability_files kind="unit"
    # frob:waive COV006 reason="T-0536: SCANNED_LANGUAGES (frob.vet._capability) and \
    # LANGUAGES (frob.vet._capability_registry) are both module-level constants \
    # asserted for set equality here -- neither is ever CALLED by this test's body, so \
    # there is no call-graph edge for the graph to find regardless of which symbol \
    # frob:tests names. Retargeting the directive straight at SCANNED_LANGUAGES was \
    # tried and rejected: DRIFT002 then reports the ref as unresolvable (module-level \
    # assignments are not graph nodes), trading one false positive for another. Same \
    # module-constant-drift-lock shape as T-0516's tests/test_gates.py waiver."
    def test_scanned_languages_equals_registry_languages(self):
        """T-0169 drift lock: the set of languages self-conformance (and
        `vet`) actually reach via `language_for`/`_EXT_LANGUAGE` must equal
        the set `_capability_registry.LANGUAGES` claims support (T-0158's
        coverage matrix). If a new language column is ever added to the
        registry without a matching `_EXT_LANGUAGE` extension entry (or
        vice versa), this fails immediately instead of that language
        silently going unscanned the way TS/JS did before this ticket.

        T-0170 adds `kotlin` as a fully registry-backed language (its
        `_DangerousOperation`/`_MatrixExcuse` entries live in
        `_capability_registry.py` like every other language), so the lock
        stays the strict equality it always was -- no carve-out."""
        assert SCANNED_LANGUAGES == frozenset(LANGUAGES)

    def test_language_for_is_consistent_with_scanned_languages(self):
        """Every language `language_for` can ever return is a member of
        `SCANNED_LANGUAGES` -- keeps the constant honest against the
        function it is meant to characterize, not just hand-copied."""
        samples = {
            "a.py": "python",
            "a.ts": "typescript",
            "a.tsx": "typescript",
            "a.js": "typescript",
            "a.rs": "rust",
            "a.c": "c-cpp",
            "a.cpp": "c-cpp",
            "a.kt": "kotlin",
            "a.kts": "kotlin",
        }
        for name, expected in samples.items():
            resolved = language_for(Path(name))
            assert resolved == expected
            assert resolved in SCANNED_LANGUAGES


class TestExtendedKindsDriftLock:
    # frob:tests src/frob/strata/_selfconform.py::_observed_extended_kinds_by_node \
    # kind="unit"
    # frob:waive COV006 reason="T-0536: _EXTENDED_KINDS/_KIND_MAP/_PATTERNS are \
    # module-level constants this test asserts set operations over -- never CALLED, so \
    # there is no call-graph edge regardless of binding. Retargeting straight at \
    # _EXTENDED_KINDS was tried and rejected: DRIFT002 then reports the ref as \
    # unresolvable (module-level assignments are not graph nodes), trading one false \
    # positive for another. Same module-constant-drift-lock shape as T-0516's \
    # tests/test_gates.py waiver."
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

    def test_observed_extended_kinds_by_node_only_ever_yields_extended_kinds(
        self, tmp_path: Path
    ):
        """`_observed_extended_kinds_by_node` intersects its raw scan against
        `_EXTENDED_KINDS` (the `& _EXTENDED_KINDS` in its body) -- exercise it
        against a real file containing an `eval(` needle (a `_KIND_MAP`-
        disjoint kind per the test above) and confirm the observed set is
        both non-empty and a subset of `_EXTENDED_KINDS`, never leaking a
        `_KIND_MAP` kind through. Ties the drift-lock constants to the
        function that actually consumes them, not just to each other."""
        src = tmp_path / "danger.py"
        src.write_text("def f(x):\n    return eval(x)\n")
        binding = CodeBinding(owner={"danger.py": "node.danger"})

        observed = _observed_extended_kinds_by_node(binding, tmp_path)

        assert observed == {"node.danger": frozenset({"eval"})}
        assert observed["node.danger"] <= _EXTENDED_KINDS
        assert observed["node.danger"].isdisjoint(_KIND_MAP.keys())

    # frob:tests tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock.test_observed_all_kinds_by_node_normalizes_through_kind_map  # noqa: E501
    def test_observed_all_kinds_by_node_normalizes_through_kind_map(
        self, tmp_path: Path
    ):
        """`_observed_all_kinds_by_node`'s SYS101 sibling: a real
        `subprocess.run(...)` call scans as the raw `"exec"` kind, which
        `_KIND_MAP` maps to itself (`"exec" -> "exec"`) -- confirms the
        normalized-view wrapper reaches a `_KIND_MAP`-covered kind end to
        end, not just `_observed_extended_kinds_by_node`'s disjoint-kind
        case above."""
        src = tmp_path / "spawn.py"
        src.write_text('import subprocess\ndef f():\n    subprocess.run(["ls"])\n')
        binding = CodeBinding(owner={"spawn.py": "node.spawn"})

        observed = _observed_all_kinds_by_node(binding, tmp_path)

        assert observed == {"node.spawn": frozenset({_KIND_MAP["exec"]})}


class TestWaiverChannel:
    """T-0174: a `Node.waives` entry suppresses its matching SYS finding
    (kept in `report.waived`, never dropped) and a waiver matching nothing
    is reported as a new SYSWAIVE002 violation (drift-lock)."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_matching_waiver_moves_violation_to_waived(self, tmp_path: Path):
        """SYS100 is multi-instance-per-node (T-0174 REJECT round), so the
        waiver must name the exact capability kind (`net.connect`, T-0771's
        precise spelling now that `net` is wired -- matching
        `requests.get`'s observed effect) as a `SYS100:net.connect` sub-
        target -- a bare `SYS100` waiver would be an elaborate-adjacent-
        invalid value this test does not construct."""
        _write(
            tmp_path, "src/frob/widget/_io.py", "import requests\nrequests.get('x')\n"
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    waives=(
                        Waiver(
                            rule=f"{SYS_UNDECLARED_INTERFACE}:net.connect",
                            reason="pilot fixture, tracked in T-0174",
                        ),
                    ),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTERFACE for v in result.danger_ok.violations
        )
        waived = [
            v
            for v in result.danger_ok.waived
            if v.rule == SYS_UNDECLARED_INTERFACE and v.node == "widget"
        ]
        assert len(waived) == 1
        assert "WAIVED" in waived[0].detail
        assert "pilot fixture, tracked in T-0174" in waived[0].detail
        assert "SYS100:net.connect" in waived[0].detail

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_stale(self, tmp_path: Path):
        """`widget` declares no capability at all, so SYS100:net never
        fires -- the waiver on it matches zero findings and must be
        reported as a new SYSWAIVE002 violation, not silently accepted."""
        _write(tmp_path, "src/frob/widget/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    waives=(
                        Waiver(
                            rule=f"{SYS_UNDECLARED_INTERFACE}:net",
                            reason="never fires -- stale waiver litmus",
                        ),
                    ),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        stale = [v for v in result.danger_ok.violations if v.rule == STALE_WAIVER_RULE]
        assert len(stale) == 1
        assert stale[0].node == "widget"

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_sub_target_waiver_does_not_suppress_a_different_kind(self, tmp_path: Path):
        """T-0174 REJECT round, the critical fixture at the
        `check_self_conformance` layer: `widget` observes BOTH `net.connect`
        (`requests.get`, T-0771's precise spelling) and `exec`
        (`subprocess.run`) undeclared -- two SYS100 findings on the same
        node. Waiving only `SYS100:net.connect` must NOT suppress the
        `SYS100:exec` finding."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import requests\nimport subprocess\n"
            "requests.get('x')\nsubprocess.run(['ls'])\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    waives=(
                        Waiver(
                            rule=f"{SYS_UNDECLARED_INTERFACE}:net.connect",
                            reason="net leg tracked separately, litmus fixture",
                        ),
                    ),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        remaining = [
            v for v in result.danger_ok.violations if v.rule == SYS_UNDECLARED_INTERFACE
        ]
        assert len(remaining) == 1
        assert remaining[0].capability == "exec"
        waived = [
            v for v in result.danger_ok.waived if v.rule == SYS_UNDECLARED_INTERFACE
        ]
        assert len(waived) == 1
        assert waived[0].capability == "net.connect"


@pytest.mark.xdist_group(name="selfconform-full-repo-scan")
class TestRealGateGreen:
    """`xdist_group` (T-drafted for this suite-repair pass): this class
    and `TestCoverageTotality` below both run a full, unrestricted
    repo-tree capability scan (measured ~400MB peak RSS each, standalone)
    -- pinning both to the SAME xdist worker keeps their peaks from
    landing concurrently on two separate workers, which is the scenario
    that reproduced a worker crash (gw1/gw0, different runs, same full-
    suite `make coverage` shape) even though each test is individually
    clean and fast in isolation. Sharing a group serializes the two
    within that one worker instead of eliminating either scan's cost."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance \
    # kind="integration"
    def test_repo_design_and_declarations_are_self_conformant(self):
        """`design/frob.strata`'s real `code`/`may` declarations, run
        against the REAL repo tree (T-1091: the WHOLE tree, not just
        `src/frob/`), produce zero SYS100/SYS101/SYS102/SYS103/SYS104
        violations -- the T-0150 gate-green assertion, UNCHANGED and
        still strict (T-0667: SYS103/SYS-COV joins it at zero too --
        `_coverage_totality_scan_prefix` is now UNRESTRICTED as of
        T-1091, docs/modules/strata.md#sys-cov-coverage-totality-sys103-
        t-0667, so it DOES scan `tests/**`/`scripts/**`/
        `frob-core/src/**`/`strata-core/src/**` now, and stays zero
        there because T-1079 modeled all four as real nodes). Skips
        (does not xfail) when the native strata_core extension isn't
        installed, matching every other `.strata`-parsing test's guard in
        this suite."""
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


class TestBindingErrorPropagation:
    """`check_self_conformance` must propagate `bind_code`'s error
    unchanged (deny by default, never a silent partial scan) --
    docstring's `Err` clause."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_ambiguous_code_binding_propagates_as_err(self, tmp_path: Path):
        """Two nodes whose `code=` globs both match the same file make
        `bind_code` return `Err(AmbiguousCodeBinding)`; that must surface
        unchanged from `check_self_conformance`, not be swallowed."""
        _write(tmp_path, "src/frob/widget/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(id="a", trust="trusted", attrs=("code=src/frob/widget/**",)),
                Node(id="b", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_err
        assert result.danger_err == StrataError.AmbiguousCodeBinding


class TestModeQualifiedFsStaleDesign:
    """T-0717 acceptance clause 1: a node declaring precisely `may
    "fs.read"` and whose bound code only reads discharges SYS101 narrowly
    (only `fs.read` itself can satisfy it)."""

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_fs_read_declaration_discharges_on_read_only_code(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').read_text()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fs.read",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(v.rule == SYS_STALE_DESIGN for v in result.danger_ok.violations)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_fs_read_declaration_stays_stale_when_only_writes_observed(
        self, tmp_path: Path
    ):
        """The precise declaration does NOT discharge on the OTHER mode --
        a `fs.read`-only declarer whose code only writes is still stale."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').write_text('y')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("fs.read",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [v for v in result.danger_ok.violations if v.rule == SYS_STALE_DESIGN]
        assert any(v.node == "widget" and v.capability == "fs.read" for v in hit)


# invariant spec: [INV-048](invariants/INV-048.md)
class TestCoverageTotality:
    """SYS103 (SYS-COV, T-0667): a `FOREIGN` file the binding-aware
    scanner observes ANY capability in fires, on any root -- not just
    `src/frob/` (docs/modules/strata.md#sys-cov-coverage-totality-sys103-t-0667).

    `test_repo_unrestricted_scan_is_clean` below shares the
    `selfconform-full-repo-scan` xdist group with `TestRealGateGreen` --
    see that class's docstring for why (both run a ~400MB full-repo scan;
    grouping keeps the two peaks off separate concurrent workers)."""

    # frob:tests src/frob/strata/_selfconform.py::_coverage_totality_violations \
    # kind="unit"
    def test_foreign_file_with_capability_fires_sys103(self, tmp_path: Path):
        """A file with an observed `net` effect and no node's `code=`
        glob binding it fires SYS103, even though SYS100/SYS101 (which
        only reconcile BOUND files) have nothing to say about it."""
        _write(
            tmp_path,
            "src/frob/orphan/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        model = KernelModel(nodes=())
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [
            v for v in result.danger_ok.violations if v.rule == SYS_COVERAGE_TOTALITY
        ]
        assert any(
            v.node == "src/frob/orphan/_io.py" and "net" in v.detail for v in hit
        )

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_bound_file_discharges_sys103(self, tmp_path: Path):
        """The same capable file, once a node's `code=` glob binds it,
        produces no SYS103 -- 'every module bound to a node' is silent --
        REGARDLESS of whether that node declares `may` for the observed
        kind. SYS103's only question is binding, never conformance
        (module docstring); the node here declares NO `may` at all, so
        SYS100 fires for the SAME site while SYS103 stays silent,
        proving the two rules are answering genuinely different
        questions rather than one masking the other."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import subprocess\nsubprocess.run(['ls'])\n",
        )
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_COVERAGE_TOTALITY for v in result.danger_ok.violations
        )
        assert any(
            v.rule == SYS_UNDECLARED_INTERFACE for v in result.danger_ok.violations
        )

    # frob:tests src/frob/strata/_selfconform.py::_coverage_totality_violations \
    # kind="unit"
    def test_foreign_capability_free_file_does_not_fire_sys103(self, tmp_path: Path):
        """A `FOREIGN` file with zero observed capabilities (plain data)
        does not fire SYS103 -- only capable-but-unbound code is the
        failure mode SYS-COV catches (SYS102 still catches this same file
        under its own, frob-tree-only rule -- unaffected here)."""
        _write(tmp_path, "src/frob/orphan/_io.py", "x = 1\n")
        model = KernelModel(nodes=())
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_COVERAGE_TOTALITY for v in result.danger_ok.violations
        )

    # frob:tests src/frob/strata/_selfconform.py::_coverage_totality_violations \
    # kind="unit"
    def test_fires_outside_src_frob_layout(self, tmp_path: Path):
        """SYS103 is repo-general, unlike SYS102's `_PACKAGE_ROOT`
        hardcoding: a capable, unbound file OUTSIDE `src/frob/` entirely
        still fires."""
        _write(
            tmp_path,
            "app/widget/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        model = KernelModel(nodes=())
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [
            v for v in result.danger_ok.violations if v.rule == SYS_COVERAGE_TOTALITY
        ]
        assert any(v.node == "app/widget/_io.py" for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::_coverage_totality_violations \
    # kind="unit"
    def test_sys103_waivable_as_bare_rule(self, tmp_path: Path):
        """A bare `waive "SYS103"` clause suppresses the finding -- SYS103
        is NOT in `MULTI_INSTANCE_WAIVER_FAMILIES`, so it must not require
        a sub-target, unlike SYS100/SYS101 (docs/strata/selfconform.md's
        SYS102 waiver precedent: `apply_waivers` reads `Node.waives`
        keyed by `node.id`, and a SYS102/SYS103 finding's `node` field is
        the unbound file's OWN path, matching SYS102's `waive "SYS102"`
        convention -- a `Node` entry with id == the file path, `code=`-
        free, exists purely to carry the waiver, same shape a `.strata`
        author would declare)."""
        _write(
            tmp_path,
            "src/frob/orphan/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="src/frob/orphan/_io.py",
                    trust="trusted",
                    waives=(Waiver(rule=SYS_COVERAGE_TOTALITY, reason="test waiver"),),
                ),
            ),
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_COVERAGE_TOTALITY for v in result.danger_ok.violations
        )
        assert any(v.rule == SYS_COVERAGE_TOTALITY for v in result.danger_ok.waived)

    # frob:tests src/frob/strata/_selfconform.py::_coverage_totality_violations \
    # kind="unit"
    @pytest.mark.xdist_group(name="selfconform-full-repo-scan")
    def test_repo_unrestricted_scan_is_clean(self, monkeypatch: pytest.MonkeyPatch):
        """T-1079 (SYS103's 264-finding follow-up), STILL GREEN post-T-1091:
        `design/frob.strata` models `tests/**`/`scripts/**`/
        `frob-core/src/**`/`strata-core/src/**` (the `testsuite`/
        `scripts_ops`/`strata_core_native`/`frob_core_native` nodes,
        docs/modules/strata.md's "Modeled: `_PACKAGE_ROOT` restriction's
        264-finding follow-up" section). `_coverage_totality_scan_prefix`
        is now UNCONDITIONALLY unrestricted (T-1091 dropped the
        `_PACKAGE_ROOT` carve-out entirely, closing the gap this test
        used to prove existed only in the model, not yet in the live
        gate) -- the `monkeypatch.setattr` below is now a no-op (it sets
        the function to the SAME `lambda r: None` behavior it already
        has) but is kept so this test still independently pins "an
        unrestricted scan against the real design/real tree is clean"
        even if `_coverage_totality_scan_prefix` is ever re-restricted in
        the future, without depending on that function's current
        default. `TestRealGateGreen` covers the same zero-violations
        claim through the now-unrestricted PRODUCTION path (no
        monkeypatch needed there since T-1091)."""
        pytest.importorskip("strata_core")
        from frob.strata import _selfconform as sc
        from frob.strata._design_load import load_design_ids
        from frob.strata._sysdoc import merge_models

        root = Path(__file__).resolve().parents[3]
        ids = load_design_ids(root, "design")
        assert not ids.errors, f"design load failed: {ids.errors}"
        model = merge_models(ids.models)

        monkeypatch.setattr(sc, "_coverage_totality_scan_prefix", lambda r: None)

        result = sc.check_self_conformance(model, root)
        assert result.is_ok, result.err
        violations = result.danger_ok.violations
        assert violations == (), [(v.rule, v.node, v.detail) for v in violations]


class TestDuplicateInterface:
    """SYS108 (T-1624): a node's `interface=` attrs must not name the same
    symbol more than once -- the elaborated-model shape two byte-identical
    `attr interface=[...]` blocks on one node produce."""

    # frob:tests src/frob/strata/_selfconform.py::_duplicate_interface_violations \
    # kind="unit"
    def test_duplicate_symbol_fires(self, tmp_path: Path):
        """A node whose `interface=` attrs repeat a name (the shape two
        duplicate `attr interface=[...]` blocks elaborate into) fires
        SYS108, naming the duplicated symbol."""
        _write(tmp_path, "src/frob/widget/_io.py", "def public_fn():\n    pass\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=(
                        "code=src/frob/widget/**",
                        "interface=public_fn",
                        "interface=public_fn",
                    ),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hits = [
            v for v in result.danger_ok.violations if v.rule == SYS_DUPLICATE_INTERFACE
        ]
        assert len(hits) == 1
        assert hits[0].node == "widget"
        assert hits[0].capability == "public_fn"

    # frob:tests src/frob/strata/_selfconform.py::_duplicate_interface_violations \
    # kind="unit"
    def test_grammar_parsed_duplicate_blocks_fire_not_lexical_text(
        self, tmp_path: Path
    ) -> None:
        """SYS108 must judge duplication from the REAL parsed grammar
        (`Node.attrs`, via `load_design_ids`/`merge_models`), not a text
        scan of the raw `.strata` source: a `//` comment line that happens
        to contain the literal text `attr interface=[public_fn];` is NOT a
        declaration at all under this language's grammar (comments are
        `//`-prefixed only, no block-comment form -- `strata-core/src/
        parse/lexer.rs`) and must not be counted, while the two REAL
        (non-commented) `attr interface=[...]` blocks on the same node
        must still fire exactly once for the one genuinely duplicated
        symbol."""
        pytest.importorskip("strata_core")
        from frob.strata._design_load import load_design_ids
        from frob.strata._sysdoc import merge_models

        _write(tmp_path, "src/frob/widget/_io.py", "def public_fn():\n    pass\n")
        design_dir = tmp_path / "design"
        design_dir.mkdir()
        (design_dir / "widget.strata").write_text(
            "module widget\n"
            "node widget : trusted {\n"
            "    // NOT a real declaration -- a comment that merely LOOKS\n"
            "    // like one: attr interface=[public_fn];\n"
            '    code "src/frob/widget/**";\n'
            "    attr interface=[\n"
            "        public_fn,\n"
            "    ];\n"
            "    attr interface=[\n"
            "        public_fn,\n"
            "    ];\n"
            "}\n",
            encoding="utf-8",
        )
        ids = load_design_ids(tmp_path, "design")
        assert not ids.errors, f"design load failed: {ids.errors}"
        model = merge_models(ids.models)

        result = check_self_conformance(model, tmp_path)
        assert result.is_ok, result.err
        hits = [
            v for v in result.danger_ok.violations if v.rule == SYS_DUPLICATE_INTERFACE
        ]
        # Exactly one duplicated symbol, exactly one finding -- the comment
        # contributed nothing (grammar-aware), and the two REAL blocks each
        # contribute one `interface=public_fn` attr, giving 2 total (one
        # duplicate pair), not 3 (which a lexical text-count including the
        # comment line would have produced).
        assert len(hits) == 1
        assert hits[0].capability == "public_fn"

    # frob:tests src/frob/strata/_selfconform.py::_duplicate_interface_violations \
    # kind="unit"
    def test_no_duplicates_silent(self, tmp_path: Path):
        """A node whose `interface=` attrs name every symbol exactly once
        fires no SYS108 at all."""
        _write(tmp_path, "src/frob/widget/_io.py", "def public_fn():\n    pass\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**", "interface=public_fn"),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_DUPLICATE_INTERFACE for v in result.danger_ok.violations
        )


class TestUndeclaredIntendedSurface:
    """SYS110 (T-1629): `interface=` is hand-declared INTENT, not a
    generated mirror (the deleted SYS104's own shape) -- a node that has
    opted in (non-empty `interface=`) must declare every real public
    symbol; a node with NO `interface=` attrs at all has not opted in and
    is silently skipped (phased per-node migration, not a big-bang
    requirement)."""

    # frob:tests \
    # src/frob/strata/_selfconform.py::_undeclared_intended_surface_violations \
    # kind="unit"
    def test_real_symbol_outside_declared_set_fires(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "def declared_fn():\n    pass\n\n\ndef undeclared_fn():\n    pass\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**", "interface=declared_fn"),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok, result.err
        hits = [
            v
            for v in result.danger_ok.violations
            if v.rule == SYS_UNDECLARED_INTENDED_SURFACE
        ]
        assert len(hits) == 1
        assert hits[0].node == "widget"
        assert hits[0].capability == "undeclared_fn"

    # frob:tests \
    # src/frob/strata/_selfconform.py::_undeclared_intended_surface_violations \
    # kind="unit"
    def test_declared_superset_is_silent(self, tmp_path: Path) -> None:
        """Declaring MORE than the real surface (an aspirational/future
        entry) is not itself a SYS110 finding -- only the reverse
        direction (real beyond declared) fires."""
        _write(tmp_path, "src/frob/widget/_io.py", "def declared_fn():\n    pass\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=(
                        "code=src/frob/widget/**",
                        "interface=declared_fn",
                        "interface=not_yet_written_fn",
                    ),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTENDED_SURFACE
            for v in result.danger_ok.violations
        )

    # frob:tests \
    # src/frob/strata/_selfconform.py::_undeclared_intended_surface_violations \
    # kind="unit"
    def test_node_with_no_interface_attrs_is_skipped(self, tmp_path: Path) -> None:
        """A node with ZERO `interface=` attrs has not opted into
        hand-declared intent yet -- the phased-migration design point,
        not "declares an empty surface" (which would fire on every
        public symbol)."""
        _write(tmp_path, "src/frob/widget/_io.py", "def public_fn():\n    pass\n")
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTENDED_SURFACE
            for v in result.danger_ok.violations
        )

    # frob:tests src/frob/strata/_selfconform.py::SYS110_UNAUDITED_NODES kind="unit"
    def test_unaudited_node_is_silenced_regardless_of_drift(
        self, tmp_path: Path
    ) -> None:
        """A node named in `SYS110_UNAUDITED_NODES` is silenced even
        though its declared set does not cover its real surface -- the
        T-1629 migration-boundary exemption, distinct from the "not
        opted in at all" skip above."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "def declared_fn():\n    pass\n\n\ndef undeclared_fn():\n    pass\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="cli",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**", "interface=declared_fn"),
                ),
            )
        )
        assert "cli" in SYS110_UNAUDITED_NODES
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_UNDECLARED_INTENDED_SURFACE
            for v in result.danger_ok.violations
        )


class TestPurposeContract:
    """SYS105 (T-0669): a node's `purpose=` attr bounds its allowed
    observed effect kinds -- opt-in only (module docstring's SYS105
    scope cut)."""

    # frob:tests src/frob/strata/_selfconform.py::_purpose_contract_violations \
    # kind="unit"
    def test_effect_outside_profile_fires(self, tmp_path: Path):
        """A `purpose=logging` node that opens a network socket fires
        SYS105 -- the design doc's "purpose drift" evasion row."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    may=("net",),
                    attrs=("code=src/frob/widget/**", "purpose=logging"),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hits = [
            v for v in result.danger_ok.violations if v.rule == SYS_PURPOSE_CONTRACT
        ]
        assert any(v.capability == "net.connect" for v in hits)

    # frob:tests src/frob/strata/_selfconform.py::_purpose_contract_violations \
    # kind="unit"
    def test_read_only_purpose_with_write_effect_fires(self, tmp_path: Path):
        """T-0669's own acceptance wording, verbatim: a node whose
        `purpose=read-only` profile declares a read-only effect profile
        but whose bound code performs a WRITE fires SYS105."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').write_text('y')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    may=("fs.write",),
                    attrs=("code=src/frob/widget/**", "purpose=read-only"),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hits = [
            v for v in result.danger_ok.violations if v.rule == SYS_PURPOSE_CONTRACT
        ]
        assert any(v.capability == "fs.write" for v in hits)

    # frob:tests src/frob/strata/_selfconform.py::_purpose_contract_violations \
    # kind="unit"
    def test_unrecognized_profile_fires(self, tmp_path: Path):
        """A typo'd `purpose=` profile name is itself a finding -- never
        silently treated as permissive."""
        _write(tmp_path, "src/frob/widget/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**", "purpose=logg1ng"),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hits = [
            v for v in result.danger_ok.violations if v.rule == SYS_PURPOSE_CONTRACT
        ]
        assert any("logg1ng" in v.detail for v in hits)

    # frob:tests src/frob/strata/_selfconform.py::_purpose_contract_violations \
    # kind="unit"
    def test_effect_inside_profile_is_silent(self, tmp_path: Path):
        """A `purpose=read-only` node that only reads a file fires no
        SYS105."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from pathlib import Path\nPath('x').read_text()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    may=("fs.read",),
                    attrs=("code=src/frob/widget/**", "purpose=read-only"),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_PURPOSE_CONTRACT for v in result.danger_ok.violations
        )

    # frob:tests src/frob/strata/_selfconform.py::_purpose_contract_violations \
    # kind="unit"
    def test_node_with_no_purpose_attr_is_never_checked(self, tmp_path: Path):
        """A node declaring no `purpose=` attr at all is silently skipped
        (opt-in scope cut)."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    may=("net",),
                    attrs=("code=src/frob/widget/**",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_PURPOSE_CONTRACT for v in result.danger_ok.violations
        )


class TestBindingTotality:
    """SYS106 (T-0670): a `FOREIGN` file reachable via resolved local
    imports from a bound node's own files, with an observed capability,
    fires -- "logic laundered into an unbound file"."""

    # frob:tests src/frob/strata/_selfconform.py::_binding_totality_violations \
    # kind="unit"
    def test_laundered_capable_file_fires(self, tmp_path: Path):
        """A bound node's file imports an unmodeled helper module that
        itself performs a capable effect -- the helper is FOREIGN but
        reachable, so SYS106 fires on it."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from . import _helper\n_helper.do_it()\n",
        )
        _write(
            tmp_path,
            "src/frob/widget/_helper.py",
            "import requests\n\n\ndef do_it():\n    requests.get('x')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget", trust="trusted", attrs=("code=src/frob/widget/_io.py",)
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hits = [
            v for v in result.danger_ok.violations if v.rule == SYS_BINDING_TOTALITY
        ]
        assert any(v.node == "src/frob/widget/_helper.py" for v in hits)

    # frob:tests src/frob/strata/_selfconform.py::_binding_totality_violations \
    # kind="unit"
    def test_unreachable_foreign_file_does_not_fire_sys106(self, tmp_path: Path):
        """A capable FOREIGN file that no bound file imports (unreachable)
        does not fire SYS106, even though SYS103 catches it under its own
        blanket unbound-and-capable rule."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "def public_fn():\n    pass\n",
        )
        _write(
            tmp_path,
            "src/frob/orphan/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_BINDING_TOTALITY and v.node == "src/frob/orphan/_io.py"
            for v in result.danger_ok.violations
        )

    # frob:tests src/frob/strata/_selfconform.py::_binding_totality_violations \
    # kind="unit"
    def test_bound_reachable_file_does_not_fire_sys106(self, tmp_path: Path):
        """A reachable file that IS bound to some node (any node, not
        just the reaching one) never fires SYS106 -- the rule is about
        binding, not about which specific node owns it."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "from ..other import _helper\n_helper.do_it()\n",
        )
        _write(
            tmp_path,
            "src/frob/other/_helper.py",
            "import requests\n\n\ndef do_it():\n    requests.get('x')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget", trust="trusted", attrs=("code=src/frob/widget/_io.py",)
                ),
                Node(
                    id="other",
                    trust="trusted",
                    may=("net",),
                    attrs=("code=src/frob/other/**",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_BINDING_TOTALITY for v in result.danger_ok.violations
        )


class TestConformanceWaiverStaleness:
    """T-0671: a SYS104/SYS105/SYS106 waiver older than its
    `expires:YYYY-MM-DD` staleness bound is treated as EXPIRED -- the
    underlying obligation re-fires and a SYSWAIVE003 finding names the
    expired waiver (acceptance criterion [0]). A conformance waiver's
    valid (unexpired) state still surfaces in `report.waived`, which
    `sys_runner.py` prints unconditionally every run -- the floor view
    acceptance criterion [1]."""

    # frob:tests src/frob/strata/_selfconform.py::_apply_conformance_waiver_staleness \
    # kind="unit"
    def test_expired_waiver_refires_and_is_flagged(self, tmp_path: Path):
        """A `purpose=logging` waiver with a PAST `expires:` date does
        NOT suppress the SYS105 finding -- it re-fires, plus a
        SYSWAIVE003 finding names the expired waiver."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    may=("net",),
                    attrs=("code=src/frob/widget/**", "purpose=logging"),
                    waives=(
                        Waiver(
                            rule="SYS105:net.connect",
                            reason="stale debt, expires:2020-01-01",
                        ),
                    ),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        violations = result.danger_ok.violations
        assert any(v.rule == SYS_PURPOSE_CONTRACT for v in violations)
        assert any(v.rule == CONFORMANCE_WAIVER_EXPIRED_RULE for v in violations)
        assert not any(v.rule == SYS_PURPOSE_CONTRACT for v in result.danger_ok.waived)

    # frob:tests src/frob/strata/_selfconform.py::_apply_conformance_waiver_staleness \
    # kind="unit"
    def test_missing_expiry_marker_treated_as_expired(self, tmp_path: Path):
        """A SYS105 waiver with NO `expires:` marker at all is treated
        identically to an expired one -- staleness-dating is mandatory
        for the conformance families, not optional."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    may=("net",),
                    attrs=("code=src/frob/widget/**", "purpose=logging"),
                    waives=(Waiver(rule="SYS105:net.connect", reason="undated debt"),),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        violations = result.danger_ok.violations
        assert any(v.rule == SYS_PURPOSE_CONTRACT for v in violations)
        assert any(v.rule == CONFORMANCE_WAIVER_EXPIRED_RULE for v in violations)

    # frob:tests src/frob/strata/_selfconform.py::_apply_conformance_waiver_staleness \
    # kind="unit"
    def test_unexpired_waiver_still_visible_in_floor_view(self, tmp_path: Path):
        """A conformance waiver with a FUTURE `expires:` date suppresses
        the finding as normal, but the waiver stays fully visible in
        `report.waived` -- the un-droppable floor view T-0671's
        acceptance criterion [1] requires."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    may=("net",),
                    attrs=("code=src/frob/widget/**", "purpose=logging"),
                    waives=(
                        Waiver(
                            rule="SYS105:net.connect",
                            reason="tracked debt, expires:2099-01-01",
                            ticket="T-0671",
                        ),
                    ),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_PURPOSE_CONTRACT for v in result.danger_ok.violations
        )
        assert not any(
            v.rule == CONFORMANCE_WAIVER_EXPIRED_RULE
            for v in result.danger_ok.violations
        )
        assert any(v.rule == SYS_PURPOSE_CONTRACT for v in result.danger_ok.waived)
