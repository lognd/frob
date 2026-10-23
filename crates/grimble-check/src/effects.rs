//! The effects capability of a language adapter, as COH002 consumes it (cohesion.md 1).
//!
//! An adapter that declares the capability classifies a call from its qualified path, not from
//! the bare callee name: `fs.write_file(..)` is an effect because `fs` is an IO module of the
//! language, `items.remove(x)` is not, because `remove` on an unknown receiver may be an in-memory
//! collection operation. Names the capability cannot place are [`EffectClass::Unknown`], never a
//! silent pass. A language without a capability is absent from [`effects_for`], and COH002 leaves
//! its verdict Unresolved instead of guessing.

// frob:ticket 01M5HJ07DTC2JQT9MP5T0TGDAS

use tracing::trace;

/// How an adapter classifies one call.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EffectClass {
    /// The call performs IO, messaging or persistence.
    Effect,
    /// Logging, metrics or assertion: never an effect.
    Trivial,
    /// The adapter cannot place the call (an alias, an import-bound name, an unknown receiver).
    Unknown,
}

/// One language's effects capability: the facts its adapter knows about what a call does.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct EffectsCapability {
    /// The language tag the capability belongs to (`rust`, `python`, `typescript`).
    pub lang: &'static str,
    /// Qualifier segments naming an IO module or type: any call through one is an effect.
    pub effect_qualifiers: &'static [&'static str],
    /// Bare callee names that are IO builtins of the language (`open`, `fetch`).
    pub effect_builtins: &'static [&'static str],
    /// Method names that are effects whatever the receiver (`send`, `write_all`, `commit`).
    pub effect_methods: &'static [&'static str],
    /// Qualifier segments naming a logging or metrics facility: any call through one is trivial.
    pub trivial_qualifiers: &'static [&'static str],
    /// Bare callee names that are trivial (`log`, `assert`, `print` free of IO guarantees).
    pub trivial_names: &'static [&'static str],
}

/// Methods that are effects on any receiver in every supported language.
const COMMON_METHODS: &[&str] = &[
    "write",
    "write_all",
    "writeln",
    "send",
    "send_all",
    "sendall",
    "emit",
    "publish",
    "dispatch",
    "save",
    "persist",
    "commit",
    "execute",
    "flush",
    "unlink",
];

/// Rust: `std::fs`, `std::process`, `std::net` paths and the channel and writer methods.
pub const RUST_EFFECTS: EffectsCapability = EffectsCapability {
    lang: "rust",
    effect_qualifiers: &[
        "fs",
        "File",
        "OpenOptions",
        "process",
        "Command",
        "net",
        "TcpStream",
    ],
    effect_builtins: &[],
    effect_methods: COMMON_METHODS,
    trivial_qualifiers: &["log", "logger", "tracing"],
    trivial_names: &[
        "log",
        "debug",
        "info",
        "warn",
        "error",
        "trace",
        "assert",
        "debug_assert",
        "assert_eq",
        "assert_ne",
        "debug_assert_eq",
        "debug_assert_ne",
    ],
};

/// Python: `os`, `shutil`, `subprocess`, `socket`, `requests` and the builtin `open`.
pub const PYTHON_EFFECTS: EffectsCapability = EffectsCapability {
    lang: "python",
    effect_qualifiers: &[
        "os",
        "shutil",
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "sqlite3",
    ],
    effect_builtins: &["open"],
    effect_methods: COMMON_METHODS,
    trivial_qualifiers: &["logging", "logger", "log", "warnings"],
    trivial_names: &[
        "log", "debug", "info", "warning", "error", "critical", "assert",
    ],
};

/// TypeScript: `fs`, `child_process`, `http` and the builtin `fetch`; `console` is trivial.
pub const TYPESCRIPT_EFFECTS: EffectsCapability = EffectsCapability {
    lang: "typescript",
    effect_qualifiers: &[
        "fs",
        "child_process",
        "http",
        "https",
        "axios",
        "localStorage",
    ],
    effect_builtins: &["fetch"],
    effect_methods: COMMON_METHODS,
    trivial_qualifiers: &["console", "logger", "log"],
    trivial_names: &["log", "debug", "info", "warn", "error", "assert"],
};

/// The effects capability of a language tag, or `None` when its adapter does not declare one.
pub fn effects_for(lang: &str) -> Option<&'static EffectsCapability> {
    match lang {
        "rust" => Some(&RUST_EFFECTS),
        "python" => Some(&PYTHON_EFFECTS),
        "typescript" => Some(&TYPESCRIPT_EFFECTS),
        _ => None,
    }
}

impl EffectsCapability {
    /// Classify a call by its head `path` (qualifier segments, then the callee name last).
    ///
    /// Trivial wins over effect; a qualifier decides before the bare name; an empty path or a
    /// name the capability cannot place is [`EffectClass::Unknown`].
    pub fn classify(&self, path: &[String]) -> EffectClass {
        let Some((name, qualifiers)) = path.split_last() else {
            return EffectClass::Unknown;
        };
        let has = |set: &[&str]| qualifiers.iter().any(|q| set.contains(&q.as_str()));
        let class = if has(self.trivial_qualifiers) || self.trivial_names.contains(&name.as_str()) {
            EffectClass::Trivial
        } else if has(self.effect_qualifiers)
            || self.effect_methods.contains(&name.as_str()) && !qualifiers.is_empty()
            || self.effect_builtins.contains(&name.as_str()) && qualifiers.is_empty()
        {
            EffectClass::Effect
        } else {
            EffectClass::Unknown
        };
        trace!(
            lang = self.lang,
            ?path,
            ?class,
            "effects capability classified a call"
        );
        class
    }
}
