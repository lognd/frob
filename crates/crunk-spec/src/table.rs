//! The TOML-shaped tables of `crunk.toml`: one struct per fixed-key table.
//!
//! These types are the single source of the file format. They deserialize the file (unknown
//! keys are rejected), are reused unchanged inside [`crate::DesignSpec`] where no resolution is
//! needed, and their doc comments and defaults become `docs/schemas/crunk.json` and
//! `docs/crunk/config.md`. Cross-field rules (ascending scales, dangling references) live in
//! the `validate` module so every failure can carry a location.

// frob:ticket 01M43ARX764095Q4VWABWXXV5H

use indexmap::IndexMap;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::dynamic::Dyn;

fn yes() -> bool {
    true
}

/// The `[project]` table: where managed CSS and generated tokens live.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ProjectConfig {
    /// Directory of the managed CSS, relative to the project root.
    pub css_root: String,
    /// The generated tokens file, relative to `css_root`. This is the one `*_file` key that
    /// resolves against `css_root`; every other `*_file` key resolves against the project root.
    pub tokens_file: String,
    /// Pixels per `rem`, used to compare `rem` lengths against the px scales.
    pub root_font_size: f64,
}

/// The `[scales]` table: strictly ascending px step lists.
///
/// `spacing` and `font_sizes` are required and non-empty. `radii` and `sizes` are optional:
/// empty `radii` keeps RADIUS001 silent and empty `sizes` makes SIZE001 fall back to `spacing`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ScalesConfig {
    /// Allowed spacing steps in px, strictly ascending.
    pub spacing: Vec<f64>,
    /// Allowed font sizes in px, strictly ascending.
    pub font_sizes: Vec<f64>,
    /// Allowed border radii in px, strictly ascending; empty means no radius tokens.
    #[serde(default)]
    pub radii: Vec<f64>,
    /// Allowed sizes (width and height) in px, strictly ascending; empty means use `spacing`.
    #[serde(default)]
    pub sizes: Vec<f64>,
}

/// The `[typography]` table: allowed font families and weights, and named stacks.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct TypographyConfig {
    /// Allowed font family names, at least one.
    pub families: Vec<String>,
    /// Allowed font weights, at least one.
    pub weights: Vec<i64>,
    /// Named font stacks: name to an ordered list of members, each of which must be one of
    /// `families` (compared case-insensitively).
    #[serde(default)]
    pub stacks: IndexMap<String, Vec<String>>,
}

/// Class-name casing enforced by ORG rules.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum ClassCase {
    /// `my-class`.
    #[default]
    Kebab,
    /// `my_class`.
    Snake,
    /// `myClass`.
    Camel,
}

/// How style files are organized.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize, JsonSchema)]
pub enum OrgModel {
    /// Files live in the declared buckets.
    #[default]
    #[serde(rename = "buckets")]
    Buckets,
    /// Utility-first (Tailwind style) organization.
    #[serde(rename = "utility-first")]
    UtilityFirst,
}

/// The `[org]` table: file and class organization rules (ORG001 to ORG005).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct OrgConfig {
    /// Allowed bucket directory names under `css_root`, at least one.
    pub buckets: Vec<String>,
    /// Required class-name casing.
    #[serde(default)]
    pub class_case: ClassCase,
    /// Whether component classes must carry the component name as a prefix.
    #[serde(default = "yes")]
    pub component_prefix: bool,
    /// Whether custom properties may only be defined in the tokens file.
    #[serde(default = "yes")]
    pub tokens_only_custom_props: bool,
    /// File organization model.
    #[serde(default)]
    pub model: OrgModel,
    /// Root-relative globs the ORG rules skip.
    #[serde(default)]
    pub ignore: Vec<String>,
    /// Root-relative entry stylesheet globs.
    #[serde(default)]
    pub entry: Vec<String>,
}

/// The `[jsx]` table: sources to ingest for style props and `className` strings.
#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct JsxConfig {
    /// Root-relative globs of `.tsx` and `.jsx` sources; empty means JSX ingest is off.
    #[serde(default)]
    pub globs: Vec<String>,
}

