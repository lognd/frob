//! The `crunk-web` std pack: A11Y, SEO, LAUNCH and WEBPERF rules in GRL, registered under the
//! crunk namespace and switched by `[packs] crunk_web` (opt-in; default on is an owner decision,
//! design gaps). The sources live under `packs/crunk-web`, embedded so the pack ships in the
//! binary; every rule must compile with a firing and a clean example (GRL011).

// frob:ticket 01M43AVHX91K72WYKYFX5W2SPP

use std::path::Path;

use gob_packs::lock::{LockedPack, snapshot};
use gob_packs::{Digest, Manifest, PackError, tree_digest};
use gob_plan::check::{Severity, compile_diagnostics};
use gob_plan::lower::lower_source;
use gob_plan::plan::Plan;

/// The pack name.
pub const NAME: &str = "crunk-web";
/// The label used for the embedded manifest in error messages.
pub const FILE: &str = "<builtin>/crunk-web/pack.toml";

const MANIFEST_TEXT: &str = include_str!("../../../packs/crunk-web/pack.toml");

/// Embedded GRL sources by pack-relative path, one rule per file.
pub const RULES: [(&str, &str); 11] = [
    (
        "rules/A11Y101.grl",
        include_str!("../../../packs/crunk-web/rules/A11Y101.grl"),
    ),
    (
        "rules/a11y/A11Y102.grl",
        include_str!("../../../packs/crunk-web/rules/a11y/A11Y102.grl"),
    ),
    (
        "rules/a11y/A11Y103.grl",
        include_str!("../../../packs/crunk-web/rules/a11y/A11Y103.grl"),
    ),
    (
        "rules/LAUNCH101.grl",
        include_str!("../../../packs/crunk-web/rules/LAUNCH101.grl"),
    ),
    (
        "rules/launch/LAUNCH102.grl",
        include_str!("../../../packs/crunk-web/rules/launch/LAUNCH102.grl"),
    ),
    (
        "rules/launch/LAUNCH103.grl",
        include_str!("../../../packs/crunk-web/rules/launch/LAUNCH103.grl"),
    ),
    (
        "rules/launch/LAUNCH104.grl",
        include_str!("../../../packs/crunk-web/rules/launch/LAUNCH104.grl"),
    ),
    (
        "rules/SEO101.grl",
        include_str!("../../../packs/crunk-web/rules/SEO101.grl"),
    ),
    (
        "rules/seo/SEO102.grl",
        include_str!("../../../packs/crunk-web/rules/seo/SEO102.grl"),
    ),
    (
        "rules/seo/SEO103.grl",
        include_str!("../../../packs/crunk-web/rules/seo/SEO103.grl"),
    ),
    (
        "rules/WEBPERF101.grl",
        include_str!("../../../packs/crunk-web/rules/WEBPERF101.grl"),
    ),
];

/// The `[packs]` table of `crunk.toml`: which std packs are on.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct PacksSwitch {
    /// `crunk_web`: run the crunk-web pack (opt-in, off by default).
    pub crunk_web: bool,
}

/// One `crunk rule catalog` row of the pack: a family and its rule.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CatalogRow {
    /// The pack name.
    pub pack: String,
    /// The family prefix (`A11Y`).
    pub family: String,
    /// The rule id (`A11Y101`).
    pub rule: String,
}

