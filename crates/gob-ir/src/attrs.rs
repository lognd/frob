//! Structured attributes: carried, never checked (universal-model.md 2.2 item 5).

use std::collections::BTreeMap;

/// Attribute keys with a meaning to gob-ir itself; they never enter the Attr facet.
pub mod reserved {
    /// Marks a unit child as belonging to the `sig` facet when set to `"sig"`.
    pub const FACET: &str = "ir.facet";
    /// Opaque qualifier of a unit name, spelled `Name[qualifier]` in a symref.
    pub const QUALIFIER: &str = "ir.qualifier";
    /// Names an opaque region or phase may define: a list of strings, or `"*"`.
    pub const MAY_DEFINE: &str = "ir.may_define";
    /// A boolean: the opaque region may read names of the enclosing scope.
    pub const MAY_READ_SCOPE: &str = "ir.may_read_scope";

    /// A boolean on the root node: the adapter provides unit attributes completely. `false`
    /// makes an absent attribute Unknown rather than No for `attr(...)` selectors (grmb-spec 6.3).
    pub const ATTRS_PROVIDED: &str = "ir.attrs_provided";

    /// True when `key` is reserved for gob-ir.
    pub fn is_reserved(key: &str) -> bool {
        key.starts_with("ir.")
    }
}

/// A structured attribute value.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum AttrValue {
    /// A boolean flag.
    Bool(bool),
    /// A signed integer.
    Int(i64),
    /// A string.
    Str(String),
    /// An ordered list.
    List(Vec<AttrValue>),
    /// A sorted map.
    Map(BTreeMap<String, AttrValue>),
}

impl From<bool> for AttrValue {
    fn from(v: bool) -> Self {
        Self::Bool(v)
    }
}

impl From<i64> for AttrValue {
    fn from(v: i64) -> Self {
        Self::Int(v)
    }
}

impl From<&str> for AttrValue {
    fn from(v: &str) -> Self {
        Self::Str(v.to_owned())
    }
}

impl From<String> for AttrValue {
    fn from(v: String) -> Self {
        Self::Str(v)
    }
}

/// A sorted key-value attribute bag attached to a node.
///
/// ```
/// use gob_ir::{Attributes, AttrValue};
/// let mut a = Attributes::default();
/// a.set("visibility", "pub");
/// assert_eq!(a.get("visibility"), Some(&AttrValue::Str("pub".into())));
/// ```
#[derive(Debug, Clone, Default, PartialEq, Eq, Hash)]
pub struct Attributes {
    map: BTreeMap<String, AttrValue>,
}

impl Attributes {
    /// Set `key`, replacing any previous value.
    pub fn set(&mut self, key: impl Into<String>, value: impl Into<AttrValue>) {
        self.map.insert(key.into(), value.into());
    }

    /// The value of `key`, if present.
    pub fn get(&self, key: &str) -> Option<&AttrValue> {
        self.map.get(key)
    }

    /// String value of `key`, if present and a string.
    pub fn get_str(&self, key: &str) -> Option<&str> {
        match self.map.get(key) {
            Some(AttrValue::Str(s)) => Some(s),
            _ => None,
        }
    }

    /// Iterate entries in key order.
    pub fn iter(&self) -> impl Iterator<Item = (&str, &AttrValue)> {
        self.map.iter().map(|(k, v)| (k.as_str(), v))
    }

    /// Iterate entries that are not reserved for gob-ir.
    pub fn user(&self) -> impl Iterator<Item = (&str, &AttrValue)> {
        self.iter().filter(|(k, _)| !reserved::is_reserved(k))
    }

    /// True when there are no entries.
    pub fn is_empty(&self) -> bool {
        self.map.is_empty()
    }
}
