"""REL2xx reliability family litmus + unit coverage (T-0640 TIMEOUT,
T-0644 HEALTH; `frob.strata._reliability`) -- mirrors `test_contention.
py`'s real `strata_core` parse -> elaborate round-trip discipline for the
REL200/REL210 missing-obligation/waiver shapes, plus `test_selfconform.
py`'s `tmp_path` real-file convention for REL201/REL211's proof-against-
code (bind_code-backed, so it needs a real file tree, not just a parsed
`.strata` fixture).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import Flow, KernelModel, Module, Node, Waiver, elaborate, parse_module
from frob.strata._reliability import (
    REL_MISSING_HEALTH,
    REL_MISSING_TIMEOUT,
    REL_UNPROVEN_HEALTH,
    REL_UNPROVEN_TIMEOUT,
    check_reliability_health,
    check_reliability_timeouts,
)

_LITMUS_DIR = Path(__file__).resolve().parent / "litmus"


def _load(filename: str) -> tuple[Module, KernelModel]:
    """Parse+elaborate one `.strata` fixture under `litmus/`."""
    text = (_LITMUS_DIR / filename).read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    model = elaborate(module).danger_ok
    return module, model


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestMissingTimeout:
    # frob:tests \
    # tests/unit/strata/test_reliability.py::TestMissingTimeout.test_flow_without_timeo\
    # ut_fires
    def test_flow_without_timeout_fires(self, tmp_path: Path):
        _module, model = _load("reliability_timeout_missing_vuln.strata")
        result = check_reliability_timeouts(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        missing = [v for v in report.violations if v.rule == REL_MISSING_TIMEOUT]
        sub_targets = {v.sub_target for v in missing}
        assert sub_targets == {"f_missing"}
        assert all(v.node == "caller" for v in missing)
        # f_ok (declares `attr timeout;`) must not spuriously fire.
        assert "f_ok" not in sub_targets

    # frob:tests \
    # tests/unit/strata/test_reliability.py::TestMissingTimeout.test_discharged_and_exe\
    # mpt_flows_clean
    def test_discharged_and_exempt_flows_clean(self, tmp_path: Path):
        _module, model = _load("reliability_timeout_clean.strata")
        result = check_reliability_timeouts(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not [v for v in report.violations if v.rule == REL_MISSING_TIMEOUT]

    # frob:tests \
    # tests/unit/strata/test_reliability.py::TestMissingTimeout.test_cache_fill_and_inv\
    # alidation_flows_are_local_exempt
    def test_cache_fill_and_invalidation_flows_are_local_exempt(self, tmp_path: Path):
        """T-0845: a `cache X of Y` construct's elaborator-synthesized
        fill/invalidation flows now carry `_infra.py::_CACHE_LOCAL_ATTR`
        unconditionally, so REL200 must never fire on them -- no waiver
        needed at all (burns down the two `graph_cache__fill`/
        `graph_cache__inval_*` waivers this ticket removed from
        `design/frob.strata`)."""
        text = """
        module m
        node api : trusted
        store db : trusted { clearance Pii; }
        flow w1 : api -> db { label Pii; attr timeout; }
        cache c of db {
            keyed_by user_id;
            staleness 30 s;
            invalidate_on w1;
        }
        """
        module = parse_module(text).danger_ok
        model = elaborate(module).danger_ok
        result = check_reliability_timeouts(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        missing = {
            v.sub_target for v in report.violations if v.rule == REL_MISSING_TIMEOUT
        }
        assert "c__fill" not in missing
        assert "c__inval_w1" not in missing
        # No waiver was declared -- this is a real exemption, not a hidden one.
        assert not report.waived

    # frob:tests \
    # tests/unit/strata/test_reliability.py::TestMissingTimeout.test_waiver_on_one_flow\
    # _keeps_sibling_flow_finding
    def test_waiver_on_one_flow_keeps_sibling_flow_finding(self, tmp_path: Path):
        _module, model = _load("reliability_timeout_waived.strata")
        result = check_reliability_timeouts(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        kept = {
            v.sub_target for v in report.violations if v.rule == REL_MISSING_TIMEOUT
        }
        waived = {v.sub_target for v in report.waived if v.rule == REL_MISSING_TIMEOUT}
        assert kept == {"f_other"}
        assert waived == {"f_missing"}


class TestUnprovenTimeout:
    """REL201 proof-against-code needs a real file tree bound via
    `bind_code` -- a parsed `.strata` fixture alone cannot exercise it, so
    these build a `KernelModel` directly (the `test_selfconform.py`/
    `test_crash.py` precedent) against `tmp_path`."""

    # frob:tests \
    # tests/unit/strata/test_reliability.py::TestUnprovenTimeout.test_declared_timeout_\
    # with_no_code_evidence_fires
    def test_declared_timeout_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(tmp_path, "src/widget/_io.py", "def call():\n    return remote()\n")
        model = KernelModel(
            nodes=(
                Node(id="caller", trust="trusted", attrs=("code=src/widget/**",)),
                Node(id="worker", trust="trusted"),
            ),
            flows=(Flow(id="f1", src="caller", dst="worker", attrs=("timeout",)),),
        )
        result = check_reliability_timeouts(model, tmp_path)
        assert result.is_ok
        violations = [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_TIMEOUT
        ]
        assert {v.sub_target for v in violations} == {"f1"}
        assert violations[0].node == "caller"

    # frob:tests \
    # tests/unit/strata/test_reliability.py::TestUnprovenTimeout.test_declared_timeout_\
    # with_real_code_evidence_discharges
    def test_declared_timeout_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_io.py",
            "def call():\n    return remote(timeout=30)\n",
        )
        model = KernelModel(
            nodes=(
                Node(id="caller", trust="trusted", attrs=("code=src/widget/**",)),
                Node(id="worker", trust="trusted"),
            ),
            flows=(Flow(id="f1", src="caller", dst="worker", attrs=("timeout",)),),
        )
        result = check_reliability_timeouts(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_TIMEOUT
        ]

    # frob:tests \
    # tests/unit/strata/test_reliability.py::TestUnprovenTimeout.test_declared_timeout_\
    # with_no_bound_code_is_uncheckable_not_a_violation
    def test_declared_timeout_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        # caller declares no `code=` glob at all -- REL201 cannot check it,
        # so it must stay silent rather than guess at a violation.
        model = KernelModel(
            nodes=(
                Node(id="caller", trust="trusted"),
                Node(id="worker", trust="trusted"),
            ),
            flows=(Flow(id="f1", src="caller", dst="worker", attrs=("timeout",)),),
        )
        result = check_reliability_timeouts(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_TIMEOUT
        ]

    # frob:tests \
    # tests/unit/strata/test_reliability.py::TestUnprovenTimeout.test_codeless_src_with\
    # _coded_dst_proves_against_dst
    def test_codeless_src_with_coded_dst_proves_against_dst(self, tmp_path: Path):
        # T-0758: this is the f_registry_fetch shape -- the flow's SRC
        # (a foreign external registry) has no bound code at all, but its
        # DST (the vet caller) does, and that dst code has a real
        # `timeout=` token. REL201 must anchor proof on dst and report
        # PROVED (no violation), not skip it as uncheckable the way it
        # would if only src were ever considered.
        _write(
            tmp_path,
            "src/vet/_nvd.py",
            "def fetch():\n    return urlopen(url, timeout=timeout_s)\n",
        )
        model = KernelModel(
            nodes=(
                Node(id="registry", trust="untrusted"),
                Node(id="vet", trust="trusted", attrs=("code=src/vet/**",)),
            ),
            flows=(
                Flow(
                    id="f_registry_fetch",
                    src="registry",
                    dst="vet",
                    attrs=("timeout",),
                ),
            ),
        )
        result = check_reliability_timeouts(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_TIMEOUT
        ]

    # frob:tests \
    # tests/unit/strata/test_reliability.py::TestUnprovenTimeout.test_codeless_src_with\
    # _coded_dst_lacking_evidence_fires_against_dst
    def test_codeless_src_with_coded_dst_lacking_evidence_fires_against_dst(
        self, tmp_path: Path
    ):
        # Same codeless-src/coded-dst shape, but dst's bound code has no
        # real timeout= token -- REL201 must still fire, reporting the
        # dst node (the only endpoint it could actually check).
        _write(tmp_path, "src/vet/_nvd.py", "def fetch():\n    return urlopen(url)\n")
        model = KernelModel(
            nodes=(
                Node(id="registry", trust="untrusted"),
                Node(id="vet", trust="trusted", attrs=("code=src/vet/**",)),
            ),
            flows=(
                Flow(
                    id="f_registry_fetch",
                    src="registry",
                    dst="vet",
                    attrs=("timeout",),
                ),
            ),
        )
        result = check_reliability_timeouts(model, tmp_path)
        assert result.is_ok
        violations = [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_TIMEOUT
        ]
        assert {v.sub_target for v in violations} == {"f_registry_fetch"}
        assert violations[0].node == "vet"


class TestMissingHealth:
    # frob:tests \
    # tests/unit/strata/test_reliability.py::TestMissingHealth.test_daemon_without_heal\
    # th_fires
    def test_daemon_without_health_fires(self, tmp_path: Path):
        _module, model = _load("reliability_health_missing_vuln.strata")
        result = check_reliability_health(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        missing = [v for v in report.violations if v.rule == REL_MISSING_HEALTH]
        nodes = {v.node for v in missing}
        assert nodes == {"api_missing"}
        # api_ok (declares `attr health;`) and plain_store (not a daemon
        # node at all) must not spuriously fire.
        assert "api_ok" not in nodes
        assert "plain_store" not in nodes

    # frob:tests \
    # tests/unit/strata/test_reliability.py::TestMissingHealth.test_discharged_daemon_n\
    # odes_clean
    def test_discharged_daemon_nodes_clean(self, tmp_path: Path):
        _module, model = _load("reliability_health_clean.strata")
        result = check_reliability_health(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not [v for v in report.violations if v.rule == REL_MISSING_HEALTH]

    # frob:tests \
    # tests/unit/strata/test_reliability.py::TestMissingHealth.test_waiver_on_one_node_\
    # keeps_sibling_node_finding
    def test_waiver_on_one_node_keeps_sibling_node_finding(self, tmp_path: Path):
        _module, model = _load("reliability_health_waived.strata")
        result = check_reliability_health(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        kept = {v.node for v in report.violations if v.rule == REL_MISSING_HEALTH}
        waived = {v.node for v in report.waived if v.rule == REL_MISSING_HEALTH}
        assert kept == {"api_other"}
        assert waived == {"api_missing"}


class TestUnprovenHealth:
    """REL211 proof-against-code needs a real file tree bound via
    `bind_code` -- a parsed `.strata` fixture alone cannot exercise it, so
    these build a `KernelModel` directly (the `TestUnprovenTimeout`
    precedent above) against `tmp_path`."""

    # frob:tests \
    # tests/unit/strata/test_reliability.py::TestUnprovenHealth.test_declared_health_wi\
    # th_no_code_evidence_fires
    def test_declared_health_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(tmp_path, "src/widget/_app.py", "def handler():\n    return 'ok'\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="api",
                    trust="trusted",
                    attrs=("unit", "health", "code=src/widget/**"),
                ),
            ),
        )
        result = check_reliability_health(model, tmp_path)
        assert result.is_ok
        violations = [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_HEALTH
        ]
        assert {v.node for v in violations} == {"api"}

    # frob:tests \
    # tests/unit/strata/test_reliability.py::TestUnprovenHealth.test_declared_health_wi\
    # th_real_code_evidence_discharges
    def test_declared_health_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_app.py",
            "@app.route('/healthz')\ndef healthz():\n    return 'ok'\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="api",
                    trust="trusted",
                    attrs=("unit", "health", "code=src/widget/**"),
                ),
            ),
        )
        result = check_reliability_health(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_HEALTH
        ]

    # frob:tests \
    # tests/unit/strata/test_reliability.py::TestUnprovenHealth.test_declared_health_wi\
    # th_no_bound_code_is_uncheckable_not_a_violation
    def test_declared_health_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        # api declares no `code=` glob at all -- REL211 cannot check it,
        # so it must stay silent rather than guess at a violation.
        model = KernelModel(
            nodes=(Node(id="api", trust="trusted", attrs=("unit", "health")),),
        )
        result = check_reliability_health(model, tmp_path)
        assert result.is_ok
        assert not [
            v for v in result.danger_ok.violations if v.rule == REL_UNPROVEN_HEALTH
        ]


class TestCrossFamilyWaiverScoping:
    """Reviewer-caught regression (T-0644 REJECT round): `check_reliability_
    health` only ever produces REL210/REL211 findings, so a SHARED
    `in_scope=RELIABILITY_RULES` made it treat every declared REL200/
    REL201 waiver as stale (it can never match one, since it never sees a
    REL200/REL201 finding) -- reddening `frob sys audit`'s reliability leg
    on a repo with pre-existing, genuinely-effective REL200 waivers (this
    repo's own `graph_cache__fill`/`graph_cache__inval_f_parse`) even
    though `check_reliability_timeouts` correctly matched and applied
    those SAME waivers in its own pass. Fix: each entrypoint scopes
    `in_scope` to its OWN rule family (`_TIMEOUT_RULES`/`_HEALTH_RULES`),
    never the shared `RELIABILITY_RULES` superset. This model carries
    BOTH a genuine REL200 waiver (on `caller`, for `f_missing`) AND a
    daemon node (`api`) with no health obligation (fires REL210) -- run
    through BOTH entrypoints, neither may report the OTHER family's
    waiver stale."""

    # frob:tests \
    # tests/unit/strata/test_reliability.py::TestCrossFamilyWaiverScoping.test_timeout_\
    # entrypoint_ignores_health_family_and_health_entrypoint_ignores_timeout_family
    def test_timeout_entrypoint_ignores_health_family_and_health_entrypoint_ignores_timeout_family(  # noqa: E501
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(
                    id="caller",
                    trust="trusted",
                    waives=(
                        Waiver(
                            rule="REL200:f_missing",
                            reason="known dev-only debug hook, tracked in T-0640",
                        ),
                    ),
                ),
                Node(id="worker", trust="trusted"),
                Node(id="api", trust="trusted", attrs=("unit",)),
            ),
            flows=(Flow(id="f_missing", src="caller", dst="worker"),),
        )

        timeouts = check_reliability_timeouts(model, tmp_path)
        assert timeouts.is_ok
        timeout_report = timeouts.danger_ok
        # The genuine REL200 waiver on f_missing is applied (not stale),
        # and no cross-family RELWAIVE002 finding leaks in from REL210.
        assert {v.sub_target for v in timeout_report.waived} == {"f_missing"}
        assert not [v for v in timeout_report.violations if v.rule == "RELWAIVE002"]

        health = check_reliability_health(model, tmp_path)
        assert health.is_ok
        health_report = health.danger_ok
        # REL210 fires for api (no health obligation), and the entrypoint
        # that never sees a REL200 finding must NOT report the caller's
        # REL200 waiver as stale -- this is the exact regression: a
        # shared in_scope made every REL200/REL201 waiver look
        # unmatched-this-run to check_reliability_health.
        assert {
            v.node for v in health_report.violations if v.rule == REL_MISSING_HEALTH
        } == {"api"}
        assert not [v for v in health_report.violations if v.rule == "RELWAIVE002"]
        assert not health_report.waived
