"""Regression test for T-2697: `tickets/T-2691/ticket.md` tripped DOC006's
CLI-invocation-pointer check because its prose backtick-quoted a
not-yet-implemented future verb, ``frob land status``, which DOC006's
scan (correctly) reads as a real CLI invocation that must resolve against
the live argparse dispatch table. Reproduces the exact shape as a
synthetic fixture (mirroring `tests/test_docptr_gate.py`'s own pattern)
rather than depending on the live ticket file's exact wording staying
byte-identical forever.
"""
# frob:ticket T-2697

from __future__ import annotations

from pathlib import Path

from frob.gates._docptr import doc006_gate
from frob.graph import build_graph

# Reuse the existing DOC006 fixture helpers rather than redefining a 14th
# byte-identical copy of _git/_init_repo/_write (DUP001: every prior test
# file covering this gate already carries its own copy of these three
# functions; importing tests.test_docptr_gate's versions instead of
# adding another copy is the NO DUPLICATION fix).
from tests.test_docptr_gate import _CLI_CONFIG, _git, _init_repo, _write  # noqa: E402

# T-3712: self-contained reproduction of T-2691's actual ticket.md prose
# (post-T-2697-fix wording, copied verbatim from the archived ticket) so
# this regression no longer depends on the live/archived ledger path --
# `frob ticket archive` legitimately relocates closed tickets and must
# never be able to break this test.
_TICKET_2691_BODY = (
    "An operator watching `frob ticket land` while the fleet is contended has\n"
    "no visibility into whether it is progressing, waiting on land.lock, or\n"
    "was preempted/killed mid-flight -- the only way to tell is inspecting the\n"
    "process tree and `.frob/land.lock` by hand (observed directly during a\n"
    "2026-08-20 fleet-serialization incident: a land killed by its own\n"
    "foreground timeout under lock contention left a MERGE_HEAD-in-progress\n"
    "worktree, an orphaned land.lock entry, and no visible signal beyond a\n"
    "truncated log that the attempt had failed rather than succeeded -- 270s\n"
    "of wall clock, mostly spent waiting on another ticket's held lock, then\n"
    "nothing landed and no land commit produced).\n"
    "\n"
    "`frob ticket land` already logs a WARNING when it starts waiting on a\n"
    'held land.lock ("waiting up to 500s before refusing") and again when it\n'
    "reclaims an orphaned one -- but that line only reaches whoever is reading\n"
    "stdout live; it is not surfaced anywhere an operator or coordinator can\n"
    "poll (no `.frob/land-status.json`, no `frob ticket show`/`fleet_status`\n"
    'field distinguishing "queued behind lock" from "actively running gates"\n'
    'from "dead, needs a retry"). Fold this into the T-2141 disclosure\n'
    "direction: a small land-status marker file (holder pid, phase,\n"
    "started_at, last-heartbeat) that `fleet_status.py` and a future,\n"
    'not-yet-implemented "frob land status" verb can read, so "is my land\n'
    "alive, and did it accomplish\n"
    'anything" stops requiring manual `ps`/`git log --grep`/`git status`\n'
    "archaeology after the fact.\n"
    "\n"
    "Filed from the T-2141/T-1549/T-2303 series per an explicit coordinator\n"
    "instruction during a live fleet-serialization hold (2026-08-20): the\n"
    "starved-batch incident that motivated the hold is itself the missing-\n"
    "disclosure case this ticket should fix.\n"
)


