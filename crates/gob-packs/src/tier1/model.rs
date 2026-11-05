//! The parsed, validated tier-1 content of one pack.

use gob_ir::registry::DetectorKind;

/// One `[[atom]]`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AtomDecl {
    /// Dotted atom name.
    pub name: String,
    /// Extra spellings.
    pub aliases: Vec<String>,
    /// CWE identifiers the atom maps to.
    pub cwe: Vec<String>,
    /// Severity per rule id (`CAP001`): `error` or `warn`.
    pub severity: std::collections::BTreeMap<String, String>,
}

/// One `[[vocab]]`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VocabDecl {
    /// Language tag.
    pub lang: String,
    /// Vocabulary class.
    pub class: String,
    /// Callee names.
    pub names: Vec<String>,
}

/// One expanded detector row (one atom, one language).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DetectorDecl {
    /// The pack-owned atom.
    pub atom: String,
    /// Language tag.
    pub lang: String,
    /// The registry detector kind.
    pub kind: DetectorKind,
    /// Detector precision class, if stated.
    pub precision: Option<String>,
    /// CWE identifiers the row maps to.
    pub cwe: Vec<String>,
    /// Why the use is a risk, if stated.
    pub rationale: Option<String>,
    /// What to use instead, if stated.
    pub safer_alternative: Option<String>,
}

/// One `[[template]]` matrix-build excuse.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TemplateDecl {
    /// Template name.
    pub name: String,
    /// The excused pack-owned atom.
    pub atom: String,
    /// Selector text over units.
    pub selector: String,
    /// Mandatory reason.
    pub reason: String,
}

/// Everything a pack's tier-1 files declare.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Content {
    /// The owning pack's name.
    pub pack: String,
    /// Atoms.
    pub atoms: Vec<AtomDecl>,
    /// Vocabularies.
    pub vocabs: Vec<VocabDecl>,
    /// Expanded detector rows.
    pub detectors: Vec<DetectorDecl>,
    /// Excuse templates.
    pub templates: Vec<TemplateDecl>,
}
