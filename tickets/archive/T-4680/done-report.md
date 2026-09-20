## Done report

DECISION ticket. Its only deliverable is an owner decision recorded in the body,
and the owner recorded it on 2026-09-19 as D-M6.

DECISION: split the monofile (the ticket's option 2), with one binding
constraint the option as written did not carry -- the split is done MODULE BY
MODULE, BY HAND, and no split tool is to be written.

WHAT THE EVIDENCE WAS (SF-10, measured at HEAD c8f56ef10): design/frob.strata is
2,766 lines = 1,948 comment lines + 722 non-blank non-comment lines, of which
111 (15.4%) are literal duplicates of another line -- `clearance Internal;` x24,
`attr interface=[` x19, `];` x19, `attr flag=frob_check_exec_kill_switch;` x8,
`access "tickets_ledger" mode write;` x5, `owns "tickets.md" "0644";` x5,
`label Internal;` x4, `attr local;` x4. The header comment block alone runs ~50
lines and contains a paragraph explaining that a previous version of the header
was wrong.

WHY SPLITTING ANSWERS IT: per-module files make each of those restatements a
single statement in the module that owns it. The contention half of the finding
resolves the same way -- 434 commits in 60 days and 65 open tickets naming this
one file (SF-01, SF-06) is a monofile problem, and a module's model is leased
with that module once split.

WHY NO TOOL: deciding which module owns which node IS the design work. A
mechanical splitter would relocate text without making that judgment, and would
produce a plausible-looking split nobody had thought about. This also disposes of
option 3 ("split first with a tool, defaults later") -- there is no automated
first pass.

WHY NOT OPTION 1 (grammar defaults/inheritance): the module boundary becomes the
unit of sharing, and a defaults block would be a second competing mechanism for
the same thing. Consistent with D-M8 on T-4677, which refuses templated assumes
on the same reasoning.

WHAT THIS SETTLES THAT WAS OPEN: the body previously asked the owner to
coordinate this with T-4598 (append-shared registry files) because the two
attacked the same contention from opposite directions. D-M6 settles it: the
split is the answer for the model, and T-4598 remains the right fix for the
registry files that are not split.

WHERE THE WORK GOES: the hand split belongs to the module-system story being
filed by the other planner. One consequence was propagated out of this ticket --
T-4668's body now requires the single ratchet-lock loader/writer to be designed
for per-module lock files (design/<module>.via.lock.json) from the start, since
migration step 7 splits the lock per module.

NO BEHAVIOR CHANGE: no code, model or documentation file was modified under this
ticket. The Changed section is empty by design.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)
