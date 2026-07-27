"""Unit-level coverage for HOST001/HOST002 movement-impossibility proofs
(T-0256, `src/frob/strata/_host_isolation.py`) against hand-built
`KernelModel` values -- mirroring `test_host.py`'s unit-test shape.
End-to-end parse -> elaborate coverage lives in
`test_litmus_host_isolation.py`.
"""

from __future__ import annotations

from typani.result import Err

from frob.strata import _host_isolation
from frob.strata._errors import StrataError
from frob.strata._host import HostAcl
from frob.strata._host_isolation import (
    COMPROMISED_OWNER_CATALOG,
    COMPROMISED_OWNER_VIEWS,
    _join_acl_entries,
    evaluate_host_isolation_waived,
    evaluate_lateral_isolation,
    evaluate_vertical_isolation,
    host_movement_flows,
)
from frob.strata._models import Flow, KernelModel, Node
from frob.strata._scenarios import build_compromised_user_scenario, evaluate_scenarios
from frob.strata._threat import check_catalog_completeness


# frob:waive DUP001 reason="parallel test fixtures across 2 sibling test file(s) (2 \
# sites) sharing an arrange-act scaffold typical of exhaustive per-case/per-scenario \
# coverage; extracting would obscure per-case intent"
def _shared_user_model() -> KernelModel:
    """Two service users sharing a writable path, a listening port, and
    (T-0272) an OS group, with no declared Flow between them -- the
    HOST001/HOST002 VULN shape."""
    api = Node(
        id="api",
        trust="trusted",
        attrs=(
            "runs_as=svc-a",
            "unit",
            "owns=/var/lib/shared:0664",
            "listens=9000",
            "group=ops",
            "sudoers=ALL=(root) NOPASSWD: /bin/true",
        ),
    )
    worker = Node(
        id="worker",
        trust="trusted",
        attrs=(
            "runs_as=svc-b",
            "unit",
            "owns=/var/lib/shared:0664",
            "listens=9000",
            "group=ops",
        ),
    )
    return KernelModel(nodes=(api, worker))


# frob:waive DUP001 reason="parallel test fixtures across 2 sibling test file(s) (2 \
# sites) sharing an arrange-act scaffold typical of exhaustive per-case/per-scenario \
# coverage; extracting would obscure per-case intent"
def _isolated_hardened_model() -> KernelModel:
    """Two service users with disjoint owns/listens/group and no declared
    sudoers grant -- the HOST001/HOST002 HARDENED shape that discharges
    with no waivers needed at all now that T-0272 makes shared-group/
    sudoers structurally provable (previously this fixture carried
    explicit waivers for those two always-fire sub-targets)."""
    api = Node(
        id="api",
        trust="trusted",
        attrs=(
            "runs_as=svc-a",
            "unit",
            "owns=/etc/api:0640",
            "listens=8080",
            "group=api-grp",
        ),
    )
    worker = Node(
        id="worker",
        trust="trusted",
        attrs=(
            "runs_as=svc-b",
            "unit",
            "owns=/etc/worker:0640",
            "listens=8081",
            "group=worker-grp",
        ),
    )
    return KernelModel(nodes=(api, worker))


