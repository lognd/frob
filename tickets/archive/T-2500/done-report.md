## Done report

Read T-2479's Done report first, per the coordinator's instruction. The
resolver (_resolve_py_boto3_client_call) is already service-agnostic --
this was purely a needle-table extension, no resolver code touched.

Added the "next tier" the ticket's own body prioritized: EC2, RDS,
Lambda, SNS, SQS, Secrets Manager, KMS -- 7 more services beyond T-2479's
S3/DynamoDB/IAM, same _op(...) shape, same
boto3.{factory}(service).{verb}( needle pattern.

boto3 covers roughly 350 services total; a literal service-by-service
survey of all ~347 remaining is not attempted in one pass -- this
extends coverage to the highest-value tier the ticket itself named and
discloses the remainder as still-representative-not-exhaustive, matching
T-2479's own precedent. No resolver limitation was found: every
service's mutating verbs (create/delete/put/update/attach/schedule/etc)
express cleanly through the existing binding-aware resolver -- nothing
here needed forcing.

One test (EC2 read-only control) was removed after `frob check` flagged
it as a 100%-AST-duplicate (DUP001) of an existing S3 control test --
the "a read verb does not fire" distinction is already proven there, so
removing was correct rather than waiving a real duplicate.

### Changed
```
 docs/modules/vet.md                                |   7 +-
 .../_capability_registry/_dangerous_ops_python.py  | 224 +++++++++++++++++++++
 tests/test_capability_registry.py                  |  94 +++++++++
 tickets/T-2500/ticket.md                           |  35 +++-
 4 files changed, 357 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_capability_registry.py::TestBoto3NextTierServiceBindingResolution::test_ec2_terminate_instances_reports_net_mutate` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestBoto3NextTierServiceBindingResolution::test_rds_delete_db_instance_reports_net_mutate` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestBoto3NextTierServiceBindingResolution::test_lambda_update_function_code_reports_net_mutate` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestBoto3NextTierServiceBindingResolution::test_sns_publish_reports_net_mutate` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestBoto3NextTierServiceBindingResolution::test_sqs_send_message_reports_net_mutate` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestBoto3NextTierServiceBindingResolution::test_secretsmanager_put_secret_value_reports_net_mutate` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestBoto3NextTierServiceBindingResolution::test_kms_schedule_key_deletion_reports_net_mutate` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2500/src/frob/testing/_collect_kotlin.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
