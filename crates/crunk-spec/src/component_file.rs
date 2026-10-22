//! A standalone component spec file (`design/components/<name>.component.toml`): a component's
//! props, variant matrix, states, token bindings, a11y contract and code mapping.

// frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F

use indexmap::IndexMap;
use serde::{Deserialize, Serialize};

use crate::table::{ScreenKind, ScreenStatus};

/// Why a component spec file could not be read as a [`ComponentConfig`].
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum ComponentFileError {
    /// Not valid TOML, or not the component schema.
    #[error("invalid component file: {0}")]
    Parse(String),
}

/// The kind of value a component prop takes.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PropKind {
    /// A true/false switch.
    Bool,
    /// One of a fixed set of `values`.
    Enum,
    /// Free text.
    Text,
    /// A slot holding child content, `min` to `max` children.
    Slot,
    /// A swappable component instance.
    InstanceSwap,
}

/// One component prop.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Prop {
    /// Prop name, unique within the component.
    pub name: String,
    /// The value kind.
    pub kind: PropKind,
    /// The allowed values of an `enum` prop.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub values: Vec<String>,
    /// The default value, one of `values` for an `enum`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub default: Option<String>,
    /// Whether this `enum` prop is a variant axis the `[[variants]]` matrix must cover.
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub axis: bool,
    /// Minimum children of a `slot`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub min: Option<u32>,
    /// Maximum children of a `slot`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub max: Option<u32>,
}

/// One cell of the variant matrix: a value for each axis prop.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Variant {
    /// Axis prop name to chosen value.
    pub axes: IndexMap<String, String>,
}

/// One declared component state.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ComponentState {
    /// State id, unique within the component.
    pub id: String,
}

/// The anatomy: the node ids bindings attach to.
#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Anatomy {
    /// Node ids, the first being the root.
    #[serde(default)]
    pub nodes: Vec<String>,
}

/// A design property of a node bound to a token (or, wrongly, a literal).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Binding {
    /// The anatomy node id.
    pub node: String,
    /// The bound property (`background`, `padding`, ...).
    pub property: String,
    /// The state the binding applies in; absent means every state.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub state: Option<String>,
    /// The token the property takes its value from.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub token: Option<String>,
    /// A literal value; always a finding (COMP004), kept so it can be located.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub value: Option<String>,
}

/// The accessibility contract of a component.
#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct A11yContract {
    /// The ARIA role.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub role: Option<String>,
    /// Where the accessible name comes from (`content`, `label-prop`, ...).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name_source: Option<String>,
    /// Key to behavior.
    #[serde(default, skip_serializing_if = "IndexMap::is_empty")]
    pub keyboard: IndexMap<String, String>,
    /// Minimum pointer target size in CSS pixels.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub min_target: Option<u32>,
}

/// Where a component is implemented in code.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CodeMapping {
    /// The framework (`react`, `swiftui`, ...).
    pub framework: String,
    /// Source path relative to the project root.
    pub path: String,
    /// The exported symbol.
    pub export: String,
    /// The prop names the code exposes; checked against `[[props]]` when present.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub props: Option<Vec<String>>,
}

/// A whole component spec file.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ComponentConfig {
    /// Component name, the root of its node ids.
    pub name: String,
    /// Which STATE coverage families apply.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub kinds: Vec<ScreenKind>,
    /// Lifecycle status; `ready` and `completed` components must carry a matching hash.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub status: Option<ScreenStatus>,
    /// Hash of the content when the status was last set (COMP009).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub content_hash: Option<String>,
    /// The anatomy nodes.
    #[serde(default)]
    pub anatomy: Anatomy,
    /// The props.
    #[serde(default)]
    pub props: Vec<Prop>,
    /// The variant matrix cells.
    #[serde(default)]
    pub variants: Vec<Variant>,
    /// The declared states.
    #[serde(default)]
    pub states: Vec<ComponentState>,
    /// The token bindings.
    #[serde(default)]
    pub bindings: Vec<Binding>,
    /// The accessibility contract.
    #[serde(default)]
    pub a11y: A11yContract,
    /// The code mappings.
    #[serde(default)]
    pub code: Vec<CodeMapping>,
}

impl ComponentConfig {
    /// The node id of `node` within this component (`button/label`).
    #[must_use]
    pub fn node_id(&self, node: &str) -> String {
        format!("{}/{node}", self.name)
    }
}

/// Parse one component spec file's text; semantic checks are the COMP rules' job, so a file that
/// is merely wrong still loads and yields findings.
///
/// # Errors
/// [`ComponentFileError::Parse`] on bad TOML or a schema mismatch.
pub fn parse_component_file(text: &str) -> Result<ComponentConfig, ComponentFileError> {
    let c: ComponentConfig =
        toml_edit::de::from_str(text).map_err(|e| ComponentFileError::Parse(e.to_string()))?;
    tracing::debug!(component = %c.name, props = c.props.len(), "parsed component file");
    Ok(c)
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-spec/src/component_file.rs::parse_component_file
    #[test]
    fn parses_a_full_component() {
        let c = parse_component_file(
            r#"
name = "button"
kinds = ["interactive"]
status = "ready"
[anatomy]
nodes = ["root", "label"]
[[props]]
name = "size"
kind = "enum"
values = ["sm", "lg"]
default = "sm"
axis = true
[[variants]]
axes = { size = "sm" }
[[states]]
id = "default"
[[bindings]]
node = "label"
property = "color"
token = "color.fg"
[a11y]
role = "button"
keyboard = { Enter = "activate" }
min_target = 44
[[code]]
framework = "react"
path = "src/Button.tsx"
export = "Button"
props = ["size"]
"#,
        )
        .expect("parses");
        assert_eq!(c.name, "button");
        assert_eq!(c.props[0].kind, PropKind::Enum);
        assert_eq!(c.variants[0].axes["size"], "sm");
        assert_eq!(c.a11y.min_target, Some(44));
        assert_eq!(c.node_id("label"), "button/label");
    }

    // frob:tests crates/crunk-spec/src/component_file.rs::parse_component_file
    #[test]
    fn minimal_component_needs_only_a_name() {
        let c = parse_component_file("name = \"chip\"\n").expect("parses");
        assert!(c.props.is_empty() && c.code.is_empty());
    }

    // frob:tests crates/crunk-spec/src/component_file.rs::parse_component_file
    #[test]
    fn rejects_bad_toml_missing_name_and_unknown_keys() {
        assert!(parse_component_file("name = ").is_err());
        assert!(parse_component_file("kinds = []\n").is_err());
        assert!(parse_component_file("name = \"a\"\nbogus = 1\n").is_err());
        assert!(
            parse_component_file("name = \"a\"\n[[props]]\nname = \"p\"\nkind = \"nope\"\n")
                .is_err()
        );
        assert!(parse_component_file("").is_err());
    }

    // frob:tests crates/crunk-spec/src/component_file.rs::parse_component_file
    #[test]
    fn unicode_names_and_duplicates_load() {
        let c = parse_component_file(
            "name = \"bouton-\u{e9}\"\n[[states]]\nid = \"a\"\n[[states]]\nid = \"a\"\n",
        )
        .expect("parses");
        assert_eq!(c.states.len(), 2);
        assert_eq!(c.node_id("x"), "bouton-\u{e9}/x");
    }
}
