## Done report

std.host gains a Windows platform, mirroring the linux/systemd model
T-0255 established: `HostPlatform.WINDOWS` plus five new node/store
clauses -- `platform "windows"` (discriminator), `service_account "NAME"
[gmsa]` (Windows analog of `runs_as`: dedicated low-priv account or a
group Managed Service Account), `service` (Windows analog of `unit`: an
SCM service binding), `acl "PATH" "RULE"` (Windows analog of `owns`: an
NTFS DACL entry expressing per-principal rights, deny ACEs, and
deny-inheritance -- richer than a 3-octal mode), and `pipe "NAME"` (named
pipes, additive to the already-platform-agnostic `listens` PORT surface
Windows firewall ports reuse unchanged). Grammar lives in
strata-core/src/parse.rs (parse_node + parse_store, mirroring every
existing std.host clause's node/store symmetry), read back into
HostManifest via src/frob/strata/_host.py, threaded through
_elaborate.py/_infra.py's shared _host_attrs desugar. tmLanguage keyword
list updated so the new keywords keep syntax highlighting.

A real encoding bug was caught and fixed during implementation: a naive
`path:rule` colon-separator for the acl attr collides with a Windows
drive-letter colon (`C:\ProgramData\api`) and with RULE's own internal
colons (`PRINCIPAL:RIGHTS:deny`) -- switched to `|`, which cannot appear
in a Windows path.

Cut (disclosed, not silently dropped, matching T-0255's own manifest-only
precedent for linux): no windows-side deploy generator, conformance
checker, or VM auditor, and -- most importantly -- HOST001/HOST002 and
_scenarios.py::build_compromised_user_scenario do NOT yet branch on
service_account/acl/pipes at all, so a windows-only node produces no
movement-impossibility findings today, not because it is proven isolated
but because nothing reads its windows-shaped facts yet. This mirrors
T-0256/T-0257/T-0258/T-0259's staged sequencing after T-0255 and is
documented in docs/strata/host.md's Scope boundary section. Filed
T-0606 (ex-draft, id lost at land) to wire HOST001/HOST002/the compromised-user scenario
builder to the Windows fields.

### Changed
```
 docs/strata/host.md                                | 155 +++++-
 .../vscode-strata/syntaxes/strata.tmLanguage.json  |   2 +-
 src/frob/strata/_ast.py                            |  54 ++
 src/frob/strata/_elaborate.py                      |   9 +-
 src/frob/strata/_host.py                           | 202 ++++++-
 src/frob/strata/_infra.py                          |   9 +-
 strata-core/src/parse.rs                           | 194 +++++++
 .../strata/litmus/host_windows_declared.strata     |  26 +
 tests/unit/strata/test_host.py                     | 108 ++++
 tests/unit/strata/test_litmus_host.py              |  24 +
 tickets.md                                         | 588 ++++++++++++++++++++-
 11 files changed, 1335 insertions(+), 36 deletions(-)
```

### Evidence
(no evidence recorded)
