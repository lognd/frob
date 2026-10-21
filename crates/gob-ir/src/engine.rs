//! Engine entry-point vocabulary: the names an engine calls itself, so no caller exists in the repository.
//!
//! A pack (the built-in `unity` pack) supplies the vocabulary; reach and coverage rules ask it
//! whether a method is called by the engine and so counts as a root, and effect and flow rules ask
//! whether a field is written from outside the code (the editor serializer) so a never-assigned
//! report does not fire for it.

// frob:ticket 01M44YQXS4BXE0X07FBYR0STJ5
// frob:ticket 01M44YQY6KR3NCCNGKJ9QK3N9A
// frob:ticket 01M44YQYKX1PTSGQE3TMVX4GEN

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
/// Vocabulary class of bare method names that call another method by name (`SendMessage`, `Invoke`).
pub const CLASS_DYNAMIC_CALL: &str = "dynamic.call";
/// Vocabulary class of `Type.Method` string-keyed lookups (`GameObject.Find`, `Resources.Load`).
pub const CLASS_DYNAMIC_LOOKUP: &str = "dynamic.lookup";

/// What the first argument of a call is, as far as the syntax shows.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NameArg {
    /// A plain string literal.
    Literal,
    /// Any other expression (a variable, an interpolation, a concatenation).
    Computed,
    /// The call has no arguments.
    Absent,
}

/// Which kind of dynamic call a call is.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DynamicKind {
    /// A method chosen by name at run time (`Invoke("Reload")`).
    MethodByName,
    /// An object or asset chosen by string key at run time (`GameObject.Find("Hero")`).
    LookupByKey,
}

/// A call the engine resolves by name at run time: an Unresolved call edge, never a guessed one.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DynamicCall {
    /// Method-by-name or string-keyed lookup.
    pub kind: DynamicKind,
    /// True when the name is spelled as a literal at the call site.
    pub literal: bool,
}

impl DynamicCall {
    /// The reason an edge for this call is Unresolved, named for the report.
    pub fn reason(self) -> &'static str {
        match (self.kind, self.literal) {
            (DynamicKind::MethodByName, true) => {
                "dynamic call: the engine resolves a literal method name at run time"
            }
            (DynamicKind::MethodByName, false) => {
                "dynamic call: the engine resolves a computed method name at run time"
            }
            (DynamicKind::LookupByKey, true) => {
                "dynamic lookup: the engine resolves a literal string key at run time"
            }
            (DynamicKind::LookupByKey, false) => {
                "dynamic lookup: the engine resolves a computed string key at run time"
            }
        }
    }
}

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
    /// Bare method names that call another method by name (`SendMessage`, `Invoke`).
    pub dynamic_calls: BTreeSet<String>,
    /// `Type.Method` string-keyed lookups (`GameObject.Find`).
    pub dynamic_lookups: BTreeSet<String>,
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
            CLASS_DYNAMIC_CALL => &mut self.dynamic_calls,
            CLASS_DYNAMIC_LOOKUP => &mut self.dynamic_lookups,
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
            !self.is_empty() && f.is_public && !f.is_property && f.owner_is_engine
        };
        tracing::trace!(external, ?f, "field external-writer decision");
        external
    }

    /// Classifies a call as dynamic, or `None` when it is an ordinary call (the empty vocabulary never classifies).
    ///
    /// `qualifier` is the type written before the method (`GameObject` in `GameObject.Find("x")`);
    /// `own_receiver` is true for an unqualified call or one on `this`. A method-by-name call needs a
    /// string literal first argument, or a computed one on an own receiver (a computed argument on another
    /// receiver may be an ordinary delegate `Invoke`). A lookup is dynamic whenever it has an argument.
    pub fn classify_call(
        &self,
        qualifier: Option<&str>,
        callee: &str,
        arg: NameArg,
        own_receiver: bool,
    ) -> Option<DynamicCall> {
        let found = match arg {
            NameArg::Absent => None,
            _ if qualifier
                .is_some_and(|q| self.dynamic_lookups.contains(&format!("{q}.{callee}"))) =>
            {
                Some(DynamicKind::LookupByKey)
            }
            NameArg::Literal if self.dynamic_calls.contains(callee) => {
                Some(DynamicKind::MethodByName)
            }
            NameArg::Computed if own_receiver && self.dynamic_calls.contains(callee) => {
                Some(DynamicKind::MethodByName)
            }
            _ => None,
        };
        let call = found.map(|kind| DynamicCall {
            kind,
            literal: arg == NameArg::Literal,
        });
        tracing::trace!(callee, ?arg, ?call, "dynamic call decision");
        call
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

    fn dynamic_vocab() -> EngineVocab {
        let mut v = EngineVocab::default();
        assert!(v.add_class(CLASS_DYNAMIC_CALL, ["Invoke".to_owned()]));
        assert!(v.add_class(CLASS_DYNAMIC_LOOKUP, ["GameObject.Find".to_owned()]));
        v
    }

    // frob:tests EngineVocab.classify_call
    #[test]
    fn classify_call_separates_dynamic_from_ordinary_calls() {
        let v = dynamic_vocab();
        let lit = v.classify_call(None, "Invoke", NameArg::Literal, true);
        assert_eq!(lit.map(|c| c.kind), Some(DynamicKind::MethodByName));
        assert!(lit.is_some_and(|c| c.literal));
        assert_eq!(
            v.classify_call(None, "Reload", NameArg::Literal, true),
            None
        );
        assert_eq!(v.classify_call(None, "Invoke", NameArg::Absent, true), None);
        assert_eq!(
            v.classify_call(Some("d"), "Invoke", NameArg::Computed, false),
            None
        );
        let computed = v.classify_call(None, "Invoke", NameArg::Computed, true);
        assert!(computed.is_some_and(|c| !c.literal));
        let find = v.classify_call(Some("GameObject"), "Find", NameArg::Computed, false);
        assert_eq!(find.map(|c| c.kind), Some(DynamicKind::LookupByKey));
        assert_eq!(
            v.classify_call(Some("list"), "Find", NameArg::Literal, false),
            None
        );
        let empty = EngineVocab::default();
        assert_eq!(
            empty.classify_call(None, "Invoke", NameArg::Literal, true),
            None
        );
    }

    // frob:tests DynamicCall.reason
    #[test]
    fn every_dynamic_reason_is_named() {
        for kind in [DynamicKind::MethodByName, DynamicKind::LookupByKey] {
            for literal in [true, false] {
                assert!(
                    DynamicCall { kind, literal }
                        .reason()
                        .starts_with("dynamic ")
                );
            }
        }
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
