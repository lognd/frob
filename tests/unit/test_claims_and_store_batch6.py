"""Direct-call coverage for `src/frob/strata/_claims.py` and
`src/frob/tickets/_store.py` remaining branches (T-0160 batch 6).

Both modules already carry substantial coverage from other test files
(test_claims.py, test_capacity.py, the tickets store's own callers); these
tests fill in the specific branches those suites don't reach: malformed
skew/growth attrs, malformed/overdue assume review dates, unit-mismatch and
zero-ceiling bound refutations, RATE/AGE/SIZE-latency unknown-target and
no-declared-quantity paths for _claims.py; malformed frontmatter/YAML,
duplicate ids, and atomic-write/migrate failure paths for _store.py.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from frob.strata import (
    BoundClaim,
    Capacity,
    Claim,
    Flow,
    KernelModel,
    Metric,
    Node,
    Quantity,
    StrataError,
    Verdict,
    evaluate_claims,
)
from frob.tickets._models import Origin, Ticket, TicketError, TicketKind, TicketState
from frob.tickets._store import (
    _parse_ticket_file,
    _serialize_ticket,
    atomic_write,
    migrate_to_ledger,
    write_all,
    write_ticket,
)


def _node(nid: str, trust: str = "trusted", **kw) -> Node:
    """A minimal trusted node for fixtures, forwarding kwargs to `Node`."""
    return Node(id=nid, trust=trust, **kw)


def _flow(fid: str, src: str, dst: str, **kw) -> Flow:
    """A minimal flow for fixtures, forwarding kwargs to `Flow`."""
    return Flow(id=fid, src=src, dst=dst, **kw)


def _one(model: KernelModel, today: dt.date = dt.date(2026, 7, 17)):
    """Evaluate a single-claim model and return its lone `ClaimResult`."""
    results = evaluate_claims(model, today=today).danger_ok
    assert len(results) == 1
    return results[0]


class TestClaimsMalformedAttrs:
    """Malformed `skew=`/`growth=` node/flow attrs (T-0160)."""

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestClaimsMalformedAttrs.test_malformed_skew_attr_is_ignored
    def test_malformed_skew_attr_is_ignored(self, caplog) -> None:
        capacity = Capacity(
            service_rate=Quantity(value=10, unit="req/s"), replicas_max=2
        )
        model = KernelModel(
            nodes=(
                _node("src"),
                _node("hot", capacity=capacity, attrs=("skew=notanumber",)),
            ),
            flows=(_flow("f", "src", "hot", rate=Quantity(value=5, unit="req/s")),),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.UTILIZATION,
                        target="hot",
                        limit=Quantity(value=90, unit="%"),
                    ),
                ),
            ),
        )
        with caplog.at_level("WARNING"):
            result = _one(model)
        assert "malformed skew attr" in caplog.text
        # falls back to unskewed ceiling math (proved: 5/(10*2) = 25%)
        assert result.verdict is Verdict.PROVED

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestClaimsMalformedAttrs.test_malformed_growth_attr_is_ignored
    def test_malformed_growth_attr_is_ignored(self, caplog) -> None:
        capacity = Capacity(
            service_rate=Quantity(value=10, unit="req/s"), replicas_max=1
        )
        model = KernelModel(
            nodes=(_node("src"), _node("hot", capacity=capacity)),
            flows=(
                _flow(
                    "f",
                    "src",
                    "hot",
                    rate=Quantity(value=5, unit="req/s"),
                    attrs=("growth=notanumber",),
                ),
            ),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.UTILIZATION,
                        target="hot",
                        limit=Quantity(value=90, unit="%"),
                    ),
                ),
            ),
        )
        with caplog.at_level("WARNING"):
            result = _one(model)
        assert "malformed growth attr" in caplog.text
        assert result.verdict is Verdict.PROVED


class TestAssumeReviewDates:
    """`assume` claims' review-date detail branches (malformed/overdue)."""

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestAssumeReviewDates.test_malformed_review_date_logs_and_notes
    def test_malformed_review_date_logs_and_notes(self, caplog) -> None:
        model = KernelModel(
            nodes=(_node("api"),),
            claims=(
                Claim(
                    id="c1",
                    assumed=True,
                    owner="alice",
                    review="not-a-date",
                    body=BoundClaim(
                        metric=Metric.LATENCY,
                        target="ghost-flow",
                        limit=Quantity(value=1, unit="s"),
                    ),
                ),
            ),
        )
        with caplog.at_level("WARNING"):
            result = _one(model)
        assert result.verdict is Verdict.ASSUMED
        assert "review date malformed" in result.detail
        assert "malformed review date" in caplog.text

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestAssumeReviewDates.test_overdue_review_date_is_flagged
    def test_overdue_review_date_is_flagged(self, caplog) -> None:
        model = KernelModel(
            nodes=(_node("api"),),
            claims=(
                Claim(
                    id="c1",
                    assumed=True,
                    owner="alice",
                    review="2020-01-01",
                    body=BoundClaim(
                        metric=Metric.LATENCY,
                        target="ghost-flow",
                        limit=Quantity(value=1, unit="s"),
                    ),
                ),
            ),
        )
        with caplog.at_level("WARNING"):
            result = _one(model, today=dt.date(2026, 7, 17))
        assert result.verdict is Verdict.ASSUMED
        assert "review overdue since 2020-01-01" in result.detail
        assert "review overdue" in caplog.text


