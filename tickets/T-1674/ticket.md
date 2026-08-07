---
id: T-1674
title: 'Every frob verb resolves root from cwd silently: widen T-1638 beyond land'
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1638 records that 'frob ticket land' resolves the repo root from cwd, so running it from inside a worktree targets the wrong tree. The defect is not specific to land -- it is how EVERY frob verb resolves root, and the ledger-writing verbs are just as damaging.

Field incident, coordinator, 2026-08-06: a shell whose cwd had drifted into .claude/worktrees/w34-dispatch ran 'frob ticket new'. The ticket was filed into that WORKTREE's ledger rather than main's, and nothing in the output said so -- the command printed a created id and exited 0, identical to a correct run. It was caught only because the id came back as a T-draft-* rather than a T-#### (drafts are allocated in worktrees), and that tell exists only for 'new'. 'close', 'drop', 'evidence', and 'done-report' would have written to the wrong ledger with no distinguishing signal at all. In this case the worktree was about to land, so promotion recovers it; had the worktree been abandoned, the ticket would have been silently destroyed.

This is the R4 shape (position validated too late) and the same class as the earlier incident where a gate measurement was taken against a worktree and reported as main's number.

Work:
1. Every frob command reports the root it resolved -- at minimum on any ledger-writing or measuring verb, unconditionally, not behind -v. A run that cannot be attributed to a tree is not a trustworthy run.
2. Add an explicit --root / FROB_ROOT override so a caller can pin the tree rather than depending on ambient cwd. The coordinator's own measure wrapper already pins ROOT by hand for exactly this reason; that logic belongs in frob.
3. Decide the ownership rule per verb: which verbs are legitimate inside a worktree (start, evidence, done-report on the ticket being worked), and which should refuse or warn (new/close/drop targeting a ticket the worktree does not own). This overlaps T-1669's ownership model -- fold it in there if that is the cleaner home.

Supersedes the narrow framing of T-1638, which should become a child of this.