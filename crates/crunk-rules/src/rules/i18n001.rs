//! I18N001: a content key's text, grown by the pseudo-locale expansion, no longer fits its `max_chars` budget. Off when the project has no content files.

// frob:ticket 01M5H5P5H1CSMP9Q3NF4RY4M26

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, content_subjects, missing_content_inputs};
use crate::i18n::{PSEUDO_EXPANSION_PERCENT, expanded_chars};

/// A copy key that fits its budget in the source language but not once translated longer.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "I18N001",
    slug = "pseudo-locale-expansion",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct I18n001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for I18n001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.content() else {
            return;
        };
        for file in &facts.files {
            for key in &file.content.keys {
                let Some(budget) = key.max_chars else {
                    continue;
                };
                let len = key.text.chars().count();
                let expanded = expanded_chars(&key.text);
                // A key already over budget is CONTENT002's finding, not this rule's.
                if len as u64 > u64::from(budget) || expanded as u64 <= u64::from(budget) {
                    continue;
                }
                let message = format!(
                    "copy key '{}' is {len} characters, but a pseudo-locale ({PSEUDO_EXPANSION_PERCENT}% longer) makes it {expanded}, over its budget of {budget}",
                    key.id,
                );
                tracing::debug!(path = %file.path, key = %key.id, len, expanded, budget, "I18N001: overflows when expanded");
                out.fire_in(&file.path, file.offset_of_key(&key.id), message);
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_content_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for I18n001 {
    fn subjects(&self, host: &P) -> usize {
        content_subjects(host)
    }
}
