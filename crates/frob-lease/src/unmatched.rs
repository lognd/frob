//! Zero-match scope globs (~PVJ9SQM): a lease over nothing is warned about, never refused.
//!
//! A scope entry that matches no file tracked at `HEAD` grants a write lease over nothing and
//! reports zero overlaps, which reads as "cleanly disjoint". The denominator is the tracked
//! tree, not the disk: a repository with no tracked files (an empty fixture, a fresh `git init`)
//! is never judged. A ticket that really creates files declares the entry with the label
//! `creates:<glob>` (`--new-scope` on `ticket new`, `--add-new-scope` on `ticket update`,
//! `--new-glob` on `lease widen`), which silences the warning for exactly that entry and
//! survives in the ledger, so `work` stays quiet on later calls too. A near tracked path (same
//! file name elsewhere, or a one-typo neighbour in the same directory) is named as a
//! suggestion; with no near candidate the warning is plain.

use frob_ledger::TicketId;

use crate::error::LeaseError;
use crate::overlap::{covers_foreign_fragments, has_wildcard, is_own_fragment, matcher, normalize};

/// The label prefix declaring that a scope entry names files the ticket will create.
pub const CREATES_PREFIX: &str = "creates:";

/// How many same-name suggestions one warning lists at most.
const MAX_SUGGESTIONS: usize = 3;

/// The label that declares `glob` as a not-yet-existing scope entry.
pub fn creates_label(glob: &str) -> String {
    format!("{CREATES_PREFIX}{}", normalize(glob))
}

/// One scope entry that matches no tracked file, with the nearest tracked paths (possibly none).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScopeMiss {
    /// The entry as written in the ticket scope.
    pub glob: String,
    /// Near tracked paths, best first; empty when nothing is close enough to suggest.
    pub suggestions: Vec<String>,
}

impl ScopeMiss {
    /// The one-line warning text for this entry, naming the glob and the escape hatch.
    pub fn message(&self) -> String {
        let hint = match self.suggestions.as_slice() {
            [] => String::new(),
            near => format!(
                "; did you mean {}?",
                near.iter()
                    .map(|s| format!("`{s}`"))
                    .collect::<Vec<_>>()
                    .join(" or ")
            ),
        };
        format!(
            "scope glob `{}` matches no tracked file, so its lease covers nothing{hint} (if the ticket will create it, declare it with the label `{}`)",
            self.glob,
            creates_label(&self.glob)
        )
    }
}

/// The scope entries of `ticket` that match nothing in `tracked`.
///
/// Empty when `tracked` is empty (no real checkout to judge against), for entries declared
/// with a `creates:` label in `labels`, and for changelog-fragment entries (a ticket's own
/// fragment needs no lease and does not exist until written).
///
/// # Errors
///
/// [`LeaseError::BadGlob`] when an entry does not parse.
pub fn unmatched(
    scope: &[String],
    labels: &[String],
    ticket: TicketId,
    tracked: &[String],
) -> Result<Vec<ScopeMiss>, LeaseError> {
    if tracked.is_empty() {
        tracing::debug!(%ticket, "no tracked files; scope not judged");
        return Ok(Vec::new());
    }
    let mut out = Vec::new();
    for entry in scope {
        let g = normalize(entry);
        if labels.iter().any(|l| l == &creates_label(&g)) {
            tracing::debug!(%ticket, glob = %g, "scope entry declared as creating files");
            continue;
        }
        if covers_foreign_fragments(&g) || is_own_fragment(&g, ticket) {
            continue;
        }
        let m = matcher(&g)?;
        let literal_dir = format!("{g}/");
        let hit = tracked
            .iter()
            .any(|t| m.is_match(t) || (!has_wildcard(&g) && t.starts_with(&literal_dir)));
        if hit {
            continue;
        }
        let suggestions = suggest(&g, tracked);
        tracing::info!(%ticket, glob = %g, suggestions = ?suggestions, "scope entry matches no tracked file");
        out.push(ScopeMiss {
            glob: entry.clone(),
            suggestions,
        });
    }
    Ok(out)
}

