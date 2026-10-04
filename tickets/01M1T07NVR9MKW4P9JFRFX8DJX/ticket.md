+++
id = "01M1T07NVR9MKW4P9JFRFX8DJX"
title = "known-dangerous-comparison-idiom rule (substring vs prefix)"
type = "security"
category = "triage"
priority = "low"
parent = "01M1QDTYTRW714S858S0TP6YWM"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-04T21:04:50Z"
aliases = ["T-3960"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/gates/_cve_fingerprint_scan.py"]

[[acceptance]]
text = "given a substring-containment check applied to a request-path, route, or identity-like variable, when frob check runs, then the new rule fires with a suggestion to use a prefix/exact/segment match"
bound = false

[[acceptance]]
text = "given a genuine substring search over free text (not a path/identity value), when frob check runs, then the rule stays quiet"
bound = false
+++

Convergence 5 of T-3928 (backend audit item 10 + threat-model item 5, arrived independently -- both call it cheap). Also T-3919 item 10 and T-3920 item 5 in those epics' own numbering; do NOT file separately there, cite this one. FINDING THIS WOULD HAVE CAUGHT: semantic authorization bugs from a substring test used where a prefix/exact check was needed -- e.g. a route-path or identity check using containment or startswith with the wrong operand order instead of a real path-segment or exact match, which is out of [[policy.pattern]] reach today (policy.pattern is a syntactic pattern surface, not a semantic-comparison-shape one). Proposed rule kind: a known-dangerous-comparison-idiom lint, structurally similar to the existing CVE-fingerprint scan (frob.strata._cve_fingerprint.CVE_FINGERPRINTS plus this gate's file) but for comparison-idiom needles rather than CVE needles -- e.g. flag substring containment used against a request path, route, or identity value where a prefix/exact/segment match is the security-relevant semantics. A small, cheap lexical/AST pattern lint per both auditors.


Item 2. Same rule as T-3960 (T-3928's convergence 5, dangerous-comparison-idiom, already filed) -- this is the THIRD independent arrival of the same ask (backend audit item 10, threat-model item 5, now here), the strongest corroboration any item in these six epics has had. Do NOT file a second ticket; this body is attached to T-3960 as an update rather than a new child (see append below) -- filed here only as a pointer for T-4025's own bookkeeping.

TRIGGER SET MEASURED AGAINST src/frob/ BEFORE FILING, per the epic's own requirement: an AST scan (not a text grep) over every src/frob/**/*.py function named to*/is_*/normalize*/check_* (114 candidate functions), looking for (a) an `in`/`not in` comparison where either side is a Name/Attribute whose name matches url/host/domain/path/hostname/origin/referer, or (b) a `.replace(...)` call whose receiver matches the same pattern. frob ships no TS/JS source of its own (it processes other languages' source but has none itself), so the `.includes()` half of the trigger set has no applicable surface here.

RESULT: 1 syntactic hit -- src/frob/arch/_logging_checks.py::check_print_as_diagnostic line 271, `marker in path_lower`. ON INSPECTION THIS IS NOT A SECURITY INSTANCE: it is an internal check of whether a repo-relative file path contains one of a small set of CLI-output directory markers, used to decide whether a bare print() is exempt from a logging-discipline lint -- not an authorization or trust decision over an untrusted URL/host/path. So the precise trigger set finds EFFECTIVELY ZERO live instances in frob's own Python code today.

WHAT THIS DOES AND DOES NOT CHANGE: it does NOT mean frob is clean of this bug CLASS -- the queue's own 9-instance lexical-hook tally (most recently T-4015, a ticket-id regex with no left boundary) is real and ongoing, but that class is boundary-less pattern matching in general, a broader shape than this specific url/host/path-receiver-plus-naming-convention trigger. The narrow trigger the consumer proposes did not fire here. Priority for the underlying rule (T-3960) stands on its THREE independent cross-repo/cross-language arrivals regardless of this repo's own scan result; it is not elevated further by a positive hit here, because there was none.