class TestTicket2691Doc006Regression:
    """T-2697: `frob land status` backtick-quoted as a real CLI invocation
    while describing a future, not-yet-implemented verb."""

    def test_backticked_future_verb_is_flagged(self, tmp_path: Path) -> None:
        """The pre-fix shape (T-2697's own repro): a backtick-quoted
        two-word phrase that reads exactly like a live CLI invocation but
        names a verb that does not exist yet must be flagged -- DOC006
        cannot distinguish "real but missing" from "deliberately
        aspirational" by pattern alone, which is why the fix is to stop
        backtick-quoting it as an invocation at all (see the passing test
        below)."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _write(
            tmp_path,
            "tickets/T-2691/ticket.md",
            "a future `frob land status` can read the marker file.\n",
        )
        _git(tmp_path, "add", "-A")
        violations = doc006_gate(
            tmp_path, build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
        )
        found = [v for v in violations if v.rule == "DOC006"]
        assert found
        assert any("land status" in v.message for v in found)

    def test_prose_description_of_future_verb_not_flagged(self, tmp_path: Path) -> None:
        """T-2697's actual fix: describe the future verb in plain quoted
        prose instead of backticks, so DOC006 no longer reads it as a
        real CLI invocation that must resolve today."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _write(
            tmp_path,
            "tickets/T-2691/ticket.md",
            'a future, not-yet-implemented "frob land status" verb can'
            " read the marker file.\n",
        )
        _git(tmp_path, "add", "-A")
        violations = doc006_gate(
            tmp_path, build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
        )
        found = [v for v in violations if v.rule == "DOC006"]
        assert not found

    def test_real_ticket_file_not_flagged(self, tmp_path: Path) -> None:
        """T-2697's own repro, reproduced as a SELF-CONTAINED fixture
        (T-3712) rather than reading the live ticket file: the ledger's
        `frob ticket archive` legitimately moves closed tickets out of
        `tickets/T-2691/` to `tickets/archive/T-2691/`, so a test that
        hardcodes the active-ledger path breaks on archival even though
        DOC006's behavior against the content shape has not changed.
        `_TICKET_2691_BODY` below is T-2691's post-fix prose, copied
        verbatim: the future verb is quoted in prose
        (`not-yet-implemented "frob land status" verb`) rather than
        backtick-quoted as a live invocation, which is exactly the shape
        this regression must keep asserting DOC006 does not flag."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _write(
            tmp_path,
            "tickets/T-2691/ticket.md",
            _TICKET_2691_BODY,
        )
        _git(tmp_path, "add", "-A")
        violations = doc006_gate(
            tmp_path, build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
        )
        found = [v for v in violations if v.rule == "DOC006"]
        assert not found


class TestTicket2742Doc006Regression:
    """T-2745: the identical mistake recurred on a DIFFERENT ticket
    (`tickets/T-2742/ticket.md`) three days after T-2697 fixed T-2691's
    instance of it -- same two-word hypothetical verb, `frob land
    status`, backtick-quoted as though it were a real invocation. DOC006
    correctly flagged it again; the sweep that surfaced it was
    UNATTRIBUTED because the land it was filed against never touched this
    file -- the drift was introduced by the ticket's own body edit, not
    by the blamed land. Same fix as T-2697: stop backtick-quoting the
    hypothetical verb.

    Uses a synthetic fixture (not a full copy of the live ticket file, as
    `test_real_ticket_file_not_flagged` above does for T-2691): the real
    T-2742 body also backtick-references several genuine repo paths
    (`docs/guides/agent-playbook.md`, `.frob/land.lock`) that resolve
    fine in the real repo tree but do not exist in an isolated fixture
    repo, which would make a full-body copy fail here for a reason
    unrelated to DOC006's CLI-invocation check. The synthetic shape
    below isolates exactly the recurring mistake."""

    def test_backticked_future_verb_is_flagged(self, tmp_path: Path) -> None:
        """The pre-fix shape (T-2745's own repro, same as T-2697's): a
        backtick-quoted phrase reading like a live CLI invocation for a
        verb that does not exist yet must be flagged."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _write(
            tmp_path,
            "tickets/T-2742/ticket.md",
            "A first-class query -- e.g. `frob land status` or a field.\n",
        )
        _git(tmp_path, "add", "-A")
        violations = doc006_gate(
            tmp_path, build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
        )
        found = [v for v in violations if v.rule == "DOC006"]
        assert found
        assert any("land status" in v.message for v in found)

    def test_prose_description_of_future_verb_not_flagged(self, tmp_path: Path) -> None:
        """T-2745's actual fix: describe the future verb in plain prose
        (no backticks), so DOC006 no longer reads it as a real CLI
        invocation that must resolve today. Matches the exact wording
        landed in `tickets/T-2742/ticket.md`."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _write(
            tmp_path,
            "tickets/T-2742/ticket.md",
            'A first-class query -- e.g. a hypothetical "frob land status"'
            " verb (not a real command; do not run it) or a field.\n",
        )
        _git(tmp_path, "add", "-A")
        violations = doc006_gate(
            tmp_path, build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
        )
        found = [v for v in violations if v.rule == "DOC006"]
        assert not found
