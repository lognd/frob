//! [`Fidelity`], [`Capability`] and [`Precision`]: the vocabulary of one matrix cell.

use std::fmt;

/// Fidelity of an adapter (universal-model.md 3.3), checked by its corpus.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Default)]
#[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
pub enum Fidelity {
    /// Opaque only: locations and whole-artifact digests.
    #[default]
    F0,
    /// Units, roles and containment.
    F1,
    /// F1 plus binders, references and a lexical scope graph with Must edges.
    F2,
    /// F2 plus `apply` edges resolved to the adapter's declared status.
    F3,
    /// F3 plus attributes, comments bound to targets, regions and phases.
    F4,
}

impl fmt::Display for Fidelity {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Self::F0 => "F0",
            Self::F1 => "F1",
            Self::F2 => "F2",
            Self::F3 => "F3",
            Self::F4 => "F4",
        })
    }
}

/// A capability an adapter may declare (universal-model.md 4.4, plus the D107 additions).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Capability {
    /// Resolving a reference to its declarations.
    ResolveRef,
    /// The targets of an application (call graph).
    ApplyTargets,
    /// Whether a unit is visible outside its container.
    Visibility,
    /// Effects of a region.
    Effects,
    /// Which units are tests.
    TestItems,
    /// The imports of an artifact.
    Imports,
    /// Expansion of a phase (macro).
    Expand,
    /// Evaluation order of a group.
    Order,
    /// Packages, their dependencies, path aliases and entry files (language-engines.md section 2).
    ProjectModel,
    /// Comment nodes and directive binding (replaces `Need::EveryTextArtifact`).
    Comments,
    /// Style facts: rules, selectors, declarations and their values.
    Style,
    /// Markup structure: elements, attributes and headings.
    Markup,
}

impl Capability {
    /// Every capability in matrix column order.
    pub const ALL: [Self; 12] = [
        Self::ResolveRef,
        Self::ApplyTargets,
        Self::Visibility,
        Self::Effects,
        Self::TestItems,
        Self::Imports,
        Self::Expand,
        Self::Order,
        Self::ProjectModel,
        Self::Comments,
        Self::Style,
        Self::Markup,
    ];

    /// The capabilities of the generated languages page, in table order (the pre-D107 nine).
    pub const PAGE: [Self; 9] = [
        Self::ResolveRef,
        Self::ApplyTargets,
        Self::Visibility,
        Self::Effects,
        Self::TestItems,
        Self::Imports,
        Self::Expand,
        Self::Order,
        Self::ProjectModel,
    ];

    /// The spelling used in universal-model.md and `frob doctor --languages`.
    pub const fn name(self) -> &'static str {
        match self {
            Self::ResolveRef => "resolve_ref",
            Self::ApplyTargets => "apply_targets",
            Self::Visibility => "visibility",
            Self::Effects => "effects",
            Self::TestItems => "test_items",
            Self::Imports => "imports",
            Self::Expand => "expand",
            Self::Order => "order",
            Self::ProjectModel => "project_model",
            Self::Comments => "comments",
            Self::Style => "style",
            Self::Markup => "markup",
        }
    }
}

/// How precisely a capability is answered (one rung of its ladder).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Precision {
    /// Not provided: the answer is Unknown.
    None,
    /// The language has no such concept: the answer is `NotApplicable`.
    NotApplicable,
    /// Lexical scoping only.
    Lexical,
    /// Lexical scoping plus `use` imports resolved inside the crate.
    LexicalImports,
    /// Resolution by name inside the crate; ambiguous names give May sets.
    ByNameInCrate,
    /// Resolution of link targets against the project's anchors.
    LinkTargets,
    /// Read from a keyword or modifier.
    Keyword,
    /// Read from the syntax alone.
    Syntactic,
    /// Declared by the source, not inferred.
    Declared,
    /// Read from the build manifests (`Cargo.toml`, `.csproj`, `package.json`, `tsconfig.json`).
    Manifest,
}

impl Precision {
    /// The label printed by `frob doctor --languages`.
    pub const fn label(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::NotApplicable => "not-applicable",
            Self::Lexical => "lexical",
            Self::LexicalImports => "lexical+imports",
            Self::ByNameInCrate => "by-name-in-crate (May)",
            Self::LinkTargets => "link-targets",
            Self::Keyword => "keyword",
            Self::Syntactic => "syntactic",
            Self::Declared => "declared",
            Self::Manifest => "manifest",
        }
    }

    /// The capability-matrix cell word: `Implemented`, `NotApplicable` or `Gap` (code-model.md section 3).
    pub const fn cell(self) -> &'static str {
        match self {
            Self::None => "Gap",
            Self::NotApplicable => "NotApplicable",
            _ => "Implemented",
        }
    }

    /// True when the cell is provided: neither a gap nor declared not-applicable.
    pub const fn is_provided(self) -> bool {
        !matches!(self, Self::None | Self::NotApplicable)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    // frob:tests crates/gob-caps/src/capability.rs::Precision.cell
    fn cell_words_follow_the_ladder() {
        assert_eq!(Precision::None.cell(), "Gap");
        assert_eq!(Precision::NotApplicable.cell(), "NotApplicable");
        assert_eq!(Precision::Manifest.cell(), "Implemented");
        assert!(!Precision::None.is_provided());
        assert!(Precision::Syntactic.is_provided());
    }

    #[test]
    fn the_page_capabilities_are_the_first_nine() {
        assert_eq!(Capability::PAGE[..], Capability::ALL[..9]);
    }
}
