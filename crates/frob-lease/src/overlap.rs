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

use std::collections::{BTreeSet, HashMap};
use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, OnceLock};

use frob_ledger::TicketId;
use frob_release::{Kind, parse_name};
use globset::{Glob, GlobBuilder, GlobMatcher, GlobSet, GlobSetBuilder};
use gob_walk::WalkConfig;

use crate::error::LeaseError;

/// Characters that start a wildcard in a glob.
const WILD: [char; 4] = ['*', '?', '[', '{'];

/// The directory holding changelog fragments, with a trailing slash.
const FRAGMENT_DIR: &str = "changelog.d/";

/// A valid ULID no real ticket owns, used to probe whether a glob would cover other tickets' fragments.
const PROBE_ULID: &str = "01ARZ3NDEKTSV4RRFFQ69G5FAV";

/// True when `path` is `changelog.d/<ticket ULID>.<type>.md` for exactly this `ticket`.
///
/// Reuses the release fragment name parser; a malformed name or another ticket's ULID is not "own".
pub fn is_own_fragment(path: &str, ticket: TicketId) -> bool {
    let Some(name) = path.strip_prefix(FRAGMENT_DIR) else {
        return false;
    };
    parse_name(name).is_ok_and(|(ulid, _)| ulid == ticket.to_string().to_ascii_uppercase())
}

/// True when a directory-qualified `changelog.d/` glob would match other tickets' fragments.
///
/// Such a glob (`changelog.d/**`, `changelog.d/*`) blocks every other ticket from its own
/// fragment, so leases ignore it and a new request for it is refused. A glob naming one exact
/// fragment, or one with no `changelog.d/` literal prefix (`**`), is not covered by this rule.
pub fn covers_foreign_fragments(glob: &str) -> bool {
    let g = normalize(glob);
    if !has_wildcard(&g) || !literal_prefix(&g).starts_with(FRAGMENT_DIR) {
        return false;
    }
    let Ok(m) = matcher(&g) else {
        return false;
    };
    Kind::ALL
        .iter()
        .any(|k| m.is_match(format!("{FRAGMENT_DIR}{PROBE_ULID}.{}.md", k.as_str())))
}

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
/// - Both have wildcards: a segment-wise intersection over the `/`-separated
///   segments. Literal segments must be equal, `*`/`?` segments match one segment
///   (two of them are compatible when their literal prefixes and suffixes agree),
///   `**` matches zero or more, and a glob that runs out of segments first must have
///   only `**` left on the other side. Disjoint is answered
///   only when proven; a glob with a character class, brace alternative or escape is
///   undecidable here and always overlaps.
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
            builder(&a)?;
            builder(&b)?;
            let overlap = wild_segments_overlap(&a, &b);
            tracing::debug!(%a, %b, overlap, "wildcard glob pair tested");
            Ok(overlap)
        }
    }
}

/// Segment-wise intersection test for two wildcard globs; `false` only when provably disjoint.
///
/// Globs with `[`, `{` or `\` are undecidable (alternatives and classes can contain `/`, which
/// would misalign the segments), so they answer `true`.
fn wild_segments_overlap(a: &str, b: &str) -> bool {
    if a.contains(['[', '{', '\\']) || b.contains(['[', '{', '\\']) {
        return true;
    }
    let (sa, sb): (Vec<&str>, Vec<&str>) = (a.split('/').collect(), b.split('/').collect());
    let mut memo = vec![vec![None; sb.len() + 1]; sa.len() + 1];
    segs_overlap(&sa, &sb, 0, 0, &mut memo)
}

/// True for a segment that can span several path segments (`**`, or any run of stars the
/// matcher might treat that way; over-approximated to stay sound).
fn is_globstar(seg: &str) -> bool {
    seg.contains("**")
}

