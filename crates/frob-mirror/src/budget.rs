//! Budget planner (mirror.md 3.2, F8): how much of the tracker's rate limit one run may spend.
//!
//! A run spends at most a share of what remains, at most C creates and M mutations,
//! serially with a minimum spacing between mutations.

// frob:ticket 01M4052RRC7X5Y23PNBDKR9V6W

use std::time::Duration;

use tracing::{debug, warn};

/// Rate-limit state read from the response headers at the start of a run.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RateLimit {
    /// Calls left in the current window (`x-ratelimit-remaining`).
    pub remaining: Option<u64>,
    /// Unix time the window resets (`x-ratelimit-reset`).
    pub reset: Option<u64>,
}

/// Operator configuration for the planner.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct BudgetConfig {
    /// Percent (0..=100) of the remaining calls one run may spend.
    pub share_percent: u64,
    /// Most creates per run.
    pub max_creates: u64,
    /// Most mutations per run.
    pub max_mutations: u64,
    /// Calls needed to read one ticket's state.
    pub reads_per_ticket: u64,
    /// Minimum wait between mutations.
    pub spacing: Duration,
}

impl Default for BudgetConfig {
    /// The design defaults: half the remaining calls, 50 creates, 300 mutations, 1 s spacing.
    fn default() -> Self {
        Self {
            share_percent: 50,
            max_creates: 50,
            max_mutations: 300,
            reads_per_ticket: 2,
            spacing: Duration::from_secs(1),
        }
    }
}

/// The planned allowance for one run.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Plan {
    /// Total calls the run may make.
    pub calls: u64,
    /// Creates the run may make.
    pub creates: u64,
    /// Mutations the run may make (creates included).
    pub mutations: u64,
    /// Minimum wait between mutations.
    pub spacing: Duration,
}

/// Why no plan could be made; both report MIR001.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum BudgetError {
    /// The rate-limit headers were absent, so the run must not guess (MIR001).
    #[error("MIR001 budget-unknown: rate-limit headers missing ({missing})")]
    HeadersMissing {
        /// Which header(s) were absent.
        missing: &'static str,
    },
    /// The allowance cannot cover one ticket's reads plus one write (MIR001).
    #[error("MIR001 budget-too-small: {allowed} calls allowed, {needed} needed for one ticket")]
    TooSmall {
        /// Calls the share allows.
        allowed: u64,
        /// Calls one ticket's reads plus one write need.
        needed: u64,
    },
}

/// Plan a run from the rate-limit headers; makes no write itself.
///
/// # Errors
/// `HeadersMissing` when a header is absent; `TooSmall` when one ticket does not fit.
pub fn plan(limit: RateLimit, cfg: &BudgetConfig) -> Result<Plan, BudgetError> {
    let missing = match (limit.remaining, limit.reset) {
        (Some(_), Some(_)) => None,
        (None, Some(_)) => Some("x-ratelimit-remaining"),
        (Some(_), None) => Some("x-ratelimit-reset"),
        (None, None) => Some("x-ratelimit-remaining, x-ratelimit-reset"),
    };
    if let Some(missing) = missing {
        warn!(missing, "budget: rate-limit headers missing, stopping");
        return Err(BudgetError::HeadersMissing { missing });
    }
    let remaining = limit.remaining.unwrap_or(0);
    let calls = remaining.saturating_mul(cfg.share_percent.min(100)) / 100;
    let needed = cfg.reads_per_ticket + 1;
    if calls < needed {
        warn!(calls, needed, "budget: too small for one ticket");
        return Err(BudgetError::TooSmall {
            allowed: calls,
            needed,
        });
    }
    let mutations = cfg.max_mutations.min(calls);
    let creates = cfg.max_creates.min(mutations);
    debug!(calls, creates, mutations, "budget: planned");
    Ok(Plan {
        calls,
        creates,
        mutations,
        spacing: cfg.spacing,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn lim(r: Option<u64>, t: Option<u64>) -> RateLimit {
        RateLimit {
            remaining: r,
            reset: t,
        }
    }

    #[test]
    fn default_share_caps_calls_creates_and_mutations() {
        let p = plan(lim(Some(5000), Some(1)), &BudgetConfig::default()).unwrap();
        assert_eq!((p.calls, p.creates, p.mutations), (2500, 50, 300));
        assert_eq!(p.spacing, Duration::from_secs(1));
    }

    #[test]
    fn below_one_ticket_is_too_small() {
        let e = plan(lim(Some(5), Some(1)), &BudgetConfig::default()).unwrap_err();
        assert!(matches!(e, BudgetError::TooSmall { .. }));
        assert!(e.to_string().contains("MIR001"));
    }

    #[test]
    fn missing_headers_stop_with_reason() {
        let e = plan(lim(None, Some(1)), &BudgetConfig::default()).unwrap_err();
        assert!(matches!(e, BudgetError::HeadersMissing { .. }));
        assert!(e.to_string().contains("MIR001"));
        assert!(plan(lim(Some(9), None), &BudgetConfig::default()).is_err());
    }
}
