//! Change feed (mirror.md 3.2 F1): the bot's issues updated since the stored cursor.
//!
//! One GraphQL query per 100 issues lists the bot's issues updated since the cursor, ordered by
//! update time (oldest first). Only issues whose update time passed the stored observed value
//! get a history read ([`needs_history`]). A response whose `errors` array is non-empty, or
//! whose data is partial, fails the whole feed for the scope: no cursor is returned, so the
//! stored cursor does not advance.

// frob:ticket 01M4052RC6C32957W1A9PYQAEE

use serde_json::{Value, json};
use tracing::{debug, info, trace, warn};

use crate::adapter::{AdapterError, AdapterResult, IssueRef};
use crate::mapfile::Shard;

/// Issues per GraphQL page (the GitHub maximum).
pub const PAGE_SIZE: usize = 100;

/// Shard `observed` key holding the issue update time last seen by the feed.
pub const OBSERVED_UPDATED_AT: &str = "updated_at";

/// GraphQL query for one feed page; variables: owner, repo, creator login, since, after.
pub const FEED_QUERY: &str = "query($o:String!,$r:String!,$c:String!,$s:DateTime!,$a:String){\
    repository(owner:$o,name:$r){issues(first:100,after:$a,\
    filterBy:{createdBy:$c,since:$s},orderBy:{field:UPDATED_AT,direction:ASC}){\
    pageInfo{hasNextPage endCursor} nodes{number updatedAt}}}}";

/// One issue the feed saw.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FeedIssue {
    /// The tracker issue.
    pub issue: IssueRef,
    /// Update time, RFC 3339 UTC.
    pub updated_at: String,
}

/// One page of the feed.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FeedPage {
    /// Issues on this page, oldest update first.
    pub issues: Vec<FeedIssue>,
    /// Page cursor for the next page, when there is one.
    pub next: Option<String>,
}

/// The whole feed for one scope.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FeedRead {
    /// Every issue updated since the cursor, ordered by update time.
    pub issues: Vec<FeedIssue>,
    /// The new feed cursor (latest update time seen); `None` when the feed was empty.
    pub cursor: Option<String>,
}

/// Page-at-a-time source of the feed (live GraphQL or recorded fixtures).
pub trait FeedSource {
    /// Fetch one page of the bot's issues updated since `since`, after page cursor `after`.
    ///
    /// # Errors
    /// Returns an `AdapterError` when the query fails or its response carries errors.
    fn page(&self, since: &str, after: Option<&str>) -> AdapterResult<FeedPage>;
}

/// The GraphQL request body for one feed page.
pub fn feed_request(
    owner: &str,
    repo: &str,
    creator_login: &str,
    since: &str,
    after: Option<&str>,
) -> Value {
    json!({"query": FEED_QUERY, "variables": {
        "o": owner, "r": repo, "c": creator_login, "s": since, "a": after}})
}

/// Parse one GraphQL feed response; any `errors` entry or missing data fails the page.
///
/// # Errors
/// `RateLimited` when an error is of type `RATE_LIMITED`, else `Other` for any other `errors`
/// entry or for partial data.
pub fn parse_page(response: &Value) -> AdapterResult<FeedPage> {
    if let Some(errors) = response
        .get("errors")
        .and_then(Value::as_array)
        .filter(|e| !e.is_empty())
    {
        let limited = errors
            .iter()
            .any(|e| e.get("type").and_then(Value::as_str) == Some("RATE_LIMITED"));
        warn!(count = errors.len(), limited, "feed: errors array in page");
        return Err(if limited {
            AdapterError::RateLimited
        } else {
            AdapterError::Other(format!("graphql: {} error(s) in feed page", errors.len()))
        });
    }
    let partial = || AdapterError::Other("graphql: partial feed data".into());
    let issues = response
        .pointer("/data/repository/issues")
        .ok_or_else(partial)?;
    let nodes = issues
        .get("nodes")
        .and_then(Value::as_array)
        .ok_or_else(partial)?;
    let mut out = Vec::with_capacity(nodes.len());
    for n in nodes {
        let number = n
            .get("number")
            .and_then(Value::as_u64)
            .ok_or_else(partial)?;
        let updated_at = n
            .get("updatedAt")
            .and_then(Value::as_str)
            .ok_or_else(partial)?;
        out.push(FeedIssue {
            issue: IssueRef(number.to_string()),
            updated_at: updated_at.to_string(),
        });
    }
    let has_next = issues
        .pointer("/pageInfo/hasNextPage")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    let next = if has_next {
        issues
            .pointer("/pageInfo/endCursor")
            .and_then(Value::as_str)
            .map(str::to_owned)
    } else {
        None
    };
    trace!(count = out.len(), has_next, "feed: parsed page");
    Ok(FeedPage { issues: out, next })
}

