//! The embedded core-effects pack (packs.md 8.1): atoms, vocabularies and detectors as data.
//!
//! `packs/core-effects/atoms.toml` is the single source of the 18 core atoms, their parents,
//! typed arguments, severities, callee vocabularies, detector rows, the receiver-type gates and
//! the non-process crate list. It is parsed once and interned as the `core-effects` owner; the
//! lock in `grimble.packs.lock` pins its version.

// frob:ticket 01M5XNNHV9M8HCP76TD867GGVJ

use std::collections::BTreeMap;
use std::sync::OnceLock;

use serde::Deserialize;

use crate::registry::{AtomEntry, DetectorEntry, DetectorKind, VocabEntry};

/// The owner name the core pack's atoms are registered under.
pub const OWNER: &str = "core-effects";

/// The embedded `pack.toml` of the core pack.
pub const PACK_TOML: &str = include_str!("../../../packs/core-effects/pack.toml");

/// The embedded `atoms.toml` of the core pack.
pub const ATOMS_TOML: &str = include_str!("../../../packs/core-effects/atoms.toml");

/// Pack-level facts about one core atom that [`AtomEntry`] does not carry.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AtomMeta {
    /// Dotted atom name.
    pub name: &'static str,
    /// The atom this one refines (`net` for `net.connect`), if any.
    pub parent: Option<&'static str>,
    /// The typed-argument kind of the atom (`path`, `host`, `env_name`, `binary`), if any.
    pub arg_kind: Option<&'static str>,
    /// Argument slot names the atom's grants may constrain.
    pub args: Vec<&'static str>,
    /// CWE identifiers the atom maps to.
    pub cwe: Vec<&'static str>,
    /// Severity per rule id (`CAP001`, `CAP002`).
    pub severity: BTreeMap<&'static str, &'static str>,
}

/// Methods that name a capability only through the receiver's type (a socket, an archive).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReceiverFamily {
    /// Language tag.
    pub lang: &'static str,
    /// The module a file must reach for an untyped receiver to be a May use.
    pub module: &'static str,
    /// Qualified constructors whose result is a receiver of this family.
    pub ctors: Vec<&'static str>,
    /// `(atom, method)` pairs: calling `method` on such a receiver uses `atom`.
    pub methods: Vec<(&'static str, &'static str)>,
}

struct Loaded {
    atoms: Vec<&'static AtomEntry>,
    vocabs: Vec<&'static VocabEntry>,
    meta: Vec<AtomMeta>,
    families: Vec<ReceiverFamily>,
    non_process: Vec<&'static str>,
}

#[derive(Deserialize)]
struct File {
    #[serde(default)]
    atom: Vec<AtomRow>,
    #[serde(default)]
    vocab: Vec<VocabRow>,
    #[serde(default)]
    detector: Vec<DetectorRow>,
    #[serde(default)]
    receiver_family: Vec<FamilyRow>,
    #[serde(default)]
    non_process: NonProcessRow,
}

#[derive(Deserialize)]
struct AtomRow {
    name: String,
    #[serde(default)]
    aliases: Vec<String>,
    #[serde(default)]
    parent: Option<String>,
    #[serde(default)]
    arg_kind: Option<String>,
    #[serde(default)]
    args: Option<String>,
    #[serde(default)]
    cwe: Vec<String>,
    #[serde(default)]
    severity: BTreeMap<String, String>,
}

#[derive(Deserialize)]
struct VocabRow {
    lang: String,
    class: String,
    names: Vec<String>,
}

#[derive(Deserialize)]
#[serde(untagged)]
enum Many {
    One(String),
    List(Vec<String>),
}

#[derive(Deserialize)]
struct DetectorRow {
    atom: Option<String>,
    atoms: Option<Many>,
    lang: Option<String>,
    langs: Option<Vec<String>>,
    kind: String,
}

#[derive(Deserialize)]
struct FamilyRow {
    lang: String,
    module: String,
    ctors: Vec<String>,
    methods: Vec<String>,
}

#[derive(Deserialize, Default)]
struct NonProcessRow {
    #[serde(default)]
    crates: Vec<String>,
}

fn leak(s: String) -> &'static str {
    Box::leak(s.into_boxed_str())
}

fn leak_all(v: Vec<String>) -> Vec<&'static str> {
    v.into_iter().map(leak).collect()
}

