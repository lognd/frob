//! Engine entry-point vocabulary: the names an engine calls itself, so no caller exists in the repository.
//!
//! A pack (the built-in `unity` pack) supplies the vocabulary; reach and coverage rules ask it
//! whether a method is called by the engine and so counts as a root, and effect and flow rules ask
//! whether a field is written from outside the code (the editor serializer) so a never-assigned
//! report does not fire for it.

// frob:ticket 01M44YQXS4BXE0X07FBYR0STJ5
// frob:ticket 01M44YQY6KR3NCCNGKJ9QK3N9A

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
/// Vocabulary class of attributes that make a field or `[field: ...]` property serialized (`SerializeField`).
pub const CLASS_SERIALIZE_ATTRIBUTE: &str = "serialized.attribute";
/// Vocabulary class of attributes that exclude a field from serialization (`NonSerialized`).
pub const CLASS_SKIP_ATTRIBUTE: &str = "serialized.skip_attribute";

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
    /// Attributes that make a field serialized, so the engine writes it from outside the code.
    pub serialize_attributes: BTreeSet<String>,
    /// Attributes that exclude a field from serialization; they win over every other signal.
    pub skip_attributes: BTreeSet<String>,
}

/// What a scan learned about one field declaration (or an auto-property with `[field: ...]` attributes).
#[derive(Debug, Clone, Copy)]
#[allow(
    clippy::struct_excessive_bools,
    reason = "independent declaration facts, one per modifier"
)]
pub struct FieldFacts<'a> {
    /// Attribute names on the field, `[field: X]` targets included.
    pub attributes: &'a [String],
    /// The declaration is `public`.
    pub is_public: bool,
    /// The declaration is `static`.
    pub is_static: bool,
    /// The declaration is `const`.
    pub is_const: bool,
    /// The declaration is `readonly`.
    pub is_readonly: bool,
    /// The declaration is a property rather than a field.
    pub is_property: bool,
    /// The declaring type derives from an engine base (through project-local bases).
    pub owner_is_engine: bool,
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
            CLASS_SERIALIZE_ATTRIBUTE => &mut self.serialize_attributes,
            CLASS_SKIP_ATTRIBUTE => &mut self.skip_attributes,
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

    /// True when the engine serializer writes the field from outside the code (scenes, prefabs, Inspector).
    ///
    /// Static, const and readonly members are never serialized, and a skip attribute (`NonSerialized`)
    /// always wins. A property is serialized only through a serialize attribute with a `field:` target.
    /// A serialize attribute is an explicit opt-in on any type; a public instance field is serialized
    /// only on a type deriving from an engine base.
    pub fn has_external_writer(&self, f: &FieldFacts<'_>) -> bool {
        let named = |set: &BTreeSet<String>| f.attributes.iter().any(|a| set.contains(a));
        let external = if f.is_static || f.is_const || f.is_readonly || named(&self.skip_attributes)
        {
            false
        } else if named(&self.serialize_attributes) {
            true
        } else {
            f.is_public && !f.is_property && f.owner_is_engine
        };
        tracing::trace!(external, ?f, "field external-writer decision");
        external
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

    fn vocab() -> EngineVocab {
        let mut v = EngineVocab::default();
        assert!(v.add_class(CLASS_SERIALIZE_ATTRIBUTE, ["SerializeField".to_owned()]));
        assert!(v.add_class(CLASS_SKIP_ATTRIBUTE, ["NonSerialized".to_owned()]));
        v
    }

    fn facts(attrs: &[String]) -> FieldFacts<'_> {
        FieldFacts {
            attributes: attrs,
            is_public: false,
            is_static: false,
            is_const: false,
            is_readonly: false,
            is_property: false,
            owner_is_engine: true,
        }
    }

    // frob:tests EngineVocab.has_external_writer
    #[test]
    fn serialized_fields_have_an_external_writer() {
        let v = vocab();
        let ser = ["SerializeField".to_owned()];
        let skip = ["NonSerialized".to_owned()];
        assert!(v.has_external_writer(&facts(&ser)));
        let public = FieldFacts {
            is_public: true,
            ..facts(&[])
        };
        assert!(v.has_external_writer(&public));
        let off_engine = FieldFacts {
            owner_is_engine: false,
            ..public
        };
        assert!(!v.has_external_writer(&off_engine));
        assert!(!v.has_external_writer(&FieldFacts { ..facts(&[]) }));
        assert!(!v.has_external_writer(&FieldFacts {
            attributes: &skip,
            ..public
        }));
        let both = ["SerializeField".to_owned(), "NonSerialized".to_owned()];
        assert!(!v.has_external_writer(&facts(&both)));
    }

    // frob:tests EngineVocab.has_external_writer
    #[test]
    fn static_const_readonly_and_plain_properties_are_not_serialized() {
        let v = vocab();
        let ser = ["SerializeField".to_owned()];
        let base = FieldFacts {
            is_public: true,
            ..facts(&ser)
        };
        assert!(!v.has_external_writer(&FieldFacts {
            is_static: true,
            ..base
        }));
        assert!(!v.has_external_writer(&FieldFacts {
            is_const: true,
            ..base
        }));
        assert!(!v.has_external_writer(&FieldFacts {
            is_readonly: true,
            ..base
        }));
        let prop = FieldFacts {
            is_public: true,
            is_property: true,
            ..facts(&[])
        };
        assert!(!v.has_external_writer(&prop));
        assert!(v.has_external_writer(&FieldFacts {
            is_property: true,
            ..base
        }));
        assert!(!EngineVocab::default().has_external_writer(&base));
    }
}