/// Read the whole feed since `since`, one query per page, ordered by update time.
///
/// The cursor in the result is the latest update time seen; on any page error the feed stops
/// and the error is returned instead, so the caller's stored cursor stays where it was.
///
/// # Errors
/// Returns the source's `AdapterError` when a page fails (including a GraphQL `errors` array).
pub fn read_feed(source: &dyn FeedSource, since: &str) -> AdapterResult<FeedRead> {
    let mut issues: Vec<FeedIssue> = Vec::new();
    let mut after: Option<String> = None;
    let mut queries = 0u32;
    loop {
        let page = source.page(since, after.as_deref()).inspect_err(|e| {
            warn!(since, queries, error = %e, "feed: stopped, cursor not advanced");
        })?;
        queries += 1;
        debug!(queries, count = page.issues.len(), "feed: page read");
        issues.extend(page.issues);
        match page.next {
            Some(n) if after.as_deref() != Some(n.as_str()) => after = Some(n),
            _ => break,
        }
    }
    issues.sort_by(|a, b| a.updated_at.cmp(&b.updated_at));
    let cursor = issues.last().map(|i| i.updated_at.clone());
    info!(queries, issues = issues.len(), "feed: read complete");
    Ok(FeedRead { issues, cursor })
}

/// Whether `issue` needs a history read: its update time is past the shard's observed value.
///
/// Timestamps compare as strings, exact for GitHub's fixed-width `Z` form. An issue with no
/// stored observed value always needs a read.
pub fn needs_history(issue: &FeedIssue, shard: Option<&Shard>) -> bool {
    let seen = shard.and_then(|s| s.observed.get(OBSERVED_UPDATED_AT));
    let needed = seen.is_none_or(|o| issue.updated_at.as_str() > o.as_str());
    trace!(issue = %issue.issue.0, needed, "feed: history decision");
    needed
}

/// The feed issues that need a history read, in feed order; `shard_of` looks up the stored shard.
pub fn select_for_history<'a>(
    feed: &'a FeedRead,
    shard_of: &dyn Fn(&IssueRef) -> Option<Shard>,
) -> Vec<&'a FeedIssue> {
    feed.issues
        .iter()
        .filter(|i| needs_history(i, shard_of(&i.issue).as_ref()))
        .collect()
}

#[cfg(test)]
mod tests {
    use std::cell::RefCell;

    use super::*;

    fn raw(n: usize) -> Value {
        json!({"number": n, "updatedAt": format!("2026-10-{:02}T00:{:02}:00Z", 1 + n / 60, n % 60)})
    }

    /// Serves 250 issues in 100-sized pages from GraphQL-shaped responses, newest first within
    /// nothing in particular (reversed) to prove the feed sorts.
    struct Fixture {
        log: RefCell<Vec<Option<String>>>,
        fail_page: Option<usize>,
    }

