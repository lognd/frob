//! Row types the queries return; every one serializes straight into a verb's `data`.

// frob:ticket 01M43ATCZXK3B3952GGEBT1ASJ

use schemars::JsonSchema;
use serde::Serialize;

/// A file and 1-based line, relative to the project root.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize, JsonSchema)]
pub struct Site {
    /// Path relative to the project root, `/`-separated.
    pub path: String,
    /// 1-based line.
    pub line: u32,
}

/// How a `find` query matched a name.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum MatchKind {
    /// The whole name equals the query.
    Exact,
    /// The name starts with the query.
    Prefix,
    /// The query appears inside the name.
    Substring,
}

/// What a `find` hit names.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum NameKind {
    /// A design token.
    Token,
    /// A CSS class selector.
    Class,
}

/// One `find` hit.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct FindRow {
    /// Token name (with `--`) or class name (without `.`).
    pub name: String,
    /// Token or class.
    pub kind: NameKind,
    /// How the query matched.
    #[serde(rename = "match")]
    pub matched: MatchKind,
    /// Use count: `var()` references plus utility uses (tokens), utility uses (classes).
    pub uses: usize,
}

/// One BEM element of a component and its modifiers.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct ElementRow {
    /// Element name (the part after `__`).
    pub name: String,
    /// Modifiers on the element (the parts after `--`).
    pub modifiers: Vec<String>,
}

/// One component: its sheet and BEM structure.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct ComponentRow {
    /// Component (block) name.
    pub name: String,
    /// Sheets that define it, relative to the project root.
    pub paths: Vec<String>,
    /// Modifiers on the block itself.
    pub modifiers: Vec<String>,
    /// Elements, sorted by name.
    pub elements: Vec<ElementRow>,
    /// Declarations across the component's sheets.
    pub declarations: usize,
}

/// A pair of sheets that repeat the same declarations.
#[derive(Debug, Clone, PartialEq, Serialize, JsonSchema)]
pub struct DupeRow {
    /// First sheet (sorts before `b`).
    pub a: String,
    /// Second sheet.
    pub b: String,
    /// Shared `(property, value)` pairs over the smaller sheet's pair count, 2 decimals.
    pub score: f64,
    /// Number of shared pairs.
    pub shared: usize,
}

/// A token nothing references.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct UnusedRow {
    /// Token name with `--`.
    pub name: String,
}

/// One palette color and its distance to the query color.
#[derive(Debug, Clone, PartialEq, Serialize, JsonSchema)]
pub struct ColorRow {
    /// Palette key (the token name without `--`).
    pub name: String,
    /// The palette value as written.
    pub value: String,
    /// Redmean distance to the query color, 2 decimals.
    pub distance: f64,
    /// True when color and alpha are identical.
    pub exact: bool,
    /// True when only the alpha differs.
    pub alpha_variant: bool,
}

/// One entry of the `map` inventory.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct MapEntry {
    /// Path relative to the project root.
    pub path: String,
    /// The owning component, when the sheet is one.
    pub component: Option<String>,
    /// Class selectors defined (CSS sheets).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub classes: Option<usize>,
    /// Declarations parsed (JSX sources).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub declarations: Option<usize>,
    /// Tailwind utilities used (JSX sources).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub utilities: Option<usize>,
}

/// The project inventory: every bucket's files plus the strays.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct MapData {
    /// `(bucket, entries)` in the canonical bucket order.
    pub buckets: indexed::Buckets,
    /// Sheets that sit in no bucket.
    pub strays: Vec<String>,
}

/// One token and everything that touches it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct ExplainRow {
    /// Token name with `--`.
    pub name: String,
    /// The token's value as CSS, when it has one.
    pub value: Option<String>,
    /// Token family in kebab case.
    pub group: String,
    /// The generated tokens file that defines it, when known.
    pub defined_in: Option<String>,
    /// `var()` reference sites.
    pub sites: Vec<Site>,
    /// Tailwind utilities that resolve to it, as written.
    pub utilities: Vec<String>,
}

/// Ordered bucket map so JSON keeps the canonical bucket order.
pub mod indexed {
    use std::collections::BTreeMap;

    use schemars::JsonSchema;
    use serde::ser::{Serialize, SerializeMap, Serializer};

    use super::MapEntry;

    /// Bucket name to entries, serialized in insertion order.
    #[derive(Debug, Clone, PartialEq, Eq, Default)]
    pub struct Buckets(pub Vec<(String, Vec<MapEntry>)>);

    impl Serialize for Buckets {
        fn serialize<S: Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
            let mut map = s.serialize_map(Some(self.0.len()))?;
            for (name, entries) in &self.0 {
                map.serialize_entry(name, entries)?;
            }
            map.end()
        }
    }

    impl JsonSchema for Buckets {
        fn schema_name() -> std::borrow::Cow<'static, str> {
            "Buckets".into()
        }

        fn json_schema(generator: &mut schemars::SchemaGenerator) -> schemars::Schema {
            <BTreeMap<String, Vec<MapEntry>>>::json_schema(generator)
        }
    }
}
