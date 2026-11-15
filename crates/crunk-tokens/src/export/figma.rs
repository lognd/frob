//! The Figma variables exporter: a JSON document shaped for the Figma variables REST API.
//!
//! Collections are the token tiers, modes are the token modes (every collection has the
//! `default` mode plus the modes its tokens override), variables are the tokens. A token with no
//! Figma variable type (channel companions, easings, composites) and an alias that is cyclic,
//! dangling or points at such a token are skipped with a named [`FigmaWarning`], never a panic.
//! [`plan_overruns`] is the plan-limit check (modes and variables per collection).

// frob:ticket 01M5XCVZFESE41V1GVEYC5VP5X

use std::collections::BTreeMap;
use std::fmt;
use std::path::PathBuf;

use crunk_spec::DesignSpec;
use crunk_spec::table::FigmaConfig;
use serde_json::{Map, Value, json};

use super::{Comparison, Exporter, Target};
use crate::model::{Scope, Tier, Token, TokenSet, TokenValue};

/// The name of the mode every collection has (a token's default value).
pub const DEFAULT_MODE: &str = "default";

/// Why a token was left out of the Figma variables document.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WarningKind {
    /// The alias chain is cyclic or ends at an unknown token.
    AliasCycle,
    /// The token (or its alias target) has no Figma variable type.
    NoFigmaType,
}

impl WarningKind {
    /// The stable name logged and shown for this warning.
    pub fn name(self) -> &'static str {
        match self {
            Self::AliasCycle => "figma-alias-cycle",
            Self::NoFigmaType => "figma-no-type",
        }
    }
}

/// A token skipped by the Figma export, named by [`WarningKind`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FigmaWarning {
    /// The skipped token's custom property name.
    pub token: String,
    /// Why it was skipped.
    pub kind: WarningKind,
}

impl fmt::Display for FigmaWarning {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let why = match self.kind {
            WarningKind::AliasCycle => "its alias chain is cyclic or dangling",
            WarningKind::NoFigmaType => "it has no Figma variable type",
        };
        write!(
            f,
            "{}: skipped `{}` because {why}",
            self.kind.name(),
            self.token
        )
    }
}

/// The Figma variables document for `tokens` and the warnings for what it left out.
#[derive(Debug, Clone, PartialEq)]
pub struct FigmaExport {
    /// The deterministic JSON document.
    pub document: Value,
    /// Skipped tokens, in token order.
    pub warnings: Vec<FigmaWarning>,
}

/// One collection's size, the quantity the plan limits bound.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CollectionSize {
    /// The collection name (the tier).
    pub collection: &'static str,
    /// Modes, counting the default mode.
    pub modes: usize,
    /// Variables the collection would hold.
    pub variables: usize,
}

/// A collection that exceeds a plan limit.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PlanOverrun {
    /// The collection name.
    pub collection: &'static str,
    /// `modes` or `variables`.
    pub what: &'static str,
    /// How many the collection has.
    pub count: usize,
    /// How many the plan allows.
    pub limit: usize,
    /// The plan name, or `custom` when only an override limit is configured.
    pub plan: String,
}

impl fmt::Display for PlanOverrun {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "Figma collection `{}` has {} {} but the `{}` plan allows {}",
            self.collection, self.count, self.what, self.plan, self.limit
        )
    }
}

fn tier_name(tier: Tier) -> &'static str {
    match tier {
        Tier::Primitive => "primitive",
        Tier::Semantic => "semantic",
        Tier::Component => "component",
    }
}

fn figma_type(value: &TokenValue) -> Option<&'static str> {
    match value {
        TokenValue::Color(_) => Some("COLOR"),
        TokenValue::Dimension { .. }
        | TokenValue::Number(_)
        | TokenValue::Float(_)
        | TokenValue::Duration(_) => Some("FLOAT"),
        TokenValue::Text(_) | TokenValue::FontFamily(_) => Some("STRING"),
        TokenValue::Channels { .. }
        | TokenValue::CubicBezier(_)
        | TokenValue::Composite(_)
        | TokenValue::Alias(_) => None,
    }
}

