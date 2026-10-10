//! What counts as a test, which package owns it and what nextest calls it.
//!
//! # The `#[test]` heuristic
//!
//! The symbol graph records no attributes. With the file text at hand
//! ([`is_test_fn`] given `Some(text)`) a function is a test when a contiguous
//! attribute or comment line directly above it is an attribute whose last path
//! segment is `test`, `rstest` or `test_case` (`#[test]`, `#[tokio::test(..)]`,
//! `#[rstest]`); `#[cfg(test)]` is not one. Without text (the `None` form, used
//! by [`crate::test001`]) the fallback is naming:
//! a free function inside a module called `tests`, or any free function in a
//! file under a `tests/` directory. The fallback over-approximates helpers in
//! `tests/`; selecting a helper only adds a filter that matches nothing.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use gob_symbols::{SymbolKind, SymbolRecord, Target};

/// Directories whose files are crate roots of their own (no module prefix).
const ROOT_DIRS: &[&str] = &["tests", "benches", "examples"];

/// True when the attribute line `line` marks a test function.
fn is_test_attribute(line: &str) -> bool {
    let Some(inner) = line.strip_prefix("#[") else {
        return false;
    };
    let head = inner
        .split(['(', ']', '='])
        .next()
        .unwrap_or_default()
        .trim();
    let last = head.rsplit("::").next().unwrap_or_default();
    matches!(last, "test" | "rstest" | "test_case")
}

/// True when `path` is an integration-test file (under a `tests/` directory).
pub fn is_test_file(path: &str) -> bool {
    path.starts_with("tests/")
        || path.contains("/tests/")
        || gob_symbols::is_python_test_file(path)
        || gob_symbols::is_typescript_test_file(path)
        || gob_symbols::is_csharp_test_file(path)
}

/// True when `rec` is a test function; see the module docs for the heuristic.
pub fn is_test_fn(rec: &SymbolRecord, text: Option<&str>) -> bool {
    // frob:ticket 01M43A5DJT8XBQYEK36F0KSGKF
    if gob_symbols::is_python_path(rec.symref.path()) {
        return gob_symbols::is_python_test_fn(rec);
    }
    if gob_symbols::is_csharp_path(rec.symref.path()) {
        // frob:ticket 01M44YQV7C3FYXB3QH20R4E5N8
        return match text {
            Some(text) => gob_symbols::is_csharp_test_fn(rec, text),
            None => {
                rec.kind == SymbolKind::Method
                    && gob_symbols::is_csharp_test_file(rec.symref.path())
            }
        };
    }
    if gob_symbols::is_typescript_path(rec.symref.path()) {
        // frob:ticket 01M4828JB2S4JZY2QRB97A7SXX
        return gob_symbols::is_typescript_test_fn(rec);
    }
    if rec.kind != SymbolKind::Function || !matches!(rec.symref.target(), Target::Symbol(_)) {
        return false;
    }
    let Some(text) = text else {
        let segs = rec.symref.segments();
        let in_tests_mod = segs.len() >= 2 && segs[..segs.len() - 1].iter().any(|s| s == "tests");
        return in_tests_mod || is_test_file(rec.symref.path());
    };
    let start = usize::try_from(u32::from(rec.span.start())).unwrap_or(usize::MAX);
    let Some(before) = text.get(..start) else {
        return false;
    };
    for line in before.trim_end_matches([' ', '\t']).lines().rev() {
        let t = line.trim();
        if t.starts_with("#[") {
            if is_test_attribute(t) {
                return true;
            }
        } else if !t.starts_with("//") {
            return false;
        }
    }
    false
}

// frob:ticket 01M44YQV7C3FYXB3QH20R4E5N8
/// The C# test `rec` is (id `Namespace.Type.Method`, framework, `PlayMode` capability), read from the file `text`.
pub fn csharp_test(rec: &SymbolRecord, text: &str) -> Option<gob_symbols::CsharpTest> {
    gob_symbols::csharp_test(rec, text)
}

/// The module path of a source file inside its package (`src/a/b.rs` is `a::b`; crate roots are empty).
pub fn module_prefix(path_in_package: &Path) -> Vec<String> {
    let comps: Vec<String> = path_in_package
        .components()
        .map(|c| c.as_os_str().to_string_lossy().into_owned())
        .collect();
    let Some((first, rest)) = comps.split_first() else {
        return Vec::new();
    };
    if ROOT_DIRS.contains(&first.as_str()) {
        return Vec::new();
    }
    let rest = if first == "src" { rest } else { &comps[..] };
    if rest.first().is_some_and(|s| s == "bin") {
        return Vec::new();
    }
    let mut out: Vec<String> = rest.to_vec();
    if let Some(last) = out.pop() {
        let stem = last.strip_suffix(".rs").unwrap_or(&last);
        if !matches!(stem, "lib" | "main" | "mod") {
            out.push(stem.to_owned());
        }
    }
    out
}

