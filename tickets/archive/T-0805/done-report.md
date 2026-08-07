## Done report

Removed shell=True from _run_evidence_command (src/frob/tickets/__init__.py):
`cmd:` evidence entries in ticket YAML are repo-writable by every agent/tool,
so handing them to a shell was injection-adjacent even though cmd evidence
itself is a sanctioned feature (T-0215).

Survey of every real `cmd:` entry recorded in tickets.md/tickets-archive.md
found five distinct commands. Four are plain argv with no shell metacharacters
(`grep -n '...'`, `grep -q "..."`, `python3 <script>`, `uv run frob check
--only docblocks`) and parse identically under shlex.split. Exactly one
(T-0677's archived, already-DONE evidence: `test "$(grep -c ...)" = N &&
test "$(grep -c ...)" = N`) relies on shell command substitution and `&&`
sequencing and cannot be expressed as a single argv -- that ticket is closed
and nothing re-verifies its evidence live, so it is the deliberate migration
case, not a live constraint.

Chose argv-only execution (shlex.split(command), no shell) over a
constrained-shell path: with only one dead entry needing shell features,
keeping shell=True anywhere (even guarded) would still let a freshly
hand-pasted evidence command reach a shell interpreter, which is the exact
class of finding this ticket flags. _run_evidence_command now shlex.splits
the command into argv and runs it through frob.process._guard.
guarded_subprocess_run (T-0778) so FROB_DISABLE_EXEC also stops evidence
commands, not just frob check's own tool runners. A ValueError from
shlex.split (unbalanced quotes) or an empty parsed argv both fold to
Err(EvidenceCmdFailed), same failure shape as a nonzero exit -- callers
don't need a new error branch.

Honest assessment of the trust-domain argument in the ticket: cmd evidence
does execute in the same trust domain as the repo's own hooks/CI (an agent
that can write ticket YAML can also write source), so shell=True was never
a privilege-escalation vector by itself. What this fix removes is shell
*metacharacter interpretation* -- `;`, `$()`, backticks, `|`, `>` -- from a
string an agent may paste without full attention (copy-pasted from a log,
or containing an accidental semicolon), turning a plausible slip into inert
argv text instead of a sequenced/substituted command. That is a real,
non-cosmetic hardening, not a no-op: the regression test proves a `;
touch <marker>` payload no longer creates the marker file.

Migration note for future evidence needing multi-step/substitution logic:
shell out to a checked-in script and record `cmd:python3 <script>` or
`cmd:bash <script>` as a single argv entry, rather than relying on inline
shell syntax in the YAML string itself. Documented in
_run_evidence_command's own docstring.

### Changed
(no changed files detected)

### Evidence
- `tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_shell_metacharacters_do_not_reach_a_shell` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_command_substitution_is_not_expanded` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_malformed_quoting_fails_cleanly_instead_of_shelling_out` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_exec_kill_switch_stops_evidence_commands` (pytest node id, verified passing when recorded)