#[allow(clippy::cast_precision_loss, reason = "z-indexes are small")]
fn figma_value(value: &TokenValue) -> Value {
    match value {
        TokenValue::Color(c) => json!({"r": c.r, "g": c.g, "b": c.b, "a": c.a}),
        TokenValue::Dimension { value, .. }
        | TokenValue::Float(value)
        | TokenValue::Duration(value) => {
            json!(value)
        }
        TokenValue::Number(n) => json!(*n as f64),
        TokenValue::Text(t) => json!(t),
        TokenValue::FontFamily(names) => json!(names.join(", ")),
        _ => Value::Null,
    }
}

fn variable_id(name: &str) -> String {
    format!("variable:{}", name.trim_start_matches("--"))
}

/// The Figma variable path of `name` (`--color-ink` is `color/ink`).
fn variable_name(name: &str) -> String {
    let bare = name.trim_start_matches("--");
    bare.split_once('-')
        .map_or_else(|| bare.to_owned(), |(g, rest)| format!("{g}/{rest}"))
}

fn scopes(token: &Token) -> Vec<&'static str> {
    if token.scopes.is_empty() {
        return vec!["ALL_SCOPES"];
    }
    let mut out: Vec<&'static str> = Vec::new();
    for scope in &token.scopes {
        let mapped: &[&'static str] = match scope {
            Scope::Color => &["ALL_FILLS", "STROKE_COLOR", "EFFECT_COLOR"],
            Scope::Spacing => &["GAP"],
            Scope::FontSize => &["FONT_SIZE"],
            Scope::Radius => &["CORNER_RADIUS"],
            Scope::Size => &["WIDTH_HEIGHT"],
            Scope::FontFamily => &["FONT_FAMILY"],
            Scope::ZIndex => &[],
        };
        for s in mapped {
            if !out.contains(s) {
                out.push(s);
            }
        }
    }
    out.sort_unstable();
    if out.is_empty() {
        out.push("ALL_SCOPES");
    }
    out
}

/// The Figma type of `token`, resolving an alias; or the reason it has none.
fn token_type(token: &Token, tokens: &TokenSet) -> Result<&'static str, WarningKind> {
    match &token.value {
        TokenValue::Alias(_) => match tokens.resolve(&token.name, None) {
            None => Err(WarningKind::AliasCycle),
            Some(v) => figma_type(v).ok_or(WarningKind::NoFigmaType),
        },
        v => figma_type(v).ok_or(WarningKind::NoFigmaType),
    }
}

/// The Figma value of `value` in a mode of a variable typed `ty`, or `None` to leave the mode out.
fn mode_value(value: &TokenValue, ty: &str, tokens: &TokenSet) -> Option<Value> {
    if let TokenValue::Alias(target) = value {
        let t = tokens.get(target)?;
        let resolved = tokens.resolve(target, None)?;
        return (figma_type(resolved) == Some(ty))
            .then(|| json!({"type": "VARIABLE_ALIAS", "id": variable_id(&t.name)}));
    }
    (figma_type(value) == Some(ty)).then(|| figma_value(value))
}

/// The modes each collection holds (default first, then first-seen order), per tier name.
fn collection_modes(tokens: &TokenSet) -> BTreeMap<&'static str, Vec<String>> {
    let mut map: BTreeMap<&'static str, Vec<String>> = BTreeMap::new();
    for token in tokens.iter() {
        let modes = map
            .entry(tier_name(token.tier))
            .or_insert_with(|| vec![DEFAULT_MODE.to_owned()]);
        for mode in token.modes.keys() {
            if !modes.contains(mode) {
                modes.push(mode.clone());
            }
        }
    }
    map
}

