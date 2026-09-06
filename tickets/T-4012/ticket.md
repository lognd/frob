---
id: T-4012
title: 'F-224: REF002 fires on binary assets whose only documented escape is an in-file
  comment they cannot carry (cleanest no-exit yet)'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_refs.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-224, 2026-09-06:

  "Media files under frontend/public/media (mp4, posters) get REF002 'one inbound
   reference' findings and a binary cannot carry a frob:waive comment;
   refs.entrypoint is the only escape and it is per-file. Add a glob-level waiver
   or exempt declared asset directories."

THIS IS THE CLEANEST NO-EXIT IN THE QUEUE, and it is worth stating precisely
because the class is usually arguable and this instance is not. The other nine
instances involve a rule whose escape hatch is missing, misplaced, or defeated by
some mechanism. Here the escape hatch is a SOURCE COMMENT and the subject is an
MP4. It is not hard, or awkward, or unsupported -- it is physically impossible.
A binary file cannot carry a comment, so the documented remedy can never apply,
for any binary, ever.

That makes it the reference example for the class: a rule demanding something the
subject STRUCTURALLY cannot provide. Ten instances now: T-3843 (frontmatter waive
cannot attach), T-3852, T-3855, T-3900, F-067, T-3924, F-080, T-3979 (amend
re-creates the finding it fixes), T-4008 (--skip-mutation-evidence does not lift
the check it names), and this.

THE ONLY AVAILABLE ESCAPE DOES NOT SCALE, which is the second half of the report:
refs.entrypoint is PER FILE. A media directory is exactly the case where per-file
declaration is wrong -- assets arrive in batches, are added by non-engineers, and
carry no engineering intent worth declaring one line at a time. So the workaround
that technically exists converts a rule into a maintenance tax that grows with
content.

TWO REMEDIES, AND THEY ARE NOT ALTERNATIVES -- the first is needed regardless:
  1. A GLOB-LEVEL WAIVER for rules whose only escape is an in-file directive.
     This is the general fix and it serves every binary/generated/vendored case,
     not just media. Without it, ANY rule that fires on a non-text file is
     unwaivable by construction, which is a property of the waiver system rather
     than of REF002.
  2. DECLARED ASSET DIRECTORIES -- the consumer points at the refs.artifact idea,
     which is already filed here as T-3976 (from their own earlier frontend
     audit, F-198). That is the semantically richer answer: a verbatim-copy asset
     surface declared once, with each entry justified. CROSS-REFERENCE T-3976
     rather than designing a second construct; if refs.artifact lands, this
     becomes its first real consumer.

WHAT TO DETERMINE FIRST: does REF002 have any non-comment waiver path today
(config-level, glob-level) that the consumer simply did not find? "There is no
mechanism" is a claim about our code and must be grepped before it is believed --
three items in the recent audit epics turned out to be already implemented. If a
config-level path exists, this is a discoverability defect and the fix is
different and much smaller.

DO NOT fix this by exempting binaries from REF002 wholesale. An orphaned 40MB
video that nothing references is a real finding and exactly what REF002 is for;
the problem is that the finding cannot be DISCHARGED, not that it cannot be made.

MUST-FIRE FIXTURE: a genuinely unreferenced binary asset still produces a
finding.
MUST-STAY-QUIET: a declared asset directory's contents do not produce per-file
findings, and adding a new asset to it requires no new declaration.
THIRD FIXTURE: a glob-level waiver discharges a finding on a file that cannot
carry a comment.

ACCEPTANCE
- Whether a non-comment waiver path already exists, answered by grep first.
- A discharge mechanism that works for files that cannot hold a directive.
- Cross-referenced with T-3976 rather than duplicating refs.artifact.
- All three fixtures committed.