+++
id = "01M1T07NW8K8QP6PXTM4RBRQHB"
title = "refs.artifact: declared surface for verbatim build-output directories"
type = "security"
category = "triage"
priority = "low"
parent = "01M1QDTYTRW714S858S0TP6YWM"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-04T21:05:06Z"
aliases = ["T-3976"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/gates/_refs_schema.py"]

[[acceptance]]
text = "given a design note deciding what watched means for an artifact glob (annotation-required vs content-scanned), when this ticket's design step completes, then the note is attached before implementation"
bound = false

[[acceptance]]
text = "given the proposed refs.artifact construct is implemented (named in prose, not in double-bracket TOML form: as a literal section header it parses as a live config pointer and DOC006 correctly refuses it, because no such key exists yet), when a file under a declared artifact glob changes with no reasoned annotation, then it is flagged the same way an undeclared entrypoint change is today"
bound = false
+++

T-3928 frontend-unique item. VERIFIED: git grep confirms [[refs.entrypoint]] exists (src/frob/gates/_refs_schema.py, REFSCHEMA001) as a declared-surface concept, but it is for CODE entrypoints -- nothing declares a build-output/static-asset surface.

FINDING THIS WOULD HAVE CAUGHT: frontend/public/** (or equivalent verbatim-copy build directories) is outside every strata code glob and every frob entrypoint, yet ships to production byte-for-byte. The consumer's framing, worth preserving: "files that reach production without passing through a compiler is the highest-leverage unwatched surface in any frontend repo" -- these files get zero review pressure from anything frob does today because nothing treats them as reachable/shippable at all.

Proposed: a refs.artifact construct alongside the existing refs.entrypoint one (both named in prose here, not in literal double-bracket TOML form -- refs.artifact does not exist yet, so as a literal section header it parses as a live config pointer and DOC006 correctly refuses it), each file individually justified (mirroring entrypoint's own per-entry reason= discipline visible in _refs_schema.py), declaring a verbatim-copy build/static directory as a watched surface. What "watched" means in practice (min: a change to a declared artifact glob requires a reasoned annotation; ambitious: some content check e.g. no obvious secret/credential pattern) is a design decision to make explicit before implementing.

frob:waive DOC006 reason="the remaining DOC006 finding on this ticket is in the ledger's own `old_text:` audit field, which records the criterion text as it read BEFORE it was corrected. That field is by construction a historical record of text that is no longer live, and `frob ticket accept --amend` -- the sanctioned mechanism for making this exact correction -- is what wrote it. So amending to remove the violation re-creates it, and no amount of further amending can clear it: a no-exit. The live prose has already been fixed to name refs.artifact as prose rather than a literal TOML section header. The structural fix (exempt the old_text audit field from DOC006) is T-3979; this waiver covers only the historical record, not any live pointer" follow_up="T-3979"


T-4025 item 8, cross-referenced rather than filed as a second construct -- CHECKED per the coordinator's instruction: this ticket's own refs.artifact proposal (declaring a verbatim-copy build/static directory as a watched surface, each file/glob individually justified) is the right home for both of item 8's findings: a post-build step that deletes the entry bundle (a build-output correctness property) and 138MB of tracked binaries shipping in dist/ (a build-output size/content property). Both are "properties of build OUTPUT, entirely outside frob's graph" in exactly the way this ticket already frames the problem. Fold both into this ticket's design step as concrete motivating cases for what "watched" should mean in practice: the entry-bundle-deletion case argues for the content-scanned option (verify the declared artifact glob's expected files are actually present after build, not just that changes to them are annotated) rather than the cheaper annotation-only option: an annotation alone would not have caught a build step silently DELETING a file that should exist.
