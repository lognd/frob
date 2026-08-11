"""T-2083: `_reverify_done_report_claims_post_merge` must never collapse a
SKIPPED (unmeasured) claims re-verification into the same `Ok(None)` a real
PASS returns -- that equivalence is the exact defect class T-2076 already
fixed one instance of (T-1584 landing 8 error-severity findings under a
Done report claiming "land-parity: clean" because an unmeasured check read
as a clean one). This module is a small, dedicated test file rather than
an addition to the 16000+-line `tests/test_ticket_land.py`, to avoid
taking a write lease on that file for a two-site fix.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets import Origin, TicketKind, TicketSpec, new_ticket
from frob.tickets._land_verify import (
    _ClaimsReverifyOutcome,
    _reverify_done_report_claims_post_merge,
)
from frob.tickets._models import DoneReportClaims, render_claims_block
from frob.tickets._store import atomic_write, ledger_path, load_all, write_ticket


# frob:waive DUP001 reason="the run/git-init/commit-all/spec/repo-fixture quintet is \
# an established real-git-fixture idiom this test module family repeats verbatim \
# (tests/test_ticket_work_and_land_finish.py's own \
# _run/_git_init/_commit_all/_spec/repo carries the identical DUP001 waiver already, \
# same established idiom text) -- extracting a shared conftest helper is a real, \
# independent cleanup outside T-2083's own scope, not something to fold into a \
# two-site bug fix"
def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _spec(title: str) -> TicketSpec:
    return TicketSpec(title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A minimal git checkout with an initialized ledger, matching the
    real-git fixture idiom `tests/test_ticket_work_and_land_finish.py`'s
    own `repo` fixture uses (DUP001-waived there as an established,
    repeated idiom across this test family)."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    atomic_write(ledger_path(main_repo), "# Tickets\n\n")
    _commit_all(main_repo, "init")
    return main_repo


# frob:ticket T-2083
# frob:tests tests/test_land_verify_claims_outcome.py::TestClaimsReverifyOutcomeDistinguishesSkipFromPass.test_unmeasured_passing_ids_and_check_gates_is_surfaced_as_skipped  # noqa: E501
# frob:tests tests/test_land_verify_claims_outcome.py::TestClaimsReverifyOutcomeDistinguishesSkipFromPass.test_no_captured_claims_section_is_surfaced_as_skipped  # noqa: E501
# frob:tests tests/test_land_verify_claims_outcome.py::TestClaimsReverifyOutcomeDistinguishesSkipFromPass.test_a_real_reverification_that_passes_is_surfaced_as_passed  # noqa: E501
class TestClaimsReverifyOutcomeDistinguishesSkipFromPass:
    """SKIPPED and PASSED must be distinguishable at the RETURN VALUE, not
    just in a log line -- a caller that reads `.danger_ok` and only checks
    `.is_err` (as `_land.py`'s own call site does today) must not be able
    to mistake one for the other."""

    def test_unmeasured_passing_ids_and_check_gates_is_surfaced_as_skipped(
        self, tmp_path: Path
    ) -> None:
        """Site 1 (`passing_ids is None or check_gates is None`): the
        fully-silent skip before this fix -- no log line at all, and a
        bare `Ok(None)` indistinguishable from a real pass. Must now
        return a distinguishable SKIPPED_UNMEASURED outcome."""
        result = _reverify_done_report_claims_post_merge(
            tmp_path, "T-9999", None, None
        )
        assert result.is_ok
        assert result.danger_ok is _ClaimsReverifyOutcome.SKIPPED_UNMEASURED

    def test_no_captured_claims_section_is_surfaced_as_skipped(
        self, repo: Path
    ) -> None:
        """Site 2: a Done report with no `### Captured claims` section
        already logs a WARNING (T-1907) but until this fix still returned
        a bare `Ok(None)` -- indistinguishable, at the return value a
        caller actually inspects, from a real pass."""
        created = new_ticket(repo, _spec("No captured claims"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(repo)
        assert loaded.is_ok
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "body": ticket.body
                + "\n## Done report\n\nDone by hand, no capture run.\n"
            }
        )
        assert write_ticket(repo, ticket).is_ok
        _commit_all(repo, "add done report with no captured claims")

        result = _reverify_done_report_claims_post_merge(
            repo, tid, frozenset(), lambda: (0, 0, 0)
        )
        assert result.is_ok
        assert result.danger_ok is _ClaimsReverifyOutcome.SKIPPED_UNMEASURED

    def test_a_real_reverification_that_passes_is_surfaced_as_passed(
        self, repo: Path
    ) -> None:
        """A Done report WITH a matching Captured claims section, verified
        against a matching fresh `passing_ids`/`check_gates()` pair, is a
        REAL pass -- and must be reported as PASSED, not merely `Ok(None)`,
        so the PASSED/SKIPPED distinction is exhaustive, not one-sided."""
        created = new_ticket(repo, _spec("Real captured claims"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(repo)
        assert loaded.is_ok
        ticket = loaded.danger_ok[tid]
        claims_block = render_claims_block(
            DoneReportClaims(
                test_count=0,
                evidence_count=0,
                gate_errors=0,
                gate_warnings=0,
                gate_waived=0,
            )
        )
        ticket = ticket.model_copy(
            update={
                "body": ticket.body
                + "\n## Done report\n\nReal capture.\n\n"
                + claims_block
                + "\n"
            }
        )
        assert write_ticket(repo, ticket).is_ok
        _commit_all(repo, "add done report with matching captured claims")

        result = _reverify_done_report_claims_post_merge(
            repo, tid, frozenset(), lambda: (0, 0, 0)
        )
        assert result.is_ok
        assert result.danger_ok is _ClaimsReverifyOutcome.PASSED
