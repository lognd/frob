---
id: T-draft-ac80b4e1
title: Decompose the C++ family into a cpp base plus cmake-install-export, cmake-exe
  and pybind11-bridge facets
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4766
parent: T-4757
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/data/bases/cpp/**
- src/frob/scaffold/data/facets/cmake-install-export/**
- src/frob/scaffold/data/facets/cmake-exe/**
- src/frob/scaffold/data/facets/pybind11-bridge/**
- src/frob/scaffold/data/shared/cpp/**
- src/frob/scaffold/data/types/cpp-library/**
- src/frob/scaffold/data/types/cpp-tool/**
- src/frob/scaffold/data/types/pybind11-library/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given the template data tree, when file content digests are compared, then
    the cpp header and cpp test templates exist exactly once (two identical pairs
    today)
  evidence: []
- text: Given the pybind11-library preset, when its rendered frob.toml and pyproject
    are compared against the python base's, then they are the same files, not forks
  evidence: []
- text: Given pybind11-library, when it is rendered, then the python package sits
    under a src directory
  evidence: []
- text: Given all three cpp presets, when frob check runs in the rendered trees, then
    it is clean
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Decompose the C++ family into the cpp BASE plus facets, per audit 6.3.

cpp-library becomes cpp plus cmake-install-export plus github-ci plus
docs-site plus release-ci.
cpp-tool becomes cpp plus cmake-exe plus the same.
pybind11-library becomes cpp plus python plus a pybind11-bridge facet plus
github-ci -- which is the first real test of two bases composing.

Measured duplication this removes: the cpp header template and the cpp test
template are 100 percent identical between cpp-library and cpp-tool (two
files, 10 lines); the rendered Makefiles are identical but for one variable
(75 lines, already deleted by the wrappers leaf); pybind11's pyproject is 79
percent a duplicate of the shared python one (27 lines) and its CI workflow
53 percent (16 lines).

pybind11 also moves to src layout: today it puts the Python package at the
repository root, which refs/python.md forbids.

Positive controls:
1. the cpp header and test templates exist exactly once in the tree,
   asserted by a content-digest test over the template data directory;
2. pybind11-library renders with the python base's frob.toml and pyproject,
   not a fork -- asserted by comparing the rendered files against the
   python base's rendering of the same;
3. frob check clean on all three presets.
