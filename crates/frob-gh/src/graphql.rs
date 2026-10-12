//! GraphQL response checking: the `errors` array is read on every response (mirror.md 3.2).

use crate::RateLimit;

/// Why a GraphQL response yielded no usable data; the whole query scope is failed.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum GraphqlFailure {
    /// Rate limiting reported inside a 200 response; no data is returned.
    #[error("graphql rate limited; window resets at {reset:?} (epoch seconds)")]
    RateLimited {
        /// Reset time from the response's rate-limit headers, when present.
        reset: Option<u64>,
    },
    /// Data arrived alongside a non-empty `errors` array: partial data is failure.
    #[error("partial data with errors: {}", messages.join("; "))]
    PartialData {
        /// The error messages.
        messages: Vec<String>,
    },
    /// Errors and no data.
    #[error("graphql errors: {}", messages.join("; "))]
    Errors {
        /// The error messages.
        messages: Vec<String>,
    },
    /// The body is not a GraphQL JSON envelope.
    #[error("malformed graphql body: {0}")]
    Malformed(String),
}

fn is_rate_limit(err: &serde_json::Value) -> bool {
    let kind = err.get("type").and_then(|v| v.as_str()).unwrap_or("");
    let msg = err.get("message").and_then(|v| v.as_str()).unwrap_or("");
    kind.eq_ignore_ascii_case("RATE_LIMITED") || msg.to_ascii_lowercase().contains("rate limit")
}

/// Parse a GraphQL body into its `data`, failing the whole scope on any `errors` entry.
///
/// # Errors
/// [`GraphqlFailure`]: rate limiting (carrying `rate.reset`), partial data, errors, or a bad body.
pub fn parse_response(
    body: &[u8],
    rate: Option<&RateLimit>,
) -> Result<serde_json::Value, GraphqlFailure> {
    let envelope: serde_json::Value =
        serde_json::from_slice(body).map_err(|e| GraphqlFailure::Malformed(e.to_string()))?;
    let errors = envelope
        .get("errors")
        .and_then(|e| e.as_array())
        .filter(|a| !a.is_empty());
    let data = envelope.get("data").filter(|d| !d.is_null());
    if let Some(errors) = errors {
        if errors.iter().any(is_rate_limit) {
            let reset = rate.and_then(|r| r.reset);
            tracing::warn!(?reset, "graphql errors array reports rate limiting");
            return Err(GraphqlFailure::RateLimited { reset });
        }
        let messages: Vec<String> = errors
            .iter()
            .map(|e| {
                e.get("message")
                    .and_then(|m| m.as_str())
                    .unwrap_or("unknown")
                    .to_string()
            })
            .collect();
        tracing::warn!(
            partial = data.is_some(),
            ?messages,
            "graphql errors; failing scope"
        );
        return Err(if data.is_some() {
            GraphqlFailure::PartialData { messages }
        } else {
            GraphqlFailure::Errors { messages }
        });
    }
    data.cloned()
        .ok_or_else(|| GraphqlFailure::Malformed("no data and no errors".into()))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rate() -> RateLimit {
        RateLimit {
            limit: None,
            remaining: 0,
            used: None,
            reset: Some(1_700_000_000),
            resource: None,
        }
    }

    // frob:ticket 01M4052QNSFSWV0SQ0A05XQ12K
    #[test]
    fn rate_limit_in_errors_is_a_failure_with_reset_and_no_data() {
        let body = br#"{"data":{"x":1},"errors":[{"type":"RATE_LIMITED","message":"API rate limit exceeded"}]}"#;
        let err = parse_response(body, Some(&rate())).unwrap_err();
        assert_eq!(
            err,
            GraphqlFailure::RateLimited {
                reset: Some(1_700_000_000)
            }
        );
    }

    // frob:ticket 01M4052QNSFSWV0SQ0A05XQ12K
    #[test]
    fn partial_data_fails_the_scope() {
        let body = br#"{"data":{"x":1},"errors":[{"message":"boom"}]}"#;
        let err = parse_response(body, None).unwrap_err();
        assert_eq!(
            err,
            GraphqlFailure::PartialData {
                messages: vec!["boom".into()]
            }
        );
    }

    #[test]
    fn clean_data_passes() {
        let v = parse_response(br#"{"data":{"x":1},"errors":[]}"#, None).unwrap();
        assert_eq!(v["x"], 1);
    }
}
