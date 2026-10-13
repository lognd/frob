//! The human review lock's pure judgment (crunk.md 4.1): given a subject's current inputs, its
//! recorded `[[review]]` entry, the `[review]` policy and the introducing commit's signature, what
//! state is the review in? The product (crunk-check) gathers the inputs and signatures; the rules
//! HUMAN001 and HUMAN002 only read the resulting [`ReviewFacts`].

// frob:ticket 01M4CXSM408E7A05DWKENDB7V4

use std::collections::BTreeMap;

use crunk_spec::table::ReviewConfig;
use gob_lock::{ReviewEntry, ReviewVerdict};

/// A thing a human reviews: one screen state, with the digest of every input it depends on.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Subject {
    /// The lock key, `screen/<id>/<state>`.
    pub id: String,
    /// The screen id, for messages.
    pub screen: String,
    /// Input name (`spec:...`, `source:<path>`, `token:<--name>`, `font:<family>`, `render`) to its digest.
    pub inputs: BTreeMap<String, String>,
}

impl Subject {
    /// The combined digest recorded in the lock: a hash of the subject id and every input.
    pub fn digest(&self) -> String {
        let mut hasher = blake3::Hasher::new();
        hasher.update(self.id.as_bytes());
        for (name, digest) in &self.inputs {
            hasher.update(b"\n");
            hasher.update(name.as_bytes());
            hasher.update(b"\t");
            hasher.update(digest.as_bytes());
        }
        hasher.finalize().to_hex()[..32].to_owned()
    }
}

/// What the introducing commit of an ack said about its signature.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AckSignature {
    /// A good signature by this key id or fingerprint.
    Good(String),
    /// The commit is unsigned or its signature is not good; the reason.
    Unsigned(String),
}

/// Where a subject's review stands.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ReviewStatus {
    /// Reviewed, approved, trusted and unchanged since.
    Current,
    /// No recorded review.
    Missing,
    /// An input changed since the review; the changed input names.
    Stale(Vec<String>),
    /// The reviewer is not on the allow-list.
    Unlisted(String),
    /// `require_signed` and the ack's commit is not validly signed by a listed key; the reason.
    Unsigned(String),
    /// A current review that rejects the subject; the reviewer and note.
    Rejected(String),
}

/// One subject with its judged status and the sentence that explains it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReviewFinding {
    /// The lock key.
    pub subject: String,
    /// The screen id.
    pub screen: String,
    /// The status.
    pub status: ReviewStatus,
    /// The one-sentence explanation naming the screen and what changed.
    pub message: String,
}

/// Every judged subject of a project; what the HUMAN rules read.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ReviewFacts {
    /// One row per reviewable subject.
    pub findings: Vec<ReviewFinding>,
    /// Why the facts could not be gathered (an unreadable lock or token set), when they could not.
    pub unreadable: Option<String>,
}

/// The input names whose digests differ between `then` and `now` (added, removed or changed).
pub fn changed_inputs(
    then: &BTreeMap<String, String>,
    now: &BTreeMap<String, String>,
) -> Vec<String> {
    let mut out: Vec<String> = now
        .iter()
        .filter(|(k, v)| then.get(*k) != Some(*v))
        .map(|(k, _)| k.clone())
        .collect();
    out.extend(then.keys().filter(|k| !now.contains_key(*k)).cloned());
    out.sort();
    out.dedup();
    out
}

/// True when `identity` (`Name <email>` or a bare id) names reviewer `id`.
fn names(identity: &str, id: &str) -> bool {
    identity == id || identity.contains(&format!("<{id}>"))
}

fn key_matches(have: &str, listed: &str) -> bool {
    let (a, b) = (have.to_ascii_lowercase(), listed.to_ascii_lowercase());
    !a.is_empty() && !b.is_empty() && (a == b || a.ends_with(&b) || b.ends_with(&a))
}

/// Judge one subject: `entry` is its recorded review, `signature` the introducing commit's.
pub fn judge(
    subject: &Subject,
    entry: Option<&ReviewEntry>,
    policy: &ReviewConfig,
    signature: Option<&AckSignature>,
) -> ReviewFinding {
    let screen = &subject.screen;
    let (status, message) = match entry {
        None => (
            ReviewStatus::Missing,
            format!(
                "screen `{screen}` ({}) has no recorded human review; run `crunk review`",
                subject.id
            ),
        ),
        Some(e) if e.digest != subject.digest() => {
            let changed = changed_inputs(&e.inputs, &subject.inputs);
            let what = if changed.is_empty() {
                "its inputs".to_owned()
            } else {
                changed
                    .iter()
                    .map(|n| format!("`{n}`"))
                    .collect::<Vec<_>>()
                    .join(", ")
            };
            (
                ReviewStatus::Stale(changed),
                format!(
                    "screen `{screen}` ({}) changed since {} reviewed it: {what}; run `crunk ack` after re-review",
                    subject.id, e.reviewer
                ),
            )
        }
        Some(e) => trusted(subject, e, policy, signature),
    };
    tracing::debug!(subject = %subject.id, ?status, "human review judged");
    ReviewFinding {
        subject: subject.id.clone(),
        screen: subject.screen.clone(),
        status,
        message,
    }
}

/// The trust checks and verdict of a review whose digest is current.
fn trusted(
    subject: &Subject,
    e: &ReviewEntry,
    policy: &ReviewConfig,
    signature: Option<&AckSignature>,
) -> (ReviewStatus, String) {
    let screen = &subject.screen;
    let reviewer = policy.reviewers.iter().find(|r| names(&e.reviewer, &r.id));
    if !policy.reviewers.is_empty() && reviewer.is_none() {
        return (
            ReviewStatus::Unlisted(e.reviewer.clone()),
            format!(
                "the review of screen `{screen}` ({}) was recorded by {}, who is not a listed reviewer",
                subject.id, e.reviewer
            ),
        );
    }
    if policy.require_signed {
        let listed = |key: &str| {
            policy
                .reviewers
                .iter()
                .filter(|r| reviewer.is_none_or(|m| m.id == r.id))
                .any(|r| r.keys.iter().any(|k| key_matches(key, k)))
        };
        match signature {
            Some(AckSignature::Good(key)) if listed(key) => {}
            Some(AckSignature::Good(key)) => {
                return (
                    ReviewStatus::Unsigned(format!("key {key} is not listed for the reviewer")),
                    format!(
                        "the review of screen `{screen}` ({}) was committed with key {key}, which is not listed for reviewer {}",
                        subject.id, e.reviewer
                    ),
                );
            }
            Some(AckSignature::Unsigned(why)) => {
                return (
                    ReviewStatus::Unsigned(why.clone()),
                    format!(
                        "the review of screen `{screen}` ({}) was added in an unsigned commit ({why})",
                        subject.id
                    ),
                );
            }
            None => {
                return (
                    ReviewStatus::Unsigned("signature not read".to_owned()),
                    format!(
                        "the review of screen `{screen}` ({}) has no readable commit signature",
                        subject.id
                    ),
                );
            }
        }
    }
    match e.verdict {
        ReviewVerdict::Approved => (ReviewStatus::Current, String::new()),
        ReviewVerdict::Rejected => {
            let note = e.note.as_deref().unwrap_or("no note");
            (
                ReviewStatus::Rejected(e.reviewer.clone()),
                format!(
                    "screen `{screen}` ({}) was rejected by {}: {note}",
                    subject.id, e.reviewer
                ),
            )
        }
    }
}
