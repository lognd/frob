+++
id = "01M12TN67V4ZDWR934C439DB86"
title = "WAIVE009 ignores follow_up=, only scans reason= prose for a resolving ticket id"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-08-28T00:00:00Z"
updated = "2026-10-04T21:07:33Z"
aliases = ["T-3323"]
labels = ["milestone:1.1.0", "v1-cluster:F1"]
scope = ["src/frob/gates/_waive.py"]
+++

REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-052 -- this entry
appeared in FROBLEMS.md AFTER this triage drive started; filed promptly
rather than left for a later pass since the reporter already pinned the
exact code path).

CONFIRMED BY THE REPORTER'S OWN CODE CITATION (re-verify against current
main before fixing, in case this has already moved): `frob.gates._waive`'s
`_reason_ticket_ids` extracts bare `T-\d+` tokens ONLY from the `reason=`
attribute's prose, and only when that prose matches one of a fixed set of
"promise phrase" regexes ("once X lands", "follow-up ticket", etc). It never
reads the STRUCTURED `follow_up=`/`ticket=` attribute at all.

IMPACT: an idiomatic `frob:waive WIRE001 ... follow_up="T-0005"` -- copied
from an existing waiver in the same file, with `follow_up=` correctly
naming a real, open ticket -- fails WAIVE009 ("cites no ticket id that
resolves in the queue") whenever the `reason=` prose happens to use
promise-phrase wording without ALSO spelling the ticket id inline in that
prose. Reported cost: three separate WAIVE009 failures on one ticket (T-0041
in diax), diagnosable only by reading frob's own gate source -- neither the
WAIVE009 message nor any repo doc says `follow_up=` is insufficient on its
own.

WHAT NOT TO DO: do not fix this by DROPPING the promise-phrase check and
accepting any `follow_up=` unconditionally regardless of the reason text --
if the two attributes are meant to agree (reason describes what will
resolve it, follow_up names who), silently ignoring a mismatch between them
would hide a real bookkeeping error (e.g. a copy-pasted follow_up that no
longer matches the reason).

WHAT TO BUILD: pick one, state which, and make WAIVE009's message and any
docs agree with it:
  (a) have WAIVE009 ALSO count `follow_up=`/`ticket=` as valid ticket-id
      evidence, independent of whether the `reason=` prose matches a
      promise-phrase regex -- the reporter's first suggested fix; or
  (b) keep `follow_up=` insufficient on its own by design, but say so
      PLAINLY in the WIRE001/WAIVE009 finding message itself (not buried in
      source), so the next person does not have to read `_waive.py` to
      learn the rule.

MUST-FIRE FIXTURE: a `frob:waive` whose `reason=` names a ticket id that is
NOT open/does not resolve (whether inline or via follow_up=) -- WAIVE009
must still fire.

MUST-STAY-QUIET FIXTURE: a `frob:waive WIRE001 reason="wired once X lands"
follow_up="T-XXXX"` where T-XXXX is a real, open ticket -- if (a) is built,
0 WAIVE009 findings; if (b) is built, the message must make the fix
(spell the id inline) obvious without reading source.
