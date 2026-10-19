//! The host the declared grimble rules judge: the model facts and the binding facts together.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P
use grimble_bind::host::BindHost;
use grimble_model::host::MdlHost;

use crate::GrimbleInputs;

/// Everything a declared grimble rule may ask: the model host and the binding host.
pub trait GrimbleHost: MdlHost + BindHost {}

impl<T: MdlHost + BindHost + ?Sized> GrimbleHost for T {}

impl MdlHost for GrimbleInputs {}

impl BindHost for GrimbleInputs {
    fn subjects_of(&self, id: &str) -> usize {
        self.binding.subjects.get(id).copied().unwrap_or(0)
    }
}