/// Maps repo-relative files to the Cargo package that owns them.
#[derive(Debug)]
pub struct Packages {
    root: PathBuf,
    cache: HashMap<PathBuf, Option<(String, PathBuf)>>,
}

impl Packages {
    /// A resolver for the work tree at `root`.
    pub fn new(root: &Path) -> Self {
        Self {
            root: root.to_path_buf(),
            cache: HashMap::new(),
        }
    }

    /// The package name and the file's path relative to the package directory.
    pub fn owner(&mut self, file: &str) -> Option<(String, PathBuf)> {
        let mut dir = Path::new(file).parent().map(Path::to_path_buf);
        while let Some(d) = dir {
            if let Some((name, pkg_dir)) = self.package_at(&d) {
                let rel = Path::new(file).strip_prefix(&pkg_dir).ok()?.to_path_buf();
                return Some((name, rel));
            }
            dir = d.parent().map(Path::to_path_buf);
        }
        None
    }

    // frob:ticket 01M4CTTRCCJMVJDYVEJZWTT8J3
    /// The repo-relative directory cargo must run in for the package owning `file`: the nearest enclosing `[workspace]` root, else the package directory (empty at the repository root).
    pub fn cargo_root(&mut self, file: &str) -> Option<PathBuf> {
        let mut dir = Path::new(file).parent().map(Path::to_path_buf);
        let pkg_dir = loop {
            let d = dir?;
            if let Some((_, pkg_dir)) = self.package_at(&d) {
                break pkg_dir;
            }
            dir = d.parent().map(Path::to_path_buf);
        };
        let workspace = pkg_dir.ancestors().find(|a| {
            std::fs::read_to_string(self.root.join(a).join("Cargo.toml"))
                .ok()
                .and_then(|t| t.parse::<toml::Table>().ok())
                .is_some_and(|t| t.contains_key("workspace"))
        });
        Some(workspace.map_or_else(|| pkg_dir.clone(), Path::to_path_buf))
    }

    fn package_at(&mut self, dir: &Path) -> Option<(String, PathBuf)> {
        if let Some(hit) = self.cache.get(dir) {
            return hit.clone();
        }
        let manifest = self.root.join(dir).join("Cargo.toml");
        let found = std::fs::read_to_string(&manifest)
            .ok()
            .and_then(|t| t.parse::<toml::Table>().ok())
            .and_then(|t| {
                t.get("package")?
                    .get("name")?
                    .as_str()
                    .map(|n| (n.to_owned(), dir.to_path_buf()))
            });
        tracing::trace!(manifest = %manifest.display(), found = ?found, "package lookup");
        self.cache.insert(dir.to_path_buf(), found.clone());
        found
    }
}

/// The nextest test name of `rec` inside a package (`tests::doubles`, or `integration_quad`).
pub fn test_name(rec: &SymbolRecord, path_in_package: &Path) -> String {
    let mut parts = module_prefix(path_in_package);
    parts.extend(rec.symref.segments().iter().cloned());
    parts.join("::")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn attributes_are_recognised_by_last_segment() {
        for ok in [
            "#[test]",
            "#[tokio::test]",
            "#[tokio::test(flavor = \"x\")]",
            "#[rstest]",
            "#[test_case(1)]",
        ] {
            assert!(is_test_attribute(ok), "{ok}");
        }
        for no in [
            "#[cfg(test)]",
            "#[derive(Debug)]",
            "#[allow(dead_code)]",
            "// #[test]",
        ] {
            assert!(!is_test_attribute(no), "{no}");
        }
    }

    #[test]
    fn module_prefixes_follow_cargo_layout() {
        let p = |s: &str| module_prefix(Path::new(s));
        assert!(p("src/lib.rs").is_empty());
        assert!(p("src/main.rs").is_empty());
        assert_eq!(p("src/a/b.rs"), ["a", "b"]);
        assert_eq!(p("src/a/mod.rs"), ["a"]);
        assert!(p("tests/it.rs").is_empty());
        assert!(p("src/bin/tool.rs").is_empty());
    }

    #[test]
    // frob:ticket 01M4828JB2S4JZY2QRB97A7SXX
    // frob:tests crates/frob-tests/src/catalog.rs::is_test_fn
    fn typescript_test_units_are_tests() {
        use gob_walk::{Digest, FileEntry, LanguageHint};
        let src = "describe('x', () => { it('adds', () => {}); });\nfunction helper() {}\n";
        let path = "src/a.test.ts";
        let entry = FileEntry {
            path: path.to_owned(),
            size: src.len() as u64,
            digest: Digest::of(src.as_bytes()),
            language: LanguageHint::from_path(path),
        };
        let file = gob_symbols::extract_file(&entry, src);
        let tests: Vec<String> = file
            .symbols
            .iter()
            .filter(|r| is_test_fn(r, None))
            .map(|r| r.symref.to_string())
            .collect();
        assert_eq!(
            tests,
            ["src/a.test.ts::suite$x", "src/a.test.ts::suite$x.test$adds"]
        );
        assert!(is_test_file(path));
    }
}