/// The Figma variables document for `tokens`, with a warning per skipped token.
pub fn export(tokens: &TokenSet) -> FigmaExport {
    let mut warnings = Vec::new();
    let mut by_collection: BTreeMap<&'static str, Vec<Value>> = BTreeMap::new();
    let mut counts: BTreeMap<&'static str, usize> = BTreeMap::new();
    for token in tokens.iter() {
        let ty = match token_type(token, tokens) {
            Ok(ty) => ty,
            Err(kind) => {
                let w = FigmaWarning {
                    token: token.name.clone(),
                    kind,
                };
                tracing::warn!(token = %w.token, warning = kind.name(), "figma export skips a token");
                warnings.push(w);
                continue;
            }
        };
        let collection = tier_name(token.tier);
        let mut values = Map::new();
        if let Some(v) = mode_value(&token.value, ty, tokens) {
            values.insert(format!("mode:{DEFAULT_MODE}"), v);
        }
        for (mode, value) in &token.modes {
            if let Some(v) = mode_value(value, ty, tokens) {
                values.insert(format!("mode:{mode}"), v);
            } else {
                tracing::debug!(token = %token.name, mode, "figma mode value skipped");
            }
        }
        *counts.entry(collection).or_default() += 1;
        by_collection.entry(collection).or_default().push(json!({
            "id": variable_id(&token.name),
            "name": variable_name(&token.name),
            "variableCollectionId": format!("collection:{collection}"),
            "resolvedType": ty,
            "description": token.description.clone().unwrap_or_default(),
            "scopes": scopes(token),
            "valuesByMode": Value::Object(values),
        }));
    }
    let modes = collection_modes(tokens);
    let collections: Vec<Value> = by_collection
        .keys()
        .map(|c| {
            let list: Vec<Value> = modes
                .get(c)
                .map(|ms| {
                    ms.iter()
                        .map(|m| json!({"modeId": format!("mode:{m}"), "name": m}))
                        .collect()
                })
                .unwrap_or_default();
            json!({
                "id": format!("collection:{c}"),
                "name": c,
                "defaultModeId": format!("mode:{DEFAULT_MODE}"),
                "modes": list,
            })
        })
        .collect();
    let variables: Vec<Value> = by_collection.into_values().flatten().collect();
    FigmaExport {
        document: json!({"variableCollections": collections, "variables": variables}),
        warnings,
    }
}

/// The size of every collection of `tokens` (only tokens with a Figma type count).
pub fn collection_sizes(tokens: &TokenSet) -> Vec<CollectionSize> {
    let modes = collection_modes(tokens);
    let mut counts: BTreeMap<&'static str, usize> = BTreeMap::new();
    for token in tokens.iter().filter(|t| token_type(t, tokens).is_ok()) {
        *counts.entry(tier_name(token.tier)).or_default() += 1;
    }
    counts
        .into_iter()
        .map(|(collection, variables)| CollectionSize {
            collection,
            modes: modes.get(collection).map_or(1, Vec::len),
            variables,
        })
        .collect()
}

/// Every collection of `tokens` that exceeds the limits `config` sets (empty when within them).
pub fn plan_overruns(config: &FigmaConfig, tokens: &TokenSet) -> Vec<PlanOverrun> {
    let plan = config.plan.clone().unwrap_or_else(|| "custom".to_owned());
    let mode_limit = config.modes_limit().map(|n| n as usize);
    let var_limit = config.variables_limit() as usize;
    let mut out = Vec::new();
    for size in collection_sizes(tokens) {
        if let Some(limit) = mode_limit.filter(|l| size.modes > *l) {
            out.push(PlanOverrun {
                collection: size.collection,
                what: "modes",
                count: size.modes,
                limit,
                plan: plan.clone(),
            });
        }
        if size.variables > var_limit {
            out.push(PlanOverrun {
                collection: size.collection,
                what: "variables",
                count: size.variables,
                limit: var_limit,
                plan: plan.clone(),
            });
        }
    }
    out
}

/// Renders the Figma variables JSON.
#[derive(Debug, Clone, Copy, Default)]
pub struct FigmaExporter;

impl Exporter for FigmaExporter {
    fn target(&self) -> Target {
        Target::FigmaVariables
    }

    /// The pretty-printed variables document with a trailing newline.
    fn render(&self, _spec: &DesignSpec, tokens: &TokenSet) -> String {
        let mut text = serde_json::to_string_pretty(&export(tokens).document).unwrap_or_default();
        text.push('\n');
        text
    }

    fn path(&self, _spec: &DesignSpec) -> Option<PathBuf> {
        None
    }

    fn comparison(&self) -> Comparison {
        Comparison::Json
    }
}

#[cfg(test)]
mod tests {
    use indexmap::IndexMap;

    use super::*;
    use crate::model::Unit;
    use crunk_values::Color;

    fn tok(name: &str, value: TokenValue, modes: &[(&str, TokenValue)]) -> Token {
        Token {
            name: name.to_owned(),
            kind: crate::model::TokenKind::Custom,
            key: name.trim_start_matches("--").to_owned(),
            origin: "test".to_owned(),
            tier: Tier::Primitive,
            value,
            modes: modes
                .iter()
                .map(|(k, v)| ((*k).to_owned(), v.clone()))
                .collect::<IndexMap<_, _>>(),
            scopes: vec![],
            description: None,
            deprecated: None,
        }
    }

