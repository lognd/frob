//! The spike's TODO001-shaped rule: file scope, universal, evaluated against a host trait.

use super::{FileCx, FileRule, ObligationHost, Out, rule};

#[rule(
    id = "TODO001", slug = "bare-work-marker",
    severity = Error, polarity = Pplus, must_measure = false,
    scope = File, fix = Manual,
    applies = universal(needs = [Comments], min_fidelity = F1),
    host = ObligationHost,
    version = 1, since = "0.1.0",
)]
/// Flags a bare work marker comment that no `frob:todo` directive owns.
pub struct Todo001;

impl<P: ?Sized + ObligationHost> FileRule<P> for Todo001 {
    fn check(&self, cx: &FileCx<'_, P>, out: &mut Out<'_, Self>) {
        for (offset, text) in cx.host.comments(cx.text) {
            if text.contains("TODO") && !cx.host.owned_by_todo(cx.text, offset) {
                out.fire(
                    offset,
                    "bare work marker: file a ticket, then add `frob:todo <ulid>`",
                );
            }
        }
    }
}

/// A line-comment host for demos and tests: `//` comments, owned when `frob:todo` follows.
pub fn todo001_demo_host() -> impl ObligationHost {
    struct Demo;
    impl ObligationHost for Demo {
        fn comments<'t>(&self, text: &'t str) -> Vec<(usize, &'t str)> {
            text.match_indices("//")
                .map(|(i, _)| (i, text[i..].lines().next().unwrap_or("")))
                .collect()
        }
        fn owned_by_todo(&self, text: &str, offset: usize) -> bool {
            text[offset..]
                .lines()
                .next()
                .is_some_and(|l| l.contains("frob:todo"))
        }
    }
    Demo
}