class TestBoundClaimEdgeCases:
    """AGE/RATE/UTILIZATION unknown-target, unit-mismatch, and zero-ceiling
    refutation branches."""

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases.test_age_unknown_target_fails_closed
    def test_age_unknown_target_fails_closed(self) -> None:
        model = KernelModel(
            nodes=(_node("api"),),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.AGE,
                        target="ghost",
                        limit=Quantity(value=1, unit="s"),
                    ),
                ),
            ),
        )
        outcome = evaluate_claims(model)
        assert outcome.is_err
        assert outcome.danger_err is StrataError.UnknownReference

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases.test_rate_unknown_target_fails_closed
    def test_rate_unknown_target_fails_closed(self) -> None:
        model = KernelModel(
            nodes=(_node("api"),),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.RATE,
                        target="ghost",
                        limit=Quantity(value=1, unit="req/s"),
                    ),
                ),
            ),
        )
        outcome = evaluate_claims(model)
        assert outcome.is_err
        assert outcome.danger_err is StrataError.UnknownReference

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases.test_utilization_wrong_dimension_limit_errors
    def test_utilization_wrong_dimension_limit_errors(self) -> None:
        capacity = Capacity(
            service_rate=Quantity(value=10, unit="req/s"), replicas_max=1
        )
        model = KernelModel(
            nodes=(_node("hot", capacity=capacity),),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.UTILIZATION,
                        target="hot",
                        limit=Quantity(value=1, unit="s"),
                    ),
                ),
            ),
        )
        outcome = evaluate_claims(model)
        assert outcome.is_err
        assert outcome.danger_err is StrataError.UnitMismatch

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases.test_utilization_zero_ceiling_refutes
    def test_utilization_zero_ceiling_refutes(self) -> None:
        capacity = Capacity(
            service_rate=Quantity(value=0, unit="req/s"), replicas_max=1
        )
        model = KernelModel(
            nodes=(_node("src"), _node("hot", capacity=capacity)),
            flows=(_flow("f", "src", "hot", rate=Quantity(value=5, unit="req/s")),),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.UTILIZATION,
                        target="hot",
                        limit=Quantity(value=90, unit="%"),
                    ),
                ),
            ),
        )
        result = _one(model)
        assert result.verdict is Verdict.REFUTED
        assert "zero service ceiling" in result.detail

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases.test_utilization_skewed_zero_ceiling_refutes
    def test_utilization_skewed_zero_ceiling_refutes(self) -> None:
        capacity = Capacity(
            service_rate=Quantity(value=0, unit="req/s"), replicas_max=2
        )
        model = KernelModel(
            nodes=(
                _node("src"),
                _node("hot", capacity=capacity, attrs=("skew=1.5",)),
            ),
            flows=(_flow("f", "src", "hot", rate=Quantity(value=5, unit="req/s")),),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.UTILIZATION,
                        target="hot",
                        limit=Quantity(value=90, unit="%"),
                    ),
                ),
            ),
        )
        result = _one(model)
        assert result.verdict is Verdict.REFUTED
        assert "zero service ceiling" in result.detail

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases.test_latency_unknown_flow_fails_closed
    def test_latency_unknown_flow_fails_closed(self) -> None:
        model = KernelModel(
            nodes=(_node("api"),),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.LATENCY,
                        target="ghost-flow",
                        limit=Quantity(value=1, unit="s"),
                    ),
                ),
            ),
        )
        outcome = evaluate_claims(model)
        assert outcome.is_err
        assert outcome.danger_err is StrataError.UnknownReference

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases.test_latency_on_a_real_flow_is_refused_not_silently_refuted  # noqa: E501
    def test_latency_on_a_real_flow_is_refused_not_silently_refuted(self) -> None:
        """strata audit G11 (T-0497) counterexample: before this fix, a
        LATENCY bound against a REAL flow (not just an unknown target) would
        silently REFUTE-as-missing every time, forever -- `Flow` has no
        `latency` field to ever declare. Prove it now comes back as a typed
        `UnsupportedMetric` error instead of a fake ordinary-looking
        REFUTED verdict."""
        model = KernelModel(
            nodes=(_node("a"), _node("b")),
            flows=(_flow("f1", "a", "b"),),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.LATENCY,
                        target="f1",
                        limit=Quantity(value=1, unit="s"),
                    ),
                ),
            ),
        )
        outcome = evaluate_claims(model)
        assert outcome.is_err
        assert outcome.danger_err is StrataError.UnsupportedMetric

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases.test_size_no_declared_size_refutes
    def test_size_no_declared_size_refutes(self) -> None:
        model = KernelModel(
            nodes=(_node("a"), _node("b")),
            flows=(_flow("f1", "a", "b"),),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.SIZE,
                        target="f1",
                        limit=Quantity(value=1, unit="KB"),
                    ),
                ),
            ),
        )
        result = _one(model)
        assert result.verdict is Verdict.REFUTED
        assert "declares no size to check" in result.detail