/// Which Tailwind generation the `[tailwind] config` file is written for.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum TailwindVersion {
    /// Detect from the file content.
    #[default]
    Auto,
    /// A v3 JS config with `theme` and `theme.extend`.
    V3,
    /// A v4 CSS-first config with `@theme`.
    V4,
}

/// The `[tailwind]` table: the config to cross-check and an optional generated theme mapping.
///
/// Every `*_file` key here resolves against the project root, not `css_root`.
#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct TailwindConfig {
    /// Path of the Tailwind config to cross-check; empty means Tailwind support is off.
    #[serde(default)]
    pub config: String,
    /// Tailwind v4 CSS entry (the file carrying `@import "tailwindcss"`); empty means detect.
    #[serde(default)]
    pub css_entry: String,
    /// Output path of the generated Tailwind theme mapping; empty means none.
    #[serde(default)]
    pub tokens_file: String,
    /// Emit prefix-qualified `theme.extend` keys (`space-4`) instead of bare steps (`4`).
    #[serde(default)]
    pub namespace_keys: bool,
    /// Also emit `-rgb` channel triplets so Tailwind opacity modifiers work.
    #[serde(default)]
    pub alpha_channels: bool,
    /// Shape of the `config` file.
    #[serde(default)]
    pub version: TailwindVersion,
}

/// The `[tokens.prefixes]` table: custom-property name prefixes.
///
/// `color`, `layer` and `font_family` may be empty (a bare identifier name); the others must be
/// non-empty so numeric steps keep a leading letter. A non-empty prefix matches `[a-z][a-z0-9-]*`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct TokenPrefixes {
    /// Prefix of palette color tokens: `--color-ink`.
    #[serde(default = "d_color")]
    pub color: String,
    /// Prefix of spacing tokens: `--space-4`.
    #[serde(default = "d_space")]
    pub space: String,
    /// Prefix of font-size tokens: `--font-size-16`.
    #[serde(default = "d_font_size")]
    pub font_size: String,
    /// Prefix of radius tokens: `--radius-8`.
    #[serde(default = "d_radius")]
    pub radius: String,
    /// Prefix of layer (z-index) tokens: `--layer-toast`.
    #[serde(default = "d_layer")]
    pub layer: String,
    /// Prefix of font-family tokens: `--font-family-base`.
    #[serde(default = "d_font_family")]
    pub font_family: String,
    /// Prefix of size tokens: `--size-32`.
    #[serde(default = "d_size")]
    pub size: String,
}

fn d_color() -> String {
    "color".to_owned()
}
fn d_space() -> String {
    "space".to_owned()
}
fn d_font_size() -> String {
    "font-size".to_owned()
}
fn d_radius() -> String {
    "radius".to_owned()
}
fn d_layer() -> String {
    "layer".to_owned()
}
fn d_font_family() -> String {
    "font-family".to_owned()
}
fn d_size() -> String {
    "size".to_owned()
}

impl Default for TokenPrefixes {
    fn default() -> Self {
        Self {
            color: d_color(),
            space: d_space(),
            font_size: d_font_size(),
            radius: d_radius(),
            layer: d_layer(),
            font_family: d_font_family(),
            size: d_size(),
        }
    }
}

/// The `[tokens]` table: prefixes, an optional verbatim CSS header and a JSON export path.
#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct RawTokens {
    /// Custom-property prefixes, see `[tokens.prefixes]`.
    #[serde(default)]
    pub prefixes: TokenPrefixes,
    /// A complete CSS comment block emitted verbatim above the generated marker; empty means
    /// no header. Must start with `/*`, end with `*/` and hold no interior `*/`.
    #[serde(default)]
    pub header: String,
    /// Path of a committed flat JSON export of the tokens, relative to the project root; empty
    /// means none.
    #[serde(default)]
    pub json_file: String,
}

