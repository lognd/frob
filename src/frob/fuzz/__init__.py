"""frob.fuzz -- enforced property fuzzing with invariant-respecting generators.

(docs/fuzz.md is authoritative.)

Fuzzing stops being optional: every fuzz-obligated function (invariant-
anchored by default, or every public function under `enforce="public"`)
must have a `frob:tests kind="fuzz"` binding fed by a generator resolved
via the Arbitrary protocol (`resolve`) -- a missing generator or missing
binding is FUZZ002/FUZZ001, gate failures, not code-review hopes.

This package is library-only: `register`/`resolve` build the generator
registry, `obligations` computes fuzz debt purely from a `GraphSnapshot`,
`FUZZ001`/`FUZZ002`/`FUZZ003` are pure rule functions returning
`tuple[Violation, ...]`, and `stamp_fuzz`/`load_fuzz_stamp` persist
`.frob/fuzz-stamp.json`. Wiring these into `run_gates`, `frob.toml`
parsing, and the `frob test --fuzz` CLI surface is coordinator work on
this ticket (T-0002), not this module's.
"""

from __future__ import annotations

from frob.fuzz._arbitrary import HYPOTHESIS_AVAILABLE, register, resolve
from frob.fuzz._models import (
    FuzzEnforce,
    FuzzError,
    FuzzObligation,
    FuzzPolicy,
    FuzzResult,
)
from frob.fuzz._obligations import obligations
from frob.fuzz._rules import FUZZ001, FUZZ002, FUZZ003
from frob.fuzz._run import run_fuzz
from frob.fuzz._signatures import resolve_param_types
from frob.fuzz._stamp import load_fuzz_stamp, stamp_fuzz

__all__ = [
    "FUZZ001",
    "FUZZ002",
    "FUZZ003",
    "HYPOTHESIS_AVAILABLE",
    "FuzzEnforce",
    "FuzzError",
    "FuzzObligation",
    "FuzzPolicy",
    "FuzzResult",
    "load_fuzz_stamp",
    "obligations",
    "register",
    "resolve",
    "resolve_param_types",
    "run_fuzz",
    "stamp_fuzz",
]