/// The tracked paths nearest to a zero-match glob; empty rather than a guess.
///
/// Same file name elsewhere wins (the file moved); failing that, the single closest name in
/// the glob's own directory within about a quarter of its length in edits (a typo). Only a
/// wildcard-free final segment can be compared.
fn suggest(glob: &str, tracked: &[String]) -> Vec<String> {
    let (dir, base) = glob.rsplit_once('/').map_or(("", glob), |(d, b)| (d, b));
    if base.is_empty() || has_wildcard(base) {
        return Vec::new();
    }
    let name = |t: &str| t.rsplit('/').next().unwrap_or(t).to_owned();
    let mut same: Vec<&String> = tracked.iter().filter(|t| name(t) == base).collect();
    if !same.is_empty() {
        let shared = |t: &str| {
            t.chars()
                .zip(glob.chars())
                .take_while(|(a, b)| a == b)
                .count()
        };
        same.sort_by_key(|t| std::cmp::Reverse(shared(t)));
        return same.into_iter().take(MAX_SUGGESTIONS).cloned().collect();
    }
    if has_wildcard(dir) {
        return Vec::new();
    }
    let limit = (base.chars().count() / 4).max(1);
    let mut near: Vec<(usize, &String)> = tracked
        .iter()
        .filter(|t| t.rsplit_once('/').map_or("", |(d, _)| d) == dir)
        .map(|t| (strsim::levenshtein(&name(t), base), t))
        .filter(|(d, _)| *d <= limit)
        .collect();
    near.sort();
    match near.as_slice() {
        [(_, t0)] => vec![(*t0).clone()],
        [(d0, t0), (d1, _), ..] if d0 < d1 => vec![(*t0).clone()],
        _ => Vec::new(),
    }
}

/// Warning lines for a ticket's zero-match scope entries, judged against the tracked tree at `HEAD`.
///
/// Never fails: an unreadable tree or an unparseable glob is logged and yields no warnings, so
/// the verb that asked is never refused over a hint.
pub fn scope_warnings(
    repo: &gob_git::Repo,
    ticket: TicketId,
    scope: &[String],
    labels: &[String],
) -> Vec<String> {
    let tracked = match repo.tracked_files_at("HEAD") {
        Ok(t) => t,
        Err(e) => {
            tracing::debug!(%ticket, error = %e, "tracked files unavailable; scope not judged");
            return Vec::new();
        }
    };
    match unmatched(scope, labels, ticket, &tracked) {
        Ok(misses) => misses.iter().map(ScopeMiss::message).collect(),
        Err(e) => {
            tracing::warn!(%ticket, error = %e, "scope check skipped");
            Vec::new()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tid() -> TicketId {
        "01M1T07NWAFVRT2V4RAPVJ9SQM".parse().unwrap()
    }

    fn files() -> Vec<String> {
        [
            "crates/frob/src/lib.rs",
            "crates/frob/src/lease_cmd.rs",
            "tests/unit/pages/content-projects.test.ts",
        ]
        .map(String::from)
        .to_vec()
    }

    fn s(v: &[&str]) -> Vec<String> {
        v.iter().map(|x| (*x).to_owned()).collect()
    }

    // frob:ticket 01M1T07NWAFVRT2V4RAPVJ9SQM
    #[test]
    fn zero_match_glob_warns_naming_the_glob() {
        let m = unmatched(&s(&["crates/frob/src/scope_cmd.rs"]), &[], tid(), &files()).unwrap();
        assert_eq!(m.len(), 1);
        assert!(m[0].message().contains("`crates/frob/src/scope_cmd.rs`"));
        assert!(m[0].suggestions.is_empty(), "no near candidate, no guess");
    }

    #[test]
    fn matching_globs_stay_quiet() {
        let scope = s(&[
            "crates/frob/**",
            "crates/frob/src/lib.rs",
            "crates/frob/src/",
            "crates/frob",
        ]);
        assert!(unmatched(&scope, &[], tid(), &files()).unwrap().is_empty());
    }

    #[test]
    fn declared_new_file_stays_quiet() {
        let scope = s(&["crates/frob/src/scope_cmd.rs"]);
        let labels = vec![creates_label("crates/frob/src/scope_cmd.rs")];
        assert!(
            unmatched(&scope, &labels, tid(), &files())
                .unwrap()
                .is_empty()
        );
    }

    #[test]
    fn repo_without_tracked_files_is_not_judged() {
        let scope = s(&["anything/at/all.rs"]);
        assert!(unmatched(&scope, &[], tid(), &[]).unwrap().is_empty());
    }

    #[test]
    fn moved_file_is_suggested_by_name() {
        let scope = s(&["frontend/tests/unit/content-projects.test.ts"]);
        let m = unmatched(&scope, &[], tid(), &files()).unwrap();
        assert_eq!(
            m[0].suggestions,
            vec!["tests/unit/pages/content-projects.test.ts".to_owned()]
        );
        assert!(m[0].message().contains("did you mean"));
    }

    #[test]
    fn typo_in_same_directory_is_suggested() {
        let m = unmatched(&s(&["crates/frob/src/lease_cnd.rs"]), &[], tid(), &files()).unwrap();
        assert_eq!(
            m[0].suggestions,
            vec!["crates/frob/src/lease_cmd.rs".to_owned()]
        );
    }

    #[test]
    fn own_fragment_is_exempt() {
        let scope = s(&["changelog.d/01M1T07NWAFVRT2V4RAPVJ9SQM.fixed.md"]);
        assert!(unmatched(&scope, &[], tid(), &files()).unwrap().is_empty());
    }
}
