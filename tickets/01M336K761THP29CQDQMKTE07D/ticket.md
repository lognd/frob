+++
id = "01M336K761THP29CQDQMKTE07D"
title = "A11Y substrate: HTML/JSX/Vue accessibility-tree query helpers"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M2Y1SS0T6ZDPMY6DRJGEK1XJ"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5313"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_a11y_substrate.py", "tests/fixtures/webapp/a11y1xx/**", "docs/modules/webapp-a11y.md", "tests/unit/test_webapp_a11y_substrate.py"]

[[links]]
kind = "blocked-by"
target = "01M336K75PBAVJE0SEABECQYQV"
+++

Small internal tree-sitter query-helper library over the html/jsx/vue grammars (WEBSUB-1): element-with-attribute lookup (img[alt], input[aria-label]), heading-sequence walk, <html lang> lookup -- shared by every A11Y rule below instead of duplicated per-rule query strings. Fixture: one clean + one violating HTML/JSX/Vue sample per query shape.
