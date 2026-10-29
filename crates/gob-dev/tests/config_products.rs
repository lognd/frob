//! Product-scoped config pages and schemas: each product gets its own, with only its own keys.

// frob:ticket 01M43MPG53JR8TP0E15394FZ5T

use gob_config::{product_config_schema, product_tables};
use gob_dev::render::config::{generate, page_path, render};
use gob_dev::render::schemas::schema_path;

/// Touch crunk-spec so the linker keeps its table registrations.
fn crunk_page() -> String {
    assert!(!crunk_spec::OWN_TABLES.is_empty());
    let tables: Vec<_> = product_tables("crunk").collect();
    render("crunk", &tables)
}

// frob:tests crates/gob-dev/src/render/config.rs::render
#[test]
fn crunk_page_has_a_section_per_table_and_a_row_per_key() {
    let page = crunk_page();
    for heading in [
        "## `[project]`",
        "## `[palette]`",
        "## `[scales]`",
        "## `[typography]`",
        "## `[org]`",
        "## `[lint]`",
        "## `[tokens]`",
        "## `[tokens.prefixes]`",
        "## `[tailwind]`",
        "## `[breakpoints]`",
        "## `[[platform]]`",
        "## `[[screen]]`",
        "## `[[screen.states]]`",
        "## `[[session]]`",
    ] {
        assert!(page.contains(heading), "page lacks {heading}\n{page}");
    }
    assert!(page.contains("| `css_root` | `String` | yes |"), "{page}");
    assert!(page.contains("Path-base law"), "{page}");
    assert!(page.is_ascii(), "page must be ASCII");
    assert_eq!(page, crunk_page(), "deterministic");
}

// frob:tests crates/gob-dev/src/render/config.rs::generate
#[test]
fn every_product_gets_its_own_page_and_schema_path() {
    assert!(!crunk_page().is_empty());
    let files = generate();
    let crunk = files
        .iter()
        .find(|f| f.path == page_path("crunk"))
        .expect("crunk page generated");
    assert_eq!(crunk.path, "docs/crunk/config.md");
    assert_eq!(schema_path("crunk"), "docs/schemas/crunk.json");
    assert_eq!(page_path("frob"), "docs/reference/config.md");
    assert_eq!(schema_path("frob"), "docs/schemas/config.json");
    for other in files.iter().filter(|f| f.path != crunk.path) {
        assert!(
            !other.content.contains("css_root"),
            "{} leaked a crunk key",
            other.path
        );
    }
    let schema = product_config_schema("crunk").to_string();
    assert!(schema.contains("css_root"));
}