class TestTicketStoreParsing:
    """Malformed-frontmatter / malformed-YAML / duplicate-id parse failures."""

    def _base_ticket(self) -> Ticket:
        return Ticket(
            id="T-0001",
            title="a ticket",
            kind=TicketKind.FEATURE,
            state=TicketState.QUEUED,
            origin=Origin.HUMAN,
            created=dt.date(2026, 7, 17),
            body="body text",
        )

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestTicketStoreParsing.test_parse_ticket_file_no_frontmatter_block
    def test_parse_ticket_file_no_frontmatter_block(self, tmp_path: Path) -> None:
        path = tmp_path / "T-0001-x.md"
        path.write_text("no frontmatter here at all\n", encoding="utf-8")
        result = _parse_ticket_file(path)
        assert result.is_err
        assert result.danger_err is TicketError.MalformedFrontmatter

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestTicketStoreParsing.test_parse_ticket_file_bad_yaml
    def test_parse_ticket_file_bad_yaml(self, tmp_path: Path) -> None:
        path = tmp_path / "T-0001-x.md"
        path.write_text("---\n[unterminated: [flow\n---\nbody\n", encoding="utf-8")
        result = _parse_ticket_file(path)
        assert result.is_err
        assert result.danger_err is TicketError.MalformedFrontmatter

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestTicketStoreParsing.test_parse_ticket_file_roundtrips_valid
    def test_parse_ticket_file_roundtrips_valid(self, tmp_path: Path) -> None:
        ticket = self._base_ticket()
        path = tmp_path / "T-0001-x.md"
        path.write_text(_serialize_ticket(ticket), encoding="utf-8")
        result = _parse_ticket_file(path)
        assert result.is_ok
        assert result.danger_ok.id == "T-0001"


