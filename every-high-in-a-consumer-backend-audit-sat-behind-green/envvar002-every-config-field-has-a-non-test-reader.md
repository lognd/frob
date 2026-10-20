+++
id = "01M1T07NW3YT3YM71W7Z53C7YQ"
title = "ENVVAR002: every config field has a non-test reader"
type = "security"
category = "todo"
priority = "low"
parent = "01M1QDTYTFZHQYMDHNFBSGQXJJ"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-04T22:22:21Z"
aliases = ["T-3971"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/app/config.py"]

[[acceptance]]
text = "given a config field with a schema/doc entry but no non-test read site anywhere in the codebase, when frob check runs, then ENVVAR002 fires naming the field"
bound = false

[[acceptance]]
text = "given a field read by at least one non-test call site, when frob check runs, then the rule stays quiet"
bound = false
+++

T-3919 item 8. Distinct from ENVVAR003 (T-3942 item 8, already filed as T-3966: flags construction of a config class outside its designated site). This one is about READING: every AppConfig-shaped field should have a non-test reader somewhere in the codebase. The existing three-way sync gate (env-var doc/schema/code sync) proves a field is DOCUMENTED, not that it DOES anything -- a field can be declared, synced across all three surfaces, and never actually consulted by any non-test code path.

FINDING THIS WOULD HAVE CAUGHT: a security-relevant config knob that exists on paper (documented, schema-validated) but is dead in practice because nothing reads it, so changing it has no effect -- the auditor's framing is that the existing sync gate creates false confidence here. Proposed: extend (or add alongside) the sync gate a check that every config field has at least one non-test read site, using the same reachability-style analysis already proven out for COV006/similar rules in this repo.
