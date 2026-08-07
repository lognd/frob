## Done report

Changed:
- src/frob/app/ticket_runner.py::_attach (stdin.isatty() check before any
  clipboard attempt)
- docs/modules/tickets.md (Clipboard capture)

The check lives in the CLI runner, not `frob.tickets.attach` -- the library
function stays a pure "copy these bytes from a path or the clipboard"
primitive; the CLI is what decides whether the clipboard should even be
offered. Non-TTY + no path now exits 1 immediately with remedy text
("pass an explicit file path: frob ticket attach <id> <path>") instead of
spawning a clipboard backend (wl-paste/xclip/powershell.exe/pngpaste) that
can never produce an image in a headless agent session -- the actual
adoption-agent gap report this ticket exists to close.

Evidence: see structured `evidence:` list above (1 pytest node id,
tests/system/test_cli_ticket.py::TestTicketAttachNonInteractive, an
end-to-end subprocess test with a 10s timeout to catch a hang, recorded via
`frob ticket evidence`).
Filed: none.
Gates: `frob check --ticket T-0098 --only gates` clean (exit 0; remaining
118 warn-level violations are pre-existing repo-wide debt outside this
ticket's scope). Widened scope mid-ticket (via `frob ticket sweep`) to
include `docs/modules/tickets.md`, `tickets.md`, and `src/frob/__main__.py`
-- the doc update this house rule requires, plus files already modified on
this branch by the sibling T-0094/T-0096 tickets worked in the same
session, not anticipated by the ticket's original scope.
