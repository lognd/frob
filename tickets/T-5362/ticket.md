---
id: T-5362
title: 'SEO121-127: crawl/discovery config'
state: done
kind: feature
origin: human
created: '2026-09-23'
priority: high
blocked_by:
- T-5302
parent: T-5147
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5362
branch: t-5362
scope:
- src/frob/webapp/_seo_crawl.py
- tests/fixtures/webapp/seo1xx/crawl/**
- tests/unit/test_seo_crawl.py
- docs/modules/webapp-seo-crawl.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/seo1xx/**
  reason: per-ticket fixture subdir (siblings own tags/ and spam/) plus test file
    and module doc, batched at intake
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/seo1xx/crawl/**
  reason: per-ticket fixture subdir (siblings own tags/ and spam/) plus test file
    and module doc, batched at intake
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_seo_crawl.py
  reason: per-ticket fixture subdir (siblings own tags/ and spam/) plus test file
    and module doc, batched at intake
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/webapp-seo-crawl.md
  reason: per-ticket fixture subdir (siblings own tags/ and spam/) plus test file
    and module doc, batched at intake
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
evidence:
- tests/unit/test_seo_crawl.py::test_seo_crawl_findings_fixture[seo121_positive-SEO121-True]
- tests/unit/test_seo_crawl.py::test_seo_crawl_findings_fixture[seo121_negative-SEO121-False]
- tests/unit/test_seo_crawl.py::test_seo_crawl_findings_fixture[seo122_positive-SEO122-True]
- tests/unit/test_seo_crawl.py::test_seo_crawl_findings_fixture[seo122_negative-SEO122-False]
- tests/unit/test_seo_crawl.py::test_seo_crawl_findings_fixture[seo123_positive-SEO123-True]
- tests/unit/test_seo_crawl.py::test_seo_crawl_findings_fixture[seo123_negative-SEO123-False]
- tests/unit/test_seo_crawl.py::test_seo_crawl_findings_fixture[seo124_positive-SEO124-True]
- tests/unit/test_seo_crawl.py::test_seo_crawl_findings_fixture[seo124_negative-SEO124-False]
- tests/unit/test_seo_crawl.py::test_seo_crawl_findings_fixture[seo125_positive-SEO125-True]
- tests/unit/test_seo_crawl.py::test_seo_crawl_findings_fixture[seo125_negative-SEO125-False]
- tests/unit/test_seo_crawl.py::test_seo_crawl_findings_fixture[seo126_positive-SEO126-True]
- tests/unit/test_seo_crawl.py::test_seo_crawl_findings_fixture[seo126_negative-SEO126-False]
- tests/unit/test_seo_crawl.py::test_seo_crawl_findings_no_framework_short_circuits
- tests/unit/test_seo_crawl.py::test_websec_findings_emits_violation_when_called_directly
- tests/unit/test_seo_crawl.py::test_websec_findings_empty_frameworks_short_circuits
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
robots.txt malformed/Google-Extended decision-record, sitemap.xml schema validation against the sitemaps.org structure, llms.txt advisory-only presence, hreflang, canonical for query-string variants. robots.txt is line-oriented (no grammar needed); sitemap.xml via stdlib xml.etree. Fixture per rule id.