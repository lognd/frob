//! The resolved, validated design law: [`DesignSpec`] and the sub-models that differ from the
//! TOML shape.

// frob:ticket 01M43ARX764095Q4VWABWXXV5H

use std::path::{Component, Path, PathBuf};

use crunk_values::Color;
use indexmap::IndexMap;
use serde::{Serialize, Serializer};

use crate::catalog::{Severity, default_severity};
use crate::table::{
    Engine, JsxConfig, MediaFeatures, NetworkThrottle, OrgConfig, ProjectConfig, RosterEntry,
    ScalesConfig, ScreenConfig, TailwindConfig, TypographyConfig, Viewport,
};

/// One `[palette.roles]` entry: a foreground and background palette name plus a contrast floor.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct RolePair {
    /// Palette name of the foreground color.
    pub foreground: String,
    /// Palette name of the background color.
    pub background: String,
    /// Minimum contrast ratio, defaulting to the WCAG AA floor.
    pub floor: f64,
}

/// The `[lint]` table: severity overrides plus the two fix tolerances.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct LintConfig {
    /// Severity overrides by rule id, in declaration order.
    pub rules: IndexMap<String, Severity>,
    /// Largest relative distance a fix may move a value; in (0, 1), default 0.15.
    pub fix_tolerance: f64,
    /// Largest palette distance treated as a palette color; greater than 0, default 8.0.
    pub color_tolerance: f64,
}

impl Default for LintConfig {
    fn default() -> Self {
        Self {
            rules: IndexMap::new(),
            fix_tolerance: 0.15,
            color_tolerance: 8.0,
        }
    }
}

/// The `[breakpoints]` table resolved once at load: viewport name to px plus `base_required`.
///
/// Precedence: a declared section wins; absent with a `[tailwind]` config declared falls back to
/// the Tailwind v3 defaults; absent entirely leaves `points` empty and the BP rules off.
#[derive(Debug, Clone, PartialEq, Default, Serialize)]
pub struct BreakpointsConfig {
    /// Viewport name to px width, in declaration order.
    pub points: IndexMap<String, i64>,
    /// Utility families whose responsive variants demand an unprefixed mobile base (BP002).
    pub base_required: Vec<String>,
}

/// The `[tokens]` table flattened for naming: the seven prefixes, header and JSON export path.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct TokensConfig {
    /// Prefix of color tokens (may be empty).
    pub color: String,
    /// Prefix of spacing tokens.
    pub space: String,
    /// Prefix of font-size tokens.
    pub font_size: String,
    /// Prefix of radius tokens.
    pub radius: String,
    /// Prefix of layer tokens (may be empty).
    pub layer: String,
    /// Prefix of font-family tokens (may be empty).
    pub font_family: String,
    /// Prefix of size tokens.
    pub size: String,
    /// Verbatim CSS header comment, or empty.
    pub header: String,
    /// Committed flat-JSON export path relative to the project root, or empty.
    pub json_file: String,
}

impl Default for TokensConfig {
    fn default() -> Self {
        let prefixes = crate::table::TokenPrefixes::default();
        Self {
            color: prefixes.color,
            space: prefixes.space,
            font_size: prefixes.font_size,
            radius: prefixes.radius,
            layer: prefixes.layer,
            font_family: prefixes.font_family,
            size: prefixes.size,
            header: String::new(),
            json_file: String::new(),
        }
    }
}

/// Resolved parameters of a platform using the built-in `web` renderer.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct WebRendererParams {
    /// Browser engine.
    pub engine: Engine,
    /// Viewport size.
    pub viewport: Viewport,
    /// Device scale factor.
    pub device_scale: f64,
    /// Emulated media features.
    pub media: MediaFeatures,
    /// Browser locale.
    pub locale: Option<String>,
    /// Settle delay in ms added to the readiness wait.
    pub settle_ms: u32,
    /// Context-level init scripts.
    pub init_scripts: Vec<String>,
    /// Whether JavaScript is enabled.
    pub java_script_enabled: bool,
    /// CPU throttling multiplier (chromium only).
    pub cpu_throttle: Option<f64>,
    /// Network throttling profile (chromium only).
    pub network_throttle: Option<NetworkThrottle>,
    /// Base URL renders hit for approval.
    pub base_url: Option<String>,
}

/// Resolved parameters of a platform using the generic `command` renderer.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct CommandRendererParams {
    /// The command line.
    pub command: String,
    /// Working directory.
    pub cwd: Option<String>,
    /// Extra environment variables.
    pub env: IndexMap<String, String>,
}

/// Renderer-specific parameters of a platform.
#[derive(Debug, Clone, PartialEq, Serialize)]
#[serde(untagged)]
pub enum RendererParams {
    /// The built-in `web` renderer.
    Web(WebRendererParams),
    /// The generic `command` renderer.
    Command(CommandRendererParams),
}

