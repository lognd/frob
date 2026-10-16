//! Project detection for `init`: JSX sources and a Tailwind config.

// frob:ticket 01M43ATD7ZGTNCY5036AYEJR7P

use std::path::Path;

/// Tailwind config names, in the order `init` prefers them.
const TAILWIND_CONFIGS: [&str; 4] = [
    "tailwind.config.ts",
    "tailwind.config.js",
    "tailwind.config.cjs",
    "tailwind.config.mjs",
];
/// Directories never searched for JSX sources.
const SKIP_DIRS: [&str; 5] = ["node_modules", "dist", "build", "target", "coverage"];
/// How deep below the project root JSX sources are searched.
const MAX_DEPTH: usize = 5;

/// What `init` found in the project.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Detected {
    /// `[jsx] globs`, when the project uses React or has `.jsx`/`.tsx` files.
    pub jsx_globs: Vec<String>,
    /// `[tailwind] config`, when a Tailwind config file exists.
    pub tailwind_config: Option<String>,
}

/// Inspect `root` for JSX and Tailwind.
#[must_use]
pub fn detect(root: &Path) -> Detected {
    let (mut tsx, mut jsx) = (false, false);
    walk(root, 0, &mut tsx, &mut jsx);
    let react = package_has_dep(root, "react");
    let base = if root.join("src").is_dir() {
        "src/"
    } else {
        ""
    };
    let mut jsx_globs = Vec::new();
    if tsx || (react && !jsx) {
        jsx_globs.push(format!("{base}**/*.tsx"));
    }
    if jsx || (react && !tsx) {
        jsx_globs.push(format!("{base}**/*.jsx"));
    }
    let tailwind_config = TAILWIND_CONFIGS
        .iter()
        .find(|name| root.join(name).is_file())
        .map(|name| (*name).to_owned());
    let found = Detected {
        jsx_globs,
        tailwind_config,
    };
    tracing::debug!(?found, "init: detection");
    found
}

fn walk(dir: &Path, depth: usize, tsx: &mut bool, jsx: &mut bool) {
    if depth > MAX_DEPTH {
        return;
    }
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        let name = entry.file_name().to_string_lossy().into_owned();
        if path.is_dir() {
            if !name.starts_with('.') && !SKIP_DIRS.contains(&name.as_str()) {
                walk(&path, depth + 1, tsx, jsx);
            }
        } else {
            match path.extension().and_then(|e| e.to_str()) {
                Some(e) if e.eq_ignore_ascii_case("tsx") => *tsx = true,
                Some(e) if e.eq_ignore_ascii_case("jsx") => *jsx = true,
                _ => {}
            }
        }
    }
}

fn package_has_dep(root: &Path, dep: &str) -> bool {
    let Ok(text) = std::fs::read_to_string(root.join("package.json")) else {
        return false;
    };
    let Ok(doc) = serde_json::from_str::<serde_json::Value>(&text) else {
        return false;
    };
    ["dependencies", "devDependencies"]
        .iter()
        .any(|k| doc.get(k).and_then(|d| d.get(dep)).is_some())
}

/// The TOML appended to the preset for what was detected, plus the section names.
#[must_use]
pub fn sections(found: &Detected) -> (String, Vec<String>) {
    let mut blocks = Vec::new();
    let mut names = Vec::new();
    if !found.jsx_globs.is_empty() {
        let globs: Vec<String> = found.jsx_globs.iter().map(|g| format!("\"{g}\"")).collect();
        blocks.push(format!("\n[jsx]\nglobs = [{}]\n", globs.join(", ")));
        names.push("jsx".to_owned());
    }
    if let Some(config) = &found.tailwind_config {
        blocks.push(format!("\n[tailwind]\nconfig = \"{config}\"\n"));
        names.push("tailwind".to_owned());
    }
    (blocks.concat(), names)
}
