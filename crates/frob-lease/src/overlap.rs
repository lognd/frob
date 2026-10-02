//! Scope overlap: glob-text analysis OR resolved-file-set intersection.
//!
//! Two scopes overlap when any pair of their globs overlaps as text
//! ([`globs_overlap`]) or when they resolve to a common file in the repository
//! ([`Resolver`]). The text test is what catches two tickets scoped to
//! `src/newmod/**` before any file exists; the resolved test catches globs that
//! look disjoint but share a file (`src/*.rs` and `src/lib.*`). Both err on the
//! side of reporting an overlap: a spurious refusal costs a narrower scope, a
//! missed overlap costs a merge conflict. Files matching the configured shared
//! patterns never count.

use std::collections::BTreeSet;
use std::path::PathBuf;
use std::sync::OnceLock;

use globset::{Glob, GlobBuilder, GlobMatcher, GlobSet, GlobSetBuilder};
use gob_walk::WalkConfig;

use crate::error::LeaseError;

/// Characters that start a wildcard in a glob.
const WILD: [char; 4] = ['*', '?', '[', '{'];

/// Canonical spelling of a scope entry: no `./`, and `dir/` meaning `dir/**`.
pub fn normalize(glob: &str) -> String {
    let g = glob.trim().trim_start_matches("./");
    if g.ends_with('/') {
        format!("{g}**")
    } else {
        g.to_owned()
    }
}

/// True when the glob contains a wildcard (or an escape, treated as one to stay conservative).
pub fn has_wildcard(glob: &str) -> bool {
    glob.contains(WILD) || glob.contains('\\')
}

/// The text before the first wildcard.
pub fn literal_prefix(glob: &str) -> &str {
    glob.find(|c| WILD.contains(&c) || c == '\\')
        .map_or(glob, |i| &glob[..i])
}

/// Compile one glob so that `*` and `?` stop at `/` and `**` crosses it.
///
/// # Errors
///
/// [`LeaseError::BadGlob`] when the pattern does not parse.
pub fn matcher(glob: &str) -> Result<GlobMatcher, LeaseError> {
    let g = normalize(glob);
    builder(&g).map(|g| g.compile_matcher())
}

fn builder(g: &str) -> Result<Glob, LeaseError> {
    GlobBuilder::new(g)
        .literal_separator(true)
        .build()
        .map_err(|e| LeaseError::BadGlob {
            glob: g.to_owned(),
            message: e.to_string(),
        })
}

/// Compile many globs into one set.
///
/// # Errors
///
/// [`LeaseError::BadGlob`] for the first pattern that does not parse.
pub fn glob_set<'a>(globs: impl IntoIterator<Item = &'a String>) -> Result<GlobSet, LeaseError> {
    let mut b = GlobSetBuilder::new();
    for g in globs {
        b.add(builder(&normalize(g))?);
    }
    b.build().map_err(|e| LeaseError::BadGlob {
        glob: "<set>".to_owned(),
        message: e.to_string(),
    })
}

/// The conservative text test for two scope globs.
///
/// - Neither has a wildcard: they overlap when equal or when one names a
///   directory containing the other (`src` and `src/a.rs`).
/// - One has a wildcard: it overlaps the literal when it matches it, or when
///   the literal names a directory above the wildcard's literal prefix.
/// - Both have wildcards: they overlap when either literal prefix is a prefix
///   of the other (an empty prefix, as in `**/*.rs`, overlaps everything).
///
/// # Errors
///
/// [`LeaseError::BadGlob`] when a wildcard pattern does not parse.
pub fn globs_overlap(a: &str, b: &str) -> Result<bool, LeaseError> {
    let (a, b) = (normalize(a), normalize(b));
    if a == b {
        return Ok(true);
    }
    match (has_wildcard(&a), has_wildcard(&b)) {
        (false, false) => Ok(dir_contains(&a, &b) || dir_contains(&b, &a)),
        (false, true) => literal_vs_wild(&a, &b),
        (true, false) => literal_vs_wild(&b, &a),
        (true, true) => {
            let (pa, pb) = (literal_prefix(&a), literal_prefix(&b));
            builder(&a)?;
            builder(&b)?;
            Ok(pa.starts_with(pb) || pb.starts_with(pa))
        }
    }
}

fn dir_contains(dir: &str, path: &str) -> bool {
    path.strip_prefix(dir)
        .is_some_and(|rest| rest.starts_with('/'))
}

