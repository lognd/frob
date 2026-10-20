+++
id = "01M26W79A7P49AM654H5CVRR4Y"
title = "Promote DOCARCH001/DOC012/NARR001 to error once denominators reach zero"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
parent = "01M0XNVQXJ1A3FA43N7AA0PAPK"
reporter = "human"
created = "2026-09-11T00:00:00Z"
updated = "2026-10-04T21:08:01Z"
aliases = ["T-4423"]
labels = ["milestone:0.534.0", "v1-cluster:F1"]

[[links]]
kind = "blocked-by"
target = "01M26W79A2PAT8PMCRQ9P7CYAX"

[[links]]
kind = "blocked-by"
target = "01M26W79A4S0QNSSKHQW1BRJGC"

[[acceptance]]
text = "Given all five debloat stories closed with zero denominators, when frob.toml is checked, then DOCARCH001, DOC012 and NARR001 are severity=error"
bound = false
+++

DOCARCH001, DOC012 and NARR001 (172 warnings on the last ubuntu CI self-gate) are WARN-tier and non-blocking today, so a green frob check makes no narrative-hygiene claim. Once the five debloat stories (T-4418..T-4422) each measure zero for their denominator, promote DOCARCH001, DOC012 and NARR001 to error severity in frob.toml so the class cannot regress silently.
