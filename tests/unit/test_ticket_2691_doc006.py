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
        """T-2697's own repro, tied directly to the LIVE ticket file
        rather than a synthetic stand-in: copies the actual current
        content of `tickets/T-2691/ticket.md` into a throwaway fixture
        repo and asserts DOC006 raises nothing against it. Before the
        T-2697 fix this failed for real (the live file backtick-quoted
        `frob land status`); after the fix it passes."""
        repo_root = Path(__file__).resolve().parents[2]
        real_ticket = repo_root / "tickets" / "T-2691" / "ticket.md"
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _write(
            tmp_path,
            "tickets/T-2691/ticket.md",
            real_ticket.read_text(encoding="utf-8"),
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
