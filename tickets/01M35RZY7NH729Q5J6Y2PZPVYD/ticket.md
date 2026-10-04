+++
id = "01M35RZY7NH729Q5J6Y2PZPVYD"
title = "SEO113-120: spam-policy shape detectors"
type = "task"
category = "triage"
priority = "high"
points = 5
parent = "01M2Y1SS0V388SVN54W7PX2ZBW"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:00Z"
aliases = ["T-5365"]
labels = ["milestone:0.534.0", "v1-cluster:B2", "area:crunk"]
scope = ["src/frob/webapp/_seo_spam.py", "tests/fixtures/webapp/seo1xx/spam/**", "tests/unit/test_seo_spam.py", "docs/modules/webapp-seo-spam.md"]

[[links]]
kind = "blocked-by"
target = "01M336K75Q1WF4Q0HYZP31HTJV"

[[links]]
kind = "blocked-by"
target = "01M35RZY7MEWNFG9P8JWACT55Y"
+++

Keyword stuffing (shape-based n-gram repetition, NOT a density threshold per the story's explicit correction), cloaking via user-agent branching, hidden text via CSS (color==background/font-size:0/opacity:0/off-screen-position -- needs CSS grammar, WEBSUB-1b), scaled-content/doorway-page config advisories, framework-default-title detection (Vite/CRA/Next), staging-without-noindex. Fixture per rule id.