class TestLateralIsolation:
    # frob:tests src/frob/strata/_host_isolation.py::evaluate_lateral_isolation \
    # kind="unit"
    def test_skips_below_two_users(self):
        node = Node(id="solo", trust="trusted", attrs=("runs_as=svc-a", "unit"))
        model = KernelModel(nodes=(node,))
        violations = evaluate_lateral_isolation(model).danger_ok
        assert violations == ()

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_lateral_isolation \
    # kind="unit"
    def test_shared_writable_path_and_socket_fire(self):
        violations = evaluate_lateral_isolation(_shared_user_model()).danger_ok
        sub_targets = {v.sub_target for v in violations}
        assert "shared-writable-path" in sub_targets
        assert "cross-user-socket" in sub_targets
        assert "shared-group" in sub_targets  # T-0272: derived from shared group=ops

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_lateral_isolation \
    # kind="unit"
    def test_declared_flow_discharges_cross_user_socket(self):
        api = Node(
            id="api",
            trust="trusted",
            attrs=("runs_as=svc-a", "unit", "listens=9000"),
        )
        worker = Node(
            id="worker",
            trust="trusted",
            attrs=("runs_as=svc-b", "unit", "listens=9000"),
        )
        model = KernelModel(
            nodes=(api, worker), flows=(Flow(id="f1", src="api", dst="worker"),)
        )
        violations = evaluate_lateral_isolation(model).danger_ok
        assert "cross-user-socket" not in {v.sub_target for v in violations}

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_lateral_isolation \
    # kind="unit"
    def test_isolated_paths_do_not_fire_shared_writable_path(self):
        violations = evaluate_lateral_isolation(_isolated_hardened_model()).danger_ok
        assert "shared-writable-path" not in {v.sub_target for v in violations}

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_lateral_isolation \
    # kind="unit"
    def test_disjoint_groups_do_not_fire_shared_group(self):
        """T-0272: two users declaring DIFFERENT groups must not fire
        shared-group -- it is now a real intersection, not an always-fire
        honest gap."""
        violations = evaluate_lateral_isolation(_isolated_hardened_model()).danger_ok
        assert "shared-group" not in {v.sub_target for v in violations}


class TestVerticalIsolation:
    # frob:tests src/frob/strata/_host_isolation.py::evaluate_vertical_isolation \
    # kind="unit"
    def test_skips_with_no_users(self):
        model = KernelModel(nodes=(Node(id="n", trust="trusted"),))
        assert evaluate_vertical_isolation(model).danger_ok == ()

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_vertical_isolation \
    # kind="unit"
    def test_setuid_owned_path_fires(self):
        node = Node(
            id="api",
            trust="trusted",
            attrs=("runs_as=svc-a", "unit", "owns=/usr/bin/su-helper:4755"),
        )
        model = KernelModel(nodes=(node,))
        violations = evaluate_vertical_isolation(model).danger_ok
        assert any(v.sub_target == "setuid" for v in violations)

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_vertical_isolation \
    # kind="unit"
    # T-0272: renamed from `test_sudoers_always_fires_as_honest_gap` would
    # break T-0256's archived Done-report evidence (tickets-archive.md is
    # outside this ticket's declared scope) -- kept as the historical
    # name, behavior updated to match the new derived-not-honest-gap
    # semantics (module docstring).
    def test_sudoers_always_fires_as_honest_gap(self):
        """T-0272: `sudoers` fires when a user's HostManifest.sudoers is
        non-empty -- derived from the grant, not an always-fire gap
        (name kept for T-0256 evidence continuity, see comment above)."""
        node = Node(
            id="api",
            trust="trusted",
            attrs=("runs_as=svc-a", "unit", "sudoers=ALL=(root) NOPASSWD: /bin/true"),
        )
        model = KernelModel(nodes=(node,))
        violations = evaluate_vertical_isolation(model).danger_ok
        assert any(v.sub_target == "sudoers" for v in violations)

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_vertical_isolation \
    # kind="unit"
    def test_sudoers_does_not_fire_when_undeclared(self):
        """T-0272: a user with no `sudoers` clause at all produces no
        sudoers finding -- absence is now structurally provable."""
        node = Node(id="api", trust="trusted", attrs=("runs_as=svc-a", "unit"))
        model = KernelModel(nodes=(node,))
        violations = evaluate_vertical_isolation(model).danger_ok
        assert not any(v.sub_target == "sudoers" for v in violations)

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_vertical_isolation \
    # kind="unit"
    def test_root_unit_path_writable_by_user_fires(self):
        root_unit = Node(
            id="rootd",
            trust="trusted",
            attrs=("unit", "owns=/opt/app/run.sh:0755"),
        )
        user = Node(
            id="api",
            trust="trusted",
            attrs=("runs_as=svc-a", "unit", "owns=/opt/app/run.sh:0666"),
        )
        model = KernelModel(nodes=(root_unit, user))
        violations = evaluate_vertical_isolation(model).danger_ok
        assert any(v.sub_target == "root-unit-writable-by-user" for v in violations)

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_vertical_isolation \
    # kind="unit"
    def test_write_to_higher_trust_path_fires(self):
        model = KernelModel(
            nodes=(
                Node(
                    id="db",
                    trust="trusted",
                    attrs=("runs_as=svc-db", "unit", "owns=/data/shared:0644"),
                ),
                Node(
                    id="api",
                    trust="authenticated",
                    attrs=("runs_as=svc-a", "unit", "owns=/data/shared:0666"),
                ),
            )
        )
        violations = evaluate_vertical_isolation(model).danger_ok
        assert any(v.sub_target == "write-to-higher-trust-path" for v in violations)


