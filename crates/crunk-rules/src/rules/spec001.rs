//! SPEC001: a component, screen, flow or content file that cannot be read or parsed. Off when the project has none of them.

// frob:ticket 01M7ETK8WHHFV8590QXMH57TRZ

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, design_file_problems, design_file_subjects, inapplicable_without};

/// A design file that is skipped by every other rule because it does not load.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SPEC001",
    slug = "design-file-invalid",
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
pub struct Spec001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Spec001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        for problem in design_file_problems(host) {
            tracing::debug!(path = %problem.path, "SPEC001: design file does not load");
            out.fire_in(&problem.path, 0, problem.message.clone());
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        inapplicable_without(
            host,
            design_file_subjects(host),
            "no component, screen, flow or content files",
        )
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Spec001 {
    fn subjects(&self, host: &P) -> usize {
        design_file_subjects(host)
    }
}
