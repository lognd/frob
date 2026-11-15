//! Detection of the Tailwind v4 CSS entry when `[tailwind] css_entry` is unset.
//!
//! Root-relative candidates come first (as in the Python crunk). Failing those, a CSS file below
//! the directory of the configured `[tailwind] config` whose `@config` names that file wins: this
//! finds `web/src/index.css` for `web/tailwind.config.ts`.

// frob:ticket 01M4DVX3DEBN2QS1WVQACE8EHJ

use std::path::{Component, Path, PathBuf};

use super::v4::read_v4;

/// Where V4 CSS entries are looked for, relative to the project root.
const V4_CSS_CANDIDATES: [&str; 6] = [
    "styles/tailwind.css",
    "styles/main.css",
    "styles/index.css",
    "src/index.css",
    "src/main.css",
    "src/styles.css",
];

/// How many directory levels below the config directory the `@config` back-reference scan visits.
const SCAN_DEPTH: usize = 4;

/// Directory names never scanned for a CSS entry.
const SKIPPED_DIRS: [&str; 4] = ["node_modules", "target", "dist", "build"];

/// Resolve `.` and `..` lexically, so `web/src/../tailwind.config.ts` equals `web/tailwind.config.ts`.
fn normalize(path: &Path) -> PathBuf {
    let mut out = PathBuf::new();
    for part in path.components() {
        match part {
            Component::CurDir => {}
            Component::ParentDir => {
                out.pop();
            }
            other => out.push(other.as_os_str()),
        }
    }
    out
}

/// Whether the CSS file at `path` is a v4 entry; with `config` also requires its `@config` to name it.
fn is_entry(path: &Path, config: Option<&Path>) -> bool {
    let Some(read) = std::fs::read_to_string(path)
        .ok()
        .and_then(|text| read_v4(&text).ok())
    else {
        return false;
    };
    let Some(config) = config else {
        return read.is_v4;
    };
    let dir = path.parent().unwrap_or(Path::new(""));
    read.config_ref
        .is_some_and(|r| normalize(&dir.join(r)) == normalize(config))
}

/// The first existing root-relative candidate that is a v4 CSS entry.
fn root_candidate(root: &Path) -> Option<PathBuf> {
    V4_CSS_CANDIDATES
        .iter()
        .map(|c| root.join(c))
        .find(|p| is_entry(p, None))
}

/// The CSS file at most `depth` levels below `dir` whose `@config` names `config`, in name order.
fn back_reference(dir: &Path, config: &Path, depth: usize) -> Option<PathBuf> {
    let mut entries: Vec<_> = std::fs::read_dir(dir).ok()?.flatten().collect();
    entries.sort_by_key(std::fs::DirEntry::file_name);
    for entry in &entries {
        let path = entry.path();
        let is_css = path
            .extension()
            .is_some_and(|e| e.eq_ignore_ascii_case("css"));
        if is_css && path.is_file() && is_entry(&path, Some(config)) {
            return Some(path);
        }
    }
    if depth == 0 {
        return None;
    }
    entries.iter().find_map(|entry| {
        let name = entry.file_name().to_string_lossy().into_owned();
        let scanned = !name.starts_with('.') && !SKIPPED_DIRS.contains(&name.as_str());
        (scanned && entry.path().is_dir())
            .then(|| back_reference(&entry.path(), config, depth - 1))
            .flatten()
    })
}

/// The v4 CSS entry of the project at `root`: a root-relative candidate, else a CSS file below
/// `config`'s directory (and then its parents up to `root`) whose `@config` names `config`.
pub fn detect_css_entry(root: &Path, config: Option<&Path>) -> Option<PathBuf> {
    if let Some(found) = root_candidate(root) {
        tracing::debug!(entry = %found.display(), "tailwind detect: root-relative css entry");
        return Some(found);
    }
    let config = normalize(config?);
    let mut dir = config.parent()?;
    loop {
        if let Some(found) = back_reference(dir, &config, SCAN_DEPTH) {
            tracing::info!(entry = %found.display(), config = %config.display(), "tailwind detect: css entry found by its @config back-reference");
            return Some(found);
        }
        if dir == normalize(root) || !dir.starts_with(normalize(root)) {
            return None;
        }
        dir = dir.parent()?;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn project(files: &[(&str, &str)]) -> tempfile::TempDir {
        let dir = tempfile::tempdir().expect("tempdir");
        for (rel, text) in files {
            let path = dir.path().join(rel);
            std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
            std::fs::write(path, text).expect("write");
        }
        dir
    }

    // frob:tests crates/crunk-ingest/src/tailwind/detect.rs::detect_css_entry
    #[test]
    fn an_entry_below_the_config_directory_is_found_by_its_config_back_reference() {
        let dir = project(&[
            ("web/tailwind.config.ts", "export default {}"),
            (
                "web/src/index.css",
                "@import \"tailwindcss\";\n@config \"../tailwind.config.ts\";\n",
            ),
            ("web/src/other.css", "@config \"../nope.ts\";\n"),
        ]);
        let found = detect_css_entry(dir.path(), Some(&dir.path().join("web/tailwind.config.ts")));
        assert_eq!(found, Some(dir.path().join("web/src/index.css")));
    }

    // frob:tests crates/crunk-ingest/src/tailwind/detect.rs::detect_css_entry
    #[test]
    fn a_root_candidate_wins_and_no_back_reference_means_no_entry() {
        let dir = project(&[
            ("web/tailwind.config.ts", "export default {}"),
            ("web/src/index.css", "body { color: red; }\n"),
        ]);
        let config = dir.path().join("web/tailwind.config.ts");
        assert_eq!(detect_css_entry(dir.path(), Some(&config)), None);
        assert_eq!(detect_css_entry(dir.path(), None), None);
        std::fs::create_dir_all(dir.path().join("src")).expect("mkdir");
        std::fs::write(
            dir.path().join("src/index.css"),
            "@import \"tailwindcss\";\n",
        )
        .expect("write");
        assert_eq!(
            detect_css_entry(dir.path(), Some(&config)),
            Some(dir.path().join("src/index.css"))
        );
    }
}
