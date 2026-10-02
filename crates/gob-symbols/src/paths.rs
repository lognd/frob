//! Mapping repo-relative Rust file paths to crate directories and module paths.

/// Splits `path` into `(crate_dir, module_path_segments)`.
///
/// The crate dir is everything before the first `src` directory (empty when
/// there is none); the module path follows from the components after it
/// (`lib.rs`/`main.rs` at the crate root and `mod.rs` contribute nothing).
pub fn crate_and_module(path: &str) -> (String, Vec<String>) {
    let comps: Vec<&str> = path.split('/').collect();
    let dirs = comps.len().saturating_sub(1);
    let src = comps[..dirs].iter().position(|c| *c == "src");
    let (crate_dir, rel) = match src {
        Some(i) => (comps[..i].join("/"), &comps[i + 1..]),
        None => (String::new(), &comps[..]),
    };
    let mut segs: Vec<String> = rel.iter().map(|s| (*s).to_owned()).collect();
    if let Some(last) = segs.pop() {
        let stem = last.rsplit_once('.').map_or(last.as_str(), |(s, _)| s);
        let drop = stem == "mod" || (segs.is_empty() && (stem == "lib" || stem == "main"));
        if !drop {
            segs.push(stem.to_owned());
        }
    }
    (crate_dir, segs)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cm(p: &str) -> (String, String) {
        let (c, m) = crate_and_module(p);
        (c, m.join("::"))
    }

    #[test]
    fn module_paths() {
        assert_eq!(
            cm("crates/x/src/lib.rs"),
            ("crates/x".into(), String::new())
        );
        assert_eq!(
            cm("crates/x/src/a/b.rs"),
            ("crates/x".into(), "a::b".into())
        );
        assert_eq!(cm("crates/x/src/a/mod.rs"), ("crates/x".into(), "a".into()));
        assert_eq!(cm("src/main.rs"), (String::new(), String::new()));
        assert_eq!(cm("tests/t.rs"), (String::new(), "tests::t".into()));
    }
}