    impl FeedSource for Fixture {
        fn page(&self, _since: &str, after: Option<&str>) -> AdapterResult<FeedPage> {
            self.log.borrow_mut().push(after.map(str::to_owned));
            let idx = self.log.borrow().len() - 1;
            if self.fail_page == Some(idx) {
                return parse_page(&json!({"errors": [{"type": "RATE_LIMITED"}], "data": null}));
            }
            let start = after.map_or(0, |a| a.parse::<usize>().unwrap());
            let end = (start + PAGE_SIZE).min(250);
            let nodes: Vec<Value> = (start..end).rev().map(raw).collect();
            parse_page(&json!({"data": {"repository": {"issues": {
                "pageInfo": {"hasNextPage": end < 250, "endCursor": end.to_string()},
                "nodes": nodes}}}}))
        }
    }

    // frob:tests read_feed
    #[test]
    fn two_hundred_fifty_issues_take_three_queries_ordered_by_update_time() {
        let src = Fixture {
            log: RefCell::default(),
            fail_page: None,
        };
        let feed = read_feed(&src, "2026-10-01T00:00:00Z").unwrap();
        assert_eq!(src.log.borrow().len(), 3);
        assert_eq!(feed.issues.len(), 250);
        assert!(
            feed.issues
                .windows(2)
                .all(|w| w[0].updated_at <= w[1].updated_at)
        );
        assert_eq!(
            feed.cursor.as_deref(),
            Some(feed.issues[249].updated_at.as_str())
        );
    }

    // frob:tests needs_history
    #[test]
    fn an_issue_not_past_its_observed_time_gets_no_history_read() {
        let mut shard = Shard::new("U");
        shard
            .observed
            .insert(OBSERVED_UPDATED_AT.into(), "2026-10-05T00:00:00Z".into());
        let at = |t: &str| FeedIssue {
            issue: IssueRef("1".into()),
            updated_at: t.into(),
        };
        assert!(!needs_history(&at("2026-10-05T00:00:00Z"), Some(&shard)));
        assert!(!needs_history(&at("2026-10-04T00:00:00Z"), Some(&shard)));
        assert!(needs_history(&at("2026-10-05T00:00:01Z"), Some(&shard)));
        assert!(needs_history(&at("2026-10-01T00:00:00Z"), None));
    }

    // frob:tests select_for_history
    #[test]
    fn selection_keeps_only_changed_issues() {
        let feed = FeedRead {
            issues: vec![
                FeedIssue {
                    issue: IssueRef("1".into()),
                    updated_at: "2026-10-02T00:00:00Z".into(),
                },
                FeedIssue {
                    issue: IssueRef("2".into()),
                    updated_at: "2026-10-03T00:00:00Z".into(),
                },
            ],
            cursor: None,
        };
        let lookup = |i: &IssueRef| {
            let mut s = Shard::new("U");
            let t = if i.0 == "1" {
                "2026-10-02T00:00:00Z"
            } else {
                "2026-10-01T00:00:00Z"
            };
            s.observed.insert(OBSERVED_UPDATED_AT.into(), t.into());
            Some(s)
        };
        let got = select_for_history(&feed, &lookup);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].issue.0, "2");
    }

    // frob:tests read_feed
    #[test]
    fn an_errors_array_stops_the_feed_and_yields_no_cursor() {
        let src = Fixture {
            log: RefCell::default(),
            fail_page: Some(1),
        };
        let err = read_feed(&src, "2026-10-01T00:00:00Z").unwrap_err();
        assert_eq!(err, AdapterError::RateLimited);
        assert_eq!(src.log.borrow().len(), 2);
    }

    // frob:tests parse_page
    #[test]
    fn partial_data_and_generic_errors_fail_the_page() {
        let e = parse_page(&json!({"errors": [{"message": "x"}], "data": {}})).unwrap_err();
        assert!(matches!(e, AdapterError::Other(_)));
        assert!(parse_page(&json!({"data": {"repository": null}})).is_err());
    }

    // frob:tests feed_request
    #[test]
    fn request_carries_variables() {
        let r = feed_request("o", "r", "bot", "2026-10-01T00:00:00Z", Some("c"));
        assert_eq!(r["variables"]["a"], "c");
        assert_eq!(r["variables"]["c"], "bot");
    }
}
