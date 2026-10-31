//! LOG001: Direct output (print, println!, console.*, Console.Write*, sys.stdout and the like) outside the logging layer.

// frob:ticket 01M5XMR67K19SFAWNTDJKKJPTT

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::LogHost;

/// Direct output (print, println!, console.*, Console.Write*, sys.stdout and the like) outside the logging layer.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "LOG001",
    slug = "direct-output",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = LogHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Log001;

impl<P: ?Sized + LogHost> RepoRule<P> for Log001 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + LogHost> Measured<P> for Log001 {
    fn subjects(&self, host: &P) -> usize {
        host.log_subjects_of("LOG001")
    }
}
