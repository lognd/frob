//! An order-preserving untyped TOML value, for the tables whose keys are user data.
//!
//! `[palette]` names, `[lint]` rule ids and `[[session]]` payloads cannot be a fixed struct;
//! they deserialize into [`Dyn`] and are validated by hand with located errors.

// frob:ticket 01M43ARX764095Q4VWABWXXV5H

use std::fmt;

use indexmap::IndexMap;
use schemars::{JsonSchema, Schema, SchemaGenerator, json_schema};
use serde::de::{self, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Deserializer, Serialize};

/// A TOML value of any shape; tables keep their declaration order.
#[derive(Debug, Clone, PartialEq, Serialize)]
#[serde(untagged)]
pub enum Dyn {
    /// A boolean.
    Bool(bool),
    /// An integer.
    Int(i64),
    /// A float.
    Float(f64),
    /// A string.
    Str(String),
    /// An array.
    Array(Vec<Dyn>),
    /// A table, in declaration order.
    Table(IndexMap<String, Dyn>),
}

impl Dyn {
    /// The TOML type name, for error messages.
    pub const fn type_name(&self) -> &'static str {
        match self {
            Self::Bool(_) => "a boolean",
            Self::Int(_) => "an integer",
            Self::Float(_) => "a float",
            Self::Str(_) => "a string",
            Self::Array(_) => "an array",
            Self::Table(_) => "a table",
        }
    }

    /// The value as a float when it is a number (an integer widens); booleans are not numbers.
    #[allow(
        clippy::cast_precision_loss,
        reason = "TOML integers in a design spec are small"
    )]
    pub const fn as_number(&self) -> Option<f64> {
        match self {
            Self::Int(i) => Some(*i as f64),
            Self::Float(f) => Some(*f),
            _ => None,
        }
    }
}

impl JsonSchema for Dyn {
    fn schema_name() -> std::borrow::Cow<'static, str> {
        "Dyn".into()
    }

    fn json_schema(_: &mut SchemaGenerator) -> Schema {
        json_schema!(true)
    }

    fn inline_schema() -> bool {
        true
    }
}

impl<'de> Deserialize<'de> for Dyn {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        struct DynVisitor;

        impl<'de> Visitor<'de> for DynVisitor {
            type Value = Dyn;

            fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                f.write_str("a TOML value")
            }

            fn visit_bool<E>(self, v: bool) -> Result<Dyn, E> {
                Ok(Dyn::Bool(v))
            }

            fn visit_i64<E>(self, v: i64) -> Result<Dyn, E> {
                Ok(Dyn::Int(v))
            }

            fn visit_u64<E: de::Error>(self, v: u64) -> Result<Dyn, E> {
                i64::try_from(v)
                    .map(Dyn::Int)
                    .map_err(|_| E::custom("integer out of range"))
            }

            fn visit_f64<E>(self, v: f64) -> Result<Dyn, E> {
                Ok(Dyn::Float(v))
            }

            fn visit_str<E>(self, v: &str) -> Result<Dyn, E> {
                Ok(Dyn::Str(v.to_owned()))
            }

            fn visit_seq<A: SeqAccess<'de>>(self, mut seq: A) -> Result<Dyn, A::Error> {
                let mut items = Vec::new();
                while let Some(item) = seq.next_element()? {
                    items.push(item);
                }
                Ok(Dyn::Array(items))
            }

            fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Dyn, A::Error> {
                let mut table = IndexMap::new();
                while let Some((key, value)) = map.next_entry::<String, Dyn>()? {
                    table.insert(key, value);
                }
                Ok(Dyn::Table(table))
            }
        }

        deserializer.deserialize_any(DynVisitor)
    }
}