class TestHostIsolationWaivers:
    # frob:tests src/frob/strata/_host_isolation.py::evaluate_host_isolation_waived \
    # kind="unit"
    def test_vuln_model_fires_unwaived(self):
        h1, h2 = evaluate_host_isolation_waived(_shared_user_model()).danger_ok
        assert h1.kept != ()
        assert h2.kept != ()

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_host_isolation_waived \
    # kind="unit"
    def test_hardened_model_discharges_with_waivers(self):
        h1, h2 = evaluate_host_isolation_waived(_isolated_hardened_model()).danger_ok
        assert h1.kept == ()
        assert h2.kept == ()
        assert h1.stale == ()
        assert h2.stale == ()

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_host_isolation_waived \
    # kind="unit"
    # frob:waive DUP001 reason="parallel test methods within test_host_isolation.py (2 \
    # sites) sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_propagates_lateral_isolation_error(self, monkeypatch):
        """HOST001's delegate failing must short-circuit before HOST002
        ever runs -- deny by default, never a silent partial result."""
        monkeypatch.setattr(
            _host_isolation,
            "evaluate_lateral_isolation",
            lambda model: Err(StrataError.UnknownReference),
        )
        result = evaluate_host_isolation_waived(_shared_user_model())
        assert result.is_err
        assert result.danger_err == StrataError.UnknownReference

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_host_isolation_waived \
    # kind="unit"
    # frob:waive DUP001 reason="parallel test methods within test_host_isolation.py (2 \
    # sites) sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_propagates_vertical_isolation_error(self, monkeypatch):
        """HOST002's delegate failing must propagate even when HOST001
        succeeded -- the second fallible step is not silently ignored."""
        monkeypatch.setattr(
            _host_isolation,
            "evaluate_vertical_isolation",
            lambda model: Err(StrataError.UnknownReference),
        )
        result = evaluate_host_isolation_waived(_shared_user_model())
        assert result.is_err
        assert result.danger_err == StrataError.UnknownReference


class TestCompromisedOwnerCatalog:
    # frob:tests src/frob/strata/_host_isolation.py::COMPROMISED_OWNER_CATALOG \
    # kind="unit"
    def test_catalog_completeness_over_own_view(self):
        result = check_catalog_completeness(
            "compromised-owner-baseline",
            catalog=COMPROMISED_OWNER_CATALOG,
            views=COMPROMISED_OWNER_VIEWS,
        )
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_host_isolation.py::COMPROMISED_OWNER_CATALOG \
    # kind="unit"
    def test_default_owasp_view_unaffected(self):
        """The compromised-owner class lives in its OWN view -- checking
        the default `owasp-top-10` view never implicates CWE-284/269/522
        (separate-views precedent, module docstring)."""
        result = check_catalog_completeness("owasp-top-10")
        assert result.is_ok


class TestCompromisedUserScenario:
    # frob:tests src/frob/strata/_scenarios.py::build_compromised_user_scenario \
    # kind="unit"
    def test_unknown_user_fails_closed(self):
        model = _shared_user_model()
        result = build_compromised_user_scenario(model, "svc-nope", "scn-1")
        assert result.is_err


# frob:tests src/frob/strata/_scenarios.py::build_compromised_user_scenario kind="unit"
def test_blast_radius():
    """Compromising `svc-a` (owning only `api`) proves NoFlow to every
    OTHER node -- the scenario's closure shows the blast radius is
    exactly `svc-a`'s own manifest slice, no wider. Module-level (not a
    class method) so the pytest node id stays under the 88-char line
    limit for its `frob:tests` directive above."""
    model = _isolated_hardened_model()
    scenario = build_compromised_user_scenario(model, "svc-a", "compromise-svc-a")
    assert scenario.is_ok
    model_with_scenario = model.model_copy(update={"scenarios": (scenario.danger_ok,)})
    results = evaluate_scenarios(model_with_scenario).danger_ok
    assert len(results) == 1
    scenario_result = results[0]
    assert scenario_result.scenario_id == "compromise-svc-a"
    assert len(scenario_result.results) == 1  # one other node: worker
    for claim_result in scenario_result.results:
        assert claim_result.verdict.value == "proved"