    fn dim(v: f64) -> TokenValue {
        TokenValue::Dimension {
            value: v,
            unit: Unit::Px,
        }
    }

    fn set(tokens: Vec<Token>) -> TokenSet {
        TokenSet::from_tokens(tokens).unwrap()
    }

    // frob:tests crates/crunk-tokens/src/export/figma.rs::plan_overruns
    #[test]
    fn five_modes_on_a_four_mode_plan_names_plan_and_limit() {
        let t = set(vec![tok(
            "--space-1",
            dim(1.0),
            &[
                ("a", dim(2.0)),
                ("b", dim(3.0)),
                ("c", dim(4.0)),
                ("d", dim(5.0)),
            ],
        )]);
        let cfg = FigmaConfig {
            plan: Some("professional".into()),
            max_modes: Some(4),
            max_variables: None,
        };
        let found = plan_overruns(&cfg, &t);
        assert_eq!(found.len(), 1);
        let msg = found[0].to_string();
        assert!(
            msg.contains("professional") && msg.contains("allows 4") && msg.contains("5 modes"),
            "{msg}"
        );
        let ok = FigmaConfig {
            plan: Some("professional".into()),
            max_modes: None,
            max_variables: None,
        };
        assert!(plan_overruns(&ok, &t).is_empty());
    }

    // frob:tests crates/crunk-tokens/src/export/figma.rs::export
    #[test]
    fn export_is_byte_identical_on_two_runs() {
        let build = || {
            set(vec![
                tok("--space-1", dim(4.0), &[("dark", dim(8.0))]),
                tok(
                    "--color-ink",
                    TokenValue::Color(Color {
                        r: 0.0,
                        g: 0.0,
                        b: 0.0,
                        a: 1.0,
                    }),
                    &[],
                ),
                tok("--space-alias", TokenValue::Alias("--space-1".into()), &[]),
            ])
        };
        let a = serde_json::to_string_pretty(&export(&build()).document).unwrap();
        let b = serde_json::to_string_pretty(&export(&build()).document).unwrap();
        assert_eq!(a, b);
        assert!(a.contains("VARIABLE_ALIAS") && a.contains("space/1") && a.contains("mode:dark"));
    }

    // frob:tests crates/crunk-tokens/src/export/figma.rs::variable_id
    // frob:tests crates/crunk-tokens/src/export/figma.rs::variable_name
    // frob:tests crates/crunk-tokens/src/export/figma.rs::scopes
    // frob:tests crates/crunk-tokens/src/export/figma.rs::WarningKind.name
    #[test]
    fn variable_helpers_and_warning_names_are_stable() {
        assert_eq!(variable_id("--color-ink"), "variable:color-ink");
        assert_eq!(variable_name("--color-ink"), "color/ink");
        assert_eq!(variable_name("--solo"), "solo");
        assert_eq!(scopes(&tok("--a-b", dim(1.0), &[])), vec!["ALL_SCOPES"]);
        assert_eq!(WarningKind::AliasCycle.name(), "figma-alias-cycle");
        assert_eq!(WarningKind::NoFigmaType.name(), "figma-no-type");
    }

    // frob:tests crates/crunk-tokens/src/export/figma.rs::export
    #[test]
    fn cycles_and_untyped_tokens_are_skipped_with_named_warnings() {
        let t = set(vec![
            tok("--a-x", TokenValue::Alias("--a-y".into()), &[]),
            tok("--a-y", TokenValue::Alias("--a-x".into()), &[]),
            tok(
                "--ease-out",
                TokenValue::CubicBezier([0.0, 0.0, 1.0, 1.0]),
                &[],
            ),
            tok("--space-1", dim(1.0), &[]),
        ]);
        let out = export(&t);
        let kinds: Vec<(&str, WarningKind)> = out
            .warnings
            .iter()
            .map(|w| (w.token.as_str(), w.kind))
            .collect();
        assert_eq!(
            kinds,
            vec![
                ("--a-x", WarningKind::AliasCycle),
                ("--a-y", WarningKind::AliasCycle),
                ("--ease-out", WarningKind::NoFigmaType),
            ]
        );
        assert_eq!(out.document["variables"].as_array().unwrap().len(), 1);
        assert!(out.warnings[0].to_string().starts_with("figma-alias-cycle"));
    }
}
