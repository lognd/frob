"""Tests for T-0571's structured adversarial-review evidence channel:
`frob.tickets.record_review`/`has_approved_review_for_commit`/
`load_require_review_for_close` (library) and `frob ticket review` /
`frob ticket close --strict` (CLI) (docs/modules/tickets.md#review-record).
"""


from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import _close, _review
from frob.tickets import (
    Origin,
    ReviewVerdict,
    Ticket,
    TicketError,
    TicketKind,
    TicketSpec,
    TicketState,
    has_approved_review_for_commit,
    load_queue,
    load_require_review_for_close,
    new_ticket,
    record_review,
    transition,
)


def _git(root: Path, *args: str) -> str:
    """Run `git <args>` in `root`, returning stripped stdout -- the shared
    plumbing behind this module's real-repo fixtures (T-0571 review round
    2's commit-normalization tests need genuine git objects to resolve
    against, not fabricated sha-shaped strings)."""
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _init_git_repo(root: Path) -> str:
    """Initialize a real git repo under `root` with one commit; returns
    its full SHA."""
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(root, "add", "seed.txt")
    _git(root, "commit", "-q", "-m", "seed commit")
    return _git(root, "rev-parse", "HEAD")


def _short_sha(root: Path, full_sha: str) -> str:
    """The abbreviated form git itself would print for `full_sha` -- a
    genuine short SHA, not a hand-truncated stand-in."""
    short = _git(root, "rev-parse", "--short", full_sha)
    assert short != full_sha
    return short


def _commit_more(root: Path) -> str:
    """Add a second commit under `root` (already an `_init_git_repo` repo)
    and return its full SHA -- gives stale-vs-current-commit tests a real
    second commit to distinguish."""
    (root / "more.txt").write_text("more\n", encoding="utf-8")
    _git(root, "add", "more.txt")
    _git(root, "commit", "-q", "-m", "second commit")
    return _git(root, "rev-parse", "HEAD")


def _seed_in_progress_ticket(tmp_path: Path) -> Ticket:
    """One in-progress ticket carrying a substantive Done report + evidence
    -- the minimum state `close` (non-strict) already accepts, before this
    module's tests layer T-0571's review requirement on top.

    T-1006: the evidence id must actually collect and pass against
    `tmp_path` -- `_close`'s N-02 evidence reverification (added after this
    fixture was first written) now re-runs every non-`cmd:` evidence id at
    close time via a real `pytest --collect-only`/run against `root`, so a
    fabricated id like the old `tests/fixture.py::test_ok` (no such file)
    always fails to re-verify and blocks the close this fixture exists to
    set up. Write one trivial always-green test under `tmp_path` instead so
    reverification has something real to find."""
    (tmp_path / "tests").mkdir(exist_ok=True)
    (tmp_path / "tests" / "test_fixture.py").write_text(
        "def test_ok() -> None:\n    assert True\n", encoding="utf-8"
    )
    created = new_ticket(
        tmp_path,
        TicketSpec(
            title="review fixture",
            kind=TicketKind.FEATURE,
            origin=Origin.AGENT,
            body="## Description\nx\n\n## Done report\nAll good.\n",
            evidence=("tests/test_fixture.py::test_ok",),
        ),
    )
    assert created.is_ok, created
    ticket = created.danger_ok
    transition(tmp_path, ticket.id, TicketState.PLANNED)
    transition(tmp_path, ticket.id, TicketState.IN_PROGRESS)
    return ticket


