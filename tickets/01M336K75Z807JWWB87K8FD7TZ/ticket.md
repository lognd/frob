+++
id = "01M336K75Z807JWWB87K8FD7TZ"
title = "WEBSEC123-125: resource-exhaustion input-bounds"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M2Y1SS0NVJMAC21FPVPYYSEE"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5311"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_websec_bounds.py", "tests/fixtures/webapp/websec1xx/bounds/**", "docs/modules/webapp-websec-bounds.md", "tests/unit/test_websec_bounds.py", "src/frob/gates/_taint_gate.py"]

[[links]]
kind = "blocked-by"
target = "01M336K75VAADETHRZ71MT5J2W"
+++

Unbounded input length (Pydantic/Zod/class-validator schema AST for missing max_length/maxLength/maxItems), XML entity bomb/XXE (XML-parser-instantiation AST for missing resolve_entities=False/defusedxml), JSON bomb/unbounded nesting depth (body-parser config for missing depth/size limit), unbounded recursion on user-controlled input (recursive function with no max-depth guard). Item 28 (business-logic step-skipping) is dynamic-only per the corpus -- file as a frob:tests obligation in this leaf's Done report, not a static rule. Fixture per rule id.
