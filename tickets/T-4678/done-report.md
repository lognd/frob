## Done report

DECISION ticket. Its only deliverable is an owner decision recorded in the body,
and the owner recorded it on 2026-09-19.

DECISION: NO DELETIONS. Dormant keywords are WIRED, not removed. The governing
rule is the owner's: "err on the side of adding capabilities; we originally had
a good idea and then forgot to implement it."

WHY NONE OF THE THREE OPTIONS SURVIVED AS FRAMED: the pessimistic keyword audit
(scratchpad/STRATA-KEYWORDS.md, 139 rows) returned 43 KEEP, 24 LITMUS-ONLY,
68 DORMANT, 4 DEAD-CANDIDATE and 0 DEAD. The delete list is EMPTY, so option 1
(retire the dead surfaces) has nothing to operate on and option 3 loses its
retiring half. Option 2 (exercise rather than retire) survives, generalised.

THE TWO CORRECTIONS TO SF-09, both recorded on this ticket's body because they
are corrections to this ticket's own evidence:

1. COMMENT INFLATION. SF-09 counted raw grep over design/frob.strata, which is
   70% comment prose (SF-10). Stripping comments and string literals drops 32
   keywords from non-zero to zero. The honest in-repo unused figure is 86, not
   56 -- SF-09 UNDERCOUNTED the disuse.
2. CONSUMER DESIGNS. Twelve .strata files in sibling checkouts total 5,682
   lines, twice design/frob.strata's size, and SF-09 never looked at them.
   Fourteen keywords are used only there, seven of them the whole vmodel family
   (vmodel.strata: kind x1292, dst x764, runnable x269, code_ref x259).
   SF-09 would have had them deleted.

Both corrections are recorded on the ticket rather than silently fixed in the
audit file, so the original overreach stays visible to anyone who reads the
SF-09 evidence later. This is the concrete instance of
memory/silent-zero-is-the-dominant-bug-class.md: a zero in a corpus you did not
search is not a zero, and here it was nearly a deletion order.

WHERE THE WORK GOES: three follow-ups are filed separately -- the boundary
`admit` WIRE leaf, the `forbid call`/`forbid import` enforcement WIRE leaf, and
the kernel.md eight-domains docs leaf plus per-domain decisions tracked on
T-4681.

NO BEHAVIOR CHANGE: no keyword was deleted, no parser, elaborator or gate was
touched, and no file changed under this id. The Changed section is empty by
design.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)
