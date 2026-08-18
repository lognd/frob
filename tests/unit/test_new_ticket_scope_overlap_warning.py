"""T-2257: `frob ticket new` does not warn when another QUEUED/IN-PROGRESS
ticket already declares scope over the same file(s) -- four tickets piled
onto `scripts/fleet_status.py` in one real session because nothing ever
told the filer. `_scope_overlap_warnings` computes the overlap on RESOLVED
paths (never scope text) so a glob-vs-file overlap is caught, is advisory
only (filing always succeeds), and excludes terminal (done/dropped)
tickets since their old scope is history, not a live claim."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner._new import _new


# frob:ticket T-2257
def _write(path: Path, text: str) -> None:
    """Create `path`'s parent dirs and write `text` -- test helper only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# frob:ticket T-2257
# frob:waive WIRE001 follow_up="T-2057" reason="private test-fixture helper used only \
# by this file's own tests, same posture as tests/unit/conftest.py's and \
# test_type_name_only_regression_t1957.py's own identical WIRE001 waivers for a \
# per-file test helper -- follow_up points at T-2057, this repo's established shared \
# tracker for a genuinely-wired-but-not-externally-called symbol (see \
# src/frob/__main__.py, src/frob/gates/_arch.py, src/frob/gates/_coverage_sites.py's \
# own identical WIRE001 waivers citing it), since a private per-file test helper will \
# never have a caller outside this module by construction and citing THIS ticket's own \
# id would make the waiver self-referential and unresolvable the moment T-2257 closes"
def _file_cfg(tmp_path: Path, *, title: str, body: str, scope: list[str]) -> AppConfig:
    """A minimal `frob ticket new`-shaped `AppConfig` -- test helper only,
    mirroring `test_ticket_new_scope_plausibility.py`'s own precedent for
    calling `_new` directly against a bare `tmp_path`, no git repo
    required."""
    return AppConfig(
        ticket_command="new",
        ticket_title=title,
        ticket_body=body,
        ticket_kind="bug",
        ticket_path=tmp_path,
        ticket_scope=scope,
        ticket_ack_related=True,
    )


