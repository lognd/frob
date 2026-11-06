//! An insertion-ordered YAML value tree (the workflow rules report jobs in file order).

use std::fmt;

use indexmap::IndexMap;
use serde::de::{Deserialize, Deserializer, MapAccess, SeqAccess, Visitor};
use serde::ser::{Serialize, SerializeMap, SerializeSeq, Serializer};
use serde_json::Number;

/// A parsed YAML node; mappings keep file order and have string keys.
#[derive(Debug, Clone, PartialEq)]
pub(crate) enum Value {
    /// `null`, `~` or an empty value.
    Null,
    /// A boolean scalar.
    Bool(bool),
    /// An integer or float scalar.
    Number(Number),
    /// A string scalar.
    String(String),
    /// A sequence.
    Array(Vec<Value>),
    /// A mapping in file order.
    Object(IndexMap<String, Value>),
}

impl Value {
    /// The string of a string scalar.
    pub(crate) fn as_str(&self) -> Option<&str> {
        match self {
            Self::String(s) => Some(s),
            _ => None,
        }
    }

    /// The entries of a mapping.
    pub(crate) fn as_object(&self) -> Option<&IndexMap<String, Value>> {
        match self {
            Self::Object(m) => Some(m),
            _ => None,
        }
    }

    /// The items of a sequence.
    pub(crate) fn as_array(&self) -> Option<&Vec<Value>> {
        match self {
            Self::Array(v) => Some(v),
            _ => None,
        }
    }

    /// True for a mapping.
    pub(crate) fn is_object(&self) -> bool {
        matches!(self, Self::Object(_))
    }

    /// The value of `key` in a mapping, `None` for a non-mapping or an absent key.
    pub(crate) fn get(&self, key: &str) -> Option<&Value> {
        self.as_object()?.get(key)
    }
}

/// Parse YAML text into a [`Value`]; the error is the parser's message.
pub(crate) fn from_str(text: &str) -> Result<Value, String> {
    serde_saphyr::from_str::<Value>(text).map_err(|e| e.to_string())
}

/// Render a node back to YAML text (empty if it cannot be rendered).
pub(crate) fn to_string(value: &Value) -> String {
    serde_saphyr::to_string(value).unwrap_or_default()
}

impl Serialize for Value {
    fn serialize<S: Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        match self {
            Self::Null => s.serialize_unit(),
            Self::Bool(b) => s.serialize_bool(*b),
            Self::Number(n) => n.serialize(s),
            Self::String(v) => s.serialize_str(v),
            Self::Array(items) => {
                let mut seq = s.serialize_seq(Some(items.len()))?;
                for item in items {
                    seq.serialize_element(item)?;
                }
                seq.end()
            }
            Self::Object(map) => {
                let mut m = s.serialize_map(Some(map.len()))?;
                for (k, v) in map {
                    m.serialize_entry(k, v)?;
                }
                m.end()
            }
        }
    }
}

impl<'de> Deserialize<'de> for Value {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        d.deserialize_any(ValueVisitor)
    }
}

struct ValueVisitor;

impl<'de> Visitor<'de> for ValueVisitor {
    type Value = Value;

    fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("any YAML value")
    }

    fn visit_bool<E>(self, v: bool) -> Result<Value, E> {
        Ok(Value::Bool(v))
    }

    fn visit_i64<E>(self, v: i64) -> Result<Value, E> {
        Ok(Value::Number(v.into()))
    }

    fn visit_u64<E>(self, v: u64) -> Result<Value, E> {
        Ok(Value::Number(v.into()))
    }

    fn visit_f64<E>(self, v: f64) -> Result<Value, E> {
        Ok(Number::from_f64(v).map_or(Value::Null, Value::Number))
    }

    fn visit_str<E>(self, v: &str) -> Result<Value, E> {
        Ok(Value::String(v.to_owned()))
    }

    fn visit_string<E>(self, v: String) -> Result<Value, E> {
        Ok(Value::String(v))
    }

    fn visit_unit<E>(self) -> Result<Value, E> {
        Ok(Value::Null)
    }

    fn visit_none<E>(self) -> Result<Value, E> {
        Ok(Value::Null)
    }

    fn visit_some<D: Deserializer<'de>>(self, d: D) -> Result<Value, D::Error> {
        Value::deserialize(d)
    }

    fn visit_seq<A: SeqAccess<'de>>(self, mut seq: A) -> Result<Value, A::Error> {
        let mut items = Vec::new();
        while let Some(item) = seq.next_element()? {
            items.push(item);
        }
        Ok(Value::Array(items))
    }

    fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Value, A::Error> {
        let mut out = IndexMap::new();
        while let Some((k, v)) = map.next_entry::<String, Value>()? {
            out.insert(k, v);
        }
        Ok(Value::Object(out))
    }
}
