## Done report

## Done report

Changed:
src/frob/strata/_host_isolation.py::_acl_ace_of
src/frob/strata/_host_isolation.py::_acl_grants_write
src/frob/strata/_host_isolation.py::_join_acl_entries
src/frob/strata/_host_isolation.py::_owned_paths_by_user

Semantics design: `_join_acl_entries` replaces the last-declaration-wins
dict overwrite (`_owned_paths_by_user`'s prior `claims[acl_entry.path] = ...`
loop, which discarded every ACE for a path except whichever happened to
land last in node/field-declaration order) with a real NTFS deny-
overrides-allow join across ALL ACEs declared for a path. ACEs are
grouped by PRINCIPAL (parsed from the RULE's `PRINCIPAL:RIGHTS[:deny]
[:no_inherit]` shape via the new `_acl_ace_of` helper, shared by
`_acl_grants_write`'s single-ACE question and the new multi-ACE join so
the RULE grammar is only split in one place). An explicit `:deny` ACE
always wins over an explicit allow ACE for the SAME principal, no matter
declaration order (`net_deny_by_principal`/`net_allow_by_principal` sets
in `_join_acl_entries`). A deny for one principal never cancels a
DIFFERENT principal's allow -- the path is write-capable overall if ANY
principal's net verdict is allow (final `any(...)` OR-reduction). This
closes the T-0606 reviewer finding: the prior collapse could silently
drop an earlier ACE's real write grant to a different principal purely
because a later-iterated ACE for a DIFFERENT principal happened to be a
deny, under-reporting a shared-writable-path violation. `owns` (linux
POSIX MODE, one mode per path) keeps its existing last-declaration-wins
behavior unchanged -- only the windows `acl` half needed the multi-ACE
join.

Token-privilege disposition: SeImpersonatePrivilege/SeDebugPrivilege-class
windows token privileges are recorded as an explicit OUT-OF-SCOPE
disposition with reason in the module docstring (new "Token-privilege
classes: explicit out-of-scope disposition (T-0792)" section,
src/frob/strata/_host_isolation.py). `std.host`'s grammar has no
`privilege "NAME"` clause parallel to `group`/`sudoers` (T-0272's
precedent) for a manifest to declare a granted windows privilege, so
there is no fact this module could join against -- modeling it would
require a `strata-core/src/parse.rs` grammar addition, outside this
ticket's `src/frob/strata/**` scope (mirroring the T-0272 precedent of
deferring a grammar-gated gap to a follow-up). Not modeled in docs/strata/
host.md itself since that file is outside this ticket's declared scope
globs (src/frob/strata/_host_isolation.py, tests/unit/strata/
test_host_isolation.py only) -- documented in the in-scope module
docstring instead, disclosed here rather than silently left unstated.

T-0791 absorption: T-0791 ("strata host: :deny ACL flag path has zero
test evidence") asked for a fire/no-fire pair explicitly exercising the
`:deny` flag on write-capable RIGHTS (the existing test used Everyone:Read,
a non-write RIGHTS value, never an actual `:deny` flag). This ticket's
new tests `TestWindowsHostIsolation::test_explicit_deny_acl_flag_does_not_
fire_shared_writable_path` (no-fire: both sides carry ONLY a
`Everyone:Modify:deny` ACE) and `test_explicit_deny_acl_flag_fires_when_
write_rights_present_elsewhere` (fire: a `:deny`'d ACE for one principal
alongside a plain write-capable ACE for a different principal, also
exercising T-0792's multi-ACE join) satisfy T-0791's acceptance criterion
exactly -- both were written to close this ticket's own acceptance
criterion (which also names the T-0791 deny-flag test gap explicitly) and
happen to be the identical fire/no-fire pair T-0791 asks for. Evidence
recorded on T-0791 directly (`frob ticket evidence T-0791 --accepts 0 ...`)
so the coordinator can drop it without re-deriving evidence; T-0791 was
NOT closed/landed by this ticket (land-owned, out of scope for a worktree
agent per the playbook).

Evidence:
tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_deny_entry_denies
tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_allow_entry_grants
tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_then_broad_allow_same_principal_denies
tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_broad_allow_then_narrow_deny_same_principal_still_denies
tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_deny_for_one_principal_does_not_cancel_another_principals_allow
tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_no_write_rights_entries_denies
tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_explicit_deny_acl_flag_does_not_fire_shared_writable_path
tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_explicit_deny_acl_flag_fires_when_write_rights_present_elsewhere

Full-file test run: `uv run --frozen pytest tests/unit/strata/test_host_isolation.py
-p no:cacheprovider -q` -> 33 passed (all pre-existing 25+ tests preserved
plus 8 new). `uv run --frozen frob test --base main` (touched-set) ->
[PASS] python exit=0.

Filed: none.

Gates: `uv run --frozen frob check --ticket T-0792` chunked over lint,
static, gates-fast, gates-native, gates-security, and prework (via
`frob ticket sweep T-0792` before the prework re-check) -- all clean, 0
errors in every stage. `git diff main --diff-filter=D --stat` empty
(deletion-filter land rule).

### Changed
(no changed files detected)

### Evidence
- `tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_deny_entry_denies` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_allow_entry_grants` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_then_broad_allow_same_principal_denies` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_broad_allow_then_narrow_deny_same_principal_still_denies` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_deny_for_one_principal_does_not_cancel_another_principals_allow` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_no_write_rights_entries_denies` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_explicit_deny_acl_flag_does_not_fire_shared_writable_path` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_explicit_deny_acl_flag_fires_when_write_rights_present_elsewhere` (pytest node id, verified passing when recorded)
