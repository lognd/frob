"""frob.dup -- semantic duplication detection (docs/modules/dup.md).

Two entry points coexist during the re-platform:

- `find_duplicates` (from `frob.dup._legacy`): the original Type-1/Type-2
  tree-sitter scan. `frob check`'s dup stage and the `frob dup` CLI
  (`frob.app.dup_runner`) still call this; kept working unchanged so
  neither breaks mid-migration.
- `find_clones` (from `frob.dup._pipeline`): the smart rung-ladder pipeline
  docs/modules/dup.md describes -- R1/R2 pure Python, R3+ via the `frob_core`
  native extension, region-granular `ClonePair`/`CloneReport` output. New
  code (the DUP001/DUP002 gate rules in `frob.gates`) should use this.
"""

from __future__ import annotations

from frob.dup._cache import get_fingerprint, get_verdict, put_fingerprint, put_verdict
from frob.dup._core import anti_unify, core_available
from frob.dup._legacy import CloneGroup, CodeFragment, DupResult, find_duplicates
from frob.dup._models import (
    AntiUnifyTemplate,
    CloneBinding,
    CloneMatchGroup,
    ClonePair,
    CloneRegion,
    CloneReport,
    CloneTemplate,
    DupConfig,
    DupError,
    DupStats,
    ProbeVerdict,
)
from frob.dup._pipeline import (
    find_clones,
    find_helper_clones,
    probe_equivalence,
    touched_refs,
)
from frob.dup._rules import DUP001, DUP002
from frob.dup._template import build_group_template

__all__ = [
    "DUP001",
    "DUP002",
    "AntiUnifyTemplate",
    "CloneBinding",
    "CloneGroup",
    "CloneMatchGroup",
    "ClonePair",
    "CloneRegion",
    "CloneReport",
    "CloneTemplate",
    "CodeFragment",
    "DupConfig",
    "DupError",
    "DupResult",
    "DupStats",
    "ProbeVerdict",
    "anti_unify",
    "build_group_template",
    "core_available",
    "find_clones",
    "find_duplicates",
    "find_helper_clones",
    "get_fingerprint",
    "get_verdict",
    "probe_equivalence",
    "put_fingerprint",
    "put_verdict",
    "touched_refs",
]
