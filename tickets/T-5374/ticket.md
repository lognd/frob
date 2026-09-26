---
id: T-5374
title: 'SEO101-112: per-page tags'
state: done
kind: feature
origin: human
created: '2026-09-23'
priority: high
blocked_by:
- T-5364
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
worktree: /home/logan/projects/frob/.claude/worktrees/t-5374
branch: t-5374
scope:
- src/frob/webapp/_seo_tags.py
- tests/fixtures/webapp/seo1xx/tags/**
- tests/unit/test_seo_tags.py
- docs/modules/webapp-seo-tags.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/seo1xx/**
  reason: per-ticket fixture subdir, siblings own seo1xx/spam/** (T-5365) and seo1xx/crawl/**
    (T-5362)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/seo1xx/tags/**
  reason: per-ticket fixture subdir, siblings own seo1xx/spam/** (T-5365) and seo1xx/crawl/**
    (T-5362)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_seo_tags.py
  reason: unit test file + module doc, per T-5325-family convention
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/webapp-seo-tags.md
  reason: unit test file + module doc, per T-5325-family convention
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
evidence:
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo101_positive-SEO101-True]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo101_negative-SEO101-False]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo102_positive-SEO102-True]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo102_negative-SEO102-False]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo103_positive-SEO103-True]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo103_negative-SEO103-False]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo104_positive-SEO104-True]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo104_negative-SEO104-False]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo105_positive-SEO105-True]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo105_negative-SEO105-False]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo106_positive-SEO106-True]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo106_negative-SEO106-False]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo107_positive-SEO107-True]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo107_negative-SEO107-False]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo108_positive-SEO108-True]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo108_negative-SEO108-False]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo109_positive-SEO109-True]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo109_negative-SEO109-False]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo110_positive-SEO110-True]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo110_negative-SEO110-False]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo111_positive-SEO111-True]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo111_negative-SEO111-False]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo112_positive-SEO112-True]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_fixture[seo112_negative-SEO112-False]
- tests/unit/test_seo_tags.py::test_seo_tag_findings_no_framework_short_circuits
- tests/unit/test_seo_tags.py::test_websec_findings_emits_violation_when_called_directly
- tests/unit/test_seo_tags.py::test_websec_findings_empty_frameworks_short_circuits
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Unique title/meta-description per route, og:title/og:type/og:image/og:url, canonical link, favicon, JSON-LD LocalBusiness required properties. html-lang cross-refs A11Y104's rule id, not duplicated. Fixture per rule id via 5147-1.