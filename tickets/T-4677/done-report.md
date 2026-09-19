## Done report

DECISION ticket. Its only deliverable is an owner decision recorded in the body,
and the owner recorded it on 2026-09-19 as D-M8.

DECISION: assumes become MODULE-OWNED and SPECIFIC, and a structural gate
REFUSES templated assumes.

This rejects the framing of all three options the ticket offered, rather than
picking one. Option 1 (a class-level/quantified assume) would have made the
templating cheaper to express; D-M8 makes it illegal instead. Option 2
(defaults/inheritance) is superseded, because the unit that carries the posture
is now the module, not a defaults block. Option 3 (a generator) is the direct
opposite of the decision.

WHAT THE EVIDENCE WAS (SF-08, measured at HEAD c8f56ef10): all 33 assume
statements in design/frob.strata match one template,
`assume "weakness:CWE-NNN:<node>" noflow registry -> <node> owner logan review
"2026-10-15"` -- CWE-78 x18, CWE-94 x6, CWE-89 x3, CWE-502 x2, CWE-639 x2,
CWE-918 x2, one owner, one date for all 33, and zero assumes of any other shape
though the kernel defines bound/reach/frame. Growth was (nodes x weaknesses).

WHERE THE WORK GOES: the module-system story being filed by the other planner
owns the structural gate that refuses templated assumes and the rewrite of the
33 existing ones. Nothing is implemented under this id.

WHAT IS UNAFFECTED: T-4675 (SF-07) still lands independently. It makes an
overdue assume review a gate failure regardless of who owns the assume, and it
is the critical leaf with 26 days to the shared 2026-10-15 expiry. D-M8 removes
the shared cliff going forward by giving each module its own review cadence; it
does not wire the verdict, which is what T-4675 does.

NO BEHAVIOR CHANGE: no code, model or documentation file was modified under this
ticket. The Changed section is empty by design.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)
