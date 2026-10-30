//! Family metadata (crunk.md sections 4.1 and 6): what the rules of one prefix share.
//!
//! A rule's own declaration (`#[rule]`) carries id, slug, severity, scope and fix; what is common to
//! a whole family (its check tiers, whether a `crunk:waive` may silence it) is stated once here, so a new rule of a known family declares nothing
//! extra and an unknown family is caught by [`crate::registry::unknown_families`].
//!
//! # Gates
//!
//! Which gates a rule runs at (`local`, `ci`, `release`) is declared per rule with
//! `#[rule(gates = [...])]` and resolved by [`gob_rules::rule_in_gate`] (rules.md 6.1.5).
//! HUMAN001 and HUMAN002 are `gates = [release]`.

// frob:ticket 01M43ATASM383KB9130JY79XVV

/// The check tier that can decide a family (crunk.md section 4).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum CheckTier {
    /// Static: the files alone.
    T0,
    /// Layout solve.
    T1,
    /// Render.
    T2,
    /// Live browser or editor.
    T3,
}

impl CheckTier {
    /// `T0` to `T3`.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::T0 => "T0",
            Self::T1 => "T1",
            Self::T2 => "T2",
            Self::T3 => "T3",
        }
    }
}

/// The metadata one family of crunk rules shares.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct FamilyMeta {
    /// The id prefix, for example `COLOR`.
    pub prefix: &'static str,
    /// One line on what the family checks.
    pub summary: &'static str,
    /// Tiers that decide the family's rules.
    pub tiers: &'static [CheckTier],
    /// True when a `crunk:waive` may silence the family's findings (organisation and waiver
    /// findings describe the file, not a declaration, and are never waivable).
    pub waivable: bool,
}

const fn fam(
    prefix: &'static str,
    summary: &'static str,
    tiers: &'static [CheckTier],
    waivable: bool,
) -> FamilyMeta {
    FamilyMeta {
        prefix,
        summary,
        tiers,
        waivable,
    }
}

use CheckTier::{T0, T1, T2, T3};

/// Every family crunk owns or has designed (crunk.md section 6), in documentation order.
pub const FAMILIES: &[FamilyMeta] = &[
    fam(
        "TOKEN",
        "token schema, alias cycles, naming tiers, mode completeness, scope violations",
        &[T0],
        false,
    ),
    fam(
        "TOKENS",
        "generated token output drifting from its source",
        &[T0],
        false,
    ),
    fam(
        "COLOR",
        "colour literals that are not tokens or palette colours",
        &[T0, T2],
        true,
    ),
    fam(
        "CONTRAST",
        "contrast of declared colour pairs in every mode",
        &[T0, T2],
        true,
    ),
    fam(
        "TYPE",
        "type scale steps, families, weights and ramp",
        &[T0],
        true,
    ),
    fam("SPACE", "spacing scale steps", &[T0], true),
    fam("RADIUS", "corner radius scale steps", &[T0], true),
    fam("SIZE", "size scale steps", &[T0], true),
    fam("LAYER", "z-index layers", &[T0], true),
    fam(
        "SLOP",
        "unchosen defaults and generic copy, silenced by declared decisions",
        &[T0],
        true,
    ),
    fam(
        "ORG",
        "stylesheet organisation: buckets, class naming, custom property placement",
        &[T0],
        false,
    ),
    fam(
        "TW",
        "Tailwind utilities against the token scales",
        &[T0],
        true,
    ),
    fam("BP", "breakpoint coverage and usage", &[T0], true),
    fam(
        "LAYOUT",
        "overflow, overlap, clipping, safe area, target size",
        &[T1],
        true,
    ),
    fam(
        "RESP",
        "responsive breakpoint coverage per profile",
        &[T1],
        true,
    ),
    fam(
        "COMP",
        "component variants, props bound to tokens, code mapping",
        &[T0, T1],
        true,
    ),
    fam(
        "STATE",
        "required component states present",
        &[T0, T1],
        true,
    ),
    fam(
        "A11Y",
        "names, roles, landmarks, heading and focus order, keyboard map",
        &[T0, T1, T3],
        true,
    ),
    fam(
        "CRAFT",
        "presence rules paired with SLOP rules: a deleted policy is reported",
        &[T0],
        true,
    ),
    fam(
        "MOTION",
        "durations and easings from tokens, reduced-motion twin",
        &[T0, T2],
        true,
    ),
    fam(
        "CONTENT",
        "literal copy in scenes, length budgets",
        &[T0, T1],
        true,
    ),
    fam(
        "I18N",
        "pseudo-locale expansion, right-to-left mirroring",
        &[T0, T1],
        true,
    ),
    fam("VIS", "visual regression thresholds", &[T0, T2], true),
    fam("THEME", "theme completeness", &[T0, T2], true),
    fam(
        "EXPORT",
        "export parity across Tailwind, USS and C#",
        &[T0, T2],
        true,
    ),
    fam(
        "GX",
        "game UI: gamepad focus graph, glyphs, HUD safe area, text size",
        &[T0, T1],
        true,
    ),
    fam("UX", "design-cycle traceability and flows", &[T0], true),
    fam("PROC", "ready gate and design process", &[T0], true),
    fam(
        "SCENE",
        "scene dialect: properties the layout solver does not implement",
        &[T0],
        true,
    ),
    fam(
        "PORT",
        "Figma-only effects with no CSS or USS equivalent in imports",
        &[T0],
        true,
    ),
    fam(
        "GALLERY",
        "gallery manifest, approvals and renders",
        &[T0, T2],
        false,
    ),
    fam("WAIVE", "crunk:waive comments", &[T0], false),
    // crunk.md 4.1 and D117: the rules are release-only (`gates = [release]`).
    fam(
        "HUMAN",
        "human review lock: a subject changed since its recorded ack",
        &[T0],
        false,
    ),
];

/// The row of `prefix`, if crunk knows the family.
pub fn family(prefix: &str) -> Option<&'static FamilyMeta> {
    FAMILIES.iter().find(|f| f.prefix == prefix)
}

/// True when a `crunk:waive` for `rule_id` may silence anything (its family is waivable).
pub fn is_waivable(rule_id: &str) -> bool {
    let prefix = rule_id.trim_end_matches(|c: char| c.is_ascii_digit());
    family(prefix).is_some_and(|f| f.waivable)
}
