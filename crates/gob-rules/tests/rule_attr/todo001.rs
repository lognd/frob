//! The TODO001-shaped example rule: file scope, universal, evaluated against a host trait.

use gob_rules::{FileCx, FileRule, rule};

use super::ObligationHost;

#[rule(
    id = "TODO001",
    slug = "bare-work-marker",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = File,
    fix = Manual,
    applies = universal(needs = [Comments], min_fidelity = F1),
    host = ObligationHost,
    version = 1,
    since = "0.1.0",
)]
/// Flags a bare work marker comment that no `frob:todo` directive owns.
pub struct Todo001;

impl<P: ?Sized + ObligationHost> FileRule<P> for Todo001 {
    fn check(&self, cx: &FileCx<'_, P>, out: &mut gob_rules::Out<'_, Self>) {
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
