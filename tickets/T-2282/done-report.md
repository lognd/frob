## Done report

**Feasibility (acceptance 1), answered with evidence, not fabricated.** The
Stop payload's own documented fields -- confirmed against the plugin-dev
hook-development skill's documented Stop/SubagentStop payload shape --
are `session_id`, `transcript_path`, `cwd`, `permission_mode`,
`hook_event_name`, and (Stop/SubagentStop-specific) `reason`, plus the
empirically-observed `stop_hook_active` this repo's own
`diagnosis-nudge.py` already reads. NONE of these is a dedicated
"pending background tasks" field. Pending-task state IS recoverable, but
only indirectly: `transcript_path` (itself a documented field) points at
the session's JSONL transcript, and every backgrounded Bash call leaves a
structured trace there -- `toolUseResult.backgroundTaskId` for the
harness's own auto-background case, and a `"running in background with
ID: <id>"` tool_result string for an explicit `run_in_background: true`
call. A genuine completion is ALSO written back into the transcript later
as a synthetic user turn tagged `origin.kind == "task-notification"`
carrying `<task-id>ID</task-id>...<status>...</status>`. All of this was
verified directly against real transcript files on disk in this repo
(`~/.claude/projects/-home-logan-projects-frob/**/subagents/*.jsonl`),
not inferred from documentation alone -- including reproducing the exact
failure mode live during this same ticket's own work (a `find` command
this agent ran auto-backgrounded mid-session, confirming the harness-side
mechanism firsthand). So: NOT a dedicated field, but a real, evidence-based
answer -- `pending-background-guard.py` reconstructs the fact it needs
from the transcript already on hand, never a fabricated signal.

**Two fixes landed, matching the two levers named in the ticket:**

- `.claude/hooks/pending-background-guard.py` (new Stop hook): scans the
  last `_TAIL_BYTES` of the transcript for an unresolved background-start
  marker and blocks the Stop event (`decision: block`) exactly once per
  turn when one is found (`stop_hook_active` reentrancy guard -- never
  blocks twice, so report-and-stop always stays reachable). This is what
  closes the auto-background case: it fires on the STRANDING itself, not
  on which command or how it was backgrounded.
- `.claude/hooks/frob-timeout-guard.py`: denies an explicit
  `run_in_background=true` outright, keyed on the structured
  `tool_input.run_in_background` parameter (not a command-name pattern),
  scoped to agent context (`FROB_AGENT` set) so the coordinator's own
  legitimate long-measurement backgrounding is unaffected.

**Residual gap (acceptance 5), stated plainly.** Auto-backgrounding at
~120s is NOT prevented -- no PreToolUse hook can see or veto the
harness's own timer, and this ticket does not claim otherwise. The class
is CAUGHT, not CLOSED: `pending-background-guard.py` is the only backstop
for it, firing after the fact (at the next Stop event) rather than
preventing the background in the first place. Two narrower gaps in the
Stop hook's own detection, both deliberate/accepted (see the hook's
module docstring): (1) an agent that explicitly POLLS a still-running
task's output (BashOutput, a `Read` of the output file) reads as
"resolved" here even though the job has not finished -- the id
reappearing is treated as resolution regardless of what the poll showed;
(2) detection is lexical (regex over transcript text, matching this
repo's own `diagnosis-nudge.py` precedent), so a transcript whose content
happens to alter the marker text would not be recognized -- accepted
because the marker text is harness-generated, not attacker/model-
controlled.

Changed:
- `.claude/hooks/pending-background-guard.py::main` (new)
- `.claude/hooks/pending-background-guard.py::_tail_text` (new)
- `.claude/hooks/pending-background-guard.py::_pending_task_id` (new)
- `.claude/hooks/pending-background-guard.py::_decision` (new)
- `.claude/hooks/pending-background-guard.py::REASON` (new)
- `.claude/hooks/frob-timeout-guard.py::main` (changed)
- `.claude/hooks/frob-timeout-guard.py::RUN_IN_BACKGROUND_REASON` (new)
- `.claude/settings.json` (new Stop hook registration)
- `docs/guides/claude-hooks.md` (new/extended sections)

Evidence: 18 pytest node ids bound above across acceptance 2-5 (criterion
1 is a documentation/feasibility claim, answered in prose above with
transcript evidence, not pytest-bound). Designated repro:
`tests/test_hook_pending_background_guard.py::test_auto_backgrounded_task_with_no_resolution_is_blocked`
(`--check-repro` verified FAILED_AT_PARENT against the tests-only commit
1106d3901).

Filed: none -- no out-of-scope work discovered.

Gates: `frob check --ticket T-2282` clean on every ticket-scoped gate
family (gate:SCOPE, gate:PREWORK, and the diff-driven parts of gate:COV/
gate:FMT/gate:AFFECT); `frob test --base main` selected and passed all 24
touched-set tests (exit=0).
