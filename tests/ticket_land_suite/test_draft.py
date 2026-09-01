from pathlib import Path

import pytest

import frob.tickets._land_finalize as _land_finalize_mod
from frob.tickets import (
    TicketState,
    new_ticket,
    transition,
)
from frob.tickets._land import land
from frob.tickets._models import (
    LandError,
)
from frob.tickets._store import (
    ledger_path,
    load_all,
    write_ticket,
)
from tests.ticket_land_suite.conftest import (
    _commit_all,
    _make_closeable,
    _run,
    _spec,
)

pytestmark = pytest.mark.heavy_subprocess



class TestDraftFinalizeRewritesCodeAndLeavesWorktreeClean:
    """Reviewer bug 1: `finalize_draft` rewrites tickets.md AND every code
    file carrying a `frob:ticket <draft-id>` directive, uncommitted, in the
    worktree -- but the old `land` squashed from the branch's last commit,
    which predated those rewrites. A landed source file kept the dangling
    draft id, and the worktree was left dirty after a "successful" land.
    `land` must commit finalize/close's changes in the worktree BEFORE the
    squash so both the ledger AND the rewritten code reach main, and the
    worktree ends up clean."""

    def test_code_directive_rewritten_and_worktree_clean_after_land(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-i", str(wt)], repo)

        created = new_ticket(wt, _spec("Filed off-branch", scope=("src/thing2.py",)))
        assert created.is_ok
        draft_id = created.danger_ok.id
        assert draft_id.startswith("T-draft-")
        _make_closeable(wt, draft_id)
        # A code file carrying a frob:ticket directive naming the DRAFT id --
        # renumber_one (finalize_draft's rename primitive) must rewrite this
        # reference, and that rewrite must actually reach main.
        (wt / "src" / "thing2.py").write_text(
            f"# frob:ticket {draft_id}\ndef f():\n    pass\n"
        )
        _commit_all(wt, "off-branch ticket with a code directive")

        result = land(repo, draft_id, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        final_id = report.final_id
        assert final_id != draft_id

        # The landed file on MAIN must carry the FINAL id, never the draft.
        landed_src = (repo / "src" / "thing2.py").read_text()
        assert draft_id not in landed_src
        assert f"frob:ticket {final_id}" in landed_src

        # The worktree must be left completely clean -- finalize/close's
        # writes were committed before the squash, not left dangling.
        wt_status = _run(["git", "status", "--porcelain"], wt).stdout.strip()
        assert wt_status == "", f"worktree left dirty: {wt_status!r}"

        # And the worktree's own copy of the file must ALSO carry the final
        # id (the commit-before-squash fix touches the worktree itself).
        wt_src = (wt / "src" / "thing2.py").read_text()
        assert draft_id not in wt_src
        assert f"frob:ticket {final_id}" in wt_src


class TestDraftFinalizeRewritesRegistryYamlRefs:
    """T-0577: draft finalize at land time (`renumber_one`) used to rewrite
    only `frob:` directive lines -- a registry yaml's `disposition:
    "deferred:<draft-id>"` value (docs/design/registry/*.yaml's grammar,
    `frob.registry._models.parse_disposition`) was left pointing at the
    now-dead draft id, breaking REG003 until a human hand-swapped it (the
    real T-0388/compliance.yaml incident). `_rewrite_registry_references`
    must rewrite these too."""

    def test_registry_yaml_deferred_ref_rewritten_to_final_id(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-yaml", str(wt)], repo)

        # T-0854: the ticket's own scope must cover the registry row it
        # defers to itself -- otherwise T-0854's live-tracker-citation
        # preflight (correctly) refuses to land a ticket while a registry
        # disposition still names it as the reason a compliance gap is
        # open, unless the ticket's own change is what resolves that row.
        created = new_ticket(
            wt,
            _spec(
                "Filed off-branch",
                scope=("src/thing3.py", "docs/design/registry/compliance.yaml"),
            ),
        )
        assert created.is_ok
        draft_id = created.danger_ok.id
        assert draft_id.startswith("T-draft-")
        _make_closeable(wt, draft_id)

        registry_dir = wt / "docs" / "design" / "registry"
        registry_dir.mkdir(parents=True)
        (registry_dir / "compliance.yaml").write_text(
            f'entries:\n  - id: some-check\n    disposition: "deferred:{draft_id}"\n'
        )
        (wt / "src" / "thing3.py").write_text("def f():\n    pass\n")
        _commit_all(wt, "off-branch ticket deferred in a registry yaml")

        result = land(repo, draft_id, wt, dry_run=False)
        assert result.is_ok, result.err
        final_id = result.danger_ok.final_id
        assert final_id != draft_id

        landed_yaml = (
            repo / "docs" / "design" / "registry" / "compliance.yaml"
        ).read_text()
        assert draft_id not in landed_yaml
        assert f'"deferred:{final_id}"' in landed_yaml



class TestDraftIdFinalization:
    """Incident class 3: a ticket filed off the default branch got a
    provisional T-draft-<hex> id; landing must finalize it to a real
    sequential id (T-0162's promised mechanism) before closing."""

    def test_draft_id_finalized_on_land(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-h", str(wt)], repo)

        # A worktree is, by definition, off the default branch -- new_ticket
        # mints a draft id here unconditionally.
        created = new_ticket(wt, _spec("Filed off-branch", scope=("src/thing.py",)))
        assert created.is_ok
        draft_id = created.danger_ok.id
        assert draft_id.startswith("T-draft-")
        _make_closeable(wt, draft_id)
        (wt / "src" / "thing.py").write_text("# thing\n")
        _commit_all(wt, "off-branch ticket")

        result = land(repo, draft_id, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.final_id != draft_id
        assert not report.final_id.startswith("T-draft-")

        landed = load_all(repo)
        assert landed.is_ok
        assert draft_id not in landed.danger_ok
        assert report.final_id in landed.danger_ok
        assert landed.danger_ok[report.final_id].state == TicketState.DONE


# frob:ticket T-0637
class TestStandaloneSiblingDraftSurvivesLand:
    """T-0637 field incident: a worktree's ledger held a REAL ticket being
    landed AND a completely separate, standalone draft ticket (filed via
    `frob ticket new` mid-session, `frob:new`'s own scope-cut discovery --
    the T-0575/T-draft-3d5f6965 and T-0576's two-draft shapes). Before this
    fix, the sibling draft block was silently dropped by the land splice
    (never carried forward, since it was neither the ticket being landed
    nor already present on main) -- it must survive and land with a real,
    finalized id."""

    def test_sibling_draft_ticket_finalized_and_lands_alongside(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-j", str(wt)], repo)

        # The ticket actually being landed.
        primary = new_ticket(wt, _spec("Primary landed work", scope=("src/main3.py",)))
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        assert primary_id.startswith("T-draft-")
        _make_closeable(wt, primary_id)
        (wt / "src" / "main3.py").write_text("# primary work\n")

        # A STANDALONE sibling, filed while working the primary ticket,
        # left QUEUED -- never touched again, never landed on its own.
        sibling = new_ticket(
            wt, _spec("Found while working the primary ticket", scope=("src/sib.py",))
        )
        assert sibling.is_ok
        sibling_draft_id = sibling.danger_ok.id
        assert sibling_draft_id.startswith("T-draft-")
        assert sibling_draft_id != primary_id

        _commit_all(wt, "primary work plus a standalone sibling draft ticket")

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok

        landed = load_all(repo)
        assert landed.is_ok
        landed_map = landed.danger_ok

        # The sibling draft must NOT have vanished, and must NOT still
        # carry a draft id on main (T-0162: drafts never persist there).
        assert sibling_draft_id not in landed_map, (
            "sibling draft id should have been finalized away, not landed verbatim"
        )
        finalized_siblings = [
            tid
            for tid, t in landed_map.items()
            if t.title == "Found while working the primary ticket"
        ]
        assert finalized_siblings, "standalone sibling draft ticket was dropped at land"
        assert len(finalized_siblings) == 1
        sibling_final_id = finalized_siblings[0]
        assert not sibling_final_id.startswith("T-draft-")
        assert sibling_final_id != report.final_id

        # It survives in whatever state it was left in (QUEUED) -- landing
        # the PRIMARY ticket must not itself close/alter the sibling.
        assert landed_map[sibling_final_id].state == TicketState.QUEUED
        assert landed_map[report.final_id].state == TicketState.DONE



# frob:ticket T-2425
class TestForeignOwnedSiblingDraftSkipped:
    """T-2425: a sibling draft ACTIVELY leased by a DIFFERENT, live
    worktree (a different agent's own epic decomposition, still being
    written) must not be finalized here -- and, critically, must not
    fail THIS land, whose own content has nothing to do with it. The
    measured incident: T-2394's land was refused repeatedly with
    `ScopeLeaseConflict` while trying to finalize `T-2428`, a draft it
    had never heard of."""

    def test_land_succeeds_and_skips_the_foreign_draft(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land_finalize.py::_finalize_sibling_drafts kind="unit"  # noqa: E501
        from frob.tickets._leases import record_lease

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-landing", str(wt)], repo)

        primary = new_ticket(wt, _spec("Primary landed work", scope=("src/main4.py",)))
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        _make_closeable(wt, primary_id)
        (wt / "src" / "main4.py").write_text("# primary work\n")

        # This SAME landing worktree's ledger also carries a sibling
        # draft -- filed here (drafts live on main -- every worktree
        # carries a checkout copy, the exact "looks like a worktree
        # lease" red herring the ticket names) but ACTIVELY owned and
        # leased by a DIFFERENT, live worktree elsewhere in the same
        # repo, simulating a different agent's own in-progress epic
        # decomposition. This land has no relation to it and must never
        # even attempt to renumber it.
        foreign_draft = new_ticket(wt, _spec("Epic child filed by a different agent"))
        assert foreign_draft.is_ok
        foreign_draft_id = foreign_draft.danger_ok.id
        _commit_all(wt, "primary work plus a foreign-owned sibling draft")

        foreign_wt = repo.parent / "foreign_wt"
        _run(
            ["git", "worktree", "add", "-b", "epic-decomposition", str(foreign_wt)],
            repo,
        )
        leased = record_lease(foreign_wt, foreign_draft_id, ())
        assert leased.is_ok

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.final_id == primary_id or not report.final_id.startswith(
            "T-draft-"
        )

        landed = load_all(repo)
        assert landed.is_ok
        landed_map = landed.danger_ok
        assert landed_map[report.final_id].state == TicketState.DONE
        # The foreign draft must NOT have been finalized/carried onto
        # main by THIS land -- it is still its own owner's job.
        assert not any(
            t.title == "Epic child filed by a different agent"
            and not tid.startswith("T-draft-")
            for tid, t in landed_map.items()
        )

    def test_land_still_refuses_a_genuine_scope_conflict_on_its_own_ticket(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land_finalize.py::_finalize_sibling_drafts kind="unit"  # noqa: E501
        # Must-still-refuse control (T-2425 acceptance [1]): this fix must
        # not weaken the LANDING ticket's own conflict detection -- only
        # sibling drafts get the skip-with-notice treatment.
        from frob.tickets._leases import record_lease

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-conflict", str(wt)], repo)
        primary = new_ticket(wt, _spec("Primary work", scope=("src/main5.py",)))
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        _make_closeable(wt, primary_id)
        (wt / "src" / "main5.py").write_text("# primary work\n")
        _commit_all(wt, "primary work")

        # A DIFFERENT, live worktree holds a foreign lease on the SAME
        # id this land is trying to finalize (simulating a genuine
        # collision on the ticket actually being landed, not a sibling).
        foreign_wt = repo.parent / "foreign_wt2"
        _run(["git", "worktree", "add", "-b", "collider", str(foreign_wt)], repo)
        leased = record_lease(foreign_wt, primary_id, ())
        assert leased.is_ok

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed




# frob:ticket T-2425
class TestForeignOwnedDraftWorktree:
    """Unit coverage for `_foreign_owned_draft_worktree` directly, isolated
    from the full `land()` pipeline above."""

    def test_no_leases_is_none(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land_finalize.py::_foreign_owned_draft_worktree kind="unit"  # noqa: E501
        assert (
            _land_finalize_mod._foreign_owned_draft_worktree(repo, "T-draft-deadbeef")
            is None
        )

    def test_own_worktree_lease_is_not_foreign(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land_finalize.py::_foreign_owned_draft_worktree kind="unit"  # noqa: E501
        from frob.tickets._leases import record_lease

        assert record_lease(repo, "T-draft-aaaaaaaa", ()).is_ok
        assert (
            _land_finalize_mod._foreign_owned_draft_worktree(repo, "T-draft-aaaaaaaa")
            is None
        )

    def test_foreign_live_lease_names_the_worktree(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land_finalize.py::_foreign_owned_draft_worktree kind="unit"  # noqa: E501
        from frob.tickets._leases import record_lease

        foreign_wt = repo.parent / "foreign_unit_wt"
        _run(["git", "worktree", "add", "-b", "foreign-unit", str(foreign_wt)], repo)
        assert record_lease(foreign_wt, "T-draft-bbbbbbbb", ()).is_ok

        owner = _land_finalize_mod._foreign_owned_draft_worktree(
            repo, "T-draft-bbbbbbbb"
        )
        assert owner is not None
        assert Path(owner).resolve() == foreign_wt.resolve()

    def test_ttl_expired_foreign_lease_is_not_foreign(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land_finalize.py::_foreign_owned_draft_worktree kind="unit"  # noqa: E501
        from frob.tickets._leases import record_lease

        foreign_wt = repo.parent / "foreign_ttl_wt"
        _run(["git", "worktree", "add", "-b", "foreign-ttl", str(foreign_wt)], repo)
        assert record_lease(foreign_wt, "T-draft-cccccccc", ()).is_ok

        monkeypatch.setattr(
            "frob.tickets._leases.is_lease_ttl_expired",
            lambda _record: True,
        )
        assert (
            _land_finalize_mod._foreign_owned_draft_worktree(repo, "T-draft-cccccccc")
            is None
        )


class TestDraftReferenceRewriteOnLand:
    """T-0811: land renumbers a finalized draft's structural id fields, but
    before this fix left Done-report PROSE citing the old draft id
    untouched, so TICK006's phantom-filing-claim gate reds main the
    moment the draft finalizes to a real id (recurred 3x this drive:
    T-0778/T-0797, T-0745/T-0764). A land whose own Done report cites its
    own (pre-finalize) draft id must come out with that reference rewritten
    to the final id, and zero `T-draft-` ids left anywhere in the ledger."""

    def test_land_rewrites_own_draft_id_reference_in_done_report(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-k", str(wt)], repo)

        primary = new_ticket(
            wt, _spec("Self-citing draft work", scope=("src/self.py",))
        )
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        assert primary_id.startswith("T-draft-")
        (wt / "src" / "self.py").write_text("# self-citing draft work\n")

        assert transition(wt, primary_id, TicketState.PLANNED).is_ok
        assert transition(wt, primary_id, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[primary_id]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": (
                    ticket.body
                    + "\n## Done report\n\nevidence attached\n"
                    + f"Filed: {primary_id} (scope-cut note filed against self)\n"
                ),
            }
        )
        assert write_ticket(wt, ticket).is_ok

        _commit_all(wt, "self-citing draft work")

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        final_id = report.final_id
        assert final_id != primary_id

        landed = load_all(repo)
        assert landed.is_ok
        landed_map = landed.danger_ok
        assert primary_id not in landed_map

        final_ticket = landed_map[final_id]
        assert primary_id not in final_ticket.body, (
            "stale draft-id reference survived in the landed Done report"
        )
        assert f"Filed: {final_id}" in final_ticket.body

        ledger_text = ledger_path(repo).read_text(encoding="utf-8")
        assert "T-draft-" not in ledger_text, (
            "a T-draft- id survived somewhere in the landed ledger text"
        )

    # frob:ticket T-1622
    def test_land_rewrites_a_sibling_drafts_citation_in_the_primary_done_report(
        self, repo: Path
    ) -> None:
        """T-1622's exact real-world shape: an agent, mid-work on its
        assigned ticket, discovers follow-up work and files it via `frob
        ticket new` (which mints a draft id off-branch) -- then cites that
        DIFFERENT ticket's draft id in ITS OWN Done report's "Filed: ..."
        line, never editing the sibling's own body at all. `_land_
        rewrite_draft_references_in_bodies` is called with the FULL
        `draft_id_mapping` (primary + every finalized sibling,
        `_land_finalize_and_close`'s `draft_id_mapping.update(siblings_
        finalized...)`), so this citation must be rewritten too -- proving
        the land alone (no draft/finalize round-trip left for a human,
        no hand-edited citation anywhere) satisfies T-1622's acceptance:
        an agent files a follow-up from a worktree, lands its work, and
        nobody touches the ledger by hand for the citation to be correct
        on main."""
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-t1622", str(wt)], repo)

        primary = new_ticket(
            wt, _spec("Primary work citing a sibling", scope=("src/primary622.py",))
        )
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        assert primary_id.startswith("T-draft-")
        (wt / "src" / "primary622.py").write_text("# primary work\n")

        # The follow-up, discovered mid-work, filed as its own standalone
        # ticket -- left QUEUED, exactly like a real residue filing.
        sibling = new_ticket(
            wt, _spec("Follow-up discovered mid-work", scope=("src/sib622.py",))
        )
        assert sibling.is_ok
        sibling_draft_id = sibling.danger_ok.id
        assert sibling_draft_id.startswith("T-draft-")
        assert sibling_draft_id != primary_id

        _make_closeable(wt, primary_id)
        loaded = load_all(wt)
        ticket = loaded.danger_ok[primary_id]
        ticket = ticket.model_copy(
            update={
                "body": (
                    ticket.body
                    + f"\nFiled: {sibling_draft_id} (follow-up, out of scope)\n"
                )
            }
        )
        assert write_ticket(wt, ticket).is_ok
        _commit_all(wt, "primary work citing a standalone sibling draft")

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        final_id = report.final_id

        landed = load_all(repo)
        assert landed.is_ok
        landed_map = landed.danger_ok

        # The sibling must have been promoted to a real id alongside the
        # primary -- never left as a draft, never dropped.
        assert sibling_draft_id not in landed_map
        finalized_siblings = [
            tid
            for tid, t in landed_map.items()
            if t.title == "Follow-up discovered mid-work"
        ]
        assert finalized_siblings, "sibling draft ticket was dropped at land"
        sibling_final_id = finalized_siblings[0]
        assert not sibling_final_id.startswith("T-draft-")

        # And the PRIMARY's own Done report -- a DIFFERENT ticket's body
        # than the sibling's -- must cite the sibling's REAL final id, not
        # its now-defunct draft id, with no human intervention.
        final_body = landed_map[final_id].body
        assert sibling_draft_id not in final_body, (
            "primary's Done report still cites the sibling's dead draft id "
            "-- this is the exact toil T-1622 exists to eliminate"
        )
        assert f"Filed: {sibling_final_id}" in final_body

        ledger_text = ledger_path(repo).read_text(encoding="utf-8")
        assert "T-draft-" not in ledger_text

    def test_land_rewrites_strata_waive_clause_draft_id_reference(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        # T-0812: extends the T-0811 body-prose rewrite to a `design/*.
        # strata` `waive` clause citing the SAME draft id being finalized
        # -- the original T-draft-8cd37914 incident class WAIVE007's
        # T-draft-* exemption otherwise leaves dangling forever.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-strata", str(wt)], repo)

        primary = new_ticket(
            wt, _spec("Strata-citing draft work", scope=("src/strata_ref.py",))
        )
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        assert primary_id.startswith("T-draft-")
        (wt / "src" / "strata_ref.py").write_text("# strata-citing draft work\n")

        design_dir = wt / "design"
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / "waivers.strata").write_text(
            "component demo {\n"
            f'    waive "SYS203:demo" reason "draft waiver" ticket "{primary_id}";\n'
            "}\n"
        )

        assert transition(wt, primary_id, TicketState.PLANNED).is_ok
        assert transition(wt, primary_id, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[primary_id]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": ticket.body + "\n## Done report\n\nevidence attached\n",
            }
        )
        assert write_ticket(wt, ticket).is_ok

        _commit_all(wt, "strata-citing draft work")

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        final_id = result.danger_ok.final_id
        assert final_id != primary_id

        strata_text = (repo / "design" / "waivers.strata").read_text(encoding="utf-8")
        assert primary_id not in strata_text, (
            "stale draft-id reference survived in the landed .strata waive clause"
        )
        assert f'ticket "{final_id}"' in strata_text

    def test_land_rewrites_frob_waive_comment_draft_id_reference(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        # T-0812: same rewrite, source `frob:waive ... ticket=` comment
        # channel rather than `.strata`.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waivecomment", str(wt)], repo)

        primary = new_ticket(
            wt, _spec("Comment-citing draft work", scope=("src/waive_ref.py",))
        )
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        assert primary_id.startswith("T-draft-")
        (wt / "src" / "waive_ref.py").write_text(
            "x = 1  # noqa: E501\n"
            f'# frob:waive DEMO001 reason="draft waiver" ticket={primary_id}\n'
        )

        assert transition(wt, primary_id, TicketState.PLANNED).is_ok
        assert transition(wt, primary_id, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[primary_id]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": ticket.body + "\n## Done report\n\nevidence attached\n",
            }
        )
        assert write_ticket(wt, ticket).is_ok

        _commit_all(wt, "comment-citing draft work")

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        final_id = result.danger_ok.final_id
        assert final_id != primary_id

        comment_text = (repo / "src" / "waive_ref.py").read_text(encoding="utf-8")
        assert primary_id not in comment_text, (
            "stale draft-id reference survived in the landed frob:waive comment"
        )
        assert f"ticket={final_id}" in comment_text

    def test_land_leaves_unrelated_draft_id_reference_untouched(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        # T-0812 (reviewer follow-up on T-0811): the rewrite must be
        # per-id-keyed against the actual old->new mapping, not a blanket
        # "strip every T-draft- token" pass -- an UNRELATED draft id
        # mentioned in ledger prose (one that is not itself being
        # finalized by this land) must survive verbatim. Kept as its own
        # test since planting an unrelated draft id conflicts with the
        # existing blanket "zero T-draft- ids left in the ledger"
        # assertion in test_land_rewrites_own_draft_id_reference_in_done_report.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-unrelated", str(wt)], repo)

        primary = new_ticket(
            wt, _spec("Primary work", scope=("src/unrelated_primary.py",))
        )
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        assert primary_id.startswith("T-draft-")
        (wt / "src" / "unrelated_primary.py").write_text("# primary work\n")

        unrelated_draft_id = "T-draft-deadbeef"
        assert unrelated_draft_id != primary_id

        assert transition(wt, primary_id, TicketState.PLANNED).is_ok
        assert transition(wt, primary_id, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[primary_id]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": (
                    ticket.body
                    + "\n## Done report\n\nevidence attached\n"
                    + f"Note: unrelated to {unrelated_draft_id}, not landing it\n"
                ),
            }
        )
        assert write_ticket(wt, ticket).is_ok

        _commit_all(wt, "primary work citing an unrelated draft id in prose")

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        final_id = result.danger_ok.final_id
        assert final_id != primary_id

        landed = load_all(repo)
        assert landed.is_ok
        final_ticket = landed.danger_ok[final_id]
        assert unrelated_draft_id in final_ticket.body, (
            "unrelated draft id in prose was rewritten/stripped -- the "
            "substitution must be scoped to this land's own old->new "
            "mapping, not a blanket T-draft- removal"
        )