class TestTicketStoreWriteAndMigrate:
    """write_ticket/write_all/migrate_to_ledger failure branches, plus
    atomic_write's own OSError path."""

    def _base_ticket(self, ticket_id: str = "T-0001") -> Ticket:
        return Ticket(
            id=ticket_id,
            title="a ticket",
            kind=TicketKind.FEATURE,
            state=TicketState.QUEUED,
            origin=Origin.HUMAN,
            created=dt.date(2026, 7, 17),
            body="body text",
        )

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate.test_write_ticket_single_mode_existing_load_error_propagates
    def test_write_ticket_single_mode_existing_load_error_propagates(
        self, tmp_path: Path
    ) -> None:
        # A malformed existing ledger makes load_all (called by write_ticket
        # in single mode) fail; the Err must propagate, not be swallowed.
        (tmp_path / "tickets.md").write_text(
            "<!-- ticket:T-0001 -->\nnot a yaml fence at all\n", encoding="utf-8"
        )
        result = write_ticket(tmp_path, self._base_ticket())
        assert result.is_err
        assert result.danger_err is TicketError.MalformedFrontmatter

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate.test_write_all_dir_mode_prunes_stale_files
    def test_write_all_dir_mode_prunes_stale_files(self, tmp_path: Path) -> None:
        # Dir-mode is selected by the absence of a single-file tickets.md
        # plus at least one tickets/*.md file already present.
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()
        stale = tickets_dir / "T-0099-stale.md"
        stale.write_text(
            _serialize_ticket(self._base_ticket("T-0099")), encoding="utf-8"
        )

        result = write_all(tmp_path, {"T-0001": self._base_ticket("T-0001")})
        assert result.is_ok
        assert not stale.exists()
        assert any(tickets_dir.glob("T-0001-*.md"))

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate.test_migrate_to_ledger_empty_is_noop
    def test_migrate_to_ledger_empty_is_noop(self, tmp_path: Path) -> None:
        result = migrate_to_ledger(tmp_path)
        assert result.is_ok
        assert result.danger_ok == 0

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate.test_migrate_to_ledger_malformed_file_fails_closed
    def test_migrate_to_ledger_malformed_file_fails_closed(
        self, tmp_path: Path
    ) -> None:
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()
        (tickets_dir / "T-0001-bad.md").write_text("garbage\n", encoding="utf-8")
        result = migrate_to_ledger(tmp_path)
        assert result.is_err
        assert result.danger_err is TicketError.MalformedFrontmatter

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate.test_migrate_to_ledger_moves_dir_files_into_ledger
    def test_migrate_to_ledger_moves_dir_files_into_ledger(
        self, tmp_path: Path
    ) -> None:
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()
        (tickets_dir / "T-0001-a.md").write_text(
            _serialize_ticket(self._base_ticket("T-0001")), encoding="utf-8"
        )
        result = migrate_to_ledger(tmp_path)
        assert result.is_ok
        assert result.danger_ok == 1
        assert not (tickets_dir / "T-0001-a.md").exists()
        assert (tmp_path / "tickets.md").exists()

    # frob:tests tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate.test_atomic_write_oserror_returns_write_failed
    def test_atomic_write_oserror_returns_write_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import frob.tickets._store as store_mod

        def _boom_replace(*_a, **_kw):  # noqa: ANN002, ANN003, ANN202
            raise OSError("disk full")

        monkeypatch.setattr(store_mod.os, "replace", _boom_replace)
        result = atomic_write(tmp_path / "x.txt", "content")
        assert result.is_err
        assert result.danger_err is TicketError.WriteFailed
