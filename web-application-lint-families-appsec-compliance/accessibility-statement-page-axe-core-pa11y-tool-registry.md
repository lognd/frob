+++
id = "01M336K76C6QT2TEEY81FYMD0X"
title = "Accessibility-statement page + axe-core/pa11y tool-registry entries"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M2Y1SS0T6ZDPMY6DRJGEK1XJ"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5324"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_a11y_statement.py", "src/frob/doctor.py", "docs/modules/gates.md", "docs/guides/install.md", "tests/unit/test_webapp_a11y_statement.py", "tests/fixtures/webapp/a11y1xx/statement/**"]

[[links]]
kind = "blocked-by"
target = "01M336K75NMT3A5A562PMFWHYX"

[[links]]
kind = "blocked-by"
target = "01M336K761THP29CQDQMKTE07D"
+++

Content-lint for the accessibility-statement page (W3C WAI required contents: commitment, standard applied WCAG 2.2 AA, contact, known limitations, measures, technical prerequisites, tested environments), same shape as T-5145-2's privacy-policy lint. Add _RELEVANT_TOOLS entries for axe-core/pa11y in src/frob/doctor.py (T-5139/T-3276 pattern, same as the existing cargo-audit entry): relevant_when = an HTML/JSX file exists AND a dynamic-only A11Y criterion (color-only meaning) is in scope; absence is a failing UNMEASURED RelevantToolFinding, never silently skipped.
