## Done report

Established denominator directly: `frob check --only cycle --no-cache` reports
exactly one ERROR-severity CYCLE001 spanning 175 unique files across 15
packages, matching the ticket's own ~180/~15 estimate. Cross-checked with an
independent ast-based module import graph (609 edges) and a from-scratch
Tarjan pass -- both confirm a single 175-node SCC.

Tested the working hypothesis (a small number of hub files chain tighter
sub-cycles into one reported SCC) directly by removing top-K highest-degree
files and re-running Tarjan: removing the single biggest package __init__.py
(gates, 65 combined edges) still leaves a 133-node SCC; removing the three
biggest package __init__.py files (gates/tickets/strata) leaves 82; removing
the top 20 files by degree (>11% of the cluster) still leaves a 10-node
residual SCC. Finding: this cluster does NOT decompose via a small hub set --
the coupling is diffuse, not concentrated behind a handful of chokepoints.
Recorded package-level seams (tickets<->app.ticket_runner,
gates<->strata<->tickets three-way cycle) as the more scopeable target for
follow-on leaf tickets instead.

Answered the doc's open question by sampling edge-resolution methods: 912 of
946 raw import matches resolve because the imported package itself is
directly tracked (edges any pre-T-2211/T-2219 resolver would already find);
only 34 resolve solely via the submodule-reexport-chain fix T-2211/T-2219
added. Conclusion: the growth reflects newly-accurate detection of real,
pre-existing debt, not a detector-growth artifact.

No src/ files touched, per this ticket's own acceptance -- deliverable is
docs/investigations/T-2202-mega-cluster.md only.

### Changed
```
 docs/investigations/T-2202-mega-cluster.md | 128 +++++++++++++++++++++++++++++
 tickets/T-2057/ticket.md                   |   8 ++
 tickets/T-2234/ticket.md                   |  21 ++++-
 3 files changed, 154 insertions(+), 3 deletions(-)
```

### Evidence
- `cmd:bash -c "wc -l docs/investigations/T-2202-mega-cluster.md && grep -n 'does not decompose' docs/investigations/T-2202-mega-cluster.md && grep -n 'Answer:' docs/investigations/T-2202-mega-cluster.md" exit=0 sha256=3ce4bc59a52b` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 18 error(s), 809 warning(s), 708 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PRE001@tickets/T-2234, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