fn kind_of(kind: &str) -> Option<DetectorKind> {
    match kind {
        "callee" => Some(DetectorKind::Callee),
        "query" => Some(DetectorKind::Import),
        "attribute" => Some(DetectorKind::Attribute),
        "pattern" => Some(DetectorKind::Pattern),
        "impossible" => Some(DetectorKind::NotApplicable),
        _ => None,
    }
}

/// Expands the detector rows (`atoms = "*"` means every leaf atom) into per-atom entries.
fn detector_rows(file: &File) -> BTreeMap<String, Vec<DetectorEntry>> {
    let names: Vec<&str> = file.atom.iter().map(|a| a.name.as_str()).collect();
    let is_leaf = |n: &str| {
        !names
            .iter()
            .any(|o| o.strip_prefix(n).is_some_and(|r| r.starts_with('.')))
    };
    let mut dets: BTreeMap<String, Vec<DetectorEntry>> = BTreeMap::new();
    for d in &file.detector {
        let Some(kind) = kind_of(&d.kind) else {
            continue;
        };
        let targets: Vec<String> = match (&d.atom, &d.atoms) {
            (Some(a), _) => vec![a.clone()],
            (None, Some(Many::One(s))) if s == "*" => names
                .iter()
                .filter(|n| is_leaf(n))
                .map(|n| (*n).to_owned())
                .collect(),
            (None, Some(Many::One(s))) => vec![s.clone()],
            (None, Some(Many::List(l))) => l.clone(),
            (None, None) => Vec::new(),
        };
        let langs: Vec<String> = match (&d.lang, &d.langs) {
            (Some(l), _) => vec![l.clone()],
            (None, Some(ls)) => ls.clone(),
            (None, None) => Vec::new(),
        };
        for t in &targets {
            for l in &langs {
                dets.entry(t.clone()).or_default().push(DetectorEntry {
                    lang: leak(l.clone()),
                    kind,
                });
            }
        }
    }
    dets
}

/// Parses the embedded atoms file; a malformed core pack is a build bug, not a runtime state.
fn parse(text: &str) -> Loaded {
    let file: File =
        toml::from_str(text).expect("core-effects atoms.toml is valid (checked by tests)");
    let mut dets = detector_rows(&file);
    let mut atoms = Vec::new();
    let mut meta = Vec::new();
    for a in file.atom {
        let name = leak(a.name.clone());
        let detectors: &'static [DetectorEntry] =
            Vec::leak(dets.remove(&a.name).unwrap_or_default());
        let aliases: &'static [&'static str] = Vec::leak(leak_all(a.aliases));
        atoms.push(&*Box::leak(Box::new(AtomEntry {
            name,
            aliases,
            detectors,
        })));
        meta.push(AtomMeta {
            name,
            parent: a.parent.map(leak),
            arg_kind: a.arg_kind.map(leak),
            args: a
                .args
                .map(|s| s.split(',').map(|p| leak(p.trim().to_owned())).collect())
                .unwrap_or_default(),
            cwe: leak_all(a.cwe),
            severity: a
                .severity
                .into_iter()
                .map(|(k, v)| (leak(k), leak(v)))
                .collect(),
        });
    }
    let vocabs = file
        .vocab
        .into_iter()
        .map(|v| {
            let names: &'static [&'static str] = Vec::leak(leak_all(v.names));
            &*Box::leak(Box::new(VocabEntry {
                lang: leak(v.lang),
                kind: leak(v.class),
                names,
            }))
        })
        .collect();
    let families = file
        .receiver_family
        .into_iter()
        .map(|f| ReceiverFamily {
            lang: leak(f.lang),
            module: leak(f.module),
            ctors: leak_all(f.ctors),
            methods: f
                .methods
                .into_iter()
                .filter_map(|m| {
                    m.split_once(':')
                        .map(|(a, b)| (leak(a.to_owned()), leak(b.to_owned())))
                })
                .collect(),
        })
        .collect();
    tracing::debug!(atoms = atoms.len(), "core-effects pack parsed");
    Loaded {
        atoms,
        vocabs,
        meta,
        families,
        non_process: leak_all(file.non_process.crates),
    }
}

fn loaded() -> &'static Loaded {
    static LOADED: OnceLock<Loaded> = OnceLock::new();
    LOADED.get_or_init(|| parse(ATOMS_TOML))
}

/// The core pack's atoms (the 18 of packs.md 8.1 plus the retained `code.eval` and `ffi`).
pub fn atoms() -> &'static [&'static AtomEntry] {
    &loaded().atoms
}

