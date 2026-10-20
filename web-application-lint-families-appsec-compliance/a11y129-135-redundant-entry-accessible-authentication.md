+++
id = "01M336K76AE2YVZAQ3QKWWJS3X"
title = "A11Y129-135: redundant entry, accessible authentication, contrast"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0T6ZDPMY6DRJGEK1XJ"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5322"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_a11y_forms_contrast.py", "tests/fixtures/webapp/a11y1xx/forms_contrast/**", "docs/modules/webapp-a11y-forms-contrast.md", "tests/unit/test_webapp_a11y_forms_contrast.py"]

[[links]]
kind = "blocked-by"
target = "01M336K75Q1WF4Q0HYZP31HTJV"

[[links]]
kind = "blocked-by"
target = "01M336K761THP29CQDQMKTE07D"
+++

Redundant entry across multi-step forms (SC 3.3.7, no autofill/prefill binding), accessible authentication (SC 3.3.8, CAPTCHA step with no alternative), contrast ratio (SC 1.4.3, WCAG relative-luminance formula over literal hex/rgb pairs in CSS -- needs CSS grammar, WEBSUB-1b). Ship the contrast-ratio computation as a reusable pure function -- T-5147 (SEO/WEBPERF) needs the same math. Fixture per rule id.
