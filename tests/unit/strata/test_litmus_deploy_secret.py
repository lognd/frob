"""Surface-syntax secret/deploy litmus goldens (T-0136).

T-0136 exit criterion (docs/strata/surface.md#std-secrets, #std-deploy):
`design/litmus/deploy_secret.strata` must reproduce, end to end through
`parse_module -> elaborate -> evaluate_claims` /
`evaluate_deploy_contracts`, the `secret` construct's issue/revoke/reads
desugaring and the `on deploy` contract's endorsement-chain + canary
schedule, both reaching T-0082/T-0083's landed kernel constructs from real
`.strata` source text for the first time. These goldens are permanent CI
fixtures.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from frob.strata import (
    ClaimResult,
    KernelModel,
    Quantifier,
    SetEquality,
    Verdict,
    elaborate,
    evaluate_claims,
    evaluate_deploy_contracts,
    parse_module,
)

_TODAY = dt.date(2026, 7, 18)


def _repo_root() -> Path:
    """Walk up from this file until a directory containing `frob.toml` is found."""
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "frob.toml").is_file():
            return candidate
    raise RuntimeError(
        "could not locate repo root (no frob.toml found above test file)"
    )


_LITMUS_DIR = _repo_root() / "design" / "litmus"


def _load_model() -> KernelModel:
    text = (_LITMUS_DIR / "deploy_secret.strata").read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    return elaborate(module).danger_ok


def _results(model: KernelModel) -> dict[str, ClaimResult]:
    evaluated = evaluate_claims(model, today=_TODAY).danger_ok
    return {r.claim_id: r for r in evaluated}


class TestDeploySecretGoldens:
    """design/litmus/deploy_secret.strata claim verdicts and deploy contracts,
    evaluated end to end."""

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_secret_desugars_to_issue_revoke_reads_flows(self):
        model = _load_model()
        flow_ids = {f.id for f in model.flows}
        assert {
            "db_creds__issue",
            "db_creds__revoke",
            "db_creds__reads_api",
        } <= flow_ids

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_secret_auto_generates_readers_claim(self):
        model = _load_model()
        readers_claim = next(c for c in model.claims if c.id == "db_creds__readers")
        assert isinstance(readers_claim.body, SetEquality)
        assert readers_claim.body.expected == ("api",)

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_secret_age_bound_proves_off_the_issue_flow(self):
        result = _results(_load_model())["c_secret_age_bound"]
        assert result.verdict is Verdict.PROVED
        assert result.quantifier is Quantifier.FORALL

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_on_deploy_lands_on_worker_node(self):
        model = _load_model()
        worker_node = next(n for n in model.nodes if n.id == "worker")
        assert worker_node.deploy is not None
        assert [s.level for s in worker_node.deploy.stages] == [
            "authenticated",
            "trusted",
        ]
        assert worker_node.deploy.endorsement_chain == ("review_gate",)
        assert worker_node.deploy.rollback_budget.value == 10.0
        assert worker_node.deploy.rollback_budget.unit == "min"

    # frob:tests src/frob/strata/_deploy.py::evaluate_deploy_contracts kind="unit"
    def test_on_deploy_reaches_evaluate_deploy_contracts_end_to_end(self):
        model = _load_model()
        report = evaluate_deploy_contracts(model, today=_TODAY)
        assert report.is_ok
        # 2 canary stages + 1 rollback scenario for the one deploying node.
        assert len(report.danger_ok.scenario_results) == 3