fn literal_vs_wild(literal: &str, wild: &str) -> Result<bool, LeaseError> {
    let m = matcher(wild)?;
    Ok(m.is_match(literal) || literal_prefix(wild).starts_with(&format!("{literal}/")))
}

/// Resolves scope globs to repository files, walking the tree at most once.
#[derive(Debug)]
pub struct Resolver {
    root: PathBuf,
    files: OnceLock<Result<Vec<String>, String>>,
}

impl Resolver {
    /// A resolver over the work tree at `root`.
    pub fn new(root: PathBuf) -> Self {
        Self {
            root,
            files: OnceLock::new(),
        }
    }

    fn all_files(&self) -> Result<&[String], LeaseError> {
        let walked = self.files.get_or_init(|| {
            let cfg = WalkConfig {
                size_cap: u64::MAX,
                ..WalkConfig::default()
            };
            gob_walk::walk(&self.root, &cfg)
                .map(|r| r.files.into_iter().map(|f| f.path).collect())
                .map_err(|e| e.to_string())
        });
        walked
            .as_ref()
            .map(Vec::as_slice)
            .map_err(|e| LeaseError::Walk(e.clone()))
    }

    /// Files matching any of `scope`, minus those matching `shared`.
    ///
    /// # Errors
    ///
    /// [`LeaseError::BadGlob`] or [`LeaseError::Walk`].
    pub fn resolve(
        &self,
        scope: &[String],
        shared: &GlobSet,
    ) -> Result<BTreeSet<String>, LeaseError> {
        if scope.is_empty() {
            return Ok(BTreeSet::new());
        }
        let set = glob_set(scope)?;
        Ok(self
            .all_files()?
            .iter()
            .filter(|f| set.is_match(f.as_str()) && !shared.is_match(f.as_str()))
            .cloned()
            .collect())
    }
}

/// Scope entries that survive the shared-file exemption.
fn effective(scope: &[String], shared: &GlobSet) -> Vec<String> {
    scope
        .iter()
        .map(|g| normalize(g))
        .filter(|g| !shared.is_match(g.as_str()))
        .collect()
}

/// Describe how scopes `a` and `b` overlap, or `None` when they are disjoint.
///
/// Shared files are exempt on both sides; the text test runs first and the
/// repository walk only when it finds nothing.
///
/// # Errors
///
/// [`LeaseError::BadGlob`] or [`LeaseError::Walk`].
pub fn scopes_overlap(
    a: &[String],
    b: &[String],
    shared: &GlobSet,
    resolver: &Resolver,
) -> Result<Option<String>, LeaseError> {
    let (ea, eb) = (effective(a, shared), effective(b, shared));
    for ga in &ea {
        for gb in &eb {
            if globs_overlap(ga, gb)? {
                return Ok(Some(if ga == gb {
                    ga.clone()
                } else {
                    format!("{ga} and {gb}")
                }));
            }
        }
    }
    let (ra, rb) = (
        resolver.resolve(&ea, shared)?,
        resolver.resolve(&eb, shared)?,
    );
    let common: Vec<&String> = ra.intersection(&rb).take(3).collect();
    Ok((!common.is_empty()).then(|| {
        common
            .iter()
            .map(|s| s.as_str())
            .collect::<Vec<_>>()
            .join(", ")
    }))
}

/// Unit tests of the text analysis.
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn text_overlap_cases() {
        let yes = [
            ("src/newmod/**", "src/newmod/**"),
            ("src/newmod/**", "src/newmod/lib.rs"),
            ("src", "src/a.rs"),
            ("src/a*", "src/ab*"),
            ("**/*.rs", "src/x/**"),
            ("crates/a/", "crates/a/src/**"),
        ];
        for (a, b) in yes {
            assert!(globs_overlap(a, b).unwrap(), "{a} vs {b}");
            assert!(globs_overlap(b, a).unwrap(), "{b} vs {a}");
        }
        let no = [
            ("src/a/**", "src/b/**"),
            ("src/a.rs", "src/b.rs"),
            ("src/ab*", "src/ac*"),
            ("src/a.rs", "lib/**"),
            ("srcx", "src/a.rs"),
        ];
        for (a, b) in no {
            assert!(!globs_overlap(a, b).unwrap(), "{a} vs {b}");
            assert!(!globs_overlap(b, a).unwrap(), "{b} vs {a}");
        }
    }

    #[test]
    fn bad_glob_is_reported() {
        assert!(matches!(
            globs_overlap("src/[", "src/**"),
            Err(LeaseError::BadGlob { .. })
        ));
    }
}
