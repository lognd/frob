"""T-3847: `_verify_ids_passing`'s evidence-verification buckets no longer
stop at python/rust -- an id that resolves against neither is tried
against every OTHER collector `frob.testing.LANGUAGE_COLLECTORS`
registers (cpp/kotlin/ts today), and whatever STILL matches nothing gets
a loud, typed `UNMEASURED` outcome naming the id and every language
tried, rather than silently vanishing from the result (the defect this
ticket fixes)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typani.result import Err, Ok

from frob.app import ticket_runner
from frob.app.ticket_runner._verify import VerifyStatus
from frob.testing import CollectedTests, TestingError


class _FakeRunReport:
    """A minimal `run_selected` return stand-in carrying only `.ok`."""

    def __init__(self, *, ok: bool) -> None:
        self.ok = ok


# frob:waive WIRE001 reason="test-fixture builder for this module's own tests only, \
# same shape/precedent as tests/test_tickets_migration.py's _git_init-family WIRE001 \
# waivers -- no production caller to wire it to by design" permanent="true"
def _fake_run_selected_always_ok(selection, runners, root):  # noqa: ANN001, ANN202
    """`run_selected` stand-in: every batch it is handed reports green,
    without spawning anything real."""
    return Ok(_FakeRunReport(ok=True))


class TestUnbucketedIdsAreLoud:
    """T-3847 MUST-FIRE: an id matching no collector is refused, naming
    the id -- never silently absent from `outcomes`."""

    def test_id_matching_no_collector_is_a_named_unmeasured_refusal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_verify.py::_verify_unbucketed_ids
        import frob.testing as _testing_mod

        for language in ("cpp", "kotlin", "ts"):
            monkeypatch.setitem(
                _testing_mod.LANGUAGE_COLLECTORS,
                language,
                lambda root: Ok(CollectedTests(node_ids=frozenset())),
            )
        outcomes = ticket_runner._verify_unbucketed_ids(
            tmp_path, ("mystery.spec::does a thing",), tried=("python", "rust"), runners=()
        )
        assert set(outcomes) == {"mystery.spec::does a thing"}
        outcome = outcomes["mystery.spec::does a thing"]
        assert outcome.status is VerifyStatus.UNMEASURED
        assert outcome.reason is not None
        assert "mystery.spec::does a thing" in outcome.reason
        for language in ("python", "rust", "cpp", "kotlin", "ts"):
            assert language in outcome.reason

    def test_id_matching_a_registered_non_python_rust_collector_verifies(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_verify.py::_verify_unbucketed_ids
        import frob.testing as _testing_mod

        cpp_id = "MySuite.MyCase"
        monkeypatch.setitem(
            _testing_mod.LANGUAGE_COLLECTORS,
            "cpp",
            lambda root: Ok(CollectedTests(node_ids=frozenset({cpp_id}))),
        )
        for language in ("kotlin", "ts"):
            monkeypatch.setitem(
                _testing_mod.LANGUAGE_COLLECTORS,
                language,
                lambda root: Ok(CollectedTests(node_ids=frozenset())),
            )
        monkeypatch.setattr(
            _testing_mod, "run_selected", _fake_run_selected_always_ok
        )
        outcomes = ticket_runner._verify_unbucketed_ids(
            tmp_path, (cpp_id,), tried=("python", "rust"), runners=()
        )
        assert outcomes[cpp_id].status is VerifyStatus.PASSED

    def test_collector_error_is_tried_but_never_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_verify.py::_verify_unbucketed_ids
        import frob.testing as _testing_mod

        monkeypatch.setitem(
            _testing_mod.LANGUAGE_COLLECTORS,
            "cpp",
            lambda root: Err(TestingError.SpawnFailed),
        )
        for language in ("kotlin", "ts"):
            monkeypatch.setitem(
                _testing_mod.LANGUAGE_COLLECTORS,
                language,
                lambda root: Ok(CollectedTests(node_ids=frozenset())),
            )
        outcomes = ticket_runner._verify_unbucketed_ids(
            tmp_path, ("some.id",), tried=("python", "rust"), runners=()
        )
        assert outcomes["some.id"].status is VerifyStatus.UNMEASURED
        reason = outcomes["some.id"].reason
        assert reason is not None
        assert "cpp" in reason


class TestVerifyIdsPassingFallsThroughToOtherCollectors:
    """T-3847: `_verify_ids_passing` itself (not just the helper) must
    reach the unbucketed path for an id that matches neither the caller's
    python nor rust collected sets."""

    def test_id_unmatched_by_python_and_rust_still_gets_an_outcome(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_verify.py::_verify_ids_passing
        import frob.testing as _testing_mod

        for language in ("cpp", "kotlin", "ts"):
            monkeypatch.setitem(
                _testing_mod.LANGUAGE_COLLECTORS,
                language,
                lambda root: Ok(CollectedTests(node_ids=frozenset())),
            )
        outcomes = ticket_runner._verify_ids_passing(
            tmp_path,
            ("nothing/knows/this::id",),
            frozenset(),
            frozenset(),
            (),
        )
        assert set(outcomes) == {"nothing/knows/this::id"}
        assert outcomes["nothing/knows/this::id"].status is VerifyStatus.UNMEASURED

    def test_python_and_rust_matches_are_unaffected_by_this_change(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_verify.py::_verify_ids_passing
        import frob.testing as _testing_mod

        monkeypatch.setattr(
            _testing_mod, "run_selected", _fake_run_selected_always_ok
        )
        outcomes = ticket_runner._verify_ids_passing(
            tmp_path,
            ("tests/x.py::a",),
            frozenset({"tests/x.py::a"}),
            frozenset(),
            (),
        )
        assert outcomes["tests/x.py::a"].status is VerifyStatus.PASSED


class TestUnbucketedIdsSkipAlreadyTriedLanguages:
    """T-3847 mutation-kill: `_verify_unbucketed_ids` must never re-collect
    a language already in `tried` (its collector was already consulted by
    the caller) -- only OTHER registered languages are worth the extra
    collection call."""

    def test_already_tried_language_collector_is_never_invoked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_verify.py::_verify_unbucketed_ids
        import frob.testing as _testing_mod

        calls: list[str] = []

        def _tracking_collector(language):  # noqa: ANN001, ANN202
            def fn(root):  # noqa: ANN001, ANN202
                calls.append(language)
                return Ok(CollectedTests(node_ids=frozenset()))

            return fn

        monkeypatch.setitem(
            _testing_mod.LANGUAGE_COLLECTORS, "python", _tracking_collector("python")
        )
        monkeypatch.setitem(
            _testing_mod.LANGUAGE_COLLECTORS, "cpp", _tracking_collector("cpp")
        )
        for language in ("rust", "kotlin", "ts"):
            monkeypatch.setitem(
                _testing_mod.LANGUAGE_COLLECTORS,
                language,
                _tracking_collector(language),
            )
        ticket_runner._verify_unbucketed_ids(
            tmp_path, ("some.id",), tried=("python",), runners=()
        )
        assert "python" not in calls
        assert "cpp" in calls