# frob:ticket T-2257
class TestScopeOverlapWarnings:
    """Acceptance criteria 1-5 (T-2257): a scope-overlap warning at
    `frob ticket new` filing time, naming the other open ticket(s) and the
    overlapping resolved path(s)."""

    # frob:ticket T-2257
    def test_overlapping_scope_names_the_other_ticket_and_path(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings.test_overlapping_scope_names_the_other_ticket_and_path  # noqa: E501
        """(MUST FAIL FIRST on main, T-2257 acceptance criterion 1): filing
        a ticket whose scope overlaps an existing QUEUED ticket's scope
        must warn, naming the other ticket and the overlapping path."""
        _write(
            tmp_path / "scripts/fleet_status.py",
            "def status():\n    return 'ok'\n",
        )
        first_cfg = _file_cfg(
            tmp_path,
            title="fleet_status prints a stale count",
            body="fleet_status.py's own summary line is off by one.",
            scope=["scripts/fleet_status.py"],
        )
        with caplog.at_level(logging.WARNING):
            _new(tmp_path, first_cfg)
        first_id = next(p.name for p in (tmp_path / "tickets").iterdir() if p.is_dir())

        caplog.clear()
        second_cfg = _file_cfg(
            tmp_path,
            title="fleet_status also mis-sorts the dispatchable list",
            body="fleet_status.py's own sort key ignores priority.",
            scope=["scripts/fleet_status.py"],
        )
        with caplog.at_level(logging.WARNING):
            _new(tmp_path, second_cfg)

        messages = "\n".join(r.getMessage() for r in caplog.records)
        assert first_id in messages, (
            f"expected the overlap warning to name {first_id}; got:\n{messages}"
        )
        assert "scripts/fleet_status.py" in messages

    # frob:ticket T-2257
    def test_real_case_four_prior_tickets_all_named(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings.test_real_case_four_prior_tickets_all_named  # noqa: E501
        """Acceptance criterion 5: verified against the real T-2257 incident
        shape -- FOUR already-open tickets all declaring scope over one
        file (`scripts/fleet_status.py`, echoing the real T-2213/T-2229/
        T-2236/T-2249 pileup this ticket's own body measured), then a
        FIFTH ticket filed against the same file must name every one of
        the four in its overlap warning."""
        _write(tmp_path / "scripts/fleet_status.py", "def status():\n    return 1\n")
        prior_ids: list[str] = []
        for n in range(4):
            cfg = _file_cfg(
                tmp_path,
                title=f"fleet_status defect number {n}",
                body=f"fleet_status.py has independent defect {n}.",
                scope=["scripts/fleet_status.py"],
            )
            _new(tmp_path, cfg)
            new_id = next(
                p.name
                for p in (tmp_path / "tickets").iterdir()
                if p.is_dir() and p.name not in prior_ids
            )
            prior_ids.append(new_id)
        assert len(prior_ids) == 4

        caplog.clear()
        fifth_cfg = _file_cfg(
            tmp_path,
            title="fleet_status defect number 4",
            body="fleet_status.py has independent defect 4.",
            scope=["scripts/fleet_status.py"],
        )
        with caplog.at_level(logging.WARNING):
            _new(tmp_path, fifth_cfg)

        messages = "\n".join(r.getMessage() for r in caplog.records)
        for prior_id in prior_ids:
            assert prior_id in messages, (
                f"expected {prior_id} named in the overlap warning; got:\n{messages}"
            )

    # frob:ticket T-2257
    def test_glob_vs_file_overlap_is_detected(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings.test_glob_vs_file_overlap_is_detected  # noqa: E501
        """Acceptance criterion 2: overlap is computed on RESOLVED PATHS,
        so a glob-vs-file overlap (`src/frob/**` vs
        `src/frob/gates/_x.py`) is caught even though the two scope
        entries never share any substring."""
        _write(tmp_path / "src/frob/gates/_x.py", "x = 1\n")
        _write(tmp_path / "src/frob/__init__.py", "\n")
        broad_cfg = _file_cfg(
            tmp_path,
            title="broad refactor across all of frob",
            body="Touches many things under src/frob.",
            scope=["src/frob/**"],
        )
        with caplog.at_level(logging.WARNING):
            _new(tmp_path, broad_cfg)
        broad_id = next(p.name for p in (tmp_path / "tickets").iterdir() if p.is_dir())

        caplog.clear()
        narrow_cfg = _file_cfg(
            tmp_path,
            title="fix _x.py's off-by-one",
            body="src/frob/gates/_x.py computes x wrong.",
            scope=["src/frob/gates/_x.py"],
        )
        with caplog.at_level(logging.WARNING):
            _new(tmp_path, narrow_cfg)

        messages = "\n".join(r.getMessage() for r in caplog.records)
        assert broad_id in messages
        assert "src/frob/gates/_x.py" in messages

    # frob:ticket T-2257
    def test_non_overlapping_scope_is_silent(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings.test_non_overlapping_scope_is_silent  # noqa: E501
        """Acceptance criterion 3 (must-still-pass control): a ticket whose
        scope does not overlap any other open ticket files silently, as
        today -- this is advisory output, never a gate, and filing always
        succeeds either way."""
        _write(tmp_path / "src/frob/a.py", "a = 1\n")
        _write(tmp_path / "src/frob/b.py", "b = 1\n")
        first_cfg = _file_cfg(
            tmp_path,
            title="alpha module's off-by-one",
            body="src/frob/a.py computes a wrong.",
            scope=["src/frob/a.py"],
        )
        _new(tmp_path, first_cfg)

        caplog.clear()
        second_cfg = _file_cfg(
            tmp_path,
            title="beta widget's sort order is reversed",
            body="src/frob/b.py computes b wrong.",
            scope=["src/frob/b.py"],
        )
        with caplog.at_level(logging.WARNING):
            _new(tmp_path, second_cfg)

        messages = "\n".join(r.getMessage() for r in caplog.records)
        assert "scope overlaps" not in messages
        # Filing itself still succeeded -- a second ticket dir exists.
        assert len(list((tmp_path / "tickets").iterdir())) == 2

    # frob:ticket T-2257
    def test_terminal_state_tickets_are_excluded(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings.test_terminal_state_tickets_are_excluded  # noqa: E501
        """Acceptance criterion 4: a DONE/DROPPED ticket's old scope is
        history, not a live claim -- it must not trigger the overlap
        warning."""
        from frob.tickets._models import TicketState
        from frob.tickets._store import load_all, write_ticket

        _write(tmp_path / "scripts/fleet_status.py", "x = 1\n")
        first_cfg = _file_cfg(
            tmp_path,
            title="fleet_status prints a stale count",
            body="fleet_status.py's own summary line is off by one.",
            scope=["scripts/fleet_status.py"],
        )
        _new(tmp_path, first_cfg)
        first_id = next(p.name for p in (tmp_path / "tickets").iterdir() if p.is_dir())
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        first_ticket = loaded.danger_ok[first_id]
        done_ticket = first_ticket.model_copy(update={"state": TicketState.DONE})
        assert write_ticket(tmp_path, done_ticket).is_ok

        caplog.clear()
        second_cfg = _file_cfg(
            tmp_path,
            title="fleet_status also mis-sorts the dispatchable list",
            body="fleet_status.py's own sort key ignores priority.",
            scope=["scripts/fleet_status.py"],
        )
        with caplog.at_level(logging.WARNING):
            _new(tmp_path, second_cfg)

        messages = "\n".join(r.getMessage() for r in caplog.records)
        assert "scope overlaps" not in messages


# frob:ticket T-2342
class TestNonRelativeScopeDoesNotCrash:
    """T-2342 (reader-side half): a ticket with a corrupted, ABSOLUTE-path
    scope entry (T-2308's real incident -- the rapid-sweep auto-filer had
    written filesystem-absolute paths into `scope:`) used to crash EVERY
    `frob ticket new` fleet-wide with `NotImplementedError: Non-relative
    patterns are unsupported`, because `Path.glob()`'s laziness meant the
    `try/except` around the call never actually caught the error raised
    during iteration. Filing an unrelated ticket must still succeed, and
    the malformed entry must be named in a warning, not silently
    swallowed or silently coerced into something plausible."""

    # frob:ticket T-2342
    # frob:tests tests/unit/test_new_ticket_scope_overlap_warning.py::TestNonRelativeScopeDoesNotCrash.test_unrelated_ticket_still_files_despite_one_corrupt_row  # noqa: E501
    def test_unrelated_ticket_still_files_despite_one_corrupt_row(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Positive control 3 (T-2342): `frob ticket new` for an UNRELATED
        ticket still succeeds when one bad row exists elsewhere in the
        ledger -- this MUST FAIL on main (raises NotImplementedError)."""
        from frob.tickets._store import load_all, write_ticket

        _write(tmp_path / "scripts/fleet_status.py", "x = 1\n")
        corrupt_cfg = _file_cfg(
            tmp_path,
            title="corrupt scope victim",
            body="placeholder body.",
            scope=["scripts/fleet_status.py"],
        )
        _new(tmp_path, corrupt_cfg)
        corrupt_id = next(p.name for p in (tmp_path / "tickets").iterdir() if p.is_dir())
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        corrupt_ticket = loaded.danger_ok[corrupt_id]
        # T-2308's real corruption shape: an absolute filesystem path
        # instead of a repo-relative glob, on an otherwise-normal
        # non-terminal (queued) ticket.
        corrupted = corrupt_ticket.model_copy(
            update={"scope": [str((tmp_path / "scripts/fleet_status.py").resolve())]}
        )
        assert write_ticket(tmp_path, corrupted).is_ok

        _write(tmp_path / "src/unrelated.py", "y = 1\n")
        caplog.clear()
        unrelated_cfg = _file_cfg(
            tmp_path,
            title="an entirely unrelated ticket",
            body="src/unrelated.py has its own, unrelated defect.",
            scope=["src/unrelated.py"],
        )
        with caplog.at_level(logging.WARNING):
            _new(tmp_path, unrelated_cfg)  # must not raise

        ids = {p.name for p in (tmp_path / "tickets").iterdir() if p.is_dir()}
        assert corrupt_id in ids
        assert len(ids) == 2, f"expected the unrelated ticket to have filed too: {ids}"

    # frob:ticket T-2342
    # frob:tests tests/unit/test_new_ticket_scope_overlap_warning.py::TestNonRelativeScopeDoesNotCrash.test_corrupt_row_is_named_loudly_not_silently_coerced  # noqa: E501
    def test_corrupt_row_is_named_loudly_not_silently_coerced(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Positive control 2 (T-2342, must-still-pass): a genuinely
        malformed scope entry is REJECTED loudly -- named in a warning
        identifying the offending ticket and path -- rather than silently
        coerced into a plausible-looking relative path or silently
        dropped with no trace."""
        from frob.tickets._store import load_all, write_ticket

        _write(tmp_path / "scripts/fleet_status.py", "x = 1\n")
        corrupt_cfg = _file_cfg(
            tmp_path,
            title="corrupt scope victim",
            body="placeholder body.",
            scope=["scripts/fleet_status.py"],
        )
        _new(tmp_path, corrupt_cfg)
        corrupt_id = next(p.name for p in (tmp_path / "tickets").iterdir() if p.is_dir())
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        corrupt_ticket = loaded.danger_ok[corrupt_id]
        abs_path = str((tmp_path / "scripts/fleet_status.py").resolve())
        corrupted = corrupt_ticket.model_copy(update={"scope": [abs_path]})
        assert write_ticket(tmp_path, corrupted).is_ok

        _write(tmp_path / "src/unrelated.py", "y = 1\n")
        caplog.clear()
        unrelated_cfg = _file_cfg(
            tmp_path,
            title="an entirely unrelated ticket",
            body="src/unrelated.py has its own, unrelated defect.",
            scope=["src/unrelated.py"],
        )
        with caplog.at_level(logging.WARNING):
            _new(tmp_path, unrelated_cfg)

        messages = "\n".join(r.getMessage() for r in caplog.records)
        assert corrupt_id in messages, (
            f"expected the offending ticket {corrupt_id} named; got:\n{messages}"
        )
        assert abs_path in messages or "non-relative" in messages.lower(), (
            f"expected the malformed path or a 'non-relative' label; got:\n{messages}"
        )

    # frob:ticket T-2342
    # frob:tests tests/unit/test_new_ticket_scope_overlap_warning.py::TestNonRelativeScopeDoesNotCrash.test_multiple_corrupt_entries_use_plural_wording  # noqa: E501
    def test_multiple_corrupt_entries_use_plural_wording(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T-2342 TEST016 kill: TWO malformed scope entries on the same
        offending ticket must pluralize ("entries", not "entry") -- this
        distinguishes the singular/plural branch from a mutant that always
        picks one or the other, which a single-bad-entry test cannot."""
        from frob.tickets._store import load_all, write_ticket

        _write(tmp_path / "scripts/fleet_status.py", "x = 1\n")
        _write(tmp_path / "scripts/other.py", "y = 1\n")
        corrupt_cfg = _file_cfg(
            tmp_path,
            title="corrupt scope victim two",
            body="placeholder body.",
            scope=["scripts/fleet_status.py"],
        )
        _new(tmp_path, corrupt_cfg)
        corrupt_id = next(p.name for p in (tmp_path / "tickets").iterdir() if p.is_dir())
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        corrupt_ticket = loaded.danger_ok[corrupt_id]
        abs_paths = [
            str((tmp_path / "scripts/fleet_status.py").resolve()),
            str((tmp_path / "scripts/other.py").resolve()),
        ]
        corrupted = corrupt_ticket.model_copy(update={"scope": abs_paths})
        assert write_ticket(tmp_path, corrupted).is_ok

        _write(tmp_path / "src/unrelated2.py", "z = 1\n")
        caplog.clear()
        unrelated_cfg = _file_cfg(
            tmp_path,
            title="another entirely unrelated ticket",
            body="src/unrelated2.py has its own, unrelated defect.",
            scope=["src/unrelated2.py"],
        )
        with caplog.at_level(logging.WARNING):
            _new(tmp_path, unrelated_cfg)

        messages = "\n".join(r.getMessage() for r in caplog.records)
        assert "entries" in messages, f"expected plural 'entries'; got:\n{messages}"
        assert "entry" not in messages.replace("entries", ""), (
            f"expected no singular 'entry' when 2 bad patterns exist; got:\n{messages}"
        )