# frob:tests src/frob/strata/_host_isolation.py::host_movement_flows kind="unit"
def test_movement_flows():
    """`host_movement_flows` derives a bidirectional synthetic Flow pair
    over a shared writable path -- the fact HOST001 already detects,
    materialized so the closure can see it too (module docstring's
    REJECT-round fix)."""
    api = Node(
        id="api", trust="trusted", attrs=("runs_as=svc-a", "unit", "owns=/x:0664")
    )
    worker = Node(
        id="worker", trust="trusted", attrs=("runs_as=svc-b", "unit", "owns=/x:0664")
    )
    flows = host_movement_flows(KernelModel(nodes=(api, worker)))
    pairs = {(f.src, f.dst) for f in flows}
    assert ("api", "worker") in pairs
    assert ("worker", "api") in pairs


class TestWindowsHostIsolation:
    """T-0606: HOST001/HOST002 movement-impossibility proofs wired to the
    windows `service_account`/`acl`/`pipe` surface (T-0261), equivalent in
    strength to the linux `runs_as`/`owns`/`listens` path (docs/strata/
    host.md#windows-wiring-t-0606)."""

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_lateral_isolation \
    # kind="unit"
    def test_shared_writable_acl_path_and_pipe_fire(self):
        """Two windows-only nodes (`service_account`/`acl`/`pipe`, no
        `runs_as`/`owns`/`listens` at all) sharing a write-capable ACL
        path and a named pipe fire the SAME HOST001 sub-targets a linux
        pair would."""
        api = Node(
            id="api",
            trust="trusted",
            attrs=(
                "platform=windows",
                "service_account=svc-a",
                "service",
                "acl=C:\\ProgramData\\shared|Everyone:Modify",
                "pipe=api-ipc",
            ),
        )
        worker = Node(
            id="worker",
            trust="trusted",
            attrs=(
                "platform=windows",
                "service_account=svc-b",
                "service",
                "acl=C:\\ProgramData\\shared|Everyone:Modify",
                "pipe=api-ipc",
            ),
        )
        model = KernelModel(nodes=(api, worker))
        violations = evaluate_lateral_isolation(model).danger_ok
        sub_targets = {v.sub_target for v in violations}
        assert "shared-writable-path" in sub_targets
        assert "cross-user-socket" in sub_targets

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_lateral_isolation \
    # kind="unit"
    # frob:waive DUP001 reason="parallel test methods within test_host_isolation.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case \
    # coverage; extracting would obscure per-case intent"
    def test_deny_acl_does_not_fire_shared_writable_path(self):
        """A shared ACL path where neither side's RULE grants write (both
        `:deny`'d, or a read-only RIGHTS) must not fire
        shared-writable-path -- the windows analog of a non-writable POSIX
        mode."""
        api = Node(
            id="api",
            trust="trusted",
            attrs=(
                "platform=windows",
                "service_account=svc-a",
                "service",
                "acl=C:\\ProgramData\\ro|Everyone:Read",
            ),
        )
        worker = Node(
            id="worker",
            trust="trusted",
            attrs=(
                "platform=windows",
                "service_account=svc-b",
                "service",
                "acl=C:\\ProgramData\\ro|Everyone:Read",
            ),
        )
        model = KernelModel(nodes=(api, worker))
        violations = evaluate_lateral_isolation(model).danger_ok
        assert "shared-writable-path" not in {v.sub_target for v in violations}

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_lateral_isolation \
    # kind="unit"
    # frob:waive DUP001 reason="parallel test methods within test_host_isolation.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case \
    # coverage; extracting would obscure per-case intent"
    def test_explicit_deny_acl_flag_does_not_fire_shared_writable_path(self):
        """T-0791: exercise the `:deny` flag directly (not just a
        non-write RIGHTS value) -- Everyone:Modify:deny on a write-capable
        RIGHTS must not grant write, so a shared path where BOTH sides
        carry only that deny'd ACE must not fire shared-writable-path."""
        api = Node(
            id="api",
            trust="trusted",
            attrs=(
                "platform=windows",
                "service_account=svc-a",
                "service",
                "acl=C:\\ProgramData\\denied|Everyone:Modify:deny",
            ),
        )
        worker = Node(
            id="worker",
            trust="trusted",
            attrs=(
                "platform=windows",
                "service_account=svc-b",
                "service",
                "acl=C:\\ProgramData\\denied|Everyone:Modify:deny",
            ),
        )
        model = KernelModel(nodes=(api, worker))
        violations = evaluate_lateral_isolation(model).danger_ok
        assert "shared-writable-path" not in {v.sub_target for v in violations}

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_lateral_isolation \
    # kind="unit"
    def test_explicit_deny_acl_flag_fires_when_write_rights_present_elsewhere(self):
        """T-0791's fire counterpart: a `:deny`'d ACE for one principal
        alongside a plain write-capable ACE for a DIFFERENT principal on
        the same path must still fire -- the deny only cancels its own
        principal, it does not blanket-suppress the path (also exercises
        T-0792's multi-ACE join, see TestMultiAceDenyOverridesAllow)."""
        api = Node(
            id="api",
            trust="trusted",
            attrs=(
                "platform=windows",
                "service_account=svc-a",
                "service",
                "acl=C:\\ProgramData\\mixed|svc-x:Modify:deny",
                "acl=C:\\ProgramData\\mixed|Everyone:Modify",
            ),
        )
        worker = Node(
            id="worker",
            trust="trusted",
            attrs=(
                "platform=windows",
                "service_account=svc-b",
                "service",
                "acl=C:\\ProgramData\\mixed|svc-x:Modify:deny",
                "acl=C:\\ProgramData\\mixed|Everyone:Modify",
            ),
        )
        model = KernelModel(nodes=(api, worker))
        violations = evaluate_lateral_isolation(model).danger_ok
        assert "shared-writable-path" in {v.sub_target for v in violations}

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_vertical_isolation \
    # kind="unit"
    def test_service_with_no_account_is_root_run(self):
        """A windows `service` with no `service_account` (SCM's own
        LocalSystem default) is the root-run-equivalent identity HOST002's
        root-unit-writable-by-user sub-target guards against -- the
        windows analog of a `unit` with no `runs_as`."""
        local_system_service = Node(
            id="svc-host",
            trust="trusted",
            attrs=(
                "platform=windows",
                "service",
                "acl=C:\\ProgramData\\app\\run.exe|Everyone:Modify",
            ),
        )
        user = Node(
            id="api",
            trust="trusted",
            attrs=(
                "platform=windows",
                "service_account=svc-a",
                "service",
                "acl=C:\\ProgramData\\app\\run.exe|svc-a:Modify",
            ),
        )
        model = KernelModel(nodes=(local_system_service, user))
        violations = evaluate_vertical_isolation(model).danger_ok
        assert any(v.sub_target == "root-unit-writable-by-user" for v in violations)

    # frob:tests src/frob/strata/_scenarios.py::build_compromised_user_scenario \
    # kind="unit"
    def test_compromised_windows_service_account_scenario(self):
        """`build_compromised_user_scenario` resolves a windows
        `service_account` identity exactly like a linux `runs_as` one."""
        api = Node(
            id="api",
            trust="trusted",
            attrs=("platform=windows", "service_account=svc-a", "service"),
        )
        worker = Node(
            id="worker",
            trust="trusted",
            attrs=("platform=windows", "service_account=svc-b", "service"),
        )
        model = KernelModel(nodes=(api, worker))
        scenario = build_compromised_user_scenario(model, "svc-a", "compromise-svc-a")
        assert scenario.is_ok
        model_with_scenario = model.model_copy(
            update={"scenarios": (scenario.danger_ok,)}
        )
        results = evaluate_scenarios(model_with_scenario).danger_ok
        assert len(results) == 1
        for claim_result in results[0].results:
            assert claim_result.verdict.value == "proved"


