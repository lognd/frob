+++
id = "01M1T07NZW282WVXGBXCGQFD33"
title = "H3-3: units/epoch obligation on time-typed ABI parameters"
type = "story"
flavour = "quality_objective"
category = "triage"
priority = "low"
parent = "01M1T07NZSWG65V1BFPEJK6SE6"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-04T21:05:38Z"
aliases = ["T-4092"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/gates/_inv.py"]

[[acceptance]]
text = "given a design note settling the frob:invariant form for naming an ABI parameter's epoch/units explicitly, when this ticket's design step completes, then the note is attached before implementation"
bound = false

[[acceptance]]
text = "given a time-typed ABI parameter with no bound epoch invariant, when the check runs, then it is flagged as underspecified"
bound = false
+++

H3-3 (F-296). Same structural theme as H3-1a (this epic): a prose contract enforced on one side of an ABI boundary and unenforced/ambiguous on the other. Here BOTH implementations are internally consistent and match each other exactly -- a parity gate (like H3-1a's) is the WRONG instrument for this one; the gap is purely in what the shared prose contract fails to say.

VERIFIED: git grep for a units/epoch obligation construct over a time-typed parameter found nothing in src/frob.

FINDING THIS WOULD HAVE CAUGHT: COMP-1703/COMP-1712 both say a value is "time-decaying" WITHOUT NAMING THE EPOCH (what zero means -- seconds since process start, since the originating pointer event, since the Unix epoch, etc.), so the caller was free to pass a different clock than the callee assumed. Both sides implement the SAME wrong assumption consistently, so no diff/parity check would ever catch it -- the defect is that the CONTRACT itself is underspecified in prose, not that the two implementations disagree.

Proposed: a units/epoch obligation on a time-typed ABI parameter -- a frob:invariant naming the parameter's epoch explicitly (their worked example: "hotspot_bands' time is seconds since the originating pointer event") bound to a test that passes a large page-clock value (a value that would only make sense under a wrong-epoch assumption) and asserts the expected behavior (their example: the ripple effect is still present) still holds. This generalizes beyond time: any ABI parameter whose UNITS or REFERENCE FRAME are stated in prose only (a distance in what unit, an angle in degrees vs radians) is the same underspecified-contract shape -- scope this ticket to the time/epoch case specifically as the first instance, and note the generalization as a possible follow-up rather than building it now.
