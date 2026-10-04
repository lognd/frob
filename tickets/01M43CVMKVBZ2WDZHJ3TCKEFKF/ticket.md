+++
id = "01M43CVMKVBZ2WDZHJ3TCKEFKF"
title = "DOC rules read Python docstrings"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M43A5349M17PED730HKNM4VV"
reporter = "lognd"
created = "2026-10-04T12:05:14Z"
updated = "2026-10-04T12:05:14Z"
scope = ["crates/frob-obligations/**"]

[[acceptance]]
text = "Given a public Python function without a docstring, when frob check runs, then DOC001 reports it"
bound = false
+++

~F0KSGKF records Python docstrings in the doc facet but DOC001 examines only Rust; extend the DOC family to Python units (public functions, classes and methods without a docstring).
