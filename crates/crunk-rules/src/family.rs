//! Family metadata (crunk.md sections 4.1 and 6): what the rules of one prefix share.
//!
//! A rule's own declaration (`#[rule]`) carries id, slug, severity, scope and fix; what is common to
//! a whole family (its check tiers, whether a `crunk:waive` may silence it, the severity it takes
//! at the release gate) is stated once here, so a new rule of a known family declares nothing
//! extra and an unknown family is caught by [`crate::registry::unknown_families`].
//!
//! # Release severity
//!
//! `release_severity` (D117, crunk.md 4.1) can be declared per rule on `#[rule]` or once on the
//! family row; the rule's own value wins, the family's is the fallback. HUMAN001 and HUMAN002
//! (Advisory in `crunk check`, Error at release) use the family row. [`gate_severity`] and
//! [`apply_gate`] are the places that read it.

// frob:ticket 01M43ATASM383KB9130JY79XVV

use gob_rules::{Finding, RuleDef, Severity};

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

/// Where a finding is being judged: the everyday check or the release gate.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Hash)]
pub enum Gate {
    /// `crunk check`, `frob check`, local runs and CI.
    #[default]
    Check,
    /// `crunk check --gate release` and `frob release`.
    Release,
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
    /// Severity the family's rules take at the release gate, when it differs from their default.
    pub release_severity: Option<Severity>,
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
        release_severity: None,
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
    // crunk.md 4.1 and D117: Advisory in check and CI, Error at the release gate.
    FamilyMeta {
        prefix: "HUMAN",
        summary: "human review lock: a subject changed since its recorded ack",
        tiers: &[T0],
        waivable: false,
        release_severity: Some(Severity::Error),
    },
];

/// The row of `prefix`, if crunk knows the family.
pub fn family(prefix: &str) -> Option<&'static FamilyMeta> {
    FAMILIES.iter().find(|f| f.prefix == prefix)
}

/// The severity `def` takes at `gate`: its declared default at [`Gate::Check`]; at
/// [`Gate::Release`] the rule's own `release_severity`, else the family's, when either is set.
pub fn gate_severity(def: &RuleDef, gate: Gate) -> Severity {
    let severity = match gate {
        Gate::Check => def.severity,
        Gate::Release => def
            .release_severity
            .or_else(|| family(def.family).and_then(|f| f.release_severity))
            .unwrap_or(def.severity),
    };
    tracing::trace!(rule = def.id, ?gate, ?severity, "gate severity resolved");
    severity
}

// frob:ticket 01M4CXSM408E7A05DWKENDB7V4
/// Give every resolved finding of a rule (or family) with a `release_severity` that severity at the
/// release gate, the rule's own value first; at [`Gate::Check`] nothing changes.
pub fn apply_gate(findings: &mut [Finding], gate: Gate) {
    if gate != Gate::Release {
        return;
    }
    for f in findings
        .iter_mut()
        .filter(|f| f.severity != Severity::Unresolved)
    {
        let prefix = f
            .rule
            .as_str()
            .trim_end_matches(|c: char| c.is_ascii_digit());
        let own = crate::rules::INDEX
            .metas
            .iter()
            .find(|d| d.id == f.rule.as_str())
            .and_then(|d| d.release_severity);
        if let Some(sev) = own.or_else(|| family(prefix).and_then(|row| row.release_severity))
            && sev != f.severity
        {
            tracing::debug!(rule = %f.rule, from = ?f.severity, to = ?sev, "release gate raises severity");
            f.severity = sev;
        }
    }
}

/// True when a `crunk:waive` for `rule_id` may silence anything (its family is waivable).
pub fn is_waivable(rule_id: &str) -> bool {
    let prefix = rule_id.trim_end_matches(|c: char| c.is_ascii_digit());
    family(prefix).is_some_and(|f| f.waivable)
}
