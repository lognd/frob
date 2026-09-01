import subprocess
import sys

import pytest

from tests.unit.conftest import (
    _completed,  # noqa: F401 -- T-3596
    verify_lands,
    wait_for_land_slot,
)


class TestResolve:
    """`verify_lands.resolve`."""

    def test_resolves_full_sha(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A resolvable sha/ref returns git's full commit id, stripped."""
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed("abc123\n"))
        assert verify_lands.resolve("abc") == "abc123"

    def test_unknown_sha_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A sha `rev-parse` cannot verify returns None, never raises."""
        monkeypatch.setattr(
            subprocess, "run", lambda *a, **k: _completed("", returncode=128)
        )
        assert verify_lands.resolve("not-a-sha") is None


class TestIsAncestor:
    """`verify_lands.is_ancestor`."""

    def test_true_when_ancestor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`merge-base --is-ancestor` exit 0 means the sha landed."""
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed(returncode=0))
        assert verify_lands.is_ancestor("abc123", "main") is True

    def test_false_when_not_ancestor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A non-zero exit means the sha resolves but never landed on ref."""
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed(returncode=1))
        assert verify_lands.is_ancestor("abc123", "main") is False


class TestSubject:
    """`verify_lands.subject`."""

    def test_returns_commit_subject(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The stripped stdout of `git log -1 --format=%s` is returned."""
        monkeypatch.setattr(
            subprocess, "run", lambda *a, **k: _completed("fix: a thing\n")
        )
        assert verify_lands.subject("abc123") == "fix: a thing"


