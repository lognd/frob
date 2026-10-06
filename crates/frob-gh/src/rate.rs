//! The `x-ratelimit-*` response headers as a typed value.

use std::collections::BTreeMap;

/// Rate-limit state from one response; `None` from [`RateLimit::parse`] means the headers were absent.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct RateLimit {
    /// `x-ratelimit-limit`: the window's allowance.
    pub limit: Option<u64>,
    /// `x-ratelimit-remaining`: requests left in the window.
    pub remaining: u64,
    /// `x-ratelimit-used`: requests spent in the window, when reported.
    pub used: Option<u64>,
    /// `x-ratelimit-reset`: window reset, UTC epoch seconds.
    pub reset: Option<u64>,
    /// `x-ratelimit-resource`: `core`, `graphql`, `search`, ...
    pub resource: Option<String>,
}

impl RateLimit {
    /// Parse lower-cased headers; `None` when `x-ratelimit-remaining` is missing or malformed.
    pub fn parse(headers: &BTreeMap<String, String>) -> Option<Self> {
        let num = |name: &str| headers.get(name).and_then(|v| v.trim().parse::<u64>().ok());
        let remaining = num("x-ratelimit-remaining")?;
        Some(Self {
            limit: num("x-ratelimit-limit"),
            remaining,
            used: num("x-ratelimit-used"),
            reset: num("x-ratelimit-reset"),
            resource: headers.get("x-ratelimit-resource").cloned(),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn absent_headers_are_an_explicit_none() {
        assert_eq!(RateLimit::parse(&BTreeMap::new()), None);
    }

    #[test]
    fn parses_the_full_set() {
        let h: BTreeMap<String, String> = [
            ("x-ratelimit-limit", "5000"),
            ("x-ratelimit-remaining", "4990"),
            ("x-ratelimit-used", "10"),
            ("x-ratelimit-reset", "1700000000"),
            ("x-ratelimit-resource", "core"),
        ]
        .into_iter()
        .map(|(k, v)| (k.to_string(), v.to_string()))
        .collect();
        let r = RateLimit::parse(&h).unwrap();
        assert_eq!(
            (r.remaining, r.used, r.reset),
            (4990, Some(10), Some(1_700_000_000))
        );
        assert_eq!(r.resource.as_deref(), Some("core"));
    }
}
