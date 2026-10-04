+++
id = "01M2VFD1ZDWWNTW1FFGKHCKTS3"
title = "Claude Code hooks: 10% precision on frob-suggest, double registration doubles the attempt counter, blind FROB_SUGGEST_ACK on 97% of uses, no logging"
type = "story"
flavour = "user_story"
category = "todo"
priority = "medium"
reporter = "human"
created = "2026-09-19T00:00:00Z"
updated = "2026-10-04T22:22:23Z"
aliases = ["T-5101"]
labels = ["v1-cluster:E1", "triage:accepted"]
+++

Audit at scratchpad/HOOK-AUDIT.md. frob-suggest.py precision 10.4%, dual hook registration double-counts attempts per Bash call, FROB_SUGGEST_ACK is a blind blanket bypass used blindly in 97.3% of uses, hook logs nothing. Story tracks 4 leaves: registration/counter fix, rule verdict narrowing, per-rule ack token, and decision logging.

ORDERING NOTE (coordinator via planner, 2026-09-19): this story's leaf T-5098 ('frob-suggest: log every block/allow/ignored-ack decision to .frob/telemetry.jsonl') declares scope .claude/hooks/*, which covers .claude/hooks/tool-call-telemetry.py. T-4689 (CLI debloat story T-4687, 'Telemetry records the verb and subverb of every frob invocation') also edits that file and LANDS FIRST. T-4689 makes every frob invocation record verb and subverb (91% of the 34388 telemetry rows carry an empty subcommand today; every kind=tool row is empty because this hook never parses the frob verb out of the Bash command it records). Build the kind=hook rows on top of the fields T-4689 introduces rather than inventing a second row shape for the same stream.
