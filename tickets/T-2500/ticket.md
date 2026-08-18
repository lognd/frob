---
id: T-2500
title: 'boto3 net-mutate: exhaustive per-service mutating-verb survey (S3/DynamoDB/IAM
  done, ~347 services remain)'
state: queued
kind: security
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/vet/_capability_registry/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2479: T-2479 implemented boto3.client("service")/
boto3.resource("service") binding-aware resolution for the net-mutate
capability signal, and populated per-service mutating-verb needle tables
for exactly THREE high-value services (S3, DynamoDB, IAM) as a
representative, not exhaustive, starting set.

boto3 covers roughly 350 AWS services total. A full survey would walk
each service's own API reference and classify every mutating
(create/put/delete/update/attach/detach/...) operation into the needle
table T-2479 added to
src/frob/vet/_capability_registry/_dangerous_ops_python.py, following
the exact same _op(...) entry shape T-2479 established (one entry per
service, needles built as
f"boto3.{factory}({service}).{verb}(" for factory in
("client", "resource") for verb in <service's mutating verb list>).

The binding-aware resolver itself
(src/frob/vet/_capability_python.py::_resolve_py_boto3_client_call) is
already service-agnostic -- no resolver code changes are needed for
additional services, only new registry entries (and their tests,
mirroring tests/test_capability_registry.py::TestBoto3ServiceBindingResolution).

Suggest prioritizing by real-world usage/consequence: EC2 (instance
create/terminate/security-group changes), RDS (database create/delete/
snapshot), Lambda (function create/delete/update-code -- code-execution
surface), SNS/SQS (publish/send, lower severity), and Secrets Manager/
KMS (secret/key create/delete/rotate -- credential-adjacent, IAM-like
severity) are the next tier after S3/DynamoDB/IAM.
