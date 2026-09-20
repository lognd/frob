"""T-4911: the boundary `admit { rate_limit ...; max_size ... }` block is
parsed into `AdmitPhase` and modelled in `PhaseBlock`, but at HEAD it is
read by nothing -- `_elaborate.py::_validate_boundary_phases` validates
`parse`/`effect`/`record`/`refuse` but not `admit`, and
`_backpressure.py` infers bounded intake from a source-text regex instead
of the declared ceiling. This module covers both leaves: the elaborator
validator/desugaring in `frob.strata._elaborate`, and the backpressure
declared-over-guessed preference in `frob.strata._backpressure`.
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import (
    AdmitPhase,
    Boundary,
    BoundaryDecl,
    BoundaryDirection,
    BoundClaim,
    Claim,
    Flow,
    FlowDecl,
    KernelModel,
    Metric,
    Module,
    Node,
    NodeDecl,
    PhaseBlock,
    Quantity,
    StrataError,
)
from frob.strata._backpressure import (
    REL_UNPROVEN_BOUNDED_INTAKE,
    check_backpressure_obligations,
)
from frob.strata._elaborate import elaborate


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _module_with_admit(
    *, rate_limit: Quantity | None = None, max_size: Quantity | None = None
) -> Module:
    """A minimal two-node module with one endorsing boundary declaring
    `admit`, used by both the elaborator and the desugaring tests below."""
    return Module(
        name="admit_wiring",
        nodes=(
            NodeDecl(id="edge", trust="foreign"),
            NodeDecl(id="core", trust="trusted"),
        ),
        flows=(FlowDecl(id="f_in", src="edge", dst="core"),),
        boundaries=(
            BoundaryDecl(
                id="b_admit",
                flow_id="f_in",
                kind="endorse",
                from_level="foreign",
                to_level="trusted",
                phases=PhaseBlock(
                    admit=AdmitPhase(rate_limit=rate_limit, max_size=max_size)
                ),
            ),
        ),
    )


class TestAdmitPhaseValidation:
    """`_validate_boundary_phases` now validates the `admit` phase (acceptance 1)."""

    # frob:tests \
    # tests/unit/strata/test_admit_phase_wiring.py::TestAdmitPhaseValidation.test_valid_admit_rate_and_size_elaborates  # noqa: E501
    def test_valid_admit_rate_and_size_elaborates(self):
        module = _module_with_admit(
            rate_limit=Quantity(value=100, unit="req/s"),
            max_size=Quantity(value=64, unit="KiB"),
        )
        result = elaborate(module)
        assert result.is_ok, result.err

    # frob:tests \
    # tests/unit/strata/test_admit_phase_wiring.py::TestAdmitPhaseValidation.test_admit_rate_limit_with_wrong_dimension_fails_closed  # noqa: E501
    def test_admit_rate_limit_with_wrong_dimension_fails_closed(self):
        module = _module_with_admit(rate_limit=Quantity(value=100, unit="KiB"))
        result = elaborate(module)
        assert result.is_err
        assert result.danger_err == StrataError.UnitMismatch

    # frob:tests \
    # tests/unit/strata/test_admit_phase_wiring.py::TestAdmitPhaseValidation.test_admit_max_size_with_wrong_dimension_fails_closed  # noqa: E501
    def test_admit_max_size_with_wrong_dimension_fails_closed(self):
        module = _module_with_admit(max_size=Quantity(value=10, unit="req/s"))
        result = elaborate(module)
        assert result.is_err
        assert result.danger_err == StrataError.UnitMismatch


class TestAdmitBoundDesugaring:
    """A declared `admit` block desugars into `BoundClaim` kernel facts."""

    # frob:tests \
    # tests/unit/strata/test_admit_phase_wiring.py::TestAdmitBoundDesugaring.test_admit_rate_limit_emits_bound_claim  # noqa: E501
    def test_admit_rate_limit_emits_bound_claim(self):
        module = _module_with_admit(rate_limit=Quantity(value=50, unit="req/s"))
        result = elaborate(module)
        assert result.is_ok, result.err
        model = result.danger_ok
        rate_claims = [
            c
            for c in model.claims
            if isinstance(c.body, BoundClaim) and c.body.metric == Metric.RATE
        ]
        assert len(rate_claims) == 1
        body = rate_claims[0].body
        assert isinstance(body, BoundClaim)
        assert body.target == "b_admit"
        assert body.limit == Quantity(value=50, unit="req/s")

    # frob:tests \
    # tests/unit/strata/test_admit_phase_wiring.py::TestAdmitBoundDesugaring.test_no_admit_block_emits_no_bound_claim  # noqa: E501
    def test_no_admit_block_emits_no_bound_claim(self):
        module = Module(
            name="no_admit",
            nodes=(
                NodeDecl(id="edge", trust="foreign"),
                NodeDecl(id="core", trust="trusted"),
            ),
            flows=(FlowDecl(id="f_in", src="edge", dst="core"),),
            boundaries=(
                BoundaryDecl(
                    id="b_plain",
                    flow_id="f_in",
                    kind="endorse",
                    from_level="foreign",
                    to_level="trusted",
                ),
            ),
        )
        result = elaborate(module)
        assert result.is_ok, result.err
        assert not [
            c for c in result.danger_ok.claims if isinstance(c.body, BoundClaim)
        ]


class TestBackpressureDeclaredCeiling:
    """T-4911 acceptance 2/3: a declared `admit rate_limit` CHANGES the
    REL261 backpressure verdict, and the regex fallback still applies when
    no `admit` block is declared."""

    # frob:tests \
    # tests/unit/strata/test_admit_phase_wiring.py::TestBackpressureDeclaredCeiling.test_declared_admit_ceiling_discharges_with_no_code_token  # noqa: E501
    def test_declared_admit_ceiling_discharges_with_no_code_token(self, tmp_path: Path):
        """POSITIVE CONTROL: bound code has NO bounded-intake token, so the
        regex path alone would fire REL261 (proven at HEAD-minus-admit,
        below). With a declared `admit rate_limit` on the inbound
        boundary, REL261 must NOT fire -- the declaration is the proof."""
        _write(tmp_path, "src/widget/_io.py", "def handle(item):\n    process(item)\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="core",
                    trust="trusted",
                    attrs=("consumer", "bounded_intake", "code=src/widget/**"),
                ),
            ),
            flows=(Flow(id="f_in", src="edge", dst="core"),),
            boundaries=(
                Boundary(
                    id="b_admit",
                    flow_id="f_in",
                    direction=BoundaryDirection.ENDORSE,
                    from_level="foreign",
                    to_level="trusted",
                ),
            ),
        )
        # Fails today (HEAD): no admit block declared -> regex path -> REL261 fires.
        no_admit_result = check_backpressure_obligations(model, tmp_path)
        assert no_admit_result.is_ok
        assert {
            v.node
            for v in no_admit_result.danger_ok.violations
            if v.rule == REL_UNPROVEN_BOUNDED_INTAKE
        } == {"core"}

        declared_model = model.model_copy(
            update={
                "claims": (
                    *model.claims,
                    Claim(
                        id="b_admit.admit.rate",
                        body=BoundClaim(
                            metric=Metric.RATE,
                            target="b_admit",
                            limit=Quantity(value=10, unit="req/s"),
                        ),
                        assumed=True,
                    ),
                )
            }
        )
        declared_result = check_backpressure_obligations(declared_model, tmp_path)
        assert declared_result.is_ok
        assert not [
            v
            for v in declared_result.danger_ok.violations
            if v.rule == REL_UNPROVEN_BOUNDED_INTAKE and v.node == "core"
        ]

    # frob:tests \
    # tests/unit/strata/test_admit_phase_wiring.py::TestBackpressureDeclaredCeiling.test_no_admit_block_still_uses_regex_fallback  # noqa: E501
    def test_no_admit_block_still_uses_regex_fallback(self, tmp_path: Path):
        """Converse control: with no declared `admit` block, the regex
        inference still applies (this leaf does not delete it)."""
        _write(
            tmp_path,
            "src/widget/_io.py",
            "import queue\nq = queue.Queue(maxsize=100)\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="core",
                    trust="trusted",
                    attrs=("consumer", "bounded_intake", "code=src/widget/**"),
                ),
            ),
        )
        result = check_backpressure_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_BOUNDED_INTAKE
        ]
