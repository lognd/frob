//! STATE007: a screen whose status is `ready` or `completed` but whose recorded `content_hash` is missing or no longer matches its content. Off when the project has no screen files.

// frob:ticket 01M4CXR89ERNB60CEDG60E2DXH

use crunk_spec::table::ScreenStatus;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_screen_inputs, screen_subjects};
use crate::screen_files::content_hash;

/// A locked screen whose content hash is missing or stale.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "STATE007",
    slug = "screen-hash-stale",
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
pub struct State007;

impl<P: ?Sized + CrunkHost> RepoRule<P> for State007 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(screens) = host.screens() else {
            return;
        };
        for file in &screens.files {
            if !matches!(
                file.screen.status,
                Some(ScreenStatus::Ready | ScreenStatus::Completed)
            ) {
                continue;
            }
            let want = content_hash(&file.screen);
            let message = match file.screen.content_hash.as_deref() {
                None => format!(
                    "screen '{}' is locked but records no content_hash (expected {want})",
                    file.screen.id
                ),
                Some(have) if have != want => format!(
                    "screen '{}' changed since its content_hash was recorded (recorded {have}, now {want}); set status to `changed` or record the new hash",
                    file.screen.id
                ),
                Some(_) => continue,
            };
            tracing::debug!(path = %file.path, "STATE007: hash missing or stale");
            out.fire_in(&file.path, file.offset_of("status"), message);
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_screen_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for State007 {
    fn subjects(&self, host: &P) -> usize {
        screen_subjects(host)
    }
}
