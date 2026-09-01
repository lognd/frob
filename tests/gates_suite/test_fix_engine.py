import json
import subprocess
from datetime import date
from pathlib import Path

import pytest

from frob.gates import (
    sys_gate,
    tickets_gate,
)
from frob.graph import build_graph
from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState
from frob.tickets._store import write_ticket
from tests.conftest import (
    _git_init,
    _ticket,
    _write,
)


# frob:ticket T-1138
# frob:ticket T-1531
# frob:ticket T-1763
# frob:ticket T-2865
# frob:ticket T-2922
class TestFixEngineTierA:
    """`frob.gates._fix_engine`'s Tier-A deterministic --fix handlers
    (T-1138): DOC007 dotted-form rewrite, DOC002 unique-anchor-slug
    correction, TICK002 draft renumber. Each is a GIVEN/WHEN/THEN
    acceptance criterion off this ticket's own body."""

    def _snap(self, root: Path):

        return build_graph(root, root / ".frob" / "cache.db").danger_ok

    # -- T-2351: pre-fix dirty-file snapshot -------------------------------

    def test_pre_fix_dirty_snapshot_captures_uncommitted_content(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine.py::_snapshot_dirty_files  # noqa: E501
        from frob.gates._fix_engine import _snapshot_dirty_files

        root = tmp_path / "repo"
        root.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)

        clean = root / "clean.py"
        clean.write_text("clean\n", encoding="utf-8")
        dirty = root / "dirty.py"
        dirty.write_text("committed\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=root, check=True)

        # Modify one tracked file (dirty), leave the other untouched
        # (clean), and add a brand-new untracked file -- only the dirty
        # TRACKED file's content should be captured.
        dirty.write_text("uncommitted edit\n", encoding="utf-8")
        (root / "untracked.py").write_text("new\n", encoding="utf-8")

        snapshot = _snapshot_dirty_files(root)

        assert snapshot == {"dirty.py": b"uncommitted edit\n"}

    # -- acceptance [0]: DOC007 dotted-form rewrite ------------------------

    def test_doc007_dotted_form_rewrite_applies_and_reverifies_clean(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine.py::fix_doc007_dotted_form kind="unit"
        # frob:tests src/frob/gates/_docptr.py::_tests_target_shape_violations \
        # kind="unit"
        from frob.gates import apply_tier_a_fixes, doc006_gate
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "src" / "pkg").mkdir(parents=True)
        (root / "src" / "pkg" / "mod.py").write_text(
            "# frob:tests tests/test_mod.py::TestX::test_y\ndef real():\n    pass\n",
            encoding="utf-8",
        )
        snapshot = self._snap(root)
        before = doc006_gate(root, snapshot)
        assert any(v.rule == "DOC007" for v in before)

        applied = apply_tier_a_fixes(root, snapshot, TicketQueue(tickets={}))
        doc007_applied = [a for a in applied if a.rule == "DOC007"]
        assert len(doc007_applied) == 1
        assert "tests/test_mod.py::TestX.test_y" in doc007_applied[0].detail

        rewritten = (root / "src" / "pkg" / "mod.py").read_text(encoding="utf-8")
        assert "# frob:tests tests/test_mod.py::TestX.test_y" in rewritten
        assert "TestX::test_y" not in rewritten

        after_snapshot = self._snap(root)
        after = doc006_gate(root, after_snapshot)
        assert not [v for v in after if v.rule == "DOC007"]

    def test_doc007_already_dotted_is_a_no_op(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine.py::fix_doc007_dotted_form kind="unit"
        from frob.gates import apply_tier_a_fixes
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "src" / "pkg").mkdir(parents=True)
        content = (
            "# frob:tests tests/test_mod.py::TestX.test_y\ndef real():\n    pass\n"
        )
        (root / "src" / "pkg" / "mod.py").write_text(content, encoding="utf-8")
        snapshot = self._snap(root)
        applied = apply_tier_a_fixes(root, snapshot, TicketQueue(tickets={}))
        assert not [a for a in applied if a.rule == "DOC007"]
        assert (root / "src" / "pkg" / "mod.py").read_text(encoding="utf-8") == content

    def test_excluded_handler_is_skipped_and_file_untouched(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine.py::apply_tier_a_fixes kind="unit"
        # frob:ticket T-1323
        from frob.gates import apply_tier_a_fixes
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "src" / "pkg").mkdir(parents=True)
        content = (
            "# frob:tests tests/test_mod.py::TestX::test_y\ndef real():\n    pass\n"
        )
        (root / "src" / "pkg" / "mod.py").write_text(content, encoding="utf-8")
        snapshot = self._snap(root)

        applied = apply_tier_a_fixes(
            root, snapshot, TicketQueue(tickets={}), exclude=("DOC007",)
        )
        assert not [a for a in applied if a.rule == "DOC007"]
        assert (root / "src" / "pkg" / "mod.py").read_text(encoding="utf-8") == content

    # -- acceptance [1]: DOC002 unique-anchor-slug correction --------------

    def test_doc002_unique_fuzzy_candidate_rewritten_and_reverifies_clean(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine.py::fix_doc002_unique_slug kind="unit"
        # frob:tests src/frob/gates/_doclink_docanchor.py::docanchor_gate kind="unit"
        from frob.gates import apply_tier_a_fixes, docanchor_gate
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "src").mkdir()
        (root / "docs" / "m.md").write_text(
            "# Title\n\n## Real Heading\n", encoding="utf-8"
        )
        (root / "src" / "m.py").write_text(
            "# frob:doc docs/m.md#real-headin\ndef f():\n    return 1\n",
            encoding="utf-8",
        )
        snapshot = self._snap(root)
        before = docanchor_gate(root, snapshot)
        assert any(v.rule == "DOC002" for v in before)

        applied = apply_tier_a_fixes(root, snapshot, TicketQueue(tickets={}))
        doc002_applied = [a for a in applied if a.rule == "DOC002"]
        assert len(doc002_applied) == 1
        assert "docs/m.md#real-heading" in doc002_applied[0].detail

        rewritten = (root / "src" / "m.py").read_text(encoding="utf-8")
        assert "# frob:doc docs/m.md#real-heading" in rewritten

        after = docanchor_gate(root, self._snap(root))
        assert not [v for v in after if v.rule == "DOC002"]

    def test_doc002_ambiguous_candidates_stay_unfixed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine.py::fix_doc002_unique_slug kind="unit"
        from frob.gates import apply_tier_a_fixes, docanchor_gate
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "src").mkdir()
        # Two headings close enough to the mismatched target slug that
        # neither is an unambiguous single candidate -- the "stays unfixed
        # with an assisted fix-it" half of this ticket's acceptance
        # criterion.
        (root / "docs" / "m.md").write_text(
            "# Title\n\n## Widget Alpha\n\n## Widget Beta\n", encoding="utf-8"
        )
        (root / "src" / "m.py").write_text(
            "# frob:doc docs/m.md#widget-gamma\ndef f():\n    return 1\n",
            encoding="utf-8",
        )
        snapshot = self._snap(root)
        before = docanchor_gate(root, snapshot)
        assert any(v.rule == "DOC002" for v in before)

        applied = apply_tier_a_fixes(root, snapshot, TicketQueue(tickets={}))
        assert not [a for a in applied if a.rule == "DOC002"]
        unchanged = (root / "src" / "m.py").read_text(encoding="utf-8")
        assert "widget-gamma" in unchanged

        after = docanchor_gate(root, self._snap(root))
        assert any(v.rule == "DOC002" for v in after)

    def test_doc002_zero_candidates_stay_unfixed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine.py::fix_doc002_unique_slug kind="unit"
        from frob.gates import apply_tier_a_fixes, docanchor_gate
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "src").mkdir()
        (root / "docs" / "m.md").write_text(
            "# Title\n\n## Real Heading\n", encoding="utf-8"
        )
        (root / "src" / "m.py").write_text(
            "# frob:doc docs/m.md#totally-unrelated-slug\ndef f():\n    return 1\n",
            encoding="utf-8",
        )
        snapshot = self._snap(root)
        applied = apply_tier_a_fixes(root, snapshot, TicketQueue(tickets={}))
        assert not [a for a in applied if a.rule == "DOC002"]
        after = docanchor_gate(root, self._snap(root))
        assert any(v.rule == "DOC002" for v in after)

    # T-1763: the T-1177 INV006 split-carried-waiver auto-carry tests that
    # used to live here (fix_inv006_carried_waiver) were removed along with
    # the rest of the INV006 gate -- 338 waivers, zero unwaived findings
    # across its whole lifetime; see docs/modules/gates.md's T-1763 note.

    # T-1870: the SYS104 interface= union acceptance tests that used to
    # live here (fix_sys104_interface_union, T-1531/T-1774) were removed
    # along with the rest of the `frob sys sync-interface` machinery, per
    # an explicit owner directive that no code path may auto-update
    # declared public-symbol surface; see docs/modules/gates.md's T-1870
    # note.

    # -- acceptance: SYS100 auto-widening REMOVED (T-2922) -------------------
    #
    # T-1531/T-1545's `fix_sys100_may_via_union`/`fix_sys100_extended_
    # whole_node_grant` (and their acceptance tests that used to live
    # here) are deleted -- they silently widened a node's declared `may=`
    # ceiling to match observed capability use, which is the exact
    # ratchet-with-no-teeth T-2922 exists to remove. See src/frob/gates/
    # _fix_engine_sync.py's "SYS100 auto-widening -- REMOVED" comment
    # block for the full rationale and the T-1623/T-1628 supersession
    # note. The two tests below are this ticket's own proof pair: SYS100
    # the DETECTOR must still fire (must-still-fire), and running the
    # Tier-A fix engine must no longer make that finding disappear
    # (must-not-auto-resolve) -- for both the CORE (`via`-list) and
    # EXTENDED (whole-node) capability shapes T-1531/T-1545 used to cover.

    # frob:ticket T-2922
    def test_sys100_core_violation_still_fires_and_is_not_auto_resolved(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine.py::apply_tier_a_fixes kind="unit"
        # frob:tests src/frob/gates/_sys.py::sys_gate kind="unit"
        # SELFAUDIT001's fold only fires against a `root` that LOOKS like
        # this repo (`src/frob/...`, `_selfaudit_violations`'s own
        # precondition -- same shape TestSelfAuditGate's tests already use
        # a few thousand lines below this class), so this test mirrors
        # that shape rather than an arbitrary `api/` layout.
        from frob.gates import apply_tier_a_fixes
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "src" / "frob" / "widget").mkdir(parents=True)
        (root / "src" / "frob" / "widget" / "_io.py").write_text(
            "import requests\nrequests.get('x')\n", encoding="utf-8"
        )
        (root / "design").mkdir()
        design_text = (
            'module m\nnode widget : trusted {\n    code "src/frob/widget/**";\n}\n'
        )
        (root / "design" / "m.strata").write_text(design_text, encoding="utf-8")

        # must-still-fire: the undeclared net.connect use is a real SYS100
        # finding (folded into SELFAUDIT001) before any fix engine runs.
        before = sys_gate(root, self._snap(root))
        before_selfaudit = [v for v in before if v.rule == "SELFAUDIT001"]
        assert before_selfaudit, "SELFAUDIT001 must fold a SYS100 finding"
        assert any("SYS100" in v.message for v in before_selfaudit), (
            "SYS100 must fire on an undeclared capability -- detection is "
            "unaffected by T-2922"
        )

        # must-not-auto-resolve: apply_tier_a_fixes must not touch the
        # declaration, and the SYS100 finding must still be there after.
        applied = apply_tier_a_fixes(root, self._snap(root), TicketQueue(tickets={}))
        assert not [a for a in applied if a.rule == "SYS100"], (
            "no Tier-A handler may silently widen a may= grant any more"
        )
        rewritten = (root / "design" / "m.strata").read_text(encoding="utf-8")
        assert rewritten == design_text, "the ceiling must be untouched"
        after = sys_gate(root, self._snap(root))
        after_selfaudit = [v for v in after if v.rule == "SELFAUDIT001"]
        assert any("SYS100" in v.message for v in after_selfaudit), (
            "SYS100 must still fire identically after a Tier-A fix pass"
        )

    # frob:ticket T-2922
    def test_sys100_extended_violation_still_fires_and_is_not_auto_resolved(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine.py::apply_tier_a_fixes kind="unit"
        # frob:tests src/frob/gates/_sys.py::sys_gate kind="unit"
        from frob.gates import apply_tier_a_fixes
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "src" / "frob" / "danger").mkdir(parents=True)
        (root / "src" / "frob" / "danger" / "_run.py").write_text(
            "def f(x):\n    return eval(x)\n", encoding="utf-8"
        )
        (root / "design").mkdir()
        design_text = (
            'module m\nnode danger : trusted {\n    code "src/frob/danger/**";\n}\n'
        )
        (root / "design" / "m.strata").write_text(design_text, encoding="utf-8")

        before = sys_gate(root, self._snap(root))
        before_selfaudit = [v for v in before if v.rule == "SELFAUDIT001"]
        assert before_selfaudit, "SELFAUDIT001 must fold a SYS100 finding"
        assert any("SYS100" in v.message for v in before_selfaudit), (
            "SYS100 EXTENDED must fire on an undeclared eval use -- "
            "detection is unaffected by T-2922"
        )

        applied = apply_tier_a_fixes(root, self._snap(root), TicketQueue(tickets={}))
        assert not [a for a in applied if a.rule == "SYS100"], (
            "no Tier-A handler may silently insert a whole-node may= grant any more"
        )
        rewritten = (root / "design" / "m.strata").read_text(encoding="utf-8")
        assert rewritten == design_text, "the ceiling must be untouched"
        after = sys_gate(root, self._snap(root))
        after_selfaudit = [v for v in after if v.rule == "SELFAUDIT001"]
        assert any("SYS100" in v.message for v in after_selfaudit), (
            "SYS100 EXTENDED must still fire identically after a Tier-A fix pass"
        )

    # -- acceptance [2]: TICK002 draft renumber -----------------------------

    def test_tick002_renumbers_draft_and_reverifies_clean(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine.py::fix_tick002_renumber kind="unit"
        # frob:tests src/frob/gates/_tickets_gate.py::_tick002_draft_on_default \
        # kind="unit"
        import subprocess

        from frob.gates._fix_engine import fix_tick002_renumber
        from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState
        from frob.tickets._provisional import is_draft_id, mint_draft_id

        root = tmp_path / "repo"
        root.mkdir()

        def _git(*args: str) -> None:
            subprocess.run(
                ["git", "-C", str(root), *args],
                check=True,
                capture_output=True,
                text=True,
            )

        _git("init", "-q", "-b", "main")
        _git("config", "user.email", "test@example.com")
        _git("config", "user.name", "Test")
        (root / "tickets.md").write_text("# Tickets\n\n", encoding="utf-8")
        (root / "tickets-archive.md").write_text("# Archive\n\n", encoding="utf-8")
        _git("add", "-A")
        _git("commit", "-q", "-m", "init")

        draft_id = mint_draft_id()
        assert is_draft_id(draft_id)
        draft = Ticket(
            id=draft_id,
            title="stray draft on main",
            state=TicketState.QUEUED,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
        )
        write_result = write_ticket(root, draft)
        assert write_result.is_ok
        _git("add", "-A")
        _git("commit", "-q", "-m", "file draft ticket directly on main (TICK002 repro)")

        queue = TicketQueue(tickets={draft_id: draft})
        before = tickets_gate(root, queue)
        assert any(v.rule == "TICK002" for v in before)

        applied = fix_tick002_renumber(root, queue)
        assert len(applied) == 1
        assert applied[0].rule == "TICK002"
        assert draft_id in applied[0].detail

        from frob.tickets._store import load_all

        reloaded = load_all(root)
        assert reloaded.is_ok
        assert draft_id not in reloaded.danger_ok
        after_queue = TicketQueue(tickets=reloaded.danger_ok)
        after = tickets_gate(root, after_queue)
        assert not [v for v in after if v.rule == "TICK002"]

    def test_tick002_off_default_branch_is_a_no_op(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine.py::fix_tick002_renumber kind="unit"
        import subprocess

        from frob.gates._fix_engine import fix_tick002_renumber
        from frob.tickets import TicketQueue, TicketState
        from frob.tickets._provisional import mint_draft_id

        root = tmp_path / "repo"
        root.mkdir()

        def _git(*args: str) -> None:
            subprocess.run(
                ["git", "-C", str(root), *args],
                check=True,
                capture_output=True,
                text=True,
            )

        _git("init", "-q", "-b", "feature-branch")
        _git("config", "user.email", "test@example.com")
        _git("config", "user.name", "Test")
        (root / "tickets.md").write_text("# Tickets\n\n", encoding="utf-8")
        _git("add", "-A")
        _git("commit", "-q", "-m", "init")

        draft_id = mint_draft_id()
        draft = Ticket(
            id=draft_id,
            title="draft still in flight",
            state=TicketState.QUEUED,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
        )
        queue = TicketQueue(tickets={draft_id: draft})
        applied = fix_tick002_renumber(root, queue)
        assert applied == []

    def test_tick002_dropped_draft_is_exempt(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_tickets_gate.py::_tick002_draft_on_default \
        # kind="unit"
        # T-1917: a dropped draft archived in the SAME commit it was
        # filed in (no live state ever existed to renumber out of --
        # `fix_tick002_renumber` has nothing to promote) must not trip
        # this rule forever. Real repro: tickets/archive/T-draft-d718d443
        # on this repo's own `main`.
        import subprocess

        from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState
        from frob.tickets._provisional import mint_draft_id

        root = tmp_path / "repo"
        root.mkdir()

        def _git(*args: str) -> None:
            subprocess.run(
                ["git", "-C", str(root), *args],
                check=True,
                capture_output=True,
                text=True,
            )

        _git("init", "-q", "-b", "main")
        _git("config", "user.email", "test@example.com")
        _git("config", "user.name", "Test")
        (root / "tickets.md").write_text("# Tickets\n\n", encoding="utf-8")
        (root / "tickets-archive.md").write_text("# Archive\n\n", encoding="utf-8")
        _git("add", "-A")
        _git("commit", "-q", "-m", "init")

        draft_id = mint_draft_id()
        draft = Ticket(
            id=draft_id,
            title="residue draft, dropped and archived directly",
            state=TicketState.DROPPED,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
        )
        queue = TicketQueue(tickets={draft_id: draft})

        violations = tickets_gate(root, queue)

        assert not [v for v in violations if v.rule == "TICK002"]

    def test_tick002_done_draft_still_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_tickets_gate.py::_tick002_draft_on_default \
        # kind="unit"
        # T-1917: the DROPPED exemption must not swallow the real
        # promotion-failure shape -- a draft that reached `done` without
        # ever being renumbered to a real id is exactly what TICK002
        # exists to catch, and must keep failing loud.
        import subprocess

        from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState
        from frob.tickets._provisional import mint_draft_id

        root = tmp_path / "repo"
        root.mkdir()

        def _git(*args: str) -> None:
            subprocess.run(
                ["git", "-C", str(root), *args],
                check=True,
                capture_output=True,
                text=True,
            )

        _git("init", "-q", "-b", "main")
        _git("config", "user.email", "test@example.com")
        _git("config", "user.name", "Test")
        (root / "tickets.md").write_text("# Tickets\n\n", encoding="utf-8")
        (root / "tickets-archive.md").write_text("# Archive\n\n", encoding="utf-8")
        _git("add", "-A")
        _git("commit", "-q", "-m", "init")

        draft_id = mint_draft_id()
        draft = Ticket(
            id=draft_id,
            title="never promoted before it was marked done",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
        )
        queue = TicketQueue(tickets={draft_id: draft})

        violations = tickets_gate(root, queue)

        assert any(v.rule == "TICK002" for v in violations)

    # -- acceptance: TICK006 phantom draft citation refile+renumber --------

    def _tick006_repo(self, tmp_path: Path):  # noqa: ANN202
        """A repo with one ticket whose Done report affirmatively claims a
        phantom id (never filed, resolves to nothing) -- the TICK006 repro
        every test in this section shares."""
        import subprocess

        root = tmp_path / "repo"
        root.mkdir()

        def _git(*args: str) -> None:
            subprocess.run(
                ["git", "-C", str(root), *args],
                check=True,
                capture_output=True,
                text=True,
            )

        _git("init", "-q", "-b", "main")
        _git("config", "user.email", "test@example.com")
        _git("config", "user.name", "Test")
        (root / "tickets.md").write_text("# Tickets\n\n", encoding="utf-8")
        (root / "tickets-archive.md").write_text("# Archive\n\n", encoding="utf-8")
        _git("add", "-A")
        _git("commit", "-q", "-m", "init")
        return root, _git

    def test_tick006_refiles_and_rewrites_citation(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine.py::fix_tick006_phantom_refile \
        # kind="unit"
        from frob.gates._fix_engine import fix_tick006_phantom_refile
        from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState

        root, _git = self._tick006_repo(tmp_path)
        claiming = Ticket(
            id="T-0001",
            title="claiming ticket",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
            body=(
                "## Done report\n\n"
                "Filed T-draft-deadbeef (recovery ticket for the "
                "phantom-citation incident) as a follow-up.\n"
            ),
        )
        write_result = write_ticket(root, claiming)
        assert write_result.is_ok
        _git("add", "-A")
        _git("commit", "-q", "-m", "file claiming ticket with phantom citation")

        queue = TicketQueue(tickets={"T-0001": claiming})
        before = tickets_gate(root, queue)
        assert any(v.rule == "TICK006" for v in before)

        applied = fix_tick006_phantom_refile(root, queue)
        assert len(applied) == 1
        assert applied[0].rule == "TICK006"
        assert "T-draft-deadbeef" in applied[0].detail

        from frob.tickets._store import load_all

        reloaded = load_all(root)
        assert reloaded.is_ok
        # The claiming ticket's body no longer cites the phantom id.
        rewritten = reloaded.danger_ok["T-0001"]
        assert "T-draft-deadbeef" not in rewritten.body
        # A new real ticket now exists, and IS what the body cites.
        new_ids = set(reloaded.danger_ok) - {"T-0001"}
        assert len(new_ids) == 1
        new_id = next(iter(new_ids))
        assert new_id in rewritten.body
        # The refiled ticket's body quotes the original claim.
        assert "phantom-citation incident" in reloaded.danger_ok[new_id].body

        after_queue = TicketQueue(tickets=reloaded.danger_ok)
        after = tickets_gate(root, after_queue)
        assert not [v for v in after if v.rule == "TICK006"]

    def test_tick006_known_id_is_never_touched(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine.py::fix_tick006_phantom_refile \
        # kind="unit"
        """A `TICK002`-shaped claim (the id DOES exist, just as a draft)
        must never be treated as a TICK006 phantom -- `fix_tick006_
        phantom_refile` is a no-op when nothing it scans is phantom."""
        from frob.gates._fix_engine import fix_tick006_phantom_refile
        from frob.tickets import TicketQueue, TicketState

        root, _git = self._tick006_repo(tmp_path)
        claiming = Ticket(
            id="T-0001",
            title="claiming ticket",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
            body="## Done report\n\nFiled T-0001 as a follow-up.\n",
        )
        write_result = write_ticket(root, claiming)
        assert write_result.is_ok
        _git("add", "-A")
        _git("commit", "-q", "-m", "self-citation, not a phantom")

        queue = TicketQueue(tickets={"T-0001": claiming})
        applied = fix_tick006_phantom_refile(root, queue)
        assert applied == []

    # frob:tests src/frob/gates/_fix_engine.py::fix_tick006_phantom_refile kind="unit"
    def test_tick006_id_on_merge_target_but_not_worktree_is_silent(
        self, tmp_path: Path
    ) -> None:
        """T-2400 must-now-be-silent control: a citation whose id is NOT
        in this worktree's own queue/archive, but IS present in
        `merge_target_ids` (i.e. filed on main after this worktree was
        cut), must not be treated as phantom."""
        from frob.gates._fix_engine import (
            MergeTargetKnownIds,
            fix_tick006_phantom_refile,
        )
        from frob.tickets import TicketQueue, TicketState

        root, _git = self._tick006_repo(tmp_path)
        claiming = Ticket(
            id="T-0001",
            title="claiming ticket",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
            body=("## Done report\n\nFiled T-2388 (sibling fix) as a follow-up.\n"),
        )
        write_result = write_ticket(root, claiming)
        assert write_result.is_ok
        _git("add", "-A")
        _git("commit", "-q", "-m", "cite a ticket that postdates this worktree")

        queue = TicketQueue(tickets={"T-0001": claiming})
        merge_target_ids = MergeTargetKnownIds(ids=frozenset({"T-2388"}), measured=True)
        applied = fix_tick006_phantom_refile(root, queue, merge_target_ids)
        assert applied == []

    # frob:tests src/frob/gates/_fix_engine.py::fix_tick006_phantom_refile kind="unit"
    def test_tick006_genuinely_nonexistent_id_still_fires_with_merge_target(
        self, tmp_path: Path
    ) -> None:
        """T-2400 must-still-fire control: passing `merge_target_ids`
        must not suppress filing for an id genuinely absent from BOTH
        the worktree's own ledger AND the merge target -- proves the fix
        did not simply disable the check."""
        from frob.gates._fix_engine import (
            MergeTargetKnownIds,
            fix_tick006_phantom_refile,
        )
        from frob.tickets import TicketQueue, TicketState

        root, _git = self._tick006_repo(tmp_path)
        claiming = Ticket(
            id="T-0001",
            title="claiming ticket",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
            body=(
                "## Done report\n\nFiled T-draft-deadbeef (recovery ticket) "
                "as a follow-up.\n"
            ),
        )
        write_result = write_ticket(root, claiming)
        assert write_result.is_ok
        _git("add", "-A")
        _git("commit", "-q", "-m", "cite a genuinely phantom id")

        queue = TicketQueue(tickets={"T-0001": claiming})
        merge_target_ids = MergeTargetKnownIds(ids=frozenset({"T-2388"}), measured=True)
        applied = fix_tick006_phantom_refile(root, queue, merge_target_ids)
        assert len(applied) == 1
        assert applied[0].rule == "TICK006"

    # frob:tests src/frob/gates/_fix_engine.py::fix_tick006_phantom_refile kind="unit"
    def test_tick006_not_measured_merge_target_files_nothing(
        self, tmp_path: Path
    ) -> None:
        """T-2400 NOT_MEASURED control: when the merge target's own
        ledger could not be read, the handler must file NOTHING this
        pass rather than guess -- concluding "phantom" from an
        incomplete view is exactly the silent-wrong-answer class
        doctrine T-2391 forbids, even for an id that WOULD otherwise
        look phantom against this worktree's own view alone."""
        from frob.gates._fix_engine import (
            MergeTargetKnownIds,
            fix_tick006_phantom_refile,
        )
        from frob.tickets import TicketQueue, TicketState

        root, _git = self._tick006_repo(tmp_path)
        claiming = Ticket(
            id="T-0001",
            title="claiming ticket",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
            body=("## Done report\n\nFiled T-2388 (sibling fix) as a follow-up.\n"),
        )
        write_result = write_ticket(root, claiming)
        assert write_result.is_ok
        _git("add", "-A")
        _git("commit", "-q", "-m", "cite an id this pass cannot verify")

        queue = TicketQueue(tickets={"T-0001": claiming})
        merge_target_ids = MergeTargetKnownIds(ids=frozenset(), measured=False)
        applied = fix_tick006_phantom_refile(root, queue, merge_target_ids)
        assert applied == []

    # frob:tests src/frob/gates/_fix_engine.py::fix_tick006_phantom_refile kind="unit"
    # frob:waive COV006 reason="T-2550 class: reached only through \
    # fix_tick006_phantom_refile several hops out, a shape build_call_graph \
    # structurally cannot see through; confirmed reachable by direct read"
    # frob:tests src/frob/gates/_fix_engine.py::_resolve_via_git_rename kind="unit"
    def test_tick006_renamed_draft_resolved_via_git_not_refiled(
        self, tmp_path: Path
    ) -> None:
        """T-2690 positive control (1/2): a draft id genuinely renamed
        (`git mv`, what `frob ticket renumber`'s v2 path does) to a real
        id must be resolved via git history and its citation rewritten
        to the real successor -- NOT re-filed as a duplicate. This is
        the dominant false-positive shape T-2690 measured (23/23 triaged
        auto-filings were exactly this)."""
        from frob.gates._fix_engine import fix_tick006_phantom_refile
        from frob.tickets import TicketQueue, TicketState

        root, _git = self._tick006_repo(tmp_path)

        # A draft gets filed, then renamed (git mv) to a real id -- the
        # exact shape `renumber_one_v2` produces on land.
        draft_ticket_md = (
            "---\n"
            "id: T-draft-cafef00d\n"
            "title: recovered elsewhere\n"
            "state: queued\n"
            "kind: bug\n"
            "origin: agent\n"
            "created: '2026-08-01'\n"
            "---\n"
            "body\n"
        )
        (root / "tickets" / "T-draft-cafef00d").mkdir(parents=True)
        (root / "tickets" / "T-draft-cafef00d" / "ticket.md").write_text(
            draft_ticket_md, encoding="utf-8"
        )
        _git("add", "-A")
        _git("commit", "-q", "-m", "file draft T-draft-cafef00d")
        _git("mv", "tickets/T-draft-cafef00d", "tickets/T-9999")
        # `git mv` alone leaves the renamed file's own `id:` frontmatter
        # field stale (real `renumber_one_v2` rewrites it too) -- fix it
        # up so `load_all` at the end of this test can load T-9999 as a
        # valid ticket, matching what a real renumber leaves behind.
        (root / "tickets" / "T-9999" / "ticket.md").write_text(
            draft_ticket_md.replace("T-draft-cafef00d", "T-9999"), encoding="utf-8"
        )
        _git("add", "-A")
        _git("commit", "-q", "-m", "renumber T-draft-cafef00d -> T-9999")

        claiming = Ticket(
            id="T-0001",
            title="claiming ticket",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
            body=(
                "## Done report\n\nFiled T-draft-cafef00d (recovery "
                "ticket) as a follow-up.\n"
            ),
        )
        write_result = write_ticket(root, claiming)
        assert write_result.is_ok
        _git("add", "-A")
        _git("commit", "-q", "-m", "cite the now-renamed draft")

        queue = TicketQueue(tickets={"T-0001": claiming})
        applied = fix_tick006_phantom_refile(root, queue)

        assert len(applied) == 1
        assert applied[0].rule == "TICK006"
        assert "resolved via git rename" in applied[0].detail
        assert "T-9999" in applied[0].detail

        from frob.tickets._store import load_all

        reloaded = load_all(root)
        assert reloaded.is_ok
        # No new ticket was filed -- T-0001 is still the only ticket
        # `load_all` (the active ledger) knows about besides T-9999 was
        # never part of the active ledger to begin with (it lives only
        # as a renamed directory this fixture built by hand), so the
        # real assertion is narrower and load-bearing: no THIRD id
        # (a spurious "Recovered from ..." refile) exists.
        assert "T-draft-cafef00d" not in reloaded.danger_ok
        assert "T-9999" in reloaded.danger_ok["T-0001"].body
        assert "T-draft-cafef00d" not in reloaded.danger_ok["T-0001"].body

    # frob:tests src/frob/gates/_fix_engine.py::fix_tick006_phantom_refile kind="unit"
    def test_tick006_genuinely_lost_draft_still_caught_no_rename_no_duplicate(
        self, tmp_path: Path
    ) -> None:
        """T-2690 negative control: a `tid` with NO git rename record and
        NO existing recovery ticket must still be refiled exactly as
        before -- proves neither new check (git-rename resolution,
        duplicate-recovery reuse) made the detector blind to a real
        loss, only to the two false-positive shapes T-2690 measured."""
        from frob.gates._fix_engine import fix_tick006_phantom_refile
        from frob.tickets import TicketQueue, TicketState

        root, _git = self._tick006_repo(tmp_path)
        claiming = Ticket(
            id="T-0001",
            title="claiming ticket",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
            body=(
                "## Done report\n\nFiled T-draft-105af0be (genuinely lost "
                "work, never merged anywhere) as a follow-up.\n"
            ),
        )
        write_result = write_ticket(root, claiming)
        assert write_result.is_ok
        _git("add", "-A")
        _git("commit", "-q", "-m", "cite a genuinely never-existed draft")

        queue = TicketQueue(tickets={"T-0001": claiming})
        applied = fix_tick006_phantom_refile(root, queue)

        assert len(applied) == 1
        assert applied[0].rule == "TICK006"
        assert "refiled" in applied[0].detail
        assert "resolved via git rename" not in applied[0].detail
        assert "already recovered" not in applied[0].detail

    # frob:tests src/frob/gates/_fix_engine.py::fix_tick006_phantom_refile kind="unit"
    def test_tick006_already_recovered_citation_rewritten_not_refiled_again(
        self, tmp_path: Path
    ) -> None:
        """T-2690 positive control (2/2): a phantom whose recovery ticket
        already exists (an earlier pass filed it, but never rewrote THIS
        citing ticket's own body -- e.g. because the citing ticket had
        already landed/closed by the time the first recovery happened)
        must have its citation rewritten to the EXISTING recovery ticket,
        never attempt a second `new_ticket` call -- this is the exact
        "refusing to file ... already has this exact title" noise a
        coordinator once misdiagnosed as land contention."""
        from frob.gates._fix_engine import fix_tick006_phantom_refile
        from frob.tickets import TicketQueue, TicketState

        root, _git = self._tick006_repo(tmp_path)
        claiming = Ticket(
            id="T-0001",
            title="claiming ticket",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
            body=(
                "## Done report\n\nFiled T-draft-abc12345 (already "
                "recovered elsewhere) as a follow-up.\n"
            ),
        )
        # The recovery ticket an EARLIER pass already filed for this
        # exact phantom -- same deterministic title
        # `_tick006_refile_ticket_spec` would build.
        recovery = Ticket(
            id="T-0002",
            title=(
                "Recovered from T-0001's phantom TICK006 citation of T-draft-abc12345"
            ),
            state=TicketState.QUEUED,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
            body="Auto-filed by an earlier pass.",
        )
        write_ticket(root, claiming)
        write_ticket(root, recovery)
        _git("add", "-A")
        _git("commit", "-q", "-m", "citing ticket plus its own already-filed recovery")

        queue = TicketQueue(tickets={"T-0001": claiming, "T-0002": recovery})
        applied = fix_tick006_phantom_refile(root, queue)

        assert len(applied) == 1
        assert applied[0].rule == "TICK006"
        assert "already recovered" in applied[0].detail
        assert "T-0002" in applied[0].detail

        from frob.tickets._store import load_all

        reloaded = load_all(root)
        assert reloaded.is_ok
        # No THIRD ticket was filed -- still exactly T-0001 and T-0002.
        assert set(reloaded.danger_ok) == {"T-0001", "T-0002"}
        assert "T-0002" in reloaded.danger_ok["T-0001"].body
        assert "T-draft-abc12345" not in reloaded.danger_ok["T-0001"].body

    # frob:tests src/frob/gates/_fix_engine.py::fix_tick006_phantom_refile kind="unit"
    def test_tick006_ticket_id_scopes_to_landing_ticket_only(
        self, tmp_path: Path
    ) -> None:
        """T-2690 positive control: when `ticket_id` names the ticket
        actually landing, an UNRELATED ticket's own phantom citation
        (T-0002's, not T-0001's -- the one this land has nothing to do
        with) must be left completely untouched -- proves a land no
        longer processes, and cannot be blocked or spammed by, another
        ticket's stale citation. `ticket_id=None` (the bare `frob check
        --fix` default) still processes the whole queue, unchanged."""
        from frob.gates._fix_engine import fix_tick006_phantom_refile
        from frob.tickets import TicketQueue, TicketState

        root, _git = self._tick006_repo(tmp_path)
        landing = Ticket(
            id="T-0001",
            title="the ticket actually landing",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
            body="## Done report\n\nNo phantom citation here at all.\n",
        )
        unrelated = Ticket(
            id="T-0002",
            title="an unrelated ticket with its own phantom",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
            body=("## Done report\n\nFiled T-draft-face0001 as a follow-up.\n"),
        )
        write_ticket(root, landing)
        write_ticket(root, unrelated)
        _git("add", "-A")
        _git("commit", "-q", "-m", "two tickets, only one with a phantom citation")

        queue = TicketQueue(tickets={"T-0001": landing, "T-0002": unrelated})

        # Scoped to the landing ticket (T-0001): T-0002's own phantom
        # citation must be left alone entirely -- no filing, no error,
        # no touch.
        scoped_applied = fix_tick006_phantom_refile(root, queue, ticket_id="T-0001")
        assert scoped_applied == []

        from frob.tickets._store import load_all

        reloaded = load_all(root)
        assert reloaded.is_ok
        assert "T-draft-face0001" in reloaded.danger_ok["T-0002"].body
        assert set(reloaded.danger_ok) == {"T-0001", "T-0002"}

        # Unscoped (ticket_id=None, the bare `frob check --fix` shape)
        # still processes the whole queue, unchanged from before T-2690.
        unscoped_applied = fix_tick006_phantom_refile(root, queue)
        assert len(unscoped_applied) == 1
        assert unscoped_applied[0].rule == "TICK006"

    # -- T-2702: T-2690's own fix does not fire on the real land path ------
    #
    # T-2699/T-2701 (measured 2026-08-19): a phantom draft citation was
    # auto-refiled TWICE, by two separate lands, BOTH of which contained
    # T-2690's fix. Root cause A: `_resolve_via_git_rename`'s underlying
    # git spawn CAN fail/time out under real concurrent-land git
    # contention, and T-2690 collapsed that failure into the identical
    # `None` a genuine non-rename returns -- unsafe, and explicitly
    # contradicts this same module's `MergeTargetKnownIds.measured=False`
    # doctrine everywhere else. Root cause B: `_find_exact_duplicate`
    # read only the calling land's own (possibly stale, pre-cut)
    # worktree ledger, missing a byte-identical recovery ticket a
    # SIBLING land had already filed on the real merge target seconds to
    # minutes earlier. Both are fixed in `_resolve_via_git_rename_measured`
    # / `_tick006_try_resolve_without_filing` -- these tests exercise the
    # REAL failure shapes (a genuinely failing git spawn; a second,
    # independently-rooted "sibling worktree" ledger), not just the
    # function in isolation with a clean git repo, which is exactly what
    # let T-2690's own four unit tests pass while production re-filed.

    def test_tick006_git_rename_lookup_failure_files_nothing_never_treated_as_confirmed_non_rename(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """T-2702 positive control: a REAL renamed draft (same fixture
        shape as `test_tick006_renamed_draft_resolved_via_git_not_
        refiled`), but the underlying git spawn `_resolve_via_git_
        rename_measured` makes is forced to fail (simulating the
        T-2699/T-2701 incident's own concurrent-load timeout) --
        `fix_tick006_phantom_refile` must file NOTHING and rewrite
        NOTHING this pass, not silently treat the failure as "confirmed,
        not a rename" and fall through to `new_ticket`."""
        from typani import Err

        import frob.gitio as gitio_mod
        from frob.gates._fix_engine import fix_tick006_phantom_refile
        from frob.tickets import TicketQueue, TicketState

        root, _git = self._tick006_repo(tmp_path)
        draft_ticket_md = (
            "---\n"
            "id: T-draft-cafef00e\n"
            "title: recovered elsewhere\n"
            "state: queued\n"
            "kind: bug\n"
            "origin: agent\n"
            "created: '2026-08-01'\n"
            "---\n"
            "body\n"
        )
        (root / "tickets" / "T-draft-cafef00e").mkdir(parents=True)
        (root / "tickets" / "T-draft-cafef00e" / "ticket.md").write_text(
            draft_ticket_md, encoding="utf-8"
        )
        _git("add", "-A")
        _git("commit", "-q", "-m", "file draft T-draft-cafef00e")
        _git("mv", "tickets/T-draft-cafef00e", "tickets/T-9998")
        (root / "tickets" / "T-9998" / "ticket.md").write_text(
            draft_ticket_md.replace("T-draft-cafef00e", "T-9998"), encoding="utf-8"
        )
        _git("add", "-A")
        _git("commit", "-q", "-m", "renumber T-draft-cafef00e -> T-9998")

        claiming = Ticket(
            id="T-0001",
            title="claiming ticket",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
            body=(
                "## Done report\n\nFiled T-draft-cafef00e (recovery "
                "ticket) as a follow-up.\n"
            ),
        )
        write_ticket(root, claiming)
        _git("add", "-A")
        _git("commit", "-q", "-m", "cite the now-renamed draft")

        from frob.gitio import GitError

        def _always_fail(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
            return Err(GitError.GitFailed)

        monkeypatch.setattr(gitio_mod, "run_argv", _always_fail)

        queue = TicketQueue(tickets={"T-0001": claiming})
        applied = fix_tick006_phantom_refile(root, queue)

        assert applied == []

        from frob.tickets._store import load_all

        reloaded = load_all(root)
        assert reloaded.is_ok
        # Neither rewritten to T-9998 NOR refiled as a new duplicate --
        # the citation is untouched, exactly as it was before this pass.
        assert "T-draft-cafef00e" in reloaded.danger_ok["T-0001"].body
        # T-9998 is the fixture's own already-renamed draft (a real,
        # loadable ticket regardless of this test) -- the load-bearing
        # assertion is that no THIRD, spurious "Recovered from ..."
        # ticket was filed.
        assert set(reloaded.danger_ok) == {"T-0001", "T-9998"}

    def test_tick006_lookup_failure_then_clean_retry_recovers_correctly(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """T-2702: the previous test's failure mode must be RECOVERABLE,
        not a permanent block -- once the git spawn stops failing (the
        next land, after contention clears), the SAME citation resolves
        correctly via the real rename. Proves this fix does not trade
        the false-positive-refile incident for a false-negative
        never-resolves regression."""
        from typani import Err

        import frob.gitio as gitio_mod
        from frob.gates._fix_engine import fix_tick006_phantom_refile
        from frob.gitio import GitError
        from frob.tickets import TicketQueue, TicketState

        root, _git = self._tick006_repo(tmp_path)
        draft_ticket_md = (
            "---\n"
            "id: T-draft-cafef00f\n"
            "title: recovered elsewhere\n"
            "state: queued\n"
            "kind: bug\n"
            "origin: agent\n"
            "created: '2026-08-01'\n"
            "---\n"
            "body\n"
        )
        (root / "tickets" / "T-draft-cafef00f").mkdir(parents=True)
        (root / "tickets" / "T-draft-cafef00f" / "ticket.md").write_text(
            draft_ticket_md, encoding="utf-8"
        )
        _git("add", "-A")
        _git("commit", "-q", "-m", "file draft T-draft-cafef00f")
        _git("mv", "tickets/T-draft-cafef00f", "tickets/T-9997")
        (root / "tickets" / "T-9997" / "ticket.md").write_text(
            draft_ticket_md.replace("T-draft-cafef00f", "T-9997"), encoding="utf-8"
        )
        _git("add", "-A")
        _git("commit", "-q", "-m", "renumber T-draft-cafef00f -> T-9997")

        claiming = Ticket(
            id="T-0001",
            title="claiming ticket",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
            body=(
                "## Done report\n\nFiled T-draft-cafef00f (recovery "
                "ticket) as a follow-up.\n"
            ),
        )
        write_ticket(root, claiming)
        _git("add", "-A")
        _git("commit", "-q", "-m", "cite the now-renamed draft")

        real_run_argv = gitio_mod.run_argv
        monkeypatch.setattr(
            gitio_mod, "run_argv", lambda *a, **kw: Err(GitError.GitFailed)
        )
        queue = TicketQueue(tickets={"T-0001": claiming})
        first_pass = fix_tick006_phantom_refile(root, queue)
        assert first_pass == []

        monkeypatch.setattr(gitio_mod, "run_argv", real_run_argv)
        from frob.tickets._store import load_all

        queue2 = TicketQueue(tickets={"T-0001": load_all(root).danger_ok["T-0001"]})
        second_pass = fix_tick006_phantom_refile(root, queue2)
        assert len(second_pass) == 1
        assert "resolved via git rename" in second_pass[0].detail
        assert "T-9997" in second_pass[0].detail

        reloaded = load_all(root)
        assert reloaded.is_ok
        assert "T-9997" in reloaded.danger_ok["T-0001"].body
        assert "T-draft-cafef00f" not in reloaded.danger_ok["T-0001"].body
        assert set(reloaded.danger_ok) == {"T-0001", "T-9997"}

    def test_tick006_two_lands_citing_same_draft_produce_at_most_one_ticket(
        self, tmp_path: Path
    ) -> None:
        """T-2702 mandatory control (3/3): two lands, in SEPARATE
        worktrees, both citing the SAME genuinely-lost draft in quick
        succession -- the exact T-2699/T-2701 shape (T-2141's land and
        T-2251's land, ~31 minutes apart, T-2251's own worktree ledger
        cut before T-2141's land's recovery ticket existed on main).
        The SECOND land's worktree `root` alone would miss the FIRST
        land's just-filed ticket (title+scope are byte-identical,
        exactly what makes this a duplicate at all) -- passing
        `merge_target_ids.root` pointed at the real, live merge target
        must catch it anyway. At most ONE recovery ticket must exist
        after both lands run, never two."""
        import subprocess

        from frob.gates._fix_engine import (
            MergeTargetKnownIds,
            fix_tick006_phantom_refile,
        )
        from frob.tickets import TicketQueue, TicketState
        from frob.tickets._store import load_all

        (tmp_path / "main").mkdir()
        main_root, _git_main = self._tick006_repo(tmp_path / "main")

        # Land A's own claiming ticket, citing a genuinely lost draft --
        # no rename record anywhere, so this is the "real recovery"
        # shape, not the rename-resolution shape the tests above cover.
        claiming_a = Ticket(
            id="T-0001",
            title="land A's claiming ticket",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
            body="## Done report\n\nFiled T-draft-5eedca5e as a follow-up.\n",
        )
        write_ticket(main_root, claiming_a)
        _git_main("add", "-A")
        _git_main("commit", "-q", "-m", "land A: cite the shared phantom")

        # Clone main's CURRENT state (before land A's own Tier-A pass
        # runs) as land B's own SEPARATE worktree -- this is the stale
        # snapshot: it will never see land A's own recovery-ticket
        # filing unless it re-merges, exactly like a real worktree that
        # was cut before a sibling's land landed.
        worktree_root = tmp_path / "worktree_b"
        subprocess.run(
            ["git", "clone", "-q", str(main_root), str(worktree_root)], check=True
        )
        subprocess.run(
            ["git", "-C", str(worktree_root), "config", "user.email", "t@example.com"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(worktree_root), "config", "user.name", "t"], check=True
        )

        # Land A runs for real, against `main_root` directly (root ==
        # merge target for this call, matching `_apply_root_tier_a_fixes`'s
        # own post-land shape) -- files the one real recovery ticket.
        queue_a = TicketQueue(tickets={"T-0001": claiming_a})
        applied_a = fix_tick006_phantom_refile(main_root, queue_a, ticket_id="T-0001")
        assert len(applied_a) == 1
        assert "refiled" in applied_a[0].detail

        after_a = load_all(main_root)
        assert after_a.is_ok
        assert len(after_a.danger_ok) == 2  # T-0001 + the new recovery ticket

        # Land B's own claiming ticket -- SAME phantom, byte-identical
        # title (both quote the same excerpt from the same phantom id,
        # `_tick006_refile_ticket_spec`'s title is fully deterministic
        # off `(ticket.id, tid)` -- different `ticket.id` here (T-0002
        # vs T-0001) deliberately makes the RECOVERY ticket's title
        # differ too, matching T-2699/T-2701's real shape where each
        # recovery ticket's title cites ITS OWN claiming ticket
        # (T-2685 in both real cases) -- so make land B's claiming
        # ticket look like it is quoting the SAME originating ticket, by
        # using the SAME claiming id T-0001's own content directly: land
        # B is a second, stale-mirrored VIEW of the SAME land, not a
        # different one, matching the real incident (the citation lived
        # in T-2685's OWN done report, unrelated to which land's own
        # Tier-A pass happened to scan it).
        worktree_queue_ticket = load_all(worktree_root).danger_ok["T-0001"]
        queue_b = TicketQueue(tickets={"T-0001": worktree_queue_ticket})
        merge_target_ids = MergeTargetKnownIds(
            ids=frozenset(after_a.danger_ok), measured=True, root=main_root
        )
        applied_b = fix_tick006_phantom_refile(
            worktree_root,
            queue_b,
            merge_target_ids=merge_target_ids,
            ticket_id="T-0001",
        )

        # Land B must NOT file a second duplicate -- either it resolves
        # (rewrite-only, citation pointed at land A's already-filed
        # ticket) or, at worst, is a no-op; either way NOTHING with
        # `"refiled"` in its detail may appear.
        assert not any("(refiled," in a.detail for a in applied_b)

        after_b = load_all(main_root)
        assert after_b.is_ok
        recovery_tickets = [
            t
            for t in after_b.danger_ok.values()
            if t.id not in ("T-0001",) and "Recovered from" in t.title
        ]
        assert len(recovery_tickets) == 1, (
            f"expected at most one recovery ticket after two lands citing "
            f"the same draft, got {len(recovery_tickets)}: "
            f"{[t.id for t in recovery_tickets]}"
        )

    # -- SYS111 capability-ratchet lock sync (T-2001) ----------------------

    def _init_git_repo(self, root: Path) -> None:
        """A real git repo (T-2001's SYS111 handler diffs against `git
        show HEAD`, unlike every other Tier-A handler in this class --
        a plain `tmp_path` with no `.git` is not enough)."""
        import subprocess

        subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
        subprocess.run(
            ["git", "-C", str(root), "config", "user.email", "t@example.com"],
            check=True,
        )
        subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)

    def _commit_all(self, root: Path, message: str) -> None:
        import subprocess

        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(root), "commit", "-q", "-m", message], check=True
        )

    def _write_ratchet_lock(self, root: Path, entries: dict) -> None:
        import json

        registry = root / "docs" / "design" / "registry"
        registry.mkdir(parents=True, exist_ok=True)
        (registry / "capability-via-ratchet.lock.json").write_text(
            json.dumps({"entries": entries, "schema_version": 1}, indent=2) + "\n",
            encoding="utf-8",
        )

    def _write_strata(self, root: Path, via_files: tuple[str, ...]) -> None:
        (root / "design").mkdir(parents=True, exist_ok=True)
        via = ", ".join(f'"{f}"' for f in via_files)
        (root / "design" / "api.strata").write_text(
            f'module api\nnode Api : trusted {{\n    code "app/**";\n'
            f'    may "fs.write" via {via};\n}}\n',
            encoding="utf-8",
        )

    # frob:ticket T-2001
    def test_sys111_bumps_growth_this_lands_diff_caused(self, tmp_path: Path) -> None:
        # frob:tests tests/gates_suite/test_fix_engine.py::TestFixEngineTierA.test_sys111_bumps_growth_this_lands_diff_caused  # noqa: E501
        """Acceptance [1]: the handler bumps the lock in the SAME land as
        the strata via-list change, so both places move together."""
        from frob.gates._fix_engine_sync import fix_sys111_capability_ratchet_sync

        root = tmp_path / "repo"
        root.mkdir()
        (root / "app").mkdir()
        (root / "app" / "a.py").write_text('open("x", "w")\n', encoding="utf-8")
        self._write_strata(root, ("app/a.py",))
        self._write_ratchet_lock(
            root, {"Api::fs.write": {"accepted_count": 1, "reason": "T-0000 baseline"}}
        )
        self._init_git_repo(root)
        self._commit_all(root, "init: 1 via site, ceiling at 1")

        # simulate SYS100's own auto-fix widening the via-list, uncommitted,
        # in THIS land -- exactly the shape T-1977/T-1665 measured.
        self._write_strata(root, ("app/a.py", "app/b.py"))

        applied = fix_sys111_capability_ratchet_sync(root)
        assert len(applied) == 1
        assert applied[0].rule == "SYS111"
        assert "1 -> 2" in applied[0].detail

        import json

        lock = json.loads(
            (
                root
                / "docs"
                / "design"
                / "registry"
                / "capability-via-ratchet.lock.json"
            ).read_text(encoding="utf-8")
        )
        assert lock["entries"]["Api::fs.write"]["accepted_count"] == 2
        assert lock["entries"]["Api::fs.write"]["reason"]

    # frob:ticket T-2284
    def test_sys111_ratchet_bump_still_applies_through_scope_lease_filter(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine_scope.py::filter_fixes_by_scope_and_lease  # noqa: E501
        """T-2284's MUST-STILL-PASS control: run the SAME SYS111 ratchet
        bump through `apply_tier_a_fixes`'s full dispatch loop (not the
        handler directly, unlike the test above) with a real landing
        ticket whose scope covers the lock file -- the fix must still
        apply and land in `applied`, exactly as before T-2284."""
        from frob.gates import apply_tier_a_fixes

        root = tmp_path / "repo"
        root.mkdir()
        (root / "app").mkdir()
        (root / "app" / "a.py").write_text('open("x", "w")\n', encoding="utf-8")
        self._write_strata(root, ("app/a.py",))
        self._write_ratchet_lock(
            root, {"Api::fs.write": {"accepted_count": 1, "reason": "T-0000 baseline"}}
        )
        self._init_git_repo(root)
        self._commit_all(root, "init: 1 via site, ceiling at 1")
        self._write_strata(root, ("app/a.py", "app/b.py"))

        landing = _ticket(
            ticket_id="T-2284",
            state=TicketState.IN_PROGRESS,
            scope=("docs/design/**",),
        )
        queue = TicketQueue(tickets={"T-2284": landing})
        snapshot = build_graph(root, root / ".frob" / "cache.db").danger_ok

        applied = apply_tier_a_fixes(
            root, snapshot, queue, exclude=("COV002",), ticket_id="T-2284"
        )

        assert any(a.rule == "SYS111" for a in applied)
        import json

        lock = json.loads(
            (
                root
                / "docs"
                / "design"
                / "registry"
                / "capability-via-ratchet.lock.json"
            ).read_text(encoding="utf-8")
        )
        assert lock["entries"]["Api::fs.write"]["accepted_count"] == 2

    # frob:ticket T-2001
    def test_sys111_leaves_a_pre_existing_breach_untouched(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/gates_suite/test_fix_engine.py::TestFixEngineTierA.test_sys111_leaves_a_pre_existing_breach_untouched  # noqa: E501
        """Acceptance [3]: growth NOT attributable to the landing diff (the
        ceiling is already exceeded before the land begins, and nothing in
        this land's own diff touches it further) must still fail rather
        than be silently ratified."""
        from frob.gates._fix_engine_sync import fix_sys111_capability_ratchet_sync

        root = tmp_path / "repo"
        root.mkdir()
        (root / "app").mkdir()
        (root / "app" / "a.py").write_text('open("x", "w")\n', encoding="utf-8")
        # 3 via sites already committed, ceiling stuck at 1 -- a
        # pre-existing breach that predates this "land" entirely.
        self._write_strata(root, ("app/a.py", "app/b.py", "app/c.py"))
        self._write_ratchet_lock(
            root, {"Api::fs.write": {"accepted_count": 1, "reason": "T-0000 baseline"}}
        )
        self._init_git_repo(root)
        self._commit_all(root, "already 3 via sites, ceiling never moved")

        applied = fix_sys111_capability_ratchet_sync(root)
        assert applied == []

        import json

        lock = json.loads(
            (
                root
                / "docs"
                / "design"
                / "registry"
                / "capability-via-ratchet.lock.json"
            ).read_text(encoding="utf-8")
        )
        assert lock["entries"]["Api::fs.write"]["accepted_count"] == 1

        from frob.strata import merge_models
        from frob.strata._design_load import load_design_ids
        from frob.strata._effects import capability_ratchet_violations

        ids = load_design_ids(root, "design")
        model = merge_models(ids.models)
        violations = capability_ratchet_violations(model, root)
        assert any(v.node == "Api" and v.atom == "fs.write" for v in violations)

    # frob:ticket T-2001
    def test_sys111_no_design_dir_is_a_no_op(self, tmp_path: Path) -> None:
        # frob:tests tests/gates_suite/test_fix_engine.py::TestFixEngineTierA.test_sys111_no_design_dir_is_a_no_op  # noqa: E501
        from frob.gates._fix_engine_sync import fix_sys111_capability_ratchet_sync

        root = tmp_path / "repo"
        root.mkdir()
        self._init_git_repo(root)
        (root / "readme.txt").write_text("x\n", encoding="utf-8")
        self._commit_all(root, "init")
        assert fix_sys111_capability_ratchet_sync(root) == []

    # frob:ticket T-2101
    def test_sys111_before_snapshot_excludes_litmus_like_the_live_tree(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/gates_suite/test_fix_engine.py::TestFixEngineTierA.test_sys111_before_snapshot_excludes_litmus_like_the_live_tree  # noqa: E501
        """T-2101: `_capability_counts_at_head`'s `git archive`-based BEFORE
        snapshot only archived `design/`, never `frob.toml` -- so the
        scratch extraction had no `[graph].exclude` configuration and
        `design/litmus/**` (deliberately id-colliding fixture pairs, e.g.
        two files both declaring node `dup`) leaked into the merged
        `load_design_ids` call and failed closed with `DuplicateId`,
        logged at ERROR on every land. The live/current-tree
        `load_design_ids` call (used elsewhere, e.g. the running handler's
        own `current_ids`) already excludes `design/litmus/**` correctly
        via the SAME `frob.toml` sitting at the real repo root -- the
        scratch BEFORE snapshot must match that, not silently drop the
        config. Reproduces the exact defect shape (two design files
        sharing a node id, `frob.toml` declaring them excluded) rather
        than frob's own real litmus fixtures, to stay a minimal, fast,
        hermetic unit test."""
        from frob.gates._fix_engine_sync import _capability_counts_at_head

        root = tmp_path / "repo"
        root.mkdir()
        (root / "app").mkdir()
        (root / "app" / "a.py").write_text('open("x", "w")\n', encoding="utf-8")
        self._write_strata(root, ("app/a.py",))
        (root / "design" / "litmus").mkdir(parents=True)
        (root / "design" / "litmus" / "one.strata").write_text(
            'module one\nnode dup : trusted {\n    code "one/**";\n}\n',
            encoding="utf-8",
        )
        (root / "design" / "litmus" / "two.strata").write_text(
            'module two\nnode dup : trusted {\n    code "two/**";\n}\n',
            encoding="utf-8",
        )
        (root / "frob.toml").write_text(
            '[graph]\nexclude = ["design/litmus/**"]\n', encoding="utf-8"
        )
        self._init_git_repo(root)
        self._commit_all(root, "init: excluded litmus pair shares a node id")

        counts = _capability_counts_at_head(root)
        assert counts is not None
        assert counts != {}



# frob:ticket T-1348
# frob:ticket T-1548
class TestAutofixManifest:
    """`frob.gates._fix_engine`'s T-1348 recovery breadcrumb: `apply_tier_a_
    fixes` records every path it rewrites, incrementally, under
    `.frob/land-autofix-manifest.json`, and clears it on a clean finish."""

    # frob:ticket T-1348
    def _snap(self, root: Path):

        return build_graph(root, root / ".frob" / "cache.db").danger_ok

    # frob:ticket T-1348
    def test_write_then_clear_roundtrip(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/gates_suite/test_fix_engine.py::TestAutofixManifest.test_write_then_cle\
        # ar_roundtrip
        from frob.gates._fix_engine import FixApplied
        from frob.gates._fix_engine_shared import (
            _autofix_manifest_path,
            clear_autofix_manifest,
            write_autofix_manifest,
        )

        applied = [
            FixApplied(rule="DOC007", file="a.py", line=1, detail="x"),
            FixApplied(rule="DOC007", file="b.py", line=2, detail="y"),
        ]
        write_autofix_manifest(tmp_path, applied)
        manifest_path = _autofix_manifest_path(tmp_path)
        assert manifest_path.is_file()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert data["rewritten_paths"] == ["a.py", "b.py"]
        assert data["fix_count"] == 2

        clear_autofix_manifest(tmp_path)
        assert not manifest_path.is_file()
        # clearing an already-absent manifest is a no-op, not an error
        clear_autofix_manifest(tmp_path)

    # frob:ticket T-1657
    def test_clear_autofix_manifest_swallows_oserror(self, tmp_path: Path) -> None:
        # frob:tests tests/gates_suite/test_fix_engine.py::TestAutofixManifest.test_clear_autofix_manifest_swallows_oserror  # noqa: E501
        """A manifest path that is actually a DIRECTORY (not a file) makes
        `Path.unlink()` raise `IsADirectoryError` (an `OSError` subclass,
        not `FileNotFoundError`) -- the documented contract is that this
        is swallowed too (best-effort recovery aid, not load-bearing
        state), never raised to the caller."""
        from frob.gates._fix_engine_shared import (
            _autofix_manifest_path,
            clear_autofix_manifest,
        )

        manifest_path = _autofix_manifest_path(tmp_path)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.mkdir()  # a directory where a file is expected
        assert manifest_path.is_dir()

        clear_autofix_manifest(tmp_path)  # must not raise

        # the OSError path leaves the (undeletable-as-a-file) directory
        # in place -- it was never able to unlink it, and it does not
        # escalate that failure.
        assert manifest_path.is_dir()

    # frob:ticket T-1348
    def test_apply_tier_a_fixes_clears_manifest_on_clean_finish(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/gates_suite/test_fix_engine.py::TestAutofixManifest.test_apply_tier_a_fixes_clears_manifest_on_clean_finish  # noqa: E501
        from frob.gates import apply_tier_a_fixes
        from frob.gates._fix_engine_shared import _autofix_manifest_path
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "src" / "pkg").mkdir(parents=True)
        (root / "src" / "pkg" / "mod.py").write_text(
            "# frob:tests tests/test_mod.py::TestX::test_y\ndef real():\n    pass\n",
            encoding="utf-8",
        )
        snapshot = self._snap(root)
        apply_tier_a_fixes(root, snapshot, TicketQueue(tickets={}))
        assert not _autofix_manifest_path(root).is_file()

    # frob:ticket T-1548
    # frob:ticket T-1348
    def test_killed_mid_handler_leaves_manifest_naming_completed_fixes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/gates_suite/test_fix_engine.py::TestAutofixManifest.test_killed_mid_handler_leaves_manifest_naming_completed_fixes  # noqa: E501
        """T-1348 acceptance [1]: after a land killed mid-Tier-A, an agent
        can identify exactly which paths were rewritten (here: none yet,
        since the very first handler in TIER_A_HANDLERS order raises
        before completing) without discarding its own uncommitted work."""
        import frob.gates._fix_engine as fix_engine
        from frob.gates import apply_tier_a_fixes
        from frob.gates._fix_engine_shared import _autofix_manifest_path
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        root.mkdir(parents=True)

        # T-3034: was `_boom(root, snapshot, queue, ticket_id=None)` --
        # `apply_tier_a_fixes` now calls every handler with a 5th
        # positional arg (`merge_target_ids`), added after this test was
        # written; the fake handler's signature drifted from the real
        # call site it stands in for.
        def _boom(  # noqa: ANN001, ANN202
            root, snapshot, queue, ticket_id=None, merge_target_ids=None
        ):
            raise RuntimeError("simulated kill mid-handler")

        monkeypatch.setitem(fix_engine.TIER_A_HANDLERS, "DOC007", _boom)
        snapshot = self._snap(root)
        with pytest.raises(RuntimeError, match="simulated kill mid-handler"):
            apply_tier_a_fixes(root, snapshot, TicketQueue(tickets={}))
        # T-3526: apply_tier_a_fixes now writes the manifest ONCE before
        # the loop starts (empty applied list), not only after each
        # handler completes -- so a kill during the very FIRST handler
        # is also detectable as an abandoned state, not just kills after
        # handler N>=1. The manifest therefore legitimately exists here,
        # with an empty rewritten_paths and fix_count=0, even though the
        # first handler raised before completing; the loop never reached
        # clear_autofix_manifest, so this pre-first-mutation journal is
        # exactly the "died mid-phase" state T-1348 describes.
        manifest_path = _autofix_manifest_path(root)
        assert manifest_path.is_file()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["rewritten_paths"] == []
        assert manifest["fix_count"] == 0


# frob:ticket T-1348
class TestTierAAutofixCrashSafety:
    """T-1348 acceptance [0]: a land killed mid-Tier-A-auto-fix must never
    leave a source file half-rewritten. Simulates the actual crash window
    (killed between the temp-file write and the atomic rename) rather
    than merely unit-testing `_write_text` in isolation."""

    # frob:ticket T-1348
    def test_kill_between_write_and_rename_leaves_original_file_intact(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/gates_suite/test_fix_engine.py::TestTierAAutofixCrashSafety.test_kill_between_write_and_rename_leaves_original_file_intact  # noqa: E501

        root = tmp_path / "repo"
        (root / "src" / "pkg").mkdir(parents=True)
        target = root / "src" / "pkg" / "mod.py"
        original = (
            "# frob:tests tests/test_mod.py::TestX::test_y\ndef real():\n    pass\n"
        )
        target.write_text(original, encoding="utf-8")

        # `frob.tickets._store.atomic_write` fsyncs the temp file's data to
        # disk, THEN calls `os.replace` to make it visible under the real
        # path -- the real "process gets killed" window sits exactly
        # between those two steps. Simulating the kill AT that boundary
        # (raising from `os.replace` itself, after the temp file's bytes
        # are already durable) is the worst-case moment for this bug class:
        # if the original survives even here, it survives everywhere
        # earlier in the write too.
        import os as os_module

        real_replace = os_module.replace

        def _kill_before_replace(src, dst, *a, **kw):  # noqa: ANN001, ANN002, ANN003
            if str(dst) == str(target):
                raise OSError("simulated kill: process died before os.replace")
            return real_replace(src, dst, *a, **kw)

        monkeypatch.setattr(os_module, "replace", _kill_before_replace)

        from frob.gates import apply_tier_a_fixes
        from frob.tickets import TicketQueue

        snapshot = build_graph(root, root / ".frob" / "cache.db").danger_ok
        applied = apply_tier_a_fixes(root, snapshot, TicketQueue(tickets={}))

        # the rewrite never landed (DOC007 not in applied) -- correctly
        # reported as not-applied, not silently claimed -- AND the ORIGINAL
        # file is byte-for-byte intact, never garbled/truncated by the
        # interrupted write.
        assert not [a for a in applied if a.rule == "DOC007"]
        assert target.read_text(encoding="utf-8") == original



# frob:ticket T-1548
# frob:ticket T-1261
# frob:ticket T-1341
# frob:ticket T-1763
# frob:ticket T-1924
# frob:ticket T-2922
class TestFixEngineTierABatch2:
    """`frob.gates._fix_engine`'s Tier-A batch-2 `--fix` handlers
    (T-1261): fmt/registry-regen/release-sync/WAIVE004. Each is a
    GIVEN/WHEN/THEN acceptance criterion off this ticket's own body."""

    # -- acceptance [0]: fmt invocation for a FMT001 finding -----------------

    # frob:ticket T-1763
    def test_fmt001_wraps_overlong_directive_line_and_reverifies_clean(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine_text.py::fix_fmt001_directive_wrap \
        # kind="unit"
        from frob.gates._fix_engine import fix_fmt001_directive_wrap
        from frob.gates._fmt_directives import canonicalize_text, read_line_length

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        long_reason = "x" * 100
        original = f'# frob:waive SCOPE001 reason="{long_reason}"\ndef f():\n    pass\n'
        (root / "src" / "m.py").write_text(original, encoding="utf-8")
        limit = read_line_length(root)
        assert any(len(line) > limit for line in original.splitlines())

        applied = fix_fmt001_directive_wrap(root)

        assert len(applied) == 1
        assert applied[0].rule == "FMT001"
        assert applied[0].file == "src/m.py"

        rewritten = (root / "src" / "m.py").read_text(encoding="utf-8")
        assert all(len(line) <= limit for line in rewritten.splitlines())
        # idempotent: canonicalize_text agrees this is already canonical
        assert canonicalize_text(rewritten, path="src/m.py", limit=limit) == rewritten

    def test_fmt001_already_canonical_is_a_no_op(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine_text.py::fix_fmt001_directive_wrap \
        # kind="unit"
        from frob.gates._fix_engine import fix_fmt001_directive_wrap

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        content = "# frob:ticket T-0001\ndef f():\n    pass\n"
        (root / "src" / "m.py").write_text(content, encoding="utf-8")

        applied = fix_fmt001_directive_wrap(root)

        assert applied == []
        assert (root / "src" / "m.py").read_text(encoding="utf-8") == content

    # -- acceptance [1]: REG010 missing gate_rule_entries regeneration ------

    # frob:ticket T-1924
    def test_reg010_files_missing_entries_and_reverifies_clean(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine_sync.py::fix_reg010_registry_sync \
        # kind="unit"
        from frob.gates._fix_engine import fix_reg010_registry_sync
        from frob.registry._staleness import missing_gate_rule_ids

        root = tmp_path / "repo"
        registry_dir = root / "docs" / "design" / "registry"
        registry_dir.mkdir(parents=True)
        fixture = (
            "schema_version: 1\n"
            "gate_rule_total: 1\n"
            "gate_rule_entries:\n"
            '  - id: "CHK-GATE-REF001"\n'
            '    name: "REF001 is a live, enforced gate rule"\n'
            '    disposition: "handled_by:REF001"\n'
            "    cross_refs: []\n"
        )
        registry_path = registry_dir / "check-coverage.yaml"
        registry_path.write_text(fixture, encoding="utf-8")

        monkeypatch.setattr(
            "frob.gates._waive.known_gate_rule_ids",
            lambda: frozenset({"REF001", "DOC007"}),
        )

        applied = fix_reg010_registry_sync(root)

        assert len(applied) == 1
        assert applied[0].rule == "REG010"
        assert applied[0].file == "docs/design/registry/check-coverage.yaml"
        assert "DOC007" in applied[0].detail

        assert (
            missing_gate_rule_ids(registry_path, frozenset({"REF001", "DOC007"}))
            == frozenset()
        )

    # frob:ticket T-1924
    def test_reg010_already_in_sync_is_a_no_op(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine_sync.py::fix_reg010_registry_sync \
        # kind="unit"
        from frob.gates._fix_engine import fix_reg010_registry_sync

        root = tmp_path / "repo"
        registry_dir = root / "docs" / "design" / "registry"
        registry_dir.mkdir(parents=True)
        fixture = (
            "schema_version: 1\n"
            "gate_rule_total: 1\n"
            "gate_rule_entries:\n"
            '  - id: "CHK-GATE-REF001"\n'
            '    name: "REF001 is a live, enforced gate rule"\n'
            '    disposition: "handled_by:REF001"\n'
            "    cross_refs: []\n"
        )
        (registry_dir / "check-coverage.yaml").write_text(fixture, encoding="utf-8")
        monkeypatch.setattr(
            "frob.gates._waive.known_gate_rule_ids", lambda: frozenset({"REF001"})
        )

        applied = fix_reg010_registry_sync(root)
        assert applied == []

    # -- acceptance [1b]: DOCENUM001 enumerates members resync --------------

    # frob:ticket T-1974
    def test_docenum001_fails_before_fix_and_passes_after(self, tmp_path: Path) -> None:
        # frob:tests \
        # src/frob/gates/_fix_engine_sync.py::fix_docenum001_enumerates_sync kind="unit"
        from frob.gates._docenum import docenum001_gate
        from frob.gates._fix_engine import fix_docenum001_enumerates_sync
        from frob.graph._models import Edge, EdgeKind, GraphSnapshot

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "src" / "rules.py").write_text(
            '_KNOWN = frozenset({"A001", "A002", "A003"})\n', encoding="utf-8"
        )
        (root / "docs").mkdir()
        doc_path = root / "docs" / "catalog.md"
        # T-3034: T-2664 added a stricter DOCENUM001 sub-check -- every
        # claimed member also needs a resolvable table row/heading
        # somewhere in the doc, not just an entry in `members=`; this
        # fixture predates that and had none, so the AFTER assertion
        # below started failing on a genuine (WARN-severity, by-design)
        # new finding rather than the sync bug this test targets.
        doc_path.write_text(
            "# catalog\n"
            '<!-- frob:enumerates src/rules.py::_KNOWN members="A001,A002" -->\n'
            "\n"
            "## A001\n"
            "## A002\n"
            "## A003\n",
            encoding="utf-8",
        )

        def _edges() -> tuple[Edge, ...]:
            return (
                Edge(
                    src="docs/catalog.md#catalog",
                    kind=EdgeKind.ENUMERATES,
                    target="src/rules.py::_KNOWN",
                    origin="docs/catalog.md:2",
                    attrs={"members": "A001,A002"},
                ),
            )

        snapshot = GraphSnapshot(root=str(root), symbols={}, edges=_edges())

        # BEFORE: the doc's claimed member list is stale (missing A003) --
        # DOCENUM001 fires.
        before = docenum001_gate(root, snapshot)
        assert any(v.rule == "DOCENUM001" for v in before)

        applied = fix_docenum001_enumerates_sync(root, snapshot)

        assert len(applied) == 1
        assert applied[0].rule == "DOCENUM001"
        assert applied[0].file == "docs/catalog.md"
        rewritten = doc_path.read_text(encoding="utf-8")
        assert 'members="A001,A002,A003"' in rewritten

        # AFTER: re-run the gate against a snapshot reflecting the fixed
        # claim -- clean.
        fixed_snapshot = GraphSnapshot(
            root=str(root),
            symbols={},
            edges=(
                Edge(
                    src="docs/catalog.md#catalog",
                    kind=EdgeKind.ENUMERATES,
                    target="src/rules.py::_KNOWN",
                    origin="docs/catalog.md:2",
                    attrs={"members": "A001,A002,A003"},
                ),
            ),
        )
        after = docenum001_gate(root, fixed_snapshot)
        assert after == ()

    # frob:ticket T-1974
    def test_docenum001_already_in_sync_is_a_no_op(self, tmp_path: Path) -> None:
        # frob:tests \
        # src/frob/gates/_fix_engine_sync.py::fix_docenum001_enumerates_sync kind="unit"
        from frob.gates._fix_engine import fix_docenum001_enumerates_sync
        from frob.graph._models import Edge, EdgeKind, GraphSnapshot

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "src" / "rules.py").write_text(
            '_KNOWN = frozenset({"A001", "A002"})\n', encoding="utf-8"
        )
        (root / "docs").mkdir()
        doc_path = root / "docs" / "catalog.md"
        content = (
            "# catalog\n"
            '<!-- frob:enumerates src/rules.py::_KNOWN members="A001,A002" -->\n'
        )
        doc_path.write_text(content, encoding="utf-8")
        snapshot = GraphSnapshot(
            root=str(root),
            symbols={},
            edges=(
                Edge(
                    src="docs/catalog.md#catalog",
                    kind=EdgeKind.ENUMERATES,
                    target="src/rules.py::_KNOWN",
                    origin="docs/catalog.md:2",
                    attrs={"members": "A001,A002"},
                ),
            ),
        )

        applied = fix_docenum001_enumerates_sync(root, snapshot)

        assert applied == []
        assert doc_path.read_text(encoding="utf-8") == content

    # -- acceptance [2]: REL002 release sync --------------------------------

    # frob:ticket T-1924
    def test_rel002_resyncs_pyproject_and_uv_lock_from_manifest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine_sync.py::fix_rel002_release_sync \
        # kind="unit"
        from frob.gates._fix_engine import fix_rel002_release_sync

        root = tmp_path / "repo"
        root.mkdir()
        (root / ".frob-release.json").write_text(
            '{"version": "1.2.3", "api": {}}', encoding="utf-8"
        )
        (root / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "1.0.0"\n', encoding="utf-8"
        )
        # no uv.lock in this fixture -- `uv lock` is never invoked when the
        # lockfile does not already exist, so this test stays hermetic
        # (no real subprocess spawn).

        applied = fix_rel002_release_sync(root)

        rules_files = {(a.rule, a.file) for a in applied}
        assert ("REL002", "pyproject.toml") in rules_files
        rewritten = (root / "pyproject.toml").read_text(encoding="utf-8")
        assert 'version = "1.2.3"' in rewritten

    # frob:ticket T-1924
    def test_rel002_already_in_sync_touches_nothing(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine_sync.py::fix_rel002_release_sync \
        # kind="unit"
        from frob.gates._fix_engine import fix_rel002_release_sync

        root = tmp_path / "repo"
        root.mkdir()
        (root / ".frob-release.json").write_text(
            '{"version": "1.2.3", "api": {}}', encoding="utf-8"
        )
        original = '[project]\nname = "demo"\nversion = "1.2.3"\n'
        (root / "pyproject.toml").write_text(original, encoding="utf-8")

        applied = fix_rel002_release_sync(root)

        assert not [a for a in applied if a.file == "pyproject.toml"]
        assert (root / "pyproject.toml").read_text(encoding="utf-8") == original

    # -- acceptance [3]: WAIVE004 full-run-verified stale-waiver removal ----

    def test_waive004_removes_stale_waiver_on_a_full_unscoped_run(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine_sync.py::fix_waive004_stale_waiver \
        # kind="unit"
        from frob.gates._fix_engine_sync import fix_waive004_stale_waiver
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        # REF001 (single-inbound-reference) never fires against a file with
        # no cross-package references to it at all, so a REF001 waiver here
        # is genuinely dead -- matches 0 findings on a real full run.
        (root / "src" / "m.py").write_text(
            '# frob:waive REF001 reason="genuinely dead waiver, T-1261 fixture"\n'
            "def f():\n    return 1\n",
            encoding="utf-8",
        )
        (root / "tickets.md").write_text("", encoding="utf-8")
        snapshot = self._snap(root)

        applied = fix_waive004_stale_waiver(root, snapshot, TicketQueue(tickets={}))

        waive004_applied = [a for a in applied if a.rule == "WAIVE004"]
        assert len(waive004_applied) == 1
        rewritten = (root / "src" / "m.py").read_text(encoding="utf-8")
        assert "frob:waive REF001" not in rewritten

    def test_waive004_refuses_a_scoped_run(self, tmp_path: Path) -> None:
        """`gates`/`ticket` set (a scoped run) refuses to act at all --
        the waiver is left untouched, matching this ticket's own
        acceptance criterion 3's second half."""
        # frob:tests src/frob/gates/_fix_engine_sync.py::fix_waive004_stale_waiver \
        # kind="unit"
        from frob.gates._fix_engine_sync import fix_waive004_stale_waiver
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        original = (
            '# frob:waive REF001 reason="genuinely dead waiver, T-1261 fixture"\n'
            "def f():\n    return 1\n"
        )
        (root / "src" / "m.py").write_text(original, encoding="utf-8")
        (root / "tickets.md").write_text("", encoding="utf-8")
        snapshot = self._snap(root)

        applied_gates_scoped = fix_waive004_stale_waiver(
            root, snapshot, TicketQueue(tickets={}), gates=frozenset({"refs"})
        )
        applied_ticket_scoped = fix_waive004_stale_waiver(
            root, snapshot, TicketQueue(tickets={}), ticket="T-0001"
        )

        assert applied_gates_scoped == []
        assert applied_ticket_scoped == []
        assert (root / "src" / "m.py").read_text(encoding="utf-8") == original

    def test_waive004_leaves_a_multi_line_continued_waiver_alone(
        self, tmp_path: Path
    ) -> None:
        """A `\\`-continued waiver is never the single-line shape this
        handler deletes -- Tier A never guesses which physical line of a
        multi-line directive to remove."""
        # frob:tests src/frob/gates/_fix_engine_sync.py::fix_waive004_stale_waiver \
        # kind="unit"
        from frob.gates._fix_engine_sync import fix_waive004_stale_waiver
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        original = (
            '# frob:waive REF001 reason="genuinely dead waiver, \\\n'
            '# continued across two physical lines"\n'
            "def f():\n    return 1\n"
        )
        (root / "src" / "m.py").write_text(original, encoding="utf-8")
        (root / "tickets.md").write_text("", encoding="utf-8")
        snapshot = self._snap(root)

        applied = fix_waive004_stale_waiver(root, snapshot, TicketQueue(tickets={}))

        assert not [a for a in applied if a.rule == "WAIVE004"]
        assert (root / "src" / "m.py").read_text(encoding="utf-8") == original

    # -- TIER_A_HANDLERS dict promotion --------------------------------------

    # frob:ticket T-1548
    def test_tier_a_handlers_dict_covers_every_batch_rule(self) -> None:
        # frob:tests src/frob/gates/_fix_engine.py::TIER_A_HANDLERS kind="unit"
        # frob:ticket T-1341
        # frob:ticket T-2922
        from frob.gates._fix_engine import TIER_A_HANDLERS

        assert set(TIER_A_HANDLERS) == {
            "DOC007",
            "DOC002",
            "FMT001",
            "SUPPRESS001",  # T-1341
            "REG010",
            "REL002",
            "TICK002",
            "WAIVE004",
            # T-2922: SYS100 (T-1531/T-1545) is deleted from this dict --
            # it silently widened a node's may= ceiling to match observed
            # behavior; see src/frob/gates/_fix_engine_sync.py's "SYS100
            # auto-widening -- REMOVED" comment block. SYS100 the
            # detector is unaffected; only the auto-fix is gone.
            # T-1870: SYS104 (T-1531) is deleted from this dict along with
            # the rest of the sync-interface machinery, per an explicit
            # owner directive that no code path may auto-update declared
            # public-symbol surface.
            "E501",  # T-1547
            "COV002",  # T-1548
            "TICK006",  # T-1544
            "DOCENUM001",  # T-1974
            "SYS111",  # T-2001
        }

    def test_apply_tier_a_fixes_dispatches_through_the_handler_dict(
        self, tmp_path: Path
    ) -> None:
        """`apply_tier_a_fixes` still discharges DOC007 the same way it
        did before the T-1261 dict promotion -- the dispatch mechanism
        changed, the observable behavior did not."""
        # frob:tests src/frob/gates/_fix_engine.py::apply_tier_a_fixes kind="unit"
        from frob.gates import apply_tier_a_fixes
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "src" / "pkg").mkdir(parents=True)
        (root / "src" / "pkg" / "mod.py").write_text(
            "# frob:tests tests/test_mod.py::TestX::test_y\ndef real():\n    pass\n",
            encoding="utf-8",
        )
        snapshot = self._snap(root)
        applied = apply_tier_a_fixes(root, snapshot, TicketQueue(tickets={}))
        assert any(a.rule == "DOC007" for a in applied)

    def _snap(self, root: Path):

        return build_graph(root, root / ".frob" / "cache.db").danger_ok


# frob:ticket T-2284
class TestFixEngineScopeLease:
    """`frob.gates._fix_engine_scope.filter_fixes_by_scope_and_lease`
    (T-2284): a Tier-A handler's own return value, filtered against the
    landing ticket's declared scope and every other ticket's live lease,
    BEFORE the caller (`apply_tier_a_fixes`) counts a fix as applied."""

    def _repo(self, tmp_path: Path) -> Path:
        root = tmp_path / "repo"
        root.mkdir()
        _git_init(root)
        return root

    def test_out_of_scope_fix_is_reverted_and_reported(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine_scope.py::filter_fixes_by_scope_and_lease  # noqa: E501
        from frob.gates._fix_engine_scope import filter_fixes_by_scope_and_lease
        from frob.gates._fix_engine_shared import FixApplied

        root = self._repo(tmp_path)
        target = root / "scripts" / "unrelated.py"
        target.parent.mkdir(parents=True)
        target.write_text("original\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "seed unrelated.py"], cwd=root, check=True
        )
        # Simulate a handler having already written to this file.
        target.write_text("handler rewrote this\n", encoding="utf-8")

        landing = _ticket(
            ticket_id="T-2284", state=TicketState.IN_PROGRESS, scope=("src/frob/**",)
        )
        queue = TicketQueue(tickets={"T-2284": landing})
        fixes = [
            FixApplied(rule="FMT001", file="scripts/unrelated.py", line=1, detail="x")
        ]

        kept, skipped = filter_fixes_by_scope_and_lease(root, queue, "T-2284", fixes)

        assert kept == []
        assert len(skipped) == 1
        assert skipped[0].file == "scripts/unrelated.py"
        assert "outside T-2284's declared scope" in skipped[0].reason
        assert target.read_text(encoding="utf-8") == "original\n"

    def test_live_leased_file_skipped_even_when_in_landing_scope(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine_scope.py::filter_fixes_by_scope_and_lease  # noqa: E501
        from frob.gates._fix_engine_scope import filter_fixes_by_scope_and_lease
        from frob.gates._fix_engine_shared import FixApplied

        root = self._repo(tmp_path)
        target = root / "src" / "frob" / "widget.py"
        target.parent.mkdir(parents=True)
        target.write_text("original\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "seed widget.py"], cwd=root, check=True
        )
        target.write_text("handler rewrote this\n", encoding="utf-8")

        # Landing ticket's OWN scope covers the file broadly...
        landing = _ticket(
            ticket_id="T-2284", state=TicketState.IN_PROGRESS, scope=("src/frob/**",)
        )
        # ...but another ticket, IN_PROGRESS, narrowly scopes the same
        # file: its live lease must win regardless.
        other = _ticket(
            ticket_id="T-9999",
            state=TicketState.IN_PROGRESS,
            scope=("src/frob/widget.py",),
        )
        queue = TicketQueue(tickets={"T-2284": landing, "T-9999": other})
        fixes = [
            FixApplied(rule="FMT001", file="src/frob/widget.py", line=1, detail="x")
        ]

        kept, skipped = filter_fixes_by_scope_and_lease(root, queue, "T-2284", fixes)

        assert kept == []
        assert len(skipped) == 1
        assert "T-9999" in skipped[0].reason
        assert "live lease" in skipped[0].reason
        assert target.read_text(encoding="utf-8") == "original\n"

    def test_narrowed_live_lease_wins_over_stale_declared_scope(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine_scope.py::filter_fixes_by_scope_and_lease  # noqa: E501
        # T-2328: reproduces the incident that silently discarded T-2194's
        # own in-scope design/frob.strata edit -- an OTHER ticket had
        # already narrowed its LIVE lease scope (record_lease published
        # `scope=()`), but its declared ledger scope still names the
        # file. `_other_ticket_holding_live_lease` used to read only the
        # stale declared scope, so it (wrongly) treated the file as still
        # under that ticket's lease and reverted a live, needed fix --
        # the exact staleness class `_land.py::_effective_leakage_scope`
        # (T-2095/T-2111) already fixed for `CrossTicketLeakage`. The
        # live (narrower) lease must win here too: the fix is kept.
        from frob.gates._fix_engine_scope import filter_fixes_by_scope_and_lease
        from frob.gates._fix_engine_shared import FixApplied
        from frob.tickets._leases import record_lease

        root = self._repo(tmp_path)
        target = root / "design" / "frob.strata"
        target.parent.mkdir(parents=True)
        target.write_text("original\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "seed design/frob.strata"],
            cwd=root,
            check=True,
        )
        target.write_text("handler rewrote this\n", encoding="utf-8")

        landing = _ticket(
            ticket_id="T-2194", state=TicketState.IN_PROGRESS, scope=("design",)
        )
        # T-2303's declared ledger scope is still broad ("design"), but
        # its live lease has already been narrowed to nothing.
        other = _ticket(
            ticket_id="T-2303",
            state=TicketState.IN_PROGRESS,
            scope=("design",),
        )
        record_lease(root, "T-2303", ())
        queue = TicketQueue(tickets={"T-2194": landing, "T-2303": other})
        fixes = [
            FixApplied(rule="SYS100", file="design/frob.strata", line=0, detail="x")
        ]

        kept, skipped = filter_fixes_by_scope_and_lease(root, queue, "T-2194", fixes)

        assert skipped == []
        assert len(kept) == 1
        assert target.read_text(encoding="utf-8") == "handler rewrote this\n"

    def test_in_scope_fix_is_kept_unchanged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine_scope.py::filter_fixes_by_scope_and_lease  # noqa: E501
        from frob.gates._fix_engine_scope import filter_fixes_by_scope_and_lease
        from frob.gates._fix_engine_shared import FixApplied

        root = self._repo(tmp_path)
        target = root / "src" / "frob" / "widget.py"
        target.parent.mkdir(parents=True)
        target.write_text("original\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "seed widget.py"], cwd=root, check=True
        )
        target.write_text("handler rewrote this\n", encoding="utf-8")

        landing = _ticket(
            ticket_id="T-2284", state=TicketState.IN_PROGRESS, scope=("src/frob/**",)
        )
        queue = TicketQueue(tickets={"T-2284": landing})
        fixes = [
            FixApplied(rule="FMT001", file="src/frob/widget.py", line=1, detail="x")
        ]

        kept, skipped = filter_fixes_by_scope_and_lease(root, queue, "T-2284", fixes)

        assert kept == fixes
        assert skipped == []
        assert target.read_text(encoding="utf-8") == "handler rewrote this\n"

    def test_uncommitted_in_scope_edit_survives_a_disqualified_tier_a_revert(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine_scope.py::_revert_fix_file  # noqa: E501
        # T-2351: reproduces the T-2194/T-2329/T-2323 incident end to end.
        # A ticket has a REAL, UNCOMMITTED, in-scope edit to a file
        # (matching T-2194's own uncommitted design/frob.strata capability
        # grant). A Tier-A handler then writes its OWN rewrite on top
        # (SYS100 overwriting the file in place, same shape). That fix is
        # disqualified (another ticket holds a genuinely live lease on the
        # file). Before T-2351, `_revert_fix_file` ran `git checkout --`,
        # which restores to HEAD -- discarding the ticket's own edit along
        # with the handler's, because `apply_tier_a_fixes` always runs
        # BEFORE `frob ticket land`'s wip-commit step, so HEAD here is
        # still the PRE-TICKET tip. With the fix, a snapshot taken before
        # any handler ran preserves the agent's own edit through a revert.
        from frob.gates._fix_engine import _snapshot_dirty_files
        from frob.gates._fix_engine_scope import filter_fixes_by_scope_and_lease
        from frob.gates._fix_engine_shared import FixApplied

        root = self._repo(tmp_path)
        target = root / "design" / "frob.strata"
        target.parent.mkdir(parents=True)
        target.write_text("original\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "seed design/frob.strata"],
            cwd=root,
            check=True,
        )

        # The ticket's OWN real, uncommitted, in-scope edit -- made before
        # `frob ticket land` (hence `apply_tier_a_fixes`) ever runs.
        target.write_text("agent's own capability grant\n", encoding="utf-8")

        # `apply_tier_a_fixes` always captures the dirty-file snapshot
        # BEFORE running any handler -- exactly this call, at this point.
        pre_fix_snapshot = _snapshot_dirty_files(root)
        assert pre_fix_snapshot["design/frob.strata"] == (
            b"agent's own capability grant\n"
        )

        # Simulate a Tier-A handler (SYS100) having already overwritten
        # the file in place with its own computed rewrite.
        target.write_text("handler rewrote this\n", encoding="utf-8")

        landing = _ticket(
            ticket_id="T-2194", state=TicketState.IN_PROGRESS, scope=("design",)
        )
        other = _ticket(
            ticket_id="T-2303", state=TicketState.IN_PROGRESS, scope=("design",)
        )
        queue = TicketQueue(tickets={"T-2194": landing, "T-2303": other})
        fixes = [
            FixApplied(rule="SYS100", file="design/frob.strata", line=0, detail="x")
        ]

        kept, skipped = filter_fixes_by_scope_and_lease(
            root, queue, "T-2194", fixes, pre_fix_snapshot
        )

        assert kept == []
        assert len(skipped) == 1
        assert "T-2303" in skipped[0].reason
        # The ticket's OWN pre-handler edit survives -- neither the
        # handler's disqualified rewrite NOR (the pre-T-2351 bug) HEAD's
        # committed "original" content.
        assert target.read_text(encoding="utf-8") == "agent's own capability grant\n"

    def test_committed_edit_is_unaffected_by_a_disqualified_tier_a_revert(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine_scope.py::_revert_fix_file  # noqa: E501
        # T-2351: the T-2323 discriminating comparison, as a regression
        # test -- an edit the ticket already `git commit`ed to its own
        # branch was ALWAYS safe (the old `git checkout --` restores to
        # HEAD, which already includes it); confirm the new snapshot path
        # does not change this the other reproduction case.
        from frob.gates._fix_engine import _snapshot_dirty_files
        from frob.gates._fix_engine_scope import filter_fixes_by_scope_and_lease
        from frob.gates._fix_engine_shared import FixApplied

        root = self._repo(tmp_path)
        target = root / "design" / "frob.strata"
        target.parent.mkdir(parents=True)
        target.write_text("original\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "seed design/frob.strata"],
            cwd=root,
            check=True,
        )

        # The ticket's own edit, COMMITTED to its own branch first.
        target.write_text("agent's own capability grant\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "T-2194: add capability grant"],
            cwd=root,
            check=True,
        )

        # No uncommitted dirt at this point -- the file is clean.
        pre_fix_snapshot = _snapshot_dirty_files(root)
        assert "design/frob.strata" not in pre_fix_snapshot

        # A Tier-A handler overwrites it in place (uncommitted, on top of
        # the committed grant).
        target.write_text("handler rewrote this\n", encoding="utf-8")

        landing = _ticket(
            ticket_id="T-2194", state=TicketState.IN_PROGRESS, scope=("design",)
        )
        other = _ticket(
            ticket_id="T-2303", state=TicketState.IN_PROGRESS, scope=("design",)
        )
        queue = TicketQueue(tickets={"T-2194": landing, "T-2303": other})
        fixes = [
            FixApplied(rule="SYS100", file="design/frob.strata", line=0, detail="x")
        ]

        kept, skipped = filter_fixes_by_scope_and_lease(
            root, queue, "T-2194", fixes, pre_fix_snapshot
        )

        assert kept == []
        assert len(skipped) == 1
        # No snapshot entry for this file -> falls back to the old
        # HEAD-restore, which is correct here since HEAD already IS the
        # ticket's own committed grant.
        assert target.read_text(encoding="utf-8") == "agent's own capability grant\n"

    def test_no_ticket_id_passes_every_fix_through_unfiltered(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine_scope.py::filter_fixes_by_scope_and_lease  # noqa: E501
        from frob.gates._fix_engine_scope import filter_fixes_by_scope_and_lease
        from frob.gates._fix_engine_shared import FixApplied

        root = self._repo(tmp_path)
        queue = TicketQueue(tickets={})
        fixes = [
            FixApplied(rule="FMT001", file="anywhere/at/all.py", line=1, detail="x")
        ]

        kept, skipped = filter_fixes_by_scope_and_lease(root, queue, None, fixes)

        assert kept == fixes
        assert skipped == []

    def test_rel002_is_a_named_repo_wide_exemption_not_a_silent_pass(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine_scope.py::filter_fixes_by_scope_and_lease  # noqa: E501
        """T-2284 acceptance[4]: REL002 -- pyproject.toml/CHANGELOG.md/
        uv.lock, none of which any ticket ever declares in its own scope
        (docs/guides/agent-playbook.md section 4b) -- is exempted by
        NAME, so it is kept and NEVER reverted even though the landing
        ticket's own (narrow, unrelated) scope obviously does not cover
        it and no other ticket holds a lease on it either."""
        from frob.gates._fix_engine_scope import filter_fixes_by_scope_and_lease
        from frob.gates._fix_engine_shared import FixApplied

        root = self._repo(tmp_path)
        target = root / "pyproject.toml"
        target.write_text('version = "0.1.0"\n', encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "seed pyproject.toml"], cwd=root, check=True
        )
        target.write_text('version = "0.2.0"\n', encoding="utf-8")

        landing = _ticket(
            ticket_id="T-2284",
            state=TicketState.IN_PROGRESS,
            scope=("src/frob/gates/_fix_engine.py",),
        )
        queue = TicketQueue(tickets={"T-2284": landing})
        fixes = [FixApplied(rule="REL002", file="pyproject.toml", line=1, detail="x")]

        kept, skipped = filter_fixes_by_scope_and_lease(root, queue, "T-2284", fixes)

        assert kept == fixes
        assert skipped == []
        assert target.read_text(encoding="utf-8") == 'version = "0.2.0"\n'


# frob:ticket T-1643
class TestFixEngineTierB:
    """`frob.gates._fix_engine_tier_b`'s Tier-B apply-verify-rollback
    transaction engine (T-1262): each test is a GIVEN/WHEN/THEN
    acceptance criterion off this ticket's own body. `gate_runner`/
    `test_runner` are injected fakes throughout -- this suite proves the
    engine's own commit/rollback DECISION LOGIC, not any real gate's
    behavior (the real defaults are exercised end-to-end by the module's
    own synthetic `TIERBDEMO001` handler against an actual, un-injected
    `run_gates`/pytest pair would be slow and gate-composition-fragile;
    injection is the same "default preserves real behavior, override is
    test-only" shape `fix_fmt001_directive_wrap`'s `only_paths` already
    established in `_fix_engine.py`)."""

    def _snap(self, root: Path):

        return build_graph(root, root / ".frob" / "cache.db").danger_ok

    def _demo_file(self, root: Path, marker_replacement: str) -> Path:
        (root / "src").mkdir(parents=True, exist_ok=True)
        path = root / "src" / "demo.py"
        path.write_text(
            f"# frob:tierbdemo {marker_replacement}\ndef f():\n    pass\n",
            encoding="utf-8",
        )
        return path

    # -- acceptance [0]: a clean Tier-B fix commits ------------------------

    def test_clean_fix_commits_and_is_reported_fixed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine_tier_b.py::apply_tier_b_fixes \
        # kind="unit"
        from frob.gates._fix_engine_tier_b import apply_tier_b_fixes
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        self._demo_file(root, "# fixed")
        snapshot = self._snap(root)

        def always_clean(_root: Path, _gates: frozenset[str]):
            from frob.gates._models import GateReport, GateStats

            return GateReport(violations=(), waived=(), stats=GateStats())

        def always_pass(_root: Path, _bound_tests: tuple[str, ...]):
            return True, ""

        committed, rolled_back = apply_tier_b_fixes(
            root,
            snapshot,
            TicketQueue(tickets={}),
            gate_runner=always_clean,
            test_runner=always_pass,
        )
        assert rolled_back == []
        assert len(committed) == 1
        assert committed[0].rule == "TIERBDEMO001"
        rewritten = (root / "src" / "demo.py").read_text(encoding="utf-8")
        assert rewritten.splitlines()[0] == "# fixed"

    # -- acceptance [1]: a regressing Tier-B fix rolls back ----------------

    def test_regressing_fix_is_rolled_back_byte_for_byte(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine_tier_b.py::apply_tier_b_fixes \
        # kind="unit"
        from frob.gates._fix_engine_tier_b import apply_tier_b_fixes
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        path = self._demo_file(root, "# fixed")
        original = path.read_text(encoding="utf-8")
        snapshot = self._snap(root)

        def always_pass(_root: Path, _bound_tests: tuple[str, ...]):
            return False, "TestX::test_y FAILED"

        def always_clean(_root: Path, _gates: frozenset[str]):
            from frob.gates._models import GateReport, GateStats

            return GateReport(violations=(), waived=(), stats=GateStats())

        committed, rolled_back = apply_tier_b_fixes(
            root,
            snapshot,
            TicketQueue(tickets={}),
            gate_runner=always_clean,
            test_runner=always_pass,
        )
        assert committed == []
        assert len(rolled_back) == 1
        assert rolled_back[0].rule == "TIERBDEMO001"
        assert "TestX::test_y FAILED" in rolled_back[0].regression_detail
        assert path.read_text(encoding="utf-8") == original

    def test_new_error_violation_after_fix_rolls_back(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine_tier_b.py::apply_tier_b_fixes \
        # kind="unit"
        from frob.gates._fix_engine_tier_b import apply_tier_b_fixes
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        path = self._demo_file(root, "# fixed")
        original = path.read_text(encoding="utf-8")
        snapshot = self._snap(root)

        from frob.gates._models import GateReport, GateStats, Severity, Violation

        calls: list[int] = []

        def flaky(_root: Path, _gates: frozenset[str]):
            calls.append(1)
            if len(calls) == 1:
                return GateReport(violations=(), waived=(), stats=GateStats())
            return GateReport(
                violations=(
                    Violation(
                        rule="ARCH001",
                        severity=Severity.ERROR,
                        file="src/demo.py",
                        line=1,
                        message="ARCH001: new regression",
                    ),
                ),
                waived=(),
                stats=GateStats(),
            )

        def always_pass(_root: Path, _bound_tests: tuple[str, ...]):
            return True, ""

        committed, rolled_back = apply_tier_b_fixes(
            root,
            snapshot,
            TicketQueue(tickets={}),
            gate_runner=flaky,
            test_runner=always_pass,
        )
        assert committed == []
        assert len(rolled_back) == 1
        assert "ARCH001" in rolled_back[0].regression_detail
        assert path.read_text(encoding="utf-8") == original

    # -- acceptance [2]: N fixes verified sequentially, one at a time -----

    def test_multiple_fixes_verified_sequentially_not_batched(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine_tier_b.py::apply_tier_b_fixes \
        # kind="unit"
        from frob.gates._fix_engine_tier_b import apply_tier_b_fixes
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "src" / "a.py").write_text(
            "# frob:tierbdemo # a-fixed\n", encoding="utf-8"
        )
        (root / "src" / "b.py").write_text(
            "# frob:tierbdemo # b-fixed\n", encoding="utf-8"
        )
        snapshot = self._snap(root)

        gate_call_order: list[frozenset[str]] = []

        def always_clean(_root: Path, gates: frozenset[str]):
            from frob.gates._models import GateReport, GateStats

            gate_call_order.append(gates)
            return GateReport(violations=(), waived=(), stats=GateStats())

        def always_pass(_root: Path, _bound_tests: tuple[str, ...]):
            return True, ""

        committed, rolled_back = apply_tier_b_fixes(
            root,
            snapshot,
            TicketQueue(tickets={}),
            gate_runner=always_clean,
            test_runner=always_pass,
        )
        assert rolled_back == []
        assert len(committed) == 2
        # Two gate_runner calls (before + after) PER fix, never one shared
        # batched call across both fixes.
        assert len(gate_call_order) == 4
        assert (root / "src" / "a.py").read_text(encoding="utf-8") == "# a-fixed\n"
        assert (root / "src" / "b.py").read_text(encoding="utf-8") == "# b-fixed\n"

    def test_no_marker_files_is_a_no_op(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine_tier_b.py::apply_tier_b_fixes \
        # kind="unit"
        from frob.gates._fix_engine_tier_b import apply_tier_b_fixes
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "src" / "plain.py").write_text("def f():\n    pass\n", encoding="utf-8")
        snapshot = self._snap(root)

        committed, rolled_back = apply_tier_b_fixes(
            root, snapshot, TicketQueue(tickets={})
        )
        assert committed == []
        assert rolled_back == []

    # -- DEAD001: the first real, production Tier-B handler (T-1643) -------

    # frob:ticket T-1643
    def test_dead001_removes_unreferenced_private_symbol(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/gates_suite/test_fix_engine.py::TestFixEngineTierB.test_dead001_removes\
        # _unreferenced_private_symbol
        from frob.gates._fix_engine_tier_b import (
            fix_dead001_unreferenced_symbol_removal,
        )
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        _write(
            root,
            "src/a.py",
            "def _never_called() -> None:\n    pass\n\n\ndef foo() -> None:\n    pass\n",
        )
        snapshot = self._snap(root)

        applied = fix_dead001_unreferenced_symbol_removal(
            root, snapshot, TicketQueue(tickets={})
        )
        assert len(applied) == 1
        assert applied[0].rule == "DEAD001"
        assert "_never_called" in applied[0].detail
        rewritten = (root / "src" / "a.py").read_text(encoding="utf-8")
        assert "_never_called" not in rewritten
        assert "def foo" in rewritten

    # frob:ticket T-1643
    def test_dead001_skips_a_waived_finding(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/gates_suite/test_fix_engine.py::TestFixEngineTierB.test_dead001_skips_a\
        # _waived_finding
        from frob.gates._fix_engine_tier_b import (
            fix_dead001_unreferenced_symbol_removal,
        )
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        _write(
            root,
            "src/a.py",
            '# frob:waive DEAD001 reason="reached only via getattr dispatch"\n'
            "def _never_called() -> None:\n    pass\n",
        )
        snapshot = self._snap(root)

        applied = fix_dead001_unreferenced_symbol_removal(
            root, snapshot, TicketQueue(tickets={})
        )
        assert applied == []
        assert "_never_called" in (root / "src" / "a.py").read_text(encoding="utf-8")

    # frob:ticket T-1643
    def test_dead001_at_most_one_deletion_per_file_per_pass(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/gates_suite/test_fix_engine.py::TestFixEngineTierB.test_dead001_at_most\
        # _one_deletion_per_file_per_pass
        from frob.gates._fix_engine_tier_b import (
            fix_dead001_unreferenced_symbol_removal,
        )
        from frob.tickets import TicketQueue

        root = tmp_path / "repo"
        _write(
            root,
            "src/a.py",
            "def _never_called_one() -> None:\n"
            "    pass\n\n\n"
            "def _never_called_two() -> None:\n"
            "    pass\n\n\n"
            "def foo() -> None:\n"
            "    pass\n",
        )
        snapshot = self._snap(root)

        applied = fix_dead001_unreferenced_symbol_removal(
            root, snapshot, TicketQueue(tickets={})
        )
        assert len(applied) == 1
        rewritten = (root / "src" / "a.py").read_text(encoding="utf-8")
        # Exactly one of the two dead symbols was removed this pass; the
        # other survives to be caught on the NEXT --fix invocation once
        # dead_symbol_gate is re-run against the now-updated tree.
        names = ("_never_called_one", "_never_called_two")
        assert sum(name not in rewritten for name in names) == 1


class TestFixEngineTierC:
    """`frob.gates._fix_engine_tier_c`'s Tier-C fix-it emission (T-1263):
    each test is a GIVEN/WHEN/THEN acceptance criterion off this ticket's
    own body."""

    def _snap(self, root: Path):

        return build_graph(root, root / ".frob" / "cache.db").danger_ok

    # -- acceptance [0]/[2]: a content-required finding emits a FixIt,
    #    message verbatim, no file edited -----------------------------

    def test_todo001_emits_a_fixit_with_no_proposed_patch(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine_tier_c.py::emit_todo001_fixit \
        # kind="unit"
        from frob.gates._fix_engine_tier_c import apply_tier_c_fixits
        from frob.gates._models import Severity, Violation

        root = tmp_path / "repo"
        root.mkdir(parents=True)
        snapshot = self._snap(root)
        message = "TODO001: bare TODO/FIXME at src/x.py:3; bind it: frob:todo T-####"
        violation = Violation(
            rule="TODO001",
            severity=Severity.ERROR,
            file="src/x.py",
            line=3,
            message=message,
        )
        fixits = apply_tier_c_fixits(root, snapshot, (violation,))
        assert len(fixits) == 1
        fixit = fixits[0]
        assert fixit.rule == "TODO001"
        assert fixit.file == "src/x.py"
        assert fixit.line == 3
        # acceptance [2]: message is the original violation's message VERBATIM.
        assert fixit.message == message
        assert fixit.proposed_patch is None
        assert fixit.reason_unfixable

    def test_todo001_emitter_never_touches_any_file(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine_tier_c.py::emit_todo001_fixit \
        # kind="unit"
        from frob.gates._fix_engine_tier_c import apply_tier_c_fixits
        from frob.gates._models import Severity, Violation

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        path = root / "src" / "x.py"
        original = "# TODO: fix this\ndef f():\n    pass\n"
        path.write_text(original, encoding="utf-8")
        snapshot = self._snap(root)
        violation = Violation(
            rule="TODO001",
            severity=Severity.ERROR,
            file="src/x.py",
            line=1,
            message="TODO001: bare TODO/FIXME at src/x.py:1; bind it: frob:todo T-####",
        )

        apply_tier_c_fixits(root, snapshot, (violation,))
        assert path.read_text(encoding="utf-8") == original

    # -- acceptance [1]: fixits array is empty (never a missing key --
    #    a plain list, always returned) when nothing is Tier-C-eligible --

    def test_no_eligible_findings_returns_an_empty_list(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine_tier_c.py::apply_tier_c_fixits \
        # kind="unit"
        from frob.gates._fix_engine_tier_c import apply_tier_c_fixits
        from frob.gates._models import Severity, Violation

        root = tmp_path / "repo"
        root.mkdir(parents=True)
        snapshot = self._snap(root)
        violation = Violation(
            rule="ARCH001",
            severity=Severity.ERROR,
            file="src/x.py",
            line=1,
            message="ARCH001: function too long",
        )

        fixits = apply_tier_c_fixits(root, snapshot, (violation,))
        assert fixits == []

    def test_no_violations_at_all_returns_an_empty_list(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine_tier_c.py::apply_tier_c_fixits \
        # kind="unit"
        from frob.gates._fix_engine_tier_c import apply_tier_c_fixits

        root = tmp_path / "repo"
        root.mkdir(parents=True)
        snapshot = self._snap(root)
        assert apply_tier_c_fixits(root, snapshot, ()) == []
