//! `docs/reference/languages.md`: the adapter extension table and capability matrices.

// frob:ticket 01M48FXFZMWWZQ233HYSPZ6PP9

use super::md_header;
use crate::files::GenFile;

/// Repository path of the generated languages page.
const PATH: &str = "docs/reference/languages.md";

/// The languages page, `gob_symbols::languages_page` under the standard generated marker.
pub fn generate() -> Vec<GenFile> {
    tracing::debug!(path = PATH, "rendering languages page");
    vec![GenFile {
        path: PATH.to_owned(),
        content: format!(
            "{}\n{}",
            md_header("languages"),
            gob_symbols::languages_page()
        ),
    }]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    // frob:tests crates/gob-dev/src/render/languages.rs::generate
    fn emits_the_symbols_page_under_a_valid_marker() {
        let files = generate();
        assert_eq!(files.len(), 1);
        assert_eq!(files[0].path, PATH);
        assert!(files[0].content.ends_with(&gob_symbols::languages_page()));
        assert_eq!(crate::files::marker_problem(&files[0].content), None);
    }
}
