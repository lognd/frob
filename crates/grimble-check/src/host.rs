//! The host the declared grimble rules judge: the model facts and the binding facts together.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P
use grimble_arch::host::ArchHost;
use grimble_bind::host::BindHost;
use grimble_model::host::MdlHost;

use crate::GrimbleInputs;

/// Everything a declared grimble rule may ask: the model, binding and architecture hosts.
pub trait GrimbleHost: MdlHost + BindHost + ArchHost {}

impl<T: MdlHost + BindHost + ArchHost + ?Sized> GrimbleHost for T {}

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