/// A `[[platform]]` web viewport size in CSS pixels.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Viewport {
    /// Width in CSS pixels, greater than zero.
    pub width: u32,
    /// Height in CSS pixels, greater than zero.
    pub height: u32,
}

/// The `prefers-color-scheme` a platform or state emulates.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize, JsonSchema)]
pub enum ColorScheme {
    /// Light mode.
    #[serde(rename = "light")]
    Light,
    /// Dark mode.
    #[serde(rename = "dark")]
    Dark,
    /// No preference.
    #[default]
    #[serde(rename = "no-preference")]
    NoPreference,
}

/// Emulated media features (`prefers-reduced-motion`, `prefers-color-scheme`).
#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct MediaFeatures {
    /// Emulate `prefers-reduced-motion: reduce`.
    #[serde(default)]
    pub reduced_motion: bool,
    /// Emulated `prefers-color-scheme`.
    #[serde(default)]
    pub color_scheme: ColorScheme,
}

/// A web renderer's CDP network-throttling profile (chromium only).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct NetworkThrottle {
    /// Download throughput in bytes per second, greater than zero.
    pub download: f64,
    /// Upload throughput in bytes per second, greater than zero.
    pub upload: f64,
    /// Added latency in milliseconds, at least zero.
    #[serde(default)]
    pub latency: f64,
}

/// Browser engines the built-in `web` renderer drives.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum Engine {
    /// Chromium.
    Chromium,
    /// Firefox.
    Firefox,
    /// `WebKit`.
    Webkit,
}

/// One `[[platform]]` entry: an id, a renderer and that renderer's parameters.
///
/// The `web` renderer takes `engine` and `viewport` (required) plus the other web keys; the
/// `command` renderer takes `command` (required), `cwd` and `env`. A key of the other renderer
/// is rejected at load. Parameters are flat in the entry, not nested.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct RawPlatform {
    /// Platform id, unique across `[[platform]]`.
    pub id: String,
    /// Renderer id: `web` or `command`.
    pub renderer: String,
    /// Tags a screen's `applies_to` may reference as `tag:<name>`.
    #[serde(default)]
    pub tags: Vec<String>,
    /// web: browser engine.
    pub engine: Option<Engine>,
    /// web: viewport size.
    pub viewport: Option<Viewport>,
    /// web: device scale factor, greater than zero (default 1).
    pub device_scale: Option<f64>,
    /// web: emulated media features.
    pub media: Option<MediaFeatures>,
    /// web: browser locale.
    pub locale: Option<String>,
    /// web: platform-level settle delay in ms added to the readiness wait (default 500).
    pub settle_ms: Option<u32>,
    /// web: scripts added with `add_init_script` before navigation.
    pub init_scripts: Option<Vec<String>>,
    /// web: whether JavaScript is enabled (default true).
    pub java_script_enabled: Option<bool>,
    /// web, chromium only: CPU throttling multiplier, at least 1.
    pub cpu_throttle: Option<f64>,
    /// web, chromium only: network throttling profile.
    pub network_throttle: Option<NetworkThrottle>,
    /// web: base URL renders hit for approval; use the real production edge, never a dev
    /// server whose SPA fallback masks 404s.
    pub base_url: Option<String>,
    /// command: the command line, non-empty.
    pub command: Option<String>,
    /// command: working directory.
    pub cwd: Option<String>,
    /// command: extra environment variables.
    pub env: Option<IndexMap<String, String>>,
}

/// A step of a state's interaction script, run after the entry loads and before capture.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Action {
    /// Click `selector`.
    Click {
        /// CSS selector, non-empty.
        selector: String,
    },
    /// Hover `selector`.
    Hover {
        /// CSS selector, non-empty.
        selector: String,
    },
    /// Focus `selector`.
    Focus {
        /// CSS selector, non-empty.
        selector: String,
    },
    /// Type `value` into `selector`.
    Fill {
        /// CSS selector, non-empty.
        selector: String,
        /// Text to type.
        #[serde(default)]
        value: String,
    },
    /// Press `key` while `selector` is focused.
    Press {
        /// CSS selector, non-empty.
        selector: String,
        /// Key name, non-empty.
        key: String,
    },
    /// Wait for `selector` to appear.
    WaitFor {
        /// CSS selector, non-empty.
        selector: String,
        /// Renderer-enforced timeout in ms, greater than zero.
        #[serde(default)]
        timeout_ms: Option<u32>,
    },
}

