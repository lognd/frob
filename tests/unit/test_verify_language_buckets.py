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


class TestOtherLanguageCollectedIds:
    """T-3925: `_other_language_collected_ids` is the BINDING half of the
    registry wiring T-3847 left incomplete -- callers that build a
    `collected` set for `add_evidence`/`replace_evidence`/land's D-05
    post-merge re-check union this in alongside python/rust so a
    non-python/rust id (vitest, gtest, junit, ...) resolves instead of
    being rejected as unknown evidence (F-134)."""

    def test_unions_every_non_excluded_registered_language(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_verify.py::_other_language_collected_ids  # noqa: E501
        # frob:waive FMT001 reason="single-line frob:tests directive naming a long \
        # symref -- already at frob fmt's own canonical form (verified: `frob format \
        # --directives` reports it unchanged), same unwrappable shape as this repo's \
        # other pre-existing long frob:tests lines"
        import frob.testing as _testing_mod

        monkeypatch.setitem(
            _testing_mod.LANGUAGE_COLLECTORS,
            "cpp",
            lambda root: Ok(CollectedTests(node_ids=frozenset({"Suite.Case"}))),
        )
        monkeypatch.setitem(
            _testing_mod.LANGUAGE_COLLECTORS,
            "kotlin",
            lambda root: Ok(CollectedTests(node_ids=frozenset({"pkg.Foo#bar"}))),
        )
        monkeypatch.setitem(
            _testing_mod.LANGUAGE_COLLECTORS,
            "ts",
            lambda root: Ok(CollectedTests(node_ids=frozenset({"x.test.ts::it"}))),
        )
        ids = ticket_runner._other_language_collected_ids(
            tmp_path, exclude=frozenset({"python", "rust"})
        )
        assert ids == {"Suite.Case", "pkg.Foo#bar", "x.test.ts::it"}

    def test_excluded_languages_are_never_collected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_verify.py::_other_language_collected_ids  # noqa: E501
        # frob:waive FMT001 reason="single-line frob:tests directive naming a long \
        # symref -- already at frob fmt's own canonical form (verified: `frob format \
        # --directives` reports it unchanged), same unwrappable shape as this repo's \
        # other pre-existing long frob:tests lines"
        import frob.testing as _testing_mod

        def _boom(root):  # noqa: ANN001, ANN202
            raise AssertionError("excluded language must not be collected")

        monkeypatch.setitem(_testing_mod.LANGUAGE_COLLECTORS, "python", _boom)
        monkeypatch.setitem(_testing_mod.LANGUAGE_COLLECTORS, "rust", _boom)
        for language in ("cpp", "kotlin", "ts"):
            monkeypatch.setitem(
                _testing_mod.LANGUAGE_COLLECTORS,
                language,
                lambda root: Ok(CollectedTests(node_ids=frozenset())),
            )
        ticket_runner._other_language_collected_ids(
            tmp_path, exclude=frozenset({"python", "rust"})
        )

    def test_collector_error_degrades_to_empty_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_verify.py::_other_language_collected_ids  # noqa: E501
        # frob:waive FMT001 reason="single-line frob:tests directive naming a long \
        # symref -- already at frob fmt's own canonical form (verified: `frob format \
        # --directives` reports it unchanged), same unwrappable shape as this repo's \
        # other pre-existing long frob:tests lines"
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
        ids = ticket_runner._other_language_collected_ids(
            tmp_path, exclude=frozenset({"python", "rust"})
        )
        assert ids == frozenset()


# frob:ticket T-3937
# frob:tests tests/unit/test_verify_language_buckets.py::TestBindingResolvesRealNonPythonRustCollectors.test_must_fire_real_vitest_node_id_binds_via_apply_evidence  # noqa: E501
# frob:waive FMT001 reason="single-line frob:tests directive naming a long test node \
# id -- already at frob fmt's own canonical form (verified: `frob format --directives` \
# reports it unchanged), same unwrappable shape as this repo's other pre-existing long \
# frob:tests lines"
# frob:tests tests/unit/test_verify_language_buckets.py::TestBindingResolvesRealNonPythonRustCollectors.test_must_stay_quiet_nonexistent_ts_id_is_still_rejected  # noqa: E501
# frob:waive FMT001 reason="single-line frob:tests directive naming a long test node \
# id -- already at frob fmt's own canonical form (verified: `frob format --directives` \
# reports it unchanged), same unwrappable shape as this repo's other pre-existing long \
# frob:tests lines"
# frob:tests tests/unit/test_verify_language_buckets.py::TestBindingResolvesRealNonPythonRustCollectors.test_real_cpp_node_id_binds_via_apply_evidence  # noqa: E501
# frob:waive FMT001 reason="single-line frob:tests directive naming a long test node \
# id -- already at frob fmt's own canonical form (verified: `frob format --directives` \
# reports it unchanged), same unwrappable shape as this repo's other pre-existing long \
# frob:tests lines"
class TestBindingResolvesRealNonPythonRustCollectors:
    """T-3937 (F-172): `_other_language_collected_ids` (T-3925) fixed the
    BINDING path in code, but every existing test for it (see
    `TestOtherLanguageCollectedIds` above) monkeypatches
    `LANGUAGE_COLLECTORS` entries with bare lambdas -- exactly the shape
    that cannot tell a genuinely-working resolver from one that would
    accept anything. These three fixtures instead drive the REAL
    `collect_ts_tests`/`collect_cpp_tests` collectors (real file
    walking, real content-hash cache validation, real JUnit XML parsing)
    through the actual CLI binding entrypoint, `_apply_evidence` --
    reproducing the consumer's exact reported scenario: an id taken
    verbatim from a just-refreshed `.frob/vitest-collect.json` must bind,
    a nonexistent one must not, and the same holds for a second
    non-python/rust language (cpp) sharing the identical defect.

    `_verify_ids_passing` is monkeypatched to report every id it is asked
    about as passing -- this ticket fixes BINDING (does the id resolve at
    all), not execution (T-3933 tracks that vitest/cpp runs are not
    yet actually spawned end to end); patching the pass-check keeps these
    fixtures from conflating the two."""

    @staticmethod
    def _patch_passing_and_python(monkeypatch: pytest.MonkeyPatch) -> None:
        """Shared hermetic setup: no real python collection or test run,
        so only the non-python/rust collector under test is real."""
        import frob.app.ticket_runner as runner_mod
        from frob.app.ticket_runner._verify import VerifyOutcome as _VerifyOutcome
        from frob.app.ticket_runner._verify import VerifyStatus as _VerifyStatus

        monkeypatch.setattr(
            "frob.testing.collect_python_tests",
            lambda root: Ok(CollectedTests(node_ids=frozenset())),
        )
        monkeypatch.setattr(
            runner_mod,
            "_verify_ids_passing",
            lambda root, node_ids, python_collected, rust_collected, runners: {
                n: _VerifyOutcome(status=_VerifyStatus.PASSED) for n in node_ids
            },
        )

    @staticmethod
    def _seed_real_vitest_project(tmp_path: Path, *, node_id_name: str) -> str:
        """Writes a genuine vitest project (`package.json` declaring the
        `vitest` devDependency plus a real `.test.ts` file) and then seeds
        `.frob/vitest-collect.json` with the key `collect_ts_tests`'s own
        `_ts_content_key` computes for those exact files -- i.e. exactly
        the cache state `frob test` leaves behind after a real collection,
        never a hand-invented key. Returns the resulting node id."""
        import json as _json

        from frob.testing._collect_shared import _TS_CACHE_REL, _store_cache
        from frob.testing._collect_ts import _find_vitest_projects, _ts_content_key

        pkg_dir = tmp_path / "web"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "package.json").write_text(
            _json.dumps({"name": "web", "devDependencies": {"vitest": "^2.0.0"}}),
            encoding="utf-8",
        )
        test_file = pkg_dir / "greet.test.ts"
        test_file.write_text(
            f'import {{ it }} from "vitest";\nit("{node_id_name}", () => {{}});\n',
            encoding="utf-8",
        )

        projects = _find_vitest_projects(tmp_path)
        assert projects == [pkg_dir]
        key = _ts_content_key(tmp_path, projects)
        node_id = f"web/greet.test.ts::{node_id_name}"
        _store_cache(tmp_path / _TS_CACHE_REL, key, frozenset({node_id}))
        return node_id

    def test_must_fire_real_vitest_node_id_binds_via_apply_evidence(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-FIRE: a genuine vitest node id present in
        `.frob/vitest-collect.json` (cache-seeded via the collector's own
        real content-key function, not fabricated) binds successfully."""
        from frob.app.config import AppConfig
        from frob.app.ticket_runner import _apply_evidence, _new

        node_id = self._seed_real_vitest_project(tmp_path, node_id_name="greets")
        self._patch_passing_and_python(monkeypatch)

        cfg = AppConfig(
            ticket_command="new",
            ticket_title="wire vitest evidence",
            ticket_kind="feature",
            ticket_path=tmp_path,
        )
        _new(tmp_path, cfg)

        result = _apply_evidence(tmp_path, "T-0001", [node_id])
        assert result.is_ok, result.err
        assert result.danger_ok.evidence == (node_id,)

    def test_must_stay_quiet_nonexistent_ts_id_is_still_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-STAY-QUIET: alongside a real, collected vitest project, an
        id that was never collected is still rejected as UnknownEvidence
        -- proving the resolver actually validates against the real
        collected set rather than accepting anything non-python/rust."""
        from frob.app.config import AppConfig
        from frob.app.ticket_runner import _apply_evidence, _new
        from frob.tickets import TicketError

        self._seed_real_vitest_project(tmp_path, node_id_name="greets")
        self._patch_passing_and_python(monkeypatch)

        cfg = AppConfig(
            ticket_command="new",
            ticket_title="wire vitest evidence",
            ticket_kind="feature",
            ticket_path=tmp_path,
        )
        _new(tmp_path, cfg)

        bogus_id = "web/greet.test.ts::this test does not exist"
        result = _apply_evidence(tmp_path, "T-0001", [bogus_id])
        assert result.is_err
        assert result.danger_err is TicketError.UnknownEvidence

    def test_real_cpp_node_id_binds_via_apply_evidence(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """THIRD FIXTURE: a real cpp/ctest node id, cache-seeded via
        `collect_cpp_tests`'s own real `_ctest_content_key` (same
        cache-hit shortcut used for vitest above -- no `ctest` binary
        needs to be on PATH for this fixture, exactly as a repo with no
        C++ toolchain but a stale-but-valid cache would hit), binds via
        the same `_apply_evidence` entrypoint -- proving the fix is not
        vitest-specific. The ctest test name is deliberately dot-free
        (`GreetsWorks`, not `Suite.Case`) so this fixture is not also
        exercising `normalize_evidence_separator`'s separate, pre-existing
        dot-rewrite behavior -- out of this ticket's scope."""
        from frob.app.config import AppConfig
        from frob.app.ticket_runner import _apply_evidence, _new
        from frob.testing._collect_cpp import _ctest_content_key
        from frob.testing._collect_shared import _CTEST_CACHE_REL, _store_cache

        project_dir = tmp_path / "native"
        project_dir.mkdir()
        (project_dir / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.16)\nproject(native)\n",
            encoding="utf-8",
        )
        build_dir = project_dir / "build"
        build_dir.mkdir()
        (build_dir / "CTestTestfile.cmake").write_text(
            'add_test(GreetsWorks "native/build/greets_test")\n', encoding="utf-8"
        )

        build_dirs = [build_dir]
        key = _ctest_content_key(tmp_path, build_dirs)
        rel_build = build_dir.relative_to(tmp_path).as_posix()
        node_id = f"{rel_build}::GreetsWorks"
        _store_cache(tmp_path / _CTEST_CACHE_REL, key, frozenset({node_id}))

        self._patch_passing_and_python(monkeypatch)

        cfg = AppConfig(
            ticket_command="new",
            ticket_title="wire cpp evidence",
            ticket_kind="feature",
            ticket_path=tmp_path,
        )
        _new(tmp_path, cfg)

        result = _apply_evidence(tmp_path, "T-0001", [node_id])
        assert result.is_ok, result.err
        assert result.danger_ok.evidence == (node_id,)
