---
id: T-2313
title: rapid-sweep auto-filer writes a genuinely-empty (rule, file) identity into
  a ticket body (observed in T-2297)
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
evidence_scope:
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_rapid_sweep.py::TestNormalizeIdentities::test_drops_genuinely_empty_identity_pair
- tests/unit/test_rapid_sweep.py::TestNormalizeIdentities::test_leaves_well_formed_pairs_untouched
- tests/unit/test_rapid_sweep.py::TestNormalizeIdentities::test_partial_identity_one_field_empty_is_kept
designated_repro_test: tests/unit/test_rapid_sweep.py::TestNormalizeIdentities::test_drops_genuinely_empty_identity_pair
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 21390b41c73ff7647b292947a79c3d54c84ca186
---
The rapid post-land sweep auto-filer can write a (rule, file) identity with
BOTH fields empty into a ticket body. Observed verbatim in T-2297 (now
landed, kind=bug, "post-land sweep regression from T-1783"), quoted exactly
as it rendered in `frob ticket show T-2297` before I fixed T-2297's other,
real findings:

New (rule, file) identit(ies) filed here:

    -   
    E402  /home/logan/projects/frob/scripts/fleet_status.py
    E501  /home/logan/projects/frob/scripts/fleet_status.py
    E501  /home/logan/projects/frob/src/frob/lang/_nodes.py
    F541  /home/logan/projects/frob/tests/test_ticket_work_and_land_finish.py
    F841  /home/logan/projects/frob/tests/test_ticket_land.py

And in the attribution section immediately below it, the SAME blank entry
recurs:

    -     -> UNATTRIBUTED (no batch commit's touched symbols reach this
    finding); candidate commits: []

The other five entries in that same ticket all have a real, well-formed
`RULE  path` pair; only the first is empty on both fields. This is a
sibling defect to T-2312 (auto-filer skips DISPOSAL on a duplicate-title
decline) but distinct: T-2312's three pinned findings had real, well-formed
rule/file identities and NO owning ticket; this one has NO identity at all
-- rule and file are both empty strings (or None rendered as blank) -- yet
it was still written into a ticket body as if it were a real finding.

RISK: T-2312's own investigation shows quarantine has been pinned twice in
one day by findings with missing/mismatched identity data (`commit=None,
ticket=None`, and separately a path-shape mismatch between absolute- and
relative-path identities). A finding with a genuinely EMPTY (rule, file)
pair is a more extreme version of the same identity-integrity gap:
`dispose`/`--file-ticket`/auto-filer dedup logic that keys off (rule, file)
cannot address, attribute, or dedup an entry with no key at all, and the
quarantine store's own `dispose` path is already known (see the "Quarantine
unclearable: empty finding" precedent, T-2207) to reject a genuinely
identity-less record as malformed rather than clearing it -- so this shape
of finding is a plausible NEW way to pin quarantine unclearably, not
observed to have fired yet but structurally reachable from the same code
path T-2312 is fixing.

Likely origin: `_rapid_sweep.py`'s per-identity ticket-body renderer
iterating over a (rule, file) collection that can contain an empty/None
tuple -- worth checking whether the underlying attribution/collection step
(`_attribute_new_findings` / `_partition_findings_by_attribution`, both
referenced in T-2260/T-2206/T-2297's own attribution sections) can produce
a zero-length key, or whether this is a rendering-layer bug that drops the
rule/file text but keeps the row.

Not filed as a duplicate of T-2312: T-2312's acceptance criteria are about
the DISPOSAL gap on a well-formed duplicate finding; this is about a
malformed EMPTY finding entering a ticket body in the first place. Related,
not identical -- flagging the connection for whoever picks up T-2312 so the
same investigation can check whether their fix also needs to handle (or
explicitly reject) an empty identity.