/// What a network override does to the requests it matches.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum NetworkAction {
    /// Abort the request.
    Abort,
    /// Answer with `status`.
    Status,
    /// Delay by `delay_ms`.
    Delay,
    /// Never resolve (the loading-state primitive).
    Hold,
}

/// A state's network override for requests matching `url_pattern`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct NetworkOverride {
    /// URL pattern of the requests to override, non-empty.
    pub url_pattern: String,
    /// What to do to matching requests.
    pub action: NetworkAction,
    /// HTTP status 100 to 599, for `action = "status"`.
    pub status: Option<u32>,
    /// Delay in ms, greater than zero, for `action = "delay"`.
    pub delay_ms: Option<u32>,
}

/// One named state of a `[[screen]]`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ScreenState {
    /// State id, unique within its screen.
    pub id: String,
    /// Fixture path used to reach the state.
    pub fixture: Option<String>,
    /// Setup data used to reach the state.
    pub setup: Option<String>,
    /// Narrower platform set than the screen's: platform ids and `tag:<name>` entries.
    pub applies_to: Option<Vec<String>>,
    /// Media features overlaid on the platform's.
    pub media: Option<MediaFeatures>,
    /// Ordered interaction script.
    #[serde(default)]
    pub actions: Vec<Action>,
    /// Network overrides.
    #[serde(default)]
    pub network: Vec<NetworkOverride>,
    /// Id of a declared `[[session]]`.
    pub session: Option<String>,
    /// Id of a declared `[[mock_set]]`.
    pub mock: Option<String>,
    /// URL the page must end on.
    pub expect_url: Option<String>,
    /// Id of a sibling state this one is diffed against.
    pub diff_against: Option<String>,
    /// Per-state settle delay in ms overriding the platform's.
    pub settle_ms: Option<u32>,
}

/// One `[[screen]]` entry: a route, page or activity with named states.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ScreenConfig {
    /// Screen id, unique across `[[screen]]`.
    pub id: String,
    /// Entry route, page or activity.
    pub entry: String,
    /// Named states, at least one.
    pub states: Vec<ScreenState>,
    /// Platform ids and `tag:<name>` entries the screen applies to; absent means every platform.
    pub applies_to: Option<Vec<String>>,
}

/// One `[[session]]` or `[[mock_set]]` roster entry: an id plus opaque renderer-consumed data.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct RosterEntry {
    /// Entry id, unique within its roster.
    pub id: String,
    /// Opaque data the renderer reads.
    #[serde(default)]
    pub data: IndexMap<String, Dyn>,
}