/// Memoized recursion over segment positions `(li, ri)` of the two globs.
fn segs_overlap(
    left: &[&str],
    right: &[&str],
    li: usize,
    ri: usize,
    memo: &mut [Vec<Option<bool>>],
) -> bool {
    if let Some(r) = memo[li][ri] {
        return r;
    }
    let r = if li == left.len() {
        right[ri..].iter().all(|s| is_globstar(s))
    } else if ri == right.len() {
        left[li..].iter().all(|s| is_globstar(s))
    } else if is_globstar(left[li]) || is_globstar(right[ri]) {
        // The star side spans zero segments or absorbs one more of the other side.
        segs_overlap(left, right, li + 1, ri, memo) || segs_overlap(left, right, li, ri + 1, memo)
    } else {
        segment_compatible(left[li], right[ri]) && segs_overlap(left, right, li + 1, ri + 1, memo)
    };
    memo[li][ri] = Some(r);
    r
}

/// True when two single-segment patterns (no `**`, class, brace or escape) can match a common string.
fn segment_compatible(a: &str, b: &str) -> bool {
    let simple = |s: &str| !s.contains(['*', '?']);
    match (simple(a), simple(b)) {
        (true, true) => a == b,
        (true, false) => segment_matches(b, a),
        (false, true) => segment_matches(a, b),
        (false, false) => wild_pair_compatible(a, b),
    }
}

/// Necessary condition for two `*`/`?` segments to share a string: literal prefixes and suffixes agree.
///
/// Only `false` is a proof of disjointness; `ab*` and `ac*` cannot match one string, `a*` and `*b` can.
fn wild_pair_compatible(a: &str, b: &str) -> bool {
    let affixes = |s: &str| {
        let head = s.find(['*', '?']).map_or(s, |i| &s[..i]);
        let tail = s.rfind(['*', '?']).map_or(s, |i| &s[i + 1..]);
        (head.to_owned(), tail.to_owned())
    };
    let ((ha, ta), (hb, tb)) = (affixes(a), affixes(b));
    (ha.starts_with(&hb) || hb.starts_with(&ha)) && (ta.ends_with(&tb) || tb.ends_with(&ta))
}

fn segment_matches(pattern: &str, literal: &str) -> bool {
    // A pattern that fails to compile is undecidable: treat it as compatible.
    GlobBuilder::new(pattern)
        .literal_separator(true)
        .build()
        .map_or(true, |g| g.compile_matcher().is_match(literal))
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
    /// Files matched per scope (before the shared exemption), so a scope is matched once.
    matched: Mutex<HashMap<Vec<String>, Arc<BTreeSet<String>>>>,
    /// How many scopes were actually matched against the file list (cache misses).
    match_runs: AtomicUsize,
}

impl Resolver {
    /// A resolver over the work tree at `root`.
    pub fn new(root: PathBuf) -> Self {
        Self {
            root,
            files: OnceLock::new(),
            matched: Mutex::new(HashMap::new()),
            match_runs: AtomicUsize::new(0),
        }
    }

    /// How many scopes were matched against the file list so far; repeats are served from the cache.
    pub fn match_runs(&self) -> usize {
        self.match_runs.load(Ordering::Relaxed)
    }

    fn all_files(&self) -> Result<&[String], LeaseError> {
        let walked = self.files.get_or_init(|| {
            let cfg = WalkConfig {
                size_cap: u64::MAX,
                ..WalkConfig::default()
            };
            gob_walk::walk(&self.root, &cfg)
                .map(|r| {
                    let mut paths: Vec<String> = r.files.into_iter().map(|f| f.path).collect();
                    paths.sort_unstable();
                    paths
                })
                .map_err(|e| e.to_string())
        });
        walked
            .as_ref()
            .map(Vec::as_slice)
            .map_err(|e| LeaseError::Walk(e.clone()))
    }

