//! Milestone rules the verbs share: semver versions, `new` idempotency and did-you-mean.
//!
//! Pure functions over folded [`Milestone`]s so the CLI layer only maps their
//! typed [`MilestoneError`] to a refusal; nothing here touches the ledger.

use crate::model::{Day, Milestone};

/// A milestone request that cannot be honoured, each with the fix the caller needs.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum MilestoneError {
    /// The version is not a valid semantic version.
    #[error("`{input}` is not a semantic version: {reason}")]
    BadVersion {
        /// The version as given.
        input: String,
        /// What is wrong with it.
        reason: &'static str,
    },
    /// A milestone with this version exists with different fields.
    #[error("milestone `{version}` already exists with different {}", fields.join(", "))]
    Conflict {
        /// The shared version.
        version: String,
        /// Names of the fields that differ (`goal`, `target`, `criteria`).
        fields: Vec<&'static str>,
    },
    /// No milestone has this version.
    #[error("no milestone has version `{input}`")]
    UnknownVersion {
        /// The version as given.
        input: String,
        /// Existing versions closest to the input, best first.
        suggestions: Vec<String>,
    },
}

/// Validate `input` as a semantic version (semver.org 2.0.0) and return it unchanged.
///
/// # Errors
///
/// [`MilestoneError::BadVersion`] naming the first rule it breaks.
pub fn parse_version(input: &str) -> Result<String, MilestoneError> {
    let bad = |reason| {
        tracing::debug!(input, reason, "version refused");
        Err(MilestoneError::BadVersion {
            input: input.to_owned(),
            reason,
        })
    };
    let (rest, build) = match input.split_once('+') {
        Some((r, b)) => (r, Some(b)),
        None => (input, None),
    };
    let (core, pre) = match rest.split_once('-') {
        Some((c, p)) => (c, Some(p)),
        None => (rest, None),
    };
    let parts: Vec<&str> = core.split('.').collect();
    if parts.len() != 3 {
        return bad("expected MAJOR.MINOR.PATCH");
    }
    for p in &parts {
        if p.is_empty() || !p.bytes().all(|b| b.is_ascii_digit()) {
            return bad("MAJOR, MINOR and PATCH must be plain numbers");
        }
        if p.len() > 1 && p.starts_with('0') {
            return bad("numbers must not have leading zeros");
        }
    }
    let ident_ok =
        |s: &str| !s.is_empty() && s.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'-');
    if let Some(pre) = pre {
        for id in pre.split('.') {
            if !ident_ok(id) {
                return bad(
                    "pre-release identifiers must be non-empty ASCII letters, digits or `-`",
                );
            }
            if id.bytes().all(|b| b.is_ascii_digit()) && id.len() > 1 && id.starts_with('0') {
                return bad("numeric pre-release identifiers must not have leading zeros");
            }
        }
    }
    if let Some(build) = build
        && !build.split('.').all(ident_ok)
    {
        return bad("build identifiers must be non-empty ASCII letters, digits or `-`");
    }
    Ok(input.to_owned())
}

/// What `milestone new` should do given the milestones that already exist.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NewPlan {
    /// No milestone has the version: create it.
    Create,
    /// An identical milestone exists: nothing to write.
    Already(Box<Milestone>),
}

/// Decide `milestone new`: create, report `already`, or refuse a conflicting repeat.
///
/// # Errors
///
/// [`MilestoneError::Conflict`] when the version exists with a different goal, target or criteria.
pub fn plan_new(
    existing: &[Milestone],
    version: &str,
    goal: &str,
    target: Option<Day>,
    criteria: &[String],
) -> Result<NewPlan, MilestoneError> {
    let Some(m) = existing.iter().find(|m| m.version == version) else {
        return Ok(NewPlan::Create);
    };
    let mut fields = Vec::new();
    if m.goal != goal {
        fields.push("goal");
    }
    if m.target != target {
        fields.push("target");
    }
    if !m
        .criteria
        .iter()
        .map(|c| c.text.as_str())
        .eq(criteria.iter().map(String::as_str))
    {
        fields.push("criteria");
    }
    if fields.is_empty() {
        tracing::debug!(version, "milestone new repeats an identical milestone");
        Ok(NewPlan::Already(Box::new(m.clone())))
    } else {
        Err(MilestoneError::Conflict {
            version: version.to_owned(),
            fields,
        })
    }
}

/// The [`MilestoneError::UnknownVersion`] for `input`, suggesting the closest of `existing`.
pub fn unknown_version(existing: &[Milestone], input: &str) -> MilestoneError {
    let mut scored: Vec<(usize, &str)> = existing
        .iter()
        .map(|m| (distance(&m.version, input), m.version.as_str()))
        .filter(|(d, _)| *d <= 3)
        .collect();
    scored.sort_unstable();
    MilestoneError::UnknownVersion {
        input: input.to_owned(),
        suggestions: scored
            .into_iter()
            .take(3)
            .map(|(_, v)| v.to_owned())
            .collect(),
    }
}

/// Levenshtein distance between two short strings.
fn distance(a: &str, b: &str) -> usize {
    let b: Vec<char> = b.chars().collect();
    let mut row: Vec<usize> = (0..=b.len()).collect();
    for (i, ca) in a.chars().enumerate() {
        let mut prev = row[0];
        row[0] = i + 1;
        for (j, cb) in b.iter().enumerate() {
            let cur = row[j + 1];
            row[j + 1] = (prev + usize::from(ca != *cb)).min(row[j] + 1).min(cur + 1);
            prev = cur;
        }
    }
    row[b.len()]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accepts_semver() {
        for v in [
            "0.532.0",
            "1.0.0",
            "1.2.3-rc.1",
            "1.2.3+build.5",
            "1.0.0-alpha-1+x",
        ] {
            assert_eq!(parse_version(v).as_deref(), Ok(v), "{v}");
        }
    }

    #[test]
    fn refuses_non_semver() {
        for v in [
            "", "1", "1.2", "v1.2.3", "01.2.3", "1.2.x", "1.2.3-", "1.2.3-01", "1.2.3+", "1.2.3.4",
        ] {
            assert!(parse_version(v).is_err(), "{v}");
        }
    }

    #[test]
    fn distance_basics() {
        assert_eq!(distance("0.532.0", "0.532.0"), 0);
        assert_eq!(distance("0.532.0", "0.533.0"), 1);
        assert_eq!(distance("", "abc"), 3);
    }
}