class TestMultiAceDenyOverridesAllow:
    """T-0792: `_join_acl_entries`'s real NTFS deny-overrides-allow join
    across every ACE declared for one path, replacing the last-
    declaration-wins collapse the T-0606 reviewer flagged as a soundness
    gap (module docstring's "Multi-ACE deny-overrides-allow join"
    section)."""

    # frob:tests src/frob/strata/_host_isolation.py::_join_acl_entries kind="unit"
    def test_single_deny_entry_denies(self):
        entries = [HostAcl(path="/p", rule="Everyone:Modify:deny")]
        assert _join_acl_entries(entries) is False

    # frob:tests src/frob/strata/_host_isolation.py::_join_acl_entries kind="unit"
    def test_single_allow_entry_grants(self):
        entries = [HostAcl(path="/p", rule="Everyone:Modify")]
        assert _join_acl_entries(entries) is True

    # frob:tests src/frob/strata/_host_isolation.py::_join_acl_entries kind="unit"
    # frob:waive DUP001 reason="parallel test methods within test_host_isolation.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case \
    # coverage; extracting would obscure per-case intent"
    def test_narrow_deny_then_broad_allow_same_principal_denies(self):
        """T-0825 WRITE_DAC-indirection corner (the T-0792 reviewer
        finding this ticket closes; SAME test name as the pre-fix T-0791/
        T-0792 assertion this replaces, so archived evidence citing this
        node id keeps resolving -- only the assertion's expected result
        changed): same principal, narrow `Modify` deny declared first,
        broad `FullControl` allow declared second. Real NTFS: the
        `Modify` deny removes the plain content-write bit but never
        reaches WRITE_DAC/WRITE_OWNER (only an explicit `FullControl`-
        level deny does) -- those bits survive from the `FullControl`
        allow, letting the principal rewrite the path's own DACL and
        regain full write. The join must still count this write-capable
        via that indirection (a PRE-fix build of this module got this
        backwards, treating it as a clean deny -- this test's OLD name
        literally said "denies"; that was the bug)."""
        entries = [
            HostAcl(path="/p", rule="Everyone:Modify:deny"),
            HostAcl(path="/p", rule="Everyone:FullControl"),
        ]
        assert _join_acl_entries(entries) is True

    # frob:tests src/frob/strata/_host_isolation.py::_join_acl_entries kind="unit"
    # frob:waive DUP001 reason="parallel test methods within test_host_isolation.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case \
    # coverage; extracting would obscure per-case intent"
    def test_broad_allow_then_narrow_deny_same_principal_still_denies(self):
        """Same corner as above, declaration order reversed: `FullControl`
        allow first, narrower `Modify` deny second -- still write-capable
        via WRITE_DAC indirection, order-independence cutting both ways
        exactly like the rest of this join's ordering guarantees. SAME
        test name as the pre-fix assertion (archived T-0791/T-0792
        evidence keeps resolving); only the expected result changed, for
        the identical T-0825 reason as the previous test."""
        entries = [
            HostAcl(path="/p", rule="Everyone:FullControl"),
            HostAcl(path="/p", rule="Everyone:Modify:deny"),
        ]
        assert _join_acl_entries(entries) is True

    # frob:tests src/frob/strata/_host_isolation.py::_join_acl_entries kind="unit"
    # frob:waive DUP001 reason="parallel test methods within test_host_isolation.py (3 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case \
    # coverage; extracting would obscure per-case intent"
    def test_fullcontrol_deny_denies_fullcontrol_allow_no_indirection(self):
        """The WRITE_DAC-indirection corner does NOT apply when the deny
        is ITSELF `FullControl`-level: an explicit `FullControl` deny
        reaches WRITE_DAC/WRITE_OWNER too, so there is no surviving bit
        for the principal to rewrite the DACL with -- a genuinely clean
        deny, same principal, both entries at the SAME (broadest)
        level."""
        entries = [
            HostAcl(path="/p", rule="Everyone:FullControl:deny"),
            HostAcl(path="/p", rule="Everyone:FullControl"),
        ]
        assert _join_acl_entries(entries) is False

    # frob:tests src/frob/strata/_host_isolation.py::_join_acl_entries kind="unit"
    # frob:waive DUP001 reason="parallel test methods within test_host_isolation.py (3 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case \
    # coverage; extracting would obscure per-case intent"
    def test_narrow_deny_narrow_allow_same_principal_still_denies(self):
        """The indirection corner is `FullControl`-allow-specific: a
        `Modify` allow never grants WRITE_DAC/WRITE_OWNER in the first
        place (only `FullControl` does), so a same-level `Modify` deny
        still fully cancels it -- unaffected by the T-0825 fix, same
        result as before."""
        entries = [
            HostAcl(path="/p", rule="Everyone:Modify:deny"),
            HostAcl(path="/p", rule="Everyone:Modify"),
        ]
        assert _join_acl_entries(entries) is False

    # frob:tests src/frob/strata/_host_isolation.py::_join_acl_entries kind="unit"
    # frob:waive DUP001 reason="parallel test methods within test_host_isolation.py (3 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case \
    # coverage; extracting would obscure per-case intent"
    def test_write_deny_modify_allow_same_principal_still_denies(self):
        """A narrower `Write` deny against a `Modify` allow: `Modify`
        never grants WRITE_DAC either, so there is no indirection bit to
        survive -- the plain content-write bit `Write` covers is still
        fully cancelled, same as any deny among `_ACL_WRITE_RIGHTS`
        removing the shared content-write bit every level carries."""
        entries = [
            HostAcl(path="/p", rule="Everyone:Write:deny"),
            HostAcl(path="/p", rule="Everyone:Modify"),
        ]
        assert _join_acl_entries(entries) is False

    # frob:tests src/frob/strata/_host_isolation.py::_join_acl_entries kind="unit"
    def test_deny_for_one_principal_does_not_cancel_another_principals_allow(self):
        """The T-0792 fix's core case: a deny for principal X does not
        reach across to cancel a write grant to a DIFFERENT principal Y
        on the same path -- a last-declaration-wins collapse could
        silently drop Y's real grant if X's ACE happened to land last in
        iteration order, under-reporting the violation."""
        entries = [
            HostAcl(path="/p", rule="svc-x:Modify:deny"),
            HostAcl(path="/p", rule="Everyone:Modify"),
        ]
        assert _join_acl_entries(entries) is True
        # order-independence: the deny'd principal's ACE landing LAST
        # must not flip the verdict either.
        reversed_entries = [
            HostAcl(path="/p", rule="Everyone:Modify"),
            HostAcl(path="/p", rule="svc-x:Modify:deny"),
        ]
        assert _join_acl_entries(reversed_entries) is True

    # frob:tests src/frob/strata/_host_isolation.py::_join_acl_entries kind="unit"
    def test_no_write_rights_entries_denies(self):
        entries = [
            HostAcl(path="/p", rule="Everyone:Read"),
            HostAcl(path="/p", rule="svc-x:Read:deny"),
        ]
        assert _join_acl_entries(entries) is False


