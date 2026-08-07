## Done report

Root cause nuance: the two crate build lines were structurally identical;
the observed asymmetry (stray strata-core/.venv) is uv/maturin-version-
dependent cwd-walk-up venv discovery, not a Makefile structural
difference. A clean pre-fix rebuild in the current environment did not
reproduce the stray venv, so the fix hardens both crates against the
version-dependent behavior rather than repairing a still-reproducible
break.

Fix: the core target now pins VIRTUAL_ENV=$(CURDIR)/.venv and uses
maturin's -m <crate>/Cargo.toml manifest flag for BOTH crates (no cd),
so builds land in the repo-root venv deterministically.

Verification: clean rebuild creates no frob-core/.venv or
strata-core/.venv; md5 of strata-core/target/release/libstrata_core.so
matches .venv/.../strata_core.abi3.so (1ffdba30...) and
frob-core/target/release/libfrob_core.so matches
.venv/.../frob_core.abi3.so (75e1725b...); tests/unit/strata green
(evidence ids attached prove strata_core imports from the root venv);
frob check exit 0 with unchanged diagnostics (A-B via stash).

T-0117 adjudication: the R5 dup test still fails against a
byte-identical, correctly-installed fresh frob_core build, ruling OUT
venv contamination (cause b) and confirming rust-source drift (cause a)
as the live hypothesis. Out of scope here; T-0117 remains open for the
rust-side fix.
