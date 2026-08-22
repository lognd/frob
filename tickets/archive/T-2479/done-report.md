## Done report

Changed:
- src/frob/vet/_capability_python.py::_resolve_py_call (new, dispatcher)
- src/frob/vet/_capability_python.py::_resolve_py_partial_call (split out of the old combined function, same behavior)
- src/frob/vet/_capability_python.py::_resolve_py_boto3_client_call (new)
- src/frob/vet/_capability_registry/_dangerous_ops_python.py (3 new _op entries: S3, DynamoDB, IAM mutating-verb net-mutate needles)
- docs/modules/vet.md (documented the boto3 net-mutate extension)
- tests/test_capability_registry.py::TestBoto3ServiceBindingResolution (new, 6 tests)

Followed the ticket's own recommendation: implemented the binding-aware
resolver extension for boto3 rather than a flat needle survey.
`_resolve_py_boto3_client_call` resolves `boto3.client("service")`/
`boto3.resource("service")` call sites (string-literal service name
only, fail-closed on a non-literal name) to a synthetic
`boto3.client(service)`/`boto3.resource(service)` identity. This flows
through the EXISTING alias-table copy-propagation machinery
(`_record_py_alias`/`_resolve_py_attribute`) unchanged: `s3 =
boto3.client("s3")` binds `s3` to that synthetic identity, so
`s3.put_object(...)` resolves all the way to
`boto3.client(s3).put_object`, which the new per-service needle entries
match.

Covered THREE high-value services, disclosed as representative not
exhaustive (matching T-2464's own disclosed-gap precedent, and the
ticket's own "do not attempt a one-line needle-table fix" instruction --
this is a real resolver extension, not a flat needle):
- S3 (put_object/delete_object/delete_objects/create_bucket/
  delete_bucket/put_object_acl/put_bucket_acl/put_bucket_policy/
  delete_bucket_policy/copy_object/upload_file/upload_fileobj/
  restore_object) -- severity "high"
- DynamoDB (put_item/delete_item/update_item/create_table/delete_table/
  update_table/batch_write_item/transact_write_items) -- severity "high"
- IAM (create_user/delete_user/update_user/create_role/delete_role/
  put_role_policy/delete_role_policy/attach_role_policy/
  detach_role_policy/create_policy/delete_policy/attach_user_policy/
  detach_user_policy/create_access_key/delete_access_key) -- severity
  "critical" (privilege-escalation surface, the ticket's own "highest
  value, hardest to cover" framing)

NOT attempted, matching the ticket's own explicit scoping:
- aiohttp: same disclosed session/instance-method gap as requests/httpx
  (T-2464) -- `session.post(url)` has no library-name prefix and a bare
  `.post(` needle would false-positive broadly. Not a boto3-shaped
  binding problem (no service-name literal to resolve through), so the
  T-2479 resolver technique does not apply here.
- asyncpg: `.execute(`'s read/write reality depends on the SQL STRING
  passed to it, the same inherent ambiguity the existing `sql`
  capability kind already lives with -- not attempted, per the ticket's
  own text.
- http.client/ftplib/smtplib/socket: no clean verb-shaped idiom -- not
  attempted, per the ticket's own text.
- A full per-service survey across boto3's ~350 services (only S3/
  DynamoDB/IAM done here) -- filed as a follow-up (T-2500).

Evidence:
- tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_s3_client_put_object_reports_net_mutate_and_net_connect
  (DESIGNATED REPRO -- confirmed FAILED_AT_PARENT at d7213fbc6, the
  test-alone commit before the fix, via `frob ticket evidence
  --check-repro --base-ref d7213fbc6`; T-2021's own technique for a
  brand-new test with no pre-fix ref in main's history)
- tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_s3_resource_delete_object_reports_net_mutate
- tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_s3_get_object_does_not_report_net_mutate
  (control: a read-only S3 verb does NOT fire net-mutate)
- tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_dynamodb_put_item_reports_net_mutate
- tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_iam_create_user_reports_net_mutate
- tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_non_literal_service_name_does_not_resolve
  (control: fail-closed on a non-literal service name)

Full test run: `pytest tests/test_capability_registry.py
tests/test_vet_capability.py -q` -> 470/470 passed, no regressions.

Filed: T-2500 (exhaustive per-service boto3 verb survey, follow-up), and
T-2498 (unrelated bug found while landing T-2452: `frob ticket body
--append` misroutes into done-report.md, not this ticket's own scope)

Gates: `frob check --ticket T-2479 --only ty` clean (0 issues). `frob
check --ticket T-2479 --only archgate` (repo-wide, no findings in either
changed file -- ARCH001/ARCH103 clean for both). `frob check --ticket
T-2479 --only scope --only prework --only affect_drift --only fmt`
clean (0 errors; added tests/test_capability_registry.py and
docs/modules/vet.md to scope for the files this ticket actually edits).

### Changed
```
 docs/modules/vet.md                                |  12 ++-
 src/frob/vet/_capability_python.py                 | 111 ++++++++++++++++----
 .../_capability_registry/_dangerous_ops_python.py  | 115 +++++++++++++++++++++
 tests/test_capability_registry.py                  | 105 +++++++++++++++++++
 tickets/T-2479/ticket.md                           |  25 ++++-
 5 files changed, 347 insertions(+), 21 deletions(-)
```

### Evidence
- `tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_s3_client_put_object_reports_net_mutate_and_net_connect` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_s3_resource_delete_object_reports_net_mutate` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_s3_get_object_does_not_report_net_mutate` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_dynamodb_put_item_reports_net_mutate` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_iam_create_user_reports_net_mutate` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_non_literal_service_name_does_not_resolve` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
