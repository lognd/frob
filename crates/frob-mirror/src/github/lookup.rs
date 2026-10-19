//! GitHub issue lookup (mirror.md 3.3 "Lookup is read-your-writes"; F5).
//!
//! A ticket's issues are found by listing the bot's issues by creator, newest first, and paging
//! back until a create-start time is passed. The search endpoint is never used: it lags, so a
//! just-created issue can be missing from it. The `ListingSource` trait has no search method, so
//! no caller can reach search through this module.

// frob:ticket 01M4052QWSEERAG3JPCGXM4RK4

use tracing::{debug, trace, warn};

use crate::adapter::{AdapterResult, IssueSummary};

/// One page-at-a-time view of the bot's issue listing, newest first.
pub trait ListingSource {
    /// Fetch page `page` (1-based) of `creator_id`'s issues, newest first; empty past the end.
    ///
    /// # Errors
    /// Returns an `AdapterError` when the tracker call fails.
    fn page(&self, creator_id: u64, page: u32) -> AdapterResult<Vec<IssueSummary>>;
}

/// List `creator_id`'s issues newest first until one older than `since` (RFC 3339 UTC) is seen.
///
/// Paging stops at the first page containing an issue created before `since`, or at an empty
/// page. Issues created at or after `since` are returned in listing order; timestamps compare
/// as strings, which is exact for GitHub's fixed-width `Z` form.
///
/// # Errors
/// Returns the source's `AdapterError` when a page fetch fails.
pub fn lookup_since(
    source: &dyn ListingSource,
    creator_id: u64,
    since: &str,
) -> AdapterResult<Vec<IssueSummary>> {
    let mut found = Vec::new();
    let mut page = 1u32;
    loop {
        let items = source.page(creator_id, page)?;
        trace!(
            creator_id,
            page,
            count = items.len(),
            "lookup: fetched page"
        );
        if items.is_empty() {
            debug!(creator_id, page, "lookup: listing exhausted");
            return Ok(found);
        }
        let mut passed = false;
        for item in items {
            if item.created_at.as_str() < since {
                passed = true;
                break;
            }
            found.push(item);
        }
        if passed {
            debug!(creator_id, page, since, "lookup: passed create-start time");
            return Ok(found);
        }
        if page == u32::MAX {
            warn!(creator_id, "lookup: page counter exhausted");
            return Ok(found);
        }
        page += 1;
    }
}

#[cfg(test)]
mod tests {
    use std::cell::RefCell;

    use super::*;
    use crate::adapter::IssueRef;

    fn issue(n: u32, at: &str) -> IssueSummary {
        IssueSummary {
            issue: IssueRef(n.to_string()),
            title: format!("t{n}"),
            creator_id: 7,
            created_at: at.into(),
        }
    }

    /// Recorded listing pages plus a log of every request made.
    struct Recorded {
        pages: Vec<Vec<IssueSummary>>,
        log: RefCell<Vec<String>>,
    }

    impl ListingSource for Recorded {
        fn page(&self, creator_id: u64, page: u32) -> AdapterResult<Vec<IssueSummary>> {
            self.log
                .borrow_mut()
                .push(format!("GET /issues?creator={creator_id}&page={page}"));
            Ok(self
                .pages
                .get(page as usize - 1)
                .cloned()
                .unwrap_or_default())
        }
    }

    // frob:tests lookup_since
    #[test]
    fn found_through_listing_only_never_search() {
        let src = Recorded {
            pages: vec![vec![
                issue(3, "2026-10-03T00:00:02Z"),
                issue(2, "2026-10-03T00:00:01Z"),
                issue(1, "2026-10-01T00:00:00Z"),
            ]],
            log: RefCell::default(),
        };
        let got = lookup_since(&src, 7, "2026-10-03T00:00:00Z").unwrap();
        let ids: Vec<_> = got.iter().map(|i| i.issue.0.as_str()).collect();
        assert_eq!(ids, ["3", "2"]);
        let log = src.log.borrow();
        assert!(!log.is_empty());
        assert!(log.iter().all(|l| l.contains("/issues?creator=")));
        assert!(!log.iter().any(|l| l.contains("search")));
    }

    // frob:tests lookup_since
    #[test]
    fn paging_continues_until_the_start_time_is_passed() {
        let src = Recorded {
            pages: vec![
                vec![
                    issue(5, "2026-10-05T00:00:00Z"),
                    issue(4, "2026-10-04T00:00:00Z"),
                ],
                vec![
                    issue(3, "2026-10-03T00:00:00Z"),
                    issue(2, "2026-10-02T00:00:00Z"),
                ],
                vec![issue(1, "2026-10-01T00:00:00Z")],
                vec![issue(0, "2026-09-01T00:00:00Z")],
            ],
            log: RefCell::default(),
        };
        let got = lookup_since(&src, 7, "2026-10-02T12:00:00Z").unwrap();
        let ids: Vec<_> = got.iter().map(|i| i.issue.0.as_str()).collect();
        assert_eq!(ids, ["5", "4", "3"]);
        // Page 2 held an older issue, so page 3 is never fetched.
        assert_eq!(src.log.borrow().len(), 2);
    }

    // frob:tests lookup_since
    #[test]
    fn an_exhausted_listing_ends_paging() {
        let src = Recorded {
            pages: vec![vec![issue(1, "2026-10-05T00:00:00Z")]],
            log: RefCell::default(),
        };
        let got = lookup_since(&src, 7, "2026-01-01T00:00:00Z").unwrap();
        assert_eq!(got.len(), 1);
        assert_eq!(src.log.borrow().len(), 2);
    }

    /// Live check of the UNVERIFIED read-your-writes fact (mirror.md 3.3). The operator creates
    /// an issue with a live token, then immediately saves the creator listing
    /// (`GET /repos/OWNER/REPO/issues?creator=BOT&state=all&sort=created&direction=desc`) to
    /// the file named by `FROB_GH_PROBE_LISTING`, and names the new issue in `FROB_GH_PROBE_NUMBER`.
    // frob:tests lookup_since
    #[test]
    #[ignore = "needs a live GitHub token; run by hand, then record the result on the ticket"]
    fn live_created_issue_appears_in_listing_at_once() {
        let path = std::env::var("FROB_GH_PROBE_LISTING").expect("FROB_GH_PROBE_LISTING");
        let number: u64 = std::env::var("FROB_GH_PROBE_NUMBER")
            .expect("FROB_GH_PROBE_NUMBER")
            .parse()
            .expect("numeric issue number");
        let text = std::fs::read_to_string(path).expect("read listing");
        let list: serde_json::Value = serde_json::from_str(&text).expect("listing json");
        let seen = list
            .as_array()
            .expect("array")
            .iter()
            .any(|i| i["number"].as_u64() == Some(number));
        assert!(seen, "issue {number} missing from the creator listing");
    }
}
