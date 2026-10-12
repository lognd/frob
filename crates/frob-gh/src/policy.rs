//! The mirror error policy (mirror.md 3.2): honour Retry-After, stop at no budget, 60 s doubling.

use std::time::Duration;

use crate::{Error, Pause, RateLimit, RawRequest, RawResponse, Transport};

/// Why a run must stop; the caller records it and reports MIR001 where it applies.
#[derive(Debug, thiserror::Error)]
pub enum Halt {
    /// Rate limited with no remaining budget: stop without sleeping; the reset time is recorded.
    #[error("rate limited with no budget left; window resets at {reset:?} (epoch seconds)")]
    RateLimited {
        /// `x-ratelimit-reset`, UTC epoch seconds, when the server reported it.
        reset: Option<u64>,
    },
    /// Every permitted retry was spent on 5xx or Retry-After answers.
    #[error("gave up after {retries} retries; last status {status}")]
    RetriesExhausted {
        /// Retries performed after the first attempt.
        retries: u32,
        /// The last status seen.
        status: u16,
    },
    /// The transport itself failed.
    #[error(transparent)]
    Transport(#[from] Error),
}

/// Retry bounds of the mirror: first wait, doubling, and a retry ceiling.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ErrorPolicy {
    /// Wait before the first retry when the server named none; doubles per retry.
    pub first_wait: Duration,
    /// Retries after the first attempt.
    pub max_retries: u32,
}

impl Default for ErrorPolicy {
    fn default() -> Self {
        Self {
            first_wait: Duration::from_secs(60),
            max_retries: 3,
        }
    }
}

impl ErrorPolicy {
    /// The doubling wait before retry number `retry` (1-based).
    pub fn wait_for(&self, retry: u32) -> Duration {
        let factor = 1u32
            .checked_shl(retry.saturating_sub(1))
            .unwrap_or(u32::MAX);
        self.first_wait.saturating_mul(factor)
    }
}

/// What to do with one response.
enum Verdict {
    /// Hand it to the caller.
    Done,
    /// Stop the run now.
    Stop(Option<u64>),
    /// Retry after the server-named wait, if any.
    Retry(Option<Duration>),
}

fn classify(response: &RawResponse) -> Verdict {
    let rate = RateLimit::parse(&response.headers);
    let asked = response
        .headers
        .get("retry-after")
        .and_then(|v| v.trim().parse::<u64>().ok())
        .map(Duration::from_secs);
    let limited = matches!(response.status, 429)
        || (matches!(response.status, 403)
            && (asked.is_some() || rate.as_ref().is_some_and(|r| r.remaining == 0)));
    if limited {
        if let Some(r) = rate.as_ref().filter(|r| r.remaining == 0) {
            return Verdict::Stop(r.reset);
        }
        return Verdict::Retry(asked);
    }
    if response.status >= 500 {
        return Verdict::Retry(asked);
    }
    Verdict::Done
}

/// Send `request`, applying the policy; non-retryable responses (including 4xx) are returned as-is.
///
/// # Errors
/// [`Halt`] when the run must stop: no budget, retries spent, or a transport failure.
pub async fn send_with_policy<T: Transport, P: Pause>(
    transport: &T,
    pause: &P,
    policy: ErrorPolicy,
    request: RawRequest,
) -> Result<RawResponse, Halt> {
    let mut retries = 0u32;
    loop {
        let response = transport.send(request.clone()).await?;
        match classify(&response) {
            Verdict::Done => return Ok(response),
            Verdict::Stop(reset) => {
                tracing::warn!(?reset, "rate limited with no remaining budget; stopping");
                return Err(Halt::RateLimited { reset });
            }
            Verdict::Retry(asked) => {
                if retries >= policy.max_retries {
                    tracing::warn!(retries, status = response.status, "retries exhausted");
                    return Err(Halt::RetriesExhausted {
                        retries,
                        status: response.status,
                    });
                }
                retries += 1;
                let wait = asked.unwrap_or_else(|| policy.wait_for(retries));
                tracing::info!(retries, ?wait, status = response.status, "retrying");
                pause.pause(wait).await;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;
    use std::future::Future;
    use std::sync::Mutex;

    use super::*;
    use crate::Method;

    struct Script(Mutex<Vec<RawResponse>>, Mutex<usize>);

    impl Transport for Script {
        fn send(&self, _r: RawRequest) -> impl Future<Output = Result<RawResponse, Error>> + Send {
            *self.1.lock().unwrap() += 1;
            std::future::ready(Ok(self.0.lock().unwrap().remove(0)))
        }
    }

    #[derive(Default)]
    struct Clock(Mutex<Vec<Duration>>);

    impl Pause for Clock {
        async fn pause(&self, d: Duration) {
            self.0.lock().unwrap().push(d);
        }
    }

    fn resp(status: u16, headers: &[(&str, &str)]) -> RawResponse {
        RawResponse {
            status,
            headers: headers
                .iter()
                .map(|(k, v)| ((*k).to_string(), (*v).to_string()))
                .collect::<BTreeMap<_, _>>(),
            body: Vec::new(),
        }
    }

    fn req() -> RawRequest {
        RawRequest {
            method: Method::Get,
            url: "https://api.github.com/x".into(),
            headers: BTreeMap::new(),
            body: None,
        }
    }

    // frob:ticket 01M4052QNSFSWV0SQ0A05XQ12K
    #[tokio::test(flavor = "current_thread")]
    async fn no_budget_stops_without_sleeping_and_reports_reset() {
        let t = Script(
            Mutex::new(vec![resp(
                403,
                &[
                    ("x-ratelimit-remaining", "0"),
                    ("x-ratelimit-reset", "1700000000"),
                    ("retry-after", "30"),
                ],
            )]),
            Mutex::new(0),
        );
        let clock = Clock::default();
        let err = send_with_policy(&t, &clock, ErrorPolicy::default(), req())
            .await
            .unwrap_err();
        assert!(matches!(
            err,
            Halt::RateLimited {
                reset: Some(1_700_000_000)
            }
        ));
        assert!(clock.0.lock().unwrap().is_empty());
    }

    // frob:ticket 01M4052QNSFSWV0SQ0A05XQ12K
    #[tokio::test(flavor = "current_thread")]
    async fn repeated_5xx_waits_60_120_240_then_stops_after_three_retries() {
        let t = Script(
            Mutex::new((0..4).map(|_| resp(502, &[])).collect()),
            Mutex::new(0),
        );
        let clock = Clock::default();
        let err = send_with_policy(&t, &clock, ErrorPolicy::default(), req())
            .await
            .unwrap_err();
        assert!(matches!(
            err,
            Halt::RetriesExhausted {
                retries: 3,
                status: 502
            }
        ));
        let secs: Vec<u64> = clock
            .0
            .lock()
            .unwrap()
            .iter()
            .map(Duration::as_secs)
            .collect();
        assert_eq!(secs, vec![60, 120, 240]);
        assert_eq!(*t.1.lock().unwrap(), 4);
    }

    #[tokio::test(flavor = "current_thread")]
    async fn retry_after_is_honoured_with_budget_left() {
        let t = Script(
            Mutex::new(vec![
                resp(
                    429,
                    &[("retry-after", "7"), ("x-ratelimit-remaining", "10")],
                ),
                resp(200, &[]),
            ]),
            Mutex::new(0),
        );
        let clock = Clock::default();
        let r = send_with_policy(&t, &clock, ErrorPolicy::default(), req())
            .await
            .unwrap();
        assert_eq!(r.status, 200);
        assert_eq!(*clock.0.lock().unwrap(), vec![Duration::from_secs(7)]);
    }
}
