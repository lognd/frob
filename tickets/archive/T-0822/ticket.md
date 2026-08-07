---
id: T-0822
title: 'vet: wire net_enabled kill-switch into vet''s network call sites'
state: done
kind: security
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- tests/test_vet.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestRegistryLookup::test_fetch_publish_date_refuses_when_net_disabled
- tests/test_vet.py::TestNvdLookup::test_fetch_cwe_for_cve_refuses_when_net_disabled
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
designated_repro_test: null
acceptance:
- text: Given FROB_DISABLE_NET=1, when vet looks up a registry publish date or an
    NVD CVE->CWE mapping, then no urlopen call happens and the result degrades to
    ok=False with a "net disabled" note.
  evidence:
  - tests/test_vet.py::TestRegistryLookup::test_fetch_publish_date_refuses_when_net_disabled
  - tests/test_vet.py::TestNvdLookup::test_fetch_cwe_for_cve_refuses_when_net_disabled
- text: Given design/frob.strata's vet node, when frob sys audit runs, then the node
    declares a real attr flag=<id> kill-switch and carries no LINT004 waiver.
  evidence:
  - tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
  - tests/test_vet.py::TestRegistryLookup::test_fetch_publish_date_refuses_when_net_disabled
threat: null
component: null
---
Dispatch referenced ticket id T-0817 ("vet: wire net_enabled kill-switch
into vet's network call sites"), but no such ticket exists in
tickets.md/tickets-archive.md (`frob ticket show T-0817` -> "no ticket
T-0817"). Filing the real ticket here so the implementation has a real
frob:ticket edge to bind evidence to, per the ticket's own instructions
("do not force it ... file a ticket").

Survey (done as part of this ticket): vet has two real, live outbound
`urllib.request.urlopen` call sites -- src/frob/vet/_registry.py::
_result_from_network (publish-date lookups) and src/frob/vet/_nvd.py::
_fetch_from_network (CVE->CWE lookups). `_osv.py` and `_popular_*.py`
do not make network calls (osv-scanner subprocess / static curated
lists respectively). design/frob.strata's `vet` node already declares
`may "net"` with a `waive "LINT004"` pointing at T-0200, and T-0200
already built the real mechanism (`frob.process.net_enabled()` /
`FROB_DISABLE_NET`, `src/frob/process/_guard.py`) but left it unwired
pending a real net call site -- this ticket is that wiring.

Plan: gate both `urlopen` sites behind `net_enabled()`, degrading to the
existing `ok=False` "could not verify" shape each site's docstring
already commits to for a network failure (VET011's offline-must-never-
hard-block posture) -- a disabled kill switch is not a new failure mode,
it degrades identically to an unreachable host. Declare `attr
flag=frob_vet_net_kill_switch;` on the `vet` node in design/frob.strata
and delete the LINT004 waiver (mirrors the T-0769 stratamod precedent).
Add tests with a no-connect `urlopen` spy proving the switch
short-circuits before any socket opens.