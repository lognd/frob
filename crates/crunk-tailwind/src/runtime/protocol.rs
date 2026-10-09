//! The JSON request the node helper reads and the response it prints (`node/helper.mjs`).

// frob:ticket 01M43ARYX61ESX3S9XG1WS0DQ4

use std::collections::BTreeMap;
use std::path::Path;

use serde::{Deserialize, Serialize};

/// What the helper is asked to do; the tag is the helper's `mode`.
#[derive(Debug, Clone, Serialize)]
#[serde(tag = "mode")]
pub(crate) enum Request {
    /// Compile candidates against a v3 config (or Tailwind's defaults when none).
    #[serde(rename = "v3")]
    V3 {
        #[serde(rename = "projectRoot")]
        project_root: String,
        #[serde(rename = "configPath", skip_serializing_if = "Option::is_none")]
        config_path: Option<String>,
        candidates: Vec<String>,
    },
    /// Compile candidates against a v4 CSS entry.
    #[serde(rename = "v4")]
    V4 {
        #[serde(rename = "projectRoot")]
        project_root: String,
        #[serde(rename = "cssEntryPath")]
        css_entry_path: String,
        candidates: Vec<String>,
    },
    /// Resolve the project-owned theme of a v3 config.
    #[serde(rename = "v3-theme")]
    V3Theme {
        #[serde(rename = "projectRoot")]
        project_root: String,
        #[serde(rename = "configPath", skip_serializing_if = "Option::is_none")]
        config_path: Option<String>,
    },
    /// Resolve the project-owned theme of a v4 CSS entry.
    #[serde(rename = "v4-theme")]
    V4Theme {
        #[serde(rename = "projectRoot")]
        project_root: String,
        #[serde(rename = "cssEntryPath")]
        css_entry_path: String,
    },
}

/// The helper's single JSON object.
#[derive(Debug, Clone, Deserialize)]
pub(crate) struct Response {
    pub ok: bool,
    #[serde(default)]
    pub error: Option<String>,
    #[serde(default, rename = "configPath")]
    pub config_path: Option<String>,
    #[serde(default)]
    pub css: Option<String>,
    #[serde(default)]
    pub theme: Option<BTreeMap<String, String>>,
}

/// A path as the UTF-8 text the request carries.
pub(crate) fn path_text(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}