/// The core pack's callee vocabularies.
pub fn vocabs() -> &'static [&'static VocabEntry] {
    &loaded().vocabs
}

/// Pack metadata (parent, argument kind, severities) of the core atom `name` or one of its aliases.
pub fn meta(name: &str) -> Option<&'static AtomMeta> {
    let l = loaded();
    let canon = l
        .atoms
        .iter()
        .find(|a| a.name == name || a.aliases.contains(&name))?
        .name;
    l.meta.iter().find(|m| m.name == canon)
}

/// The receiver-type families declared for `lang` (sockets, archives).
pub fn receiver_families(lang: &str) -> impl Iterator<Item = &'static ReceiverFamily> {
    let lang = lang.to_owned();
    loaded().families.iter().filter(move |f| f.lang == lang)
}

/// Crates whose `Command` is a builder type rather than a process spawn.
pub fn non_process_crates() -> &'static [&'static str] {
    &loaded().non_process
}

/// Whether `name` is a grouping atom: another core atom names it as its parent, so a use is
/// detected through its children and the grouping atom carries no callee vocabulary of its own.
pub fn is_grouping(name: &str) -> bool {
    loaded().meta.iter().any(|m| m.parent == Some(name))
}

/// Whether `name` is an atom (or alias) the core pack declares.
pub fn declares(name: &str) -> bool {
    loaded()
        .atoms
        .iter()
        .any(|a| a.name == name || a.aliases.contains(&name))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Answer;
    use crate::registry;

    const PACKS_MD_8_1: [&str; 18] = [
        "fs",
        "fs.read",
        "fs.write",
        "net",
        "net.connect",
        "net.listen",
        "env",
        "env.read",
        "env.write",
        "clock",
        "rng",
        "stdio",
        "stdio.read",
        "stdio.write",
        "exit",
        "process",
        "process.spawn",
        "unsafe",
    ];

    // frob:tests crates/gob-ir/src/registry.rs::atom
    #[test]
    fn every_atom_of_packs_md_8_1_resolves() {
        for name in PACKS_MD_8_1 {
            assert!(declares(name), "{name} is not declared by core-effects");
            assert_eq!(registry::canonical(name), Some(name), "{name} must resolve");
        }
        assert_eq!(registry::canonical("process.env"), Some("env.read"));
        assert_eq!(registry::canonical("exec"), Some("process.spawn"));
    }

    // frob:tests crates/gob-ir/src/registry.rs::detectors
    #[test]
    fn every_leaf_atom_has_rust_and_python_detector_rows() {
        for name in PACKS_MD_8_1.iter().filter(|n| !is_grouping(n)) {
            for lang in ["rust", "python"] {
                assert!(
                    !matches!(registry::detectors(name, lang), Answer::Unknown),
                    "{name} has no {lang} detector row"
                );
            }
        }
    }

    // frob:tests crates/gob-ir/src/core_pack.rs::meta
    #[test]
    fn parents_and_argument_kinds_are_pack_data() {
        assert_eq!(meta("fs.read").and_then(|m| m.parent), Some("fs"));
        assert_eq!(
            meta("process.spawn").and_then(|m| m.parent),
            Some("process")
        );
        assert_eq!(meta("process.env").map(|m| m.name), Some("env.read"));
        assert_eq!(meta("net.connect").and_then(|m| m.arg_kind), Some("host"));
        assert!(is_grouping("net") && !is_grouping("net.connect"));
        for m in atoms_meta() {
            if let Some(p) = m.parent {
                assert!(declares(p), "{} names an undeclared parent {p}", m.name);
            }
        }
    }

    // frob:tests crates/gob-ir/src/core_pack.rs::receiver_families
    #[test]
    fn method_gates_and_non_process_crates_are_pack_data() {
        assert!(non_process_crates().contains(&"clap"));
        let sockets = receiver_families("python").find(|f| f.module == "socket");
        let sockets = sockets.expect("a socket family");
        assert!(sockets.ctors.contains(&"socket.socket"));
        assert!(sockets.methods.contains(&("net.listen", "bind")));
        assert!(receiver_families("python").any(|f| f.module == "tarfile"));
        assert_eq!(receiver_families("rust").count(), 0);
    }

    fn atoms_meta() -> &'static [AtomMeta] {
        &loaded().meta
    }
}
