# `frob.doctor` -- external-tool inventory and health

<!-- frob:doc docs/modules/doctor.md -->

`src/frob/doctor.py` is `frob doctor`'s own module: native-extension
presence, derived-state fingerprinting, and the external-tool inventory
`scan_external_tools`/`_EXTERNAL_TOOLS` drives. This page covers the one
section T-5762 added; the general REQUIRED/OPTIONAL/OPTIONAL_FOR_GATE/
REQUIRED_FOR_FAMILY tool-category mechanism itself is documented in
depth at docs/guides/install.md#required_for_family-tool-gating-t-5335.

## REQUIRED_FOR_FAMILY

<!-- frob:doc docs/modules/doctor.md#required_for_family -->

`ToolCategory.REQUIRED_FOR_FAMILY` (T-5335 owner directive) makes a
tool's absence a FAILING verdict only when a rule FAMILY's own
`relevant_when(root)` predicate is true for the target repo -- see
docs/guides/install.md#required_for_family-tool-gating-t-5335 for the
mechanism (`_FAMILY_TOOL_RELEVANCE`, `family_required_tool_findings`)
in full; this page documents only the entries this module registers.

### crunk (T-5762, frob leaf F-1 of the LAYOUT review gate story T-5747)

`crunk` is registered `REQUIRED_FOR_FAMILY` for the LAYOUT family the
same way `sqlfluff`/`squawk` are registered for the SQL family
(docs/modules/sql.md#required_for_family-tool-gating). Its relevance
predicate, `_gallery_org_buckets_relevance(root)`, is true only when
`<root>/crunk.toml` declares a `components` or `layouts` entry in its
`[org].buckets` list (crunk's own `OrgConfig.buckets`,
<!-- frob:waive DOC006 reason="cross-repo pointer: this path lives in the crunk repository, which owns the gallery manifest (T-5747 split)" -->`src/crunk/spec/models.py` in the crunk repo) -- a repo with no such
bucket declared has nothing for crunk's gallery pipeline to enumerate,
so crunk's absence is never reported.

This predicate reads `crunk.toml` as plain TOML (`tomllib`) rather than
importing crunk's own pydantic `OrgConfig` model: `frob.doctor` and
`frob.webapp` both stay leaf layers with zero crunk dependency, the same
posture `frob.webapp._gallery_schema` (T-5764,
docs/modules/webapp-layout.md) already takes for the vendored manifest
schema. Any read/parse failure (missing file, malformed TOML, missing
`[org]`/`buckets` keys) is treated as not-relevant, never raised --
matching `sql_relevance`'s own fail-soft discipline.

Positive control (this leaf's own acceptance criterion): a fixture repo
with a `crunk.toml` declaring `buckets = ["components"]` and no `crunk`
binary on `PATH` makes `scan_external_tools`/`family_required_tool_findings`
return a FAILING finding named `crunk`; removing the declared buckets
(or the file entirely) makes that finding disappear.
