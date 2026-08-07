---
id: T-1164
title: 'strata: blast-radius scan spuriously fires for nodes with no declared runs_as
  (None treated as a real compromised-user identity)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_audit.py
- tests/unit/strata/test_audit.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_audit.py
  reason: regression test lives here per playbook evidence convention
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/strata/test_audit.py::TestHostWiring::test_owns_without_runs_as_no_blast_radius_scenario
designated_repro_test: null
threat: null
component: null
---
`_audit.py::_blast_radius_gaps_per_user` (`src/frob/strata/_audit.py`)
builds its per-user blast-radius scan set as:

```
users = sorted({
    manifest.runs_as
    for node in model.nodes
    if (manifest := host_manifest_for(node)) is not None
})
```

`host_manifest_for(node)` returns non-`None` the moment a node declares
ANY std.host construct at all (`owns`/`acl`/`unit`/`listens`/`runs_as`
per its own docstring) -- `manifest.runs_as` is independently optional
and legitimately `None` when a node declares e.g. `owns` but no
`runs_as` service-account claim. The comprehension above does not filter
that out: a bare `None` lands in `users` as if it were a real
compromised-user identity, and `build_compromised_user_scenario(model,
None, "compromised-user:None")` then runs a full blast-radius scan
treating "no declared service user" as its own reachability scenario,
firing `HOST-BLAST` "influence path X -> Y with no boundary" for every
node reachable from any node whose `owns`/`acl` claim (with no
`runs_as`) triggered the manifest.

Reproduced directly: `design/frob.strata`'s five `tickets_ledger`
writer nodes (`cli`/`gates`/`fleet`/`core`/`serve`) never declared any
std.host construct before T-1158. The moment T-1158 added `owns
"tickets.md" "0644";` to close out the SYS205 waivers, `frob sys audit`
went from 13 checked views (no blast-radius entry at all -- an empty
`users` set) to 14, with a new `host:blast-radius:None` view firing 10
new unwaived `HOST-BLAST` gaps, none of which existed, or were
intended, before -- these nodes are plain trusted repo-internal
components, not services running as any particular OS user, and "None"
is not a real compromised-user identity to model a blast radius against.

Fix: `_blast_radius_gaps_per_user` should exclude manifests whose
`runs_as` is `None` from the `users` set (or otherwise skip the
per-user scenario when there is no real declared service-account
identity to scan against) -- a node declaring pure path ownership
(`owns`/`acl`) with no `runs_as` has nothing for a "compromised user"
scenario to represent.

Blocks T-1158 (`design/frob.strata`'s owns= declarations for the
tickets_ledger writers cannot land clean until this is fixed -- `frob
sys audit`/SELFAUDIT001 would go from 5 pre-existing unrelated gaps to
15).