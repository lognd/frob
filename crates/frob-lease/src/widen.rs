//! Growing a lease scope to the files a ticket diff touches (frob:ticket 01M4KW3A47K7S9WGD3NBVVPJB4).
//!
//! The planner is pure: it takes the ticket's scope, the changed paths and the other live leases,
//! and answers which paths may be absorbed and which are held by someone else. Callers
//! (`lease widen --from-diff`, `check --ticket --widen`) apply the answer through the ledger and
//! the lease store.

use globset::GlobSet;

use frob_ledger::TicketId;

use crate::error::LeaseError;
use crate::model::Lease;
use crate::overlap::{ScopeMatcher, is_own_fragment};

/// What a diff-driven widen would do.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Absorb {
    /// Literal-path globs to add to the scope: out of scope and held by no other live lease.
    pub add: Vec<String>,
    /// Changed paths another live lease holds, with that lease's ticket; never absorbed.
    pub held: Vec<(String, TicketId)>,
}

/// Split a stored scope entry on top-level commas, so a comma-joined `a, b` entry counts as two globs.
///
/// Commas inside `{...}` or `[...]` belong to the glob and are kept.
pub fn split_entries(entry: &str) -> Vec<String> {
    let mut out = Vec::new();
    let (mut depth, mut cur) = (0_i32, String::new());
    for c in entry.chars() {
        match c {
            '{' | '[' => depth += 1,
            '}' | ']' => depth = (depth - 1).max(0),
            ',' if depth == 0 => {
                out.push(std::mem::take(&mut cur));
                continue;
            }
            _ => {}
        }
        cur.push(c);
    }
    out.push(cur);
    out.into_iter()
        .map(|s| s.trim().to_owned())
        .filter(|s| !s.is_empty())
        .collect()
}

/// The glob that matches exactly `path`: wildcard characters in the name are bracket-escaped.
pub fn literal_glob(path: &str) -> String {
    let mut out = String::with_capacity(path.len());
    for c in path.chars() {
        match c {
            '*' | '?' | '[' | '{' => {
                out.push('[');
                out.push(c);
                out.push(']');
            }
            _ => out.push(c),
        }
    }
    out
}

/// Compile every entry (comma-joined ones split) into matchers.
fn matchers(scope: &[String]) -> Result<Vec<ScopeMatcher>, LeaseError> {
    scope
        .iter()
        .flat_map(|e| split_entries(e))
        .map(|e| ScopeMatcher::new(&e))
        .collect()
}

/// Decide which of `changed` the lease of `ticket` (scope `scope`) may absorb.
///
/// A path already covered by `scope`, a shared file, or the ticket's own changelog fragment is
/// skipped; a path an entry of any lease in `others` covers is reported in [`Absorb::held`]
/// (the ticket's own lease in `others` is ignored); the rest become literal globs in
/// [`Absorb::add`], sorted and deduplicated.
///
/// # Errors
///
/// [`LeaseError::BadGlob`] when a scope entry does not parse.
pub fn plan_absorb(
    ticket: TicketId,
    scope: &[String],
    changed: &[String],
    others: &[Lease],
    shared: &GlobSet,
) -> Result<Absorb, LeaseError> {
    let mine = matchers(scope)?;
    let mut theirs = Vec::new();
    for l in others.iter().filter(|l| l.ticket != ticket) {
        theirs.push((l.ticket, matchers(&l.scope)?));
    }
    let mut out = Absorb::default();
    for path in changed {
        if mine.iter().any(|m| m.is_match(path))
            || shared.is_match(path)
            || is_own_fragment(path, ticket)
        {
            tracing::trace!(%path, "widen: already covered");
            continue;
        }
        if let Some((other, _)) = theirs
            .iter()
            .find(|(_, ms)| ms.iter().any(|m| m.is_match(path)))
        {
            tracing::info!(%path, %other, "widen: held by another live lease, not absorbed");
            out.held.push((path.clone(), *other));
            continue;
        }
        let glob = literal_glob(path);
        if !out.add.contains(&glob) {
            out.add.push(glob);
        }
    }
    out.add.sort();
    tracing::info!(%ticket, add = out.add.len(), held = out.held.len(), "widen planned");
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Holder;
    use frob_ledger::model::Stamp;

    const A: &str = "01ARZ3NDEKTSV4RRFFQ69G5FAV";
    const B: &str = "01BX5ZZKBKACTAV9WEVGEMMVRY";

    fn lease(id: &str, scope: &[&str]) -> Lease {
        Lease {
            ticket: id.parse().expect("ulid"),
            holder: Holder {
                actor: "x".into(),
                worktree: "/w".into(),
            },
            scope: scope.iter().map(|s| (*s).to_owned()).collect(),
            acquired_at: Stamp::from_unix(0),
            renewed_at: Stamp::from_unix(0),
            ttl_secs: 100,
            history: Vec::new(),
            queued: false,
            agent: None,
            touched_at: None,
            touch_note: None,
            base: None,
        }
    }

    fn plan(scope: &[&str], changed: &[&str], others: &[Lease]) -> Absorb {
        let s: Vec<String> = scope.iter().map(|s| (*s).to_owned()).collect();
        let c: Vec<String> = changed.iter().map(|s| (*s).to_owned()).collect();
        plan_absorb(A.parse().expect("ulid"), &s, &c, others, &GlobSet::empty()).expect("plan")
    }

    #[test]
    fn absorbs_a_free_file_outside_scope() {
        let got = plan(&["src/a.rs"], &["src/a.rs", "src/b.rs"], &[]);
        assert_eq!(got.add, vec!["src/b.rs".to_owned()]);
        assert!(got.held.is_empty());
    }

    #[test]
    fn leaves_a_file_another_live_lease_holds() {
        let other = lease(B, &["src/b.rs"]);
        let got = plan(&["src/a.rs"], &["src/b.rs", "src/c.rs"], &[other]);
        assert_eq!(got.add, vec!["src/c.rs".to_owned()]);
        assert_eq!(got.held.len(), 1);
        assert_eq!(got.held[0].0, "src/b.rs");
    }

    #[test]
    fn a_comma_joined_scope_entry_still_covers_each_part() {
        let got = plan(
            &["src/a.rs, docs/**"],
            &["src/a.rs", "docs/x.md", "src/z.rs"],
            &[],
        );
        assert_eq!(got.add, vec!["src/z.rs".to_owned()]);
    }

    #[test]
    fn braces_keep_their_commas() {
        assert_eq!(split_entries("a/{x,y}.rs, b"), vec!["a/{x,y}.rs", "b"]);
    }

    #[test]
    fn replanning_after_the_add_is_a_no_op() {
        let first = plan(&["src/a.rs"], &["src/b.rs"], &[]);
        let mut scope = vec!["src/a.rs"];
        scope.extend(first.add.iter().map(String::as_str));
        let again = plan(&scope, &["src/b.rs"], &[]);
        assert_eq!(again, Absorb::default());
    }

    #[test]
    fn wildcard_names_are_escaped_to_match_exactly() {
        let got = plan(&[], &["app/[id]/page.tsx"], &[]);
        assert_eq!(got.add, vec!["app/[[]id]/page.tsx".to_owned()]);
        let again = plan(&["app/[[]id]/page.tsx"], &["app/[id]/page.tsx"], &[]);
        assert!(again.add.is_empty());
    }

    #[test]
    fn the_tickets_own_lease_among_the_others_is_ignored() {
        let own = lease(A, &["src/a.rs"]);
        let got = plan(&["src/a.rs"], &["src/b.rs"], &[own]);
        assert_eq!(got.add, vec!["src/b.rs".to_owned()]);
    }
}
