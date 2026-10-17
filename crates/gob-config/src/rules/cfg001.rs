//! `CFG001`: a materialized knob is absent from the product file

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use gob_rules::{Out, RepoRule, rule};

use crate::host::ConfigHost;

/// A materialized knob is absent from the product file
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CFG001",
    slug = "missing-materialized-knob",
    severity = Error,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    fix = Deterministic,
    applies = project,
    host = ConfigHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Cfg001;

/// The finding is raised by [`crate::check`] from the doctor, which reads the product file; this declaration registers the id.
impl<P: ?Sized + ConfigHost> RepoRule<P> for Cfg001 {
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