/// One `[[platform]]` entry resolved: id, renderer id, typed params and tags.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct PlatformConfig {
    /// Platform id.
    pub id: String,
    /// Renderer id (`web` or `command`).
    pub renderer: String,
    /// Renderer parameters.
    pub params: RendererParams,
    /// Tags a screen may reference as `tag:<name>`.
    pub tags: Vec<String>,
}

/// The fully validated, frozen design law loaded from one `crunk.toml`.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct DesignSpec {
    /// The project root every relative path resolves against.
    pub root: PathBuf,
    /// `[project]`.
    pub project: ProjectConfig,
    /// `[palette]` colors in declaration order.
    #[serde(serialize_with = "serialize_palette")]
    pub palette: IndexMap<String, Color>,
    /// `[palette.roles]` in declaration order.
    pub roles: IndexMap<String, RolePair>,
    /// `[scales]`.
    pub scales: ScalesConfig,
    /// `[typography]`.
    pub typography: TypographyConfig,
    /// `[layers]`: layer name to z-index, empty when absent.
    pub layers: IndexMap<String, i64>,
    /// `[org]`.
    pub org: OrgConfig,
    /// `[lint]`.
    pub lint: LintConfig,
    /// `[tokens]`.
    pub tokens: TokensConfig,
    /// `[jsx]`.
    pub jsx: JsxConfig,
    /// `[tailwind]`.
    pub tailwind: TailwindConfig,
    /// `[breakpoints]` resolved.
    pub breakpoints: BreakpointsConfig,
    /// `[[platform]]` by id.
    pub platforms: IndexMap<String, PlatformConfig>,
    /// `[[screen]]` by id.
    pub screens: IndexMap<String, ScreenConfig>,
    /// `[[session]]` by id.
    pub sessions: IndexMap<String, RosterEntry>,
    /// `[[mock_set]]` by id.
    pub mock_sets: IndexMap<String, RosterEntry>,
}

fn serialize_palette<S: Serializer>(
    palette: &IndexMap<String, Color>,
    serializer: S,
) -> Result<S::Ok, S::Error> {
    #[derive(Serialize)]
    struct Channels {
        r: f64,
        g: f64,
        b: f64,
        a: f64,
    }
    serializer.collect_map(palette.iter().map(|(name, c)| {
        (
            name,
            Channels {
                r: c.r,
                g: c.g,
                b: c.b,
                a: c.a,
            },
        )
    }))
}

/// Join `base` and `rel` and collapse `.` and `..` lexically, without touching the filesystem.
pub fn normalize_join(base: &Path, rel: &str) -> PathBuf {
    let mut out = PathBuf::new();
    for component in base.join(rel).components() {
        match component {
            Component::CurDir => {}
            Component::ParentDir => {
                if !out.pop() {
                    out.push("..");
                }
            }
            other => out.push(other.as_os_str()),
        }
    }
    out
}

impl DesignSpec {
    /// The effective severity of `rule`: catalog default, overridden by `[lint]`.
    pub fn severity(&self, rule: &str) -> Severity {
        self.lint
            .rules
            .get(rule)
            .copied()
            .or_else(|| default_severity(rule))
            .unwrap_or(Severity::Error)
    }

    /// Absolute managed CSS root: `root` joined with `[project] css_root`.
    pub fn css_root(&self) -> PathBuf {
        normalize_join(&self.root, &self.project.css_root)
    }

    /// The generated tokens file. Path-base law: `[project] tokens_file` resolves against
    /// `css_root`.
    pub fn tokens_path(&self) -> PathBuf {
        normalize_join(&self.css_root(), &self.project.tokens_file)
    }

    /// The generated Tailwind theme mapping, if configured. Path-base law: `[tailwind]
    /// tokens_file` resolves against the project root, not `css_root`.
    pub fn tailwind_tokens_path(&self) -> Option<PathBuf> {
        self.root_relative(&self.tailwind.tokens_file)
    }

    /// The committed flat-JSON token export, if configured. Path-base law: `[tokens] json_file`
    /// resolves against the project root, not `css_root`.
    pub fn json_tokens_path(&self) -> Option<PathBuf> {
        self.root_relative(&self.tokens.json_file)
    }

    /// The Tailwind config to cross-check, if configured; resolves against the project root.
    pub fn tailwind_config_path(&self) -> Option<PathBuf> {
        self.root_relative(&self.tailwind.config)
    }

    fn root_relative(&self, rel: &str) -> Option<PathBuf> {
        (!rel.is_empty()).then(|| normalize_join(&self.root, rel))
    }
}
