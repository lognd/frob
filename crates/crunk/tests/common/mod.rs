//! Shared fixture pieces for the crunk integration tests.
//!
//! CRAFT001/005/010 fire at error on a project with UI but no focus, press or motion styling, so
//! every fixture that expects a clean `crunk check` carries `STATE_CSS`.

// frob:ticket 01M61WBFHXRYRQBBW2RWJH9CR5

#![allow(dead_code, reason = "each test binary uses a different subset")]

use std::io::Write;
use std::path::Path;

use gob_path::Shown;

/// Focus, press and motion styling that satisfies CRAFT001, CRAFT005 and CRAFT010.
pub const STATE_CSS: &str = ":focus-visible { outline: 2px solid currentColor; }\n:active { opacity: 0.9; }\nbody { transition: opacity 0.2s; }\n@media (prefers-reduced-motion: reduce) { body { transition: none; } }\n";

/// Append `STATE_CSS` to the stylesheet at `path`, unless it already styles `:focus-visible`.
pub fn append_states(path: &Path) {
    let text = std::fs::read_to_string(path).unwrap_or_default();
    if text.contains(":focus-visible") {
        tracing::debug!(path = %Shown::of(path), "fixture already carries state styles");
        return;
    }
    let mut file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .expect("open stylesheet");
    file.write_all(STATE_CSS.as_bytes()).expect("append states");
    tracing::debug!(path = %Shown::of(path), "appended state styles to fixture");
}

/// Every `.css` file under `dir` (sorted), skipping generated token files and dependency dirs.
fn sheets(dir: &Path, out: &mut Vec<std::path::PathBuf>) {
    let mut entries: Vec<_> = std::fs::read_dir(dir)
        .into_iter()
        .flatten()
        .flatten()
        .map(|e| e.path())
        .collect();
    entries.sort();
    for path in entries {
        let name = path
            .file_name()
            .map(|n| Shown::of(Path::new(n)).to_string())
            .unwrap_or_default();
        if path.is_dir() {
            if name != "node_modules" && !name.starts_with('.') {
                sheets(&path, out);
            }
        } else if path
            .extension()
            .is_some_and(|e| e.eq_ignore_ascii_case("css"))
            && !name.contains("tokens")
        {
            out.push(path);
        }
    }
}

/// WCAG relative luminance of a `#rrggbb` colour, or `None` for anything else.
fn luminance(hex: &str) -> Option<f64> {
    let digits = hex.strip_prefix('#').filter(|d| d.len() == 6)?;
    let channel = |i: usize| {
        let v = f64::from(u8::from_str_radix(&digits[i..i + 2], 16).ok()?) / 255.0;
        Some(if v <= 0.03928 {
            v / 12.92
        } else {
            ((v + 0.055) / 1.055).powf(2.4)
        })
    };
    Some(0.2126 * channel(0)? + 0.7152 * channel(2)? + 0.0722 * channel(4)?)
}

/// Declare the danger, warning and success roles CRAFT008 wants in the `crunk.toml` under `root`,
/// each pairing the project's darkest and lightest hex palette colours (maximal contrast); a project
/// with fewer than two such colours, or that already declares a role, is left alone.
pub fn satisfy_roles(root: &Path) {
    let path = root.join("crunk.toml");
    let Ok(text) = std::fs::read_to_string(&path) else {
        return;
    };
    let Ok(mut doc) = text.parse::<toml_edit::DocumentMut>() else {
        return;
    };
    let Some(palette) = doc.get("palette").and_then(|p| p.as_table()) else {
        return;
    };
    let mut colours: Vec<(String, f64)> = palette
        .iter()
        .filter_map(|(k, v)| Some((k.to_string(), luminance(v.as_str()?)?)))
        .collect();
    colours.sort_by(|a, b| a.1.total_cmp(&b.1));
    let (Some(dark), Some(light)) = (colours.first(), colours.last()) else {
        return;
    };
    if colours.len() < 2 {
        return;
    }
    let (fg, bg) = (dark.0.clone(), light.0.clone());
    let roles = doc["palette"]
        .as_table_mut()
        .expect("palette is a table")
        .entry("roles")
        .or_insert_with(|| toml_edit::Item::Table(toml_edit::Table::new()));
    let Some(roles) = roles.as_table_mut() else {
        return;
    };
    for (role, aliases) in [
        ("danger", ["danger", "error", "destructive"]),
        ("warning", ["warning", "caution", "warning"]),
        ("success", ["success", "positive", "success"]),
    ] {
        if roles
            .iter()
            .any(|(k, _)| aliases.iter().any(|a| k.eq_ignore_ascii_case(a)))
        {
            continue;
        }
        let mut pair = toml_edit::Array::new();
        pair.push(fg.as_str());
        pair.push(bg.as_str());
        roles.insert(role, toml_edit::value(pair));
    }
    std::fs::write(&path, doc.to_string()).expect("write crunk.toml");
    tracing::debug!(path = %Shown::of(&path), "declared semantic roles in fixture spec");
}

/// Make the project under `root` satisfy the CRAFT rules: semantic roles via `satisfy_roles`, and
/// `STATE_CSS` appended to its first hand-written stylesheet (none: no UI to judge, nothing added).
pub fn satisfy_craft(root: &Path) {
    satisfy_roles(root);
    let mut found = Vec::new();
    sheets(root, &mut found);
    if found
        .iter()
        .any(|p| std::fs::read_to_string(p).is_ok_and(|t| t.contains(":focus-visible")))
    {
        return;
    }
    // Prefer a sheet under `css_root`: a stray sheet beside it may be org-ignored and unjudged.
    let css_root = root.join(css_root_of(root));
    if let Some(first) = found
        .iter()
        .find(|p| p.starts_with(&css_root))
        .or(found.first())
    {
        append_states(first);
    } else {
        tracing::debug!(root = %Shown::of(root), "no stylesheet to carry state styles");
    }
}

/// The `[project] css_root` of the spec under `root`, defaulting to `styles`.
fn css_root_of(root: &Path) -> String {
    std::fs::read_to_string(root.join("crunk.toml"))
        .ok()
        .and_then(|t| t.parse::<toml_edit::DocumentMut>().ok())
        .and_then(|d| {
            d.get("project")?
                .get("css_root")?
                .as_str()
                .map(String::from)
        })
        .unwrap_or_else(|| "styles".to_string())
}
