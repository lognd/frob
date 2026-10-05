+++
id = "01M44YQXS4BXE0X07FBYR0STJ5"
title = "unity vocabulary pack: skeleton, registration and engine entry points as reach roots"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:37:01Z"
updated = "2026-10-05T02:37:01Z"
idempotency_key = "d94-pack"
scope = ["crates/gob-ir/**", "crates/gob-packs/**", "crates/frob-tests/src/reach.rs", "crates/frob-obligations/src/cov.rs", "crates/frob-obligations/src/refs.rs", "packs/unity.toml", "docs/design/packs.md", "docs/reference/config.md"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FKFSHB8KZM2N4CNF0P9"

[[links]]
kind = "blocked-by"
target = "01M3ZX7JRYNHG0BHJ3ZHC9450N"

[[links]]
kind = "blocked-by"
target = "01M44YQVN6PMK0D8NJ801ENJEW"

[[links]]
kind = "blocked-by"
target = "01M44YQWGP5553K61QKC8HB0GQ"

[[acceptance]]
text = "Given the unity pack enabled and a MonoBehaviour subclass whose Update method has no caller, when reach is computed, then Update is a root and is not reported as unreached"
bound = false

[[acceptance]]
text = "Given the same code with the unity pack disabled, when reach is computed, then Update is reported as unreached"
bound = false

[[acceptance]]
text = "Given a [MenuItem] static method in an editor assembly, when the pack is enabled, then it is a reach root"
bound = false

[[acceptance]]
text = "Given the pack file, when frob check runs the pack validators, then no PACK finding is raised"
bound = false
+++

Add the opt-in built-in pack `unity` (packs.md 3.2: a packs/unity.toml embedded through gob_ir::builtin_pack!, entries in crates/gob-ir registry, validated by crates/gob-packs manifest and validate) and its first vocabulary: engine entry points. MonoBehaviour and ScriptableObject messages (Awake, Start, Update, FixedUpdate, LateUpdate, OnEnable, OnDisable, OnDestroy, OnValidate, Reset, OnGUI, OnDrawGizmos*, OnTrigger*, OnCollision*, OnMouse*, OnApplicationQuit) on types deriving from those bases (base-type facts from the sym story, transitively through project-local bases), plus methods carrying [RuntimeInitializeOnLoadMethod], [InitializeOnLoad] (its static constructor), [MenuItem], [ContextMenu] and [CreateAssetMenu] types, are reach roots: reach, COV and dead-code rules treat them as called by the engine (crates/frob-tests/src/reach.rs, crates/frob-obligations/src/cov.rs and refs.rs). Disabled by default; enabled by config, never by the adapter. Blocked on the pack content and registry-merge tickets (~HC9450N tier-1 pack content, ~4CNF0P9 registry merge) which provide the mechanism. Docs: docs/design/packs.md (pack list and counts), docs/reference/config.md.
