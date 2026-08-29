"""Unit tests for `frob.verify._quarantine` (T-1693)."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.verify._quarantine import (
    QuarantinedFinding,
    QuarantineError,
    QuarantineRecord,
    _normalize_finding_path,
    clear_quarantine,
    is_quarantined,
    load_quarantine,
    raise_quarantine,
    retire_unidentifiable_findings,
)


# frob:ticket T-3065
class TestNormalizeFindingPath:
    """`_normalize_finding_path`: the write/lookup-time canonicalization
    that makes an absolute and a relative caller-given path resolve to
    the SAME stored/matched identity (T-3065's own field evidence)."""

    def test_absolute_and_relative_resolve_identical(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::_normalize_finding_path kind="unit"  # noqa: E501
        absolute = str(tmp_path / "src" / "x.py")
        relative = "src/x.py"
        assert _normalize_finding_path(tmp_path, absolute) == _normalize_finding_path(
            tmp_path, relative
        )
        assert _normalize_finding_path(tmp_path, relative) == "src/x.py"

    def test_empty_file_passes_through(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::_normalize_finding_path kind="unit"  # noqa: E501
        # An identity-less finding's `file == ""` must stay exactly `""`
        # -- `_is_unidentifiable` depends on that literal shape, not a
        # resolved cwd-relative string.
        assert _normalize_finding_path(tmp_path, "") == ""

    def test_unresolvable_path_falls_back_verbatim(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::_normalize_finding_path kind="unit"  # noqa: E501
        # A path outside `root` entirely cannot be made root-relative --
        # normalization must return it unchanged rather than raise or
        # silently produce a different string.
        outside = "/definitely/not/under/root/file.py"
        assert _normalize_finding_path(tmp_path, outside) == outside


# frob:ticket T-2207
# frob:ticket T-2246
# frob:waive WIRE001 reason="private test-seed helper (leading underscore, lives under tests/) called only by TestIdentityLessFindingRecovery's own test methods -- there is no production caller to wire it to by design, the T-1592 permanent-test-helper shape docs/modules/gates.md's WIRE001/WIRE002 section documents" permanent="true"  # noqa: E501
def _seed_stuck_store(tmp_path: Path, *, extra: tuple = ()) -> QuarantinedFinding:
    """Persist a quarantine record directly (bypassing `raise_quarantine`,
    which after T-2207's producer fix filters an identity-less finding
    out before it ever reaches disk) -- mirrors an ALREADY-stuck store
    from before the fix landed, the exact case T-2207's consumer half
    (`retire_unidentifiable_findings`) must still be able to repair."""
    identity_less = QuarantinedFinding(rule_id="", file="")
    record = QuarantineRecord(
        raised_at="2026-01-01T00:00:00+00:00",
        batch_commit_shas=("deadbeef",),
        findings=(identity_less, *extra),
    )
    path = tmp_path / ".frob" / "quarantine.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return identity_less


# frob:ticket T-2744
# frob:waive WIRE001 reason="private test-seed helper (leading underscore, lives under tests/) called only by this module's own test methods -- there is no production caller to wire it to by design, the T-1592 permanent-test-helper shape docs/modules/gates.md's WIRE001/WIRE002 section documents" permanent="true"  # noqa: E501
def _seed_real_ticket(tmp_path: Path) -> str:
    """A minimal real ticket, seeded on `tmp_path` -- T-2744's
    `_refuse_if_filed_ticket_unresolvable` check requires every `"filed"`
    disposition's ticket id to actually resolve, so tests exercising the
    normal clear-succeeds path can no longer cite a bare literal like
    `"T-1000"` (that WAS exactly the T-2736 phantom-ticket shape this
    ticket fixes)."""
    from frob.tickets import Origin, TicketKind, new_ticket
    from frob.tickets._models import TicketSpec

    spec = TicketSpec(title="seed", kind=TicketKind.BUG, origin=Origin.AGENT)
    created = new_ticket(tmp_path, spec)
    assert created.is_ok
    return created.danger_ok.id


# frob:ticket T-1693
class TestLoadQuarantine:
    # frob:ticket T-1693
    def test_missing_file_is_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::load_quarantine kind="unit"
        result = load_quarantine(tmp_path)
        assert result.is_ok
        assert result.danger_ok is None

    # frob:ticket T-1693
    def test_corrupt_file_errors(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::load_quarantine kind="unit"
        path = tmp_path / ".frob" / "quarantine.json"
        path.parent.mkdir(parents=True)
        path.write_text("not json{{{", encoding="utf-8")
        result = load_quarantine(tmp_path)
        assert result.is_err
        assert result.danger_err is QuarantineError.StoreCorrupt


# frob:ticket T-1693
class TestIsQuarantined:
    # frob:ticket T-1693
    def test_false_when_never_raised(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::is_quarantined kind="unit"
        result = is_quarantined(tmp_path)
        assert result.is_ok
        assert result.danger_ok is False

    # frob:ticket T-1693
    def test_true_while_raised(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::is_quarantined kind="unit"
        raised = raise_quarantine(
            tmp_path,
            batch_commit_shas=("deadbeef",),
            findings=(QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1),),
        )
        assert raised.is_ok
        result = is_quarantined(tmp_path)
        assert result.is_ok
        assert result.danger_ok is True

    # frob:ticket T-1693
    def test_false_after_clear(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::is_quarantined kind="unit"
        finding = QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1)
        assert raise_quarantine(
            tmp_path, batch_commit_shas=("deadbeef",), findings=(finding,)
        ).is_ok
        real_id = _seed_real_ticket(tmp_path)
        cleared = clear_quarantine(
            tmp_path,
            dispositions={
                (finding.rule_id, finding.file, finding.line): ("filed", real_id)
            },
            reason=f"filed as {real_id}",
            actor="test",
        )
        assert cleared.is_ok
        result = is_quarantined(tmp_path)
        assert result.is_ok
        assert result.danger_ok is False


# frob:ticket T-1693
class TestRaiseQuarantine:
    # frob:ticket T-1693
    def test_raises_and_persists(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        result = raise_quarantine(
            tmp_path,
            batch_commit_shas=("abc123",),
            findings=(QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1),),
        )
        assert result.is_ok
        record = result.danger_ok
        assert record.batch_commit_shas == ("abc123",)
        assert len(record.findings) == 1
        assert record.cleared_at is None

    # frob:ticket T-3065
    def test_normalizes_an_absolute_file_to_root_relative_at_write_time(
        self, tmp_path: Path
    ) -> None:
        """T-3065: whatever path shape the raising caller passes,
        `raise_quarantine` persists the canonical root-relative form --
        the write-time half of the fix (must-fire: an absolute input is
        actually rewritten, not merely tolerated)."""
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        absolute_file = str(tmp_path / "src" / "frob" / "narrative" / "_cli.py")
        result = raise_quarantine(
            tmp_path,
            batch_commit_shas=("abc123",),
            findings=(QuarantinedFinding(rule_id="E501", file=absolute_file),),
        )
        assert result.is_ok
        assert result.danger_ok.findings[0].file == "src/frob/narrative/_cli.py"

    # frob:ticket T-3065
    def test_an_already_relative_file_is_left_as_is(self, tmp_path: Path) -> None:
        """Must-stay-quiet sibling of the above: a finding already
        stored in the canonical relative shape is unchanged by the new
        normalization step."""
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        result = raise_quarantine(
            tmp_path,
            batch_commit_shas=("abc123",),
            findings=(QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1),),
        )
        assert result.is_ok
        assert result.danger_ok.findings[0].file == "src/x.py"

    # frob:ticket T-1693
    def test_empty_findings_refused(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        result = raise_quarantine(tmp_path, batch_commit_shas=("abc123",), findings=())
        assert result.is_err
        assert result.danger_err is QuarantineError.EmptyFindings

    # frob:ticket T-1693
    def test_survives_a_fresh_load_reflecting_a_restart(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        # Durability across a worker restart: a fresh `load_quarantine`
        # call (simulating a brand-new process) must see the same raised
        # state, never an in-memory-only flag.
        assert raise_quarantine(
            tmp_path,
            batch_commit_shas=("abc123",),
            findings=(QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1),),
        ).is_ok
        reloaded = load_quarantine(tmp_path)
        assert reloaded.is_ok
        assert reloaded.danger_ok is not None
        assert reloaded.danger_ok.cleared_at is None

    # frob:ticket T-2132
    def test_a_naturally_unattributable_finding_alone_does_not_raise(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        # TICK004 (ticket-rot: "T-#### has sat queued for Nd") is a
        # statement about ELAPSED TIME, not about any commit's diff --
        # commit=None here is the truth, not a failed attribution. A
        # batch whose only finding is TICK004 must not switch deferred
        # landing off repo-wide (T-2132): no land can ever "fix" a clock.
        result = raise_quarantine(
            tmp_path,
            batch_commit_shas=(),
            findings=(
                QuarantinedFinding(rule_id="TICK004", file="tickets.md", line=0),
            ),
        )
        assert result.is_err
        assert result.danger_err is QuarantineError.EmptyFindings
        assert is_quarantined(tmp_path).danger_ok is False

    # frob:ticket T-2132
    def test_an_unattributed_code_finding_still_raises(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        # Contrast case: a real code finding that attribution genuinely
        # FAILED to pin to a commit (`commit_sha=None` because the
        # reachability walk found zero or >1 candidates, not because the
        # rule is inherently clock-driven) must still raise -- T-1686's
        # prior-art incident was a sweep that treated UNATTRIBUTED code
        # findings as non-regressions, which is the opposite mistake.
        result = raise_quarantine(
            tmp_path,
            batch_commit_shas=("abc123",),
            findings=(QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1),),
        )
        assert result.is_ok
        assert is_quarantined(tmp_path).danger_ok is True

    # frob:ticket T-2132
    def test_a_mixed_batch_raises_with_only_the_attributable_finding_kept(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        # A batch with BOTH a naturally-unattributable finding and a real
        # code finding still raises (the code finding is real), but the
        # persisted record drops the naturally-unattributable one -- it
        # was never something a filed ticket against a commit could fix.
        result = raise_quarantine(
            tmp_path,
            batch_commit_shas=("abc123",),
            findings=(
                QuarantinedFinding(rule_id="TICK004", file="tickets.md", line=0),
                QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1),
            ),
        )
        assert result.is_ok
        record = result.danger_ok
        assert len(record.findings) == 1
        assert record.findings[0].rule_id == "TEST001"

    # frob:ticket T-3025
    def test_a_trivial_unattributed_ruff_finding_alone_does_not_raise(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        # MUST-STAY-QUIET fixture, incident shape 1/3: I001 (import sort),
        # unattributed -- ruff's own `--fix` resolves this with zero
        # semantic content, and there is no commit/ticket to attribute a
        # dispose to. Must not disable fleet-wide deferred landing.
        result = raise_quarantine(
            tmp_path,
            batch_commit_shas=(),
            findings=(
                QuarantinedFinding(
                    rule_id="I001", file="tests/unit/verify/test_x.py", line=1
                ),
            ),
        )
        assert result.is_err
        assert result.danger_err is QuarantineError.EmptyFindings
        assert is_quarantined(tmp_path).danger_ok is False

    # frob:ticket T-3025
    def test_a_trivial_unattributed_unused_import_finding_does_not_raise(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        # MUST-STAY-QUIET fixture, incident shape 2/3: F401 (unused
        # import), unattributed.
        result = raise_quarantine(
            tmp_path,
            batch_commit_shas=(),
            findings=(QuarantinedFinding(rule_id="F401", file="src/x.py", line=3),),
        )
        assert result.is_err
        assert result.danger_err is QuarantineError.EmptyFindings
        assert is_quarantined(tmp_path).danger_ok is False

    # frob:ticket T-3025
    def test_an_unattributed_frob_gate_autofix_rule_is_deliberately_not_exempt(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        # BOUNDARY fixture: E501 has a real frob Tier-A handler
        # (`frob.gates._fix_engine.TIER_A_HANDLERS`), but T-3025's own
        # exemption is deliberately narrowed to ruff codes only
        # (`_RUFF_DETERMINISTIC_AUTOFIX_RULES`) to avoid a new
        # `frob.verify` -> `frob.gates` architectural dependency --
        # this must still raise, unlike I001/F401 above.
        result = raise_quarantine(
            tmp_path,
            batch_commit_shas=(),
            findings=(QuarantinedFinding(rule_id="E501", file="src/y.py", line=9),),
        )
        assert result.is_ok
        assert is_quarantined(tmp_path).danger_ok is True

    # frob:ticket T-3025
    def test_an_attributed_trivial_finding_still_raises(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        # MUST-FIRE fixture 1/2: the SAME trivial rule (I001), but this
        # time attributed to a real commit -- a real commit/ticket
        # already names it, so "the fix is easy" does not exempt it.
        # Do not solve T-3025 by never raising.
        result = raise_quarantine(
            tmp_path,
            batch_commit_shas=("abc123",),
            findings=(
                QuarantinedFinding(
                    rule_id="I001",
                    file="tests/unit/verify/test_x.py",
                    line=1,
                    commit_sha="abc123",
                    ticket_id="T-9999",
                ),
            ),
        )
        assert result.is_ok
        assert is_quarantined(tmp_path).danger_ok is True

    # frob:ticket T-3025
    def test_an_unattributed_non_trivial_finding_still_raises(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        # MUST-FIRE fixture 2/2: unattributed, but NOT a proven
        # deterministic-autofix rule (a real test failure) -- genuine
        # breakage with no known cause must still stop the fleet. This is
        # the exact case T-1686/T-2132 already require and T-3025 must
        # never weaken.
        result = raise_quarantine(
            tmp_path,
            batch_commit_shas=("abc123",),
            findings=(QuarantinedFinding(rule_id="TEST001", file="src/z.py", line=4),),
        )
        assert result.is_ok
        assert is_quarantined(tmp_path).danger_ok is True

    # frob:ticket T-3025
    def test_a_mixed_batch_drops_only_the_trivial_unattributed_finding(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        # A batch with a trivial-unattributed finding alongside a real
        # unattributed finding still raises (the real one is genuine),
        # but the persisted record drops the trivial one -- it is still
        # filed as an ordinary regression ticket by the caller's own
        # unaffected filing path, just not sent to the dispose queue.
        result = raise_quarantine(
            tmp_path,
            batch_commit_shas=("abc123",),
            findings=(
                QuarantinedFinding(rule_id="I001", file="tests/x.py", line=1),
                QuarantinedFinding(rule_id="TEST001", file="src/z.py", line=4),
            ),
        )
        assert result.is_ok
        record = result.danger_ok
        assert len(record.findings) == 1
        assert record.findings[0].rule_id == "TEST001"


# frob:ticket T-1693
# frob:ticket T-2744
class TestClearQuarantine:
    # frob:ticket T-1693
    def test_refuses_when_not_raised(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::clear_quarantine kind="unit"
        result = clear_quarantine(
            tmp_path, dispositions={}, reason="nothing to clear", actor="test"
        )
        assert result.is_err
        assert result.danger_err is QuarantineError.NotQuarantined

    # frob:ticket T-2744
    def test_refuses_when_filed_ticket_does_not_resolve(self, tmp_path: Path) -> None:
        """T-2744: the T-2736 incident, reproduced directly at
        `clear_quarantine`'s own boundary -- a `"filed"` disposition
        naming a ticket id that does not exist on `root` must refuse the
        whole clear, loudly, rather than release the finding against a
        phantom home."""
        # frob:tests src/frob/verify/_quarantine.py::clear_quarantine kind="unit"
        finding = QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1)
        assert raise_quarantine(
            tmp_path, batch_commit_shas=("abc123",), findings=(finding,)
        ).is_ok
        result = clear_quarantine(
            tmp_path,
            dispositions={
                (finding.rule_id, finding.file, finding.line): ("filed", "T-2736")
            },
            reason="auto-filed by rapid sweep as T-2736",
            actor="test",
        )
        assert result.is_err
        assert result.danger_err is QuarantineError.UnresolvableFiledTicket
        # A refused clear must NOT have silently cleared it.
        assert is_quarantined(tmp_path).danger_ok is True

    # frob:ticket T-1693
    def test_refuses_when_a_finding_is_undisposed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::clear_quarantine kind="unit"
        assert raise_quarantine(
            tmp_path,
            batch_commit_shas=("abc123",),
            findings=(QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1),),
        ).is_ok
        result = clear_quarantine(
            tmp_path, dispositions={}, reason="tried anyway", actor="test"
        )
        assert result.is_err
        assert result.danger_err is QuarantineError.FindingsNotDisposed
        # A refused clear must NOT have silently cleared it.
        assert is_quarantined(tmp_path).danger_ok is True

    # frob:ticket T-1693
    def test_clears_when_every_finding_disposed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::clear_quarantine kind="unit"
        a = QuarantinedFinding(rule_id="TEST001", file="src/a.py", line=1)
        b = QuarantinedFinding(rule_id="TEST002", file="src/b.py", line=2)
        assert raise_quarantine(
            tmp_path, batch_commit_shas=("abc123",), findings=(a, b)
        ).is_ok
        real_id = _seed_real_ticket(tmp_path)
        result = clear_quarantine(
            tmp_path,
            dispositions={
                (a.rule_id, a.file, a.line): ("filed", real_id),
                (b.rule_id, b.file, b.line): ("dismissed", "false positive"),
            },
            reason="both disposed",
            actor="test",
        )
        assert result.is_ok
        record = result.danger_ok
        assert record.cleared_at is not None
        assert record.cleared_reason == "both disposed"
        by_rule = {f.rule_id: f for f in record.findings}
        assert by_rule["TEST001"].disposition == "filed"
        assert by_rule["TEST001"].disposition_ref == real_id
        assert by_rule["TEST002"].disposition == "dismissed"
        assert by_rule["TEST002"].disposition_reason == "false positive"

    # frob:ticket T-2312
    def test_path_shape_mismatch_is_diagnosed_not_a_bare_refusal(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::clear_quarantine kind="unit"
        """T-2312 acceptance [3]: the quarantine store can hold an
        ABSOLUTE-path finding identity while an operator's `--file-ticket`
        key uses a RELATIVE one (or vice versa) -- `_dispose_one` matches
        by literal string equality, so this fails identically to a
        genuinely wrong key. `clear_quarantine` must still refuse (never
        silently accept a shape-mismatched key as a match), but it must
        ALSO log a hint naming the path-shape mismatch specifically,
        rather than leaving the operator with only a bare
        `FindingsNotDisposed`."""
        stored_relative = "src/x.py"
        absolute_given = str((tmp_path / "src" / "x.py").resolve())
        assert raise_quarantine(
            tmp_path,
            batch_commit_shas=("abc123",),
            findings=(
                QuarantinedFinding(rule_id="TEST001", file=stored_relative, line=1),
            ),
        ).is_ok
        real_id = _seed_real_ticket(tmp_path)
        with caplog.at_level("ERROR"):
            result = clear_quarantine(
                tmp_path,
                dispositions={("TEST001", absolute_given, 1): ("filed", real_id)},
                reason="tried with the wrong path shape",
                actor="test",
            )
        assert result.is_err
        assert result.danger_err is QuarantineError.FindingsNotDisposed
        assert is_quarantined(tmp_path).danger_ok is True
        assert any("PATH SHAPE" in record.message for record in caplog.records), (
            "a path-shape mismatch must be named as such, not left as a bare refusal"
        )

    # frob:ticket T-1693
    def test_green_verification_alone_never_clears(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::clear_quarantine kind="unit"
        # The single most important property: `is_quarantined` staying
        # True is not affected by anything OTHER than an explicit
        # `clear_quarantine` call disposing every finding -- there is no
        # "record a green run" entrypoint in this module at all, so a
        # green verification structurally cannot clear it. This test
        # documents that absence by re-checking `is_quarantined` after
        # simply re-loading the store repeatedly (simulating however many
        # subsequent green batch runs happened) with no clear call.
        assert raise_quarantine(
            tmp_path,
            batch_commit_shas=("abc123",),
            findings=(QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1),),
        ).is_ok
        for _ in range(5):
            assert is_quarantined(tmp_path).danger_ok is True


# frob:ticket T-2207
class TestIdentityLessFindingRecovery:
    # frob:ticket T-2207
    def test_cli_addressing_can_never_key_an_identity_less_finding(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::clear_quarantine kind="unit"
        # Live incident (T-2207): a stuck store holding a record with
        # every identity field empty. The CLI's own `RULE:FILE:LINE`
        # addressing (`frob.app.verify_runner._parse_finding_arg`)
        # structurally cannot key to it -- `--dismiss '::=<reason>'`
        # always parses to `None` (malformed) because an empty `file` is
        # always rejected, never `("", "", None)`. Plain `clear_quarantine`
        # with no way to build the right disposition key correctly
        # refuses -- this documents WHY no CLI invocation can ever clear
        # this store, not a bug in `clear_quarantine` itself.
        from frob.app.verify_runner import _parse_finding_arg

        assert _parse_finding_arg("::") is None

        _seed_stuck_store(tmp_path)
        result = clear_quarantine(
            tmp_path, dispositions={}, reason="tried anyway", actor="test"
        )
        assert result.is_err
        assert result.danger_err is QuarantineError.FindingsNotDisposed
        assert is_quarantined(tmp_path).danger_ok is True

    # frob:ticket T-2207
    def test_retire_unidentifiable_findings_recovers_a_stuck_store(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::retire_unidentifiable_findings kind="unit"  # noqa: E501
        _seed_stuck_store(tmp_path)
        result = retire_unidentifiable_findings(
            tmp_path, reason="T-2207 recovery", actor="test"
        )
        assert result.is_ok
        record = result.danger_ok
        assert record.cleared_at is not None
        assert record.findings[0].disposition == "dismissed"
        assert record.findings[0].disposition_reason == "T-2207 recovery"
        assert is_quarantined(tmp_path).danger_ok is False

    # frob:ticket T-2207
    def test_retire_unidentifiable_findings_still_blocks_on_a_well_formed_sibling(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::retire_unidentifiable_findings kind="unit"  # noqa: E501
        # MUST-STILL-PASS control: retiring the identity-less record must
        # NOT clear quarantine while a real, well-formed finding is still
        # undisposed -- otherwise this "fix" would just be
        # clear_quarantine skipping findings under a new name, reopening
        # the hole T-1693 closed.
        real = QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1)
        _seed_stuck_store(tmp_path, extra=(real,))

        result = retire_unidentifiable_findings(
            tmp_path, reason="T-2207 recovery", actor="test"
        )
        assert result.is_err
        assert result.danger_err is QuarantineError.FindingsNotDisposed
        assert is_quarantined(tmp_path).danger_ok is True

        # The identity-less record IS retired even though the overall
        # clear is refused -- confirmed by disposing the real one next
        # via the normal path, which now clears cleanly.
        real_id = _seed_real_ticket(tmp_path)
        followup = clear_quarantine(
            tmp_path,
            dispositions={(real.rule_id, real.file, real.line): ("filed", real_id)},
            reason="real finding filed",
            actor="test",
        )
        assert followup.is_ok
        assert is_quarantined(tmp_path).danger_ok is False

    # frob:ticket T-2207
    def test_retire_unidentifiable_findings_refuses_when_none_present(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::retire_unidentifiable_findings kind="unit"  # noqa: E501
        real = QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1)
        assert raise_quarantine(
            tmp_path, batch_commit_shas=("deadbeef",), findings=(real,)
        ).is_ok
        result = retire_unidentifiable_findings(
            tmp_path, reason="nothing to retire", actor="test"
        )
        assert result.is_err
        assert result.danger_err is QuarantineError.NoUnidentifiableFindings

    # frob:ticket T-2207
    def test_retire_unidentifiable_findings_refuses_when_not_raised(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::retire_unidentifiable_findings kind="unit"  # noqa: E501
        result = retire_unidentifiable_findings(
            tmp_path, reason="nothing raised", actor="test"
        )
        assert result.is_err
        assert result.danger_err is QuarantineError.NotQuarantined

    # frob:ticket T-2207
    def test_raise_quarantine_drops_identity_less_findings_at_write_time(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        # Producer-side half of the fix: a batch with a real finding AND
        # an identity-less one persists only the real finding -- an
        # identity-less finding is never actionable, so it is dropped
        # before it ever reaches disk, not persisted then discovered
        # unrecoverable later.
        identity_less = QuarantinedFinding(rule_id="", file="")
        real = QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1)
        result = raise_quarantine(
            tmp_path, batch_commit_shas=("abc123",), findings=(identity_less, real)
        )
        assert result.is_ok
        record = result.danger_ok
        assert len(record.findings) == 1
        assert record.findings[0].rule_id == "TEST001"

    # frob:ticket T-2207
    def test_raise_quarantine_refuses_when_only_identity_less_findings_given(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        identity_less = QuarantinedFinding(rule_id="", file="")
        result = raise_quarantine(
            tmp_path, batch_commit_shas=("abc123",), findings=(identity_less,)
        )
        assert result.is_err
        assert result.danger_err is QuarantineError.EmptyFindings
        assert is_quarantined(tmp_path).danger_ok is False
