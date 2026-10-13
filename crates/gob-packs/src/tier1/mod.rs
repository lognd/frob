//! Tier-1 pack content: `atoms.toml` and `templates.toml` interned into the open registry
//! (plugins.md sections 3 and 7, packs.md sections 2 and 6.7).
//!
//! A pack's atoms, vocabularies, detector rows and matrix-build excuse templates are parsed
//! into a [`Content`] and then interned with [`intern`], after which `gob_ir::registry`
//! answers for them exactly as for an `inventory`-registered atom. Two packs declaring one
//! atom is PACK004 naming both packs; a malformed file is PACK005.

// frob:ticket 01M3ZX7JRYNHG0BHJ3ZHC9450N

mod model;
mod parse;

use gob_ir::registry::{self, AtomEntry, DetectorEntry, RegisterError, TemplateEntry, VocabEntry};

use crate::error::{PackCode, PackError};
pub use model::{AtomDecl, Content, DetectorDecl, TemplateDecl, VocabDecl};

/// Why tier-1 content was refused.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum Tier1Error {
    /// PACK005: a content file is malformed (file, key and line named).
    #[error(transparent)]
    Malformed(#[from] PackError),
    /// PACK004: two packs declare one atom name or alias.
    #[error("PACK004 atom `{atom}` is declared by both `{first}` and `{second}`")]
    DuplicateAtom {
        /// The contested atom name or alias.
        atom: String,
        /// The pack seen first (`<inventory>` for a linked-in atom).
        first: String,
        /// The pack seen second.
        second: String,
    },
}

impl Tier1Error {
    /// The stable rule id of this error.
    pub fn code(&self) -> PackCode {
        match self {
            Self::Malformed(e) => e.code(),
            Self::DuplicateAtom { .. } => PackCode::Pack004,
        }
    }
}

impl From<RegisterError> for Tier1Error {
    fn from(e: RegisterError) -> Self {
        match e {
            RegisterError::DuplicateAtom {
                atom,
                first,
                second,
            } => Self::DuplicateAtom {
                atom,
                first,
                second,
            },
        }
    }
}

/// Parses a pack's `atoms.toml` and optional `templates.toml` text into [`Content`].
///
/// `atoms_file` and `templates_file` label errors.
///
/// # Errors
/// PACK005 [`Tier1Error::Malformed`] for unknown keys, bad names, a detector or template on
/// an atom the pack does not own, or a missing mandatory reason.
pub fn parse(
    pack: &str,
    atoms_file: &str,
    atoms_text: &str,
    templates: Option<(&str, &str)>,
) -> Result<Content, Tier1Error> {
    parse::content(pack, atoms_file, atoms_text, templates).map_err(Tier1Error::from)
}

fn leak_str(s: &str) -> &'static str {
    Box::leak(s.to_owned().into_boxed_str())
}

fn leak_strs(v: &[String]) -> &'static [&'static str] {
    Box::leak(
        v.iter()
            .map(|s| leak_str(s))
            .collect::<Vec<_>>()
            .into_boxed_slice(),
    )
}

/// Interns `content` for its pack into the registry, all-or-nothing.
///
/// # Errors
/// PACK004 [`Tier1Error::DuplicateAtom`] naming both packs when an atom or alias is taken.
pub fn intern(content: &Content) -> Result<(), Tier1Error> {
    let atoms = content
        .atoms
        .iter()
        .map(|a| {
            let detectors: Vec<DetectorEntry> = content
                .detectors
                .iter()
                .filter(|d| d.atom == a.name)
                .map(|d| DetectorEntry {
                    lang: leak_str(&d.lang),
                    kind: d.kind,
                })
                .collect();
            AtomEntry {
                name: leak_str(&a.name),
                aliases: leak_strs(&a.aliases),
                detectors: Box::leak(detectors.into_boxed_slice()),
            }
        })
        .collect();
    let vocabs = content
        .vocabs
        .iter()
        .map(|v| VocabEntry {
            lang: leak_str(&v.lang),
            kind: leak_str(&v.class),
            names: leak_strs(&v.names),
        })
        .collect();
    let templates = content
        .templates
        .iter()
        .map(|t| TemplateEntry {
            pack: leak_str(&content.pack),
            name: leak_str(&t.name),
            atom: leak_str(&t.atom),
            selector: leak_str(&t.selector),
            reason: leak_str(&t.reason),
        })
        .collect();
    registry::register_pack(&content.pack, atoms, vocabs, templates)?;
    tracing::info!(pack = %content.pack, atoms = content.atoms.len(), "tier-1 content interned");
    Ok(())
}

/// Interns several packs in order; stops at the first PACK004, leaving earlier packs interned.
///
/// # Errors
/// PACK004 naming both packs for the first duplicate atom.
pub fn intern_all(contents: &[Content]) -> Result<(), Tier1Error> {
    contents.iter().try_for_each(intern)
}
