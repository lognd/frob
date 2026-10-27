//! The open atom registry and callee vocabularies (D63, grimble-model.md 9.6).
//!
//! Entries are `inventory` submissions, so a grimble pack extends the registries by
//! linking a crate that calls `inventory::submit!`.

// frob:ticket 01M4FGXTB8T0F8AHNN604XCAZV

use std::collections::BTreeSet;
use std::sync::RwLock;

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
    v.extend(runtime().atoms.iter().map(|(_, a)| *a));
    v.sort_by_key(|a| a.name);
    v
}

/// The atom named `name`, or the one that lists `name` as an alias.
pub fn atom(name: &str) -> Option<&'static AtomEntry> {
    let hit = |a: &&'static AtomEntry| a.name == name || a.aliases.contains(&name);
    inventory::iter::<AtomEntry>
        .into_iter()
        .find(hit)
        .or_else(|| runtime().atoms.iter().map(|(_, a)| *a).find(hit))
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
    for v in &runtime().vocabs {
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

/// Every vocabulary class registered for any language (static and runtime entries).
pub fn vocab_classes() -> BTreeSet<&'static str> {
    let mut out: BTreeSet<&'static str> = inventory::iter::<VocabEntry>
        .into_iter()
        .map(|v| v.kind)
        .collect();
    out.extend(runtime().vocabs.iter().map(|v| v.kind));
    out
}

/// A matrix-build excuse template contributed by a pack (packs.md 6.7).
#[derive(Debug)]
pub struct TemplateEntry {
    /// The pack that ships the template.
    pub pack: &'static str,
    /// Template name, unique within its pack.
    pub name: &'static str,
    /// The atom the template excuses.
    pub atom: &'static str,
    /// Selector text over units (grmb-spec 6.1).
    pub selector: &'static str,
    /// Why the atom is set aside for the selected units.
    pub reason: &'static str,
}

/// Why a pack's content could not be interned.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum RegisterError {
    /// Another owner already answers for this atom name or alias.
    #[error("atom `{atom}` is declared by both `{first}` and `{second}`")]
    DuplicateAtom {
        /// The contested atom name or alias.
        atom: String,
        /// The owner that registered it first (`<inventory>` for a linked-in atom).
        first: String,
        /// The owner whose registration was refused.
        second: String,
    },
}

#[derive(Default)]
struct Runtime {
    atoms: Vec<(&'static str, &'static AtomEntry)>,
    vocabs: Vec<&'static VocabEntry>,
    templates: Vec<&'static TemplateEntry>,
}

static RUNTIME: RwLock<Runtime> = RwLock::new(Runtime {
    atoms: Vec::new(),
    vocabs: Vec::new(),
    templates: Vec::new(),
});

fn runtime() -> std::sync::RwLockReadGuard<'static, Runtime> {
    RUNTIME
        .read()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
}

/// The pack that registered `name` at run time, or `<inventory>` for a linked-in atom.
fn owner_of(name: &str) -> Option<String> {
    if inventory::iter::<AtomEntry>
        .into_iter()
        .any(|a| a.name == name || a.aliases.contains(&name))
    {
        return Some("<inventory>".to_owned());
    }
    runtime()
        .atoms
        .iter()
        .find(|(_, a)| a.name == name || a.aliases.contains(&name))
        .map(|(o, _)| (*o).to_owned())
}

/// Interns one pack's atoms, vocabularies and templates into the open registry.
///
/// All-or-nothing: if any atom name or alias is already answered for, nothing is added.
///
/// # Errors
/// [`RegisterError::DuplicateAtom`] naming both owners.
pub fn register_pack(
    owner: &str,
    atoms: Vec<AtomEntry>,
    vocabs: Vec<VocabEntry>,
    templates: Vec<TemplateEntry>,
) -> Result<(), RegisterError> {
    let mut rt = RUNTIME
        .write()
        .unwrap_or_else(std::sync::PoisonError::into_inner);
    let mut mine: BTreeSet<&str> = BTreeSet::new();
    for a in &atoms {
        for n in std::iter::once(&a.name).chain(a.aliases.iter()) {
            let first = if mine.contains(n) {
                Some(owner.to_owned())
            } else {
                rt.atoms
                    .iter()
                    .find(|(_, e)| e.name == *n || e.aliases.contains(n))
                    .map(|(o, _)| (*o).to_owned())
                    .or_else(|| {
                        inventory::iter::<AtomEntry>
                            .into_iter()
                            .any(|e| e.name == *n || e.aliases.contains(n))
                            .then(|| "<inventory>".to_owned())
                    })
            };
            if let Some(first) = first {
                tracing::warn!(atom = *n, %first, second = owner, "duplicate atom refused");
                return Err(RegisterError::DuplicateAtom {
                    atom: (*n).to_owned(),
                    first,
                    second: owner.to_owned(),
                });
            }
            mine.insert(n);
        }
    }
    let owner: &'static str = Box::leak(owner.to_owned().into_boxed_str());
    tracing::debug!(
        owner,
        atoms = atoms.len(),
        vocabs = vocabs.len(),
        templates = templates.len(),
        "pack interned into registry"
    );
    rt.atoms
        .extend(atoms.into_iter().map(|a| (owner, &*Box::leak(Box::new(a)))));
    rt.vocabs
        .extend(vocabs.into_iter().map(|v| &*Box::leak(Box::new(v))));
    rt.templates
        .extend(templates.into_iter().map(|t| &*Box::leak(Box::new(t))));
    Ok(())
}

/// Every pack-contributed excuse template, in registration order.
pub fn templates() -> Vec<&'static TemplateEntry> {
    runtime().templates.clone()
}

/// The registered owner of `name`: the pack that interned it or `<inventory>`; `None` if unknown.
pub fn atom_owner(name: &str) -> Option<String> {
    owner_of(name)
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
        kind: "net.connect",
        names: &["TcpStream::connect", "UdpSocket::connect"],
    }
}

inventory::submit! {
    VocabEntry { lang: "python", kind: "net.connect", names: &["socket.create_connection", ".connect", "requests.get", "requests.post", "requests.put", "requests.delete", "requests.request", "urllib.request.urlopen"] }
}