    /// Files matching any of `scope`, shared exemption not applied, computed once per distinct scope.
    ///
    /// # Errors
    ///
    /// [`LeaseError::BadGlob`] or [`LeaseError::Walk`].
    pub fn matching(&self, scope: &[String]) -> Result<Arc<BTreeSet<String>>, LeaseError> {
        if scope.is_empty() {
            return Ok(Arc::default());
        }
        let cached = self
            .matched
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .get(scope)
            .cloned();
        if let Some(hit) = cached {
            return Ok(hit);
        }
        let all = self.all_files()?;
        let mut files = BTreeSet::new();
        for g in scope {
            // `all` is sorted, so the files under the glob's literal prefix are one contiguous run.
            let g = normalize(g);
            let prefix = literal_prefix(&g);
            let start = all.partition_point(|f| f.as_str() < prefix);
            let run = all[start..].iter().take_while(|f| f.starts_with(prefix));
            let m = matcher(&g)?;
            files.extend(run.filter(|f| m.is_match(f.as_str())).cloned());
        }
        self.match_runs.fetch_add(1, Ordering::Relaxed);
        tracing::debug!(
            globs = scope.len(),
            files = files.len(),
            "scope matched against the work tree"
        );
        let files = Arc::new(files);
        self.matched
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .insert(scope.to_vec(), files.clone());
        Ok(files)
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
        Ok(self
            .matching(scope)?
            .iter()
            .filter(|f| !shared.is_match(f.as_str()))
            .cloned()
            .collect())
    }
}

/// Scope entries that survive the shared-file and fragment exemptions of `ticket`.
///
/// A glob covering other tickets' fragments (legacy `changelog.d/**`) and a literal naming
/// the ticket's own fragment never contend: every ticket owns its fragment without a lease.
fn effective(scope: &[String], shared: &GlobSet, ticket: TicketId) -> Vec<String> {
    scope
        .iter()
        .map(|g| normalize(g))
        .filter(|g| !shared.is_match(g.as_str()))
        .filter(|g| {
            let skip = covers_foreign_fragments(g) || is_own_fragment(g, ticket);
            if skip {
                tracing::debug!(glob = %g, %ticket, "fragment glob ignored by overlap");
            }
            !skip
        })
        .collect()
}

/// Describe how scopes `a` and `b` overlap, or `None` when they are disjoint.
///
/// Shared files and each side's own changelog fragment are exempt (`a_ticket` owns `a`,
/// `b_ticket` owns `b`); the text test runs first and the repository walk only when it
/// finds nothing.
///
/// # Errors
///
/// [`LeaseError::BadGlob`] or [`LeaseError::Walk`].
pub fn scopes_overlap(
    (a, a_ticket): (&[String], TicketId),
    (b, b_ticket): (&[String], TicketId),
    shared: &GlobSet,
    resolver: &Resolver,
) -> Result<Option<String>, LeaseError> {
    let (ea, eb) = (
        effective(a, shared, a_ticket),
        effective(b, shared, b_ticket),
    );
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
    let (ra, rb) = (resolver.matching(&ea)?, resolver.matching(&eb)?);
    let common: Vec<&String> = ra
        .intersection(&rb)
        .filter(|f| {
            !shared.is_match(f.as_str())
                && !is_own_fragment(f, a_ticket)
                && !is_own_fragment(f, b_ticket)
        })
        .take(3)
        .collect();
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

    // frob:ticket 01M41FDWMMZTSHZETC48C6Y5DZ
    #[test]
    fn per_crate_wildcards_are_disjoint_when_segments_differ() {
        let no = [
            ("crates/*/Cargo.toml", "crates/frob-evidence/tests/**"),
            ("crates/*/Cargo.toml", "crates/*/src/**"),
            ("crates/*/src/**", "docs/**/*.md"),
            ("src/*.rs", "src/*/mod.rs"),
            ("src/*", "src/a/b/*"),
        ];
        for (a, b) in no {
            assert!(!globs_overlap(a, b).unwrap(), "{a} vs {b}");
            assert!(!globs_overlap(b, a).unwrap(), "{b} vs {a}");
        }
        let yes = [
            ("crates/*/src/**", "crates/frob-*/src/lib.rs"),
            ("crates/*/Cargo.toml", "crates/*/*.toml"),
            ("**/Cargo.toml", "crates/*/Cargo.toml"),
            ("crates/{a/b,c}/x/y", "crates/c/x/*"),
        ];
        for (a, b) in yes {
            assert!(globs_overlap(a, b).unwrap(), "{a} vs {b}");
            assert!(globs_overlap(b, a).unwrap(), "{b} vs {a}");
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
