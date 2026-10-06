//! The adapter registry: built-in adapters plus those submitted with `inventory`.
//!
//! A crate that cannot be a dependency of gob-symbols (grimble-model) submits an
//! [`AdapterEntry`]; any binary that links it then sees the adapter in [`adapters`],
//! [`adapter_for`], [`adapter_for_path`] and [`fidelity_report`].

// frob:ticket 01M3ZEH3S0PG61C2AEBM691F69

use std::collections::BTreeMap;
use std::path::Path;
use std::sync::OnceLock;

use gob_walk::LanguageHint;

use crate::adapter::{Adapter, Capability, Fidelity, Precision};
use crate::csharp::CSharpAdapter;
use crate::markdown::MarkdownAdapter;
use crate::opaque::OpaqueAdapter;
use crate::python::PythonAdapter;
use crate::rust::RustAdapter;
use crate::typescript::{EXTENSIONS as TYPESCRIPT_EXTENSIONS, TypeScriptAdapter};
use crate::yaml::YamlAdapter;

static RUST: RustAdapter = RustAdapter;
static MARKDOWN: MarkdownAdapter = MarkdownAdapter;
static YAML: YamlAdapter = YamlAdapter;
static PYTHON: PythonAdapter = PythonAdapter;
// frob:ticket 01M44YQSZ3YEXRDW9RKER9HRA2
static CSHARP: CSharpAdapter = CSharpAdapter;
// frob:ticket 01M43ARXMH7RJ63G8096KKJF80
static TYPESCRIPT: TypeScriptAdapter = TypeScriptAdapter;
static OPAQUE: OpaqueAdapter = OpaqueAdapter;

/// Extensions (no dot, lowercase) claimed by the built-in adapters, by language.
const BUILTIN_EXTENSIONS: [(&str, &[&str]); 6] = [
    ("rust", &["rs"]),
    ("markdown", &["md", "markdown"]),
    ("yaml", &["yml", "yaml"]),
    ("python", &["py", "pyi"]),
    ("csharp", &["cs"]),
    ("typescript", TYPESCRIPT_EXTENSIONS),
];

/// A registrable adapter: submit one with `inventory::submit!` to make it visible here.
pub struct AdapterEntry {
    /// The adapter's `language()` tag; the registry sorts by it.
    pub language_name: &'static str,
    /// File extensions it claims, lowercase and without the dot.
    pub extensions: &'static [&'static str],
    /// Builds the adapter once; the registry keeps it for the process lifetime.
    pub construct: fn() -> Box<dyn Adapter>,
}

inventory::collect!(AdapterEntry);

/// A constructed registry entry.
struct Registered {
    entry: &'static AdapterEntry,
    adapter: &'static dyn Adapter,
}

/// Two entries claiming one extension; the earlier language name wins.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DuplicateExtension {
    /// The contested extension.
    pub extension: String,
    /// The language that keeps it.
    pub kept: &'static str,
    /// The language that lost it.
    pub dropped: &'static str,
}

struct Registry {
    registered: Vec<Registered>,
    by_ext: BTreeMap<&'static str, usize>,
    duplicates: Vec<DuplicateExtension>,
}

/// Maps each extension to the first claimant (entries must be pre-sorted), reporting clashes.
///
/// `reserved` holds extensions already owned by built-ins, as `(language, ext)`.
pub(crate) fn index_extensions(
    reserved: &[(&'static str, &'static str)],
    entries: &[&AdapterEntry],
) -> (BTreeMap<&'static str, usize>, Vec<DuplicateExtension>) {
    let mut owner: BTreeMap<&'static str, (&'static str, Option<usize>)> = reserved
        .iter()
        .map(|&(lang, ext)| (ext, (lang, None)))
        .collect();
    let mut dups = Vec::new();
    for (i, e) in entries.iter().enumerate() {
        for &ext in e.extensions {
            match owner.get(ext) {
                Some(&(kept, _)) => dups.push(DuplicateExtension {
                    extension: ext.to_owned(),
                    kept,
                    dropped: e.language_name,
                }),
                None => {
                    owner.insert(ext, (e.language_name, Some(i)));
                }
            }
        }
    }
    let by_ext = owner
        .into_iter()
        .filter_map(|(ext, (_, i))| i.map(|i| (ext, i)))
        .collect();
    (by_ext, dups)
}

fn registry() -> &'static Registry {
    static REG: OnceLock<Registry> = OnceLock::new();
    REG.get_or_init(|| {
        let mut entries: Vec<&'static AdapterEntry> = inventory::iter::<AdapterEntry>().collect();
        entries.sort_by_key(|e| (e.language_name, e.extensions));
        let reserved: Vec<(&'static str, &'static str)> = BUILTIN_EXTENSIONS
            .iter()
            .flat_map(|&(l, exts)| exts.iter().map(move |&e| (l, e)))
            .collect();
        let (by_ext, duplicates) = index_extensions(&reserved, &entries);
        for d in &duplicates {
            tracing::warn!(
                extension = %d.extension, kept = d.kept, dropped = d.dropped,
                "two adapters claim one extension"
            );
        }
        let registered = entries
            .into_iter()
            .map(|entry| {
                let adapter: &'static dyn Adapter = Box::leak((entry.construct)());
                tracing::info!(language = entry.language_name, "adapter registered");
                Registered { entry, adapter }
            })
            .collect();
        Registry {
            registered,
            by_ext,
            duplicates,
        }
    })
}

