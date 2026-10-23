//! Syntactic detectors behind grimble's universal lint rules.
//!
//! [`err::scan`] finds swallowed errors (`ERR001` empty handler, `ERR002` discarded fallible
//! result, `ERR003` catch-all that neither rethrows nor logs) in Rust, Python, TypeScript and C#
//! from the tree-sitter parse of one file. It only reports sites; mapping a site to a severity
//! (an [`err::Certainty::Unknown`] site is Unresolved, never Warn) belongs to the rule that
//! consumes it.
//!
//! [`res::scan`] finds acquire calls with no paired release in scope (`performance.mark`,
//! `Map.set`, `setTimeout`, `addEventListener`, ...) in TypeScript and JavaScript from a table of
//! acquire/release pairs ([`res::PAIRS`]); a new pair is a data change.
//!
//! [`effect::scan`] is the React vocabulary of `PAIR001`: a `useEffect` that starts a fetch, timer,
//! listener, observer or subscription without a returned cleanup that undoes it, from a table of
//! effect-started pairs ([`effect::PAIRS`]).
//!
//! [`pair_pass::analyze`] runs [`effect::scan`] (TS/JS) and [`unity::scan`] (Unity C#) over the walked files and returns the `PAIR001`
//! verdicts for the product; the rule is declared in [`rules`] and staged like the TIME rules.
//!
//! [`unity::scan`] is the Unity vocabulary of `PAIR001`: a C# event subscription, `RegisterCallback`,
//! `UnityEvent` listener, input action `Enable` or Addressables load made in `Awake`, `Start` or
//! `OnEnable` that no `OnDisable` or `OnDestroy` undoes, from a table of pairs ([`unity::PAIRS`]).
//!
//! [`unity_input::scan`] finds `UNITY301`: the legacy `Input` class used when the project's
//! `activeInputHandler` ([`unity_input::active_input_handler`]) is the Input System.
//!
//! [`unity_physics::scan`] finds `UNITY302`: a Rigidbody force or move, or a `transform` move of a
//! Rigidbody object, made from `Update` or `LateUpdate` rather than `FixedUpdate`. Both share the
//! [`unity_common::Finding`] shape and the preprocessor-aware walk in [`unity_common`].
//!
//! [`unity_hot::scan`] finds `UNITY201` (a component or scene lookup, `Camera.main`) and `UNITY202`
//! (a managed collection or array allocated) in hot code: `Update`-style callbacks and the
//! same-class methods they reach. Both are Advisory; `Awake` and `Start` are not hot.
//!
//! [`unity_pass::analyze`] runs [`unity_hot::scan`] over the walked Unity C# files and returns the
//! `UNITY201` and `UNITY202` verdicts for the product; the rules are declared in [`rules`].
//! [`unity_pass::analyze_all`] adds `UNITY301` (legacy `Input` under the Input System handler,
//! read from `ProjectSettings/ProjectSettings.asset`) and `UNITY302` (a Rigidbody force from
//! `Update`), both Warn.
//!
//! [`path::scan`] finds `PATH001` absolute host path literals and, for Rust and Python, `PATH002`
//! path-to-string separator handling and `PATH003` paths in command-line strings; a language
//! without path-conversion roles reports them unresolved.
//!
//! [`pass::analyze`] runs [`path::scan`] over the walked files and returns the `PATH001` to
//! `PATH003` verdicts for the product; the rules are declared in [`rules`] and staged like the
//! architecture rules.
//!
//! [`time::scan`] finds `TIME001` local or zone-less clock reads whose value is stored or sent and
//! `TIME002` naive/aware datetime mixes, for Rust and Python; a language without clock roles
//! reports them unresolved.
//!
//! [`testq::scan`] finds `TESTQ001` tests with no assertion (a helper out of sight makes it
//! Unknown), `TESTQ002` sleeps, wall-clock reads and unseeded random sources in a test body, and
//! `TESTQ003` control flow in a test body (off by default), for Rust, Python, TypeScript,
//! JavaScript and `C#` tests.
//!
//! [`neat::scan`] finds `NEAT010` effect claims a unit's calls contradict (an `effects` capability
//! answering [`gob_ir::Answer`] bounds) and `NEAT031` dispatchers that own condition logic, in Rust.
//!
//! [`typing::scan`] finds `TYPING001` sites: a tsconfig with `strict` off, a csproj without
//! `<Nullable>enable</Nullable>`, or a lax mypy or pyright table, each naming the key to set.

// frob:ticket 01M4D956T20WN96P7A3K4B9CKF

pub mod effect;
pub mod err;
pub mod host;
pub mod neat;
pub mod pair_pass;
pub mod pass;
pub mod path;
pub mod res;
pub mod rules;
pub(crate) mod syntax;
pub mod testq;
pub mod time;
pub mod time_pass;
pub mod typing;
pub mod unity;
pub mod unity_common;
pub mod unity_hot;
pub mod unity_input;
pub mod unity_pass;
pub mod unity_physics;
