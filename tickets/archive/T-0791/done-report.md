## Done report

Absorbed by T-0792's land: the deny-flag fire/no-fire coverage the ticket
demanded exists as TestMultiAceDenyOverridesAllow (both declaration
orders), constructing explicit :deny ACEs on write-capable RIGHTS and
asserting no write capability and no shared-writable-path violation. The
criterion's literal _acl_grants_write reference is superseded: that
helper was deleted as dead code in the same land (all ACL paths route
through _join_acl_entries), and the behavior-level criterion is what the
bound tests prove.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_then_broad_allow_same_principal_denies` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_broad_allow_then_narrow_deny_same_principal_still_denies` (pytest node id, verified passing when recorded)
