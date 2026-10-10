//! The open atom registry and callee vocabularies (D63, grimble-model.md 9.6).
//!
//! Entries are `inventory` submissions, so a grimble pack extends the registries by
//! linking a crate that calls `inventory::submit!`.

// frob:ticket 01M4FGXTB8T0F8AHNN604XCAZV

use std::collections::BTreeSet;

use crate::answer::Answer;

/// How a detector recognizes an atom in a language.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum DetectorKind {
    /// By callee name against a vocabulary.
    Callee,
    /// By imported module.
    Import,
    /// By attribute or decorator.
    Attribute,
    /// By macro or phase kind.
    Macro,
    /// By structural pattern.
    Pattern,
    /// By lexical scan of text.
    Lexical,
    /// The capability is impossible in this language (a `not-applicable` matrix cell).
    NotApplicable,
}

/// A detector declared for one language.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DetectorEntry {
    /// Language tag.
    pub lang: &'static str,
    /// Detector kind.
    pub kind: DetectorKind,
}

/// An atom (an effect or capability name such as `net.connect`) and its detectors.
#[derive(Debug)]
pub struct AtomEntry {
    /// Dotted atom name.
    pub name: &'static str,
    /// Extra spellings of the same atom (`exec` for `process.spawn`).
    pub aliases: &'static [&'static str],
    /// Detectors per language; a parent atom such as `fs` has none of its own.
    pub detectors: &'static [DetectorEntry],
}

/// Names of one class in one language (for example Rust network callees).
#[derive(Debug)]
pub struct VocabEntry {
    /// Language tag.
    pub lang: &'static str,
    /// Vocabulary class (`net`, `fs`, `proc`).
    pub kind: &'static str,
    /// The callee names.
    pub names: &'static [&'static str],
}

inventory::collect!(AtomEntry);
inventory::collect!(VocabEntry);

/// All registered atoms, sorted by name.
pub fn atoms() -> Vec<&'static AtomEntry> {
    let mut v: Vec<_> = inventory::iter::<AtomEntry>.into_iter().collect();
    v.sort_by_key(|a| a.name);
    v
}

/// The atom named `name`, or the one that lists `name` as an alias.
pub fn atom(name: &str) -> Option<&'static AtomEntry> {
    inventory::iter::<AtomEntry>
        .into_iter()
        .find(|a| a.name == name || a.aliases.contains(&name))
}

/// The canonical atom name for `name` (an alias resolves to its atom); `None` when unregistered.
pub fn canonical(name: &str) -> Option<&'static str> {
    atom(name).map(|a| a.name)
}

/// Detector kinds for `atom` in `lang`: `Exact` when declared, `NotApplicable` when the only
/// declaration is [`DetectorKind::NotApplicable`], `Unknown` when nothing is declared.
pub fn detectors(atom_name: &str, lang: &str) -> Answer<BTreeSet<DetectorKind>> {
    let Some(a) = atom(atom_name) else {
        return Answer::Unknown;
    };
    let kinds: BTreeSet<DetectorKind> = a
        .detectors
        .iter()
        .filter(|d| d.lang == lang)
        .map(|d| d.kind)
        .collect();
    if kinds.is_empty() {
        Answer::Unknown
    } else if kinds == BTreeSet::from([DetectorKind::NotApplicable]) {
        Answer::NotApplicable
    } else {
        Answer::Exact(kinds)
    }
}

/// `callee_vocab(lang, class)` (Q47): the union of registered names; with no entry the answer
/// is `NotApplicable`, never an empty set.
pub fn callee_vocab(lang: &str, class: &str) -> Answer<BTreeSet<&'static str>> {
    let mut found = false;
    let mut names = BTreeSet::new();
    for v in inventory::iter::<VocabEntry> {
        if v.lang == lang && v.kind == class {
            found = true;
            names.extend(v.names.iter().copied());
        }
    }
    if found {
        Answer::Exact(names)
    } else {
        Answer::NotApplicable
    }
}

inventory::submit! {
    AtomEntry {
        name: "net.connect",
        aliases: &[],
        detectors: &[
            DetectorEntry { lang: "rust", kind: DetectorKind::Callee },
            DetectorEntry { lang: "python", kind: DetectorKind::Callee },
            DetectorEntry { lang: "css", kind: DetectorKind::NotApplicable },
        ],
    }
}

inventory::submit! {
    AtomEntry {
        name: "fs.write",
        aliases: &[],
        detectors: &[
            DetectorEntry { lang: "rust", kind: DetectorKind::Callee },
            DetectorEntry { lang: "python", kind: DetectorKind::Callee },
        ],
    }
}

inventory::submit! {
    VocabEntry {
        lang: "rust",
        kind: "net",
        names: &["TcpStream::connect", "UdpSocket::bind", "TcpListener::bind"],
    }
}

inventory::submit! {
    VocabEntry { lang: "python", kind: "net", names: &["socket.socket", "requests.get", "urllib.request.urlopen"] }
}
