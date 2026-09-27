"""`frob agent brief <ticket>` (T-draft-df99eb2d): print the dispatch
brief for ONE ticket, composed from two sources only -- the repo's own
`docs/guides/agent-playbook.md` (the standing dispatch contract, sections
"0"/"0a") and the ticket ledger (`frob.tickets.load_queue`, the same
loader `frob ticket show` uses) -- never a hand-pasted coordinator
scratchpad copy of either. This is deliberately a narrower sibling of
`frob ticket brief` (`frob.tickets._brief.compose_brief`): that command
composes the FULL mission briefing (acceptance, leases, verify commands,
gate baseline, REL rules); this one is the short per-ticket cheat sheet a
coordinator pastes into a dispatch prompt alongside "playbook governs",
so it renders the contract text plus only the ledger fields a coordinator
prompt would otherwise hand-type (title, body, scope, points, blocked_by,
parent, milestone, sprint, and -- when the ticket body declares one -- the
family wiring convention).
"""

from __future__ import annotations

import re
from pathlib import Path

from typani.result import Result

from frob.logging import get_logger
from frob.tickets._brief import _load_playbook_sections
from frob.tickets._models import Ticket, TicketError

_log = get_logger(__name__)

# frob:ticket T-draft-df99eb2d
# The dispatch-contract sections are every playbook section numbered "0"
# or "0<letter>" (sec 0's own ritual plus sec 0a's addenda, T-draft-
# df99eb2d) -- a plain string-prefix check on `_PlaybookSection.number`,
# not a hardcoded {"0", "0a"} set, so a future "0b"/"0c" addendum is
# picked up automatically without another edit here.
_CONTRACT_SECTION_PREFIX = "0"

# frob:ticket T-draft-df99eb2d
# A ticket body declares its family's wiring convention with a leading
# "wiring:" line (case-insensitive, matching `git grep`-able conventions
# elsewhere in this repo's ticket prose) -- e.g. "wiring: self-contained
# run(argv), bypasses App/AppConfig, __main__.py dispatches by literal
# argv[0] token (bind/agent/worktree/claude/natives precedent)". Absent
# for most tickets; when present it is the one thing a dispatched agent
# most needs to not re-derive from first principles.
_WIRING_LINE_RE = re.compile(r"^\s*wiring\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)


# frob:ticket T-draft-df99eb2d
def _dispatch_contract_text(root: Path) -> str:
    """The playbook's dispatch-contract sections (numbers prefixed
    `_CONTRACT_SECTION_PREFIX`), verbatim, reusing `frob.tickets._brief`'s
    own playbook parser (`_load_playbook_sections`) rather than a second
    hand-rolled `## N. Title` regex -- one parser, one place a heading
    format change has to be taught. Degrades to an explicit "no playbook
    found" note (never a blank section) when `root` has no playbook at
    all, matching `_load_playbook_sections`'s own empty-tuple contract."""
    sections = _load_playbook_sections(root)
    contract = [s for s in sections if s.number.startswith(_CONTRACT_SECTION_PREFIX)]
    if not contract:
        _log.warning(
            "agent brief: no dispatch-contract section found under %s -- "
            "printing without one",
            root,
        )
        return "(no dispatch-contract section found in docs/guides/agent-playbook.md)"
    lines: list[str] = []
    for section in contract:
        lines.append(f"### {section.number}. {section.title}")
        lines.append(section.body)
        lines.append("")
    return "\n".join(lines).rstrip("\n")


# frob:ticket T-draft-df99eb2d
def _family_wiring_convention(ticket: Ticket) -> str | None:
    """The ticket body's own `wiring:` line (`_WIRING_LINE_RE`), or `None`
    when the body declares no family wiring convention -- `render_agent_
    brief` omits the whole section rather than print an empty one in that
    case."""
    match = _WIRING_LINE_RE.search(ticket.body)
    if match is None:
        return None
    return match.group(1).strip()


# frob:ticket T-draft-df99eb2d
def _scope_section(ticket: Ticket) -> tuple[str, ...]:
    """Lines for the "## Scope" section: `ticket`'s own declared globs
    verbatim, or an explicit no-scope warning line (never a blank
    section, matching `frob.tickets._brief._scope_and_leases_section`'s
    same "(no scope declared)" posture) when it declares none."""
    lines = ["## Scope"]
    if ticket.scope:
        lines.extend(f"- {glob}" for glob in ticket.scope)
    else:
        lines.append(
            "WARNING: no scope declared -- narrow this before dispatch "
            "(`frob ticket scope <id> --add <glob> --reason ...`)"
        )
    lines.append("")
    return tuple(lines)


# frob:ticket T-draft-df99eb2d
# frob:doc docs/guides/agent-playbook.md#0a-dispatch-contract-addenda-moved-from-the-coordinator-scratchpad  # noqa: E501
def render_agent_brief(root: Path, ticket_id: str) -> Result[str, TicketError]:
    """`frob agent brief <ticket>` (T-draft-df99eb2d): render the short
    per-ticket dispatch brief -- the playbook's dispatch-contract sections
    (`_dispatch_contract_text`) plus `ticket_id`'s title, body, scope
    (`_scope_section`), points, blocked_by, parent, milestone, sprint, and
    (when declared) its family wiring convention
    (`_family_wiring_convention`). `root: Path`, returns `Result[str,
    TicketError]` (typani) -- `Err(TicketError.NotFound)` when `ticket_id`
    does not resolve in `root`'s ledger. Reads the ledger through `frob.
    tickets.load_queue`, the same loader `frob ticket show` uses, never a
    hand-parse of `ticket.md`."""
    from typani.result import Err, Ok

    from frob.tickets import load_queue

    loaded = load_queue(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok.tickets.get(ticket_id)
    if ticket is None:
        _log.warning("agent brief: %s not found under %s", ticket_id, root)
        return Err(TicketError.NotFound)

    lines: list[str] = [f"# Dispatch brief: {ticket.id} -- {ticket.title}", ""]
    lines.append("## Dispatch contract")
    lines.append(_dispatch_contract_text(root))
    lines.append("")

    points = ticket.points if ticket.points is not None else "UNSIZED"
    lines.append("## Ticket")
    lines.append(
        f"kind={ticket.kind.value} points={points} "
        f"parent={ticket.parent or '(none)'} "
        f"milestone={ticket.milestone or '(none)'} "
        f"sprint={ticket.sprint or '(none)'}"
    )
    lines.append(f"blocked_by={list(ticket.blocked_by)}")
    lines.append("")
    lines.append("## Body")
    lines.append(ticket.body.strip() or "(no body)")
    lines.append("")

    lines.extend(_scope_section(ticket))

    wiring = _family_wiring_convention(ticket)
    if wiring is not None:
        lines.append("## Family wiring convention")
        lines.append(wiring)
        lines.append("")

    _log.info("agent brief: rendered %s (%d line(s))", ticket.id, len(lines))
    return Ok("\n".join(lines) + "\n")
