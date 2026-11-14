//! The per-language effects capability tables for COH002, derived from the adapters' registry
//! vocabulary (`docs/design/grimble/rule-families.md` section 2.2). The types and `classify` live
//! in `gob_caps`; a language gets a capability only where its matrix `effects` cell is provided.

// frob:ticket 01M5M05N51MZ3RYXFYJT28A73Q

use std::collections::BTreeSet;
use std::sync::OnceLock;

use gob_caps::{Capability, EffectsCapability, Lang};
use tracing::debug;

/// Atom families whose callee names make a call an effect for COH002.
const EFFECT_ATOMS: [&str; 3] = ["fs", "net", "process"];

/// The qualifier segments and bare builtins the registry holds for `lang` under [`EFFECT_ATOMS`].
fn registry_names(lang: &str) -> (Vec<&'static str>, Vec<&'static str>) {
    let sep = if lang == "rust" { "::" } else { "." };
    let (mut qualifiers, mut builtins) = (BTreeSet::new(), BTreeSet::new());
    for atom in EFFECT_ATOMS {
        for (_, name) in crate::registry::callee_names(lang, atom) {
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

/// The names the registry holds for the COH002 vocabulary `class` in `lang`, sorted; empty when
/// the language declares none.
fn coh002_names(lang: &str, class: &str) -> Vec<&'static str> {
    match crate::registry::callee_vocab(lang, class) {
        crate::Answer::Exact(names) => names.into_iter().collect(),
        _ => Vec::new(),
    }
}

/// Leak a name list into the `'static` slice a capability holds (built once per language).
fn leak(names: Vec<&'static str>) -> &'static [&'static str] {
    Box::leak(names.into_boxed_slice())
}

/// Build the capability of `lang` entirely from the registry: IO qualifiers and builtins from the
/// fs/net/process atoms, plus the `coh002.*` method, qualifier and logging vocabularies.
fn build(lang: &'static str) -> EffectsCapability {
    let (mut qualifiers, builtins) = registry_names(lang);
    qualifiers.extend(coh002_names(lang, "coh002.qualifiers"));
    qualifiers.sort_unstable();
    qualifiers.dedup();
    let cap = EffectsCapability {
        lang,
        effect_qualifiers: leak(qualifiers),
        effect_builtins: leak(builtins),
        effect_methods: leak(coh002_names(lang, "coh002.methods")),
        trivial_qualifiers: leak(coh002_names(lang, "coh002.trivial.qualifiers")),
        trivial_names: leak(coh002_names(lang, "coh002.trivial.names")),
    };
    debug!(
        lang,
        qualifiers = cap.effect_qualifiers.len(),
        builtins = cap.effect_builtins.len(),
        methods = cap.effect_methods.len(),
        trivial_qualifiers = cap.trivial_qualifiers.len(),
        trivial_names = cap.trivial_names.len(),
        "effects derived from registry"
    );
    cap
}

/// The effects capability of a language tag, or `None` when its matrix `effects` cell is a gap.
pub fn effects_for(lang: &str) -> Option<&'static EffectsCapability> {
    static RUST: OnceLock<EffectsCapability> = OnceLock::new();
    static PYTHON: OnceLock<EffectsCapability> = OnceLock::new();
    static TYPESCRIPT: OnceLock<EffectsCapability> = OnceLock::new();
    if !Lang::from_tag(lang).is_some_and(|l| gob_caps::provides(l, Capability::Effects)) {
        return None;
    }
    match lang {
        "rust" => Some(RUST.get_or_init(|| build("rust"))),
        "python" => Some(PYTHON.get_or_init(|| build("python"))),
        "typescript" => Some(TYPESCRIPT.get_or_init(|| build("typescript"))),
        _ => None,
    }
}
