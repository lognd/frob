//! The per-language fidelity report of the sibling document (sibling-contract 3.4).

use std::collections::BTreeMap;

use gob_ir::registry::{atoms, detectors};
use gob_ir::{Answer, DetectorKind};
use gob_symbols::{Adapter, adapters, opaque_adapter};
use serde_json::{Value, json};

/// The language tag of files no adapter claims.
pub const OPAQUE: &str = "opaque";

/// The language tag of a walked file: its registered adapter's, else [`OPAQUE`].
///
/// `.grmb` resolves to `grmb` because `grimble-model` registers its adapter at link time.
pub fn language_tag(path: &str, _hint: &gob_walk::LanguageHint) -> &'static str {
    gob_symbols::adapter_for_path(path).map_or(OPAQUE, |a| a.language())
}

/// Every adapter linked into this binary (rust, markdown, grmb, ...) then the opaque fallback.
pub fn known_adapters() -> Vec<&'static dyn Adapter> {
    let mut all = adapters();
    all.push(opaque_adapter());
    all
}

/// `typed`, `lexical`, `none` or `not_applicable`: the answer of `detectors(lang, atom)` as a precision word.
///
/// A callee-name or lexical detector is `lexical`; any structural detector (import, attribute,
/// macro, pattern) is `typed`; no declaration is `none`.
pub fn precision_of(atom: &str, lang: &str) -> &'static str {
    match detectors(atom, lang) {
        Answer::Exact(kinds)
            if kinds.iter().any(|k| {
                matches!(
                    k,
                    DetectorKind::Import
                        | DetectorKind::Attribute
                        | DetectorKind::Macro
                        | DetectorKind::Pattern
                )
            }) =>
        {
            "typed"
        }
        Answer::Exact(_) => "lexical",
        Answer::NotApplicable => "not_applicable",
        Answer::Bounds { .. } | Answer::Unknown => "none",
    }
}

/// The capability matrix row of `lang`: every registered atom with its precision word.
pub fn capabilities_of(lang: &str) -> BTreeMap<String, &'static str> {
    atoms()
        .into_iter()
        .map(|a| (a.name.to_owned(), precision_of(a.name, lang)))
        .collect()
}

/// `(adapter, adapter_version)` split out of an adapter identity such as `gob-symbols/v3/grammar`.
fn name_and_version(identity: &str, language: &str) -> (String, String) {
    match identity.split_once("/v") {
        Some((name, rest)) => {
            let version = rest.split('/').next().unwrap_or("0").to_owned();
            let adapter = if name == "gob-symbols" {
                format!("gob-symbols/{language}")
            } else {
                name.to_owned()
            };
            (adapter, version)
        }
        None => (identity.to_owned(), "0".to_owned()),
    }
}

/// One fidelity entry per language in `seen` (adapter tag to file count), sorted by language.
///
/// `grmb` is always present: it is grimble's own language and the run read the model through it.
pub fn fidelity_json(seen: &BTreeMap<String, usize>) -> Vec<Value> {
    let mut rows: BTreeMap<String, Value> = BTreeMap::new();
    for a in known_adapters() {
        let language = a.language();
        if language != "grmb" && !seen.contains_key(language) {
            continue;
        }
        let (adapter, adapter_version) = name_and_version(&a.identity(), language);
        rows.insert(
            language.to_owned(),
            json!({
                "language": language,
                "adapter": adapter,
                "adapter_version": adapter_version,
                "level": a.fidelity().to_string(),
                "capabilities": capabilities_of(language),
                "not_applicable_rules": Vec::<String>::new(),
            }),
        );
    }
    rows.into_values().collect()
}
