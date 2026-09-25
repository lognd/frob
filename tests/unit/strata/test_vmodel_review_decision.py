"""Python-level evidence for T-3047: review/decision nodes with a required
`reason`/`commit` payload, exercised through the SAME `strata_core.
vmodel_check` PyO3 boundary `test_vmodel_check.py` uses for the other
node/edge kinds (T-3043's own precedent for why this matters: evidence
bound only to a Rust-internal `cargo test` run previously laundered a
real gap, see that file's module docstring).

Positive controls per T-3047's tree entry: a `decision` node with no
`reason` fails schema validation (surfaces as a `vmodel_check`
construction error); a `decision` superseding an earlier one via a typed
`supersedes` edge carrying a `reason` round-trips through parse -> graph
-> query (exercised here at the `vmodel_check` PyO3 boundary; the
`strata_core.parse_source` round-trip for `vmodel_node`/`vmodel_edge`
statements themselves is already covered by
`strata-core/src/parse/mod.rs::tests::vmodel_node_and_edge_attrs_round_trip`,
unchanged by this ticket since neither statement's grammar has a kind-
specific required-attr concept -- the kernel decides that, not the
parser).
"""

# frob:ticket T-3047
from __future__ import annotations

import pytest

strata_core = pytest.importorskip(
    "strata_core",
    reason="strata_core native extension not built -- run `make core`",
)


class TestDecisionNodeRequiresReason:
    # frob:tests \
    # tests/unit/strata/test_vmodel_review_decision.py::TestDecisionNodeRequiresReason.test_fires_a_construction_error_on_a_bare_decision_node  # noqa: E501
    def test_fires_a_construction_error_on_a_bare_decision_node(self) -> None:
        """T-3047's exact positive control: a decision node with no
        `reason` attr must fail schema validation -- surfaces as a
        `vmodel_check` construction error, the same channel a missing
        `runnable`/`code_ref` already uses."""
        errors, _violations = strata_core.vmodel_check(
            [("decision-1", "decision", None, {})],
            [],
        )
        assert len(errors) == 1
        assert "MissingNodeAttr" in errors[0]

    def test_quiet_when_reason_is_present(self) -> None:
        """Must-stay-quiet twin: the same node with `reason` set
        constructs cleanly."""
        errors, _violations = strata_core.vmodel_check(
            [("decision-1", "decision", None, {"reason": "because X"})],
            [],
        )
        assert errors == []


class TestReviewNodeRequiresCommitAndReason:
    def test_fires_on_a_bare_review_node(self) -> None:
        """A `review` node with neither `commit` nor `reason` fails."""
        errors, _violations = strata_core.vmodel_check(
            [("review-1", "review", None, {})],
            [],
        )
        assert len(errors) == 1
        assert "MissingNodeAttr" in errors[0]

    def test_quiet_when_commit_and_reason_are_present(self) -> None:
        """Must-stay-quiet twin: both required attrs present constructs
        cleanly."""
        errors, _violations = strata_core.vmodel_check(
            [
                (
                    "review-1",
                    "review",
                    None,
                    {"commit": "abc123", "reason": "approved, tests pass"},
                )
            ],
            [],
        )
        assert errors == []


class TestSupersedesRoundTrip:
    # frob:tests \
    # tests/unit/strata/test_vmodel_review_decision.py::TestSupersedesRoundTrip.test_reasoned_supersedes_edge_between_two_decisions_round_trips  # noqa: E501
    def test_reasoned_supersedes_edge_between_two_decisions_round_trips(self) -> None:
        """T-3047's tree positive control, exercised end to end at the
        PyO3 boundary: two decision nodes (each with a `reason`) plus a
        `supersedes` edge (also carrying a `reason`) construct with zero
        errors and zero closure violations -- a full parse-shaped-input
        -> graph -> (implicit query, `vmodel_check` runs `check_closure`
        internally) round-trip."""
        errors, violations = strata_core.vmodel_check(
            [
                ("old-decision", "decision", None, {"reason": "original call"}),
                (
                    "new-decision",
                    "decision",
                    None,
                    {"reason": "supersedes the original call"},
                ),
            ],
            [
                (
                    "supersedes",
                    "new-decision",
                    "old-decision",
                    {"reason": "the original call was wrong, here is why"},
                )
            ],
        )
        assert errors == []
        assert violations == []

    def test_supersedes_edge_missing_reason_is_a_construction_error(self) -> None:
        """Must-fire twin: the same two decision nodes, but the
        `supersedes` edge omits `reason` -- construction refuses it
        (unchanged T-3044 H3 behaviour, re-asserted here alongside the
        review/decision node additions this ticket makes)."""
        errors, _violations = strata_core.vmodel_check(
            [
                ("old-decision", "decision", None, {"reason": "original call"}),
                (
                    "new-decision",
                    "decision",
                    None,
                    {"reason": "supersedes the original call"},
                ),
            ],
            [("supersedes", "new-decision", "old-decision", {})],
        )
        assert len(errors) == 1
        assert "MissingEdgeAttr" in errors[0]

    def test_review_node_can_decide_an_artifact(self) -> None:
        """T-3047: a `review` node is now a legal `decides` source (a
        review's verdict IS a decision about the reviewed artifact), not
        only a standalone `decision` node -- the `decides` edge itself
        must construct with zero errors. This fixture's `design-1` is
        still untested/unjustified per the OTHER closure rules (rules
        1-4, unrelated to this ticket); only the construction-error slot
        is asserted here."""
        errors, _violations = strata_core.vmodel_check(
            [
                (
                    "review-1",
                    "review",
                    None,
                    {"commit": "abc123", "reason": "approved"},
                ),
                (
                    "design-1",
                    "artifact",
                    "component-design",
                    {"code_ref": "src/x.rs:Design1"},
                ),
            ],
            [("decides", "review-1", "design-1", {})],
        )
        assert errors == []
