## Done report

Sampled the current DOC006 warning set (frob check --only docblocks --json,
131 findings across ~45 doc files: 62 config reference / 30 file-path / 20
code symbol / 9 cli invocation / 13 doc-anchor after re-measure). Classified
and disposed of every one:

1. Matcher hardening (src/frob/gates/_docptr.py), three new false-positive
   classes found while triaging, each with a new regression test in
   tests/test_docptr_gate.py:
   - ALL-CAPS bracket tokens (`[IN-REPO]`) are prose citation tags, never a
     `[section]` TOML pointer -- rejected before the manifest-lookup path
     (_ALL_CAPS_TAG_RE).
   - `_DECLARED_BUT_UNSET_CONFIG_SECTIONS`: a curated, individually-verified
     allowlist of frob.toml sections this codebase's own loaders genuinely
     read (vet/vet.allow/vet.detectors, policy + its 3 rule kinds, strata +
     benign_capabilities, tickets, check, system, perf.heavy/sketch, fuzz,
     clean, tool.frob, repo) that happen not to be populated in THIS
     project's own frob.toml/pyproject.toml (frob does not need to
     configure vet/policy/etc. on itself).
   - CODE SYMBOL: a `module.Class.attr`-shaped chain one level deeper than
     the resolver proves/refutes now also credits a class RE-EXPORTED
     (not locally defined) by the outer module's __init__.py, via the
     existing _module_reexports helper; and an `X.__init__.name`-shaped
     four-part chain (a doc author spelling out a package's own
     __init__.py explicitly) now strips the `.__init__` suffix and
     re-resolves against the bare module, since `X.__init__` and `X` name
     the same module.
2. Fixed genuinely stale doc pointers: renamed/underscore-prefixed Python
   symbols (_exact_regions, _check_cmpl_registry_unit_dispositions,
   _leaf_tokens, _parse_playbook_sections, _scan_file_fingerprints,
   _walk_repo_files, frob.logging.formatter._FrobFormatter), a wrong CLI
   name (`frob reconcile` -> `frob ticket reconcile`, `frob sys check` ->
   `frob sys audit`), moved doc anchors (recomputed via
   frob.graph.dsl.slugify against each target heading), a wrong path
   prefix (agents/skills -> .claude/agents/.claude/skills), and one
   wording fix where a doc claimed a `[testing.select]` frob.toml table
   that was never real (it is SelectConfig.fallback / a CLI flag).
3. Waived the remainder as genuinely illustrative/external/future-facing
   with a specific inline reason each: hypothetical repro filenames in
   audit docs, third-party package/tool paths (gitleaks, cryptography,
   pygments, the Linux kernel docs, the NVD API), scaffold-generated
   downstream-repo files, not-yet-built CLI flags/subcommands already
   disclosed as such in the same sentence, and one module-level
   `Literal[...]` type-alias (ArchCategory) that is real but not yet
   graph-indexed as a symbol -- filed as T-draft-208a291f (out of this
   ticket's scope: src/frob/graph/**) rather than fixed here.

Residue (no ticket needed: CHANGELOG.md is permanently land-owned, never
fixable in any worktree): DOC006 measures 4 remaining findings, all inside CHANGELOG.md,
which a worktree agent cannot touch (land-owned per the agent playbook
section 4b) -- honest, ticketed-by-disclosure residue, not silently
dropped. In-scope (docs/**, src/frob/gates/_docptr.py,
tests/test_docptr_gate.py) DOC006 is 0.

Mid-ticket incident: after committing this ticket's changes, the
deletion-filter check (git diff main --diff-filter=D) surfaced a large
stale-tickets.md revert (T-0662 and ~9 other tickets reverted from
done/planned back to queued, evidence/Done-report content stripped) --
main had advanced with several other agents' lands since this worktree's
last merge. Recovered per the playbook's section 10b recipe: `git
checkout main -- tickets.md`, reapplied only this ticket's own content
edit (the tickets.md daemon-proposal DOC006 waive) and re-filed the
draft ticket via the CLI, then redid T-1016's own evidence/sweep through
the CLI rather than hand-editing the ledger.

### Changed
```
 docs/audits/check-performance.md                   |   2 +-
 docs/audits/graph.md                               |   2 +-
 docs/audits/lang-check-docs.md                     |   2 +-
 docs/audits/perf.md                                |   2 +-
 docs/audits/strata.md                              |   2 +-
 docs/audits/tickets-testing-round2.md              |   4 +-
 docs/audits/tickets-testing.md                     |   2 +-
 docs/audits/vet.md                                 |   2 +-
 docs/commands/deploy.md                            |   2 +-
 docs/commands/scaffold.md                          |   2 +-
 docs/design/language-adapter-tier-decision.md      |   5 +-
 docs/design/secrets-pii-corpus.md                  |   6 +-
 docs/design/system-design-corpus.md                |   2 +-
 docs/guides/agentic-time-profiling.md              |   4 +-
 docs/guides/exhaustive-research.md                 |   4 +-
 docs/guides/extending/dup-detector-registry.md     |   2 +-
 docs/guides/extending/language-grammar-handlers.md |   2 +-
 docs/guides/extending/prover-claim-kinds.md        |   6 +-
 docs/guides/extending/sys-export-formats.md        |   2 +-
 docs/guides/install.md                             |   4 +-
 docs/guides/quickstart.md                          |   2 +-
 docs/guides/worktree-pool.md                       |   2 +-
 docs/modules/arch.md                               |   2 +-
 docs/modules/clean.md                              |   2 +-
 docs/modules/decisions.md                          |   2 +-
 docs/modules/dup-sota-survey.md                    |   2 +-
 docs/modules/dup.md                                |   4 +-
 docs/modules/fuzz.md                               |   4 +-
 docs/modules/gates.md                              |  10 +-
 docs/modules/mutate.md                             |   2 +-
 docs/modules/perf.md                               |   4 +-
 docs/modules/serve.md                              |   4 +-
 docs/modules/stats.md                              |   2 +-
 docs/modules/testing.md                            |   9 +-
 docs/modules/tickets.md                            |   2 +-
 docs/modules/vet.md                                |   8 +-
 docs/strata/host.md                                |   2 +-
 docs/strata/kernel.md                              |   2 +-
 docs/strata/krb.md                                 |   2 +-
 docs/strata/surface.md                             |   4 +-
 docs/strata/threat.md                              |   2 +-
 docs/strata/waive.md                               |   4 +-
 src/frob/gates/_docptr.py                          |  90 ++++++++++-
 tests/test_docptr_gate.py                          |  58 +++++++
 tickets.md                                         | 167 ++++++++++++++++++++-
 45 files changed, 378 insertions(+), 73 deletions(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc006Config::test_all_caps_citation_tag_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Config::test_declared_but_unset_section_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Symbol::test_reexported_class_attribute_chain_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Symbol::test_dunder_init_mid_chain_resolves_to_module` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 6075 warning(s), 339 waived
- error-findings: COV003@tickets/T-0698, DUP001@tests/test_docptr_gate.py, E501@/home/logan/projects/frob/.claude/worktrees/agent-a40e2aaf207a475ba/src/frob/gates/_docptr.py:576
