---
id: T-0303
title: Per-repo BenignCapability declaration channel (graphite T-0017)
state: done
kind: feature
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_threat.py
- src/frob/strata/_errors.py
- src/frob/strata/__init__.py
- src/frob/app/sys_runner.py
- docs/strata/threat.md
- docs/guides/extending/benign-capabilities.md
- tests/unit/strata/test_threat.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_missing_frob_toml_is_ok_empty
- tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_missing_strata_table_is_ok_empty
- tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_declared_entry_is_loaded
- tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_missing_reason_is_malformed
- tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_blank_reason_is_malformed
- tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_unparseable_toml_is_malformed
- tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_repo_declared_excuse_resolves_threat002
designated_repro_test: null
acceptance:
- text: A repo can declare [[strata.benign_capabilities]] entries in frob.toml with
    kind+reason, merged with DEFAULT_BENIGN_CAPABILITIES by frob sys audit
  evidence: []
- text: A missing frob.toml or missing table is Ok(()); a malformed entry (missing
    kind/reason, blank reason, unparseable TOML) is Err(StrataError.MalformedBenignConfig)
  evidence: []
threat: null
component: null
---
graphite's frob-adoption sweep (its FROBLEMS.md/tickets T-0017) found THREAT002 fires for a repo's genuinely benign, non-tier-2 may capability kind (html_render/client_storage under a QUALITY_CATALOG-only view) with no excuse mechanism except patching frob's own DEFAULT_BENIGN_CAPABILITIES tuple. Adds a per-repo frob.toml [[strata.benign_capabilities]] array-of-tables channel, chosen over a .strata grammar addition because the excuse is repo configuration (which catalog gaps this repo accepts) not a claim about node behavior, matching [graph].exclude/[vet.allow]/[[policy.*]]'s existing register in frob.toml.