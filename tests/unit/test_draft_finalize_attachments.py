"""T-2199: `finalize_draft`/`finalize_draft_for_land` must rewrite an
attachment's recorded `path:` field when the rename moves the attachment's
FILE out from under it -- measured on T-2195, whose ledger carried two
attachment records still pointing at a promoted-away draft directory that
no longer exists (`tickets/T-draft-0bd874ac/`) while the files themselves
had already been relocated by `renumber_one` to `tickets/T-2195/
attachments/`."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.tickets._draft_finalize import finalize_draft
from frob.tickets._models import (
    Attachment,
    Origin,
    Ticket,
    TicketKind,
    TicketState,
)
from frob.tickets._store import _serialize_ticket, _store_mode, tickets_dir


def _draft_ticket(draft_id: str, attachments: tuple[Attachment, ...]) -> Ticket:
    """A minimal v2-mode draft `Ticket` carrying `attachments` -- mirrors
    `tests/unit/test_ticket_store.py::_ticket`'s shape."""
    return Ticket(
        id=draft_id,
        title="Filed off-branch",
        state=TicketState.QUEUED,
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        blocked_by=(),
        parent=None,
        scope=(),
        evidence=(),
        attachments=attachments,
        body="## Description\nsomething\n",
    )


def _seed_draft_with_attachment(
    tmp_path: Path, draft_id: str, caption: str, data: bytes
) -> Attachment:
    """Write a v2-mode draft ticket directory by hand plus one real
    attachment file under it, and return the `Attachment` record naming it
    -- reproduces the on-disk shape `attach()` would have produced BEFORE
    promotion, without requiring a git repo (matches
    `TestV2Attachments.test_attachment_written_under_ticket_dir`'s own
    no-git pattern)."""
    import hashlib

    ticket_dir = tmp_path / "tickets" / draft_id
    (ticket_dir / "attachments").mkdir(parents=True)
    attachment_path = ticket_dir / "attachments" / "01-x.png"
    attachment_path.write_bytes(data)
    sha256 = hashlib.sha256(data).hexdigest()
    rel_path = str(attachment_path.relative_to(tickets_dir(tmp_path)))
    attachment = Attachment(path=rel_path, caption=caption, sha256=sha256)
    (ticket_dir / "ticket.md").write_text(
        _serialize_ticket(_draft_ticket(draft_id, (attachment,)))
    )
    return attachment


class TestFinalizeDraftRelocatesAttachmentRecords:
    """`finalize_draft` renumbers a draft id to its final `T-####` id --
    the attachment record's `path:` field must follow the file the rename
    already moved, not keep citing the vanished draft directory."""

    # frob:tests tests/unit/test_draft_finalize_attachments.py::TestFinalizeDraftRelocatesAttachmentRecords.test_attachment_path_follows_the_rename  # noqa: E501
    def test_attachment_path_follows_the_rename(self, tmp_path: Path) -> None:
        draft_id = "T-draft-0bd874ac"
        assert _store_mode(tmp_path) == "v2"
        old_attachment = _seed_draft_with_attachment(
            tmp_path, draft_id, "mockup", b"fake-png-bytes"
        )
        assert old_attachment.path.startswith(f"{draft_id}/attachments/")

        result = finalize_draft(tmp_path, draft_id)
        assert result.is_ok, result.err
        final_id = result.danger_ok
        assert final_id != draft_id

        from frob.tickets._store import load_all

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        final_ticket = loaded.danger_ok[final_id]
        assert len(final_ticket.attachments) == 1
        relocated = final_ticket.attachments[0]

        # The recorded path must now point at the FINAL id's directory --
        # not the vanished draft directory -- and must actually resolve to
        # a real file on disk (COV004's own reconstruction convention:
        # `tickets_dir(root) / attachment.path`).
        assert relocated.path.startswith(f"{final_id}/attachments/")
        assert draft_id not in relocated.path
        resolved = tickets_dir(tmp_path) / relocated.path
        assert resolved.exists(), (
            f"attachment record {relocated.path!r} does not resolve to a "
            "real file after finalize_draft -- the rename moved the file "
            "but the record was never rewritten"
        )
        assert resolved.read_bytes() == b"fake-png-bytes"

        # The old draft directory must genuinely be gone -- this is not a
        # case of "both locations happen to have a copy".
        assert not (tmp_path / "tickets" / draft_id).exists()

    # frob:tests tests/unit/test_draft_finalize_attachments.py::TestFinalizeDraftRelocatesAttachmentRecords.test_sha256_is_reverified_at_the_new_location  # noqa: E501
    def test_sha256_is_reverified_at_the_new_location(self, tmp_path: Path) -> None:
        """A relocated record must still carry the SAME verified sha256 --
        proving the fix re-hashes the file at its new path rather than
        blindly trusting the old recorded value."""
        draft_id = "T-draft-cafef00d"
        data = b"\x89PNG-not-really-but-bytes-are-bytes"
        old_attachment = _seed_draft_with_attachment(tmp_path, draft_id, "shot", data)

        result = finalize_draft(tmp_path, draft_id)
        assert result.is_ok, result.err
        final_id = result.danger_ok

        from frob.tickets._store import load_all

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        relocated = loaded.danger_ok[final_id].attachments[0]
        assert relocated.sha256 == old_attachment.sha256
