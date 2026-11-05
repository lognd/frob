//! The effects capability of a language adapter, as COH002 consumes it (`docs/design/grimble/rule-families.md` section 2.2).
//!
//! An adapter that declares the capability classifies a call from its qualified path, not from
//! the bare callee name: `fs.write_file(..)` is an effect because `fs` is an IO module of the
//! language, `items.remove(x)` is not, because `remove` on an unknown receiver may be an in-memory
//! collection operation. Names the capability cannot place are [`EffectClass::Unknown`], never a
//! silent pass. A language without a capability is absent from [`effects_for`], and COH002 leaves
//! its verdict Unresolved instead of guessing.

// frob:ticket 01M5HJ07DTC2JQT9MP5T0TGDAS

use std::collections::BTreeSet;
use std::sync::OnceLock;

use tracing::{debug, trace};

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

/// Atom families whose callee names make a call an effect for COH002.
const EFFECT_ATOMS: [&str; 3] = ["fs", "net", "process"];

/// The qualifier segments and bare builtins the registry holds for `lang` under [`EFFECT_ATOMS`].
fn registry_names(lang: &str) -> (Vec<&'static str>, Vec<&'static str>) {
    let sep = if lang == "rust" { "::" } else { "." };
    let (mut qualifiers, mut builtins) = (BTreeSet::new(), BTreeSet::new());
    for atom in EFFECT_ATOMS {
        for (_, name) in gob_ir::registry::callee_names(lang, atom) {
            let bare = name.trim_end_matches('*').trim_end_matches(['.', ':']);
            if name.starts_with('.') || bare.is_empty() || (lang == "rust" && bare.contains('.')) {
                continue; // receiver-typed forms are the binder's
            }
            match bare.split_once(sep) {
                Some((head, _)) => qualifiers.insert(head),
                None if bare != name => qualifiers.insert(bare),
                None => builtins.insert(bare),
            };
        }
    }
    (
        qualifiers.into_iter().collect(),
        builtins.into_iter().collect(),
    )
}

/// Build the capability of `lang`: IO qualifiers and builtins from the registry, plus the
/// language's logging facts.
fn build(
    lang: &'static str,
    trivial_qualifiers: &'static [&'static str],
    trivial_names: &'static [&'static str],
) -> EffectsCapability {
    let (qualifiers, builtins) = registry_names(lang);
    debug!(
        lang,
        qualifiers = qualifiers.len(),
        builtins = builtins.len(),
        "effects derived from registry"
    );
    EffectsCapability {
        lang,
        effect_qualifiers: Box::leak(qualifiers.into_boxed_slice()),
        effect_builtins: Box::leak(builtins.into_boxed_slice()),
        effect_methods: COMMON_METHODS,
        trivial_qualifiers,
        trivial_names,
    }
}

/// The effects capability of a language tag, or `None` when its adapter does not declare one.
pub fn effects_for(lang: &str) -> Option<&'static EffectsCapability> {
    static RUST: OnceLock<EffectsCapability> = OnceLock::new();
    static PYTHON: OnceLock<EffectsCapability> = OnceLock::new();
    static TYPESCRIPT: OnceLock<EffectsCapability> = OnceLock::new();
    match lang {
        "rust" => Some(RUST.get_or_init(|| {
            build(
                "rust",
                &["log", "logger", "tracing"],
                &[
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
            )
        })),
        "python" => Some(PYTHON.get_or_init(|| {
            build(
                "python",
                &["logging", "logger", "log", "warnings"],
                &[
                    "log", "debug", "info", "warning", "error", "critical", "assert",
                ],
            )
        })),
        "typescript" => Some(TYPESCRIPT.get_or_init(|| {
            build(
                "typescript",
                &["console", "logger", "log"],
                &["log", "debug", "info", "warn", "error", "assert"],
            )
        })),
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

// frob:ticket 01M642307T98S89GQ4APKW7X2J
#[cfg(test)]
mod registry_agreement {
    use super::effects_for;
    use std::collections::BTreeSet;

    /// Every first segment and bare name the registry holds for `lang` over all atoms.
    fn registered_heads(lang: &str) -> BTreeSet<&'static str> {
        let sep = if lang == "rust" { "::" } else { "." };
        let mut out = BTreeSet::new();
        for atom in gob_ir::registry::atoms() {
            for (_, name) in gob_ir::registry::callee_names(lang, atom.name) {
                let bare = name.trim_end_matches('*').trim_end_matches(['.', ':']);
                out.insert(bare.split(sep).next().unwrap_or(bare));
            }
        }
        out
    }

    // frob:tests crates/grimble-check/src/effects.rs::effects_for
    #[test]
    fn every_effect_qualifier_and_builtin_is_in_the_capability_registry() {
        for lang in ["rust", "python", "typescript"] {
            let heads = registered_heads(lang);
            let cap = effects_for(lang).expect("language has a capability");
            assert!(
                !cap.effect_qualifiers.is_empty(),
                "{lang} has no qualifiers"
            );
            for name in cap.effect_qualifiers.iter().chain(cap.effect_builtins) {
                assert!(
                    heads.contains(name),
                    "{lang}: {name} is not a registry name"
                );
            }
        }
        let ts = effects_for("typescript").unwrap();
        assert!(ts.effect_builtins.contains(&"fetch"));
        assert!(ts.effect_qualifiers.contains(&"fs"));
    }
}
