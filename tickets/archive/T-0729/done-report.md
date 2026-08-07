## Done report

Mirrored the established classifier-corpus SYS100 exemption mechanism
(T-0201/T-0253's `frob.vet._capability.is_self_pattern_path` +
`_SELF_PATTERN_SUFFIXES`, already reused by `_capability_registry.
DANGEROUS_OPERATIONS`, `_cve_fingerprint.CVE_FINGERPRINTS`, and PII011/
PII012's own suffix list in `gates/_pii_structural.py`) for `frob.arch.
_srp`'s ARCH103 I/O-classifier tables (`_IO_MODULE_PREFIXES` etc.):
added `("frob", "arch", "_srp.py")` to `_SELF_PATTERN_SUFFIXES` in
`src/frob/vet/_capability.py`, with an inline comment explaining why this
is the same self-match class (string-literal classifier DATA, not
capability USAGE) and why declaring `may net`/`may exec` on `graphlang`
would have been dishonest in the other direction. This is a per-file
exclusion from self-conformance's capability scan, not a per-observation
waiver -- the same shape T-0201/T-0253/T-0539 already established, and the
right one here since `_srp.py` performs no actual I/O itself (only
imports `frob.arch._models`/`frob.arch._normalized`).

Investigated `_ocp.py` (T-0617, landed on main mid-ticket via the warm-up
merge) for the same class of issue per the dispatch note: it defines no
`_IO_MODULE_PREFIXES`-shaped classifier table and no `needles=`/`needles:
tuple[` literal corpus, so it is not affected and needed no change.

`uv run frob sys audit` after the fix (and again after merging main to
pick up T-0617): "self-conformance PROVED -- zero SYS gaps" both times,
0 SYS100/101/102 findings.

Reconciliation: T-0724's worktree drafted T-draft-890e0667 for this same
issue -- T-0729 supersedes it; the coordinator should drop the duplicate
at T-0724's land.

### Changed
```
 src/frob/vet/_capability.py | 15 +++++++++++++++
 1 file changed, 15 insertions(+)
```

### Evidence
- `tests/unit/test_arch_srp.py::TestMixedConcernFunction::test_io_compute_and_formatting_together_trigger` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_covers_every_needle_table_module` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_survives_a_foreign_install_copy` (pytest node id, verified passing when recorded)
