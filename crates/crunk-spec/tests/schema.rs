//! The JSON Schema and reference page generated from the table types.

// frob:ticket 01M43ARX764095Q4VWABWXXV5H

use crunk_spec::schema::{reference, schema};
use serde_json::Value;

// frob:tests crates/crunk-spec/src/schema.rs::schema
#[test]
fn schema_describes_every_table_and_rejects_unknown_keys() {
    let schema = schema();
    assert_eq!(
        schema["$schema"],
        "https://json-schema.org/draft/2020-12/schema"
    );
    let props = schema["properties"].as_object().unwrap();
    for table in crunk_spec::OWN_TABLES {
        assert!(props.contains_key(*table), "schema lacks [{table}]");
    }
    let project = &props["project"];
    assert_eq!(project["additionalProperties"], false);
    assert_eq!(
        project["required"],
        serde_json::json!(["css_root", "tokens_file", "root_font_size"])
    );
    assert!(project["properties"]["css_root"]["description"].is_string());
    let lint = &props["lint"];
    assert!(lint["properties"]["COLOR001"]["enum"].is_array());
    assert_eq!(lint["additionalProperties"], false);
    assert_eq!(
        props["lint"]["properties"]["fix_tolerance"]["default"],
        0.15
    );
}

// frob:tests crates/crunk-spec/src/schema.rs::reference
#[test]
fn reference_page_has_a_section_per_table_and_a_row_per_key() {
    let page = reference();
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
        assert!(page.contains(heading), "reference lacks {heading}\n{page}");
    }
    assert!(page.contains("| `css_root` | string | yes |"));
    assert!(
        page.contains("| `class_case` | `kebab` or `snake` or `camel` | no | `\"kebab\"` |"),
        "{page}"
    );
    assert!(page.is_ascii(), "reference must be ASCII");
    let again = reference();
    assert_eq!(page, again, "deterministic");
    let _: Value = crunk_spec::schema::schema();
}
