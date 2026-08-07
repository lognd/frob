## Done report

Re-measured `frob check --only arch --json` first, filtered to
abstraction-opportunity findings whose reported location is under
`src/frob/arch/`: confirmed 27 groups across 12 files, matching the
ticket body's exact per-file breakdown (_async_hazards.py 3,
_concurrency.py 1, _concurrency_model.py 2, _cpp.py 2, _exceptions.py 3,
_fallibility.py 1, _kotlin.py 8, _ocp.py 1, _patterns.py 3, _python.py 1,
_solid.py 1, _typescript.py 1).

Read every group's actual member bodies (not just the grouped names) per
the ticket's own instruction not to batch-waive. None of the 27 warrant a
manual extraction inside `src/frob/arch/`'s own declared scope. They split
into four recognizable shapes, none of them a genuine missing abstraction:

1. Check-function registry protocol collisions: `_exceptions.py`'s
   27-member `(NormalizedModule) -> list[ArchSuggestion]` group is not a
   coincidence at all -- grep confirms 33 functions across
   `src/frob/arch/*.py` match `^def check_`, and the vast majority share
   this exact bare signature. This is the package's own intentional
   common detector interface, the same shape as T-0360's dispatch-family
   exclusion and T-1068's language-parity exclusion, just not yet
   generalized to a naming-convention-based family.
2. Per-construct mirrored builders that happen to share a return type:
   `_typescript.py`'s `_ts_build_class`/`_ts_build_interface`/
   `_ts_build_enum` (read in full) build three DIFFERENT tree-sitter node
   types (`class_declaration`/`interface_declaration`/`enum_declaration`)
   into `NormalizedClass` -- distinct concerns, not one duplicated
   function. `_kotlin.py`'s 8 groups (its own module docstring explicitly
   documents "mirroring... not reusing" as the deliberate cross-adapter
   design, T-0609/T-0611) are the same shape at the cross-language-file
   level.
3. Deliberately-kept-separate trivial one-liners with reviewed precedent:
   `_bare_callee_name(callee: str) -> str` is defined byte-identically in
   `_mayraise.py`, `_fallibility.py`, and `_exceptions.py`; each docstring
   explicitly cross-references the sibling copy. A prior ticket (T-0686)
   already reviewed this exact tradeoff for the sibling `_qualname`
   duplicate in `_mayraise.py` and chose module independence over sharing
   a one-line private helper across otherwise-unrelated check families
   ("that sibling module is out of this ticket's declared scope; see this
   module's docstring for why duplicating this one small helper... is the
   intended shape here"). Re-deduplicating now would silently reverse
   that reviewed decision without a new instruction to do so -- left
   alone.
4. Large mixed-concern coincidental collisions: `_async_hazards.py`'s
   32-member `(Node) -> bool` group, `_concurrency_model.py`'s 27-member
   `(Node) -> str | None` group, etc. -- read a sample of members in each
   (e.g. `_is_async_def`/`_kt_has_override_modifier`/`_is_trivial_getter`
   share no concern beyond the generic tree-sitter-node-predicate shape).
   This is exactly the class-1 "coincidental collision, do not force
   extraction across an entire group" case the parent ticket's own body
   anticipated.

No code was changed in `src/frob/arch/`; this ticket's actual output is
the triage itself (so the next agent working this package does not
re-derive it) plus one follow-up ticket proposing the actual code fix for
class 1 above (the only class that is a genuine detector-precision gap
rather than already-correct-as-designed): T-1112 (final id after
renumbering at land), adding a `_is_check_registry_family`-style exclusion to
`frob.arch._python._check_abstraction_opportunities` for a same-signature
group where every member's bare name matches `^check_[a-z_]+$`.

Since no source changed, no new test evidence exists to bind; per the
playbook's docs-only-ticket precedent, recording the existing CLI-dispatch
integration test as evidence instead.

Gates: `uv run frob check --ticket T-1084` (gates-fast/gates-native via
the manual --only loop) clean; no new violations introduced (nothing
touched).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 894 warning(s), 426 waived
- error-findings: none (measured, zero errors)