/// The whole `crunk.toml`, as written. Tables owned by shared crates (`[check]`, `[perf]`, ...)
/// are validated by their owners and ignored here.
#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize, JsonSchema)]
#[schemars(title = "crunk.toml")]
pub struct RawSpec {
    /// Where managed CSS and generated tokens live. Required.
    #[schemars(required)]
    pub project: Option<ProjectConfig>,
    /// Named colors (`name = "<css color>"`), plus the `[palette.roles]` subtable. Required.
    #[schemars(required)]
    #[schemars(schema_with = "palette_schema")]
    pub palette: Option<IndexMap<String, Dyn>>,
    /// Allowed px scales. Required.
    #[schemars(required)]
    pub scales: Option<ScalesConfig>,
    /// Allowed font families and weights. Required.
    #[schemars(required)]
    pub typography: Option<TypographyConfig>,
    /// Named z-index layers (`name = <integer>`); optional, absent means LAYER001 is silent.
    pub layers: Option<IndexMap<String, i64>>,
    /// File and class organization. Required.
    #[schemars(required)]
    pub org: Option<OrgConfig>,
    /// Per-rule severities (`RULE001 = "error" | "warn" | "off"`), `fix_tolerance` and
    /// `color_tolerance`; optional.
    #[schemars(schema_with = "lint_schema")]
    pub lint: Option<IndexMap<String, Dyn>>,
    /// Token naming and export; optional.
    pub tokens: Option<RawTokens>,
    /// JSX ingest; optional.
    pub jsx: Option<JsxConfig>,
    /// Tailwind cross-check; optional.
    pub tailwind: Option<TailwindConfig>,
    /// Viewport name to px, plus `base_required`; optional. Absent with a `[tailwind]` config
    /// declared means the Tailwind v3 defaults; absent entirely means the BP rules are off.
    #[schemars(schema_with = "breakpoints_schema")]
    pub breakpoints: Option<IndexMap<String, Dyn>>,
    /// Gallery platforms; optional.
    pub platform: Option<Vec<RawPlatform>>,
    /// Gallery screens; optional.
    pub screen: Option<Vec<ScreenConfig>>,
    /// Gallery session roster; optional.
    pub session: Option<Vec<RosterEntry>>,
    /// Gallery mock-set roster; optional.
    pub mock_set: Option<Vec<RosterEntry>>,
}

fn palette_schema(_: &mut schemars::SchemaGenerator) -> schemars::Schema {
    schemars::json_schema!({
        "type": "object",
        "description": "Named colors (`name = \"<css color>\"`), plus the `[palette.roles]` subtable. Required.",
        "properties": {
            "roles": {
                "type": "object",
                "description": "Role name to a `[foreground, background]` palette-name pair, or a `{ pair = [fg, bg], floor = <n> }` table overriding the contrast floor (default 4.5).",
                "additionalProperties": {
                    "oneOf": [
                        {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2},
                        {
                            "type": "object",
                            "properties": {
                                "pair": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2},
                                "floor": {"type": "number", "exclusiveMinimum": 0, "default": 4.5}
                            },
                            "required": ["pair"],
                            "additionalProperties": false
                        }
                    ]
                }
            }
        },
        "additionalProperties": {"type": "string", "description": "A CSS color literal: hex, rgb(), hsl() or a named color."}
    })
}

fn lint_schema(_: &mut schemars::SchemaGenerator) -> schemars::Schema {
    let mut properties = serde_json::Map::new();
    properties.insert(
        "fix_tolerance".to_owned(),
        serde_json::json!({
            "type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 1, "default": 0.15,
            "description": "Largest relative distance a fix may move a value to snap it to a token."
        }),
    );
    properties.insert(
        "color_tolerance".to_owned(),
        serde_json::json!({
            "type": "number", "exclusiveMinimum": 0, "default": 8.0,
            "description": "Largest palette distance at which a color literal is treated as a palette color."
        }),
    );
    for row in crate::catalog::CATALOG {
        properties.insert(
            row.id(),
            serde_json::json!({
                "enum": ["error", "warn", "off"], "default": row.default.as_str(),
                "description": "Severity override for this rule."
            }),
        );
    }
    let schema = serde_json::json!({
        "type": "object",
        "description": "Per-rule severities (`RULE001 = \"error\" | \"warn\" | \"off\"`), `fix_tolerance` and `color_tolerance`; optional.",
        "properties": properties,
        "additionalProperties": false
    });
    schemars::Schema::try_from(schema).unwrap_or_else(|_| unreachable!("a JSON object is a schema"))
}

fn breakpoints_schema(_: &mut schemars::SchemaGenerator) -> schemars::Schema {
    schemars::json_schema!({
        "type": "object",
        "description": "Viewport name to px, plus `base_required`; optional.",
        "properties": {
            "base_required": {
                "type": "array", "items": {"type": "string"},
                "default": crate::catalog::DEFAULT_BASE_REQUIRED,
                "description": "Layout-critical utility families whose responsive variants demand an unprefixed mobile base (BP002)."
            }
        },
        "additionalProperties": {"type": "integer", "description": "Breakpoint width in px."}
    })
}