# frob:ticket T-2220
class TestLoadLandCommit:
    """`verify_lands.load_land_commit` -- T-2220's ticket-id resolution."""

    # frob:ticket T-2220
    def test_returns_land_commit_for_a_landed_ticket(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ticket whose `land_commit` field is set resolves to that sha."""
        from typani.result import Ok

        class _Fake:
            land_commit = "abc123full"

        # `load_land_commit` imports `frob.tickets._load_one` internally
        # (lazy import, at call time) -- patch the module attribute it
        # will fetch.
        import frob.tickets as tickets_mod

        monkeypatch.setattr(tickets_mod, "_load_one", lambda root, tid: Ok(_Fake()))
        assert verify_lands.load_land_commit("T-9999") == "abc123full"

    # frob:ticket T-2220
    def test_returns_none_for_an_unlanded_ticket(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ticket that exists but was never landed has `land_commit=None`."""
        from typani.result import Ok

        class _Fake:
            land_commit = None

        import frob.tickets as tickets_mod

        monkeypatch.setattr(tickets_mod, "_load_one", lambda root, tid: Ok(_Fake()))
        assert verify_lands.load_land_commit("T-9998") is None

    # frob:ticket T-2220
    def test_returns_missing_for_an_unknown_ticket_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ticket id that resolves to no ticket at all returns a `KeyError`
        instance (never raised), kept distinct from `None`/a real sha."""
        from typani.result import Err

        import frob.tickets as tickets_mod

        monkeypatch.setattr(
            tickets_mod, "_load_one", lambda root, tid: Err("not-found")
        )
        result = verify_lands.load_land_commit("T-0000")
        assert isinstance(result, KeyError)


# frob:ticket T-2220
class TestVerifyLandsMain:
    """`verify_lands.main`."""

    # frob:ticket T-2220
    # frob:tests tests/unit/coordinator_suite/test_verify_lands.py::TestVerifyLandsMain.test_ticket_id_argument_resolves_via_land_commit  # noqa: E501
    def test_ticket_id_argument_resolves_via_land_commit(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Acceptance criterion 3 (must-still-pass) + criterion 4: a SHA
        argument still works unchanged, AND a ticket id argument resolves
        through `load_land_commit` to a sha before the same ancestor check
        every plain sha gets -- this is what makes a `--plan` land
        (unreachable by any commit-subject grep) resolvable by id."""
        monkeypatch.setattr(
            verify_lands, "load_land_commit", lambda tid: "planlandedshafull"
        )
        monkeypatch.setattr(verify_lands, "resolve", lambda sha: f"{sha}-resolved")
        monkeypatch.setattr(verify_lands, "is_ancestor", lambda sha, ref: True)
        monkeypatch.setattr(verify_lands, "subject", lambda sha: "chore: land --plan")
        monkeypatch.setattr(
            sys, "argv", ["verify_lands.py", "T-2211", "realsha", "--ref", "main"]
        )
        assert verify_lands.main() == 0
        out = capsys.readouterr().out
        assert "ON main" in out
        assert "planlandedsh" in out  # sha truncated to 12 chars, same as ON's format

    # frob:ticket T-2220
    # frob:tests tests/unit/coordinator_suite/test_verify_lands.py::TestVerifyLandsMain.test_never_landed_ticket_id_refused_distinguishably_from_a_typo_sha  # noqa: E501
    def test_never_landed_ticket_id_refused_distinguishably_from_a_typo_sha(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Acceptance criterion 5: an unlanded ticket id (`land_commit`
        still `None`) is refused with a message DISTINCT from `UNKNOWN-SHA`
        (a plain typo) -- never conflated, exactly the discipline
        `resolve`/`is_ancestor` already apply to unknown-vs-missing shas."""
        monkeypatch.setattr(verify_lands, "load_land_commit", lambda tid: None)
        monkeypatch.setattr(verify_lands, "resolve", lambda sha: None)
        monkeypatch.setattr(
            sys, "argv", ["verify_lands.py", "T-2299", "typo123", "--ref", "main"]
        )
        assert verify_lands.main() == 1
        out = capsys.readouterr().out
        assert "NOT-LANDED" in out
        assert "T-2299" in out
        assert "UNKNOWN-SHA typo123" in out
        assert "NOT-LANDED" not in out.split("UNKNOWN-SHA")[1]

    def test_distinguishes_unknown_from_missing(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """An unresolvable sha prints UNKNOWN-SHA; a resolvable, non-landed sha
        prints MISSING -- the two must never be conflated (that conflation is
        the exact bug this script exists to prevent)."""

        def fake_resolve(sha: str) -> str | None:
            return None if sha == "typo123" else f"{sha}full"

        monkeypatch.setattr(verify_lands, "resolve", fake_resolve)
        monkeypatch.setattr(verify_lands, "is_ancestor", lambda sha, ref: False)
        monkeypatch.setattr(verify_lands, "subject", lambda sha: "irrelevant")
        monkeypatch.setattr(
            sys, "argv", ["verify_lands.py", "typo123", "realsha", "--ref", "main"]
        )
        assert verify_lands.main() == 1
        out = capsys.readouterr().out
        assert "UNKNOWN-SHA typo123" in out
        assert "MISSING" in out
        assert "realshafull" in out


# frob:ticket T-2775
class TestProbeLandsInFlight:
    """`wait_for_land_slot.probe_lands_in_flight` -- the ONLY place that
    parses the status probe's output; `None` (unmeasured) must never be
    confused with a genuine `0` reading."""

    def test_reads_a_genuine_count(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            wait_for_land_slot.subprocess,
            "run",
            lambda *a, **k: _completed("LANDS IN FLIGHT: 3\n  T-1 pids=1 ...\n"),
        )
        assert wait_for_land_slot.probe_lands_in_flight(["irrelevant"]) == 3

    def test_zero_is_a_real_reading_not_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            wait_for_land_slot.subprocess,
            "run",
            lambda *a, **k: _completed("LANDS IN FLIGHT: 0\n"),
        )
        assert wait_for_land_slot.probe_lands_in_flight(["irrelevant"]) == 0

    def test_nonzero_exit_is_unmeasured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """POSITIVE CONTROL (T-2775): force the status probe to fail --
        the exact case the whole ticket exists to guard. A nonzero exit
        must read as `None`, never as `0`."""
        monkeypatch.setattr(
            wait_for_land_slot.subprocess,
            "run",
            lambda *a, **k: _completed("LANDS IN FLIGHT: 0\n", returncode=1),
        )
        assert wait_for_land_slot.probe_lands_in_flight(["irrelevant"]) is None

    def test_unparseable_output_is_unmeasured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            wait_for_land_slot.subprocess,
            "run",
            lambda *a, **k: _completed("garbage, no such line here\n"),
        )
        assert wait_for_land_slot.probe_lands_in_flight(["irrelevant"]) is None

    def test_probe_timeout_is_unmeasured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*a, **k):
            raise subprocess.TimeoutExpired(cmd="fleet_status", timeout=30)

        monkeypatch.setattr(wait_for_land_slot.subprocess, "run", _raise)
        assert wait_for_land_slot.probe_lands_in_flight(["irrelevant"]) is None

    def test_probe_oserror_is_unmeasured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*a, **k):
            raise OSError("no such file")

        monkeypatch.setattr(wait_for_land_slot.subprocess, "run", _raise)
        assert wait_for_land_slot.probe_lands_in_flight(["irrelevant"]) is None
