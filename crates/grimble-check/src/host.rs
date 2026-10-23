//! The host the declared grimble rules judge: the model facts and the binding facts together.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P
// frob:ticket 01M5HJ075VJZAP88EVTCX1MH8C
use grimble_arch::host::ArchHost;
use grimble_bind::host::BindHost;
use grimble_lints::host::{PathHost, TimeHost};
use grimble_model::host::MdlHost;

use crate::GrimbleInputs;

/// What a COH rule may ask of its product: how many units the scan examined.
///
/// The COH rules are evaluated in one pass over the walk (`coh_pass`), so the declared rules are
/// staged (never run one by one); `coh_subjects_of` is what the must-measure rules report from.
pub trait CohHost {
    /// Units the COH pass examined for rule `id` on this run (0 when it examined none).
    fn coh_subjects_of(&self, id: &str) -> usize;
}

/// Everything a declared grimble rule may ask: the model, binding, architecture and path hosts.
pub trait GrimbleHost: MdlHost + BindHost + ArchHost + PathHost + TimeHost + CohHost {}

impl<T: MdlHost + BindHost + ArchHost + PathHost + TimeHost + CohHost + ?Sized> GrimbleHost for T {}

impl MdlHost for GrimbleInputs {}

impl BindHost for GrimbleInputs {
    fn subjects_of(&self, id: &str) -> usize {
        self.binding.subjects.get(id).copied().unwrap_or(0)
    }
}

impl ArchHost for GrimbleInputs {
    fn arch_subjects_of(&self, id: &str) -> usize {
        self.arch.subjects.get(id).copied().unwrap_or(0)
    }
}

impl PathHost for GrimbleInputs {
    fn path_subjects_of(&self, id: &str) -> usize {
        self.path.subjects.get(id).copied().unwrap_or(0)
    }
}

impl TimeHost for GrimbleInputs {
    fn time_subjects_of(&self, id: &str) -> usize {
        self.time.subjects.get(id).copied().unwrap_or(0)
    }
}

impl CohHost for GrimbleInputs {
    fn coh_subjects_of(&self, id: &str) -> usize {
        self.coh.subjects.get(id).copied().unwrap_or(0)
    }
}
