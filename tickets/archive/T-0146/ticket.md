---
id: T-0146
title: 'cvelistV5 record parser: pydantic models for CVE Record Format v5'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/cve/**
- tests/unit/cve/**
- docs/modules/cve.md
- docs/index.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/cve/test_parser.py::test_parse_log4shell_multi_adp_and_cwe
- tests/unit/cve/test_parser.py::test_parse_version_ranges_with_less_than
- tests/unit/cve/test_parser.py::test_parse_multi_vendor_affected
- tests/unit/cve/test_parser.py::test_parse_cvss_v4
- tests/unit/cve/test_parser.py::test_parse_rejected_record
- tests/unit/cve/test_parser.py::test_parse_missing_file
- tests/unit/cve/test_parser.py::test_parse_truncated_json
- tests/unit/cve/test_parser.py::test_parse_missing_required_field
- tests/unit/cve/test_parser.py::test_iter_mirror_yields_records_and_errors
- tests/unit/cve/test_parser.py::test_iter_mirror_invalid_root
- tests/unit/cve/test_parser.py::test_cve_module_end_to_end_over_mirror
- tests/unit/cve/test_parser.py::test_fixtures_are_ascii_and_escaped_unicode_round_trips
designated_repro_test: null
threat: null
component: null
---
Parser for CVE Record Format v5 JSON as published in github.com/CVEProject/cvelistV5. Pydantic v2 models: cveMetadata (id/state/dates), containers.cna and containers.adp (affected products with vendor/product/versions incl. lessThan/lessThanOrEqual/versionType/status semantics, problemTypes with CWE ids, metrics CVSS v3.1 and v4.0, references, descriptions), REJECTED-state records. parse_record(path) and iter_mirror(dir) over a local clone/snapshot layout (cves/YYYY/NNNxxx/CVE-*.json). typani Result error values; an unparseable record is a loud typed failure, never a silent skip (vacuous-pass doctrine). NO network anywhere: tests run against a handful of real record JSONs committed as fixtures covering the shape variety (version ranges, multiple containers, rejected, cwe-bearing problemTypes). This ticket is parser+models only; vet integration is the follow-up ticket.