# frob:tests src/frob/strata/_scenarios.py::build_compromised_user_scenario kind="unit"
def test_blast_radius_refutes_over_shared_writable_path_with_no_declared_flow():
    """The reviewer's exact T-0256 REJECT-round adversarial case: two
    users share a writable path with NO declared app Flow between them.
    Before the fix, `NoFlow` was proved purely over the declared-flow
    graph (vacuously PROVED, false assurance -- HOST001 fires on the SAME
    model). After the fix (`host_movement_flows` wired into the scenario
    via `AddFlow`), the blast-radius claim correctly REFUTES: the
    compromise of `svc-a` CAN reach `worker` through the shared path."""
    api = Node(
        id="api",
        trust="trusted",
        attrs=("runs_as=svc-a", "unit", "owns=/var/lib/shared:0664"),
    )
    worker = Node(
        id="worker",
        trust="trusted",
        attrs=("runs_as=svc-b", "unit", "owns=/var/lib/shared:0664"),
    )
    model = KernelModel(nodes=(api, worker))
    scenario = build_compromised_user_scenario(model, "svc-a", "compromise-svc-a")
    assert scenario.is_ok
    model_with_scenario = model.model_copy(update={"scenarios": (scenario.danger_ok,)})
    results = evaluate_scenarios(model_with_scenario).danger_ok
    assert len(results) == 1
    scenario_result = results[0]
    assert len(scenario_result.results) == 1
    assert scenario_result.results[0].verdict.value == "refuted"
