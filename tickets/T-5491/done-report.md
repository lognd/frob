## Done report

Four lands (T-5326, T-5324, T-5474, T-5475) refused with DirtyMain even
though the entire drift was one or two tickets/**-only sibling commits --
exactly what T-4572's ledger-only CAS-retry fast path exists to absorb.

Root cause (measured in /tmp/land-T-5464.log ~line 39087): the fast path
DID trigger, but on its first attempt the rebase failed to apply cleanly
(a text conflict between this land's own composed diff and a genuinely
ledger-only sibling commit touching the same ticket.md), and the loop's
prior boolean/None return collapsed "not ledger-only, give up" and "IS
ledger-only, apply conflicted" into one give-up outcome -- so it refused
after exactly one attempt while its own log line claimed the 5-attempt
bound was exhausted.

Fix distinguishes the two outcomes, retries an apply conflict with a
capped backoff (the conflicting sibling commit is not necessarily the
ref's newest one), and scales the attempt bound to the sibling-commit
count already observed at loop entry, capped at 25.

docs/modules/tickets-landing.md is currently under T-draft-342a3548's
live scope lease (same file, unrelated ticket in progress in another
worktree) so the doc update for this section could not be added in this
pass; filed as a follow-up, see Done report.

### Changed
```
 .claude/hooks/_root_write_guard_lib.py             |    24 +-
 .claude/hooks/_shellscan.py                        |   104 +
 .claude/hooks/diagnosis-nudge.py                   |     1 -
 .claude/hooks/dispatch-telemetry.py                |    12 +
 .claude/hooks/frob-directive-guard.py              |     7 -
 .claude/hooks/frob-suggest.py                      |   186 +-
 .claude/hooks/frob-timeout-guard.py                |   127 +-
 .claude/hooks/pgrep-self-match-guard.py            |   139 +
 .claude/hooks/sync-claude-config.py                |   240 +-
 .claude/hooks/tool-call-telemetry.py               |   111 +-
 .claude/settings.json                              |    11 +
 .frob-release.json                                 |     2 +-
 .github/dependabot.yml                             |     1 +
 .github/workflows/ci.yml                           |   123 +-
 .github/workflows/release.yml                      |    45 +-
 CHANGELOG.md                                       |   272 +
 changelog.d/T-2965.md                              |     2 +
 changelog.d/T-3020.md                              |     2 +
 changelog.d/T-3032.md                              |     2 +
 changelog.d/T-3082.md                              |     2 +
 changelog.d/T-3232.md                              |     2 +
 changelog.d/T-3233.md                              |     2 +
 changelog.d/T-3412.md                              |     2 +
 changelog.d/T-3612.md                              |     2 +
 changelog.d/T-3613.md                              |     2 +
 changelog.d/T-3614.md                              |     2 +
 changelog.d/T-3615.md                              |     2 +
 changelog.d/T-3802.md                              |     2 +
 changelog.d/T-3851.md                              |     2 +
 changelog.d/T-3856.md                              |     2 +
 changelog.d/T-3861.md                              |     2 +
 changelog.d/T-3865.md                              |     2 +
 changelog.d/T-3899.md                              |     2 +
 changelog.d/T-3943.md                              |     2 +
 changelog.d/T-3953.md                              |     2 +
 changelog.d/T-3961.md                              |     2 +
 changelog.d/T-3962.md                              |     2 +
 changelog.d/T-3964.md                              |     2 +
 changelog.d/T-3986.md                              |     2 +
 changelog.d/T-3993.md                              |     2 +
 changelog.d/T-3995.md                              |     2 +
 changelog.d/T-3997.md                              |     2 +
 changelog.d/T-4073.md                              |     2 +
 changelog.d/T-4111.md                              |     2 +
 changelog.d/T-4112.md                              |     2 +
 changelog.d/T-4114.md                              |     2 +
 changelog.d/T-4115.md                              |     2 +
 changelog.d/T-4116.md                              |     2 +
 changelog.d/T-4118.md                              |     2 +
 changelog.d/T-4212.md                              |     2 +
 changelog.d/T-4214.md                              |     2 +
 changelog.d/T-4221.md                              |     2 +
 changelog.d/T-4230.md                              |     2 +
 changelog.d/T-4240.md                              |     2 +
 changelog.d/T-4254.md                              |     2 +
 changelog.d/T-4379.md                              |     2 +
 changelog.d/T-4413.md                              |     2 +
 changelog.d/T-4414.md                              |     2 +
 changelog.d/T-4415.md                              |     2 +
 changelog.d/T-4416.md                              |     2 +
 changelog.d/T-4419.md                              |     2 +
 changelog.d/T-4420.md                              |     2 +
 changelog.d/T-4421.md                              |     2 +
 changelog.d/T-4437.md                              |     2 +
 changelog.d/T-4491.md                              |     2 +
 changelog.d/T-4492.md                              |     2 +
 changelog.d/T-4493.md                              |     2 +
 changelog.d/T-4494.md                              |     2 +
 changelog.d/T-4495.md                              |     2 +
 changelog.d/T-4496.md                              |     2 +
 changelog.d/T-4498.md                              |     2 +
 changelog.d/T-4501.md                              |     2 +
 changelog.d/T-4502.md                              |     2 +
 changelog.d/T-4503.md                              |     2 +
 changelog.d/T-4506.md                              |     2 +
 changelog.d/T-4507.md                              |     2 +
 changelog.d/T-4508.md                              |     2 +
 changelog.d/T-4509.md                              |     2 +
 changelog.d/T-4510.md                              |     2 +
 changelog.d/T-4511.md                              |     2 +
 changelog.d/T-4512.md                              |     2 +
 changelog.d/T-4514.md                              |     2 +
 changelog.d/T-4516.md                              |     2 +
 changelog.d/T-4517.md                              |     2 +
 changelog.d/T-4518.md                              |     2 +
 changelog.d/T-4519.md                              |     2 +
 changelog.d/T-4520.md                              |     2 +
 changelog.d/T-4521.md                              |     2 +
 changelog.d/T-4522.md                              |     2 +
 changelog.d/T-4523.md                              |     2 +
 changelog.d/T-4524.md                              |     2 +
 changelog.d/T-4531.md                              |     2 +
 changelog.d/T-4532.md                              |     2 +
 changelog.d/T-4535.md                              |     2 +
 changelog.d/T-4536.md                              |     2 +
 changelog.d/T-4540.md                              |     2 +
 changelog.d/T-4543.md                              |     2 +
 changelog.d/T-4546.md                              |     2 +
 changelog.d/T-4547.md                              |     2 +
 changelog.d/T-4548.md                              |     2 +
 changelog.d/T-4550.md                              |     2 +
 changelog.d/T-4552.md                              |     2 +
 changelog.d/T-4553.md                              |     2 +
 changelog.d/T-4554.md                              |     2 +
 changelog.d/T-4555.md                              |     2 +
 changelog.d/T-4556.md                              |     2 +
 changelog.d/T-4560.md                              |     2 +
 changelog.d/T-4561.md                              |     2 +
 changelog.d/T-4562.md                              |     2 +
 changelog.d/T-4563.md                              |     2 +
 changelog.d/T-4572.md                              |     2 +
 changelog.d/T-4578.md                              |     2 +
 changelog.d/T-4579.md                              |     2 +
 changelog.d/T-4582.md                              |     2 +
 changelog.d/T-4583.md                              |     2 +
 changelog.d/T-4588.md                              |     2 +
 changelog.d/T-4596.md                              |     2 +
 changelog.d/T-4599.md                              |     2 +
 changelog.d/T-4607.md                              |     2 +
 changelog.d/T-4611.md                              |     2 +
 changelog.d/T-4612.md                              |     2 +
 changelog.d/T-4623.md                              |     2 +
 changelog.d/T-4624.md                              |     2 +
 changelog.d/T-4625.md                              |     2 +
 changelog.d/T-4626.md                              |     2 +
 changelog.d/T-4627.md                              |     2 +
 changelog.d/T-4628.md                              |     2 +
 changelog.d/T-4629.md                              |     2 +
 changelog.d/T-4630.md                              |     2 +
 changelog.d/T-4631.md                              |     2 +
 changelog.d/T-4632.md                              |     2 +
 changelog.d/T-4633.md                              |     2 +
 changelog.d/T-4634.md                              |     2 +
 changelog.d/T-4641.md                              |     2 +
 changelog.d/T-4642.md                              |     2 +
 changelog.d/T-4645.md                              |     2 +
 changelog.d/T-4646.md                              |     2 +
 changelog.d/T-4649.md                              |     2 +
 changelog.d/T-4650.md                              |     2 +
 changelog.d/T-4657.md                              |     2 +
 changelog.d/T-4659.md                              |     2 +
 changelog.d/T-4660.md                              |     2 +
 changelog.d/T-4661.md                              |     2 +
 changelog.d/T-4663.md                              |     2 +
 changelog.d/T-4669.md                              |     2 +
 changelog.d/T-4673.md                              |     2 +
 changelog.d/T-4675.md                              |     2 +
 changelog.d/T-4684.md                              |     2 +
 changelog.d/T-4688.md                              |     2 +
 changelog.d/T-4689.md                              |     2 +
 changelog.d/T-4690.md                              |     2 +
 changelog.d/T-4692.md                              |     2 +
 changelog.d/T-4693.md                              |     2 +
 changelog.d/T-4694.md                              |     2 +
 changelog.d/T-4695.md                              |     2 +
 changelog.d/T-4696.md                              |     2 +
 changelog.d/T-4697.md                              |     2 +
 changelog.d/T-4698.md                              |     2 +
 changelog.d/T-4702.md                              |     2 +
 changelog.d/T-4709.md                              |     2 +
 changelog.d/T-4710.md                              |     2 +
 changelog.d/T-4711.md                              |     2 +
 changelog.d/T-4712.md                              |     2 +
 changelog.d/T-4713.md                              |     2 +
 changelog.d/T-4714.md                              |     2 +
 changelog.d/T-4715.md                              |     2 +
 changelog.d/T-4718.md                              |     2 +
 changelog.d/T-4719.md                              |     2 +
 changelog.d/T-4722.md                              |     2 +
 changelog.d/T-4723.md                              |     2 +
 changelog.d/T-4758.md                              |     2 +
 changelog.d/T-4760.md                              |     2 +
 changelog.d/T-4761.md                              |     2 +
 changelog.d/T-4763.md                              |     2 +
 changelog.d/T-4764.md                              |     2 +
 changelog.d/T-4767.md                              |     2 +
 changelog.d/T-4770.md                              |     2 +
 changelog.d/T-4805.md                              |     2 +
 changelog.d/T-4806.md                              |     2 +
 changelog.d/T-4911.md                              |     2 +
 changelog.d/T-4912.md                              |     2 +
 changelog.d/T-4913.md                              |     2 +
 changelog.d/T-4951.md                              |     2 +
 changelog.d/T-4952.md                              |     2 +
 changelog.d/T-4953.md                              |     2 +
 changelog.d/T-4991.md                              |     2 +
 changelog.d/T-4993.md                              |     2 +
 changelog.d/T-5034.md                              |     2 +
 changelog.d/T-5035.md                              |     2 +
 changelog.d/T-5036.md                              |     2 +
 changelog.d/T-5075.md                              |     2 +
 changelog.d/T-5084.md                              |     2 +
 changelog.d/T-5105.md                              |     2 +
 changelog.d/T-5108.md                              |     2 +
 changelog.d/T-5117.md                              |     2 +
 changelog.d/T-5120.md                              |     2 +
 changelog.d/T-5121.md                              |     2 +
 changelog.d/T-5122.md                              |     2 +
 changelog.d/T-5123.md                              |     2 +
 changelog.d/T-5124.md                              |     2 +
 changelog.d/T-5125.md                              |     2 +
 changelog.d/T-5126.md                              |     2 +
 changelog.d/T-5131.md                              |     2 +
 changelog.d/T-5132.md                              |     2 +
 changelog.d/T-5133.md                              |     2 +
 changelog.d/T-5134.md                              |     2 +
 changelog.d/T-5135.md                              |     2 +
 changelog.d/T-5136.md                              |     2 +
 changelog.d/T-5137.md                              |     2 +
 changelog.d/T-5138.md                              |     2 +
 changelog.d/T-5139.md                              |     2 +
 changelog.d/T-5151.md                              |     2 +
 changelog.d/T-5166.md                              |     2 +
 changelog.d/T-5190.md                              |     2 +
 changelog.d/T-5199.md                              |     2 +
 changelog.d/T-5201.md                              |     2 +
 changelog.d/T-5212.md                              |     2 +
 changelog.d/T-5215.md                              |     2 +
 changelog.d/T-5217.md                              |     2 +
 changelog.d/T-5219.md                              |     2 +
 changelog.d/T-5222.md                              |     2 +
 changelog.d/T-5228.md                              |     2 +
 changelog.d/T-5240.md                              |     2 +
 changelog.d/T-5242.md                              |     2 +
 changelog.d/T-5245.md                              |     2 +
 changelog.d/T-5247.md                              |     2 +
 changelog.d/T-5259.md                              |     2 +
 changelog.d/T-5261.md                              |     2 +
 changelog.d/T-5274.md                              |     2 +
 changelog.d/T-5275.md                              |     2 +
 changelog.d/T-5280.md                              |     2 +
 changelog.d/T-5286.md                              |     2 +
 changelog.d/T-5287.md                              |     2 +
 changelog.d/T-5289.md                              |     2 +
 changelog.d/T-5291.md                              |     2 +
 changelog.d/T-5292.md                              |     2 +
 changelog.d/T-5294.md                              |     2 +
 changelog.d/T-5295.md                              |     2 +
 changelog.d/T-5296.md                              |     2 +
 changelog.d/T-5299.md                              |     2 +
 changelog.d/T-5300.md                              |     2 +
 changelog.d/T-5301.md                              |     2 +
 changelog.d/T-5302.md                              |     2 +
 changelog.d/T-5303.md                              |     2 +
 changelog.d/T-5304.md                              |     2 +
 changelog.d/T-5305.md                              |     2 +
 changelog.d/T-5306.md                              |     2 +
 changelog.d/T-5307.md                              |     2 +
 changelog.d/T-5308.md                              |     2 +
 changelog.d/T-5309.md                              |     2 +
 changelog.d/T-5311.md                              |     2 +
 changelog.d/T-5313.md                              |     2 +
 changelog.d/T-5321.md                              |     2 +
 changelog.d/T-5322.md                              |     2 +
 changelog.d/T-5323.md                              |     2 +
 changelog.d/T-5324.md                              |     2 +
 changelog.d/T-5325.md                              |     2 +
 changelog.d/T-5333.md                              |     2 +
 changelog.d/T-5334.md                              |     2 +
 changelog.d/T-5335.md                              |     2 +
 changelog.d/T-5337.md                              |     2 +
 changelog.d/T-5339.md                              |     2 +
 changelog.d/T-5341.md                              |     2 +
 changelog.d/T-5347.md                              |     2 +
 changelog.d/T-5349.md                              |     2 +
 changelog.d/T-5350.md                              |     2 +
 changelog.d/T-5356.md                              |     2 +
 changelog.d/T-5360.md                              |     2 +
 changelog.d/T-5364.md                              |     2 +
 changelog.d/T-5376.md                              |     2 +
 changelog.d/T-5377.md                              |     2 +
 changelog.d/T-5378.md                              |     2 +
 changelog.d/T-5379.md                              |     2 +
 changelog.d/T-5380.md                              |     2 +
 changelog.d/T-5381.md                              |     2 +
 changelog.d/T-5382.md                              |     2 +
 changelog.d/T-5383.md                              |     2 +
 changelog.d/T-5384.md                              |     2 +
 changelog.d/T-5389.md                              |     2 +
 changelog.d/T-5392.md                              |     2 +
 changelog.d/T-5393.md                              |     2 +
 changelog.d/T-5394.md                              |     2 +
 changelog.d/T-5395.md                              |     2 +
 changelog.d/T-5396.md                              |     2 +
 changelog.d/T-5421.md                              |     2 +
 changelog.d/T-5436.md                              |     2 +
 changelog.d/T-5454.md                              |     2 +
 changelog.d/T-5464.md                              |     2 +
 design/frob.strata                                 |   355 +-
 design/litmus/fixtures/forbid_rules/clean.py       |    15 +
 design/litmus/fixtures/forbid_rules/violation.py   |    15 +
 design/litmus/forbid_rules.strata                  |    36 +
 design/litmus/sys_liveness.strata                  |    33 +
 docs/commands/ack.md                               |    13 +
 docs/commands/agent.md                             |    11 +
 docs/commands/check.md                             |    97 +-
 docs/commands/claude.md                            |    11 +
 docs/commands/clean.md                             |    13 +
 docs/commands/coverage.md                          |    11 +
 docs/commands/cycle.md                             |     4 +
 docs/commands/doctor.md                            |    11 +
 docs/commands/explore.md                           |    13 +
 docs/commands/exports.md                           |     6 +-
 docs/commands/fleet.md                             |    11 +
 docs/commands/gitlog.md                            |     5 +
 docs/commands/graph.md                             |    11 +
 docs/commands/map.md                               |     5 +-
 docs/commands/mutate.md                            |    11 +
 docs/commands/narrative.md                         |   100 +
 docs/commands/natives.md                           |    11 +
 docs/commands/outline.md                           |     5 +-
 docs/commands/perf.md                              |    11 +
 docs/commands/pool.md                              |    11 +
 docs/commands/process.md                           |    11 +
 docs/commands/profile.md                           |    11 +
 docs/commands/registry.md                          |    11 +
 docs/commands/release.md                           |     2 +-
 docs/commands/run.md                               |    78 +
 docs/commands/scaffold.md                          |   108 +-
 docs/commands/serve.md                             |    11 +
 docs/commands/status.md                            |    12 +
 docs/commands/test.md                              |    14 +
 docs/commands/ticket.md                            |    92 +
 docs/commands/verify.md                            |    11 +
 docs/commands/vet.md                               |    13 +
 docs/commands/worktree.md                          |    11 +
 docs/commands/xref.md                              |    23 +-
 docs/design/cli-regrouping.md                      |    94 +
 docs/design/coding-performance-corpus.md           |    28 +-
 docs/design/cwe-1000-registry.md                   |     2 +-
 .../registry/capability-via-ratchet.lock.json      |   146 +-
 docs/design/registry/check-coverage.yaml           |  1457 +-
 .../design/ticket-strata-shared-graph-inventory.md |    81 +
 docs/guides/agentic-time-profiling.md              |    26 +-
 docs/guides/claude-hooks.md                        |    73 +-
 docs/guides/command-reference.md                   |     2 +-
 docs/guides/coordinator-scripts.md                 |    73 +
 docs/guides/editors.md                             |     2 +-
 docs/guides/extending/comment-dsl-directives.md    |    13 +-
 docs/guides/extending/cve-fingerprints.md          |     2 +-
 docs/guides/extending/design-lint-rules.md         |     2 +-
 .../failure-injection-acceptance-criteria.md       |    79 +
 docs/guides/extending/pii-categories.md            |     2 +-
 docs/guides/extending/prover-claim-kinds.md        |     2 +-
 docs/guides/extending/registry_of_registries.json  |     7 +
 docs/guides/extending/scenario-kinds.md            |     2 +-
 docs/guides/extending/ticket-kinds-states.md       |     2 +-
 docs/guides/frob-toml.md                           |   121 +
 docs/guides/install.md                             |   123 +-
 docs/guides/release.md                             |    37 +
 docs/guides/unity.md                               |   241 +
 docs/index.md                                      |    29 +
 docs/modules/app.md                                |    57 +
 docs/modules/arch.md                               |    60 +-
 docs/modules/clean.md                              |    35 +
 docs/modules/dup.md                                |    12 +
 docs/modules/gate-config-path-defaults.md          |    39 +
 .../gate-inv011-forbidden-constant-reachability.md |    45 +
 docs/modules/gate-race001.md                       |    87 +
 docs/modules/gate-registration.md                  |   174 +
 docs/modules/gate-route-response-model.md          |    49 +
 docs/modules/gate-sys111-ratchet-auto-accept.md    |    95 +
 docs/modules/gate-testmock001.md                   |    91 +
 docs/modules/gate-time-stable-invariant.md         |    74 +
 docs/modules/gates.md                              |   876 +-
 docs/modules/graph.md                              |   179 +
 docs/modules/land-profiles.md                      |   100 +
 docs/modules/lang.md                               |    92 +-
 docs/modules/process.md                            |    25 +-
 docs/modules/sql.md                                |   238 +
 docs/modules/testing.md                            |    37 +
 docs/modules/tickets-data-storage.md               |   173 +
 docs/modules/tickets-landing.md                    |   239 +-
 docs/modules/tickets-lifecycle.md                  |   139 +
 docs/modules/tickets-verify-sweep.md               |    44 +
 docs/modules/tickets.md                            |    70 +-
 docs/modules/vet.md                                |    73 +-
 docs/modules/webapp-a11y-forms-contrast.md         |    69 +
 docs/modules/webapp-a11y-interaction.md            |    82 +
 docs/modules/webapp-a11y-structure.md              |   111 +
 docs/modules/webapp-a11y.md                        |   122 +
 docs/modules/webapp-comply.md                      |    71 +
 docs/modules/webapp-seo.md                         |   109 +
 docs/modules/webapp-websec-authz.md                |    87 +
 docs/modules/webapp-websec-bounds.md               |    79 +
 docs/modules/webapp-websec-deser.md                |    88 +
 docs/modules/webapp-websec-headers-log.md          |    98 +
 docs/modules/webapp-websec-headers.md              |   108 +
 docs/modules/webapp-websec-injection.md            |    72 +
 docs/modules/webapp-websec-session.md              |    99 +
 docs/modules/webapp-websec-xss.md                  |    97 +
 docs/modules/webapp.md                             |    66 +
 docs/strata/charter.md                             |     4 +-
 docs/strata/dataset-construct.md                   |    99 +
 docs/strata/evidence.md                            |     9 +-
 docs/strata/kernel.md                              |    92 +-
 docs/strata/provenance-trust-identity.md           |   102 +
 docs/strata/reliability.md                         |    69 +
 docs/strata/selfconform.md                         |    93 +
 docs/strata/surface.md                             |   130 +-
 docs/strata/threat.md                              |    49 +
 .../vscode-strata/syntaxes/strata.tmLanguage.json  |     4 +-
 force-overrides.jsonl                              |     2 +
 frob-core/src/callgraph.rs                         |    16 +
 frob-core/src/exact_regions.rs                     |     3 +
 frob-core/src/r3.rs                                |     2 +
 frob-core/src/r4.rs                                |     1 +
 frob-core/src/r5.rs                                |    12 +
 frob-ratchet.lock.json                             | 22649 ++++++++++++++++++-
 frob.lock                                          |   487 +-
 frob.toml                                          |   425 +-
 pyproject.toml                                     |    52 +-
 scripts/artifact_smoke.py                          |    32 -
 scripts/branch_stranded_work_analysis.py           |    22 -
 scripts/check_summary.py                           |     2 -
 scripts/count_ticket_citations.py                  |   160 +
 scripts/fleet_status.py                            |  1312 +-
 scripts/measure_evidence_reach.py                  |    17 -
 scripts/strip_help_citations.py                    |   224 +
 scripts/verify_lands.py                            |    44 +-
 scripts/verify_release_ci_status.py                |    22 -
 scripts/wait_for_land_slot.py                      |    25 -
 src/frob/__init__.py                               |    66 +-
 src/frob/__main__.py                               |   192 +-
 src/frob/_cli_parsers/__init__.py                  |     5 +
 src/frob/_cli_parsers/_check.py                    |   329 +-
 src/frob/_cli_parsers/_core.py                     |   330 +-
 src/frob/_cli_parsers/_design.py                   |    50 +-
 src/frob/_cli_parsers/_explore.py                  |   168 +-
 src/frob/_cli_parsers/_misc.py                     |   153 +-
 src/frob/_cli_parsers/_ops.py                      |    77 +-
 src/frob/_cli_parsers/_quality.py                  |    29 +-
 src/frob/_cli_parsers/_reporting.py                |   134 +-
 src/frob/_cli_parsers/_root.py                     |    75 +-
 src/frob/_cli_parsers/_run.py                      |    56 +
 src/frob/_cli_parsers/_shims.py                    |    93 +
 src/frob/_cli_parsers/_status.py                   |     5 +-
 src/frob/_cli_parsers/_ticket/__init__.py          |    73 +-
 src/frob/_cli_parsers/_ticket/_closeout.py         |    65 +-
 .../_cli_parsers/_ticket/_closeout_evidence.py     |   107 +-
 src/frob/_cli_parsers/_ticket/_metadata.py         |   227 +-
 src/frob/_cli_parsers/_ticket/_new.py              |    96 +-
 src/frob/_cli_parsers/_ticket/_progress.py         |   240 +-
 src/frob/_cli_parsers/_ticket/_query.py            |    33 +-
 src/frob/_cli_parsers/_verify.py                   |    25 +-
 src/frob/_daemon_timeout.py                        |     2 -
 src/frob/app/__init__.py                           |     2 -
 src/frob/app/_check_chunking.py                    |    16 -
 src/frob/app/_check_chunking_baseline.py           |    13 -
 src/frob/app/_config_external.py                   |    78 +-
 src/frob/app/_daemon_proxy.py                      |    51 -
 src/frob/app/_json_guard.py                        |    16 -
 src/frob/app/_snapshot.py                          |     1 -
 src/frob/app/_verify_rapid_debt.py                 |     4 -
 src/frob/app/_version_guard.py                     |     5 -
 src/frob/app/ack_runner.py                         |    25 +-
 src/frob/app/agent_runner.py                       |    56 +-
 src/frob/app/app.py                                |   101 +-
 src/frob/app/arch_runner.py                        |     1 -
 src/frob/app/bind_runner.py                        |     1 -
 src/frob/app/check_runner.py                       |   274 +-
 src/frob/app/claude_runner.py                      |     8 -
 src/frob/app/clean_runner.py                       |    57 +-
 src/frob/app/config.py                             |   191 +-
 src/frob/app/coverage_runner.py                    |    15 +-
 src/frob/app/cycle_runner.py                       |     3 -
 src/frob/app/debt_runner.py                        |     1 -
 src/frob/app/deprecated_runner.py                  |     1 -
 src/frob/app/design_runner.py                      |     3 -
 src/frob/app/docs_runner.py                        |    30 +-
 src/frob/app/doctor_runner.py                      |   105 +-
 src/frob/app/dup_runner.py                         |     7 +-
 src/frob/app/explore_runner.py                     |    92 +-
 src/frob/app/exports_runner.py                     |     6 -
 src/frob/app/fleet_runner.py                       |     3 -
 src/frob/app/fmt_runner.py                         |    25 +-
 src/frob/app/gitlog_runner.py                      |     1 -
 src/frob/app/graph_runner.py                       |    21 +-
 src/frob/app/map_runner.py                         |     1 -
 src/frob/app/mutate_runner.py                      |     2 -
 src/frob/app/natives_runner.py                     |     1 -
 src/frob/app/ops_runner.py                         |     4 -
 src/frob/app/outline_runner.py                     |     1 -
 src/frob/app/parse_runner.py                       |     7 -
 src/frob/app/perf_runner.py                        |    10 -
 src/frob/app/pool_runner.py                        |     1 -
 src/frob/app/process_runner.py                     |     4 -
 src/frob/app/profile_runner.py                     |     3 -
 src/frob/app/pyfmt_runner.py                       |    18 -
 src/frob/app/quality_runner.py                     |     4 -
 src/frob/app/registry_runner.py                    |     1 -
 src/frob/app/release_runner.py                     |     1 -
 src/frob/app/run_runner.py                         |   297 +
 src/frob/app/scaffold_runner.py                    |    76 +-
 src/frob/app/stats_runner.py                       |     2 -
 src/frob/app/status_runner.py                      |     7 -
 src/frob/app/sys_runner.py                         |   126 +-
 src/frob/app/telemetry/__init__.py                 |    61 +-
 src/frob/app/telemetry/_footguns.py                |     6 -
 src/frob/app/telemetry/_state.py                   |    13 -
 src/frob/app/telemetry/_usage.py                   |     4 -
 src/frob/app/ticket_runner/__init__.py             |   192 +-
 src/frob/app/ticket_runner/_archive.py             |     2 -
 src/frob/app/ticket_runner/_attach_backfill.py     |    52 +-
 src/frob/app/ticket_runner/_close_cmd.py           |    77 +-
 src/frob/app/ticket_runner/_land_cmd.py            |   874 +-
 src/frob/app/ticket_runner/_ledger_mirror.py       |    70 +-
 src/frob/app/ticket_runner/_lifecycle.py           |   488 +-
 src/frob/app/ticket_runner/_mutate.py              |   183 +-
 src/frob/app/ticket_runner/_new.py                 |   219 +-
 src/frob/app/ticket_runner/_query.py               |    24 -
 src/frob/app/ticket_runner/_rapid_sweep.py         |  1058 +-
 src/frob/app/ticket_runner/_verify.py              |   329 +-
 src/frob/app/ticket_runner/_waive_audit.py         |   216 +-
 src/frob/app/verify_runner.py                      |    46 +-
 src/frob/app/vet_runner.py                         |     2 -
 src/frob/app/worktree_runner.py                    |     6 -
 src/frob/app/xref_runner.py                        |     1 -
 src/frob/arch/__init__.py                          |    29 +-
 src/frob/arch/_abstraction.py                      |    91 +-
 src/frob/arch/_async_hazards.py                    |    11 -
 src/frob/arch/_concurrency.py                      |    11 -
 src/frob/arch/_concurrency_model.py                |     4 -
 src/frob/arch/_cpp_mayraise.py                     |     5 -
 src/frob/arch/_exceptions.py                       |     4 -
 src/frob/arch/_fallibility.py                      |    10 -
 src/frob/arch/_ffi.py                              |     6 -
 src/frob/arch/_kotlin.py                           |     2 -
 src/frob/arch/_layering.py                         |   177 +-
 src/frob/arch/_lock_ordering.py                    |     5 -
 src/frob/arch/_logging_checks.py                   |     8 -
 src/frob/arch/_mayraise.py                         |     2 -
 src/frob/arch/_mayraise_tables.py                  |    33 +-
 src/frob/arch/_models.py                           |    23 +-
 src/frob/arch/_normalized.py                       |    17 +-
 src/frob/arch/_ocp.py                              |     2 -
 src/frob/arch/_patterns.py                         |    16 -
 src/frob/arch/_protocol_excuse.py                  |    12 -
 src/frob/arch/_python.py                           |    93 +-
 src/frob/arch/_rust.py                             |     2 -
 src/frob/arch/_shared_state_race.py                |     5 -
 src/frob/arch/_smells.py                           |    17 -
 src/frob/arch/_solid.py                            |    17 -
 src/frob/arch/_srp.py                              |     7 -
 src/frob/arch/_typedesign.py                       |     9 -
 src/frob/arch/_typescript.py                       |     2 -
 src/frob/bind/__init__.py                          |     1 -
 src/frob/check/__init__.py                         |   412 +-
 src/frob/check/_memo.py                            |     7 -
 src/frob/check/_python.py                          |   287 +-
 src/frob/check/_ts.py                              |     1 -
 src/frob/ci_report.py                              |    15 -
 src/frob/ci_validity.py                            |    15 -
 src/frob/clean/_core.py                            |     7 -
 src/frob/clean/_models.py                          |     2 -
 src/frob/clean/_rules.py                           |    19 +-
 src/frob/cycle/__init__.py                         |     2 -
 src/frob/cycle/graph.py                            |     1 -
 src/frob/deploy/_audit.py                          |    15 +-
 src/frob/deploy/_conform.py                        |     7 -
 src/frob/deploy/_generate_common.py                |     3 -
 src/frob/docs/__init__.py                          |    75 +-
 src/frob/docs/_command_pages.py                    |   132 +
 src/frob/doctor.py                                 |   937 +-
 src/frob/dup/_cache.py                             |     6 -
 src/frob/dup/_core.py                              |     1 -
 src/frob/dup/_exhaustiveness.py                    |     3 -
 src/frob/dup/_legacy.py                            |    86 +-
 src/frob/dup/_legacy_cs.py                         |   207 +
 src/frob/dup/_legacy_py.py                         |     2 -
 src/frob/dup/_pipeline/_probe.py                   |     1 -
 src/frob/dup/_pipeline/_smt.py                     |     1 -
 src/frob/dup/_template.py                          |    21 +-
 src/frob/excludes.py                               |   102 +-
 src/frob/exports/__init__.py                       |     6 -
 src/frob/findings.py                               |    51 +-
 src/frob/fleet/__init__.py                         |    24 -
 src/frob/gates/__init__.py                         |   859 +-
 src/frob/gates/_a11y_gate.py                       |   173 +
 src/frob/gates/_arch.py                            |   118 +-
 src/frob/gates/_arch_schema.py                     |     3 -
 src/frob/gates/_bare_toolchain.py                  |     2 -
 src/frob/gates/_bug_repro.py                       |   361 +-
 src/frob/gates/_cache_gate.py                      |     3 -
 src/frob/gates/_claim_lint.py                      |   199 +
 src/frob/gates/_comment_placement.py               |     9 -
 src/frob/gates/_config_path_defaults.py            |   212 +
 src/frob/gates/_coverage.py                        |   509 +-
 src/frob/gates/_coverage_sites.py                  |     4 +-
 src/frob/gates/_cve_fingerprint_scan.py            |     5 -
 src/frob/gates/_dead_symbols.py                    |     9 -
 src/frob/gates/_debt_deprecated.py                 |    95 +-
 src/frob/gates/_decisions_compliance.py            |    11 -
 src/frob/gates/_deprecated_baseline.py             |     9 -
 src/frob/gates/_design_invariants.py               |   188 +-
 src/frob/gates/_detector_scope.py                  |     6 -
 src/frob/gates/_directive_stack.py                 |   127 +
 src/frob/gates/_docarch_structural.py              |   360 +
 src/frob/gates/_docblocks.py                       |   112 +-
 src/frob/gates/_docblocks_refs.py                  |   148 +-
 src/frob/gates/_docblocks_schema.py                |     2 -
 src/frob/gates/_docblocks_shared.py                |     1 -
 src/frob/gates/_doclink_docanchor.py               |     9 -
 src/frob/gates/_docptr.py                          |   225 +-
 src/frob/gates/_docstatus.py                       |    14 -
 src/frob/gates/_docstring_archaeology.py           |     5 -
 src/frob/gates/_dup_graph_schema.py                |     4 -
 src/frob/gates/_empty_diff_close.py                |   168 +-
 src/frob/gates/_exclude_hazard.py                  |     2 -
 src/frob/gates/_exhaustive_handling.py             |     9 -
 src/frob/gates/_ffi_boundary.py                    |     7 -
 src/frob/gates/_fix_engine.py                      |   553 +-
 src/frob/gates/_fix_engine_scope.py                |    82 +-
 src/frob/gates/_fix_engine_shared.py               |     7 -
 src/frob/gates/_fix_engine_sync.py                 |   239 +-
 src/frob/gates/_fix_engine_text.py                 |   734 +-
 src/frob/gates/_fix_engine_tier_b.py               |     8 -
 src/frob/gates/_fix_engine_tier_c.py               |     1 -
 src/frob/gates/_fixability_scan.py                 |     2 -
 src/frob/gates/_flag_coverage.py                   |    36 +-
 src/frob/gates/_fmt_directives.py                  |   434 +-
 src/frob/gates/_forbid_rules_gate.py               |   419 +
 src/frob/gates/_gate_cache.py                      |    25 -
 src/frob/gates/_gates_schema.py                    |     2 -
 src/frob/gates/_guard_closure.py                   |   295 +
 src/frob/gates/_inv.py                             |   646 +
 src/frob/gates/_land_format.py                     |    12 +-
 src/frob/gates/_land_parity.py                     |    97 +-
 src/frob/gates/_lang_conformance.py                |   279 +-
 src/frob/gates/_lexical_selfcheck.py               |     8 -
 src/frob/gates/_lock_producer.py                   |     5 -
 src/frob/gates/_markdown_scan.py                   |    28 +-
 src/frob/gates/_milestone.py                       |    90 +-
 src/frob/gates/_models.py                          |     7 +
 src/frob/gates/_mutation_evidence.py               |    12 -
 src/frob/gates/_narrative_blocks.py                |    32 +-
 src/frob/gates/_native_schema.py                   |     2 -
 src/frob/gates/_negexist.py                        |     5 -
 src/frob/gates/_opaque.py                          |     5 -
 src/frob/gates/_parse_failures.py                  |     5 -
 src/frob/gates/_pii_structural/__init__.py         |   202 +-
 .../gates/_pii_structural/_declared_surface.py     |     1 -
 src/frob/gates/_pii_structural/_emails.py          |     1 -
 src/frob/gates/_pii_structural/_keywords.py        |   100 +-
 src/frob/gates/_pii_structural/_node_index.py      |     2 -
 src/frob/gates/_pii_structural/_python_fields.py   |    28 +-
 src/frob/gates/_pii_structural/_signatures.py      |     2 -
 src/frob/gates/_pkg_resources.py                   |     8 -
 src/frob/gates/_policy_weakening_gate.py           |     4 -
 src/frob/gates/_port_selfcheck.py                  |     9 -
 src/frob/gates/_prework.py                         |    15 +-
 src/frob/gates/_profile_boundary.py                |    10 +-
 src/frob/gates/_profile_schema.py                  |     2 -
 src/frob/gates/_protocol_summary.py                |    89 +-
 src/frob/gates/_ratchet.py                         |    97 +-
 src/frob/gates/_refs.py                            |   218 +-
 src/frob/gates/_refs_schema.py                     |     2 -
 src/frob/gates/_registry.py                        |   305 +
 src/frob/gates/_registry_exhaustiveness.py         |    25 +-
 src/frob/gates/_render_lint.py                     |    49 +-
 src/frob/gates/_route_response_model.py            |   171 +
 src/frob/gates/_rule_id_scan.py                    |    23 -
 src/frob/gates/_secrets.py                         |   143 +-
 src/frob/gates/_sql_explain_obligation.py          |   180 +
 src/frob/gates/_suppress.py                        |    53 +-
 src/frob/gates/_sys.py                             |    28 -
 src/frob/gates/_sys_branch.py                      |   120 +
 src/frob/gates/_sys_provenance.py                  |   187 +
 src/frob/gates/_sys_selfaudit.py                   |   188 +-
 src/frob/gates/_taint_gate.py                      |   161 +-
 src/frob/gates/_tdd_order.py                       |    23 -
 src/frob/gates/_test_runner_schema.py              |     2 -
 src/frob/gates/_testing_schema.py                  |     3 -
 src/frob/gates/_tickets_gate.py                    |   485 +-
 src/frob/gates/_todo_fmt.py                        |    24 -
 src/frob/gates/_toplevel_scalar_schema.py          |     2 -
 src/frob/gates/_version_coupling.py                |     8 -
 src/frob/gates/_vmodel.py                          |     6 -
 src/frob/gates/_waive.py                           |   587 +-
 src/frob/gates/_waive_audit_watermark.py           |     8 -
 src/frob/gates/_waive_comments.py                  |   137 +-
 src/frob/gates/_waive_lease.py                     |     5 -
 src/frob/gates/_walk_lint.py                       |    45 +-
 src/frob/gates/_win32_kill_signal.py               |     9 +-
 src/frob/gates/_wire.py                            |   283 +-
 src/frob/gates/_wrapper_drift.py                   |   216 +
 src/frob/gates/decisions.py                        |     1 -
 src/frob/gates/invariants.py                       |    34 +-
 src/frob/ghio.py                                   |    17 -
 src/frob/gitio.py                                  |    72 +-
 src/frob/gitlog/__init__.py                        |     2 -
 src/frob/graph/__init__.py                         |   215 +-
 src/frob/graph/_core.py                            |    10 +-
 src/frob/graph/_generated.py                       |     4 -
 src/frob/graph/_hierarchy.py                       |    75 +
 src/frob/graph/_models.py                          |     1 -
 src/frob/graph/_resolve.py                         |     2 -
 src/frob/graph/affects.py                          |   143 +-
 src/frob/graph/cache.py                            |   180 +-
 src/frob/graph/callgraph.py                        |   108 +-
 src/frob/graph/digest.py                           |     3 -
 src/frob/graph/dsl.py                              |   787 +-
 src/frob/graph/imports.py                          |     7 -
 src/frob/graph/lock.py                             |    20 -
 src/frob/graph/reach.py                            |     8 -
 src/frob/graph/summary.py                          |    22 -
 src/frob/lang/__init__.py                          |    68 +-
 src/frob/lang/_common.py                           |    17 +-
 src/frob/lang/_extract.py                          |    55 +-
 src/frob/lang/_models.py                           |     1 -
 src/frob/lang/_nodes.py                            |   225 +-
 src/frob/lang/_project_detect.py                   |   135 +
 src/frob/lang/_support.py                          |   259 +-
 src/frob/lang/_walk_bash.py                        |     5 -
 src/frob/lang/_walk_csharp.py                      |   119 +-
 src/frob/lang/_walk_css.py                         |   165 +
 src/frob/lang/_walk_cuda.py                        |     6 -
 src/frob/lang/_walk_html.py                        |   116 +
 src/frob/lang/_walk_java.py                        |     8 -
 src/frob/lang/_walk_javascript.py                  |   182 +
 src/frob/lang/_walk_kotlin.py                      |    12 -
 src/frob/lang/_walk_strata.py                      |    10 +-
 src/frob/lang/_walk_vue.py                         |   111 +
 src/frob/lang/_walk_zig.py                         |     9 -
 src/frob/logging/filter.py                         |     1 -
 src/frob/logging/formatter.py                      |     1 -
 src/frob/logging/handler.py                        |     2 -
 src/frob/logging/logger.py                         |    38 +-
 src/frob/logging/quiet.py                          |     3 -
 src/frob/map/__init__.py                           |     2 -
 src/frob/mutate/__init__.py                        |    10 -
 src/frob/mutate/_journal.py                        |    10 -
 src/frob/narrative/_bulk.py                        |   334 +
 src/frob/narrative/_cli.py                         |    98 +-
 src/frob/narrative/_migrate.py                     |    16 -
 src/frob/natives/_build.py                         |     1 -
 src/frob/nodeid.py                                 |     3 -
 src/frob/outline/__init__.py                       |     4 -
 src/frob/perf/__init__.py                          |     4 +
 src/frob/perf/_advisories.py                       |     6 -
 src/frob/perf/_cache_effects.py                    |   199 +
 src/frob/perf/_collectors.py                       |     7 -
 src/frob/perf/_dup_spawn.py                        |     7 -
 src/frob/perf/_effect_summaries.py                 |     6 -
 src/frob/perf/_harness.py                          |     3 -
 src/frob/perf/_hotgraph.py                         |     6 -
 src/frob/perf/_hotpath_smells.py                   |    44 +-
 src/frob/perf/_loop_effects.py                     |     6 -
 src/frob/perf/_loop_variant.py                     |   199 +
 src/frob/perf/_ratchet.py                          |    10 -
 src/frob/perf/_recursion.py                        |     1 -
 src/frob/perf/_redundancy.py                       |     7 +-
 src/frob/perf/_rules.py                            |     6 +
 src/frob/perf/_sampler.py                          |     3 -
 src/frob/perf/_serial_pools.py                     |     5 -
 src/frob/perf/_sketch_store.py                     |    17 -
 src/frob/policy/__init__.py                        |    93 +-
 src/frob/policy/_models.py                         |    54 +-
 src/frob/process/_derived_lock.py                  |    13 -
 src/frob/process/_guard.py                         |    25 -
 src/frob/process/_lock.py                          |    42 +-
 src/frob/process/_lock_msvcrt.py                   |     1 -
 src/frob/process/_pid_liveness.py                  |    38 +-
 src/frob/process/_proc_scan.py                     |    65 +-
 src/frob/process/_project_tool.py                  |    12 -
 src/frob/process/_pytest_spawn.py                  |     6 -
 src/frob/process/_reap.py                          |    12 -
 src/frob/process/_tty.py                           |     5 -
 src/frob/process/parsers/common.py                 |    16 -
 src/frob/process/parsers/ruff.py                   |    44 +-
 src/frob/process/parsers/ty.py                     |     3 -
 src/frob/process/parsers/valgrind.py               |     9 -
 src/frob/refactor/_alias_policy.py                 |     1 -
 src/frob/refactor/_apply.py                        |     4 -
 src/frob/refactor/_cli.py                          |     3 -
 src/frob/refactor/_commit.py                       |     3 -
 src/frob/refactor/_directives.py                   |     3 -
 src/frob/refactor/_gitops.py                       |     6 -
 src/frob/refactor/_models.py                       |     3 -
 src/frob/refactor/_module_lang.py                  |     3 -
 src/frob/refactor/_module_prose.py                 |     3 -
 src/frob/refactor/_module_resolve.py               |     4 -
 src/frob/refactor/_module_scan_python.py           |     8 -
 src/frob/refactor/_module_transaction.py           |     7 -
 src/frob/refactor/_operands.py                     |     8 -
 src/frob/refactor/_prose.py                        |     4 -
 src/frob/refactor/_repointer.py                    |     9 -
 src/frob/refactor/_resolve.py                      |     5 -
 src/frob/refactor/_scan.py                         |     3 -
 src/frob/refactor/_scan_carry.py                   |     6 -
 src/frob/refactor/_scan_repoint.py                 |     1 -
 src/frob/refactor/_split.py                        |     5 -
 src/frob/refactor/_transaction.py                  |    22 +-
 src/frob/refactor/_verify.py                       |    27 +-
 src/frob/refactor/_verify_exec.py                  |     5 -
 src/frob/refactor/_verify_import.py                |     2 -
 src/frob/registry/_corpus.py                       |     2 -
 src/frob/registry/_models.py                       |     6 -
 src/frob/registry/_staleness.py                    |     6 -
 src/frob/release/__init__.py                       |    33 +-
 src/frob/release/_cli.py                           |     6 -
 src/frob/release/_fragments.py                     |     9 -
 src/frob/release/_publish.py                       |     5 -
 src/frob/repo_meta.py                              |    17 -
 src/frob/scaffold/__init__.py                      |     2 +
 src/frob/scaffold/_managed.py                      |   172 +-
 src/frob/scaffold/_pool.py                         |    11 -
 src/frob/scaffold/_skills_sync.py                  |    10 -
 src/frob/scaffold/_unity_project.py                |   183 +
 src/frob/scaffold/data/shared/cpp/Makefile.j2      |    61 +-
 src/frob/scaffold/data/shared/cpp/frob.toml.j2     |    67 +-
 src/frob/scaffold/data/shared/python/Makefile.j2   |     7 +
 src/frob/scaffold/data/shared/python/README.md.j2  |     2 +-
 .../scaffold/data/shared/python/docs/index.md.j2   |    10 +-
 src/frob/scaffold/data/shared/python/frob.toml.j2  |    75 +-
 .../data/shared/python/logging/__init__.py.j2      |     8 +-
 .../data/shared/python/logging/config.toml.j2      |     7 +-
 .../data/shared/python/logging/logger.py.j2        |    13 +
 .../scaffold/data/shared/python/pyproject.toml.j2  |     2 +-
 .../integration/test_logging_integration.py.j2     |    35 +
 .../python/tests/unit/test_placeholder.py.j2       |     7 +-
 .../data/types/pybind11-library/Makefile.j2        |    38 +-
 .../data/types/pybind11-library/frob.toml.j2       |    62 +-
 .../scaffold/data/types/pyo3-library/Makefile.j2   |    51 +-
 .../scaffold/data/types/pyo3-library/frob.toml.j2  |    72 +-
 .../scaffold/data/types/python-tool/__main__.py.j2 |    22 +-
 .../data/types/python-tool/app/__init__.py.j2      |     8 +-
 .../scaffold/data/types/python-tool/app/app.py.j2  |    22 +-
 .../data/types/python-tool/app/config.py.j2        |    89 +-
 .../data/types/python-tool/docs/index.md.j2        |     4 +
 .../scaffold/data/types/python-tool/frob.toml.j2   |     9 +
 .../python-tool/tests/system/test_build.py.j2      |    27 +
 .../types/python-tool/tests/unit/test_app.py.j2    |    17 +-
 .../scaffold/data/types/unity-project/frob.toml.j2 |    64 +
 src/frob/scaffold/data/types/web-app/Makefile.j2   |    43 +-
 src/frob/scaffold/data/types/web-app/frob.toml.j2  |    83 +-
 src/frob/scaffold/project.py                       |    26 +-
 src/frob/security/_redact.py                       |    57 +-
 src/frob/serve/_daemon.py                          |    53 +-
 src/frob/serve/_events.py                          |    16 +-
 src/frob/serve/_leases.py                          |     4 -
 src/frob/serve/_socketd.py                         |    45 +-
 src/frob/serve/_tools.py                           |    19 -
 src/frob/serve/_warm.py                            |     3 -
 src/frob/serve/_watch.py                           |     5 -
 src/frob/sql/__init__.py                           |    15 +
 src/frob/sql/_extract.py                           |   591 +
 src/frob/sql/_orm_rules.py                         |   461 +
 src/frob/sql/_sqlfluff_plugin.py                   |   221 +
 src/frob/sql/_squawk_adapter.py                    |   217 +
 src/frob/sql/sqlfluff_default_config.cfg           |     7 +
 src/frob/stats/_agentic.py                         |     2 -
 src/frob/stats/_agentic_dispatch.py                |    12 -
 src/frob/stats/_sketch.py                          |    10 -
 src/frob/strata/__init__.py                        |    24 +
 src/frob/strata/_access.py                         |     3 -
 src/frob/strata/_assume_template.py                |   307 +
 src/frob/strata/_ast.py                            |     2 -
 src/frob/strata/_audit.py                          |    38 +-
 src/frob/strata/_backpressure.py                   |    63 +-
 src/frob/strata/_bootstrap.py                      |     7 -
 src/frob/strata/_circuit_breaker.py                |     3 -
 src/frob/strata/_claims.py                         |    65 +-
 src/frob/strata/_clock_ordering.py                 |     1 -
 src/frob/strata/_compliance.py                     |    66 +-
 src/frob/strata/_contention.py                     |     1 -
 src/frob/strata/_crash.py                          |     1 -
 src/frob/strata/_cve_fingerprint.py                |     2 -
 src/frob/strata/_dataset.py                        |   127 +
 src/frob/strata/_delivery_semantics.py             |     1 -
 src/frob/strata/_design_load.py                    |    80 +-
 src/frob/strata/_distributed_txn.py                |     1 -
 src/frob/strata/_effects.py                        |   965 +-
 src/frob/strata/_elaborate.py                      |   100 +-
 src/frob/strata/_export.py                         |     1 -
 src/frob/strata/_facts.py                          |    27 +-
 src/frob/strata/_fallback.py                       |     1 -
 src/frob/strata/_host.py                           |     6 -
 src/frob/strata/_host_isolation_lateral.py         |     1 -
 src/frob/strata/_host_isolation_movement.py        |     1 -
 src/frob/strata/_host_isolation_shared.py          |     4 -
 src/frob/strata/_host_isolation_vertical.py        |     4 +-
 src/frob/strata/_inbound_rate.py                   |   231 +
 src/frob/strata/_infra.py                          |    37 +-
 src/frob/strata/_interactive_cost.py               |     1 -
 src/frob/strata/_krb.py                            |     4 -
 src/frob/strata/_krb_movement.py                   |     4 -
 src/frob/strata/_message_schema.py                 |     1 -
 src/frob/strata/_mode_conformance.py               |     3 -
 src/frob/strata/_models.py                         |     3 -
 src/frob/strata/_multifile.py                      |    20 -
 src/frob/strata/_mutation_audit.py                 |    85 +-
 src/frob/strata/_native_staleness.py               |    14 -
 src/frob/strata/_native_staleness_digest.py        |     3 -
 src/frob/strata/_native_test.py                    |     9 +-
 src/frob/strata/_obligation_proof.py               |     4 -
 src/frob/strata/_observability.py                  |     1 -
 src/frob/strata/_outbound_destination.py           |   360 +
 src/frob/strata/_packs.py                          |    30 +-
 src/frob/strata/_parse.py                          |     2 -
 src/frob/strata/_pii.py                            |   107 +
 src/frob/strata/_plan.py                           |     4 -
 src/frob/strata/_policy.py                         |     7 -
 src/frob/strata/_process_bounds.py                 |     1 -
 src/frob/strata/_reliability.py                    |     2 -
 src/frob/strata/_retry.py                          |     1 -
 src/frob/strata/_scenarios.py                      |     2 -
 src/frob/strata/_scope_config.py                   |     4 -
 src/frob/strata/_selfconform.py                    |    22 +-
 src/frob/strata/_selfconform_binding_rules.py      |     4 -
 src/frob/strata/_selfconform_core_rules.py         |     4 -
 src/frob/strata/_selfconform_ids.py                |   107 +-
 src/frob/strata/_selfconform_kinds.py              |     2 -
 src/frob/strata/_selfconform_models.py             |     2 -
 src/frob/strata/_selfconform_surface_rules.py      |    42 +-
 src/frob/strata/_shared_state.py                   |     1 -
 src/frob/strata/_shrink.py                         |     8 -
 src/frob/strata/_slo.py                            |     1 -
 src/frob/strata/_spof.py                           |     1 -
 src/frob/strata/_ssot.py                           |     1 -
 src/frob/strata/_starvation.py                     |     1 -
 src/frob/strata/_supply_chain_boot.py              |     1 -
 src/frob/strata/_sync_depth.py                     |     1 -
 src/frob/strata/_sync_may.py                       |     3 -
 src/frob/strata/_sysdoc.py                         |     2 -
 src/frob/strata/_threat.py                         |     1 -
 src/frob/strata/_threat_catalog_benign.py          |    42 +-
 src/frob/strata/_threat_catalog_cwe.py             |    96 +-
 src/frob/strata/_threat_catalog_quality.py         |   100 +-
 src/frob/strata/_threat_discharge.py               |    78 +-
 src/frob/strata/_txn.py                            |     1 -
 src/frob/strata/_unity_asmdef.py                   |   400 +
 src/frob/strata/_waive.py                          |    12 +-
 src/frob/telemetry/__init__.py                     |     2 -
 src/frob/testing/__init__.py                       |    20 +
 src/frob/testing/_collect.py                       |    25 +-
 src/frob/testing/_collect_csharp.py                |   321 +
 src/frob/testing/_collect_kotlin.py                |     7 -
 src/frob/testing/_collect_python_cache.py          |     4 -
 src/frob/testing/_coverage_cache.py                |     6 -
 src/frob/testing/_coverage_refresh.py              |    80 +-
 src/frob/testing/_coverage_wait.py                 |    67 +-
 src/frob/testing/_dotnet_runner.py                 |   241 +
 src/frob/testing/_incremental_coverage.py          |     3 -
 src/frob/testing/_runners.py                       |    11 +-
 src/frob/testing/_select.py                        |     1 -
 src/frob/testing/_stability.py                     |    36 -
 src/frob/testing/_stackdump.py                     |    68 +-
 src/frob/testing/_unity_batchmode.py               |   289 +
 src/frob/tickets/__init__.py                       |    30 +-
 src/frob/tickets/_accept.py                        |     4 -
 src/frob/tickets/_archive.py                       |    22 -
 src/frob/tickets/_brief.py                         |    13 -
 src/frob/tickets/_doable.py                        |   194 +-
 src/frob/tickets/_done_report.py                   |    19 -
 src/frob/tickets/_draft_finalize.py                |    22 +-
 src/frob/tickets/_evidence.py                      |   261 +-
 src/frob/tickets/_flow.py                          |   397 +-
 src/frob/tickets/_force_override.py                |     2 -
 src/frob/tickets/_journal.py                       |     7 -
 src/frob/tickets/_land.py                          |   744 +-
 src/frob/tickets/_land_compose.py                  |   235 +-
 src/frob/tickets/_land_finalize.py                 |   133 +-
 src/frob/tickets/_land_git_ops.py                  |   185 +-
 src/frob/tickets/_land_ledger_merge.py             |    14 -
 src/frob/tickets/_land_merge_zones.py              |     3 -
 src/frob/tickets/_land_passenger_identity.py       |     3 -
 src/frob/tickets/_land_queue.py                    |   160 +-
 src/frob/tickets/_land_release.py                  |    88 +-
 src/frob/tickets/_land_splice.py                   |     5 -
 src/frob/tickets/_land_squash.py                   |   497 +-
 src/frob/tickets/_land_verify.py                   |     9 -
 src/frob/tickets/_leases.py                        |   890 +-
 src/frob/tickets/_live_tracker.py                  |    42 +-
 src/frob/tickets/_models.py                        |   502 +-
 src/frob/tickets/_mutation_evidence.py             |    20 +-
 src/frob/tickets/_mutation_sweep_queue.py          |     7 -
 src/frob/tickets/_new_gate_rule_acceptance.py      |    11 -
 src/frob/tickets/_new_renumber.py                  |   193 +-
 src/frob/tickets/_profile.py                       |    14 -
 src/frob/tickets/_reconcile.py                     |   107 +-
 src/frob/tickets/_registry_files.py                |   136 +
 src/frob/tickets/_renumber_v2.py                   |    31 +-
 src/frob/tickets/_reporting.py                     |   135 +-
 src/frob/tickets/_reporting_attachments.py         |   153 +-
 src/frob/tickets/_scope.py                         |    12 -
 src/frob/tickets/_scope_coverage.py                |     3 -
 src/frob/tickets/_setters.py                       |   295 +-
 src/frob/tickets/_sprint.py                        |   154 +
 src/frob/tickets/_store.py                         |   170 +-
 src/frob/tickets/_store_api.py                     |   172 +
 src/frob/tickets/_store_migrate.py                 |    21 +-
 src/frob/tickets/_token_usage.py                   |   503 +
 src/frob/tickets/_unlanded.py                      |    50 +-
 src/frob/tickets/_unlanded_cache.py                |     4 -
 src/frob/tickets/_worktree_guard.py                |    29 -
 src/frob/tickets/_worktree_sweep.py                |    30 +-
 src/frob/tomlio.py                                 |     1 -
 src/frob/verify/_attribution.py                    |     8 -
 src/frob/verify/_backpressure.py                   |    26 -
 src/frob/verify/_bisect.py                         |     3 -
 src/frob/verify/_drain.py                          |    13 -
 src/frob/verify/_quarantine.py                     |    98 +-
 src/frob/verify/_selection.py                      |     5 -
 src/frob/verify/_watermark.py                      |    48 +-
 src/frob/verify/_worker.py                         |   132 +-
 src/frob/vet/__init__.py                           |    11 +-
 src/frob/vet/_allow.py                             |    21 +-
 src/frob/vet/_bare_toolchain.py                    |     2 -
 src/frob/vet/_cache.py                             |     3 -
 src/frob/vet/_capability.py                        |    12 +-
 src/frob/vet/_capability_c.py                      |    53 +-
 src/frob/vet/_capability_core.py                   |   160 +-
 src/frob/vet/_capability_csharp.py                 |   452 +
 src/frob/vet/_capability_kotlin.py                 |    34 +-
 src/frob/vet/_capability_modes.py                  |    26 +-
 src/frob/vet/_capability_python.py                 |    81 +-
 .../_dangerous_ops_bash_csharp.py                  |    17 +
 .../_capability_registry/_dangerous_ops_python.py  |    52 +-
 src/frob/vet/_capability_registry/_dotnet_bcl.py   |   214 +
 src/frob/vet/_capability_registry/_kinds.py        |    36 +-
 src/frob/vet/_capability_registry/_matrix.py       |    16 +-
 src/frob/vet/_capability_registry/_unity_api.py    |   293 +
 src/frob/vet/_capability_rust.py                   |    69 +-
 src/frob/vet/_capability_scan.py                   |   211 +-
 src/frob/vet/_capability_typescript_bindtable.py   |   140 +-
 src/frob/vet/_containment.py                       |     2 +-
 src/frob/vet/_ecosystem.py                         |     2 +-
 src/frob/vet/_lockfile.py                          |     2 -
 src/frob/vet/_models.py                            |    10 +-
 src/frob/vet/_obfuscation.py                       |    77 +-
 src/frob/vet/_osv.py                               |   556 +-
 src/frob/vet/_scan.py                              |   154 +-
 src/frob/vet/_scan_violations.py                   |     6 +-
 src/frob/vet/_supplychain.py                       |    22 +-
 src/frob/vet/_taint.py                             |     2 -
 src/frob/webapp/__init__.py                        |    24 +
 src/frob/webapp/_a11y_forms_contrast.py            |   661 +
 src/frob/webapp/_a11y_interaction.py               |   448 +
 src/frob/webapp/_a11y_statement.py                 |   289 +
 src/frob/webapp/_a11y_structure.py                 |   675 +
 src/frob/webapp/_a11y_substrate.py                 |   395 +
 src/frob/webapp/_comply_substrate.py               |   278 +
 src/frob/webapp/_detect.py                         |   209 +
 src/frob/webapp/_seo_substrate.py                  |   433 +
 src/frob/webapp/_websec_authz_substrate.py         |   243 +
 src/frob/webapp/_websec_bounds.py                  |   495 +
 src/frob/webapp/_websec_deser.py                   |   694 +
 src/frob/webapp/_websec_headers.py                 |   462 +
 src/frob/webapp/_websec_headers_log.py             |   459 +
 src/frob/webapp/_websec_session_config.py          |   467 +
 src/frob/webapp/_websec_sinks.py                   |   564 +
 src/frob/webapp/_websec_xss.py                     |   302 +
 src/frob/worktrees/__init__.py                     |    14 +
 src/frob/worktrees/_disposable_sweep.py            |   220 +
 src/frob/xref/__init__.py                          |    77 +-
 src/frob/yamlio.py                                 |     5 -
 strata-core/src/graph/query.rs                     |     4 +-
 strata-core/src/graph/vmodel/closure.rs            |    55 +-
 strata-core/src/graph/vmodel/mod.rs                |     6 +-
 strata-core/src/lib.rs                             |    86 +-
 strata-core/src/parse/grammar_core.rs              |    52 +-
 strata-core/src/parse/grammar_module.rs            |   136 +
 strata-core/src/parse/grammar_node.rs              |    28 +
 strata-core/src/parse/grammar_policy.rs            |    47 +
 strata-core/src/parse/mod.rs                       |   495 +-
 tests/conftest.py                                  |   187 +-
 tests/fixtures/check_stages/dup_sample.py          |    46 +
 .../csharp_dup_docblock/Sample/Dup/Duplicate.cs    |    37 +
 tests/fixtures/csharp_dup_docblock/guide.md        |    36 +
 .../python_control/duplicate.py                    |    29 +
 tests/fixtures/dsl_todo_notes/sample.c             |     3 +
 tests/fixtures/dsl_todo_notes/sample.cpp           |     3 +
 tests/fixtures/dsl_todo_notes/sample.cs            |     3 +
 tests/fixtures/dsl_todo_notes/sample.cu            |     3 +
 tests/fixtures/dsl_todo_notes/sample.java          |     3 +
 tests/fixtures/dsl_todo_notes/sample.kt            |     3 +
 tests/fixtures/dsl_todo_notes/sample.py            |     9 +
 tests/fixtures/dsl_todo_notes/sample.rs            |     3 +
 tests/fixtures/dsl_todo_notes/sample.sh            |     3 +
 tests/fixtures/dsl_todo_notes/sample.ts            |     3 +
 tests/fixtures/dsl_todo_notes/sample.zig           |     3 +
 tests/fixtures/lang/csharp/alias_using_fs_write.cs |    14 +
 .../lang/csharp/combined_static_and_namespace.cs   |    16 +
 tests/fixtures/lang/csharp/directives.cs           |    44 +
 .../dotnet_bcl_activator_createinstance_eval.cs    |    12 +
 .../lang/csharp/dotnet_bcl_assembly_load_eval.cs   |    12 +
 .../lang/csharp/dotnet_bcl_directory_fs_write.cs   |    12 +
 tests/fixtures/lang/csharp/dotnet_bcl_dns_net.cs   |    12 +
 .../dotnet_bcl_jsonserializer_deserialize.cs       |    12 +
 .../lang/csharp/dotnet_bcl_registry_fs_write.cs    |    12 +
 .../lang/csharp/dotnet_bcl_sqlcommand_sql.cs       |    13 +
 .../lang/csharp/dotnet_bcl_streamreader_fs_read.cs |    13 +
 .../csharp/dotnet_bcl_streamwriter_fs_write.cs     |    13 +
 .../lang/csharp/dotnet_bcl_type_gettype_eval.cs    |    12 +
 .../fixtures/lang/csharp/nested_property_event.cs  |    37 +
 tests/fixtures/lang/csharp/no_dangerous_apis.cs    |    17 +
 tests/fixtures/lang/csharp/plain_using_fs_write.cs |    12 +
 tests/fixtures/lang/csharp/static_using_console.cs |    12 +
 .../fixtures/lang/csharp/tests/SampleNunitTests.cs |    30 +
 .../fixtures/lang/csharp/tests/SampleUnityTests.cs |    15 +
 .../lang/csharp/tests/malformed_results.xml        |     5 +
 .../fixtures/lang/csharp/tests/sample_results.trx  |    15 +
 .../lang/csharp/tests/sample_unity_results.xml     |     9 +
 tests/fixtures/lang/csharp/unity/coroutine.cs      |    20 +
 .../lang/csharp/unity/lifecycle_methods.cs         |    21 +
 tests/fixtures/lang/csharp/unity/menu_item.cs      |    18 +
 tests/fixtures/lang/csharp/var_local_httpclient.cs |    12 +
 tests/fixtures/lang/sample.css                     |    13 +
 tests/fixtures/lang/sample.html                    |     9 +
 tests/fixtures/lang/sample.jsx                     |     5 +
 tests/fixtures/lang/sample.scss                    |    14 +
 tests/fixtures/lang/sample.vue                     |    21 +
 .../sql/explain/delete_all_sessions.explain.txt    |    11 +
 tests/fixtures/sql/explain/proven_waiver.py        |     7 +
 tests/fixtures/sql/explain/unproven_waiver.py      |     6 +
 .../migrations_indexed/migrations/0001_index.sql   |     2 +
 tests/fixtures/sql/migrations_indexed/models.py    |    15 +
 .../migrations/0001_unrelated.sql                  |     2 +
 tests/fixtures/sql/migrations_missing/models.py    |    14 +
 tests/fixtures/sql/orm/eager_loaded_loop.py        |    17 +
 .../fixtures/sql/orm/multi_write_no_transaction.py |    16 +
 tests/fixtures/sql/orm/n_plus_one_loop.py          |    18 +
 tests/fixtures/sql/orm/unbounded_all.py            |    13 +
 tests/fixtures/sql/orm/wrapped_transaction.py      |    18 +
 tests/fixtures/sql/pool_configured/db.py           |    16 +
 tests/fixtures/sql/pool_missing/db.py              |    14 +
 .../sql/python/cursor_execute_injection.py         |    16 +
 .../fixtures/sql/python/cursor_execute_literal.py  |    14 +
 tests/fixtures/sql/python/django_queryset_raw.py   |    12 +
 .../sql/python/psycopg_sql_composition_safe.py     |    18 +
 tests/fixtures/sql/python/sqlalchemy_text.py       |    15 +
 tests/fixtures/sql/rust/sqlx_query_literal.rs      |    10 +
 .../sql/squawk/0001_not_null_no_default.sql        |     4 +
 .../sql/squawk/0002_index_without_concurrently.sql |     4 +
 tests/fixtures/sql/squawk/clean.squawk.json        |     1 +
 .../squawk/index_without_concurrently.squawk.json  |    14 +
 .../sql/squawk/not_null_no_default.squawk.json     |    14 +
 .../sql/typescript/prisma_query_raw_injection.ts   |     8 +
 .../sql/typescript/prisma_query_raw_literal.ts     |     8 +
 .../unity_sample/Assets/Editor/BuildTool.cs        |    20 +
 .../fixtures/unity_sample/Assets/Scripts/Player.cs |    54 +
 .../unity_sample/Assets/Scripts/Runtime.asmdef     |     6 +
 .../unity_sample/Assets/Tests/PlayModeTests.cs     |    26 +
 .../unity_sample/Assets/Tests/Tests.asmdef         |     6 +
 tests/fixtures/unity_sample/Packages/manifest.json |     3 +
 .../ProjectSettings/ProjectVersion.txt             |     2 +
 .../Assets/Editor/Editor.asmdef                    |     6 +
 .../Assets/Editor/Editor.asmdef.meta               |     2 +
 tests/fixtures/unity_sample_asmdef/Assets/Loose.cs |     2 +
 .../Assets/Runtime/Runtime.asmdef                  |     6 +
 .../Assets/Runtime/Runtime.asmdef.meta             |     2 +
 .../Assets/RuntimeUtils/RuntimeUtils.asmdef        |     6 +
 .../Assets/RuntimeUtils/RuntimeUtils.asmdef.meta   |     2 +
 .../unity_sample_asmdef/Assets/Tests/Tests.asmdef  |     6 +
 .../Assets/Tests/Tests.asmdef.meta                 |     2 +
 .../unity_sample_asmdef/Packages/manifest.json     |     3 +
 .../ProjectSettings/ProjectVersion.txt             |     2 +
 .../forms_contrast/a11y129_negative/clean.html     |     6 +
 .../forms_contrast/a11y129_positive/violation.html |     6 +
 .../forms_contrast/a11y130_negative/clean.html     |     6 +
 .../forms_contrast/a11y130_positive/violation.html |     6 +
 .../forms_contrast/a11y131_negative/clean.html     |     6 +
 .../forms_contrast/a11y131_positive/violation.html |     5 +
 .../forms_contrast/a11y132_negative/clean.html     |     4 +
 .../forms_contrast/a11y132_positive/violation.html |     4 +
 .../forms_contrast/a11y133_negative/clean.css      |     5 +
 .../forms_contrast/a11y133_positive/violation.css  |     5 +
 .../forms_contrast/a11y134_negative/clean.css      |     6 +
 .../forms_contrast/a11y134_positive/violation.css  |     6 +
 .../forms_contrast/a11y135_negative/clean.scss     |     5 +
 .../forms_contrast/a11y135_positive/violation.scss |     5 +
 tests/fixtures/webapp/a11y1xx/html_alt/clean.html  |     7 +
 .../webapp/a11y1xx/html_alt/violation.html         |     7 +
 tests/fixtures/webapp/a11y1xx/html_lang/clean.html |     6 +
 .../webapp/a11y1xx/html_lang/violation.html        |     6 +
 .../a11y1xx/interaction/a11y116_negative/page.html |     8 +
 .../a11y1xx/interaction/a11y116_positive/page.html |     7 +
 .../a11y1xx/interaction/a11y117_negative/style.css |     6 +
 .../a11y1xx/interaction/a11y117_positive/style.css |     3 +
 .../a11y1xx/interaction/a11y118_negative/page.html |     6 +
 .../a11y1xx/interaction/a11y118_positive/page.html |     6 +
 .../a11y1xx/interaction/a11y119_negative/page.html |     6 +
 .../a11y1xx/interaction/a11y119_positive/page.html |     6 +
 .../a11y1xx/interaction/a11y120_negative/style.css |     4 +
 .../a11y1xx/interaction/a11y120_positive/style.css |     4 +
 .../a11y1xx/interaction/a11y121_negative/style.css |     4 +
 .../a11y1xx/interaction/a11y121_positive/style.css |     4 +
 .../a11y1xx/interaction/a11y122_negative/style.css |     8 +
 .../a11y1xx/interaction/a11y122_positive/style.css |     3 +
 .../a11y1xx/interaction/a11y123_negative/page.html |     6 +
 .../a11y1xx/interaction/a11y123_positive/page.html |     6 +
 .../a11y1xx/interaction/a11y124_negative/page.html |     8 +
 .../a11y1xx/interaction/a11y124_positive/page.html |     6 +
 .../webapp/a11y1xx/jsx_aria_label/clean.jsx        |     8 +
 .../webapp/a11y1xx/jsx_aria_label/violation.jsx    |     8 +
 .../statement/complete/pages/accessibility.tsx     |    14 +
 .../a11y1xx/statement/missing/pages/index.tsx      |     3 +
 .../statement/partial/pages/accessibility.tsx      |     9 +
 .../webapp/a11y1xx/structure/a11y101_clean.html    |     7 +
 .../a11y1xx/structure/a11y101_violation.html       |     7 +
 .../webapp/a11y1xx/structure/a11y102_clean.html    |     7 +
 .../a11y1xx/structure/a11y102_violation.html       |     7 +
 .../webapp/a11y1xx/structure/a11y103_clean.html    |     8 +
 .../a11y1xx/structure/a11y103_violation.html       |     8 +
 .../webapp/a11y1xx/structure/a11y104_clean.html    |     8 +
 .../a11y1xx/structure/a11y104_violation.html       |     8 +
 .../webapp/a11y1xx/structure/a11y105_clean.html    |     7 +
 .../a11y1xx/structure/a11y105_violation.html       |     7 +
 .../webapp/a11y1xx/structure/a11y106_clean.html    |     7 +
 .../a11y1xx/structure/a11y106_violation.html       |     7 +
 .../webapp/a11y1xx/structure/a11y107_clean.html    |     7 +
 .../a11y1xx/structure/a11y107_violation.html       |     7 +
 .../webapp/a11y1xx/structure/a11y108_clean.html    |     7 +
 .../a11y1xx/structure/a11y108_violation.html       |     7 +
 .../webapp/a11y1xx/structure/a11y109_clean.html    |     7 +
 .../a11y1xx/structure/a11y109_violation.html       |     7 +
 .../webapp/a11y1xx/structure/a11y110_clean.html    |     7 +
 .../a11y1xx/structure/a11y110_violation.html       |     7 +
 .../webapp/a11y1xx/structure/a11y111_clean.html    |    10 +
 .../a11y1xx/structure/a11y111_violation.html       |     9 +
 .../webapp/a11y1xx/structure/a11y112_clean.html    |    10 +
 .../a11y1xx/structure/a11y112_violation.html       |    10 +
 .../webapp/a11y1xx/structure/a11y113_clean.html    |     8 +
 .../a11y1xx/structure/a11y113_violation.html       |     8 +
 .../webapp/a11y1xx/structure/a11y114_clean.html    |     7 +
 .../a11y1xx/structure/a11y114_violation.html       |     7 +
 .../webapp/a11y1xx/structure/a11y115_clean.html    |     7 +
 .../a11y1xx/structure/a11y115_violation.html       |     7 +
 .../fixtures/webapp/a11y1xx/vue_headings/clean.vue |     6 +
 .../webapp/a11y1xx/vue_headings/violation.vue      |     5 +
 tests/fixtures/webapp/astro/astro.config.mjs       |     4 +
 .../webapp/comply1xx/pages_flask_missing/app.py    |     8 +
 .../comply1xx/pages_flask_missing/requirements.txt |     1 +
 .../webapp/comply1xx/pages_flask_present/app.py    |    18 +
 .../comply1xx/pages_flask_present/requirements.txt |     1 +
 .../comply1xx/pages_nextjs_missing/next.config.js  |     1 +
 .../app/accessibility/page.tsx                     |     1 +
 .../pages_nextjs_present/app/privacy/page.tsx      |     1 +
 .../pages_nextjs_present/app/terms/page.tsx        |     1 +
 .../comply1xx/pages_nextjs_present/next.config.js  |     1 +
 .../webapp/comply1xx/plain/requirements.txt        |     1 +
 .../webapp/comply1xx/signal_ai/requirements.txt    |     1 +
 .../webapp/comply1xx/signal_data_sale/package.json |     1 +
 .../webapp/comply1xx/signal_email/package.json     |     1 +
 .../comply1xx/signal_health/requirements.txt       |     1 +
 .../comply1xx/signal_session_replay/package.json   |     1 +
 .../webapp/comply1xx/signal_sms/requirements.txt   |     1 +
 .../comply1xx/signal_subscriptions/package.json    |     1 +
 tests/fixtures/webapp/django/manage.py             |    11 +
 tests/fixtures/webapp/fastapi/main.py              |     5 +
 tests/fixtures/webapp/fastapi/requirements.txt     |     2 +
 tests/fixtures/webapp/flask/app.py                 |     5 +
 tests/fixtures/webapp/flask/requirements.txt       |     1 +
 tests/fixtures/webapp/laravel/artisan              |     0
 tests/fixtures/webapp/laravel/composer.json        |     7 +
 tests/fixtures/webapp/nextjs/next.config.js        |     2 +
 tests/fixtures/webapp/plain_python_cli/main.py     |    10 +
 tests/fixtures/webapp/rails/Gemfile                |     2 +
 tests/fixtures/webapp/seo1xx/routes/about.html     |    11 +
 tests/fixtures/webapp/seo1xx/routes/duplicate.html |    10 +
 tests/fixtures/webapp/seo1xx/routes/home.html      |    13 +
 tests/fixtures/webapp/seo1xx/routes/no_head.html   |     6 +
 tests/fixtures/webapp/seo1xx/routes/no_head.jsx    |     3 +
 tests/fixtures/webapp/seo1xx/routes/product.jsx    |    12 +
 tests/fixtures/webapp/sveltekit/svelte.config.js   |     6 +
 tests/fixtures/webapp/vite/vite.config.js          |     2 +
 .../bounds/webesc123_negative/requirements.txt     |     1 +
 .../websec1xx/bounds/webesc123_negative/schema.py  |     7 +
 .../bounds/webesc123_positive/requirements.txt     |     1 +
 .../websec1xx/bounds/webesc123_positive/schema.py  |     7 +
 .../bounds/webesc124_negative/requirements.txt     |     1 +
 .../bounds/webesc124_negative/xml_parse.py         |     7 +
 .../bounds/webesc124_positive/requirements.txt     |     1 +
 .../bounds/webesc124_positive/xml_parse.py         |     7 +
 .../websec1xx/bounds/webesc125_negative/recurse.py |     8 +
 .../bounds/webesc125_negative/requirements.txt     |     1 +
 .../websec1xx/bounds/webesc125_positive/recurse.py |     6 +
 .../bounds/webesc125_positive/requirements.txt     |     1 +
 .../websec1xx/deser/webesc109_negative/app.py      |     5 +
 .../deser/webesc109_negative/requirements.txt      |     1 +
 .../websec1xx/deser/webesc109_positive/app.py      |     6 +
 .../deser/webesc109_positive/requirements.txt      |     1 +
 .../websec1xx/deser/webesc110_negative/app.py      |     2 +
 .../deser/webesc110_negative/requirements.txt      |     1 +
 .../websec1xx/deser/webesc110_positive/app.py      |     2 +
 .../deser/webesc110_positive/requirements.txt      |     1 +
 .../websec1xx/deser/webesc111_negative/app.py      |     5 +
 .../deser/webesc111_negative/requirements.txt      |     1 +
 .../websec1xx/deser/webesc111_positive/app.py      |     5 +
 .../deser/webesc111_positive/requirements.txt      |     1 +
 .../websec1xx/deser/webesc112_negative/app.py      |     5 +
 .../deser/webesc112_negative/requirements.txt      |     1 +
 .../websec1xx/deser/webesc112_positive/app.py      |     5 +
 .../deser/webesc112_positive/requirements.txt      |     1 +
 .../websec1xx/deser/webesc113_negative/app.py      |     5 +
 .../deser/webesc113_negative/requirements.txt      |     1 +
 .../websec1xx/deser/webesc113_positive/app.py      |     5 +
 .../deser/webesc113_positive/requirements.txt      |     1 +
 .../websec1xx/deser/webesc114_negative/app.py      |     2 +
 .../deser/webesc114_negative/requirements.txt      |     1 +
 .../websec1xx/deser/webesc114_positive/app.py      |     2 +
 .../deser/webesc114_positive/requirements.txt      |     1 +
 .../websec1xx/deser/webesc115_negative/app.py      |     2 +
 .../deser/webesc115_negative/requirements.txt      |     1 +
 .../websec1xx/deser/webesc115_positive/app.py      |     5 +
 .../deser/webesc115_positive/requirements.txt      |     1 +
 .../websec1xx/deser/webesc116_negative/build.sh    |     2 +
 .../deser/webesc116_negative/requirements.txt      |     1 +
 .../websec1xx/deser/webesc116_positive/build.sh    |     2 +
 .../deser/webesc116_positive/requirements.txt      |     1 +
 .../headers_log/websec117_negative/manage.py       |     1 +
 .../headers_log/websec117_negative/views.py        |     5 +
 .../headers_log/websec117_positive/manage.py       |     1 +
 .../headers_log/websec117_positive/views.py        |     2 +
 .../headers_log/websec118_negative/manage.py       |     1 +
 .../headers_log/websec118_negative/views.py        |     5 +
 .../headers_log/websec118_positive/manage.py       |     1 +
 .../headers_log/websec118_positive/views.py        |     2 +
 .../headers_log/websec119_negative/manage.py       |     1 +
 .../headers_log/websec119_negative/views.py        |     7 +
 .../headers_log/websec119_positive/manage.py       |     1 +
 .../headers_log/websec119_positive/views.py        |     7 +
 .../headers_log/websec120_negative/manage.py       |     1 +
 .../headers_log/websec120_negative/views.py        |     7 +
 .../headers_log/websec120_positive/manage.py       |     1 +
 .../headers_log/websec120_positive/views.py        |     4 +
 .../headers_log/websec121_negative/manage.py       |     1 +
 .../headers_log/websec121_negative/views.py        |     5 +
 .../headers_log/websec121_positive/manage.py       |     1 +
 .../headers_log/websec121_positive/views.py        |     5 +
 .../headers_log/websec122_negative/manage.py       |     1 +
 .../headers_log/websec122_negative/socket.js       |     9 +
 .../headers_log/websec122_positive/manage.py       |     1 +
 .../headers_log/websec122_positive/socket.js       |     4 +
 .../webapp/websec1xx/webesc101_negative/src/app.js |     3 +
 .../websec1xx/webesc101_negative/vite.config.js    |     1 +
 .../webapp/websec1xx/webesc101_positive/src/app.js |     3 +
 .../websec1xx/webesc101_positive/vite.config.js    |     1 +
 .../websec1xx/webesc102_negative/src/App.jsx       |     3 +
 .../websec1xx/webesc102_negative/vite.config.js    |     1 +
 .../websec1xx/webesc102_positive/src/App.jsx       |     3 +
 .../websec1xx/webesc102_positive/vite.config.js    |     1 +
 .../websec1xx/webesc103_negative/src/App.vue       |     6 +
 .../websec1xx/webesc103_negative/vite.config.js    |     1 +
 .../websec1xx/webesc103_positive/src/App.vue       |     6 +
 .../websec1xx/webesc103_positive/vite.config.js    |     1 +
 .../websec1xx/webesc104_negative/requirements.txt  |     1 +
 .../webesc104_negative/templates/index.html        |     1 +
 .../websec1xx/webesc104_positive/requirements.txt  |     1 +
 .../webesc104_positive/templates/index.html        |     1 +
 .../webapp/websec1xx/webesc105_negative/manage.py  |     1 +
 .../webapp/websec1xx/webesc105_negative/views.py   |     5 +
 .../webapp/websec1xx/webesc105_positive/manage.py  |     1 +
 .../webapp/websec1xx/webesc105_positive/views.py   |     5 +
 .../webapp/websec1xx/webesc106_negative/Gemfile    |     1 +
 .../webesc106_negative/app/views/show.html.erb     |     1 +
 .../webapp/websec1xx/webesc106_positive/Gemfile    |     1 +
 .../webesc106_positive/app/views/show.html.erb     |     1 +
 .../websec1xx/xss/webesc107_negative/Gemfile       |     1 +
 .../xss/webesc107_negative/app/views/show.html.erb |     1 +
 .../websec1xx/xss/webesc107_positive/Gemfile       |     1 +
 .../xss/webesc107_positive/app/views/show.html.erb |     1 +
 .../websec1xx/xss/webesc108_negative/composer.json |     5 +
 .../websec1xx/xss/webesc108_negative/index.php     |     2 +
 .../websec1xx/xss/webesc108_positive/composer.json |     5 +
 .../websec1xx/xss/webesc108_positive/index.php     |     2 +
 .../webapp/websec2xx/django_compliant/manage.py    |    11 +
 .../webapp/websec2xx/django_compliant/settings.py  |    13 +
 .../webapp/websec2xx/django_violating/manage.py    |    11 +
 .../webapp/websec2xx/django_violating/settings.py  |     9 +
 .../webapp/websec2xx/express_compliant/app.js      |    20 +
 .../websec2xx/express_compliant/package.json       |     8 +
 .../webapp/websec2xx/express_violating/app.js      |    15 +
 .../websec2xx/express_violating/package.json       |     7 +
 .../webapp/websec2xx/flask_compliant/app.py        |    14 +
 .../websec2xx/flask_compliant/requirements.txt     |     2 +
 .../webapp/websec2xx/flask_violating/app.py        |    10 +
 .../websec2xx/flask_violating/requirements.txt     |     1 +
 .../webapp/websec2xx/rails_compliant/Gemfile       |     2 +
 .../app/controllers/application_controller.rb      |     3 +
 .../config/initializers/session_store.rb           |     7 +
 .../webapp/websec2xx/rails_violating/Gemfile       |     2 +
 .../app/controllers/application_controller.rb      |     2 +
 .../config/initializers/session_store.rb           |     5 +
 .../fixtures/webapp/websec3xx/caddy_full/Caddyfile |     9 +
 .../webapp/websec3xx/caddy_missing_hsts/Caddyfile  |     8 +
 .../webapp/websec3xx/django_full/manage.py         |     7 +
 .../webapp/websec3xx/django_full/requirements.txt  |     1 +
 .../webapp/websec3xx/django_full/settings.py       |     7 +
 .../webapp/websec3xx/django_missing_xfo/manage.py  |     7 +
 .../websec3xx/django_missing_xfo/requirements.txt  |     1 +
 .../websec3xx/django_missing_xfo/settings.py       |     6 +
 .../webapp/websec3xx/express_helmet/app.js         |    11 +
 .../webapp/websec3xx/express_helmet/package.json   |     8 +
 .../webapp/websec3xx/nginx_full/nginx.conf         |    10 +
 .../webapp/websec3xx/nginx_missing_csp/nginx.conf  |     9 +
 .../fixtures/webapp/websec3xx/no_evidence/main.py  |    10 +
 tests/fixtures/webapp/websec4xx/django/views.py    |    15 +
 tests/fixtures/webapp/websec4xx/fastapi/main.py    |    25 +
 tests/fixtures/webapp/websec4xx/flask/app.py       |    21 +
 .../webapp/websec4xx/rails/orders_controller.rb    |    13 +
 tests/gates/test_bug_repro_at_ref_public.py        |     2 +
 tests/gates/test_comment_placement.py              |    22 +-
 tests/gates/test_docarch_structural.py             |   223 +
 tests/gates/test_docptr.py                         |   126 +
 tests/gates/test_docstring_archaeology.py          |     5 +
 tests/gates/test_mutation_evidence_err_branches.py |     1 +
 tests/gates/test_rule_id_scan_branches.py          |    79 +-
 tests/gates/test_scan_timeout_enforcement.py       |    32 -
 tests/gates/test_scope_symref_helpers.py           |     3 +
 tests/gates/test_tdd_order.py                      |    27 +
 tests/gates_suite/test_claim_lint.py               |   169 +
 tests/gates_suite/test_compliance.py               |   112 +-
 tests/gates_suite/test_config_path_defaults.py     |   147 +
 tests/gates_suite/test_coverage.py                 |   420 +-
 tests/gates_suite/test_debt.py                     |    79 +-
 .../gates_suite/test_depr003_severity_override.py  |    10 +-
 tests/gates_suite/test_doc.py                      |     9 +
 tests/gates_suite/test_docblocks_refs_cov009.py    |   134 +
 tests/gates_suite/test_exhaust_burndown_t3861.py   |    54 +
 tests/gates_suite/test_fix_engine.py               |   286 +-
 tests/gates_suite/test_forbid_rules.py             |   199 +
 tests/gates_suite/test_guard_closure.py            |   235 +
 tests/gates_suite/test_invariant.py                |   269 +
 tests/gates_suite/test_prework.py                  |    12 +-
 tests/gates_suite/test_protocol.py                 |    83 +-
 tests/gates_suite/test_route_response_model.py     |   159 +
 tests/gates_suite/test_run.py                      |    68 +-
 tests/gates_suite/test_severity_overrides_pin.py   |    13 +-
 tests/gates_suite/test_sys.py                      |   146 +-
 tests/gates_suite/test_sys_assume_template.py      |   283 +
 tests/gates_suite/test_sys_rule_liveness.py        |   327 +
 tests/gates_suite/test_test_gate.py                |   173 +-
 tests/gates_suite/test_tick.py                     |    93 +-
 tests/gates_suite/test_tick_dead_worktree.py       |   271 +
 tests/gates_suite/test_waive.py                    |    68 +-
 tests/gates_suite/test_wire.py                     |    47 +-
 tests/integration/test_interfaces.py               |     3 +
 tests/narrative/test_bulk.py                       |   263 +
 tests/narrative/test_docarch002_fix.py             |   353 +
 tests/system/conftest.py                           |    16 +-
 tests/system/test_artifact_smoke.py                |    37 +-
 tests/system/test_cli_check.py                     |    64 +-
 tests/system/test_cli_cycle.py                     |     2 +
 tests/system/test_cli_doctor.py                    |    11 +-
 tests/system/test_cli_evidence_enforcement.py      |    15 +-
 tests/system/test_cli_native_missing.py            |     1 +
 tests/system/test_cli_perf.py                      |     3 +
 tests/system/test_cli_scaffold_apply.py            |    37 +
 tests/system/test_cli_sys_audit.py                 |     8 +-
 tests/system/test_cli_sys_plan.py                  |     3 +-
 tests/system/test_cli_ticket.py                    |    25 +-
 tests/system/test_fleet_status_ground_truth.py     |    25 +-
 tests/system/test_frob_self_model.py               |   241 +-
 tests/system/test_run_helper_env_leak.py           |    25 +-
 tests/system/test_scaffold_pool.py                 |    11 +
 tests/system/test_scaffold_pool_cli.py             |     1 +
 tests/system/test_scaffold_unity_project_cli.py    |   104 +
 tests/system/test_unity_e2e.py                     |   256 +
 tests/test_ack_worktree_lease.py                   |     3 +
 tests/test_app.py                                  |     7 +-
 tests/test_app_config.py                           |    13 +
 tests/test_app_daemon_proxy.py                     |    88 +-
 tests/test_arch_gate.py                            |    31 +-
 tests/test_bug002_no_behavior_change.py            |     4 +
 tests/test_cache_gate.py                           |    12 +-
 tests/test_capability_registry.py                  |     1 +
 tests/test_check_coverage_registry.py              |     2 +
 tests/test_check_gate_base.py                      |    54 +
 tests/test_check_runner.py                         |   120 +-
 tests/test_ci_report.py                            |     5 +
 tests/test_ci_validity.py                          |     6 +
 tests/test_ci_workflow_job_summary.py              |     8 -
 tests/test_ci_workflow_matrix.py                   |    54 +-
 tests/test_ci_workflow_timeout.py                  |     7 +-
 tests/test_clean.py                                |    15 +
 tests/test_coverage.py                             |    62 +-
 tests/test_coverage_wait_shared.py                 |    41 +-
 tests/test_dataset_construct.py                    |   109 +
 tests/test_debt_runner.py                          |     2 +
 tests/test_decisions.py                            |     1 +
 tests/test_deprecated_runner.py                    |     1 +
 tests/test_docblocks_gate.py                       |    25 +
 tests/test_docenum_gate.py                         |    41 +
 tests/test_docptr_gate.py                          |   147 +-
 tests/test_dup.py                                  |     1 +
 tests/test_dup_inline.py                           |    18 +-
 tests/test_evidence_integrity.py                   |   127 +-
 tests/test_excludes.py                             |    96 +-
 tests/test_gate_cache.py                           |    70 +-
 tests/test_gates_directive_stack.py                |   290 +
 tests/test_gates_empty_diff_close.py               |   181 +-
 tests/test_gates_fix_engine.py                     |   361 +-
 tests/test_gates_fmt_directives.py                 |   327 +-
 tests/test_gates_milestone.py                      |    40 +
 tests/test_gates_mutation_evidence.py              |    78 +-
 tests/test_gates_ratchet.py                        |    60 +
 tests/test_gates_suppress.py                       |    54 +-
 tests/test_gates_test019.py                        |     8 +-
 tests/test_gates_tick005.py                        |     8 +-
 tests/test_gates_tick006_sibling_worktree.py       |    18 +-
 tests/test_gates_tick009_tick010.py                |     8 +-
 tests/test_gates_tickets_hygiene.py                |     1 +
 tests/test_gates_vmodel.py                         |     6 +
 tests/test_ghio.py                                 |     9 +
 tests/test_gitio.py                                |    59 +
 tests/test_graph.py                                |   120 +-
 tests/test_graph_affects.py                        |    54 +
 tests/test_graph_lock.py                           |     7 +
 tests/test_graph_reach.py                          |     2 +
 tests/test_hook_dispatch_telemetry.py              |    31 +
 tests/test_hook_frob_suggest.py                    |   272 +-
 tests/test_hook_frob_timeout_guard.py              |    65 +-
 tests/test_hook_pgrep_self_match_guard.py          |   114 +
 tests/test_hook_root_write_guard.py                |   129 +-
 tests/test_hook_sync_claude_config.py              |   198 +
 tests/test_land_verify_claims_outcome.py           |    32 +-
 tests/test_lang.py                                 |   196 +-
 tests/test_lang_conformance_gate.py                |   105 +-
 tests/test_lang_css.py                             |    97 +
 tests/test_lang_html_js_jsx_vue.py                 |   116 +
 tests/test_lang_support.py                         |    32 +-
 tests/test_mutate.py                               |     4 +
 tests/test_mutate_journal.py                       |    44 +-
 tests/test_narrative_blocks.py                     |    34 +
 tests/test_narrative_migrate.py                    |   186 +
 tests/test_perf.py                                 |    31 +-
 tests/test_perf_rules_internals.py                 |    15 +-
 tests/test_pii_provenance_trust_identity.py        |   184 +
 tests/test_pii_structural_gate.py                  |   155 +-
 tests/test_policy.py                               |   199 +
 tests/test_pool_runner.py                          |     1 +
 tests/test_prework_parity.py                       |     1 +
 tests/test_refactor.py                             |   505 +-
 tests/test_refactor_corpus.py                      |     3 +-
 tests/test_refs_gate.py                            |    65 +-
 tests/test_registry_corpus.py                      |     8 +-
 tests/test_registry_exhaustiveness.py              |    29 +
 tests/test_registry_models.py                      |     7 +
 tests/test_registry_reconciliation_compliance.py   |    27 +-
 tests/test_registry_reconciliation_patterns.py     |    21 +-
 tests/test_registry_reconciliation_pii.py          |    21 +-
 tests/test_registry_reconciliation_secrets.py      |    21 +-
 tests/test_registry_staleness.py                   |    18 +-
 tests/test_release.py                              |   107 +-
 tests/test_release_worktree_lease.py               |     2 +
 tests/test_scaffold_worktree_lease_hook.py         |    36 +-
 tests/test_secrets_gate.py                         |     2 +
 tests/test_serve.py                                |     3 +-
 tests/test_serve_daemon.py                         |    74 +-
 tests/test_serve_events.py                         |    25 +-
 tests/test_serve_leases.py                         |    34 +-
 tests/test_serve_socket.py                         |    64 +-
 tests/test_serve_tools_daemon_bypass.py            |     3 +
 tests/test_serve_watch.py                          |    12 +-
 tests/test_stats_agentic.py                        |     6 +
 tests/test_status.py                               |     9 +
 tests/test_telemetry.py                            |     5 +
 tests/test_testing.py                              |   109 +-
 tests/test_testing_collect.py                      |     1 +
 tests/test_tick012_gate.py                         |     4 +
 tests/test_tick013_gate.py                         |     6 +
 tests/test_ticket_done_report_claims.py            |    11 +
 tests/test_ticket_evidence.py                      |    51 +-
 tests/test_ticket_journal.py                       |    12 +
 tests/test_ticket_land_lint_diff_attribution.py    |    29 +-
 tests/test_ticket_land_proof_claims.py             |    20 +-
 tests/test_ticket_land_ty_diff_attribution.py      |    10 +-
 tests/test_ticket_leases.py                        |   563 +-
 tests/test_ticket_leases_cross_worktree.py         |   210 +-
 tests/test_ticket_lifecycle.py                     |     6 +
 tests/test_ticket_merge_driver.py                  |     6 +-
 tests/test_ticket_ownership_guard.py               |    12 +-
 tests/test_ticket_reconcile.py                     |   301 +-
 tests/test_ticket_reverify.py                      |     9 +
 tests/test_ticket_runner_archive_force.py          |     3 +
 tests/test_ticket_runner_done_report.py            |     3 +
 tests/test_ticket_runner_pytest_env.py             |     2 +
 tests/test_ticket_store_stale_snapshot.py          |    22 +-
 tests/test_ticket_work_and_land_finish.py          |   305 +-
 tests/test_tickets.py                              |   376 +-
 tests/test_tickets_acceptance.py                   |    38 +-
 tests/test_tickets_body.py                         |     7 +
 tests/test_tickets_brief.py                        |    17 +
 tests/test_tickets_cmd_evidence.py                 |     9 +-
 tests/test_tickets_collision.py                    |    30 +-
 tests/test_tickets_dispatch_stale.py               |    11 +
 tests/test_tickets_evidence_cli.py                 |    50 +-
 tests/test_tickets_gate_claim_evidence.py          |    10 +-
 tests/test_tickets_lease.py                        |    67 +-
 tests/test_tickets_lease_overlay.py                |    16 +-
 tests/test_tickets_leases.py                       |    51 +-
 tests/test_tickets_ledger_concurrency.py           |     9 +
 tests/test_tickets_live_tracker.py                 |    41 +-
 tests/test_tickets_migration.py                    |   141 +-
 tests/test_tickets_milestone_runs_last.py          |     8 +
 tests/test_tickets_milestone_sort.py               |    11 +
 tests/test_tickets_mutation_evidence.py            |    11 +
 tests/test_tickets_new_gate_rule_acceptance.py     |    13 +
 tests/test_tickets_no_scope.py                     |    14 +-
 tests/test_tickets_organization.py                 |    30 +-
 tests/test_tickets_own_obligations.py              |     3 +
 tests/test_tickets_parent.py                       |   301 +-
 tests/test_tickets_points.py                       |   293 +
 tests/test_tickets_priority.py                     |   122 +-
 tests/test_tickets_registry_files.py               |   221 +
 tests/test_tickets_review.py                       |    11 +
 tests/test_tickets_rule_shaped.py                  |     3 +
 tests/test_tickets_scope_mutation.py               |    79 +-
 tests/test_tickets_sprint_migrate.py               |   188 +
 tests/test_tickets_tiers.py                        |     3 +
 tests/test_tickets_triage_dates.py                 |    31 +-
 tests/test_tickets_velocity.py                     |    75 +-
 tests/test_tickets_wave.py                         |    14 +-
 tests/test_todo_fmt_gate.py                        |    17 +
 tests/test_vet_containment.py                      |     3 +
 tests/test_waive_gate.py                           |   178 +-
 tests/test_walk_lint_gate.py                       |    21 +
 tests/test_worktree_guard.py                       |    84 +-
 tests/test_worktree_pythonpath.py                  |    13 +-
 tests/ticket_land_suite/test_archive.py            |    53 +-
 tests/ticket_land_suite/test_claim_close.py        |    43 +-
 tests/ticket_land_suite/test_dirt_ownership.py     |    80 +-
 tests/ticket_land_suite/test_draft.py              |   115 +-
 tests/ticket_land_suite/test_land_core.py          |   105 +-
 tests/ticket_land_suite/test_land_lock.py          |   167 +-
 tests/ticket_land_suite/test_land_plan.py          |    81 +-
 .../test_land_proof_unmeasured.py                  |   112 +
 .../ticket_land_suite/test_land_reaps_worktree.py  |    99 +
 tests/ticket_land_suite/test_ledger_splice.py      |    48 +-
 tests/ticket_land_suite/test_push.py               |    45 +-
 tests/ticket_land_suite/test_release.py            |    78 +-
 tests/ticket_land_suite/test_verify_intent.py      |    91 +-
 tests/ticket_land_suite/test_verify_reset.py       |    48 +-
 tests/ticket_land_suite/test_waive_deletion.py     |    26 +-
 tests/ticket_land_suite/test_wip.py                |    23 +-
 tests/tickets/__init__.py                          |     0
 tests/tickets/test_land_squash.py                  |   104 +
 tests/unit/arch_suite/test_abstraction.py          |    15 +
 tests/unit/arch_suite/test_complexity.py           |    15 +-
 tests/unit/arch_suite/test_concurrency.py          |    74 +-
 tests/unit/arch_suite/test_dispatch.py             |     9 +-
 tests/unit/arch_suite/test_lang_adapters.py        |    22 +-
 tests/unit/arch_suite/test_logging.py              |    21 +
 tests/unit/arch_suite/test_lsp.py                  |    18 +
 tests/unit/arch_suite/test_misc.py                 |    23 +
 tests/unit/arch_suite/test_smells.py               |    16 +
 tests/unit/arch_suite/test_type_design.py          |    25 +
 tests/unit/coordinator_suite/test_check_summary.py |    12 +
 .../test_count_ticket_citations.py                 |   175 +
 .../unit/coordinator_suite/test_fleet_host_load.py |    57 +-
 tests/unit/coordinator_suite/test_fleet_land.py    |    29 +-
 tests/unit/coordinator_suite/test_fleet_report.py  |   118 +-
 .../unit/coordinator_suite/test_fleet_worktrees.py |    98 +-
 .../coordinator_suite/test_strip_help_citations.py |   171 +
 tests/unit/coordinator_suite/test_verify_lands.py  |    14 +
 .../coordinator_suite/test_wait_for_land_slot.py   |     8 +
 tests/unit/fleet/test_manifest.py                  |     6 +
 tests/unit/fleet/test_route.py                     |     4 +
 tests/unit/fleet/test_status.py                    |    21 +-
 .../unit/gates/test_cov002_strata_declarations.py  |   131 +
 tests/unit/gates/test_deprecated_baseline.py       |    36 +-
 tests/unit/gates/test_detector_scope.py            |    17 +-
 tests/unit/gates/test_doc011.py                    |     1 +
 tests/unit/gates/test_examined_sites.py            |    19 +-
 .../gates/test_exhaustive_handling_path_shape.py   |    20 +-
 tests/unit/gates/test_ffi_boundary_path_shape.py   |    22 +-
 tests/unit/gates/test_lexical_selfcheck.py         |    26 +-
 tests/unit/gates/test_lock_producer.py             |     6 +
 tests/unit/gates/test_negexist.py                  |    13 +
 tests/unit/gates/test_pkg_resources.py             |    15 +-
 tests/unit/gates/test_port_selfcheck.py            |    16 +-
 tests/unit/gates/test_profile_boundary.py          |     5 +
 .../gates/test_profile_boundary_subject_count.py   |     8 +-
 tests/unit/gates/test_rel001_deferred_bump.py      |     5 +
 tests/unit/gates/test_tool_registry_gate.py        |   124 +
 tests/unit/gates/test_version_coupling.py          |    10 +
 tests/unit/gates/test_win32_kill_signal.py         |     1 +
 tests/unit/gates/test_wire001_cli_dest_semantic.py |    24 +-
 tests/unit/graph/test_dsl.py                       |   479 +-
 tests/unit/graph/test_dsl_invariant_property.py    |    69 +
 tests/unit/graph/test_dsl_markdown_waive.py        |    46 +-
 tests/unit/lang/test_csharp_directives.py          |   115 +
 tests/unit/perf/test_advisories.py                 |     7 +
 tests/unit/perf/test_cache_effects.py              |    92 +
 tests/unit/perf/test_collectors.py                 |     8 +
 tests/unit/perf/test_dup_spawn.py                  |    18 +-
 tests/unit/perf/test_effect_summaries.py           |    22 +-
 tests/unit/perf/test_harness_sampling.py           |     4 +
 tests/unit/perf/test_hot_query.py                  |     3 +
 tests/unit/perf/test_hotgraph.py                   |     9 +
 tests/unit/perf/test_hotpath_smells.py             |    25 +-
 tests/unit/perf/test_loop_effects.py               |     9 +
 tests/unit/perf/test_loop_variant.py               |    90 +
 tests/unit/perf/test_persist_run_cli.py            |     1 +
 tests/unit/perf/test_ratchet.py                    |    12 +
 tests/unit/perf/test_serial_pools.py               |     6 +
 tests/unit/perf/test_sketch_store.py               |    29 +
 tests/unit/rapid_sweep_suite/test_attribution.py   |    56 +-
 tests/unit/rapid_sweep_suite/test_baseline.py      |    71 +-
 tests/unit/rapid_sweep_suite/test_commit.py        |    64 +-
 tests/unit/rapid_sweep_suite/test_dispose.py       |    78 +-
 tests/unit/rapid_sweep_suite/test_filing.py        |   105 +-
 tests/unit/rapid_sweep_suite/test_sweep_run.py     |    59 +-
 tests/unit/rapid_sweep_suite/test_window.py        |   455 +
 tests/unit/rapid_sweep_suite/test_worktrees.py     |    10 +-
 tests/unit/security/test_redact.py                 |    38 +
 tests/unit/sql/test_extract.py                     |   175 +
 tests/unit/sql/test_orm_rules.py                   |   138 +
 tests/unit/sql/test_sqlfluff_plugin.py             |   108 +
 tests/unit/sql/test_squawk_adapter.py              |    81 +
 .../strata/fixtures/outbound_destination/config.py |     5 +
 .../fixtures/outbound_destination/configured.py    |    12 +
 .../fixtures/outbound_destination/hardcoded.py     |    10 +
 tests/unit/strata/test_access.py                   |    45 +-
 tests/unit/strata/test_admit_phase_wiring.py       |   241 +
 tests/unit/strata/test_audit.py                    |    12 +-
 tests/unit/strata/test_backpressure.py             |    25 +-
 tests/unit/strata/test_bootstrap.py                |     7 +
 tests/unit/strata/test_capacity.py                 |     8 +-
 tests/unit/strata/test_capacity_projection.py      |     1 +
 tests/unit/strata/test_circuit_breaker.py          |    30 +-
 tests/unit/strata/test_claims.py                   |    13 +-
 tests/unit/strata/test_claims_overdue.py           |   110 +
 tests/unit/strata/test_clock_ordering.py           |    25 +-
 tests/unit/strata/test_conform_eval_needle.py      |    18 +-
 tests/unit/strata/test_contention.py               |    60 +-
 tests/unit/strata/test_crash.py                    |     1 +
 tests/unit/strata/test_cve_fingerprint.py          |    16 +-
 tests/unit/strata/test_cve_fingerprint_scan.py     |     8 +
 tests/unit/strata/test_delivery_semantics.py       |    25 +-
 tests/unit/strata/test_demand.py                   |    38 +-
 tests/unit/strata/test_design_load.py              |    10 +-
 tests/unit/strata/test_distributed_txn.py          |    22 +-
 tests/unit/strata/test_effects.py                  |    68 +-
 tests/unit/strata/test_elaborate.py                |     1 +
 tests/unit/strata/test_facts.py                    |    24 +-
 tests/unit/strata/test_fallback.py                 |    22 +-
 tests/unit/strata/test_fragments.py                |    74 +-
 tests/unit/strata/test_host_isolation.py           |     2 +
 tests/unit/strata/test_inbound_rate.py             |   134 +
 tests/unit/strata/test_interactive_cost.py         |    19 +-
 tests/unit/strata/test_kernel_doc_extensions.py    |    67 +
 tests/unit/strata/test_krb_movement.py             |     2 +
 tests/unit/strata/test_litmus_waive.py             |     1 +
 tests/unit/strata/test_message_schema.py           |    22 +-
 tests/unit/strata/test_mode_conformance.py         |    66 +-
 tests/unit/strata/test_multifile.py                |    24 +-
 tests/unit/strata/test_mutation_audit.py           |    35 +-
 tests/unit/strata/test_native_staleness.py         |    91 +-
 tests/unit/strata/test_native_test.py              |    20 +-
 tests/unit/strata/test_obligation_proof.py         |    31 +-
 tests/unit/strata/test_observability.py            |    25 +-
 tests/unit/strata/test_outbound_destination.py     |   180 +
 tests/unit/strata/test_packs_analyzable_warning.py |    87 +
 tests/unit/strata/test_parse.py                    |    14 +-
 tests/unit/strata/test_policy.py                   |     2 +
 tests/unit/strata/test_process_bounds.py           |    37 +-
 tests/unit/strata/test_registry_cross_refs.py      |    12 +-
 tests/unit/strata/test_reliability.py              |    50 +-
 tests/unit/strata/test_retry.py                    |    31 +-
 tests/unit/strata/test_selfconform.py              |   480 +-
 tests/unit/strata/test_shared_state.py             |    19 +-
 tests/unit/strata/test_shrink.py                   |    14 +-
 tests/unit/strata/test_slo.py                      |    16 +-
 tests/unit/strata/test_spof.py                     |     7 +-
 tests/unit/strata/test_ssot.py                     |    19 +-
 tests/unit/strata/test_starvation.py               |    31 +-
 tests/unit/strata/test_strata_core_gil.py          |     7 +-
 tests/unit/strata/test_strata_scan_cache.py        |   207 +
 tests/unit/strata/test_supply_chain_boot.py        |    37 +-
 tests/unit/strata/test_sync_depth.py               |    10 +-
 tests/unit/strata/test_sync_may.py                 |     3 +
 .../unit/strata/test_sys107_via_scope_advisory.py  |     3 +
 tests/unit/strata/test_threat.py                   |    68 +-
 tests/unit/strata/test_txn.py                      |    25 +-
 tests/unit/strata/test_unity_asmdef.py             |   173 +
 tests/unit/strata/test_vmodel_authoring.py         |    41 +-
 tests/unit/test_ack_runner.py                      |     8 +
 tests/unit/test_app_config_flag_coverage.py        |    55 +
 tests/unit/test_app_config_from_external_t1276.py  |    53 +-
 ...t_app_config_pyproject_root_t_draft_1f1ae69b.py |    66 +
 tests/unit/test_app_runners.py                     |    49 +-
 tests/unit/test_app_runners_batch5.py              |    13 +
 tests/unit/test_app_runners_batch6.py              |    54 +-
 tests/unit/test_app_runners_batch7.py              |   210 +-
 tests/unit/test_app_runners_doable_stale_lease.py  |    33 +-
 tests/unit/test_app_runners_json_guard_t2492.py    |     7 +-
 tests/unit/test_app_runners_process.py             |     8 +
 .../unit/test_app_runners_t0875_leaf_collision.py  |     6 +-
 .../test_app_runners_t0976_mutation_evidence.py    |     8 +
 tests/unit/test_app_runners_t1738_wave.py          |     3 +
 .../unit/test_app_runners_t1822_already_landed.py  |     4 +
 tests/unit/test_app_runners_t2395_contention.py    |     3 +
 tests/unit/test_app_style.py                       |    10 +-
 tests/unit/test_app_sys_capacity.py                |     5 +
 tests/unit/test_app_sys_threats.py                 |     2 +
 tests/unit/test_app_sys_trace.py                   |     1 +
 tests/unit/test_arch_ocp.py                        |     3 +
 tests/unit/test_arch_srp.py                        |    49 +-
 tests/unit/test_artifact_smoke_script.py           |    31 +-
 tests/unit/test_bind.py                            |     1 +
 tests/unit/test_branch_stranded_work_analysis.py   |    19 +
 tests/unit/test_callgraph_module_scoped.py         |     1 +
 tests/unit/test_capability_native.py               |     7 +
 tests/unit/test_check.py                           |    81 +-
 tests/unit/test_check_admission.py                 |     6 +
 tests/unit/test_check_budget.py                    |    62 +-
 tests/unit/test_check_gates_summary.py             |   137 +-
 tests/unit/test_check_measurement.py               |    30 +-
 tests/unit/test_check_only_stages.py               |   164 +
 tests/unit/test_check_runner_formatter_t1276.py    |    24 +-
 tests/unit/test_check_scoped_files.py              |   649 +
 tests/unit/test_check_skip_flag.py                 |   193 +
 tests/unit/test_check_stop_before.py               |    33 +-
 tests/unit/test_check_tool_unavailable.py          |    14 +-
 tests/unit/test_ci_self_gate_unscoped.py           |   189 +
 tests/unit/test_claims_and_store_batch6.py         |    76 +-
 tests/unit/test_claude_runner.py                   |    17 +-
 tests/unit/test_clean_worktrees_sweep.py           |   178 +
 tests/unit/test_cli_group_parity.py                |   233 +
 tests/unit/test_cli_lang_choices_drift.py          |   114 +
 tests/unit/test_cli_shims.py                       |   284 +
 tests/unit/test_cli_single_child_groups.py         |   242 +
 tests/unit/test_close_blocked_by_guard.py          |     3 +
 tests/unit/test_close_promote_drafts.py            |    15 +-
 tests/unit/test_close_rel001_bump.py               |     9 +
 tests/unit/test_close_t1648_remainder.py           |     4 +
 tests/unit/test_collect_csharp.py                  |   274 +
 tests/unit/test_collect_python_cache.py            |     9 +-
 tests/unit/test_config.py                          |    17 +
 tests/unit/test_confinement_lattice.py             |     8 +
 tests/unit/test_conftest_midrun_watchdog.py        |     6 +-
 tests/unit/test_conftest_self_scan_fixture.py      |    12 +-
 tests/unit/test_conftest_sigbreak_faulthandler.py  |    22 +-
 tests/unit/test_conftest_stackdump.py              |   152 +-
 tests/unit/test_conftest_suite_result_status.py    |    48 +-
 tests/unit/test_coverage_runner.py                 |     1 +
 tests/unit/test_cross_ticket_leakage_gate.py       |     3 +
 tests/unit/test_cycle_runner_doc_waiver_t2598.py   |     8 +-
 tests/unit/test_cycle_runner_root_resolution.py    |     1 +
 tests/unit/test_cycle_waiver.py                    |     9 +-
 tests/unit/test_daemon_proxy_error_paths_t1457.py  |    79 +-
 tests/unit/test_daemon_proxy_lease_t1276.py        |    23 +-
 tests/unit/test_design_invariants.py               |   142 +-
 tests/unit/test_dev_branch_workflow.py             |    50 +
 tests/unit/test_docs_commands_coverage.py          |   149 +
 tests/unit/test_docs_module.py                     |    59 +-
 .../unit/test_docs_test005_classification_t1418.py |     9 +-
 tests/unit/test_doctor.py                          |   450 +
 tests/unit/test_doctor_runner_t1276.py             |   115 +-
 tests/unit/test_done_report_check_scope.py         |   186 +
 tests/unit/test_dotnet_runner.py                   |   211 +
 tests/unit/test_draft_finalize_attachments.py      |    11 +
 tests/unit/test_dup.py                             |    17 +-
 tests/unit/test_dup_cache.py                       |    16 +-
 tests/unit/test_dup_legacy_cpp.py                  |    41 +-
 tests/unit/test_dup_legacy_py.py                   |    11 +-
 .../test_explore_runner_parse_artifact_cache.py    |    56 +
 tests/unit/test_explore_verb.py                    |   130 +
 tests/unit/test_exports.py                         |     6 +
 tests/unit/test_extending_guides_complete.py       |     4 +
 tests/unit/test_findings_severity_pinned.py        |    15 +-
 tests/unit/test_fix_engine_journal.py              |     1 +
 tests/unit/test_flag_coverage_gate.py              |     1 +
 tests/unit/test_fleet_runner.py                    |     4 +
 tests/unit/test_frob_core_gil.py                   |     6 +-
 tests/unit/test_gate_registry.py                   |   238 +
 .../unit/test_gitattributes_crlf_normalization.py  |    11 +-
 tests/unit/test_gitattributes_merge.py             |    42 +-
 tests/unit/test_gitlog_rendering.py                |     5 +-
 tests/unit/test_graph_build_lock.py                |     3 +
 tests/unit/test_graph_cache.py                     |   190 +-
 tests/unit/test_graph_get_snapshot.py              |    97 +
 tests/unit/test_graph_hierarchy.py                 |    63 +
 tests/unit/test_graph_ingest_batching.py           |    28 +-
 tests/unit/test_graph_lock_holder_naming.py        |     1 +
 tests/unit/test_graph_stat_trust_margin.py         |    17 +-
 tests/unit/test_ids_assigned_once.py               |   116 +
 tests/unit/test_land_already_landed.py             |     7 +-
 tests/unit/test_land_auto_rebase.py                |    35 +
 tests/unit/test_land_cas_ledger_retry.py           |   420 +
 tests/unit/test_land_cmd_backpressure.py           |     4 +
 tests/unit/test_land_cmd_drain_wiring.py           |    64 +
 tests/unit/test_land_cmd_quarantine.py             |    76 +-
 tests/unit/test_land_compose.py                    |    37 +-
 tests/unit/test_land_cross_ticket_leakage.py       |     6 +
 tests/unit/test_land_default_queue.py              |   170 +
 .../test_land_dirty_main_orphaned_ticket_t2026.py  |    21 +-
 tests/unit/test_land_duplicate_ticket_id.py        |     8 +
 tests/unit/test_land_finish_guard.py               |    16 +
 tests/unit/test_land_finish_idempotent.py          |    13 +-
 tests/unit/test_land_format_gate.py                |    32 +
 tests/unit/test_land_in_progress_window.py         |   365 +
 tests/unit/test_land_leaked_tickets_lease_hoist.py |    95 +
 tests/unit/test_land_lock_liveness.py              |    12 +-
 tests/unit/test_land_merge_conflict_drop.py        |   201 +
 tests/unit/test_land_orphaned_evidence.py          |    30 +-
 ...test_land_orphaned_evidence_node_granularity.py |     1 +
 tests/unit/test_land_parity_gate.py                |    61 +
 tests/unit/test_land_phase_elapsed_logging.py      |     3 +
 tests/unit/test_land_queue.py                      |   114 +
 tests/unit/test_land_record_commit.py              |     5 +
 tests/unit/test_land_release_coherence.py          |     2 +
 tests/unit/test_land_release_out_of_tree.py        |     4 +
 tests/unit/test_land_sibling_regression.py         |    57 +-
 tests/unit/test_land_splice_test_then_impl.py      |    23 +-
 tests/unit/test_land_squash_residue_reclaim.py     |    23 +-
 tests/unit/test_land_squash_stage.py               |     3 +
 tests/unit/test_land_stackdump.py                  |   327 +
 tests/unit/test_land_stage_flip.py                 |    25 +-
 tests/unit/test_land_step_ordering.py              |     2 +
 tests/unit/test_land_stranding_t4312.py            |     8 +
 .../test_land_verify_claim_divergence_sentinel.py  |    13 +-
 tests/unit/test_lang_artifact_cache.py             |     2 +
 tests/unit/test_lang_kotlin.py                     |    13 +
 tests/unit/test_lang_parse_guard.py                |    26 +-
 tests/unit/test_lang_project_detect.py             |   115 +
 tests/unit/test_lang_strata.py                     |    26 +-
 tests/unit/test_layering_gate.py                   |   142 +
 tests/unit/test_lease_lifecycle.py                 |   185 +
 tests/unit/test_leases_staleness_perf.py           |   311 +
 tests/unit/test_ledger_store_api.py                |   244 +
 tests/unit/test_lifecycle_work_base.py             |   200 +
 tests/unit/test_logging_module.py                  |    28 +-
 tests/unit/test_logging_quiet.py                   |    11 +-
 tests/unit/test_main_entry.py                      |    57 +-
 tests/unit/test_makefile_coverage.py               |    61 +-
 tests/unit/test_map.py                             |     2 +
 tests/unit/test_memo.py                            |    26 +-
 tests/unit/test_mutation_sweep_queue.py            |     9 +
 tests/unit/test_natives_build.py                   |     1 +
 .../test_new_ticket_over_broad_scope_warning.py    |     4 +
 .../unit/test_new_ticket_scope_breadth_ack_flag.py |     9 +-
 .../unit/test_new_ticket_scope_overlap_warning.py  |    23 +-
 tests/unit/test_outline.py                         |     2 +
 tests/unit/test_parse_runner_direct.py             |     9 +
 tests/unit/test_parser_failure_diagnostics.py      |     2 +
 tests/unit/test_policy_weakening_gate.py           |    29 +-
 tests/unit/test_post_publish_lock_window.py        |   231 +
 tests/unit/test_process.py                         |    35 +-
 tests/unit/test_process_guard.py                   |     5 +
 tests/unit/test_process_lock.py                    |    74 +-
 tests/unit/test_process_pid_liveness.py            |    33 +-
 tests/unit/test_process_reap.py                    |    54 +-
 tests/unit/test_process_tty.py                     |    20 +-
 tests/unit/test_profile.py                         |    16 +
 tests/unit/test_profile_runner.py                  |     5 +
 tests/unit/test_project_tool.py                    |     9 +
 tests/unit/test_pyfmt_runner.py                    |    15 +-
 tests/unit/test_pyproject_data_memoization.py      |   167 +
 tests/unit/test_pytest_spawn.py                    |     6 +
 tests/unit/test_pytest_spawn_env_wiring.py         |     6 +
 tests/unit/test_rapid_debt.py                      |     5 +
 tests/unit/test_rel002_dev_suffix.py               |   114 +
 tests/unit/test_release_stamp_guard.py             |     2 +
 tests/unit/test_release_workflow_gate.py           |    32 +-
 tests/unit/test_reopen_ticket.py                   |     3 +
 tests/unit/test_reporting_t1648_remainder.py       |    10 +
 .../test_reporting_t3285_fenced_subheadings.py     |     5 +
 tests/unit/test_require_python.py                  |     4 +
 tests/unit/test_ruff_reformat_parser.py            |    51 +
 tests/unit/test_run_commands.py                    |   188 +
 tests/unit/test_scaffold_frob_toml.py              |   215 +
 tests/unit/test_scaffold_managed.py                |     9 +
 tests/unit/test_scaffold_natives_shim.py           |     6 +-
 tests/unit/test_scaffold_project.py                |    43 +-
 tests/unit/test_scaffold_unity_project.py          |   138 +
 .../unit/test_scope_closure_declared_scope_only.py |   193 +
 .../test_scope_closure_warning_collapse_t1556.py   |     4 +
 tests/unit/test_skills_sync.py                     |    28 +-
 tests/unit/test_sql_explain_obligation.py          |   158 +
 tests/unit/test_stackdump.py                       |     2 +
 tests/unit/test_store_batch7.py                    |     1 +
 tests/unit/test_store_mode_memoization.py          |   111 +
 tests/unit/test_support_csharp.py                  |   190 +
 tests/unit/test_suppress_worktree_path.py          |    87 +
 .../test_sync_claude_config_stale_guard_t3408.py   |    11 +
 tests/unit/test_t2450_scope_repair.py              |     6 +-
 tests/unit/test_telemetry_verb_recording.py        |   201 +
 tests/unit/test_ticket_2691_doc006.py              |    33 +-
 tests/unit/test_ticket_anchor_cli.py               |     3 +
 tests/unit/test_ticket_cli_surface.py              |   182 +
 tests/unit/test_ticket_close_bug002_t1427.py       |     5 +
 tests/unit/test_ticket_close_bug002_t1438.py       |     1 +
 tests/unit/test_ticket_land_bug003_t2215.py        |     8 +
 tests/unit/test_ticket_list_summary.py             |    15 +-
 tests/unit/test_ticket_new_json.py                 |     2 +
 tests/unit/test_ticket_new_phase_progress.py       |    51 +
 tests/unit/test_ticket_new_readback_guard_t4339.py |    12 +-
 tests/unit/test_ticket_new_related.py              |    12 +-
 tests/unit/test_ticket_new_scope_plausibility.py   |     2 +
 tests/unit/test_ticket_restore.py                  |    32 +-
 tests/unit/test_ticket_runner_bare_root_guard.py   |    12 +-
 .../unit/test_ticket_runner_base_forward_t4105.py  |     9 +-
 tests/unit/test_ticket_runner_designate_repro.py   |    10 +
 tests/unit/test_ticket_runner_gate_findings.py     |   139 +-
 tests/unit/test_ticket_runner_land_cmd_flags.py    |     5 +-
 tests/unit/test_ticket_runner_land_release.py      |    34 +-
 tests/unit/test_ticket_runner_ledger_mirror.py     |   104 +-
 tests/unit/test_ticket_runner_repro_merge_base.py  |     2 +
 tests/unit/test_ticket_runner_venv_sync_t3320.py   |     3 +
 tests/unit/test_ticket_set.py                      |   240 +
 tests/unit/test_ticket_store.py                    |   139 +-
 tests/unit/test_ticket_subverb_tail.py             |   250 +
 tests/unit/test_ticket_verbs_wait.py               |   191 +
 tests/unit/test_tickets_evidence_only_scope.py     |    23 +-
 tests/unit/test_token_usage.py                     |   389 +
 tests/unit/test_tool_absent_parser_reconcile.py    |     9 +
 tests/unit/test_unity_batchmode.py                 |   229 +
 tests/unit/test_unlanded_branch_work.py            |   104 +-
 tests/unit/test_verify_language_buckets.py         |    24 -
 tests/unit/test_verify_release_ci_status.py        |    20 +
 tests/unit/test_version_guard.py                   |     9 +
 tests/unit/test_wait_for_land_slot_unattributed.py |     5 +
 tests/unit/test_waive004_perf_guard.py             |     9 +-
 tests/unit/test_waive_audit_runner.py              |    25 +
 tests/unit/test_waive_audit_watermark.py           |    17 +-
 tests/unit/test_webapp_a11y_forms_contrast.py      |   154 +
 tests/unit/test_webapp_a11y_interaction.py         |   183 +
 tests/unit/test_webapp_a11y_statement.py           |   157 +
 tests/unit/test_webapp_a11y_structure.py           |   196 +
 tests/unit/test_webapp_a11y_substrate.py           |   154 +
 tests/unit/test_webapp_comply_substrate.py         |   119 +
 tests/unit/test_webapp_detect.py                   |    51 +
 tests/unit/test_webapp_seo_substrate.py            |   104 +
 tests/unit/test_webapp_websec_authz_substrate.py   |   144 +
 tests/unit/test_webapp_websec_headers.py           |   118 +
 tests/unit/test_webapp_websec_session_config.py    |   162 +
 tests/unit/test_websec_bounds.py                   |    99 +
 tests/unit/test_websec_deser.py                    |   131 +
 tests/unit/test_websec_headers_log.py              |   203 +
 tests/unit/test_websec_sinks.py                    |    93 +
 tests/unit/test_websec_xss.py                      |    92 +
 tests/unit/test_wire001_atexit_register.py         |     9 +-
 .../unit/test_wire001_callback_keyword_argument.py |    11 +-
 .../unit/test_wire001_fixture_parameter_access.py  |    16 +-
 .../unit/test_wire001_property_attribute_access.py |    13 +-
 .../unit/test_wire001_pydantic_validator_rescue.py |     9 +-
 tests/unit/test_wrapper_drift.py                   |   163 +
 tests/unit/test_xref.py                            |   120 +
 tests/unit/testing/test_stability.py               |     2 +
 tests/unit/tickets/__init__.py                     |     4 +
 tests/unit/tickets/test_start_transition_ledger.py |   149 +
 tests/unit/verify/test_attribution.py              |    21 +-
 tests/unit/verify/test_backpressure.py             |    36 +-
 tests/unit/verify/test_bisect.py                   |     3 +
 tests/unit/verify/test_drain.py                    |    13 +-
 tests/unit/verify/test_quarantine.py               |    90 +-
 tests/unit/verify/test_selection.py                |     7 +
 tests/unit/verify/test_verify_runner.py            |    52 +
 tests/unit/verify/test_worker.py                   |    57 +-
 tests/unit/vet/test_bare_toolchain.py              |     4 +
 tests/unit/vet/test_capability_modes.py            |    20 +-
 tests/unit/vet/test_taint.py                       |     4 +
 tests/vet_suite/test_advisories.py                 |   355 +-
 tests/vet_suite/test_capability_registry_unity.py  |   130 +
 tests/vet_suite/test_capability_scan_csharp.py     |    84 +
 tests/vet_suite/test_capability_scan_dotnet_bcl.py |   119 +
 tests/vet_suite/test_capability_scan_python.py     |     1 +
 tests/vet_suite/test_fingerprint.py                |     1 +
 tests/vet_suite/test_lockfile.py                   |     2 +
 tests/vet_suite/test_opaque_indirection.py         |     1 +
 tests/vet_suite/test_scan_tree.py                  |    21 +-
 tests/vet_suite/test_supply_chain.py               |     1 +
 tickets/T-0969/ticket.md                           |    24 +-
 tickets/T-1273/ticket.md                           |    24 +-
 tickets/T-1382/ticket.md                           |    17 +-
 tickets/T-1597/ticket.md                           |    28 +-
 tickets/T-1598/ticket.md                           |     9 +-
 tickets/T-1607/ticket.md                           |     9 +-
 tickets/T-1608/ticket.md                           |     9 +-
 tickets/T-1609/ticket.md                           |    18 +-
 tickets/T-1661/ticket.md                           |    36 +-
 tickets/T-1686/ticket.md                           |    35 +-
 tickets/T-1778/ticket.md                           |    30 +-
 tickets/T-1820/ticket.md                           |    30 +-
 tickets/T-1831/ticket.md                           |    30 +-
 tickets/T-1953/ticket.md                           |    17 +-
 tickets/T-2202/ticket.md                           |    18 +-
 tickets/T-2371/ticket.md                           |    16 +-
 tickets/T-2377/ticket.md                           |    16 +-
 tickets/T-2451/ticket.md                           |    30 +-
 tickets/T-2676/ticket.md                           |    18 +-
 tickets/T-2752/ticket.md                           |    30 +-
 tickets/T-2799/ticket.md                           |    15 +-
 tickets/T-2802/ticket.md                           |    16 +-
 tickets/T-2803/ticket.md                           |    30 +-
 tickets/T-2819/ticket.md                           |    16 +-
 tickets/T-2835/ticket.md                           |    30 +-
 tickets/T-2837/ticket.md                           |    30 +-
 tickets/T-2856/ticket.md                           |    30 +-
 tickets/T-2886/ticket.md                           |    36 +-
 tickets/T-2889/ticket.md                           |    42 +-
 tickets/T-2894/ticket.md                           |    16 +-
 tickets/T-2939/ticket.md                           |    36 +-
 tickets/T-2962/ticket.md                           |    30 +-
 tickets/T-2963/ticket.md                           |    15 +-
 tickets/T-2964/ticket.md                           |    30 +-
 tickets/T-2982/ticket.md                           |    11 +-
 tickets/T-2987/ticket.md                           |    15 +-
 tickets/T-2994/ticket.md                           |    29 +-
 tickets/T-2998/ticket.md                           |    29 +-
 tickets/T-3002/ticket.md                           |    18 +-
 tickets/T-3004/ticket.md                           |    29 +-
 tickets/T-3008/ticket.md                           |   101 +-
 tickets/T-3010/ticket.md                           |   140 +-
 tickets/T-3020/ticket.md                           |    50 -
 tickets/T-3022/ticket.md                           |    29 +-
 tickets/T-3032/done-report.md                      |  2399 ++
 tickets/T-3032/ticket.md                           |    99 +-
 tickets/T-3047/ticket.md                           |    65 +-
 tickets/T-3048/ticket.md                           |    70 +-
 tickets/T-3049/ticket.md                           |    15 +-
 tickets/T-3053/ticket.md                           |    39 +-
 tickets/T-3063/ticket.md                           |    30 +-
 tickets/T-3067/ticket.md                           |    68 +-
 tickets/T-3068/ticket.md                           |    29 +-
 tickets/T-3073/ticket.md                           |    18 +-
 tickets/T-3076/ticket.md                           |    15 +-
 tickets/T-3082/ticket.md                           |    65 -
 tickets/T-3083/ticket.md                           |    30 +-
 tickets/T-3091/ticket.md                           |    18 +-
 tickets/T-3102/ticket.md                           |    30 +-
 tickets/T-3127/ticket.md                           |    30 +-
 tickets/T-3193/ticket.md                           |    36 +-
 tickets/T-3194/ticket.md                           |    18 +-
 tickets/T-3202/ticket.md                           |    18 +-
 tickets/T-3203/ticket.md                           |    24 +-
 tickets/T-3204/ticket.md                           |    18 +-
 tickets/T-3205/ticket.md                           |    18 +-
 tickets/T-3213/ticket.md                           |    36 +-
 tickets/T-3221/ticket.md                           |    30 +-
 tickets/T-3226/ticket.md                           |    18 +-
 tickets/T-3229/ticket.md                           |    30 +-
 tickets/T-3231/ticket.md                           |    18 +-
 tickets/T-3232/ticket.md                           |    30 -
 tickets/T-3233/ticket.md                           |    29 -
 tickets/T-3234/ticket.md                           |    11 +-
 tickets/T-3239/ticket.md                           |    18 +-
 tickets/T-3241/ticket.md                           |    30 +-
 tickets/T-3248/ticket.md                           |    11 +-
 tickets/T-3262/ticket.md                           |    30 +-
 tickets/T-3267/ticket.md                           |    18 +-
 tickets/T-3269/ticket.md                           |    18 +-
 tickets/T-3270/ticket.md                           |    30 +-
 tickets/T-3274/ticket.md                           |    29 +-
 tickets/T-3278/ticket.md                           |    18 +-
 tickets/T-3282/ticket.md                           |    17 +-
 tickets/T-3284/ticket.md                           |    18 +-
 tickets/T-3299/ticket.md                           |    18 +-
 tickets/T-3300/ticket.md                           |    18 +-
 tickets/T-3304/ticket.md                           |    18 +-
 tickets/T-3306/ticket.md                           |    18 +-
 tickets/T-3307/ticket.md                           |    18 +-
 tickets/T-3309/ticket.md                           |    18 +-
 tickets/T-3310/ticket.md                           |    18 +-
 tickets/T-3312/ticket.md                           |    18 +-
 tickets/T-3313/ticket.md                           |    18 +-
 tickets/T-3317/ticket.md                           |    18 +-
 tickets/T-3318/ticket.md                           |    18 +-
 tickets/T-3319/ticket.md                           |    18 +-
 tickets/T-3321/ticket.md                           |    18 +-
 tickets/T-3323/ticket.md                           |    18 +-
 tickets/T-3327/ticket.md                           |    30 +-
 tickets/T-3329/ticket.md                           |    11 +-
 tickets/T-3330/ticket.md                           |    17 +-
 tickets/T-3331/ticket.md                           |    18 +-
 tickets/T-3332/ticket.md                           |    18 +-
 tickets/T-3333/ticket.md                           |    18 +-
 tickets/T-3334/ticket.md                           |    18 +-
 tickets/T-3335/ticket.md                           |    30 +-
 tickets/T-3337/ticket.md                           |    11 +-
 tickets/T-3338/ticket.md                           |    11 +-
 tickets/T-3340/ticket.md                           |    24 +-
 tickets/T-3343/ticket.md                           |    18 +-
 tickets/T-3351/ticket.md                           |    30 +-
 tickets/T-3352/ticket.md                           |    18 +-
 tickets/T-3355/ticket.md                           |    18 +-
 tickets/T-3357/ticket.md                           |    30 +-
 tickets/T-3359/ticket.md                           |    30 +-
 tickets/T-3377/ticket.md                           |    30 +-
 tickets/T-3381/ticket.md                           |    18 +-
 tickets/T-3405/ticket.md                           |    18 +-
 tickets/T-3415/ticket.md                           |    30 +-
 tickets/T-3418/ticket.md                           |    18 +-
 tickets/T-3459/ticket.md                           |    30 +-
 tickets/T-3503/ticket.md                           |    15 +-
 tickets/T-3504/ticket.md                           |    30 +-
 tickets/T-3505/ticket.md                           |    35 +-
 tickets/T-3513/ticket.md                           |    30 +-
 tickets/T-3542/ticket.md                           |    16 +-
 tickets/T-3559/ticket.md                           |    30 +-
 tickets/T-3564/ticket.md                           |    30 +-
 tickets/T-3573/ticket.md                           |    18 +-
 tickets/T-3602/ticket.md                           |    16 +-
 tickets/T-3611/ticket.md                           |    29 +-
 tickets/T-3612/ticket.md                           |   107 -
 tickets/T-3613/ticket.md                           |    49 -
 tickets/T-3614/done-report.md                      |    72 +
 tickets/T-3614/ticket.md                           |   147 +-
 tickets/T-3620/ticket.md                           |    29 +-
 tickets/T-3639/ticket.md                           |    18 +-
 tickets/T-3646/ticket.md                           |    30 +-
 tickets/T-3659/ticket.md                           |    29 +-
 tickets/T-3660/ticket.md                           |    30 +-
 tickets/T-3663/ticket.md                           |    32 +-
 tickets/T-3677/ticket.md                           |    30 +-
 tickets/T-3703/ticket.md                           |    18 +-
 tickets/T-3710/ticket.md                           |    18 +-
 tickets/T-3714/ticket.md                           |    30 +-
 tickets/T-3716/ticket.md                           |    30 +-
 tickets/T-3717/ticket.md                           |    18 +-
 tickets/T-3718/ticket.md                           |    18 +-
 tickets/T-3719/ticket.md                           |    18 +-
 tickets/T-3723/ticket.md                           |    11 +-
 tickets/T-3728/ticket.md                           |    30 +-
 tickets/T-3729/ticket.md                           |    17 +-
 tickets/T-3739/ticket.md                           |    30 +-
 tickets/T-3758/ticket.md                           |    30 +-
 tickets/T-3775/ticket.md                           |    11 +-
 tickets/T-3783/ticket.md                           |    29 +-
 tickets/T-3789/ticket.md                           |    30 +-
 tickets/T-3800/ticket.md                           |    11 +-
 tickets/T-3803/ticket.md                           |    18 +-
 tickets/T-3804/ticket.md                           |    18 +-
 tickets/T-3805/ticket.md                           |    18 +-
 tickets/T-3806/ticket.md                           |    18 +-
 tickets/T-3807/ticket.md                           |    24 +-
 tickets/T-3808/ticket.md                           |    18 +-
 tickets/T-3809/ticket.md                           |    11 +-
 tickets/T-3811/ticket.md                           |    29 +-
 tickets/T-3812/ticket.md                           |    18 +-
 tickets/T-3813/ticket.md                           |    18 +-
 tickets/T-3814/ticket.md                           |    11 +-
 tickets/T-3815/ticket.md                           |    11 +-
 tickets/T-3816/ticket.md                           |    18 +-
 tickets/T-3817/ticket.md                           |    30 +-
 tickets/T-3821/ticket.md                           |    57 +-
 tickets/T-3822/ticket.md                           |   158 +-
 tickets/T-3823/ticket.md                           |   165 +-
 tickets/T-3824/ticket.md                           |    18 +-
 tickets/T-3825/ticket.md                           |    72 +-
 tickets/T-3826/ticket.md                           |    18 +-
 tickets/T-3827/ticket.md                           |    18 +-
 tickets/T-3828/ticket.md                           |    18 +-
 tickets/T-3829/ticket.md                           |    18 +-
 tickets/T-3830/ticket.md                           |    18 +-
 tickets/T-3831/ticket.md                           |    18 +-
 tickets/T-3832/ticket.md                           |    67 +-
 tickets/T-3833/ticket.md                           |    55 +-
 tickets/T-3834/ticket.md                           |    11 +-
 tickets/T-3835/ticket.md                           |    18 +-
 tickets/T-3836/ticket.md                           |    18 +-
 tickets/T-3838/ticket.md                           |    18 +-
 tickets/T-3839/ticket.md                           |    18 +-
 tickets/T-3840/ticket.md                           |    18 +-
 tickets/T-3841/ticket.md                           |    18 +-
 tickets/T-3842/ticket.md                           |    18 +-
 tickets/T-3849/ticket.md                           |    18 +-
 tickets/T-3850/ticket.md                           |    30 +-
 tickets/T-3851/done-report.md                      |   192 +
 tickets/T-3851/ticket.md                           |    53 +-
 tickets/T-3853/ticket.md                           |    18 +-
 tickets/T-3854/ticket.md                           |    30 +-
 tickets/T-3855/ticket.md                           |    18 +-
 tickets/T-3858/ticket.md                           |    18 +-
 tickets/T-3859/ticket.md                           |    30 +-
 tickets/T-3860/ticket.md                           |    11 +-
 tickets/T-3861/done-report.md                      |    68 +
 tickets/T-3861/ticket.md                           |    53 +-
 tickets/T-3862/ticket.md                           |    11 +-
 tickets/T-3863/ticket.md                           |    11 +-
 tickets/T-3864/ticket.md                           |    11 +-
 tickets/T-3865/done-report.md                      |   157 +
 tickets/T-3865/ticket.md                           |  1067 +-
 tickets/T-3866/ticket.md                           |    11 +-
 tickets/T-3867/ticket.md                           |    30 +-
 tickets/T-3868/ticket.md                           |    11 +-
 tickets/T-3869/ticket.md                           |    11 +-
 tickets/T-3870/ticket.md                           |    11 +-
 tickets/T-3871/ticket.md                           |    11 +-
 tickets/T-3872/ticket.md                           |    11 +-
 tickets/T-3873/ticket.md                           |    18 +-
 tickets/T-3874/ticket.md                           |    11 +-
 tickets/T-3875/ticket.md                           |    11 +-
 tickets/T-3876/ticket.md                           |    11 +-
 tickets/T-3877/ticket.md                           |    11 +-
 tickets/T-3878/ticket.md                           |    11 +-
 tickets/T-3879/ticket.md                           |    18 +-
 tickets/T-3880/ticket.md                           |    11 +-
 tickets/T-3881/ticket.md                           |    11 +-
 tickets/T-3882/ticket.md                           |    30 +-
 tickets/T-3883/ticket.md                           |    17 +-
 tickets/T-3888/ticket.md                           |    18 +-
 tickets/T-3889/ticket.md                           |    11 +-
 tickets/T-3894/ticket.md                           |    18 +-
 tickets/T-3896/ticket.md                           |    17 +-
 tickets/T-3897/ticket.md                           |    18 +-
 tickets/T-3898/ticket.md                           |    18 +-
 tickets/T-3899/done-report.md                      |   238 +
 tickets/T-3899/ticket.md                           |    56 +-
 tickets/T-3902/ticket.md                           |    17 +-
 tickets/T-3904/ticket.md                           |    30 +-
 tickets/T-3911/ticket.md                           |    18 +-
 tickets/T-3915/ticket.md                           |    11 +-
 tickets/T-3916/ticket.md                           |    20 +-
 tickets/T-3917/ticket.md                           |    30 +-
 tickets/T-3918/ticket.md                           |    29 +-
 tickets/T-3919/ticket.md                           |    36 +-
 tickets/T-3920/ticket.md                           |   116 +-
 tickets/T-3921/ticket.md                           |    11 +-
 tickets/T-3923/ticket.md                           |    30 +-
 tickets/T-3924/ticket.md                           |    18 +-
 tickets/T-3926/ticket.md                           |    18 +-
 tickets/T-3927/ticket.md                           |    30 +-
 tickets/T-3928/ticket.md                           |    18 +-
 tickets/T-3929/ticket.md                           |    37 +-
 tickets/T-3932/ticket.md                           |    18 +-
 tickets/T-3933/ticket.md                           |    18 +-
 tickets/T-3936/ticket.md                           |    17 +-
 tickets/T-3938/ticket.md                           |    18 +-
 tickets/T-3939/ticket.md                           |    18 +-
 tickets/T-3942/ticket.md                           |    16 +-
 tickets/T-3944/ticket.md                           |    18 +-
 tickets/T-3945/ticket.md                           |    16 +-
 tickets/T-3946/ticket.md                           |    16 +-
 tickets/T-3949/ticket.md                           |    16 +-
 tickets/T-3950/ticket.md                           |    16 +-
 tickets/T-3951/ticket.md                           |    16 +-
 tickets/T-3952/ticket.md                           |    16 +-
 tickets/T-3953/done-report.md                      |   163 +
 tickets/T-3953/ticket.md                           |    18 +-
 tickets/T-3954/ticket.md                           |    16 +-
 tickets/T-3955/ticket.md                           |    16 +-
 tickets/T-3957/ticket.md                           |    18 +-
 tickets/T-3958/ticket.md                           |    18 +-
 tickets/T-3959/ticket.md                           |    16 +-
 tickets/T-3960/ticket.md                           |    16 +-
 tickets/T-3962/done-report.md                      |   200 +
 tickets/T-3962/ticket.md                           |    32 +-
 tickets/T-3963/ticket.md                           |    16 +-
 tickets/T-3964/done-report.md                      |    34 +
 tickets/T-3964/ticket.md                           |    41 +-
 tickets/T-3965/ticket.md                           |    16 +-
 tickets/T-3966/ticket.md                           |    16 +-
 tickets/T-3967/ticket.md                           |    16 +-
 tickets/T-3968/ticket.md                           |    16 +-
 tickets/T-3969/ticket.md                           |    16 +-
 tickets/T-3970/ticket.md                           |    16 +-
 tickets/T-3971/ticket.md                           |    16 +-
 tickets/T-3972/ticket.md                           |    16 +-
 tickets/T-3973/ticket.md                           |    22 +-
 tickets/T-3974/ticket.md                           |    22 +-
 tickets/T-3975/ticket.md                           |    16 +-
 tickets/T-3976/ticket.md                           |    18 +-
 tickets/T-3977/ticket.md                           |    16 +-
 tickets/T-3978/ticket.md                           |    21 +-
 tickets/T-3981/ticket.md                           |    18 +-
 tickets/T-3982/ticket.md                           |    18 +-
 tickets/T-3983/ticket.md                           |    23 +-
 tickets/T-3984/ticket.md                           |     9 +-
 tickets/T-3986/done-report.md                      |    21 +
 tickets/T-3986/ticket.md                           |    19 +-
 tickets/T-3987/ticket.md                           |    16 +-
 tickets/T-3988/ticket.md                           |    16 +-
 tickets/T-3989/ticket.md                           |    16 +-
 tickets/T-3990/ticket.md                           |    16 +-
 tickets/T-3991/ticket.md                           |    16 +-
 tickets/T-3992/ticket.md                           |    16 +-
 tickets/T-3993/done-report.md                      |    60 +
 tickets/T-3993/ticket.md                           |    34 +-
 tickets/T-3994/ticket.md                           |    16 +-
 tickets/T-3995/done-report.md                      |    19 +
 tickets/T-3995/ticket.md                           |    33 +-
 tickets/T-3996/ticket.md                           |    16 +-
 tickets/T-3997/done-report.md                      |   188 +
 tickets/T-3997/ticket.md                           |    31 +-
 tickets/T-3998/ticket.md                           |    17 +-
 tickets/T-3999/ticket.md                           |    18 +-
 tickets/T-4001/ticket.md                           |    11 +-
 tickets/T-4002/ticket.md                           |    21 +-
 tickets/T-4003/ticket.md                           |    16 +-
 tickets/T-4004/ticket.md                           |    21 +-
 tickets/T-4005/ticket.md                           |    16 +-
 tickets/T-4006/ticket.md                           |    22 +-
 tickets/T-4007/ticket.md                           |    16 +-
 tickets/T-4008/ticket.md                           |    16 +-
 tickets/T-4009/ticket.md                           |    18 +-
 tickets/T-4010/ticket.md                           |    30 +-
 tickets/T-4011/ticket.md                           |    29 +-
 tickets/T-4012/ticket.md                           |    18 +-
 tickets/T-4014/ticket.md                           |    18 +-
 tickets/T-4015/ticket.md                           |    18 +-
 tickets/T-4016/ticket.md                           |    18 +-
 tickets/T-4017/ticket.md                           |    18 +-
 tickets/T-4020/ticket.md                           |    18 +-
 tickets/T-4021/ticket.md                           |    18 +-
 tickets/T-4022/ticket.md                           |    17 +-
 tickets/T-4025/ticket.md                           |    30 +-
 tickets/T-4029/ticket.md                           |    29 +-
 tickets/T-4030/done-report.md                      |   112 +
 tickets/T-4030/ticket.md                           |    14 +-
 tickets/T-4031/ticket.md                           |    23 +-
 tickets/T-4032/ticket.md                           |    21 +-
 tickets/T-4033/ticket.md                           |    22 +-
 tickets/T-4034/ticket.md                           |    22 +-
 tickets/T-4035/ticket.md                           |    24 +-
 tickets/T-4036/ticket.md                           |    30 +-
 tickets/T-4038/ticket.md                           |    22 +-
 tickets/T-4039/ticket.md                           |    22 +-
 tickets/T-4040/ticket.md                           |    17 +-
 tickets/T-4042/ticket.md                           |    17 +-
 tickets/T-4043/ticket.md                           |    17 +-
 tickets/T-4044/ticket.md                           |    23 +-
 tickets/T-4045/ticket.md                           |    23 +-
 tickets/T-4048/ticket.md                           |    23 +-
 tickets/T-4049/ticket.md                           |    21 +-
 tickets/T-4050/ticket.md                           |    36 +-
 tickets/T-4051/ticket.md                           |    23 +-
 tickets/T-4052/ticket.md                           |    18 +-
 tickets/T-4053/ticket.md                           |    23 +-
 tickets/T-4054/ticket.md                           |    23 +-
 tickets/T-4058/ticket.md                           |    16 +-
 tickets/T-4059/ticket.md                           |    16 +-
 tickets/T-4061/ticket.md                           |    16 +-
 tickets/T-4062/ticket.md                           |    16 +-
 tickets/T-4063/ticket.md                           |    16 +-
 tickets/T-4064/ticket.md                           |    16 +-
 tickets/T-4066/ticket.md                           |    16 +-
 tickets/T-4067/ticket.md                           |    16 +-
 tickets/T-4068/ticket.md                           |    16 +-
 tickets/T-4069/ticket.md                           |    16 +-
 tickets/T-4070/ticket.md                           |    16 +-
 tickets/T-4071/ticket.md                           |    24 +-
 tickets/T-4072/ticket.md                           |    22 +-
 tickets/T-4073/done-report.md                      |    28 +
 tickets/T-4073/ticket.md                           |    56 +-
 tickets/T-4074/ticket.md                           |    22 +-
 tickets/T-4075/ticket.md                           |    22 +-
 tickets/T-4076/ticket.md                           |    18 +-
 tickets/T-4077/ticket.md                           |    22 +-
 tickets/T-4078/ticket.md                           |    22 +-
 tickets/T-4079/ticket.md                           |    22 +-
 tickets/T-4080/ticket.md                           |    22 +-
 tickets/T-4081/ticket.md                           |    22 +-
 tickets/T-4082/ticket.md                           |    16 +-
 tickets/T-4083/ticket.md                           |    16 +-
 tickets/T-4084/ticket.md                           |    30 +-
 tickets/T-4086/ticket.md                           |    16 +-
 tickets/T-4087/ticket.md                           |    16 +-
 tickets/T-4089/ticket.md                           |    30 +-
 tickets/T-4090/ticket.md                           |    22 +-
 tickets/T-4091/ticket.md                           |    22 +-
 tickets/T-4092/ticket.md                           |    22 +-
 tickets/T-4093/ticket.md                           |    22 +-
 tickets/T-4094/ticket.md                           |    22 +-
 tickets/T-4095/ticket.md                           |    22 +-
 tickets/T-4096/ticket.md                           |    22 +-
 tickets/T-4097/ticket.md                           |    16 +-
 tickets/T-4098/ticket.md                           |    16 +-
 tickets/T-4099/ticket.md                           |    16 +-
 tickets/T-4100/ticket.md                           |    16 +-
 tickets/T-4101/ticket.md                           |    16 +-
 tickets/T-4109/ticket.md                           |    30 +-
 tickets/T-4112/done-report.md                      |  2368 ++
 tickets/T-4112/ticket.md                           |    74 +-
 tickets/T-4113/done-report.md                      |  2377 ++
 tickets/T-4113/ticket.md                           |    73 +-
 tickets/T-4114/done-report.md                      |   138 +
 tickets/T-4114/ticket.md                           |    42 +-
 tickets/T-4115/done-report.md                      |   140 +
 tickets/T-4115/ticket.md                           |    41 +-
 tickets/T-4117/ticket.md                           |    23 +-
 tickets/T-4119/ticket.md                           |    16 +-
 tickets/T-4120/ticket.md                           |    16 +-
 tickets/T-4123/ticket.md                           |    16 +-
 tickets/T-4124/ticket.md                           |    16 +-
 tickets/T-4126/ticket.md                           |    16 +-
 tickets/T-4127/ticket.md                           |    76 +-
 tickets/T-4128/ticket.md                           |    16 +-
 tickets/T-4129/ticket.md                           |    16 +-
 tickets/T-4133/ticket.md                           |    16 +-
 tickets/T-4134/ticket.md                           |    16 +-
 tickets/T-4135/ticket.md                           |    30 +-
 tickets/T-4140/ticket.md                           |    16 +-
 tickets/T-4141/ticket.md                           |    16 +-
 tickets/T-4144/ticket.md                           |    16 +-
 tickets/T-4149/ticket.md                           |    16 +-
 tickets/T-4151/ticket.md                           |    16 +-
 tickets/T-4152/ticket.md                           |    16 +-
 tickets/T-4156/ticket.md                           |    16 +-
 tickets/T-4157/ticket.md                           |    30 +-
 tickets/T-4158/ticket.md                           |    16 +-
 tickets/T-4160/ticket.md                           |    16 +-
 tickets/T-4161/ticket.md                           |    16 +-
 tickets/T-4162/ticket.md                           |    16 +-
 tickets/T-4164/ticket.md                           |    16 +-
 tickets/T-4165/ticket.md                           |    16 +-
 tickets/T-4166/ticket.md                           |    30 +-
 tickets/T-4168/ticket.md                           |    16 +-
 tickets/T-4169/ticket.md                           |    16 +-
 tickets/T-4174/ticket.md                           |    16 +-
 tickets/T-4175/ticket.md                           |    30 +-
 tickets/T-4176/ticket.md                           |    15 +-
 tickets/T-4180/ticket.md                           |    16 +-
 tickets/T-4181/ticket.md                           |    16 +-
 tickets/T-4182/ticket.md                           |    30 +-
 tickets/T-4187/ticket.md                           |    22 +-
 tickets/T-4188/ticket.md                           |    22 +-
 tickets/T-4189/ticket.md                           |    22 +-
 tickets/T-4190/ticket.md                           |    22 +-
 tickets/T-4192/ticket.md                           |    22 +-
 tickets/T-4193/ticket.md                           |    22 +-
 tickets/T-4194/ticket.md                           |    22 +-
 tickets/T-4196/ticket.md                           |    16 +-
 tickets/T-4198/ticket.md                           |    22 +-
 tickets/T-4199/ticket.md                           |    16 +-
 tickets/T-4200/ticket.md                           |    22 +-
 tickets/T-4202/ticket.md                           |    22 +-
 tickets/T-4203/ticket.md                           |    22 +-
 tickets/T-4204/ticket.md                           |    22 +-
 tickets/T-4205/ticket.md                           |    16 +-
 tickets/T-4206/ticket.md                           |    22 +-
 tickets/T-4209/ticket.md                           |    22 +-
 tickets/T-4211/ticket.md                           |    22 +-
 tickets/T-4213/ticket.md                           |    16 +-
 tickets/T-4214/ticket.md                           |    37 -
 tickets/T-4215/ticket.md                           |    22 +-
 tickets/T-4216/ticket.md                           |    22 +-
 tickets/T-4217/ticket.md                           |    22 +-
 tickets/T-4218/ticket.md                           |    22 +-
 tickets/T-4220/ticket.md                           |    22 +-
 tickets/T-4221/ticket.md                           |    30 -
 tickets/T-4222/ticket.md                           |    22 +-
 tickets/T-4223/ticket.md                           |    22 +-
 tickets/T-4224/ticket.md                           |    22 +-
 tickets/T-4225/ticket.md                           |    22 +-
 tickets/T-4226/ticket.md                           |    22 +-
 tickets/T-4227/ticket.md                           |    22 +-
 tickets/T-4228/ticket.md                           |    22 +-
 tickets/T-4229/ticket.md                           |    22 +-
 tickets/T-4231/ticket.md                           |    22 +-
 tickets/T-4232/ticket.md                           |    22 +-
 tickets/T-4233/ticket.md                           |    22 +-
 tickets/T-4235/ticket.md                           |    22 +-
 tickets/T-4237/ticket.md                           |    22 +-
 tickets/T-4238/ticket.md                           |    22 +-
 tickets/T-4239/ticket.md                           |    22 +-
 tickets/T-4242/ticket.md                           |    22 +-
 tickets/T-4245/ticket.md                           |    22 +-
 tickets/T-4247/ticket.md                           |    22 +-
 tickets/T-4248/ticket.md                           |    22 +-
 tickets/T-4249/ticket.md                           |    22 +-
 tickets/T-4250/ticket.md                           |    22 +-
 tickets/T-4252/ticket.md                           |    22 +-
 tickets/T-4253/ticket.md                           |    22 +-
 tickets/T-4254/done-report.md                      |   139 +
 tickets/T-4254/ticket.md                           |    21 +-
 tickets/T-4259/ticket.md                           |    16 +-
 tickets/T-4261/ticket.md                           |    16 +-
 tickets/T-4268/ticket.md                           |    16 +-
 tickets/T-4272/ticket.md                           |    16 +-
 tickets/T-4283/ticket.md                           |    16 +-
 tickets/T-4296/ticket.md                           |    16 +-
 tickets/T-4300/ticket.md                           |    16 +-
 tickets/T-4311/ticket.md                           |    16 +-
 tickets/T-4330/ticket.md                           |    16 +-
 tickets/T-4332/ticket.md                           |    16 +-
 tickets/T-4357/ticket.md                           |    16 +-
 tickets/T-4363/ticket.md                           |    15 +-
 tickets/T-4364/ticket.md                           |    16 +-
 tickets/T-4370/ticket.md                           |    16 +-
 tickets/T-4371/ticket.md                           |    16 +-
 tickets/T-4383/ticket.md                           |    16 +-
 tickets/T-4385/ticket.md                           |    16 +-
 tickets/T-4389/ticket.md                           |    16 +-
 tickets/T-4400/ticket.md                           |    16 +-
 tickets/T-4410/ticket.md                           |    30 +-
 tickets/T-4413/ticket.md                           |    43 -
 tickets/T-4416/ticket.md                           |    46 -
 tickets/T-4418/ticket.md                           |    24 +-
 tickets/T-4419/ticket.md                           |    31 -
 tickets/T-4420/done-report.md                      |  2260 ++
 tickets/T-4420/ticket.md                           |   394 +-
 tickets/T-4421/ticket.md                           |    31 -
 tickets/T-4422/ticket.md                           |    24 +-
 tickets/T-4423/ticket.md                           |    24 +-
 tickets/T-4437/done-report.md                      |    78 +
 tickets/T-4437/ticket.md                           |    80 +-
 tickets/T-4466/ticket.md                           |    16 +-
 tickets/T-4484/ticket.md                           |    16 +-
 tickets/T-4497/ticket.md                           |    45 +
 tickets/T-4500/ticket.md                           |    55 +
 tickets/T-4504/ticket.md                           |    83 +
 tickets/T-4506/done-report.md                      |  3392 +++
 tickets/T-4506/ticket.md                           |    70 +
 tickets/T-4509/done-report.md                      |  2819 +++
 tickets/T-4509/ticket.md                           |    62 +
 tickets/T-4513/ticket.md                           |    49 +
 tickets/T-4516/done-report.md                      |  3744 +++
 tickets/T-4516/ticket.md                           |    61 +
 tickets/T-4518/done-report.md                      |  3294 +++
 tickets/T-4518/ticket.md                           |    65 +
 tickets/T-4530/ticket.md                           |    78 +
 tickets/T-4533/ticket.md                           |    49 +
 tickets/T-4541/ticket.md                           |   126 +
 tickets/T-4558/ticket.md                           |    44 +
 tickets/T-4560/done-report.md                      |  2834 +++
 tickets/T-4560/ticket.md                           |    68 +
 tickets/T-4561/done-report.md                      |  3417 +++
 tickets/T-4561/ticket.md                           |    99 +
 tickets/T-4567/ticket.md                           |    41 +
 tickets/T-4571/ticket.md                           |    57 +
 tickets/T-4573/ticket.md                           |    41 +
 tickets/T-4574/ticket.md                           |    43 +
 tickets/T-4575/ticket.md                           |    51 +
 tickets/T-4578/done-report.md                      |  2371 ++
 tickets/T-4578/ticket.md                           |    58 +
 tickets/T-4580/ticket.md                           |    60 +
 tickets/T-4581/done-report.md                      |  2833 +++
 tickets/T-4581/ticket.md                           |    70 +
 tickets/T-4598/ticket.md                           |    53 +
 tickets/T-4599/done-report.md                      |  2808 +++
 tickets/T-4599/ticket.md                           |    73 +
 tickets/T-4600/ticket.md                           |    42 +
 tickets/T-4601/ticket.md                           |    41 +
 tickets/T-4603/ticket.md                           |    44 +
 tickets/T-4605/ticket.md                           |    96 +
 tickets/T-4606/ticket.md                           |    41 +
 tickets/T-4608/ticket.md                           |    55 +
 tickets/T-4609/ticket.md                           |    41 +
 tickets/T-4610/ticket.md                           |    42 +
 tickets/T-4611/done-report.md                      |  2840 +++
 tickets/T-4611/ticket.md                           |    64 +
 tickets/T-4612/done-report.md                      |  2463 ++
 tickets/T-4612/ticket.md                           |   129 +
 tickets/T-4617/ticket.md                           |    41 +
 tickets/T-4626/done-report.md                      |    47 +
 tickets/T-4626/ticket.md                           |    70 +
 tickets/T-4640/ticket.md                           |    44 +
 tickets/T-4641/done-report.md                      |    83 +
 tickets/T-4641/ticket.md                           |    46 +
 tickets/T-4643/ticket.md                           |    43 +
 tickets/T-4644/ticket.md                           |    43 +
 tickets/T-4645/done-report.md                      |  3710 +++
 tickets/T-4645/ticket.md                           |   699 +
 tickets/T-4647/ticket.md                           |    56 +
 tickets/T-4648/ticket.md                           |    42 +
 tickets/T-4651/ticket.md                           |    68 +
 tickets/T-4652/ticket.md                           |    53 +
 tickets/T-4653/ticket.md                           |    51 +
 tickets/T-4654/ticket.md                           |    55 +
 tickets/T-4655/ticket.md                           |    50 +
 tickets/T-4656/ticket.md                           |    54 +
 tickets/T-4657/done-report.md                      |   162 +
 tickets/T-4657/ticket.md                           |    90 +
 tickets/T-4658/done-report.md                      |   147 +
 tickets/T-4658/ticket.md                           |    73 +
 tickets/T-4661/done-report.md                      |   171 +
 tickets/T-4661/ticket.md                           |    86 +
 tickets/T-4662/ticket.md                           |   105 +
 tickets/T-4663/done-report.md                      |  2964 +++
 tickets/T-4663/ticket.md                           |   116 +
 tickets/T-4664/ticket.md                           |    82 +
 tickets/T-4665/ticket.md                           |    83 +
 tickets/T-4666/ticket.md                           |    86 +
 tickets/T-4667/ticket.md                           |    77 +
 tickets/T-4668/ticket.md                           |   153 +
 tickets/T-4670/ticket.md                           |    93 +
 tickets/T-4671/ticket.md                           |   119 +
 tickets/T-4672/ticket.md                           |   153 +
 tickets/T-4674/ticket.md                           |   104 +
 tickets/T-4676/done-report.md                      |  2225 ++
 tickets/T-4676/ticket.md                           |   119 +
 tickets/T-4679/ticket.md                           |    43 +
 tickets/T-4681/ticket.md                           |   240 +
 tickets/T-4685/ticket.md                           |    66 +
 tickets/T-4686/ticket.md                           |    47 +
 tickets/T-4687/ticket.md                           |   261 +
 tickets/T-4690/done-report.md                      |  2919 +++
 tickets/T-4690/ticket.md                           |   457 +
 tickets/T-4691/ticket.md                           |   150 +
 tickets/T-4692/done-report.md                      |  2993 +++
 tickets/T-4692/ticket.md                           |   350 +
 tickets/T-4693/done-report.md                      |  1328 ++
 tickets/T-4693/ticket.md                           |   162 +
 tickets/T-4694/done-report.md                      |  3286 +++
 tickets/T-4694/ticket.md                           |   167 +
 tickets/T-4695/done-report.md                      |  3013 +++
 tickets/T-4695/ticket.md                           |   241 +
 tickets/T-4696/done-report.md                      |  2996 +++
 tickets/T-4696/ticket.md                           |   273 +
 tickets/T-4697/done-report.md                      |   154 +
 tickets/T-4697/ticket.md                           |   130 +
 tickets/T-4698/done-report.md                      |  3003 +++
 tickets/T-4698/ticket.md                           |   319 +
 tickets/T-4702/done-report.md                      |  3386 +++
 tickets/T-4702/ticket.md                           |   532 +
 tickets/T-4703/ticket.md                           |   129 +
 tickets/T-4710/done-report.md                      |  2847 +++
 tickets/T-4710/ticket.md                           |   131 +
 tickets/T-4711/done-report.md                      |  2943 +++
 tickets/T-4711/ticket.md                           |    98 +
 tickets/T-4712/done-report.md                      |  2950 +++
 tickets/T-4712/ticket.md                           |    92 +
 tickets/T-4713/done-report.md                      |  2982 +++
 tickets/T-4713/ticket.md                           |   109 +
 tickets/T-4714/done-report.md                      |  3021 +++
 tickets/T-4714/ticket.md                           |   130 +
 tickets/T-4716/ticket.md                           |    54 +
 tickets/T-4717/ticket.md                           |    92 +
 tickets/T-4720/ticket.md                           |    43 +
 tickets/T-4721/ticket.md                           |    43 +
 tickets/T-4724/ticket.md                           |    49 +
 tickets/T-4735/ticket.md                           |    69 +
 tickets/T-4736/ticket.md                           |    70 +
 tickets/T-4737/ticket.md                           |   120 +
 tickets/T-4738/ticket.md                           |    69 +
 tickets/T-4739/ticket.md                           |    65 +
 tickets/T-4740/ticket.md                           |    67 +
 tickets/T-4741/ticket.md                           |   188 +
 tickets/T-4742/ticket.md                           |    72 +
 tickets/T-4743/ticket.md                           |    87 +
 tickets/T-4757/ticket.md                           |   100 +
 tickets/T-4758/done-report.md                      |  3859 ++++
 tickets/T-4758/ticket.md                           |   140 +
 tickets/T-4759/done-report.md                      |  1162 +
 tickets/T-4759/ticket.md                           |   126 +
 tickets/T-4760/done-report.md                      |  2631 +++
 tickets/T-4760/ticket.md                           |   136 +
 tickets/T-4761/done-report.md                      |   212 +
 tickets/T-4761/ticket.md                           |   147 +
 tickets/T-4762/ticket.md                           |    82 +
 tickets/T-4763/done-report.md                      |    14 +
 tickets/T-4763/ticket.md                           |    89 +
 tickets/T-4765/ticket.md                           |   121 +
 tickets/T-4766/ticket.md                           |    97 +
 tickets/T-4768/ticket.md                           |    97 +
 tickets/T-4769/ticket.md                           |    87 +
 tickets/T-4771/ticket.md                           |    90 +
 tickets/T-4772/ticket.md                           |   104 +
 tickets/T-4773/ticket.md                           |   122 +
 tickets/T-4774/ticket.md                           |    95 +
 tickets/T-4804/ticket.md                           |   194 +
 tickets/T-4807/ticket.md                           |   122 +
 tickets/T-4808/ticket.md                           |   156 +
 tickets/T-4809/ticket.md                           |    95 +
 tickets/T-4810/ticket.md                           |   106 +
 tickets/T-4811/ticket.md                           |    45 +
 tickets/T-4848/ticket.md                           |    98 +
 tickets/T-4853/ticket.md                           |   110 +
 tickets/T-4855/ticket.md                           |    98 +
 tickets/T-4856/ticket.md                           |   111 +
 tickets/T-4857/ticket.md                           |    98 +
 tickets/T-4863/ticket.md                           |    98 +
 tickets/T-4869/ticket.md                           |    98 +
 tickets/T-4870/ticket.md                           |    98 +
 tickets/T-4871/ticket.md                           |    99 +
 tickets/T-4874/ticket.md                           |    98 +
 tickets/T-4910/ticket.md                           |    45 +
 tickets/T-4912/done-report.md                      |  2460 ++
 tickets/T-4912/ticket.md                           |    53 +
 tickets/T-4950/ticket.md                           |    48 +
 tickets/T-4951/done-report.md                      |   248 +
 tickets/T-4951/ticket.md                           |   144 +
 tickets/T-4989/ticket.md                           |    44 +
 tickets/T-4990/ticket.md                           |    48 +
 tickets/T-4991/done-report.md                      |    73 +
 tickets/T-4991/ticket.md                           |    50 +
 tickets/T-4992/ticket.md                           |    51 +
 tickets/T-4993/done-report.md                      |   127 +
 tickets/T-4993/ticket.md                           |   126 +
 tickets/T-4994/ticket.md                           |   100 +
 tickets/T-4995/ticket.md                           |    98 +
 tickets/T-4996/ticket.md                           |    97 +
 tickets/T-4997/ticket.md                           |    93 +
 tickets/T-5033/ticket.md                           |    82 +
 tickets/T-5034/done-report.md                      |  3014 +++
 tickets/T-5034/ticket.md                           |    54 +
 tickets/T-5035/done-report.md                      |  2816 +++
 tickets/T-5035/ticket.md                           |    69 +
 tickets/T-5037/ticket.md                           |    82 +
 tickets/T-5074/ticket.md                           |    82 +
 tickets/T-5076/ticket.md                           |    82 +
 tickets/T-5077/ticket.md                           |    83 +
 tickets/T-5078/ticket.md                           |    82 +
 tickets/T-5079/ticket.md                           |    82 +
 tickets/T-5080/ticket.md                           |    83 +
 tickets/T-5081/ticket.md                           |   132 +
 tickets/T-5084/done-report.md                      |    61 +
 tickets/T-5084/ticket.md                           |    72 +
 tickets/T-5085/ticket.md                           |   106 +
 tickets/T-5086/ticket.md                           |   106 +
 tickets/T-5087/ticket.md                           |   130 +
 tickets/T-5088/ticket.md                           |    43 +
 tickets/T-5089/ticket.md                           |    51 +
 tickets/T-5090/ticket.md                           |    45 +
 tickets/T-5091/ticket.md                           |   106 +
 tickets/T-5092/ticket.md                           |    70 +
 tickets/T-5093/ticket.md                           |   106 +
 tickets/T-5094/ticket.md                           |   114 +
 tickets/T-5095/ticket.md                           |    53 +
 tickets/T-5096/ticket.md                           |    49 +
 tickets/T-5097/ticket.md                           |   113 +
 tickets/T-5098/ticket.md                           |    59 +
 tickets/T-5099/ticket.md                           |    59 +
 tickets/T-5100/ticket.md                           |    52 +
 tickets/T-5101/ticket.md                           |    52 +
 tickets/T-5102/ticket.md                           |    81 +
 tickets/T-5103/ticket.md                           |   127 +
 tickets/T-5104/ticket.md                           |    68 +
 tickets/T-5105/done-report.md                      |  2842 +++
 tickets/T-5105/ticket.md                           |    96 +
 tickets/T-5106/ticket.md                           |   384 +
 tickets/T-5107/ticket.md                           |    51 +
 tickets/T-5108/done-report.md                      |  3761 +++
 tickets/T-5108/ticket.md                           |    76 +
 tickets/T-5109/ticket.md                           |   106 +
 tickets/T-5110/ticket.md                           |   106 +
 tickets/T-5111/ticket.md                           |   106 +
 tickets/T-5112/ticket.md                           |   107 +
 tickets/T-5113/ticket.md                           |    57 +
 tickets/T-5114/ticket.md                           |    75 +
 tickets/T-5115/ticket.md                           |   113 +
 tickets/T-5116/ticket.md                           |    80 +
 tickets/T-5117/done-report.md                      |    83 +
 tickets/T-5117/ticket.md                           |    67 +
 tickets/T-5120/done-report.md                      |    43 +
 tickets/T-5120/ticket.md                           |    49 +
 tickets/T-5121/done-report.md                      |  2812 +++
 tickets/T-5121/ticket.md                           |    68 +
 tickets/T-5122/done-report.md                      |    72 +
 tickets/T-5122/ticket.md                           |    82 +
 tickets/T-5123/done-report.md                      |    71 +
 tickets/T-5123/ticket.md                           |    59 +
 tickets/T-5124/done-report.md                      |  2813 +++
 tickets/T-5124/ticket.md                           |    89 +
 tickets/T-5125/done-report.md                      |  2432 ++
 tickets/T-5125/ticket.md                           |    83 +
 tickets/T-5126/done-report.md                      |  1239 +
 tickets/T-5126/ticket.md                           |    82 +
 tickets/T-5127/ticket.md                           |    49 +
 tickets/T-5128/ticket.md                           |    50 +
 tickets/T-5129/ticket.md                           |    47 +
 tickets/T-5131/done-report.md                      |    97 +
 tickets/T-5131/ticket.md                           |    89 +
 tickets/T-5132/done-report.md                      |  3003 +++
 tickets/T-5132/ticket.md                           |   198 +
 tickets/T-5133/done-report.md                      |  3044 +++
 tickets/T-5133/ticket.md                           |   157 +
 tickets/T-5134/done-report.md                      |  3789 ++++
 tickets/T-5134/ticket.md                           |   295 +
 tickets/T-5135/done-report.md                      |  2846 +++
 tickets/T-5135/ticket.md                           |   598 +
 tickets/T-5136/done-report.md                      |  2963 +++
 tickets/T-5136/ticket.md                           |   117 +
 tickets/T-5137/done-report.md                      |  3778 ++++
 tickets/T-5137/ticket.md                           |   146 +
 tickets/T-5138/done-report.md                      |  2913 +++
 tickets/T-5138/ticket.md                           |    85 +
 tickets/T-5139/done-report.md                      |  2938 +++
 tickets/T-5139/ticket.md                           |   129 +
 tickets/T-5140/ticket.md                           |   777 +
 tickets/T-5141/ticket.md                           |   248 +
 tickets/T-5142/ticket.md                           |   289 +
 tickets/T-5143/ticket.md                           |   323 +
 tickets/T-5144/ticket.md                           |   287 +
 tickets/T-5145/ticket.md                           |   284 +
 tickets/T-5146/ticket.md                           |   363 +
 tickets/T-5147/ticket.md                           |   313 +
 tickets/T-5148/ticket.md                           |   253 +
 tickets/T-5149/ticket.md                           |    42 +
 tickets/T-5151/done-report.md                      |  3422 +++
 tickets/T-5151/ticket.md                           |   136 +
 tickets/T-5152/ticket.md                           |    31 +
 tickets/T-5153/ticket.md                           |    31 +
 tickets/T-5154/ticket.md                           |    30 +
 tickets/T-5155/ticket.md                           |    30 +
 tickets/T-5156/ticket.md                           |    33 +
 tickets/T-5157/ticket.md                           |    29 +
 tickets/T-5158/ticket.md                           |   155 +
 tickets/T-5159/ticket.md                           |  1711 ++
 tickets/T-5160/ticket.md                           |    30 +
 tickets/T-5161/ticket.md                           |    31 +
 tickets/T-5162/ticket.md                           |    31 +
 tickets/T-5163/ticket.md                           |  4299 ++++
 tickets/T-5165/ticket.md                           |   275 +
 tickets/T-5166/done-report.md                      |  2853 +++
 tickets/T-5166/ticket.md                           |    39 +
 tickets/T-5168/ticket.md                           |    94 +
 tickets/T-5171/ticket.md                           |    50 +
 tickets/T-5172/ticket.md                           |    52 +
 tickets/T-5173/ticket.md                           |    52 +
 tickets/T-5174/ticket.md                           |    52 +
 tickets/T-5175/ticket.md                           |    52 +
 tickets/T-5176/ticket.md                           |    30 +
 tickets/T-5177/ticket.md                           |    29 +
 tickets/T-5178/ticket.md                           |    55 +
 tickets/T-5179/ticket.md                           |    47 +
 tickets/T-5180/ticket.md                           |    50 +
 tickets/T-5181/ticket.md                           |    45 +
 tickets/T-5182/ticket.md                           |    44 +
 tickets/T-5190/done-report.md                      |  3784 ++++
 tickets/T-5190/ticket.md                           |   143 +
 tickets/T-5192/ticket.md                           |    38 +
 tickets/T-5198/ticket.md                           |    31 +
 tickets/T-5199/done-report.md                      |  2922 +++
 tickets/T-5199/ticket.md                           |    46 +
 tickets/T-5201/done-report.md                      |  3005 +++
 tickets/T-5201/ticket.md                           |    55 +
 tickets/T-5202/ticket.md                           |    34 +
 tickets/T-5203/ticket.md                           |    33 +
 tickets/T-5204/done-report.md                      |  3278 +++
 tickets/T-5204/ticket.md                           |    60 +
 tickets/T-5205/ticket.md                           |    44 +
 tickets/T-5212/done-report.md                      |  2949 +++
 tickets/T-5212/ticket.md                           |    42 +
 tickets/T-5213/ticket.md                           |    48 +
 tickets/T-5214/ticket.md                           |    46 +
 tickets/T-5215/done-report.md                      |  3017 +++
 tickets/T-5215/ticket.md                           |   103 +
 tickets/T-5217/done-report.md                      |  2883 +++
 tickets/T-5217/ticket.md                           |    35 +
 tickets/T-5219/done-report.md                      |  2885 +++
 tickets/T-5219/ticket.md                           |    37 +
 tickets/T-5222/done-report.md                      |  2880 +++
 tickets/T-5222/ticket.md                           |    35 +
 tickets/T-5228/done-report.md                      |  2883 +++
 tickets/T-5228/ticket.md                           |    48 +
 tickets/T-5229/ticket.md                           |    46 +
 tickets/T-5231/ticket.md                           |    63 +
 tickets/T-5238/ticket.md                           |    41 +
 tickets/T-5240/done-report.md                      |  2893 +++
 tickets/T-5240/ticket.md                           |    35 +
 tickets/T-5242/done-report.md                      |  2869 +++
 tickets/T-5242/ticket.md                           |    43 +
 tickets/T-5245/done-report.md                      |  2860 +++
 tickets/T-5245/ticket.md                           |    36 +
 tickets/T-5247/done-report.md                      |  2875 +++
 tickets/T-5247/ticket.md                           |    50 +
 tickets/T-5248/ticket.md                           |    44 +
 tickets/T-5249/ticket.md                           |    45 +
 tickets/T-5250/ticket.md                           |    47 +
 tickets/T-5251/ticket.md                           |    46 +
 tickets/T-5252/ticket.md                           |    53 +
 tickets/T-5253/ticket.md                           |    53 +
 tickets/T-5254/ticket.md                           |    47 +
 tickets/T-5255/ticket.md                           |    47 +
 tickets/T-5256/ticket.md                           |    64 +
 tickets/T-5259/done-report.md                      |  2887 +++
 tickets/T-5259/ticket.md                           |    35 +
 tickets/T-5260/ticket.md                           |    65 +
 tickets/T-5261/done-report.md                      |  3017 +++
 tickets/T-5261/ticket.md                           |    80 +
 tickets/T-5262/ticket.md                           |    49 +
 tickets/T-5263/ticket.md                           |    54 +
 tickets/T-5264/ticket.md                           |   582 +
 tickets/T-5265/ticket.md                           |    72 +
 tickets/T-5266/ticket.md                           |    47 +
 tickets/T-5267/done-report.md                      |  3284 +++
 tickets/T-5267/ticket.md                           |    88 +
 tickets/T-5268/ticket.md                           |    39 +
 tickets/T-5269/ticket.md                           |    38 +
 tickets/T-5270/ticket.md                           |    44 +
 tickets/T-5271/ticket.md                           |    45 +
 tickets/T-5272/ticket.md                           |    39 +
 tickets/T-5273/ticket.md                           |    45 +
 tickets/T-5274/done-report.md                      |  3761 +++
 tickets/T-5274/ticket.md                           |    63 +
 tickets/T-5275/done-report.md                      |  3805 ++++
 tickets/T-5275/ticket.md                           |    55 +
 tickets/T-5276/ticket.md                           |    57 +
 tickets/T-5277/ticket.md                           |    46 +
 tickets/T-5278/ticket.md                           |    40 +
 tickets/T-5279/ticket.md                           |    45 +
 tickets/T-5280/done-report.md                      |  3025 +++
 tickets/T-5280/ticket.md                           |    47 +
 tickets/T-5281/ticket.md                           |    45 +
 tickets/T-5282/ticket.md                           |    51 +
 tickets/T-5283/ticket.md                           |    39 +
 tickets/T-5284/ticket.md                           |    43 +
 tickets/T-5285/done-report.md                      |  3295 +++
 tickets/T-5285/ticket.md                           |    67 +
 tickets/T-5286/done-report.md                      |  3281 +++
 tickets/T-5286/ticket.md                           |    60 +
 tickets/T-5287/done-report.md                      |  3287 +++
 tickets/T-5287/ticket.md                           |   146 +
 tickets/T-5288/ticket.md                           |    40 +
 tickets/T-5289/done-report.md                      |  3280 +++
 tickets/T-5289/ticket.md                           |    61 +
 tickets/T-5290/ticket.md                           |    46 +
 tickets/T-5291/done-report.md                      |  3382 +++
 tickets/T-5291/ticket.md                           |    55 +
 tickets/T-5292/done-report.md                      |  4135 ++++
 tickets/T-5292/ticket.md                           |    84 +
 tickets/T-5293/done-report.md                      |  3275 +++
 tickets/T-5293/ticket.md                           |    67 +
 tickets/T-5294/done-report.md                      |  3760 +++
 tickets/T-5294/ticket.md                           |    71 +
 tickets/T-5295/done-report.md                      |  3391 +++
 tickets/T-5295/ticket.md                           |    55 +
 tickets/T-5296/done-report.md                      |  3382 +++
 tickets/T-5296/ticket.md                           |    93 +
 tickets/T-5297/ticket.md                           |    55 +
 tickets/T-5298/ticket.md                           |    74 +
 tickets/T-5299/done-report.md                      |  3386 +++
 tickets/T-5299/ticket.md                           |    84 +
 tickets/T-5300/done-report.md                      |  3959 ++++
 tickets/T-5300/ticket.md                           |   336 +
 tickets/T-5301/done-report.md                      |  3936 ++++
 tickets/T-5301/ticket.md                           |   194 +
 tickets/T-5302/done-report.md                      |  3998 ++++
 tickets/T-5302/ticket.md                           |   254 +
 tickets/T-5303/done-report.md                      |  3936 ++++
 tickets/T-5303/ticket.md                           |   351 +
 tickets/T-5304/done-report.md                      |  3938 ++++
 tickets/T-5304/ticket.md                           |   115 +
 tickets/T-5305/done-report.md                      |  4008 ++++
 tickets/T-5305/ticket.md                           |   107 +
 tickets/T-5306/done-report.md                      |  4213 ++++
 tickets/T-5306/ticket.md                           |    99 +
 tickets/T-5307/done-report.md                      |  4030 ++++
 tickets/T-5307/ticket.md                           |    96 +
 tickets/T-5308/done-report.md                      |  4164 ++++
 tickets/T-5308/ticket.md                           |   104 +
 tickets/T-5309/done-report.md                      |  4107 ++++
 tickets/T-5309/ticket.md                           |   106 +
 tickets/T-5310/ticket.md                           |   128 +
 tickets/T-5311/done-report.md                      |  4077 ++++
 tickets/T-5311/ticket.md                           |   160 +
 tickets/T-5312/ticket.md                           |   508 +
 tickets/T-5313/done-report.md                      |  4008 ++++
 tickets/T-5313/ticket.md                           |   147 +
 tickets/T-5314/ticket.md                           |    50 +
 tickets/T-5318/ticket.md                           |    37 +
 tickets/T-5321/done-report.md                      |  4339 ++++
 tickets/T-5321/ticket.md                           |   177 +
 tickets/T-5322/done-report.md                      |  4275 ++++
 tickets/T-5322/ticket.md                           |   254 +
 tickets/T-5323/done-report.md                      |  4173 ++++
 tickets/T-5323/ticket.md                           |   189 +
 tickets/T-5324/done-report.md                      |  4128 ++++
 tickets/T-5324/ticket.md                           |   148 +
 tickets/T-5325/done-report.md                      |  4181 ++++
 tickets/T-5325/ticket.md                           |   177 +
 tickets/T-5326/ticket.md                           |   141 +
 tickets/T-5327/ticket.md                           |    37 +
 tickets/T-5328/ticket.md                           |    34 +
 tickets/T-5329/ticket.md                           |   145 +
 tickets/T-5330/ticket.md                           |    65 +
 tickets/T-5331/ticket.md                           |    91 +
 tickets/T-5332/ticket.md                           |    85 +
 tickets/T-5333/done-report.md                      |  4385 ++++
 tickets/T-5333/ticket.md                           |    89 +
 tickets/T-5334/done-report.md                      |  4074 ++++
 tickets/T-5334/ticket.md                           |    89 +
 tickets/T-5335/done-report.md                      |  4282 ++++
 tickets/T-5335/ticket.md                           |    95 +
 tickets/T-5336/ticket.md                           |    38 +
 tickets/T-5337/done-report.md                      |  4182 ++++
 tickets/T-5337/ticket.md                           |    94 +
 tickets/T-5338/ticket.md                           |    66 +
 tickets/T-5339/done-report.md                      |  4306 ++++
 tickets/T-5339/ticket.md                           |    97 +
 tickets/T-5340/ticket.md                           |    37 +
 tickets/T-5341/done-report.md                      |  3979 ++++
 tickets/T-5341/ticket.md                           |    60 +
 tickets/T-5342/ticket.md                           |    61 +
 tickets/T-5343/ticket.md                           |    34 +
 tickets/T-5344/ticket.md                           |    45 +
 tickets/T-5345/ticket.md                           |    38 +
 tickets/T-5347/done-report.md                      |  3778 ++++
 tickets/T-5347/ticket.md                           |    58 +
 tickets/T-5348/ticket.md                           |    43 +
 tickets/T-5349/done-report.md                      |  4020 ++++
 tickets/T-5349/ticket.md                           |   129 +
 tickets/T-5350/done-report.md                      |  3869 ++++
 tickets/T-5350/ticket.md                           |    48 +
 tickets/T-5351/ticket.md                           |    77 +
 tickets/T-5352/ticket.md                           |    95 +
 tickets/T-5353/ticket.md                           |   114 +
 tickets/T-5354/ticket.md                           |   111 +
 tickets/T-5355/ticket.md                           |    62 +
 tickets/T-5356/done-report.md                      |  4022 ++++
 tickets/T-5356/ticket.md                           |   136 +
 tickets/T-5357/ticket.md                           |    83 +
 tickets/T-5358/ticket.md                           |    53 +
 tickets/T-5359/ticket.md                           |    96 +
 tickets/T-5360/done-report.md                      |  4026 ++++
 tickets/T-5360/ticket.md                           |    90 +
 tickets/T-5361/ticket.md                           |    47 +
 tickets/T-5362/ticket.md                           |    46 +
 tickets/T-5363/ticket.md                           |    46 +
 tickets/T-5364/done-report.md                      |  4006 ++++
 tickets/T-5364/ticket.md                           |    82 +
 tickets/T-5365/ticket.md                           |    47 +
 tickets/T-5366/ticket.md                           |    46 +
 tickets/T-5367/ticket.md                           |    48 +
 tickets/T-5368/ticket.md                           |    57 +
 tickets/T-5369/ticket.md                           |    48 +
 tickets/T-5370/ticket.md                           |    46 +
 tickets/T-5371/ticket.md                           |    46 +
 tickets/T-5372/ticket.md                           |    46 +
 tickets/T-5373/ticket.md                           |    46 +
 tickets/T-5374/ticket.md                           |    46 +
 tickets/T-5375/ticket.md                           |    37 +
 tickets/T-5376/done-report.md                      |  3917 ++++
 tickets/T-5376/ticket.md                           |    60 +
 tickets/T-5377/done-report.md                      |  3923 ++++
 tickets/T-5377/ticket.md                           |   161 +
 tickets/T-5378/done-report.md                      |  3920 ++++
 tickets/T-5378/ticket.md                           |    47 +
 tickets/T-5379/done-report.md                      |  3929 ++++
 tickets/T-5379/ticket.md                           |    57 +
 tickets/T-5380/done-report.md                      |  3927 ++++
 tickets/T-5380/ticket.md                           |    76 +
 tickets/T-5381/done-report.md                      |  3927 ++++
 tickets/T-5381/ticket.md                           |    49 +
 tickets/T-5382/done-report.md                      |  3964 ++++
 tickets/T-5382/ticket.md                           |    63 +
 tickets/T-5383/done-report.md                      |  3938 ++++
 tickets/T-5383/ticket.md                           |    50 +
 tickets/T-5384/done-report.md                      |  3955 ++++
 tickets/T-5384/ticket.md                           |    63 +
 tickets/T-5385/ticket.md                           |    49 +
 tickets/T-5386/ticket.md                           |    36 +
 tickets/T-5387/ticket.md                           |    45 +
 tickets/T-5388/ticket.md                           |    35 +
 tickets/T-5389/done-report.md                      |  3969 ++++
 tickets/T-5389/ticket.md                           |    57 +
 tickets/T-5390/ticket.md                           |    36 +
 tickets/T-5391/ticket.md                           |    37 +
 tickets/T-5392/done-report.md                      |  3993 ++++
 tickets/T-5392/ticket.md                           |    66 +
 tickets/T-5393/done-report.md                      |  3980 ++++
 tickets/T-5393/ticket.md                           |    93 +
 tickets/T-5394/done-report.md                      |  4056 ++++
 tickets/T-5394/ticket.md                           |    71 +
 tickets/T-5395/done-report.md                      |  4015 ++++
 tickets/T-5395/ticket.md                           |    49 +
 tickets/T-5396/done-report.md                      |  4071 ++++
 tickets/T-5396/ticket.md                           |    58 +
 tickets/T-5402/ticket.md                           |    34 +
 tickets/T-5403/ticket.md                           |    35 +
 tickets/T-5415/ticket.md                           |    35 +
 tickets/T-5421/done-report.md                      |  3994 ++++
 tickets/T-5421/ticket.md                           |    47 +
 tickets/T-5422/ticket.md                           |    55 +
 tickets/T-5423/ticket.md                           |    35 +
 tickets/T-5424/ticket.md                           |    35 +
 tickets/T-5425/ticket.md                           |    37 +
 tickets/T-5426/ticket.md                           |    37 +
 tickets/T-5427/ticket.md                           |    37 +
 tickets/T-5430/ticket.md                           |    39 +
 tickets/T-5436/done-report.md                      |    25 +
 tickets/T-5436/ticket.md                           |    87 +
 tickets/T-5437/ticket.md                           |    37 +
 tickets/T-5438/ticket.md                           |    36 +
 tickets/T-5440/ticket.md                           |    94 +
 tickets/T-5442/ticket.md                           |   261 +
 tickets/T-5443/ticket.md                           |    36 +
 tickets/T-5444/ticket.md                           |    58 +
 tickets/T-5445/ticket.md                           |    36 +
 tickets/T-5446/ticket.md                           |    36 +
 tickets/T-5447/ticket.md                           |    78 +
 tickets/T-5449/ticket.md                           |   180 +
 tickets/T-5454/done-report.md                      |  4304 ++++
 tickets/T-5454/ticket.md                           |    59 +
 tickets/T-5455/ticket.md                           |    62 +
 tickets/T-5456/ticket.md                           |    66 +
 tickets/T-5457/ticket.md                           |   128 +
 tickets/T-5458/ticket.md                           |    68 +
 tickets/T-5459/ticket.md                           |    42 +
 tickets/T-5460/ticket.md                           |    82 +
 tickets/T-5461/ticket.md                           |    37 +
 tickets/T-5462/ticket.md                           |    37 +
 tickets/T-5463/ticket.md                           |    73 +
 tickets/T-5464/done-report.md                      |  4402 ++++
 tickets/T-5464/ticket.md                           |    87 +
 tickets/T-5465/ticket.md                           |    64 +
 tickets/T-5466/ticket.md                           |    77 +
 tickets/T-5467/ticket.md                           |    64 +
 tickets/T-5468/ticket.md                           |    82 +
 tickets/T-5469/ticket.md                           |    49 +
 tickets/T-5470/ticket.md                           |    84 +
 tickets/T-5471/ticket.md                           |    48 +
 tickets/T-5472/ticket.md                           |    44 +
 tickets/T-5473/ticket.md                           |    53 +
 tickets/T-5474/ticket.md                           |    66 +
 tickets/T-5475/ticket.md                           |    95 +
 tickets/T-5476/ticket.md                           |    45 +
 tickets/T-5477/ticket.md                           |    78 +
 tickets/T-5478/ticket.md                           |    70 +
 tickets/T-5479/ticket.md                           |    55 +
 tickets/T-5480/ticket.md                           |    54 +
 tickets/T-5481/ticket.md                           |    47 +
 tickets/T-5482/ticket.md                           |   113 +
 tickets/T-5483/ticket.md                           |    74 +
 tickets/T-5487/ticket.md                           |    39 +
 tickets/T-5488/ticket.md                           |    38 +
 tickets/T-5492/ticket.md                 |    38 +
 tickets/T-draft-342a3548/ticket.md                 |    69 +
 tickets/T-5491/ticket.md                 |    72 +
 tickets/archive/T-0090/ticket.md                   |    18 +
 tickets/archive/T-0114/ticket.md                   |    45 +-
 tickets/archive/T-0143/ticket.md                   |    94 +-
 tickets/archive/T-0150/ticket.md                   |    48 +-
 tickets/archive/T-0151/ticket.md                   |    63 +
 tickets/archive/T-0153/ticket.md                   |    91 +
 tickets/archive/T-0157/ticket.md                   |    41 +-
 tickets/archive/T-0158/ticket.md                   |    63 +
 tickets/archive/T-0169/ticket.md                   |    39 +-
 tickets/archive/T-0171/ticket.md                   |    43 +-
 tickets/archive/T-0172/ticket.md                   |    40 +-
 tickets/archive/T-0174/ticket.md                   |    46 +-
 tickets/archive/T-0188/ticket.md                   |    41 +
 tickets/archive/T-0201/ticket.md                   |    63 +
 tickets/archive/T-0208/ticket.md                   |    90 +
 tickets/archive/T-0209/ticket.md                   |    88 +
 tickets/archive/T-0219/ticket.md                   |    34 +-
 tickets/archive/T-0240/ticket.md                   |    18 +
 tickets/archive/T-0243/ticket.md                   |    55 +-
 tickets/archive/T-0244/ticket.md                   |    35 +
 tickets/archive/T-0250/ticket.md                   |    35 +-
 tickets/archive/T-0253/ticket.md                   |   117 +
 tickets/archive/T-0265/ticket.md                   |    34 +
 tickets/archive/T-0279/ticket.md                   |    59 +-
 tickets/archive/T-0289/ticket.md                   |    36 +-
 tickets/archive/T-0292/ticket.md                   |    18 +
 tickets/archive/T-0294/ticket.md                   |    60 +
 tickets/archive/T-0309/ticket.md                   |    40 +-
 tickets/archive/T-0328/ticket.md                   |   378 +
 tickets/archive/T-0336/ticket.md                   |    18 +
 tickets/archive/T-0337/ticket.md                   |   152 +
 tickets/archive/T-0339/ticket.md                   |   123 +
 tickets/archive/T-0364/ticket.md                   |    24 +
 tickets/archive/T-0377/ticket.md                   |   300 +
 tickets/archive/T-0378/ticket.md                   |   378 +
 tickets/archive/T-0379/ticket.md                   |   111 +
 tickets/archive/T-0380/ticket.md                   |    38 +
 tickets/archive/T-0396/ticket.md                   |    39 +-
 tickets/archive/T-0401/ticket.md                   |    56 +-
 tickets/archive/T-0403/ticket.md                   |    18 +
 tickets/archive/T-0414/ticket.md                   |    36 +-
 tickets/archive/T-0427/ticket.md                   |    38 +-
 tickets/archive/T-0432/ticket.md                   |   152 +
 tickets/archive/T-0441/ticket.md                   |    26 +-
 tickets/archive/T-0458/ticket.md                   |    42 +-
 tickets/archive/T-0466/ticket.md                   |    34 +
 tickets/archive/T-0467/ticket.md                   |    24 +
 tickets/archive/T-0470/ticket.md                   |    35 +
 tickets/archive/T-0495/ticket.md                   |    40 +-
 tickets/archive/T-0496/ticket.md                   |    41 +-
 tickets/archive/T-0501/ticket.md                   |    77 +-
 tickets/archive/T-0503/ticket.md                   |    35 +-
 tickets/archive/T-0525/ticket.md                   |    18 +
 tickets/archive/T-0526/ticket.md                   |    46 +
 tickets/archive/T-0540/ticket.md                   |    38 +-
 tickets/archive/T-0553/ticket.md                   |    18 +
 tickets/archive/T-0557/ticket.md                   |    18 +
 tickets/archive/T-0576/ticket.md                   |    29 +
 tickets/archive/T-0577/ticket.md                   |    76 +
 tickets/archive/T-0605/ticket.md                   |    34 +
 tickets/archive/T-0610/ticket.md                   |    52 +
 tickets/archive/T-0627/ticket.md                   |    41 +-
 tickets/archive/T-0639/ticket.md                   |    25 +
 tickets/archive/T-0660/ticket.md                   |   152 +
 tickets/archive/T-0661/ticket.md                   |    81 +
 tickets/archive/T-0662/ticket.md                   |    45 +
 tickets/archive/T-0663/ticket.md                   |    45 +
 tickets/archive/T-0664/ticket.md                   |    45 +
 tickets/archive/T-0667/ticket.md                   |    40 +-
 tickets/archive/T-0685/ticket.md                   |    31 +
 tickets/archive/T-0687/ticket.md                   |    33 +
 tickets/archive/T-0689/ticket.md                   |    36 +
 tickets/archive/T-0723/ticket.md                   |    47 +-
 tickets/archive/T-0729/ticket.md                   |    35 +
 tickets/archive/T-0730/ticket.md                   |    18 +
 tickets/archive/T-0731/ticket.md                   |    27 +
 tickets/archive/T-0747/ticket.md                   |    27 +
 tickets/archive/T-0754/ticket.md                   |   135 +
 tickets/archive/T-0771/ticket.md                   |   114 +-
 tickets/archive/T-0779/ticket.md                   |    53 +-
 tickets/archive/T-0794/ticket.md                   |   142 +
 tickets/archive/T-0808/ticket.md                   |    31 +-
 tickets/archive/T-0814/ticket.md                   |    26 +
 tickets/archive/T-0821/ticket.md                   |    39 +
 tickets/archive/T-0845/ticket.md                   |    40 +-
 tickets/archive/T-0907/ticket.md                   |    90 +-
 tickets/archive/T-0910/ticket.md                   |    91 +
 tickets/archive/T-0918/ticket.md                   |    37 +-
 tickets/archive/T-0930/ticket.md                   |    28 +-
 tickets/archive/T-0968/ticket.md                   |    25 +
 tickets/archive/T-0971/ticket.md                   |    45 +-
 tickets/archive/T-0978/ticket.md                   |    48 +-
 tickets/archive/T-1003/ticket.md                   |    34 +
 tickets/archive/T-1011/ticket.md                   |    47 +
 tickets/archive/T-1020/ticket.md                   |    27 +-
 tickets/archive/T-1023/ticket.md                   |    35 +-
 tickets/archive/T-1034/ticket.md                   |    26 +-
 tickets/archive/T-1066/ticket.md                   |    41 +
 tickets/archive/T-1075/ticket.md                   |    36 +-
 tickets/archive/T-1095/ticket.md                   |    45 +-
 tickets/archive/T-1101/ticket.md                   |    22 +-
 tickets/archive/T-1112/ticket.md                   |    35 +
 tickets/archive/T-1126/ticket.md                   |    45 +-
 tickets/archive/T-1132/ticket.md                   |    36 +-
 tickets/archive/T-1141/ticket.md                   |    38 +
 tickets/archive/T-1144/ticket.md                   |    39 +
 tickets/archive/T-1148/ticket.md                   |    18 +
 tickets/archive/T-1181/ticket.md                   |    33 +
 tickets/archive/T-1182/ticket.md                   |    32 +
 tickets/archive/T-1195/ticket.md                   |    32 +
 tickets/archive/T-1210/ticket.md                   |    58 +
 tickets/archive/T-1211/ticket.md                   |    36 +-
 tickets/archive/T-1223/ticket.md                   |    73 +
 tickets/archive/T-1234/ticket.md                   |    31 +-
 tickets/archive/T-1246/ticket.md                   |    38 +-
 tickets/archive/T-1261/ticket.md                   |    32 +
 tickets/archive/T-1265/ticket.md                   |    18 +
 tickets/archive/T-1266/ticket.md                   |    18 +
 tickets/archive/T-1328/ticket.md                   |   125 +-
 tickets/archive/T-1341/ticket.md                   |    28 +-
 tickets/archive/T-1381/ticket.md                   |    25 +-
 tickets/archive/T-1391/ticket.md                   |    33 +-
 tickets/archive/T-1402/ticket.md                   |    18 +
 tickets/archive/T-1421/ticket.md                   |    50 +-
 tickets/archive/T-1428/ticket.md                   |    31 +
 tickets/archive/T-1433/ticket.md                   |    70 +-
 tickets/archive/T-1454/ticket.md                   |    40 +-
 tickets/archive/T-1516/ticket.md                   |    45 +-
 tickets/archive/T-1523/ticket.md                   |    39 +
 tickets/archive/T-1548/ticket.md                   |    30 +-
 tickets/archive/T-1559/ticket.md                   |    55 +-
 tickets/archive/T-1599/ticket.md                   |    22 +-
 tickets/archive/T-1600/ticket.md                   |    39 +-
 tickets/archive/T-1601/ticket.md                   |    32 +-
 tickets/archive/T-1606/ticket.md                   |    23 +-
 tickets/archive/T-1614/ticket.md                   |    16 +-
 tickets/archive/T-1616/ticket.md                   |    29 +-
 tickets/archive/T-1620/ticket.md                   |   137 +-
 tickets/archive/T-1621/ticket.md                   |    32 +-
 tickets/archive/T-1626/ticket.md                   |   242 +-
 tickets/archive/T-1629/ticket.md                   |    61 +-
 tickets/archive/T-1633/ticket.md                   |    86 +-
 tickets/archive/T-1636/ticket.md                   |    66 +
 tickets/archive/T-1647/ticket.md                   |    32 +
 tickets/archive/T-1649/ticket.md                   |   179 +-
 tickets/archive/T-1651/ticket.md                   |    11 +-
 tickets/archive/T-1659/ticket.md                   |    34 +
 tickets/archive/T-1665/ticket.md                   |    17 +-
 tickets/archive/T-1677/ticket.md                   |    59 +-
 tickets/archive/T-1684/ticket.md                   |    32 +
 tickets/archive/T-1688/ticket.md                   |    27 +-
 tickets/archive/T-1694/ticket.md                   |   129 +-
 tickets/archive/T-1700/ticket.md                   |    26 +
 tickets/archive/T-1703/ticket.md                   |    37 +-
 tickets/archive/T-1725/ticket.md                   |   104 +-
 tickets/archive/T-1727/ticket.md                   |    39 +-
 tickets/archive/T-1746/ticket.md                   |    94 +-
 tickets/archive/T-1748/ticket.md                   |    36 +
 tickets/archive/T-1760/ticket.md                   |   197 +-
 tickets/archive/T-1805/ticket.md                   |    87 +-
 tickets/archive/T-1870/ticket.md                   |    26 +-
 tickets/archive/T-1885/ticket.md                   |    35 +-
 tickets/archive/T-1886/ticket.md                   |    24 +
 tickets/archive/T-1916/ticket.md                   |    19 +-
 tickets/archive/T-1932/ticket.md                   |    34 +-
 tickets/archive/T-1970/ticket.md                   |    31 +-
 tickets/archive/T-1989/ticket.md                   |    25 +-
 tickets/archive/T-2001/ticket.md                   |    16 +
 tickets/archive/T-2011/ticket.md                   |    19 +-
 tickets/archive/T-2025/ticket.md                   |    26 +-
 tickets/archive/T-2069/ticket.md                   |    23 +-
 tickets/archive/T-2076/ticket.md                   |    59 +
 tickets/archive/T-2087/ticket.md                   |    50 +-
 tickets/archive/T-2131/ticket.md                   |    17 +-
 tickets/archive/T-2187/ticket.md                   |    15 +
 tickets/archive/T-2193/ticket.md                   |    20 +
 tickets/archive/T-2216/ticket.md                   |    27 +
 tickets/archive/T-2224/ticket.md                   |    32 +-
 tickets/archive/T-2231/ticket.md                   |    19 +-
 tickets/archive/T-2284/ticket.md                   |    16 +
 tickets/archive/T-2314/ticket.md                   |     9 +
 tickets/archive/T-2324/ticket.md                   |    33 +-
 tickets/archive/T-2338/ticket.md                   |     9 +
 tickets/archive/T-2358/ticket.md                   |    28 +
 tickets/archive/T-2365/ticket.md                   |    17 +-
 tickets/archive/T-2374/ticket.md                   |    18 +-
 tickets/archive/T-2400/ticket.md                   |    18 +
 tickets/archive/T-2409/ticket.md                   |    26 +-
 tickets/archive/T-2410/ticket.md                   |    21 +-
 tickets/archive/T-2438/ticket.md                   |     9 +
 tickets/archive/T-2454/ticket.md                   |     9 +
 tickets/archive/T-2457/ticket.md                   |    28 +-
 tickets/archive/T-2464/ticket.md                   |    62 +-
 tickets/archive/T-2473/ticket.md                   |    38 +
 tickets/archive/T-2479/ticket.md                   |    35 +-
 tickets/archive/T-2480/ticket.md                   |    20 +-
 tickets/archive/T-2493/ticket.md                   |   153 +-
 tickets/archive/T-2499/ticket.md                   |    22 +-
 tickets/archive/T-2532/ticket.md                   |    18 +-
 tickets/archive/T-2638/ticket.md                   |    27 +-
 tickets/archive/T-2668/ticket.md                   |    33 +-
 tickets/archive/T-2682/ticket.md                   |    33 +-
 tickets/archive/T-2688/ticket.md                   |     9 +
 tickets/archive/T-2698/ticket.md                   |    27 +-
 tickets/archive/T-2703/ticket.md                   |    20 +-
 tickets/archive/T-2710/ticket.md                   |     9 +
 tickets/archive/T-2740/ticket.md                   |   106 +
 tickets/archive/T-2857/ticket.md                   |    60 +-
 tickets/archive/T-2885/ticket.md                   |    42 +-
 tickets/archive/T-2906/ticket.md                   |    29 +
 tickets/archive/T-2922/ticket.md                   |    43 +
 tickets/archive/T-2931/ticket.md                   |    22 +-
 tickets/archive/T-2934/ticket.md                   |    20 +
 tickets/archive/T-2935/ticket.md                   |    20 +-
 tickets/archive/T-2965/done-report.md              |   149 +
 tickets/{ => archive}/T-2965/ticket.md             |    52 +-
 tickets/archive/T-2970/ticket.md                   |    33 +-
 tickets/archive/T-2979/ticket.md                   |    25 +-
 tickets/archive/T-2981/ticket.md                   |    26 +-
 tickets/archive/T-2996/ticket.md                   |    55 +-
 tickets/archive/T-3018/ticket.md                   |    35 +
 tickets/archive/T-3019/ticket.md                   |    23 +-
 tickets/archive/T-3020/done-report.md              |   578 +
 tickets/archive/T-3020/ticket.md                   |    92 +
 tickets/archive/T-3072/ticket.md                   |    29 +-
 tickets/archive/T-3082/done-report.md              |  2328 ++
 tickets/archive/T-3082/ticket.md                   |   126 +
 tickets/archive/T-3104/ticket.md                   |    39 +-
 tickets/archive/T-3115/ticket.md                   |    17 +
 tickets/archive/T-3128/ticket.md                   |    28 +
 tickets/archive/T-3220/ticket.md                   |    26 +-
 tickets/archive/T-3222/ticket.md                   |    31 +
 tickets/archive/T-3232/done-report.md              |   179 +
 tickets/archive/T-3232/ticket.md                   |   116 +
 tickets/archive/T-3233/done-report.md              |   606 +
 tickets/archive/T-3233/ticket.md                   |    87 +
 tickets/archive/T-3255/ticket.md                   |     9 +
 tickets/archive/T-3256/ticket.md                   |    65 +-
 tickets/{ => archive}/T-3259/ticket.md             |    24 +-
 tickets/archive/T-3275/ticket.md                   |    28 +-
 tickets/archive/T-3276/ticket.md                   |    39 +-
 tickets/{ => archive}/T-3308/done-report.md        |     0
 tickets/{ => archive}/T-3308/ticket.md             |     0
 tickets/{ => archive}/T-3315/done-report.md        |     0
 tickets/{ => archive}/T-3315/ticket.md             |     0
 tickets/archive/T-3350/ticket.md                   |    47 +-
 tickets/archive/T-3412/done-report.md              |  2262 ++
 tickets/{ => archive}/T-3412/ticket.md             |    41 +-
 tickets/archive/T-3464/ticket.md                   |    33 +-
 tickets/archive/T-3489/ticket.md                   |    18 +-
 tickets/archive/T-3492/ticket.md                   |    28 +
 tickets/archive/T-3493/ticket.md                   |    28 +
 tickets/archive/T-3496/ticket.md                   |    34 +
 tickets/{ => archive}/T-3512/done-report.md        |     0
 tickets/{ => archive}/T-3512/ticket.md             |     0
 tickets/archive/T-3541/ticket.md                   |    20 +-
 tickets/{ => archive}/T-3548/ticket.md             |     0
 tickets/archive/T-3577/ticket.md                   |    28 +-
 tickets/archive/T-3596/ticket.md                   |    26 +-
 tickets/archive/T-3612/done-report.md              |   221 +
 tickets/archive/T-3612/ticket.md                   |   255 +
 tickets/archive/T-3613/done-report.md              |   106 +
 tickets/archive/T-3613/ticket.md                   |   253 +
 tickets/archive/T-3615/done-report.md              |    33 +
 tickets/{ => archive}/T-3615/ticket.md             |    30 +-
 tickets/archive/T-3618/ticket.md                   |    37 +
 tickets/archive/T-3664/ticket.md                   |    11 +-
 tickets/archive/T-3665/ticket.md                   |    10 +-
 tickets/archive/T-3667/ticket.md                   |    28 +-
 tickets/archive/T-3669/ticket.md                   |    33 +-
 tickets/{ => archive}/T-3672/ticket.md             |     0
 tickets/archive/T-3675/ticket.md                   |    24 +-
 tickets/archive/T-3689/ticket.md                   |    58 +
 tickets/{ => archive}/T-3691/ticket.md             |     0
 tickets/{ => archive}/T-3699/done-report.md        |     0
 tickets/{ => archive}/T-3699/ticket.md             |     0
 tickets/{ => archive}/T-3701/ticket.md             |     0
 tickets/{ => archive}/T-3704/ticket.md             |     0
 tickets/archive/T-3708/ticket.md                   |   135 +-
 tickets/{ => archive}/T-3712/done-report.md        |     0
 tickets/{ => archive}/T-3712/ticket.md             |     0
 tickets/{ => archive}/T-3713/done-report.md        |     0
 tickets/{ => archive}/T-3713/ticket.md             |     0
 tickets/{ => archive}/T-3715/done-report.md        |     0
 tickets/{ => archive}/T-3715/ticket.md             |     0
 tickets/{ => archive}/T-3720/done-report.md        |     0
 tickets/{ => archive}/T-3720/ticket.md             |     0
 tickets/{ => archive}/T-3721/done-report.md        |     0
 tickets/{ => archive}/T-3721/ticket.md             |     0
 tickets/{ => archive}/T-3722/done-report.md        |     0
 tickets/{ => archive}/T-3722/ticket.md             |     0
 tickets/{ => archive}/T-3724/done-report.md        |     0
 tickets/{ => archive}/T-3724/ticket.md             |     0
 tickets/{ => archive}/T-3725/done-report.md        |     0
 tickets/{ => archive}/T-3725/ticket.md             |     0
 tickets/{ => archive}/T-3726/done-report.md        |     0
 tickets/{ => archive}/T-3726/ticket.md             |     0
 tickets/{ => archive}/T-3727/done-report.md        |     0
 tickets/{ => archive}/T-3727/ticket.md             |     0
 tickets/{ => archive}/T-3730/done-report.md        |     0
 tickets/{ => archive}/T-3730/ticket.md             |     0
 tickets/{ => archive}/T-3731/done-report.md        |     0
 tickets/{ => archive}/T-3731/ticket.md             |     0
 tickets/{ => archive}/T-3732/ticket.md             |     0
 tickets/{ => archive}/T-3733/done-report.md        |     0
 tickets/{ => archive}/T-3733/ticket.md             |     0
 tickets/{ => archive}/T-3734/done-report.md        |     0
 tickets/{ => archive}/T-3734/ticket.md             |     0
 tickets/{ => archive}/T-3735/done-report.md        |     0
 tickets/{ => archive}/T-3735/ticket.md             |     0
 tickets/{ => archive}/T-3736/ticket.md             |     0
 tickets/{ => archive}/T-3737/done-report.md        |     0
 tickets/{ => archive}/T-3737/ticket.md             |     0
 tickets/{ => archive}/T-3738/done-report.md        |     0
 tickets/{ => archive}/T-3738/ticket.md             |     0
 tickets/{ => archive}/T-3740/done-report.md        |     0
 tickets/{ => archive}/T-3740/ticket.md             |     0
 tickets/{ => archive}/T-3741/done-report.md        |     0
 tickets/{ => archive}/T-3741/ticket.md             |     0
 tickets/{ => archive}/T-3745/ticket.md             |     0
 tickets/{ => archive}/T-3746/done-report.md        |     0
 tickets/{ => archive}/T-3746/ticket.md             |     0
 tickets/{ => archive}/T-3747/done-report.md        |     0
 tickets/{ => archive}/T-3747/ticket.md             |     0
 tickets/{ => archive}/T-3748/done-report.md        |     0
 tickets/{ => archive}/T-3748/ticket.md             |     0
 tickets/{ => archive}/T-3749/done-report.md        |     0
 tickets/{ => archive}/T-3749/ticket.md             |     0
 tickets/{ => archive}/T-3750/done-report.md        |     0
 tickets/{ => archive}/T-3750/ticket.md             |     0
 tickets/{ => archive}/T-3751/done-report.md        |     0
 tickets/{ => archive}/T-3751/ticket.md             |     0
 tickets/{ => archive}/T-3752/done-report.md        |     0
 tickets/{ => archive}/T-3752/ticket.md             |     0
 tickets/{ => archive}/T-3753/done-report.md        |     0
 tickets/{ => archive}/T-3753/ticket.md             |     0
 tickets/{ => archive}/T-3754/done-report.md        |     0
 tickets/{ => archive}/T-3754/ticket.md             |     0
 tickets/{ => archive}/T-3755/done-report.md        |     0
 tickets/{ => archive}/T-3755/ticket.md             |     0
 tickets/{ => archive}/T-3756/done-report.md        |     0
 tickets/{ => archive}/T-3756/ticket.md             |     0
 tickets/{ => archive}/T-3757/done-report.md        |     0
 tickets/{ => archive}/T-3757/ticket.md             |     0
 tickets/{ => archive}/T-3759/done-report.md        |     0
 tickets/{ => archive}/T-3759/ticket.md             |     0
 tickets/{ => archive}/T-3760/done-report.md        |     0
 tickets/{ => archive}/T-3760/ticket.md             |     0
 tickets/{ => archive}/T-3761/done-report.md        |     0
 tickets/{ => archive}/T-3761/ticket.md             |     0
 tickets/{ => archive}/T-3762/done-report.md        |     0
 tickets/{ => archive}/T-3762/ticket.md             |     0
 tickets/{ => archive}/T-3763/done-report.md        |     0
 tickets/{ => archive}/T-3763/ticket.md             |     0
 tickets/{ => archive}/T-3764/done-report.md        |     0
 tickets/{ => archive}/T-3764/ticket.md             |     0
 tickets/{ => archive}/T-3765/done-report.md        |     0
 tickets/{ => archive}/T-3765/ticket.md             |     0
 tickets/{ => archive}/T-3766/done-report.md        |     0
 tickets/{ => archive}/T-3766/ticket.md             |     0
 tickets/{ => archive}/T-3767/done-report.md        |     0
 tickets/{ => archive}/T-3767/ticket.md             |     0
 tickets/{ => archive}/T-3768/done-report.md        |     0
 tickets/{ => archive}/T-3768/ticket.md             |     0
 tickets/{ => archive}/T-3769/done-report.md        |     0
 tickets/{ => archive}/T-3769/ticket.md             |     0
 tickets/{ => archive}/T-3771/done-report.md        |     0
 tickets/{ => archive}/T-3771/ticket.md             |     0
 tickets/{ => archive}/T-3774/done-report.md        |     0
 tickets/{ => archive}/T-3774/ticket.md             |     0
 tickets/{ => archive}/T-3776/done-report.md        |     0
 tickets/{ => archive}/T-3776/ticket.md             |     0
 tickets/{ => archive}/T-3777/done-report.md        |     0
 tickets/{ => archive}/T-3777/ticket.md             |     0
 tickets/{ => archive}/T-3778/done-report.md        |     0
 tickets/{ => archive}/T-3778/ticket.md             |     0
 tickets/{ => archive}/T-3779/ticket.md             |     0
 tickets/{ => archive}/T-3780/ticket.md             |     0
 tickets/{ => archive}/T-3781/done-report.md        |     0
 tickets/{ => archive}/T-3781/ticket.md             |     0
 tickets/{ => archive}/T-3782/done-report.md        |     0
 tickets/{ => archive}/T-3782/ticket.md             |     0
 tickets/{ => archive}/T-3784/done-report.md        |     0
 tickets/{ => archive}/T-3784/ticket.md             |     0
 tickets/{ => archive}/T-3785/done-report.md        |     0
 tickets/{ => archive}/T-3785/ticket.md             |     0
 tickets/{ => archive}/T-3786/done-report.md        |     0
 tickets/{ => archive}/T-3786/ticket.md             |     0
 tickets/{ => archive}/T-3787/done-report.md        |     0
 tickets/{ => archive}/T-3787/ticket.md             |     0
 tickets/{ => archive}/T-3788/done-report.md        |     0
 tickets/{ => archive}/T-3788/ticket.md             |     0
 tickets/{ => archive}/T-3790/done-report.md        |     0
 tickets/{ => archive}/T-3790/ticket.md             |     0
 tickets/{ => archive}/T-3791/done-report.md        |     0
 tickets/{ => archive}/T-3791/ticket.md             |     0
 tickets/{ => archive}/T-3792/done-report.md        |     0
 tickets/{ => archive}/T-3792/ticket.md             |     0
 tickets/{ => archive}/T-3793/done-report.md        |     0
 tickets/{ => archive}/T-3793/ticket.md             |     0
 tickets/{ => archive}/T-3794/done-report.md        |     0
 tickets/{ => archive}/T-3794/ticket.md             |     0
 tickets/{ => archive}/T-3795/done-report.md        |     0
 tickets/{ => archive}/T-3795/ticket.md             |     0
 tickets/{ => archive}/T-3796/done-report.md        |     0
 tickets/{ => archive}/T-3796/ticket.md             |     0
 tickets/{ => archive}/T-3797/done-report.md        |     0
 tickets/{ => archive}/T-3797/ticket.md             |     0
 tickets/{ => archive}/T-3798/done-report.md        |     0
 tickets/{ => archive}/T-3798/ticket.md             |     0
 tickets/{ => archive}/T-3799/done-report.md        |     0
 tickets/{ => archive}/T-3799/ticket.md             |     0
 tickets/{ => archive}/T-3801/done-report.md        |     0
 tickets/{ => archive}/T-3801/ticket.md             |     0
 tickets/archive/T-3802/done-report.md              |  2260 ++
 tickets/archive/T-3802/ticket.md                   |    54 +
 tickets/{ => archive}/T-3810/done-report.md        |     0
 tickets/{ => archive}/T-3810/ticket.md             |     0
 tickets/{ => archive}/T-3818/done-report.md        |     0
 tickets/{ => archive}/T-3818/ticket.md             |     0
 tickets/{ => archive}/T-3819/ticket.md             |     0
 tickets/{ => archive}/T-3820/done-report.md        |     0
 tickets/{ => archive}/T-3820/ticket.md             |    21 +-
 tickets/{ => archive}/T-3837/done-report.md        |     0
 tickets/{ => archive}/T-3837/ticket.md             |     0
 tickets/{ => archive}/T-3843/done-report.md        |     0
 tickets/{ => archive}/T-3843/ticket.md             |    18 +-
 tickets/{ => archive}/T-3844/done-report.md        |     0
 tickets/{ => archive}/T-3844/ticket.md             |     0
 tickets/{ => archive}/T-3845/done-report.md        |     0
 tickets/{ => archive}/T-3845/ticket.md             |     0
 tickets/{ => archive}/T-3846/done-report.md        |     0
 tickets/{ => archive}/T-3846/ticket.md             |     0
 tickets/{ => archive}/T-3847/done-report.md        |     0
 tickets/{ => archive}/T-3847/ticket.md             |     0
 tickets/{ => archive}/T-3848/done-report.md        |     0
 tickets/{ => archive}/T-3848/ticket.md             |     0
 tickets/{ => archive}/T-3852/done-report.md        |     0
 tickets/{ => archive}/T-3852/ticket.md             |     0
 tickets/archive/T-3856/done-report.md              |   247 +
 tickets/{ => archive}/T-3856/ticket.md             |    81 +-
 tickets/{ => archive}/T-3857/done-report.md        |     0
 tickets/{ => archive}/T-3857/ticket.md             |     0
 tickets/{ => archive}/T-3884/done-report.md        |     0
 tickets/{ => archive}/T-3884/ticket.md             |     0
 tickets/{ => archive}/T-3885/done-report.md        |     0
 tickets/{ => archive}/T-3885/ticket.md             |     0
 tickets/{ => archive}/T-3886/done-report.md        |     0
 tickets/{ => archive}/T-3886/ticket.md             |    28 +-
 tickets/{ => archive}/T-3887/done-report.md        |     0
 tickets/{ => archive}/T-3887/ticket.md             |     0
 tickets/{ => archive}/T-3892/done-report.md        |     0
 tickets/{ => archive}/T-3892/ticket.md             |     0
 tickets/{ => archive}/T-3893/done-report.md        |     0
 tickets/{ => archive}/T-3893/ticket.md             |    24 +-
 tickets/{ => archive}/T-3895/done-report.md        |     0
 tickets/{ => archive}/T-3895/ticket.md             |     0
 tickets/{ => archive}/T-3900/done-report.md        |     0
 tickets/{ => archive}/T-3900/ticket.md             |     0
 tickets/{ => archive}/T-3901/ticket.md             |     0
 tickets/{ => archive}/T-3903/done-report.md        |     0
 tickets/{ => archive}/T-3903/ticket.md             |     0
 tickets/{ => archive}/T-3905/ticket.md             |     0
 tickets/{ => archive}/T-3906/done-report.md        |     0
 tickets/{ => archive}/T-3906/ticket.md             |     0
 tickets/{ => archive}/T-3907/done-report.md        |     0
 tickets/{ => archive}/T-3907/ticket.md             |     0
 tickets/{ => archive}/T-3908/done-report.md        |     0
 tickets/{ => archive}/T-3908/ticket.md             |     0
 tickets/{ => archive}/T-3909/ticket.md             |     0
 tickets/{ => archive}/T-3910/ticket.md             |     0
 tickets/{ => archive}/T-3912/done-report.md        |     0
 tickets/{ => archive}/T-3912/ticket.md             |     0
 tickets/{ => archive}/T-3913/ticket.md             |     0
 tickets/{ => archive}/T-3914/done-report.md        |     0
 tickets/{ => archive}/T-3914/ticket.md             |     0
 tickets/{ => archive}/T-3922/done-report.md        |     0
 tickets/{ => archive}/T-3922/ticket.md             |     0
 tickets/{ => archive}/T-3925/done-report.md        |     0
 tickets/{ => archive}/T-3925/ticket.md             |     0
 tickets/{ => archive}/T-3930/done-report.md        |     0
 tickets/{ => archive}/T-3930/ticket.md             |     0
 tickets/{ => archive}/T-3931/done-report.md        |     0
 tickets/{ => archive}/T-3931/ticket.md             |     0
 tickets/{ => archive}/T-3934/done-report.md        |     0
 tickets/{ => archive}/T-3934/ticket.md             |     0
 tickets/{ => archive}/T-3935/done-report.md        |     0
 tickets/{ => archive}/T-3935/ticket.md             |     0
 tickets/{ => archive}/T-3937/done-report.md        |     0
 tickets/{ => archive}/T-3937/ticket.md             |     0
 tickets/{ => archive}/T-3940/done-report.md        |     0
 tickets/{ => archive}/T-3940/ticket.md             |     0
 tickets/{ => archive}/T-3941/done-report.md        |     0
 tickets/{ => archive}/T-3941/ticket.md             |     0
 tickets/archive/T-3943/done-report.md              |   626 +
 tickets/{ => archive}/T-3943/ticket.md             |    68 +-
 tickets/{ => archive}/T-3947/done-report.md        |     0
 tickets/{ => archive}/T-3947/ticket.md             |     0
 tickets/{ => archive}/T-3948/done-report.md        |     0
 tickets/{ => archive}/T-3948/ticket.md             |     0
 tickets/{ => archive}/T-3956/ticket.md             |     0
 tickets/archive/T-3961/done-report.md              |   701 +
 tickets/{ => archive}/T-3961/ticket.md             |    47 +-
 tickets/{ => archive}/T-3979/done-report.md        |     0
 tickets/{ => archive}/T-3979/ticket.md             |    39 +-
 tickets/{ => archive}/T-3980/done-report.md        |     0
 tickets/{ => archive}/T-3980/ticket.md             |     0
 tickets/{ => archive}/T-3985/done-report.md        |     0
 tickets/{ => archive}/T-3985/ticket.md             |    28 +-
 tickets/{ => archive}/T-4000/done-report.md        |     0
 tickets/{ => archive}/T-4000/ticket.md             |     0
 tickets/{ => archive}/T-4013/done-report.md        |     0
 tickets/{ => archive}/T-4013/ticket.md             |     0
 tickets/{ => archive}/T-4018/done-report.md        |     0
 tickets/{ => archive}/T-4018/ticket.md             |     0
 tickets/{ => archive}/T-4019/done-report.md        |     0
 tickets/{ => archive}/T-4019/ticket.md             |    27 +-
 tickets/{ => archive}/T-4028/done-report.md        |     0
 tickets/{ => archive}/T-4028/ticket.md             |     0
 tickets/{ => archive}/T-4037/done-report.md        |     0
 tickets/{ => archive}/T-4037/ticket.md             |     0
 tickets/{ => archive}/T-4041/done-report.md        |     0
 tickets/{ => archive}/T-4041/ticket.md             |     0
 tickets/{ => archive}/T-4046/done-report.md        |     0
 tickets/{ => archive}/T-4046/ticket.md             |     0
 tickets/{ => archive}/T-4047/done-report.md        |     0
 tickets/{ => archive}/T-4047/ticket.md             |     0
 tickets/{ => archive}/T-4055/done-report.md        |     0
 tickets/{ => archive}/T-4055/ticket.md             |     0
 tickets/{ => archive}/T-4056/done-report.md        |     0
 tickets/{ => archive}/T-4056/ticket.md             |     0
 tickets/{ => archive}/T-4057/done-report.md        |     0
 tickets/{ => archive}/T-4057/ticket.md             |     0
 tickets/{ => archive}/T-4060/ticket.md             |     0
 tickets/{ => archive}/T-4085/done-report.md        |     0
 tickets/{ => archive}/T-4085/ticket.md             |     0
 tickets/{ => archive}/T-4088/done-report.md        |     0
 tickets/{ => archive}/T-4088/ticket.md             |     0
 tickets/{ => archive}/T-4102/done-report.md        |     0
 tickets/{ => archive}/T-4102/ticket.md             |     0
 tickets/{ => archive}/T-4103/done-report.md        |     0
 tickets/{ => archive}/T-4103/ticket.md             |     0
 tickets/{ => archive}/T-4104/ticket.md             |     0
 tickets/{ => archive}/T-4105/done-report.md        |     0
 tickets/{ => archive}/T-4105/ticket.md             |     0
 tickets/{ => archive}/T-4106/done-report.md        |     0
 tickets/{ => archive}/T-4106/ticket.md             |     0
 tickets/{ => archive}/T-4107/done-report.md        |     0
 tickets/{ => archive}/T-4107/ticket.md             |     0
 tickets/{ => archive}/T-4108/done-report.md        |     0
 tickets/{ => archive}/T-4108/ticket.md             |     0
 tickets/{ => archive}/T-4110/done-report.md        |     0
 tickets/{ => archive}/T-4110/ticket.md             |    35 +-
 tickets/archive/T-4111/done-report.md              |   726 +
 tickets/{ => archive}/T-4111/ticket.md             |    29 +-
 tickets/archive/T-4116/done-report.md              |   707 +
 tickets/{ => archive}/T-4116/ticket.md             |    17 +-
 tickets/archive/T-4118/done-report.md              |  2241 ++
 tickets/{ => archive}/T-4118/ticket.md             |    33 +-
 tickets/{ => archive}/T-4121/ticket.md             |     0
 tickets/{ => archive}/T-4122/ticket.md             |     0
 tickets/{ => archive}/T-4125/done-report.md        |     0
 tickets/{ => archive}/T-4125/ticket.md             |     0
 tickets/{ => archive}/T-4130/done-report.md        |     0
 tickets/{ => archive}/T-4130/ticket.md             |     0
 tickets/{ => archive}/T-4131/done-report.md        |     0
 tickets/{ => archive}/T-4131/ticket.md             |     0
 tickets/{ => archive}/T-4132/done-report.md        |     0
 tickets/{ => archive}/T-4132/ticket.md             |     0
 tickets/{ => archive}/T-4136/done-report.md        |     0
 tickets/{ => archive}/T-4136/ticket.md             |     0
 tickets/{ => archive}/T-4137/ticket.md             |     0
 tickets/{ => archive}/T-4138/done-report.md        |     0
 tickets/{ => archive}/T-4138/ticket.md             |     0
 tickets/{ => archive}/T-4139/done-report.md        |     0
 tickets/{ => archive}/T-4139/ticket.md             |     0
 tickets/{ => archive}/T-4142/ticket.md             |     0
 tickets/{ => archive}/T-4143/done-report.md        |     0
 tickets/{ => archive}/T-4143/ticket.md             |     0
 tickets/{ => archive}/T-4145/done-report.md        |     0
 tickets/{ => archive}/T-4145/ticket.md             |    35 +-
 tickets/{ => archive}/T-4146/done-report.md        |     0
 tickets/{ => archive}/T-4146/ticket.md             |     0
 tickets/{ => archive}/T-4147/done-report.md        |     0
 tickets/{ => archive}/T-4147/ticket.md             |    19 +-
 tickets/{ => archive}/T-4148/done-report.md        |     0
 tickets/{ => archive}/T-4148/ticket.md             |     0
 tickets/{ => archive}/T-4150/done-report.md        |     0
 tickets/{ => archive}/T-4150/ticket.md             |     0
 tickets/{ => archive}/T-4153/done-report.md        |     0
 tickets/{ => archive}/T-4153/ticket.md             |    23 +-
 tickets/{ => archive}/T-4154/done-report.md        |     0
 tickets/{ => archive}/T-4154/ticket.md             |     0
 tickets/{ => archive}/T-4155/done-report.md        |     0
 tickets/{ => archive}/T-4155/ticket.md             |     0
 tickets/{ => archive}/T-4159/done-report.md        |     0
 tickets/{ => archive}/T-4159/ticket.md             |    29 +-
 tickets/{ => archive}/T-4163/done-report.md        |     0
 tickets/{ => archive}/T-4163/ticket.md             |     0
 tickets/{ => archive}/T-4167/done-report.md        |     0
 tickets/{ => archive}/T-4167/ticket.md             |     0
 tickets/{ => archive}/T-4170/done-report.md        |     0
 tickets/{ => archive}/T-4170/ticket.md             |     0
 tickets/{ => archive}/T-4171/done-report.md        |     0
 tickets/{ => archive}/T-4171/ticket.md             |     0
 tickets/{ => archive}/T-4172/done-report.md        |     0
 tickets/{ => archive}/T-4172/ticket.md             |     0
 tickets/{ => archive}/T-4173/ticket.md             |     0
 tickets/{ => archive}/T-4177/done-report.md        |     0
 tickets/{ => archive}/T-4177/ticket.md             |     0
 tickets/{ => archive}/T-4178/done-report.md        |     0
 tickets/{ => archive}/T-4178/ticket.md             |     0
 tickets/{ => archive}/T-4179/done-report.md        |     0
 tickets/{ => archive}/T-4179/ticket.md             |     0
 tickets/{ => archive}/T-4184/done-report.md        |     0
 tickets/{ => archive}/T-4184/ticket.md             |     0
 tickets/{ => archive}/T-4185/ticket.md             |     7 +-
 tickets/{ => archive}/T-4186/ticket.md             |     7 +-
 tickets/{ => archive}/T-4191/done-report.md        |     0
 tickets/{ => archive}/T-4191/ticket.md             |     0
 tickets/{ => archive}/T-4195/ticket.md             |     0
 tickets/{ => archive}/T-4197/done-report.md        |     0
 tickets/{ => archive}/T-4197/ticket.md             |     0
 tickets/{ => archive}/T-4201/done-report.md        |     0
 tickets/{ => archive}/T-4201/ticket.md             |     0
 tickets/{ => archive}/T-4207/ticket.md             |     0
 tickets/{ => archive}/T-4208/ticket.md             |     0
 tickets/{ => archive}/T-4210/ticket.md             |     0
 tickets/archive/T-4212/done-report.md              |  2299 ++
 tickets/{ => archive}/T-4212/ticket.md             |    20 +-
 tickets/archive/T-4214/done-report.md              |   667 +
 tickets/archive/T-4214/ticket.md                   |    81 +
 tickets/{ => archive}/T-4219/done-report.md        |     0
 tickets/{ => archive}/T-4219/ticket.md             |     0
 tickets/archive/T-4221/done-report.md              |   706 +
 tickets/archive/T-4221/ticket.md                   |   146 +
 tickets/archive/T-4230/done-report.md              |   723 +
 tickets/{ => archive}/T-4230/ticket.md             |    15 +-
 tickets/{ => archive}/T-4234/done-report.md        |     0
 tickets/{ => archive}/T-4234/ticket.md             |     0
 tickets/{ => archive}/T-4236/done-report.md        |     0
 tickets/{ => archive}/T-4236/ticket.md             |     0
 tickets/archive/T-4240/done-report.md              |  2300 ++
 tickets/{ => archive}/T-4240/ticket.md             |     7 +-
 tickets/{ => archive}/T-4243/done-report.md        |     0
 tickets/{ => archive}/T-4243/ticket.md             |    36 +-
 tickets/{ => archive}/T-4244/done-report.md        |     0
 tickets/{ => archive}/T-4244/ticket.md             |     0
 tickets/{ => archive}/T-4246/ticket.md             |     0
 tickets/{ => archive}/T-4255/done-report.md        |     0
 tickets/{ => archive}/T-4255/ticket.md             |     0
 tickets/{ => archive}/T-4257/done-report.md        |     0
 tickets/{ => archive}/T-4257/ticket.md             |    63 +-
 tickets/{ => archive}/T-4258/done-report.md        |     0
 tickets/{ => archive}/T-4258/ticket.md             |    27 +-
 tickets/{ => archive}/T-4260/done-report.md        |     0
 tickets/{ => archive}/T-4260/ticket.md             |     0
 tickets/{ => archive}/T-4262/ticket.md             |     0
 tickets/{ => archive}/T-4263/done-report.md        |     0
 tickets/{ => archive}/T-4263/ticket.md             |     0
 tickets/{ => archive}/T-4264/done-report.md        |     0
 tickets/{ => archive}/T-4264/ticket.md             |     0
 tickets/{ => archive}/T-4265/done-report.md        |     0
 tickets/{ => archive}/T-4265/ticket.md             |     0
 tickets/{ => archive}/T-4266/done-report.md        |     0
 tickets/{ => archive}/T-4266/ticket.md             |     0
 tickets/{ => archive}/T-4267/done-report.md        |     0
 tickets/{ => archive}/T-4267/ticket.md             |     0
 tickets/{ => archive}/T-4269/done-report.md        |     0
 tickets/{ => archive}/T-4269/ticket.md             |     0
 tickets/{ => archive}/T-4270/done-report.md        |     0
 tickets/{ => archive}/T-4270/ticket.md             |     0
 tickets/{ => archive}/T-4271/done-report.md        |     0
 tickets/{ => archive}/T-4271/ticket.md             |     0
 tickets/{ => archive}/T-4273/done-report.md        |     0
 tickets/{ => archive}/T-4273/ticket.md             |     0
 tickets/{ => archive}/T-4274/done-report.md        |     0
 tickets/{ => archive}/T-4274/ticket.md             |     0
 tickets/{ => archive}/T-4275/done-report.md        |     0
 tickets/{ => archive}/T-4275/ticket.md             |     0
 tickets/{ => archive}/T-4276/done-report.md        |     0
 tickets/{ => archive}/T-4276/ticket.md             |     0
 tickets/{ => archive}/T-4278/done-report.md        |     0
 tickets/{ => archive}/T-4278/ticket.md             |     0
 tickets/{ => archive}/T-4279/done-report.md        |     0
 tickets/{ => archive}/T-4279/ticket.md             |     0
 tickets/{ => archive}/T-4280/done-report.md        |     0
 tickets/{ => archive}/T-4280/ticket.md             |     0
 tickets/{ => archive}/T-4281/done-report.md        |     0
 tickets/{ => archive}/T-4281/ticket.md             |     0
 tickets/{ => archive}/T-4282/done-report.md        |     0
 tickets/{ => archive}/T-4282/ticket.md             |     0
 tickets/{ => archive}/T-4286/done-report.md        |     0
 tickets/{ => archive}/T-4286/ticket.md             |     0
 tickets/{ => archive}/T-4287/done-report.md        |     0
 tickets/{ => archive}/T-4287/ticket.md             |     0
 tickets/{ => archive}/T-4288/done-report.md        |     0
 tickets/{ => archive}/T-4288/ticket.md             |     0
 tickets/{ => archive}/T-4289/done-report.md        |     0
 tickets/{ => archive}/T-4289/ticket.md             |     0
 tickets/{ => archive}/T-4290/done-report.md        |     0
 tickets/{ => archive}/T-4290/ticket.md             |     0
 tickets/{ => archive}/T-4292/ticket.md             |     0
 tickets/{ => archive}/T-4295/ticket.md             |     0
 tickets/{ => archive}/T-4297/done-report.md        |     0
 tickets/{ => archive}/T-4297/ticket.md             |     0
 tickets/{ => archive}/T-4298/done-report.md        |     0
 tickets/{ => archive}/T-4298/ticket.md             |     0
 tickets/{ => archive}/T-4299/done-report.md        |     0
 tickets/{ => archive}/T-4299/ticket.md             |     0
 tickets/{ => archive}/T-4301/done-report.md        |     0
 tickets/{ => archive}/T-4301/ticket.md             |     0
 tickets/{ => archive}/T-4302/done-report.md        |     0
 tickets/{ => archive}/T-4302/ticket.md             |     0
 tickets/{ => archive}/T-4303/done-report.md        |     0
 tickets/{ => archive}/T-4303/ticket.md             |    25 +-
 tickets/{ => archive}/T-4304/ticket.md             |     0
 tickets/{ => archive}/T-4305/done-report.md        |     0
 tickets/{ => archive}/T-4305/ticket.md             |     0
 tickets/{ => archive}/T-4306/done-report.md        |     0
 tickets/{ => archive}/T-4306/ticket.md             |     0
 tickets/{ => archive}/T-4307/done-report.md        |     0
 tickets/{ => archive}/T-4307/ticket.md             |     0
 tickets/{ => archive}/T-4308/done-report.md        |     0
 tickets/{ => archive}/T-4308/ticket.md             |     0
 tickets/{ => archive}/T-4309/done-report.md        |     0
 tickets/{ => archive}/T-4309/ticket.md             |     0
 tickets/{ => archive}/T-4310/done-report.md        |     0
 tickets/{ => archive}/T-4310/ticket.md             |     0
 tickets/{ => archive}/T-4312/done-report.md        |     0
 tickets/{ => archive}/T-4312/ticket.md             |    74 +-
 tickets/{ => archive}/T-4314/done-report.md        |     0
 tickets/{ => archive}/T-4314/ticket.md             |     0
 tickets/{ => archive}/T-4315/ticket.md             |     0
 tickets/{ => archive}/T-4316/done-report.md        |     0
 tickets/{ => archive}/T-4316/ticket.md             |     0
 tickets/{ => archive}/T-4317/done-report.md        |     0
 tickets/{ => archive}/T-4317/ticket.md             |     0
 tickets/{ => archive}/T-4318/done-report.md        |     0
 tickets/{ => archive}/T-4318/ticket.md             |     0
 tickets/{ => archive}/T-4319/done-report.md        |     0
 tickets/{ => archive}/T-4319/ticket.md             |     0
 tickets/{ => archive}/T-4320/done-report.md        |     0
 tickets/{ => archive}/T-4320/ticket.md             |     0
 tickets/{ => archive}/T-4321/ticket.md             |     0
 tickets/{ => archive}/T-4322/done-report.md        |     0
 tickets/{ => archive}/T-4322/ticket.md             |     0
 tickets/{ => archive}/T-4323/done-report.md        |     0
 tickets/{ => archive}/T-4323/ticket.md             |     0
 tickets/{ => archive}/T-4324/done-report.md        |     0
 tickets/{ => archive}/T-4324/ticket.md             |     0
 tickets/{ => archive}/T-4325/done-report.md        |     0
 tickets/{ => archive}/T-4325/ticket.md             |     0
 tickets/{ => archive}/T-4326/done-report.md        |     0
 tickets/{ => archive}/T-4326/ticket.md             |     0
 tickets/{ => archive}/T-4327/done-report.md        |     0
 tickets/{ => archive}/T-4327/ticket.md             |     0
 tickets/{ => archive}/T-4328/done-report.md        |     0
 tickets/{ => archive}/T-4328/ticket.md             |     0
 tickets/{ => archive}/T-4329/done-report.md        |     0
 tickets/{ => archive}/T-4329/ticket.md             |     0
 tickets/{ => archive}/T-4331/done-report.md        |     0
 tickets/{ => archive}/T-4331/ticket.md             |     0
 tickets/{ => archive}/T-4333/done-report.md        |     0
 tickets/{ => archive}/T-4333/ticket.md             |     0
 tickets/{ => archive}/T-4334/done-report.md        |     0
 tickets/{ => archive}/T-4334/ticket.md             |     0
 tickets/{ => archive}/T-4335/done-report.md        |     0
 tickets/{ => archive}/T-4335/ticket.md             |     0
 tickets/{ => archive}/T-4336/done-report.md        |     0
 tickets/{ => archive}/T-4336/ticket.md             |     0
 tickets/{ => archive}/T-4337/ticket.md             |     0
 tickets/{ => archive}/T-4338/done-report.md        |     0
 tickets/{ => archive}/T-4338/ticket.md             |     0
 tickets/{ => archive}/T-4339/done-report.md        |     0
 tickets/{ => archive}/T-4339/ticket.md             |     0
 tickets/{ => archive}/T-4340/done-report.md        |     0
 tickets/{ => archive}/T-4340/ticket.md             |     0
 tickets/{ => archive}/T-4341/done-report.md        |     0
 tickets/{ => archive}/T-4341/ticket.md             |     0
 tickets/{ => archive}/T-4342/done-report.md        |     0
 tickets/{ => archive}/T-4342/ticket.md             |     0
 tickets/{ => archive}/T-4343/done-report.md        |     0
 tickets/{ => archive}/T-4343/ticket.md             |     0
 tickets/{ => archive}/T-4344/done-report.md        |     0
 tickets/{ => archive}/T-4344/ticket.md             |     0
 tickets/{ => archive}/T-4345/done-report.md        |     0
 tickets/{ => archive}/T-4345/ticket.md             |     0
 tickets/{ => archive}/T-4346/done-report.md        |     0
 tickets/{ => archive}/T-4346/ticket.md             |     0
 tickets/{ => archive}/T-4347/ticket.md             |     0
 tickets/{ => archive}/T-4348/done-report.md        |     0
 tickets/{ => archive}/T-4348/ticket.md             |     0
 tickets/{ => archive}/T-4349/done-report.md        |     0
 tickets/{ => archive}/T-4349/ticket.md             |     0
 tickets/{ => archive}/T-4350/done-report.md        |     0
 tickets/{ => archive}/T-4350/ticket.md             |     0
 tickets/{ => archive}/T-4351/done-report.md        |     0
 tickets/{ => archive}/T-4351/ticket.md             |     0
 tickets/{ => archive}/T-4352/ticket.md             |     0
 tickets/{ => archive}/T-4353/done-report.md        |     0
 tickets/{ => archive}/T-4353/ticket.md             |     0
 tickets/{ => archive}/T-4354/done-report.md        |     0
 tickets/{ => archive}/T-4354/ticket.md             |     0
 tickets/{ => archive}/T-4356/done-report.md        |     0
 tickets/{ => archive}/T-4356/ticket.md             |     0
 tickets/{ => archive}/T-4358/done-report.md        |     0
 tickets/{ => archive}/T-4358/ticket.md             |     0
 tickets/{ => archive}/T-4359/done-report.md        |     0
 tickets/{ => archive}/T-4359/ticket.md             |     0
 tickets/{ => archive}/T-4360/done-report.md        |     0
 tickets/{ => archive}/T-4360/measurement-notes.md  |     0
 tickets/{ => archive}/T-4360/ticket.md             |     0
 tickets/{ => archive}/T-4361/done-report.md        |     0
 tickets/{ => archive}/T-4361/ticket.md             |     0
 tickets/{ => archive}/T-4362/done-report.md        |     0
 tickets/{ => archive}/T-4362/ticket.md             |    10 +-
 tickets/{ => archive}/T-4365/done-report.md        |     0
 tickets/{ => archive}/T-4365/ticket.md             |     6 +-
 tickets/{ => archive}/T-4366/done-report.md        |     0
 tickets/{ => archive}/T-4366/ticket.md             |     0
 tickets/{ => archive}/T-4367/ticket.md             |     0
 tickets/{ => archive}/T-4368/done-report.md        |     0
 tickets/{ => archive}/T-4368/ticket.md             |     0
 tickets/{ => archive}/T-4369/done-report.md        |     0
 tickets/{ => archive}/T-4369/ticket.md             |     0
 tickets/{ => archive}/T-4372/done-report.md        |     0
 tickets/{ => archive}/T-4372/ticket.md             |     0
 tickets/{ => archive}/T-4373/done-report.md        |     0
 tickets/{ => archive}/T-4373/ticket.md             |     0
 tickets/{ => archive}/T-4374/done-report.md        |     0
 tickets/{ => archive}/T-4374/ticket.md             |     0
 tickets/{ => archive}/T-4376/ticket.md             |     0
 tickets/{ => archive}/T-4377/done-report.md        |     0
 tickets/{ => archive}/T-4377/ticket.md             |     0
 tickets/{ => archive}/T-4378/done-report.md        |     0
 tickets/{ => archive}/T-4378/ticket.md             |     0
 tickets/archive/T-4379/done-report.md              |  2254 ++
 tickets/{ => archive}/T-4379/ticket.md             |     5 +-
 tickets/{ => archive}/T-4380/done-report.md        |     0
 tickets/{ => archive}/T-4380/ticket.md             |     0
 tickets/{ => archive}/T-4381/done-report.md        |     0
 tickets/{ => archive}/T-4381/ticket.md             |     0
 tickets/{ => archive}/T-4382/done-report.md        |     0
 tickets/{ => archive}/T-4382/ticket.md             |     0
 tickets/{ => archive}/T-4386/done-report.md        |     0
 tickets/{ => archive}/T-4386/ticket.md             |     0
 tickets/{ => archive}/T-4387/done-report.md        |     0
 tickets/{ => archive}/T-4387/ticket.md             |     0
 tickets/{ => archive}/T-4388/done-report.md        |     0
 tickets/{ => archive}/T-4388/ticket.md             |     0
 tickets/{ => archive}/T-4390/done-report.md        |     0
 tickets/{ => archive}/T-4390/ticket.md             |     0
 tickets/{ => archive}/T-4391/done-report.md        |     0
 tickets/{ => archive}/T-4391/ticket.md             |     0
 tickets/{ => archive}/T-4392/done-report.md        |     0
 tickets/{ => archive}/T-4392/ticket.md             |    11 +-
 tickets/{ => archive}/T-4393/done-report.md        |     0
 tickets/{ => archive}/T-4393/ticket.md             |     0
 tickets/{ => archive}/T-4394/done-report.md        |     0
 tickets/{ => archive}/T-4394/ticket.md             |     0
 tickets/{ => archive}/T-4396/done-report.md        |     0
 tickets/{ => archive}/T-4396/ticket.md             |     0
 tickets/{ => archive}/T-4397/done-report.md        |     0
 tickets/{ => archive}/T-4397/ticket.md             |     0
 tickets/{ => archive}/T-4399/done-report.md        |     0
 tickets/{ => archive}/T-4399/ticket.md             |     0
 tickets/{ => archive}/T-4401/done-report.md        |     0
 tickets/{ => archive}/T-4401/ticket.md             |     0
 tickets/{ => archive}/T-4402/done-report.md        |     0
 tickets/{ => archive}/T-4402/ticket.md             |     0
 tickets/{ => archive}/T-4403/ticket.md             |     0
 tickets/{ => archive}/T-4404/done-report.md        |     0
 tickets/{ => archive}/T-4404/ticket.md             |     0
 tickets/{ => archive}/T-4405/ticket.md             |     0
 tickets/{ => archive}/T-4406/done-report.md        |     0
 tickets/{ => archive}/T-4406/ticket.md             |     0
 tickets/{ => archive}/T-4407/done-report.md        |     0
 tickets/{ => archive}/T-4407/ticket.md             |     0
 tickets/{ => archive}/T-4408/done-report.md        |     0
 tickets/{ => archive}/T-4408/ticket.md             |     0
 tickets/{ => archive}/T-4409/done-report.md        |     0
 tickets/{ => archive}/T-4409/ticket.md             |     0
 tickets/{ => archive}/T-4411/done-report.md        |     0
 tickets/{ => archive}/T-4411/ticket.md             |     0
 tickets/{ => archive}/T-4412/done-report.md        |     0
 tickets/{ => archive}/T-4412/ticket.md             |     0
 tickets/archive/T-4413/done-report.md              |    71 +
 tickets/archive/T-4413/ticket.md                   |   108 +
 tickets/archive/T-4414/done-report.md              |    21 +
 tickets/{ => archive}/T-4414/ticket.md             |    23 +-
 tickets/archive/T-4415/done-report.md              |    25 +
 tickets/{ => archive}/T-4415/ticket.md             |    24 +-
 tickets/archive/T-4416/done-report.md              |   980 +
 tickets/archive/T-4416/ticket.md                   |   122 +
 tickets/{ => archive}/T-4417/done-report.md        |     0
 tickets/{ => archive}/T-4417/ticket.md             |     0
 tickets/archive/T-4419/done-report.md              |  2345 ++
 tickets/archive/T-4419/ticket.md                   |   259 +
 tickets/archive/T-4421/done-report.md              |  2337 ++
 tickets/archive/T-4421/ticket.md                   |   505 +
 tickets/{ => archive}/T-4424/done-report.md        |     0
 tickets/{ => archive}/T-4424/ticket.md             |     0
 tickets/{ => archive}/T-4425/done-report.md        |     0
 tickets/{ => archive}/T-4425/ticket.md             |     0
 tickets/{ => archive}/T-4426/done-report.md        |     0
 tickets/{ => archive}/T-4426/ticket.md             |     0
 tickets/{ => archive}/T-4427/done-report.md        |     0
 tickets/{ => archive}/T-4427/ticket.md             |     0
 tickets/{ => archive}/T-4428/done-report.md        |     0
 tickets/{ => archive}/T-4428/ticket.md             |     0
 tickets/{ => archive}/T-4429/done-report.md        |     0
 tickets/{ => archive}/T-4429/ticket.md             |     0
 tickets/{ => archive}/T-4430/done-report.md        |     0
 tickets/{ => archive}/T-4430/ticket.md             |     0
 tickets/{ => archive}/T-4431/done-report.md        |     0
 tickets/{ => archive}/T-4431/ticket.md             |     0
 tickets/{ => archive}/T-4434/done-report.md        |     0
 tickets/{ => archive}/T-4434/ticket.md             |     0
 tickets/{ => archive}/T-4435/done-report.md        |     0
 tickets/{ => archive}/T-4435/ticket.md             |     0
 tickets/{ => archive}/T-4436/done-report.md        |     0
 tickets/{ => archive}/T-4436/ticket.md             |     0
 tickets/{ => archive}/T-4438/ticket.md             |     7 +-
 tickets/{ => archive}/T-4442/done-report.md        |     0
 tickets/{ => archive}/T-4442/ticket.md             |     0
 tickets/{ => archive}/T-4443/done-report.md        |     0
 tickets/{ => archive}/T-4443/ticket.md             |     0
 tickets/{ => archive}/T-4444/ticket.md             |     0
 tickets/{ => archive}/T-4445/done-report.md        |     0
 tickets/{ => archive}/T-4445/ticket.md             |     0
 tickets/{ => archive}/T-4446/done-report.md        |     0
 tickets/{ => archive}/T-4446/ticket.md             |     0
 tickets/{ => archive}/T-4447/done-report.md        |     0
 tickets/{ => archive}/T-4447/ticket.md             |    34 +-
 tickets/{ => archive}/T-4448/done-report.md        |     0
 tickets/{ => archive}/T-4448/ticket.md             |     0
 tickets/{ => archive}/T-4449/done-report.md        |     0
 tickets/{ => archive}/T-4449/ticket.md             |     0
 tickets/{ => archive}/T-4450/done-report.md        |     0
 tickets/{ => archive}/T-4450/ticket.md             |     0
 tickets/{ => archive}/T-4452/done-report.md        |     0
 tickets/{ => archive}/T-4452/ticket.md             |     0
 tickets/{ => archive}/T-4453/done-report.md        |     0
 tickets/{ => archive}/T-4453/ticket.md             |     0
 tickets/{ => archive}/T-4454/done-report.md        |     0
 tickets/{ => archive}/T-4454/ticket.md             |     0
 tickets/{ => archive}/T-4455/done-report.md        |     0
 tickets/{ => archive}/T-4455/ticket.md             |     0
 tickets/{ => archive}/T-4456/done-report.md        |     0
 tickets/{ => archive}/T-4456/ticket.md             |     0
 tickets/{ => archive}/T-4457/done-report.md        |     0
 tickets/{ => archive}/T-4457/ticket.md             |     0
 tickets/{ => archive}/T-4458/done-report.md        |     0
 tickets/{ => archive}/T-4458/ticket.md             |     0
 tickets/{ => archive}/T-4459/done-report.md        |     0
 tickets/{ => archive}/T-4459/ticket.md             |     0
 tickets/{ => archive}/T-4460/done-report.md        |     0
 tickets/{ => archive}/T-4460/ticket.md             |     0
 tickets/{ => archive}/T-4461/done-report.md        |     0
 tickets/{ => archive}/T-4461/ticket.md             |     0
 tickets/{ => archive}/T-4462/done-report.md        |     0
 tickets/{ => archive}/T-4462/ticket.md             |     0
 tickets/{ => archive}/T-4463/done-report.md        |     0
 tickets/{ => archive}/T-4463/ticket.md             |     0
 tickets/{ => archive}/T-4464/done-report.md        |     0
 tickets/{ => archive}/T-4464/ticket.md             |     0
 tickets/{ => archive}/T-4465/done-report.md        |     0
 tickets/{ => archive}/T-4465/ticket.md             |     0
 tickets/{ => archive}/T-4469/ticket.md             |     7 +-
 tickets/{ => archive}/T-4470/done-report.md        |     0
 tickets/{ => archive}/T-4470/ticket.md             |     0
 tickets/{ => archive}/T-4471/ticket.md             |     7 +-
 tickets/{ => archive}/T-4472/done-report.md        |     0
 tickets/{ => archive}/T-4472/ticket.md             |     0
 tickets/{ => archive}/T-4473/done-report.md        |     0
 tickets/{ => archive}/T-4473/ticket.md             |    18 +-
 tickets/{ => archive}/T-4474/done-report.md        |     0
 tickets/{ => archive}/T-4474/ticket.md             |     0
 tickets/{ => archive}/T-4475/done-report.md        |     0
 tickets/{ => archive}/T-4475/ticket.md             |     0
 tickets/{ => archive}/T-4476/done-report.md        |     0
 tickets/{ => archive}/T-4476/ticket.md             |     0
 tickets/{ => archive}/T-4477/done-report.md        |     0
 tickets/{ => archive}/T-4477/ticket.md             |     0
 tickets/{ => archive}/T-4478/done-report.md        |     0
 tickets/{ => archive}/T-4478/ticket.md             |     0
 tickets/{ => archive}/T-4479/done-report.md        |     0
 tickets/{ => archive}/T-4479/ticket.md             |     0
 tickets/{ => archive}/T-4480/done-report.md        |     0
 tickets/{ => archive}/T-4480/ticket.md             |     0
 tickets/{ => archive}/T-4481/done-report.md        |     0
 tickets/{ => archive}/T-4481/ticket.md             |     0
 tickets/{ => archive}/T-4482/done-report.md        |     0
 tickets/{ => archive}/T-4482/ticket.md             |     0
 tickets/{ => archive}/T-4483/done-report.md        |     0
 tickets/{ => archive}/T-4483/ticket.md             |     0
 tickets/{ => archive}/T-4485/done-report.md        |     0
 tickets/{ => archive}/T-4485/ticket.md             |     0
 tickets/archive/T-4491/done-report.md              |    23 +
 tickets/archive/T-4491/ticket.md                   |    69 +
 tickets/archive/T-4492/done-report.md              |    34 +
 tickets/archive/T-4492/ticket.md                   |    67 +
 tickets/archive/T-4493/done-report.md              |    19 +
 tickets/archive/T-4493/ticket.md                   |    61 +
 tickets/archive/T-4494/done-report.md              |   138 +
 tickets/archive/T-4494/ticket.md                   |    73 +
 tickets/archive/T-4495/done-report.md              |   197 +
 tickets/archive/T-4495/ticket.md                   |    64 +
 tickets/archive/T-4496/done-report.md              |    23 +
 tickets/archive/T-4496/ticket.md                   |    56 +
 tickets/archive/T-4498/done-report.md              |   147 +
 tickets/archive/T-4498/ticket.md                   |    55 +
 tickets/archive/T-4499/ticket.md                   |    52 +
 tickets/archive/T-4501/done-report.md              |    24 +
 tickets/archive/T-4501/ticket.md                   |    81 +
 tickets/archive/T-4502/done-report.md              |    19 +
 tickets/archive/T-4502/ticket.md                   |    73 +
 tickets/archive/T-4503/done-report.md              |   592 +
 tickets/archive/T-4503/ticket.md                   |    94 +
 tickets/archive/T-4505/ticket.md                   |    38 +
 tickets/archive/T-4507/done-report.md              |   793 +
 tickets/archive/T-4507/ticket.md                   |    57 +
 tickets/archive/T-4508/done-report.md              |   689 +
 tickets/archive/T-4508/ticket.md                   |   114 +
 tickets/archive/T-4510/done-report.md              |   149 +
 tickets/archive/T-4510/ticket.md                   |    81 +
 tickets/archive/T-4511/done-report.md              |    97 +
 tickets/archive/T-4511/ticket.md                   |   103 +
 tickets/archive/T-4512/done-report.md              |   524 +
 tickets/archive/T-4512/ticket.md                   |   102 +
 tickets/archive/T-4514/done-report.md              |   179 +
 tickets/archive/T-4514/ticket.md                   |   169 +
 tickets/archive/T-4515/done-report.md              |    24 +
 tickets/archive/T-4515/ticket.md                   |    62 +
 tickets/archive/T-4517/done-report.md              |   180 +
 tickets/archive/T-4517/ticket.md                   |    94 +
 tickets/archive/T-4519/done-report.md              |   869 +
 tickets/archive/T-4519/ticket.md                   |    79 +
 tickets/archive/T-4520/done-report.md              |   163 +
 tickets/archive/T-4520/ticket.md                   |    58 +
 tickets/archive/T-4521/done-report.md              |   228 +
 tickets/archive/T-4521/ticket.md                   |   149 +
 tickets/archive/T-4522/done-report.md              |    99 +
 tickets/archive/T-4522/ticket.md                   |    49 +
 tickets/archive/T-4523/done-report.md              |   104 +
 tickets/archive/T-4523/ticket.md                   |    40 +
 tickets/archive/T-4524/done-report.md              |   209 +
 tickets/archive/T-4524/ticket.md                   |    52 +
 tickets/archive/T-4526/ticket.md                   |    45 +
 tickets/archive/T-4529/ticket.md                   |    76 +
 tickets/archive/T-4531/done-report.md              |    21 +
 tickets/archive/T-4531/ticket.md                   |   110 +
 tickets/archive/T-4532/done-report.md              |    24 +
 tickets/archive/T-4532/ticket.md                   |    66 +
 tickets/archive/T-4534/ticket.md                   |    69 +
 tickets/archive/T-4535/done-report.md              |    64 +
 tickets/archive/T-4535/ticket.md                   |    61 +
 tickets/archive/T-4536/done-report.md              |    78 +
 tickets/archive/T-4536/ticket.md                   |   165 +
 tickets/archive/T-4537/ticket.md                   |    33 +
 tickets/archive/T-4538/ticket.md                   |    63 +
 tickets/{T-3802 => archive/T-4539}/ticket.md       |    19 +-
 tickets/archive/T-4540/done-report.md              |   543 +
 tickets/archive/T-4540/ticket.md                   |    55 +
 tickets/archive/T-4542/ticket.md                   |    58 +
 tickets/archive/T-4543/done-report.md              |   115 +
 tickets/archive/T-4543/ticket.md                   |    79 +
 tickets/archive/T-4546/done-report.md              |  1212 +
 tickets/archive/T-4546/ticket.md                   |   101 +
 tickets/archive/T-4547/done-report.md              |   137 +
 tickets/archive/T-4547/ticket.md                   |    45 +
 tickets/archive/T-4548/done-report.md              |    59 +
 tickets/archive/T-4548/ticket.md                   |    50 +
 tickets/archive/T-4549/ticket.md                   |    53 +
 tickets/archive/T-4550/done-report.md              |   545 +
 tickets/archive/T-4550/ticket.md                   |    59 +
 tickets/archive/T-4552/done-report.md              |   146 +
 tickets/archive/T-4552/ticket.md                   |   100 +
 tickets/archive/T-4553/done-report.md              |   501 +
 tickets/archive/T-4553/ticket.md                   |    55 +
 tickets/archive/T-4554/done-report.md              |   541 +
 tickets/archive/T-4554/ticket.md                   |   166 +
 tickets/archive/T-4555/done-report.md              |   556 +
 tickets/archive/T-4555/ticket.md                   |    78 +
 tickets/archive/T-4556/done-report.md              |   602 +
 tickets/archive/T-4556/ticket.md                   |    46 +
 tickets/archive/T-4559/ticket.md                   |    57 +
 tickets/archive/T-4562/done-report.md              |   665 +
 tickets/archive/T-4562/ticket.md                   |    54 +
 tickets/archive/T-4563/done-report.md              |   556 +
 tickets/archive/T-4563/ticket.md                   |    47 +
 tickets/archive/T-4566/ticket.md                   |   157 +
 tickets/archive/T-4572/done-report.md              |   972 +
 tickets/archive/T-4572/ticket.md                   |    73 +
 tickets/archive/T-4579/done-report.md              |   522 +
 tickets/archive/T-4579/ticket.md                   |    68 +
 tickets/archive/T-4582/done-report.md              |   551 +
 tickets/archive/T-4582/ticket.md                   |    56 +
 tickets/archive/T-4583/done-report.md              |   620 +
 tickets/archive/T-4583/ticket.md                   |    87 +
 tickets/archive/T-4588/done-report.md              |   715 +
 tickets/archive/T-4588/ticket.md                   |    67 +
 tickets/archive/T-4589/ticket.md                   |    56 +
 tickets/archive/T-4596/done-report.md              |   640 +
 tickets/archive/T-4596/ticket.md                   |    43 +
 tickets/archive/T-4597/ticket.md                   |    34 +
 tickets/archive/T-4602/ticket.md                   |    44 +
 tickets/archive/T-4607/done-report.md              |   803 +
 tickets/archive/T-4607/ticket.md                   |    96 +
 tickets/archive/T-4615/ticket.md                   |   107 +
 tickets/archive/T-4616/ticket.md                   |    52 +
 tickets/archive/T-4618/ticket.md                   |    61 +
 tickets/archive/T-4619/ticket.md                   |    73 +
 tickets/archive/T-4620/ticket.md                   |    61 +
 tickets/archive/T-4622/ticket.md                   |   107 +
 tickets/archive/T-4623/done-report.md              |  2348 ++
 tickets/archive/T-4623/ticket.md                   |    69 +
 tickets/archive/T-4624/done-report.md              |  2322 ++
 tickets/archive/T-4624/ticket.md                   |    55 +
 tickets/archive/T-4625/done-report.md              |  2221 ++
 tickets/archive/T-4625/ticket.md                   |    46 +
 tickets/archive/T-4627/done-report.md              |  2243 ++
 tickets/archive/T-4627/ticket.md                   |    55 +
 tickets/archive/T-4628/done-report.md              |  1530 ++
 tickets/archive/T-4628/ticket.md                   |    58 +
 tickets/archive/T-4629/done-report.md              |  1550 ++
 tickets/archive/T-4629/ticket.md                   |    49 +
 tickets/archive/T-4630/done-report.md              |  1508 ++
 tickets/archive/T-4630/ticket.md                   |    59 +
 tickets/archive/T-4631/done-report.md              |  1577 ++
 tickets/archive/T-4631/ticket.md                   |    74 +
 tickets/archive/T-4632/done-report.md              |  1478 ++
 tickets/archive/T-4632/ticket.md                   |    46 +
 tickets/archive/T-4633/done-report.md              |   743 +
 tickets/archive/T-4633/ticket.md                   |    86 +
 tickets/archive/T-4634/done-report.md              |   851 +
 tickets/archive/T-4634/ticket.md                   |    97 +
 tickets/archive/T-4635/ticket.md                   |    30 +
 tickets/archive/T-4642/done-report.md              |   671 +
 tickets/archive/T-4642/ticket.md                   |    52 +
 tickets/archive/T-4646/done-report.md              |   914 +
 tickets/archive/T-4646/ticket.md                   |    82 +
 tickets/archive/T-4649/done-report.md              |   888 +
 tickets/archive/T-4649/ticket.md                   |   105 +
 tickets/archive/T-4650/done-report.md              |   961 +
 tickets/archive/T-4650/ticket.md                   |   166 +
 tickets/archive/T-4659/done-report.md              |   962 +
 tickets/archive/T-4659/ticket.md                   |    92 +
 tickets/archive/T-4660/done-report.md              |  1376 ++
 tickets/archive/T-4660/ticket.md                   |    68 +
 tickets/archive/T-4669/done-report.md              |  1464 ++
 tickets/archive/T-4669/ticket.md                   |    98 +
 tickets/archive/T-4673/done-report.md              |  1447 ++
 tickets/archive/T-4673/ticket.md                   |    88 +
 tickets/archive/T-4675/done-report.md              |  2275 ++
 tickets/archive/T-4675/ticket.md                   |   116 +
 tickets/archive/T-4677/done-report.md              |    40 +
 tickets/archive/T-4677/ticket.md                   |   173 +
 tickets/archive/T-4678/done-report.md              |    48 +
 tickets/archive/T-4678/ticket.md                   |   201 +
 tickets/archive/T-4680/done-report.md              |    55 +
 tickets/archive/T-4680/ticket.md                   |   211 +
 tickets/archive/T-4684/done-report.md              |   909 +
 tickets/archive/T-4684/ticket.md                   |    65 +
 tickets/archive/T-4688/done-report.md              |  1048 +
 tickets/archive/T-4688/ticket.md                   |   162 +
 tickets/archive/T-4689/done-report.md              |  1029 +
 tickets/archive/T-4689/ticket.md                   |   114 +
 tickets/archive/T-4709/done-report.md              |  2621 +++
 tickets/archive/T-4709/ticket.md                   |   182 +
 tickets/archive/T-4715/done-report.md              |  2544 +++
 tickets/archive/T-4715/ticket.md                   |   194 +
 tickets/archive/T-4718/done-report.md              |  2656 +++
 tickets/archive/T-4718/ticket.md                   |   182 +
 tickets/archive/T-4719/done-report.md              |  2501 ++
 tickets/archive/T-4719/ticket.md                   |   209 +
 tickets/archive/T-4722/done-report.md              |  2383 ++
 tickets/archive/T-4722/ticket.md                   |   183 +
 tickets/archive/T-4723/done-report.md              |  2537 +++
 tickets/archive/T-4723/ticket.md                   |   210 +
 tickets/archive/T-4764/done-report.md              |  2504 ++
 tickets/archive/T-4764/ticket.md                   |    85 +
 tickets/archive/T-4767/done-report.md              |  2414 ++
 tickets/archive/T-4767/ticket.md                   |   184 +
 tickets/archive/T-4770/done-report.md              |  2562 +++
 tickets/archive/T-4770/ticket.md                   |   176 +
 tickets/archive/T-4805/done-report.md              |  1159 +
 tickets/archive/T-4805/ticket.md                   |   123 +
 tickets/archive/T-4806/done-report.md              |  1285 ++
 tickets/archive/T-4806/ticket.md                   |    64 +
 tickets/archive/T-4911/done-report.md              |  2610 +++
 tickets/archive/T-4911/ticket.md                   |   123 +
 tickets/archive/T-4913/done-report.md              |  2457 ++
 tickets/archive/T-4913/ticket.md                   |    37 +
 tickets/archive/T-4952/done-report.md              |  2518 +++
 tickets/archive/T-4952/ticket.md                   |   122 +
 tickets/archive/T-4953/done-report.md              |  2509 ++
 tickets/archive/T-4953/ticket.md                   |    47 +
 tickets/archive/T-5036/done-report.md              |  1432 ++
 tickets/archive/T-5036/ticket.md                   |    50 +
 tickets/archive/T-5075/done-report.md              |  1516 ++
 tickets/archive/T-5075/ticket.md                   |   104 +
 tickets/archive/T-5082/done-report.md              |    38 +
 tickets/archive/T-5082/ticket.md                   |   345 +
 tickets/archive/T-5083/ticket.md                   |    90 +
 uv.lock                                            |   265 +-
 4412 files changed, 763908 insertions(+), 23540 deletions(-)
```

### Evidence
- `tests/unit/test_land_cas_ledger_retry.py::TestLedgerOnlyAdvance::test_pure_ledger_advance_is_ledger_only` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cas_ledger_retry.py::TestLedgerOnlyAdvance::test_a_single_code_touching_commit_is_not_ledger_only` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cas_ledger_retry.py::TestRebaseComposedCommitOnto::test_rebased_commit_carries_the_same_content_change` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cas_ledger_retry.py::TestRebaseComposedCommitOnto::test_rebase_failure_returns_err` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_ledger_only_cas_miss_rebases_and_retries_without_regates` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_code_touching_cas_miss_falls_back_to_full_recompose` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_refused_land_leaves_root_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_dev_advances_by_ledger_only_commit_between_compose_and_publish_lands` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cas_ledger_retry.py::TestAttemptLedgerOnlyRebase::test_ledger_only_apply_conflict_is_retryable_not_a_hard_refusal` (pytest node id, verified passing when recorded)
