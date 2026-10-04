+++
id = "01M1T07NY22Y9FS0JNYNJ6WT20"
title = "frob:tests kind=a11y obligation"
type = "task"
category = "triage"
priority = "low"
parent = "01M1T07NXSGQEK1JQ4XKQSJFAK"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-09-06T00:00:00Z"
aliases = ["T-4034"]
labels = ["milestone:1.1.0", "v1-cluster:B2", "area:crunk"]
scope = ["src/frob/graph/dsl.py"]

[[acceptance]]
text = "given kind=a11y is added to _TESTS_KINDS, when a frob:tests edge declares it, then the bound test must be verified to actually invoke an accessibility-scanning tool, not merely reference an aria-* class string"
bound = false

[[acceptance]]
text = "given the existing kind=property precedent, when this ticket designs the a11y binding rule, then it follows the same exercised-not-merely-referenced discipline"
bound = false
+++

Item 6. VERIFIED: git grep for a11y/axe-core/WCAG across src/frob found nothing. src/frob/graph/dsl.py's _TESTS_KINDS frozenset (currently {"unit", "integration", "e2e", "property"}) is the exact registry a new kind gets added to.

FINDING THIS WOULD HAVE CAUGHT: axe-core installed as a devDependency that nothing actually imports or runs -- so it exists on paper as a stated accessibility-testing tool with zero exercise -- and WCAG conformance modelled only as class-string constants (e.g. an aria-* class name literal) that frob can check for EXISTENCE (the string is present somewhere) but not EFFECT (does it actually satisfy the accessibility property it names). Frontend a11y has no obligation kind at all today: a frob:tests edge can claim kind="unit" or kind="e2e" for an a11y check, but nothing distinguishes "this test actually ran an accessibility scanner and asserted on its output" from an ordinary unit test that happens to touch aria attributes.

Proposed: add kind="a11y" to _TESTS_KINDS, with the same binding discipline as the other kinds (a frob:tests edge naming a test that must actually invoke an accessibility-scanning tool, not merely reference an aria-* class string) -- mirroring how kind="property" already requires exercising a property space rather than one example.