/// Why the pack does not build.
#[derive(Debug, thiserror::Error)]
pub enum PackBuildError {
    /// The manifest is malformed (PACK005).
    #[error("{0}")]
    Manifest(#[from] PackError),
    /// A rule file fails the GRL checker; the text is the rendered diagnostic.
    #[error("{file}: {report}")]
    Rule {
        /// The pack-relative rule path.
        file: String,
        /// The first error message.
        report: String,
    },
    /// A rule file does not lower to a plan.
    #[error("{file}: {reason}")]
    Lower {
        /// The pack-relative rule path.
        file: String,
        /// Why lowering failed.
        reason: String,
    },
    /// The on-disk tree differs from the embedded sources.
    #[error("pack tree differs from the embedded copy at {0}")]
    Drift(String),
}

/// Parses the embedded manifest.
///
/// # Errors
/// PACK005 if the embedded manifest is malformed (a build defect).
pub fn manifest() -> Result<Manifest, PackError> {
    Manifest::parse(FILE, MANIFEST_TEXT)
}

/// Compiles one GRL source: checker errors (a missing example is GRL011) or lowering failure.
///
/// # Errors
/// [`PackBuildError::Rule`] on the first checker error, [`PackBuildError::Lower`] otherwise.
pub fn compile_rule(file: &str, text: &str) -> Result<Vec<Plan>, PackBuildError> {
    if let Some(d) = compile_diagnostics(file, text)
        .into_iter()
        .find(|d| d.severity == Severity::Error)
    {
        tracing::warn!(file, message = %d.message, "crunk-web rule does not compile");
        return Err(PackBuildError::Rule {
            file: file.to_owned(),
            report: d.message,
        });
    }
    lower_source(file, text).map_err(|e| PackBuildError::Lower {
        file: file.to_owned(),
        reason: e.to_string(),
    })
}

/// Compiles every embedded rule, in source order.
///
/// # Errors
/// The first [`PackBuildError`] of any rule.
pub fn plans() -> Result<Vec<Plan>, PackBuildError> {
    let mut out = Vec::new();
    for (file, text) in RULES {
        out.extend(compile_rule(file, text)?);
    }
    tracing::debug!(rules = out.len(), "crunk-web pack compiled");
    Ok(out)
}

/// The family of a rule id: the id without its trailing digits.
fn family_of(rule: &str) -> &str {
    rule.trim_end_matches(|c: char| c.is_ascii_digit())
}

/// The pack's `crunk rule catalog` rows (empty when the switch is off), one per rule.
///
/// # Errors
/// [`PackBuildError`] if the pack does not compile.
pub fn catalog(switch: PacksSwitch) -> Result<Vec<CatalogRow>, PackBuildError> {
    if !switch.crunk_web {
        tracing::debug!("crunk-web pack is off: no catalog rows");
        return Ok(Vec::new());
    }
    Ok(plans()?
        .iter()
        .map(|p| CatalogRow {
            pack: NAME.to_owned(),
            family: family_of(p.rule()).to_owned(),
            rule: p.rule().to_owned(),
        })
        .collect())
}

/// Confirms the tree at `root` holds exactly the embedded sources and returns its digest.
///
/// `read` fetches a pack-relative file as bytes (the caller owns disk access; rule code does
/// not read the disk).
///
/// # Errors
/// [`PackBuildError::Drift`] if a file differs or is missing, PACK005 if the tree is unreadable.
pub fn verify_tree(
    root: &Path,
    read: impl Fn(&Path) -> Option<Vec<u8>>,
) -> Result<Digest, PackBuildError> {
    let embedded = [("pack.toml", MANIFEST_TEXT)].into_iter().chain(RULES);
    for (rel, text) in embedded {
        if read(&root.join(rel)).as_deref() != Some(text.as_bytes()) {
            tracing::warn!(
                file = rel,
                "crunk-web pack tree differs from the embedded copy"
            );
            return Err(PackBuildError::Drift(rel.to_owned()));
        }
    }
    Ok(tree_digest(root, &[])?)
}

/// The lock entry for the pack tree at `root`: the tree digest covers every file under it.
///
/// # Errors
/// As [`verify_tree`], or PACK005 if the embedded manifest is malformed.
pub fn locked(
    root: &Path,
    read: impl Fn(&Path) -> Option<Vec<u8>>,
) -> Result<LockedPack, PackBuildError> {
    let digest = verify_tree(root, read)?;
    Ok(snapshot(&manifest()?, None, &digest))
}
