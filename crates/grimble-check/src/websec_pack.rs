//! The `grimble-websec` pack: WEBSEC (registered inside SEC), SQL, COMPLY (with PII), ROUTE and
//! WEBPERF (server side) rules in GRL. The sources live under `packs/grimble-websec`, embedded so
//! the pack ships in the binary; every rule must compile with a firing and a clean example
//! (GRL011). The `db.query` and `net` capability atoms come from core-effects and are not
//! redefined here.

// frob:ticket 01M43AWPD2DYMS2CVTJRD56D5R

use std::path::Path;

use gob_packs::lock::{LockedPack, snapshot};
use gob_packs::{Digest, Manifest, PackError, tree_digest};
use gob_plan::check::{Severity, compile_diagnostics};
use gob_plan::lower::lower_source;
use gob_plan::plan::Plan;

/// The pack name.
pub const NAME: &str = "grimble-websec";
/// The label used for the embedded manifest in error messages.
pub const FILE: &str = "<builtin>/grimble-websec/pack.toml";

const MANIFEST_TEXT: &str = include_str!("../../../packs/grimble-websec/pack.toml");

/// Embedded GRL sources by pack-relative path, one rule per file.
pub const RULES: [(&str, &str); 5] = [
    (
        "rules/SEC101.grl",
        include_str!("../../../packs/grimble-websec/rules/SEC101.grl"),
    ),
    (
        "rules/SQL101.grl",
        include_str!("../../../packs/grimble-websec/rules/SQL101.grl"),
    ),
    (
        "rules/COMPLY101.grl",
        include_str!("../../../packs/grimble-websec/rules/COMPLY101.grl"),
    ),
    (
        "rules/ROUTE101.grl",
        include_str!("../../../packs/grimble-websec/rules/ROUTE101.grl"),
    ),
    (
        "rules/WEBPERF201.grl",
        include_str!("../../../packs/grimble-websec/rules/WEBPERF201.grl"),
    ),
];

/// One `grimble rule catalog` row of the pack: a family, its namespace and its rule.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CatalogRow {
    /// The pack name.
    pub pack: String,
    /// The family label (`WEBSEC`, `SQL`).
    pub family: String,
    /// The registry namespace the rule id lives in (`SEC` for WEBSEC).
    pub namespace: String,
    /// The rule id (`SEC101`).
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
        tracing::warn!(file, message = %d.message, "grimble-websec rule does not compile");
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
    tracing::debug!(rules = out.len(), "grimble-websec pack compiled");
    Ok(out)
}

/// The namespace of a rule id: the id without its trailing digits.
fn namespace_of(rule: &str) -> &str {
    rule.trim_end_matches(|c: char| c.is_ascii_digit())
}

/// The family label of a rule id; WEBSEC rules carry SEC ids, every other family is its namespace.
fn family_of(rule: &str) -> &str {
    match namespace_of(rule) {
        "SEC" => "WEBSEC",
        other => other,
    }
}

/// The pack's `grimble rule catalog` rows, one per rule.
///
/// # Errors
/// [`PackBuildError`] if the pack does not compile.
pub fn catalog() -> Result<Vec<CatalogRow>, PackBuildError> {
    Ok(plans()?
        .iter()
        .map(|p| CatalogRow {
            pack: NAME.to_owned(),
            family: family_of(p.rule()).to_owned(),
            namespace: namespace_of(p.rule()).to_owned(),
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
                "grimble-websec pack tree differs from the embedded copy"
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
