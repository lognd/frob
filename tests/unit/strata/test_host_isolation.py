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
from frob.strata._host_isolation import (
    COMPROMISED_OWNER_CATALOG,
    COMPROMISED_OWNER_VIEWS,
    evaluate_host_isolation_waived,
    evaluate_lateral_isolation,
    evaluate_vertical_isolation,
    host_movement_flows,
)
from frob.strata._models import Flow, KernelModel, Node
from frob.strata._scenarios import build_compromised_user_scenario, evaluate_scenarios
from frob.strata._threat import check_catalog_completeness


# frob:waive DUP001 reason="parallel test fixtures across 2 sibling test \
# file(s) (2 sites) sharing an arrange-act scaffold typical of exhaustive \
# per-case/per-scenario coverage; extracting would obscure per-case intent"
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


# frob:waive DUP001 reason="parallel test fixtures across 2 sibling test \
# file(s) (2 sites) sharing an arrange-act scaffold typical of exhaustive \
# per-case/per-scenario coverage; extracting would obscure per-case intent"
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
    # frob:tests src/frob/strata/_host_isolation.py::evaluate_lateral_isolation kind="unit"
    def test_skips_below_two_users(self):
        node = Node(id="solo", trust="trusted", attrs=("runs_as=svc-a", "unit"))
        model = KernelModel(nodes=(node,))
        violations = evaluate_lateral_isolation(model).danger_ok
        assert violations == ()

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_lateral_isolation kind="unit"
    def test_shared_writable_path_and_socket_fire(self):
        violations = evaluate_lateral_isolation(_shared_user_model()).danger_ok
        sub_targets = {v.sub_target for v in violations}
        assert "shared-writable-path" in sub_targets
        assert "cross-user-socket" in sub_targets
        assert "shared-group" in sub_targets  # T-0272: derived from shared group=ops

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_lateral_isolation kind="unit"
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

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_lateral_isolation kind="unit"
    def test_isolated_paths_do_not_fire_shared_writable_path(self):
        violations = evaluate_lateral_isolation(_isolated_hardened_model()).danger_ok
        assert "shared-writable-path" not in {v.sub_target for v in violations}

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_lateral_isolation kind="unit"
    def test_disjoint_groups_do_not_fire_shared_group(self):
        """T-0272: two users declaring DIFFERENT groups must not fire
        shared-group -- it is now a real intersection, not an always-fire
        honest gap."""
        violations = evaluate_lateral_isolation(_isolated_hardened_model()).danger_ok
        assert "shared-group" not in {v.sub_target for v in violations}


class TestVerticalIsolation:
    # frob:tests src/frob/strata/_host_isolation.py::evaluate_vertical_isolation kind="unit"
    def test_skips_with_no_users(self):
        model = KernelModel(nodes=(Node(id="n", trust="trusted"),))
        assert evaluate_vertical_isolation(model).danger_ok == ()

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_vertical_isolation kind="unit"
    def test_setuid_owned_path_fires(self):
        node = Node(
            id="api",
            trust="trusted",
            attrs=("runs_as=svc-a", "unit", "owns=/usr/bin/su-helper:4755"),
        )
        model = KernelModel(nodes=(node,))
        violations = evaluate_vertical_isolation(model).danger_ok
        assert any(v.sub_target == "setuid" for v in violations)

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_vertical_isolation kind="unit"
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

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_vertical_isolation kind="unit"
    def test_sudoers_does_not_fire_when_undeclared(self):
        """T-0272: a user with no `sudoers` clause at all produces no
        sudoers finding -- absence is now structurally provable."""
        node = Node(id="api", trust="trusted", attrs=("runs_as=svc-a", "unit"))
        model = KernelModel(nodes=(node,))
        violations = evaluate_vertical_isolation(model).danger_ok
        assert not any(v.sub_target == "sudoers" for v in violations)

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_vertical_isolation kind="unit"
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

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_vertical_isolation kind="unit"
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
    # frob:tests src/frob/strata/_host_isolation.py::evaluate_host_isolation_waived kind="unit"
    def test_vuln_model_fires_unwaived(self):
        h1, h2 = evaluate_host_isolation_waived(_shared_user_model()).danger_ok
        assert h1.kept != ()
        assert h2.kept != ()

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_host_isolation_waived kind="unit"
    def test_hardened_model_discharges_with_waivers(self):
        h1, h2 = evaluate_host_isolation_waived(_isolated_hardened_model()).danger_ok
        assert h1.kept == ()
        assert h2.kept == ()
        assert h1.stale == ()
        assert h2.stale == ()

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_host_isolation_waived kind="unit"
    # frob:waive DUP001 reason="parallel test methods within \
    # test_host_isolation.py (2 sites) sharing an arrange-act scaffold \
    # typical of exhaustive per-case coverage; extracting would obscure \
    # per-case intent"
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

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_host_isolation_waived kind="unit"
    # frob:waive DUP001 reason="parallel test methods within \
    # test_host_isolation.py (2 sites) sharing an arrange-act scaffold \
    # typical of exhaustive per-case coverage; extracting would obscure \
    # per-case intent"
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
    # frob:tests src/frob/strata/_host_isolation.py::COMPROMISED_OWNER_CATALOG kind="unit"
    def test_catalog_completeness_over_own_view(self):
        result = check_catalog_completeness(
            "compromised-owner-baseline",
            catalog=COMPROMISED_OWNER_CATALOG,
            views=COMPROMISED_OWNER_VIEWS,
        )
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_host_isolation.py::COMPROMISED_OWNER_CATALOG kind="unit"
    def test_default_owasp_view_unaffected(self):
        """The compromised-owner class lives in its OWN view -- checking
        the default `owasp-top-10` view never implicates CWE-284/269/522
        (separate-views precedent, module docstring)."""
        result = check_catalog_completeness("owasp-top-10")
        assert result.is_ok


class TestCompromisedUserScenario:
    # frob:tests src/frob/strata/_scenarios.py::build_compromised_user_scenario kind="unit"
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

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_lateral_isolation kind="unit"
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

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_lateral_isolation kind="unit"
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

    # frob:tests src/frob/strata/_host_isolation.py::evaluate_vertical_isolation kind="unit"
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

    # frob:tests src/frob/strata/_scenarios.py::build_compromised_user_scenario kind="unit"
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
