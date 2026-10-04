+++
id = "01M1T07NVYEXD9JQP1G82JF0MY"
title = "ENVVAR003: config constructed outside its designated site"
type = "security"
category = "triage"
priority = "low"
parent = "01M1QDTYV6Z35XFTPNT4QW70Y2"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-04T21:04:52Z"
aliases = ["T-3966"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/app/config.py"]

[[acceptance]]
text = "given a settings/config class instantiated directly outside its designated from_external/from_env construction site and outside test files, when frob check runs, then ENVVAR003 fires naming the construction site"
bound = false

[[acceptance]]
text = "given a construction call inside the designated site or a test file, when frob check runs, then the rule stays quiet"
bound = false
+++

F-182 (T-3942 item 8). Distinct from the first audit's ENVVAR002 (T-3919 item 8, filed separately: "every AppConfig field has a non-test reader"). This one is about CONSTRUCTION, not reading: a config field read off a LOCALLY-CONSTRUCTED default instance (e.g. `Settings()` built inline somewhere instead of the one true `from_external`/`from_env`-produced instance) is itself a finding, independent of whether the field is read anywhere.

WHY THIS MATTERS OUT OF PROPORTION TO ITS SIZE (the consumer's own framing): it SILENTLY DEFEATED A LANDED SECURITY FIX, and it passes BOTH the existing env-var sync gate and the first audit's proposed ENVVAR002 -- neither of those rules would have caught it, because both check that the field is documented/read somewhere, not that every live code path actually goes through the one construction site meant to apply real config.

FINDING THIS WOULD HAVE CAUGHT: a settings/config class instantiated directly (bare `Settings()` or equivalent) at a call site outside `from_external`/`from_env`/test fixtures, so a security-relevant default (rather than the real deployed value) silently governs behavior. Narrow and mechanical per the consumer: flag any construction of the settings/config class found outside its designated construction path(s) and test files. frob's own AppConfig/from_external (src/frob/app/config.py) is a reference shape for what "the one true construction site" looks like, useful as a positive-control fixture when building the detector, even though the rule itself targets consumer code shapes generically.
