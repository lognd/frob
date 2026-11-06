# v1 migration history

Status: historical
Owner: frob
Decisions: D36, D95
Audience: contributor

Provenance: cut out of docs/design/frob/migration.md under ~XPA3A54. Text is kept as it was written. The current instructions are in the [upgrade guide](../migration/upgrade-from-v1.md), which states the v1 to v2 field mapping once; the dropped v1 fields and their reasons are in the [v1 import report](../migration/v1-import.md).

## Rollout plan (as first written)

1. v2 reaches self-hosting on this repo (its own tickets, its own check);
   this repository's own `frob.lock` is empty today and is regenerated
   once the digest scheme is final. The milestone-2 order that gates the
   later steps is build-test-ci.md, Milestone 2.
2. Install side by side as `frob2`; run both on typani and crunk;
   compare findings (`frob2 compare --against frob`) until the diff is
   explained.
3. Consumer repos migrate one at a time with `frob2 migrate`, blocked
   until the digest scheme is final (otherwise every imported ack would
   drift when the scheme lands); v1 stays installed until the fleet is
   converted.
4. `frob2` becomes `frob`; v1 archived as the `v1` branch.