/// Extension clashes found while building the registry (empty when none).
pub fn registry_conflicts() -> Vec<DuplicateExtension> {
    registry().duplicates.clone()
}

/// Every real adapter (F1 and above): the built-ins, then registered ones by language name.
pub fn adapters() -> Vec<&'static dyn Adapter> {
    let mut out: Vec<&'static dyn Adapter> =
        vec![&RUST, &MARKDOWN, &YAML, &PYTHON, &CSHARP, &TYPESCRIPT];
    out.extend(registry().registered.iter().map(|r| r.adapter));
    out
}

/// The F0 adapter used for files no real adapter claims.
pub fn opaque_adapter() -> &'static dyn Adapter {
    &OPAQUE
}

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
/// The adapter claiming `hint`, or `None` for an adapter-less language.
pub fn adapter_for(hint: &LanguageHint) -> Option<&'static dyn Adapter> {
    match hint {
        LanguageHint::Rust => Some(&RUST),
        LanguageHint::Markdown => Some(&MARKDOWN),
        LanguageHint::Toml => None,
        LanguageHint::Other(ext) if matches!(ext.as_str(), "yml" | "yaml") => Some(&YAML),
        LanguageHint::Other(ext) if matches!(ext.as_str(), "py" | "pyi") => Some(&PYTHON),
        LanguageHint::Other(ext) if ext.as_str() == "cs" => Some(&CSHARP),
        LanguageHint::Other(ext) if TYPESCRIPT_EXTENSIONS.contains(&ext.as_str()) => {
            Some(&TYPESCRIPT)
        }
        LanguageHint::Other(ext) => {
            let reg = registry();
            reg.by_ext
                .get(ext.as_str())
                .map(|&i| reg.registered[i].adapter)
        }
    }
}

/// The adapter claiming `path` by its extension, or `None`.
pub fn adapter_for_path(path: &str) -> Option<&'static dyn Adapter> {
    let ext = Path::new(path)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_ascii_lowercase();
    adapter_for(&LanguageHint::from_path(&format!("x.{ext}")))
}

/// One row of [`fidelity_report`]: an adapter with its claims.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdapterReport {
    /// The adapter's language tag.
    pub language: &'static str,
    /// Extensions it claims (empty for the opaque adapter).
    pub extensions: Vec<&'static str>,
    /// Claimed fidelity.
    pub fidelity: Fidelity,
    /// Adapter identity (cache key component).
    pub identity: String,
    /// Every capability with its precision, in table order.
    pub capabilities: Vec<(Capability, Precision)>,
}

fn report_of(a: &dyn Adapter, extensions: Vec<&'static str>) -> AdapterReport {
    AdapterReport {
        language: a.language(),
        extensions,
        fidelity: a.fidelity(),
        identity: a.identity(),
        capabilities: a.capabilities().rows(),
    }
}

/// What `frob doctor --languages` lists: every adapter linked into this binary, then opaque.
pub fn fidelity_report() -> Vec<AdapterReport> {
    let mut out: Vec<AdapterReport> = Vec::new();
    for a in adapters() {
        let exts = BUILTIN_EXTENSIONS
            .iter()
            .find(|(l, _)| *l == a.language())
            .map(|(_, e)| e.to_vec())
            .or_else(|| {
                registry()
                    .registered
                    .iter()
                    .find(|r| r.adapter.language() == a.language())
                    .map(|r| r.entry.extensions.to_vec())
            })
            .unwrap_or_default();
        out.push(report_of(a, exts));
    }
    out.push(report_of(opaque_adapter(), Vec::new()));
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn entry(name: &'static str, exts: &'static [&'static str]) -> AdapterEntry {
        AdapterEntry {
            language_name: name,
            extensions: exts,
            construct: || Box::new(OpaqueAdapter),
        }
    }

    #[test]
    // frob:tests crates/gob-symbols/src/registry.rs::index_extensions
    fn a_duplicate_extension_keeps_the_first_claimant_and_is_reported() {
        let a = entry("aaa", &["x", "y"]);
        let b = entry("bbb", &["y", "z"]);
        let (by_ext, dups) = index_extensions(&[], &[&a, &b]);
        assert_eq!(by_ext.get("y"), Some(&0));
        assert_eq!(by_ext.get("z"), Some(&1));
        assert_eq!(
            dups,
            vec![DuplicateExtension {
                extension: "y".into(),
                kept: "aaa",
                dropped: "bbb"
            }]
        );
    }

    #[test]
    // frob:tests crates/gob-symbols/src/registry.rs::index_extensions
    fn a_builtin_extension_cannot_be_taken() {
        let a = entry("evil", &["rs"]);
        let (by_ext, dups) = index_extensions(&[("rust", "rs")], &[&a]);
        assert!(by_ext.is_empty());
        assert_eq!(dups[0].kept, "rust");
    }

    #[test]
    // frob:tests crates/gob-symbols/src/registry.rs::fidelity_report
    fn the_report_lists_builtins_then_opaque() {
        let r = fidelity_report();
        let langs: Vec<_> = r.iter().map(|a| a.language).collect();
        assert_eq!(&langs[..2], ["rust", "markdown"]);
        assert_eq!(*langs.last().expect("rows"), "opaque");
        assert!(registry_conflicts().is_empty());
        assert!(adapter_for_path("a/b.RS").is_some());
        assert!(adapter_for_path("a/b.zzz").is_none());
    }
}
