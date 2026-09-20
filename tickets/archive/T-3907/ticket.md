---
id: T-3907
title: organise the README by the CLI's own verb groups with a concept paragraph per
  subsystem
state: done
kind: docs
origin: human
created: '2026-09-05'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- README.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: README.md
  reason: README rewrite scope for T-3907
  actor: logan
  at: '2026-09-05'
evidence:
- cmd:python3 /tmp/claude-1000/-home-logan-projects-frob/79c6402d-b401-4652-bea7-f81df1be9322/scratchpad/readme_check.py
  README.md exit=0 sha256=dcdcab570eef
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OWNER DIRECTIVE 2026-09-05: "refactor the README to have the verb collections
and explanations of the subsystems rather than just a long list of verbs that
look unrelated." Scheduled PRE-ALPHA.

THIS IS A FOLLOW-UP TO T-3846, NOT A REDO. T-3846 landed (30b289db0) and did the
right first pass: it removed the make-target drift, put a real install line and
a verified first-run command in the first screen, and replaced prose with a verb
table. The remaining problem is that the table is FLAT -- a reader meets twenty
verbs with no way to tell which belong together or what each subsystem is FOR.

THE STRUCTURE ALREADY EXISTS IN THE CLI AND THE README DOES NOT REFLECT IT.
`frob --help` groups the surface already:

    explore   navigation: map/outline/xref/docs-search            (T-1238)
    quality   correctness/hygiene gates: check/test/dup/arch/
              bind/cycle/mutate/perf                              (T-1567)
    design    design-knowledge surfaces: sys/registry/docs/
              graph/exports                                       (T-1568)
    ops       release/fleet/infra plumbing: release, natives,
              doctor, clean, fleet, deploy, scaffold, gitlog,
              stats                                               (T-1569)
    ticket    the statically-checkable ticket queue
    vet       dependency vetting
    serve     MCP stdio adapter

Each group is "also usable standalone". So the README should mirror the CLI's
own taxonomy rather than inventing a second one -- and if the README's grouping
and `frob --help`'s grouping ever disagree, that is itself a drift bug worth
noticing.

WHAT TO WRITE. Per group, in this order:
  1. WHAT THE SUBSYSTEM IS FOR, in one or two sentences -- the CONCEPT, not a
     verb list. What question does this group answer? When would a reader reach
     for it? `quality` is "gates that make unaccounted-for work a build
     failure"; `ticket` is "a git-tracked queue where deferred work is a
     directive in the code, not a note"; `design` is "the model frob checks the
     code against". A reader should be able to skip a whole group once they know
     they do not need it -- that is the entire value of grouping.
  2. The member verbs, one line each, WHAT and WHEN.
  3. A pointer into docs/ for depth. The README points; it does not duplicate.

KEEP WHAT T-3846 GOT RIGHT: two-or-three-sentence opening, ONE copy-paste
install line, a first-run command that produces visible output, and the
annotate -> check -> fix-or-waive loop. Do not regress the first screen; a
reader must still reach a working command without scrolling past taxonomy.

CO-ORDINATION, IMPORTANT: a sibling ticket is consolidating the `format`/`fmt`
split (they are the same word for different operations). DO NOT document a
consolidated form that has not landed -- a README naming a verb that does not
exist is a DOC006 error, and unresolvable citations in prose have blocked four
lands today. Describe the surface AS IT IS, and let the other ticket update its
own row when it lands. If you find yourself wanting to explain why there are two
formatters, that is the signal to leave it alone and let the other ticket fix
the thing rather than document the confusion.

VERIFY EVERY COMMAND YOU PUT IN IT by running it, exactly as T-3846 was required
to. An unverified README is how the make-target drift got there.

DO NOT let the grouping become a wall of prose. The failure mode on the other
side of a flat list is a README nobody finishes. Each group's concept paragraph
earns its place only if it lets a reader SKIP the group.

MUST-STAY-QUIET FIXTURES:
  - the full gate run stays clean on the rewritten README (no new DOC004/DOC006)
  - every command in it executes successfully
ACCEPTANCE
- Organised by the CLI's own groups, with a concept paragraph per group.
- First screen still reaches a working command.
- Every command run and confirmed.
- Nothing documented that does not exist yet.
- Anything cut that a reader needs moved to docs/ and linked, listed explicitly.