//! `docs/reference/grl/catalog.md`: the GRL relation catalog, rendered by the engine's own tables.

// frob:ticket 01M3ZX7DT0J6MRW68P60GAYD3N
use super::md_header;
use crate::files::GenFile;

/// The catalog page: a generated-file header over [`gob_plan::catalog::render`].
pub fn render() -> String {
    let mut out = md_header("rules");
    out.push('\n');
    out.push_str(&gob_plan::catalog::render());
    out
}

/// The catalog page as a generated file, so GEN001 keeps it current.
pub fn generate() -> Vec<GenFile> {
    vec![GenFile {
        path: "docs/reference/grl/catalog.md".to_owned(),
        content: render(),
    }]
}
