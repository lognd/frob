+++
id = "01M35RZY8E2HAT8Z7VPQG3MF99"
title = "Wire html/javascript/vue into capability/dup/docblock FACETS"
type = "bug"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:00Z"
aliases = ["T-5390"]
labels = ["v1-cluster:D2"]
scope = ["src/frob/lang/_support.py"]
+++

found while working T-5300: html/javascript/vue get a real frob.lang grammar/walker (_walk_html.py/_walk_javascript.py/_walk_vue.py) but, like css/scss before them (T-5303, T-5386), are not yet wired into the capability/dup/docblock FACETS registry -- follow-up, not this leaf's scope.
