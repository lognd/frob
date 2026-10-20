+++
id = "01M3AXSD7WN9GJ27A1ZEMT1JYG"
title = "config-surface detection and a ConfigDoc contract in frob.lang"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD8TNZP3PQVKB7EKCR7M"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-09T20:42:10Z"
aliases = ["T-6396"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/lang/_config_detect.py (new)", "src/frob/lang/_config_doc.py (new)", "docs/design/language-engines.md"]
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: config-surface detection and a ConfigDoc contract in frob.lang
kind: feature
tier: leaf
parent: T-SYS-SB
milestone: 0.539.0
sprint: sysdesign
points: 5
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/lang/_config_detect.py (new), src/frob/lang/_config_doc.py (new),
       docs/modules/lang.md, tests/fixtures/sysdesign/configdoc/**
blocked_by: []

Body:

Precedent: src/frob/webapp/__init__.py's `detect_frameworks` gates all WEBSEC-family relevance
on whether a framework was actually detected ("a CLI repo with no detected framework runs none
of this work") -- this leaf reuses that owner directive for config-surface detection: a repo
with no Kubernetes/Helm/Terraform/compose/Envoy-NGINX-Caddy files present runs none of the
per-surface parsers below.

Acceptance criteria:
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->- `frob.lang._config_detect.detect_config_surfaces(repo_root)` returns the set of surfaces
  present (k8s, helm, terraform, compose, envoy, nginx, caddy), by file-glob + light content
  sniff (e.g. a YAML with `apiVersion`+`kind` top-level keys is k8s, not generic YAML).
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->- `frob.lang._config_doc.ConfigDoc` is a pydantic model: `kind: Literal[...]`, `path: Path`,
  `raw: dict | list`, and a `get(*keys, default=None)` dotted-path accessor so per-surface
  parsers (T-SYS-B-K8S etc.) return a uniform `list[ConfigDoc]` regardless of source dialect.
- No parsing library dependency is added without `frob vet` per the global CLAUDE.md rule
  (dependency vetting) -- prefer stdlib `tomllib`/PyYAML (already a dependency per
  yaml.safe_load call sites in SYSDESIGN-INVENTORY.md sec 2) over a new HCL/YAML library
  unless one is already vetted.
- docs/modules/lang.md documents the ConfigDoc contract and the per-surface detection table.
- Positive-control fixture: tests/fixtures/sysdesign/configdoc/mixed-surfaces/** containing one
  file of each surface kind, proving detection does not cross-contaminate (a Helm values.yaml
  is not misdetected as raw k8s).
