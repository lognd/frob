//! Engine entry-point vocabulary: the names an engine calls itself, so no caller exists in the repository.
//!
//! A pack (the built-in `unity` pack) supplies the vocabulary; reach and coverage rules ask it
//! whether a method is called by the engine and so counts as a root.

// frob:ticket 01M44YQXS4BXE0X07FBYR0STJ5

use std::collections::BTreeSet;

/// Vocabulary class of message names (`Update`).
pub const CLASS_MESSAGE: &str = "entry.message";
/// Vocabulary class of message name prefixes (`OnTrigger` for `OnTriggerEnter`).
pub const CLASS_MESSAGE_PREFIX: &str = "entry.message_prefix";
/// Vocabulary class of engine base types (`MonoBehaviour`).
pub const CLASS_BASE: &str = "entry.base";
/// Vocabulary class of attributes that make a method an entry point (`MenuItem`).
pub const CLASS_METHOD_ATTRIBUTE: &str = "entry.method_attribute";
/// Vocabulary class of attributes on a type (`InitializeOnLoad`).
pub const CLASS_TYPE_ATTRIBUTE: &str = "entry.type_attribute";

/// The engine entry points of one language, as declared by a pack.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct EngineVocab {
    /// Message method names the engine calls on a type deriving from an engine base.
    pub messages: BTreeSet<String>,
    /// Name prefixes of message families (`OnTrigger`).
    pub message_prefixes: BTreeSet<String>,
    /// Engine base types whose derived types receive messages.
    pub bases: BTreeSet<String>,
    /// Attributes that make the annotated method an entry point.
    pub method_attributes: BTreeSet<String>,
    /// Type attributes: those that root the static constructor of the type.
    pub type_attributes: BTreeSet<String>,
}

impl EngineVocab {
    /// Adds `names` to the set for vocabulary `class`; false when `class` is not an engine class.
    pub fn add_class(&mut self, class: &str, names: impl IntoIterator<Item = String>) -> bool {
        let set = match class {
            CLASS_MESSAGE => &mut self.messages,
            CLASS_MESSAGE_PREFIX => &mut self.message_prefixes,
            CLASS_BASE => &mut self.bases,
            CLASS_METHOD_ATTRIBUTE => &mut self.method_attributes,
            CLASS_TYPE_ATTRIBUTE => &mut self.type_attributes,
            _ => return false,
        };
        set.extend(names);
        true
    }

    /// True when `name` is an engine message (an exact name or a member of a prefix family).
    pub fn is_message(&self, name: &str) -> bool {
        self.messages.contains(name)
            || self
                .message_prefixes
                .iter()
                .any(|p| name.starts_with(p.as_str()))
    }

    /// True when the vocabulary names nothing.
    pub fn is_empty(&self) -> bool {
        *self == Self::default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests EngineVocab.is_message
    #[test]
    fn messages_match_by_name_and_prefix() {
        let mut v = EngineVocab::default();
        assert!(v.add_class(CLASS_MESSAGE, ["Update".to_owned()]));
        assert!(v.add_class(CLASS_MESSAGE_PREFIX, ["OnTrigger".to_owned()]));
        assert!(!v.add_class("net", ["x".to_owned()]));
        assert!(v.is_message("Update") && v.is_message("OnTriggerEnter2D"));
        assert!(!v.is_message("Tick"));
    }
}