class TestRecordReview:
    def test_appends_approve_entry(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_tickets_review.py::TestRecordReview.test_appends_approve_entry
        full_sha = _init_git_repo(tmp_path)
        ticket = _seed_in_progress_ticket(tmp_path)
        result = record_review(
            tmp_path,
            ticket.id,
            verdict=ReviewVerdict.APPROVE,
            reviewer="reviewer-agent",
            findings="no issues found",
            commit=full_sha,
        )
        assert result.is_ok, result
        updated = result.danger_ok
        assert len(updated.reviews) == 1
        entry = updated.reviews[0]
        assert entry.verdict is ReviewVerdict.APPROVE
        assert entry.reviewer == "reviewer-agent"
        assert entry.findings == "no issues found"
        assert entry.commit == full_sha
        assert entry.at == date.today()

    def test_blank_findings_rejected(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_tickets_review.py::TestRecordReview.test_blank_findings_rejected
        full_sha = _init_git_repo(tmp_path)
        ticket = _seed_in_progress_ticket(tmp_path)
        result = record_review(
            tmp_path,
            ticket.id,
            verdict=ReviewVerdict.REJECT,
            reviewer="reviewer-agent",
            findings="   ",
            commit=full_sha,
        )
        assert result.is_err
        assert result.danger_err == TicketError.ReviewFindingsMissing

    def test_multiple_reviews_append_only(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_review.py::TestRecordReview.test_multiple_reviews_append_only  # noqa: E501
        full_sha = _init_git_repo(tmp_path)
        second_sha = _commit_more(tmp_path)
        ticket = _seed_in_progress_ticket(tmp_path)
        record_review(
            tmp_path,
            ticket.id,
            verdict=ReviewVerdict.REJECT,
            reviewer="r1",
            findings="found a bug",
            commit=full_sha,
        )
        result = record_review(
            tmp_path,
            ticket.id,
            verdict=ReviewVerdict.APPROVE,
            reviewer="r2",
            findings="bug fixed, approving",
            commit=second_sha,
        )
        assert result.is_ok, result
        assert len(result.danger_ok.reviews) == 2

    def test_unresolvable_commit_rejected(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_review.py::TestRecordReview.test_unresolvable_commit_rejected  # noqa: E501
        _init_git_repo(tmp_path)
        ticket = _seed_in_progress_ticket(tmp_path)
        result = record_review(
            tmp_path,
            ticket.id,
            verdict=ReviewVerdict.APPROVE,
            reviewer="reviewer-agent",
            findings="fine",
            commit="not-a-real-ref-0000",
        )
        assert result.is_err
        assert result.danger_err == TicketError.ReviewCommitUnresolvable
        # Nothing was stored on the ticket -- a bad commit is never
        # written verbatim.
        reload = load_queue(tmp_path).danger_ok.tickets[ticket.id]
        assert reload.reviews == ()

    def test_short_sha_normalized_to_full_sha(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_review.py::TestRecordReview.test_short_sha_normalized_to_full_sha  # noqa: E501
        full_sha = _init_git_repo(tmp_path)
        short_sha = _short_sha(tmp_path, full_sha)
        ticket = _seed_in_progress_ticket(tmp_path)
        result = record_review(
            tmp_path,
            ticket.id,
            verdict=ReviewVerdict.APPROVE,
            reviewer="reviewer-agent",
            findings="approving via short sha",
            commit=short_sha,
        )
        assert result.is_ok, result
        # The record stores the FULL sha, never the caller's abbreviated
        # input -- this is exactly what makes has_approved_review_for_commit
        # (a plain string-equality check against a full rev-parse HEAD)
        # able to match it later.
        assert result.danger_ok.reviews[0].commit == full_sha


class TestHasApprovedReviewForCommit:
    def test_true_only_for_matching_approve(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_review.py::TestHasApprovedReviewForCommit.test_true_only_for_matching_approve  # noqa: E501
        first_sha = _init_git_repo(tmp_path)
        current_sha = _commit_more(tmp_path)
        ticket = _seed_in_progress_ticket(tmp_path)
        record_review(
            tmp_path,
            ticket.id,
            verdict=ReviewVerdict.REJECT,
            reviewer="r1",
            findings="rejecting stale commit",
            commit=first_sha,
        )
        stale_reload = load_queue(tmp_path).danger_ok.tickets[ticket.id]
        assert has_approved_review_for_commit(stale_reload, current_sha) is False

        record_review(
            tmp_path,
            ticket.id,
            verdict=ReviewVerdict.APPROVE,
            reviewer="r2",
            findings="approving current commit",
            commit=current_sha,
        )
        reload = load_queue(tmp_path).danger_ok.tickets[ticket.id]
        assert has_approved_review_for_commit(reload, current_sha) is True
        # An approval naming a DIFFERENT (older) commit than the one asked
        # about must not count -- code moved since that review.
        assert has_approved_review_for_commit(reload, first_sha) is False


class TestLoadRequireReviewForClose:
    def test_defaults_false_with_no_frob_toml(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_review.py::TestLoadRequireReviewForClose.test_defaults_false_with_no_frob_toml  # noqa: E501
        assert load_require_review_for_close(tmp_path) is False

    def test_true_when_configured(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_review.py::TestLoadRequireReviewForClose.test_true_when_configured  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            "[tickets]\nrequire_review_for_close = true\n", encoding="utf-8"
        )
        assert load_require_review_for_close(tmp_path) is True

    def test_false_when_absent_from_section(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_review.py::TestLoadRequireReviewForClose.test_false_when_absent_from_section  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            "[tickets]\nlarge_glob_max_files = 5\n", encoding="utf-8"
        )
        assert load_require_review_for_close(tmp_path) is False


class TestReviewCli:
    def test_cli_writes_review_record(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_tickets_review.py::TestReviewCli.test_cli_writes_review_record
        full_sha = _init_git_repo(tmp_path)
        short_sha = _short_sha(tmp_path, full_sha)
        ticket = _seed_in_progress_ticket(tmp_path)
        findings_file = tmp_path / "findings.txt"
        findings_file.write_text("verified the counterexample probe", encoding="utf-8")
        cfg = AppConfig(
            ticket_command="review",
            ticket_id=ticket.id,
            ticket_path=tmp_path,
            ticket_review_verdict="approve",
            ticket_reviewer="reviewer-agent",
            ticket_findings_file=findings_file,
            ticket_review_commit=short_sha,
        )
        _review(tmp_path, cfg)

        reload = load_queue(tmp_path).danger_ok.tickets[ticket.id]
        assert len(reload.reviews) == 1
        assert reload.reviews[0].verdict is ReviewVerdict.APPROVE
        # The CLI passed an abbreviated --commit; the stored record must
        # carry the full sha it normalized to, not the short form.
        assert reload.reviews[0].commit == full_sha
        assert reload.reviews[0].findings == "verified the counterexample probe"

    def test_cli_requires_all_flags(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_tickets_review.py::TestReviewCli.test_cli_requires_all_flags
        ticket = _seed_in_progress_ticket(tmp_path)
        cfg = AppConfig(
            ticket_command="review",
            ticket_id=ticket.id,
            ticket_path=tmp_path,
            ticket_review_verdict="approve",
        )
        with pytest.raises(SystemExit) as exc:
            _review(tmp_path, cfg)
        assert exc.value.code == 1


class TestCloseStrictMode:
    """`frob ticket close --strict`, config-gated by `[tickets]
    require_review_for_close` (T-0571): off by default, both must be true
    to actually enforce."""

    def test_strict_flag_alone_does_not_gate_without_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_tickets_review.py::TestCloseStrictMode.test_strict_flag_alone_does_not_gate_without_config  # noqa: E501
        ticket = _seed_in_progress_ticket(tmp_path)
        monkeypatch.setattr(
            "frob.app.ticket_runner._current_commit", lambda root: "head-sha"
        )
        cfg = AppConfig(
            ticket_command="close",
            ticket_id=ticket.id,
            ticket_path=tmp_path,
            ticket_close_strict=True,
        )
        _close(tmp_path, cfg)
        reload = load_queue(tmp_path).danger_ok.tickets[ticket.id]
        assert reload.state == TicketState.DONE

    def test_config_gate_alone_does_not_enforce_without_strict_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_tickets_review.py::TestCloseStrictMode.test_config_gate_alone_does_not_enforce_without_strict_flag  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            "[tickets]\nrequire_review_for_close = true\n", encoding="utf-8"
        )
        ticket = _seed_in_progress_ticket(tmp_path)
        monkeypatch.setattr(
            "frob.app.ticket_runner._current_commit", lambda root: "head-sha"
        )
        cfg = AppConfig(
            ticket_command="close",
            ticket_id=ticket.id,
            ticket_path=tmp_path,
        )
        _close(tmp_path, cfg)
        reload = load_queue(tmp_path).danger_ok.tickets[ticket.id]
        assert reload.state == TicketState.DONE

    def test_both_gates_on_blocks_close_with_no_review(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_tickets_review.py::TestCloseStrictMode.test_both_gates_on_blocks_close_with_no_review  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            "[tickets]\nrequire_review_for_close = true\n", encoding="utf-8"
        )
        ticket = _seed_in_progress_ticket(tmp_path)
        monkeypatch.setattr(
            "frob.app.ticket_runner._current_commit", lambda root: "head-sha"
        )
        cfg = AppConfig(
            ticket_command="close",
            ticket_id=ticket.id,
            ticket_path=tmp_path,
            ticket_close_strict=True,
        )
        with pytest.raises(SystemExit) as exc:
            _close(tmp_path, cfg)
        assert exc.value.code == 1
        reload = load_queue(tmp_path).danger_ok.tickets[ticket.id]
        assert reload.state == TicketState.IN_PROGRESS

    def test_both_gates_on_succeeds_with_matching_approve_review(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_tickets_review.py::TestCloseStrictMode.test_both_gates_on_succeeds_with_matching_approve_review  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            "[tickets]\nrequire_review_for_close = true\n", encoding="utf-8"
        )
        full_sha = _init_git_repo(tmp_path)
        ticket = _seed_in_progress_ticket(tmp_path)
        monkeypatch.setattr(
            "frob.app.ticket_runner._current_commit", lambda root: full_sha
        )
        record_review(
            tmp_path,
            ticket.id,
            verdict=ReviewVerdict.APPROVE,
            reviewer="reviewer-agent",
            findings="verified, approving",
            commit=full_sha,
        )
        cfg = AppConfig(
            ticket_command="close",
            ticket_id=ticket.id,
            ticket_path=tmp_path,
            ticket_close_strict=True,
        )
        _close(tmp_path, cfg)
        reload = load_queue(tmp_path).danger_ok.tickets[ticket.id]
        assert reload.state == TicketState.DONE

    def test_both_gates_on_succeeds_with_abbreviated_review_commit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0571 review round 2 regression: a reviewer records via a
        genuinely abbreviated SHA (e.g. copied from `git log --oneline`);
        `record_review` normalizes it to the full sha at write time, so
        `close --strict` -- which compares against the full `rev-parse
        HEAD` sha -- must still succeed."""
        # frob:tests tests/test_tickets_review.py::TestCloseStrictMode.test_both_gates_on_succeeds_with_abbreviated_review_commit  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            "[tickets]\nrequire_review_for_close = true\n", encoding="utf-8"
        )
        full_sha = _init_git_repo(tmp_path)
        short_sha = _short_sha(tmp_path, full_sha)
        ticket = _seed_in_progress_ticket(tmp_path)
        monkeypatch.setattr(
            "frob.app.ticket_runner._current_commit", lambda root: full_sha
        )
        record_result = record_review(
            tmp_path,
            ticket.id,
            verdict=ReviewVerdict.APPROVE,
            reviewer="reviewer-agent",
            findings="verified via short sha, approving",
            commit=short_sha,
        )
        assert record_result.is_ok, record_result
        assert record_result.danger_ok.reviews[0].commit == full_sha

        cfg = AppConfig(
            ticket_command="close",
            ticket_id=ticket.id,
            ticket_path=tmp_path,
            ticket_close_strict=True,
        )
        _close(tmp_path, cfg)
        reload = load_queue(tmp_path).danger_ok.tickets[ticket.id]
        assert reload.state == TicketState.DONE

    def test_both_gates_on_blocks_close_with_stale_approve_review(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_tickets_review.py::TestCloseStrictMode.test_both_gates_on_blocks_close_with_stale_approve_review  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            "[tickets]\nrequire_review_for_close = true\n", encoding="utf-8"
        )
        old_sha = _init_git_repo(tmp_path)
        new_sha = _commit_more(tmp_path)
        ticket = _seed_in_progress_ticket(tmp_path)
        monkeypatch.setattr(
            "frob.app.ticket_runner._current_commit", lambda root: new_sha
        )
        record_review(
            tmp_path,
            ticket.id,
            verdict=ReviewVerdict.APPROVE,
            reviewer="reviewer-agent",
            findings="approved an OLD commit -- code moved since",
            commit=old_sha,
        )
        cfg = AppConfig(
            ticket_command="close",
            ticket_id=ticket.id,
            ticket_path=tmp_path,
            ticket_close_strict=True,
        )
        with pytest.raises(SystemExit) as exc:
            _close(tmp_path, cfg)
        assert exc.value.code == 1
