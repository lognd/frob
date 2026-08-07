## Done report

Fixes the five T-0260 malmberg pilot findings in the deploy generator, all
scoped to src/frob/deploy/_generate.py plus docs/commands/deploy.md and
tests/unit/deploy/test_generate.py:

- Item 5: a `runs_as` identity shared by two nodes/stores (e.g. a store and
  its consuming node both declaring the same service user) previously
  rendered its `useradd`/`userdel` guard block once per sharing entry.
  `_distinct_runs_as` collapses entries to distinct identities so each
  renders exactly once, in both install.sh and uninstall.sh.
- Item 8: `may net` unconditionally granted `CAP_NET_BIND_SERVICE` even
  when every declared `listens` port was unprivileged (>=1024).
  `_node_capabilities` now only grants it when a declared port is
  actually privileged (<1024).
- Item 6: a declared `listens` port drove status.sh's `/dev/tcp` probe but
  was never materialized into the generated unit itself. The unit file
  now carries a `# listens: PORT` comment. Full kernel-level network
  hardening (`IPAddressAllow=`/`SocketBindAllow=`) is not emitted --
  `std.host` has no inbound/outbound direction vocabulary yet, and a
  fabricated allow-list built off `listens` alone would be dishonest;
  this scope cut is documented in docs/commands/deploy.md.
- Item 4 (DEBUG flood): `generate_all` previously called
  `sorted_manifest_entries` three times (once per script), tripling
  `host_manifest_for`'s per-node debug log line for one CLI invocation.
  `generate_all` now computes the walk once and shares it across all
  three renderers via new private `_render_install_script` /
  `_render_status_script` / `_render_uninstall_script` helpers.
- Item 7 (multi-host status): status.sh always probes 127.0.0.1
  regardless of which physical host a unit actually runs on --
  `std.host` has no host/placement vocabulary yet to fix this properly.
  status.sh now carries an explicit NOTE comment documenting the
  limitation and instructing the operator to run it per declared host.
  The real fix (a placement construct) is filed as a separate ticket
  since it needs new strata-core grammar, well beyond this ticket's
  scope.
- Item 10 (doc): documented in docs/commands/deploy.md how to read
  waivers back off a parsed std.host model (the separate `_waive`
  channel, not `elaborate(...).danger_ok`).

Two regression tests were added per reviewer request covering item 5
specifically: TestInstall.test_shared_runs_as_useradd_block_rendered_once
and TestUninstall.test_shared_runs_as_userdel_block_rendered_once, each
building a two-node model sharing one runs_as identity and asserting
exactly one useradd/userdel guard block renders.

Gates: two pre-existing, out-of-scope gate errors remain on the tree
(DRIFT002 in tests/test_tickets_evidence_cli.py, REL001 version-bump-
needed) plus one pre-existing ty diagnostic in
tests/unit/strata/test_threat.py -- all three verified (via git stash in
an earlier round) to predate this ticket's changes and to be outside its
declared scope. No new gate violation was introduced by this ticket.

### Changed
```
 docs/commands/deploy.md            |  39 ++++
 src/frob/deploy/_generate.py       | 186 +++++++++++++++---
 tests/unit/deploy/test_generate.py |  70 ++++++-
 tickets.md                         | 383 +++++++++++++++++++++++++++++++++++--
 4 files changed, 634 insertions(+), 44 deletions(-)
```

### Evidence
(no evidence recorded)
