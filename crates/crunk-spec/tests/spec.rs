//! Port of the Python `tests/unit/test_spec.py` and INT-01: loading, validation, defaults and
//! the path-base law.

// frob:ticket 01M43ARX764095Q4VWABWXXV5H

mod common;

use std::path::{Path, PathBuf};

use common::{detail, err, full, line_of, load, ok, swap, with};
use crunk_spec::table::{Action, ClassCase, OrgModel, TailwindVersion};
use crunk_spec::{
    DesignSpec, Severity, SpecError, SpecErrorKind, catalog, load_spec, load_spec_file, naming,
};
use gob_diagnostics::ExitCode;

// frob:tests crates/crunk-spec/src/load.rs::load_spec
#[test]
fn full_example_loads_every_field() {
    let spec = ok(full());
    assert_eq!(spec.project.css_root, "styles");
    assert_eq!(spec.project.tokens_file, "tokens.css");
    assert!((spec.project.root_font_size - 16.0).abs() < f64::EPSILON);
    assert_eq!(
        spec.palette.keys().collect::<Vec<_>>(),
        ["ink", "paper", "accent"],
        "palette keeps declaration order"
    );
    assert_eq!(spec.roles["body"].foreground, "ink");
    assert_eq!(spec.roles["body"].background, "paper");
    assert!(spec.scales.spacing[0].abs() < f64::EPSILON);
    assert_eq!(
        spec.typography.families,
        ["Inter", "system-ui", "sans-serif"]
    );
    assert_eq!(spec.layers["dropdown"], 100);
    assert_eq!(spec.org.class_case, ClassCase::Kebab);
    assert!((spec.lint.fix_tolerance - 0.15).abs() < f64::EPSILON);
    assert!((spec.lint.color_tolerance - 8.0).abs() < f64::EPSILON);
    assert_eq!(spec.tokens_path(), Path::new("/proj/styles/tokens.css"));
    assert_eq!(spec.css_root(), Path::new("/proj/styles"));
}

// frob:tests crates/crunk-spec/src/error.rs::SpecError.code
// frob:tests crates/crunk-spec/src/error.rs::SpecError.class
// frob:tests crates/crunk-spec/src/error.rs::SpecError.exit_code
// frob:tests crates/crunk-spec/src/error.rs::SpecError.kind
#[test]
fn missing_file_is_missing_with_exit_3() {
    let dir = tempfile::tempdir().unwrap();
    let e = load_spec(dir.path()).unwrap_err();
    assert_eq!(e.kind(), SpecErrorKind::Missing);
    assert_eq!(e.code(), "E-NO-CONFIG");
    assert_eq!(e.exit_code(), ExitCode::Refused);
}

#[test]
fn load_spec_reads_the_file_at_root() {
    let dir = tempfile::tempdir().unwrap();
    std::fs::write(dir.path().join("crunk.toml"), full()).unwrap();
    let spec = load_spec(dir.path()).unwrap();
    assert_eq!(spec.root, dir.path());
    let other = dir.path().join("other.toml");
    std::fs::write(&other, full()).unwrap();
    assert!(load_spec_file(&other, Path::new("/elsewhere")).is_ok());
    let missing = load_spec_file(&dir.path().join("nope.toml"), dir.path()).unwrap_err();
    assert_eq!(missing.kind(), SpecErrorKind::Missing);
}

// frob:tests crates/crunk-spec/src/error.rs::SpecError.location
#[test]
fn bad_toml_syntax_is_malformed_with_a_line() {
    let e = err("[project\ncss_root = 'styles'\n");
    assert_eq!(e.kind(), SpecErrorKind::Malformed);
    assert_eq!(e.exit_code(), ExitCode::Usage);
    assert_eq!(e.location().map(|l| l.line), Some(1));
    assert!(e.to_string().starts_with("crunk.toml:1:"), "{e}");
}

// frob:tests crates/crunk-spec/src/error.rs::SpecError
#[test]
fn unknown_top_level_key_names_key_line_and_suggestion() {
    let e = err(&with("[projet]\nx = 1"));
    assert_eq!(e.kind(), SpecErrorKind::Invalid);
    assert_eq!(e.key(), Some("projet"));
    assert_eq!(e.suggestion(), Some("project"));
    assert_eq!(e.exit_code(), ExitCode::Usage);
    let line = full().lines().count() + 2;
    assert_eq!(e.location().map(|l| l.line), Some(line), "{e}");
    assert!(e.to_string().contains("did you mean `project`?"), "{e}");
}

// frob:tests crates/crunk-spec/src/error.rs::SpecError
// frob:tests crates/crunk-spec/src/error.rs::SpecError.key
// frob:tests crates/crunk-spec/src/error.rs::SpecError.suggestion
#[test]
fn unknown_key_in_a_section_names_key_line_and_suggestion() {
    let e = err(&swap("css_root = \"styles\"", "css_rot = \"styles\""));
    assert_eq!(e.key(), Some("css_rot"));
    assert_eq!(e.suggestion(), Some("css_root"));
    assert_eq!(e.location().map(|l| l.line), Some(2));
    assert!(detail(&e).starts_with("[project]"), "{}", detail(&e));
    assert_eq!(e.exit_code(), ExitCode::Usage);
}

#[test]
fn unknown_key_without_a_close_match_has_no_suggestion() {
    let e = err(&swap(
        "css_root = \"styles\"",
        "zzzzzzzzzzzz = 1\ncss_root = \"styles\"",
    ));
    assert_eq!(e.key(), Some("zzzzzzzzzzzz"));
    assert_eq!(e.suggestion(), None);
}

#[test]
fn unknown_key_inside_every_fixed_table_is_rejected() {
    for table in ["scales", "typography", "org", "jsx", "tailwind", "tokens"] {
        let text = if table == "scales" || table == "typography" || table == "org" {
            swap(&format!("[{table}]\n"), &format!("[{table}]\nbogus = 1\n"))
        } else {
            with(&format!("[{table}]\nbogus = 1"))
        };
        let e = err(&text);
        assert_eq!(e.key(), Some("bogus"), "[{table}]");
        assert!(
            detail(&e).starts_with(&format!("[{table}]")),
            "{}",
            detail(&e)
        );
    }
}

#[test]
fn unparseable_palette_color_names_the_key() {
    let e = err(&swap("ink = \"#1a1a1a\"", "ink = \"not-a-color\""));
    assert!(detail(&e).contains("[palette].ink"), "{}", detail(&e));
    assert_eq!(
        e.location().map(|l| l.line),
        Some(line_of(
            &swap("ink = \"#1a1a1a\"", "ink = \"not-a-color\""),
            "not-a-color"
        ))
    );
}

#[test]
fn palette_value_must_be_a_string() {
    let e = err(&swap("ink = \"#1a1a1a\"", "ink = 5"));
    assert!(detail(&e).contains("color literal must be a string"));
}

#[test]
fn empty_palette_is_legal() {
    let text = "[palette]\n\n[project]\ncss_root = \"s\"\ntokens_file = \"t.css\"\nroot_font_size = 16\n\n[scales]\nspacing = [1]\nfont_sizes = [1]\n\n[typography]\nfamilies = [\"x\"]\nweights = [400]\n\n[org]\nbuckets = [\"b\"]\n";
    assert!(ok(text).palette.is_empty());
}

#[test]
fn unsorted_scale_names_the_offender() {
    let e = err(&swap(
        "spacing = [0, 4, 8, 12, 16, 24, 32, 48, 64]",
        "spacing = [0, 8, 4]",
    ));
    assert!(detail(&e).contains("[scales].spacing"), "{}", detail(&e));
    assert!(detail(&e).contains("not strictly ascending"));
}

#[test]
fn empty_required_scale_is_rejected() {
    let e = err(&swap(
        "font_sizes = [12, 14, 16, 20, 24, 32, 48]",
        "font_sizes = []",
    ));
    assert!(detail(&e).contains("[scales].font_sizes"));
}

#[test]
fn sizes_and_radii_validate_only_when_declared() {
    let spec = ok(&swap("radii = [0, 4, 8, 16]", "radii = []"));
    assert!(spec.scales.radii.is_empty() && spec.scales.sizes.is_empty());
    let e = err(&swap("radii = [0, 4, 8, 16]", "radii = [4, 4]"));
    assert!(detail(&e).contains("[scales].radii"));
    let e = err(&swap(
        "radii = [0, 4, 8, 16]",
        "radii = [0]\nsizes = [8, 4]",
    ));
    assert!(detail(&e).contains("[scales].sizes"));
}

#[test]
fn dangling_role_reference_is_invalid() {
    let e = err(&swap(
        "body = [\"ink\", \"paper\"]",
        "body = [\"ink\", \"ghost\"]",
    ));
    assert!(detail(&e).contains("[palette.roles].body"));
    assert!(detail(&e).contains("`ghost` is not a declared palette name"));
}

#[test]
fn role_pair_floor_defaults_and_extended_form() {
    let spec = ok(full());
    assert!((spec.roles["body"].floor - catalog::CONTRAST_AA_FLOOR).abs() < f64::EPSILON);
    let spec = ok(&swap(
        "body = [\"ink\", \"paper\"]",
        "body = { pair = [\"ink\", \"paper\"], floor = 3 }",
    ));
    assert!((spec.roles["body"].floor - 3.0).abs() < f64::EPSILON);
}

#[test]
fn malformed_roles_name_the_role() {
    for (value, needle) in [
        (
            "{ pair = [\"ink\", \"paper\"], floor = \"x\" }",
            "floor must be a number",
        ),
        (
            "{ pair = [\"ink\", \"paper\"], floor = 0 }",
            "floor must be > 0",
        ),
        ("{ floor = 3 }", "table form needs `pair`"),
        (
            "{ pair = [\"ink\", \"paper\"], flor = 3 }",
            "unknown key `flor`",
        ),
        ("\"ink\"", "must be a [foreground, background] pair or"),
        ("[\"ink\"]", "must be a [foreground, background] pair"),
        ("[\"ink\", 1]", "names must be strings"),
    ] {
        let e = err(&swap(
            "body = [\"ink\", \"paper\"]",
            &format!("body = {value}"),
        ));
        assert!(
            detail(&e).contains("[palette.roles") && detail(&e).contains("body"),
            "{value}: {}",
            detail(&e)
        );
        assert!(detail(&e).contains(needle), "{value}: {}", detail(&e));
    }
    let e = err(&swap(
        "body = [\"ink\", \"paper\"]",
        "body = { pair = [\"ink\", \"paper\"], flor = 3 }",
    ));
    assert_eq!(e.suggestion(), Some("floor"));
}

#[test]
fn roles_must_be_a_table() {
    let text = swap("[palette.roles]\nbody = [\"ink\", \"paper\"]\n", "");
    let text = swap_in(&text, "[palette]\n", "[palette]\nroles = 3\n");
    assert!(detail(&err(&text)).contains("[palette].roles"));
}

fn swap_in(text: &str, from: &str, to: &str) -> String {
    assert!(text.contains(from));
    text.replacen(from, to, 1)
}

#[test]
fn layers_are_optional_ints() {
    let text = swap(
        "[layers]\nbase = 0\ndropdown = 100\noverlay = 200\ntoast = 300\n",
        "",
    );
    assert!(ok(&text).layers.is_empty());
    let e = err(&swap("base = 0", "base = \"zero\""));
    assert_eq!(
        e.location().map(|l| l.line),
        Some(line_of(full(), "base = 0")),
        "{e}"
    );
}

// frob:tests crates/crunk-spec/src/model.rs::DesignSpec.severity
#[test]
fn lint_catalog_and_overrides() {
    let spec = ok(full());
    assert_eq!(spec.severity("SPACE001"), Severity::Warn, "override");
    assert_eq!(
        spec.severity("COLOR001"),
        Severity::Error,
        "catalog default"
    );
    assert_eq!(
        spec.severity("TW003"),
        Severity::Warn,
        "catalog warn default"
    );
    assert_eq!(
        spec.severity("NOPE999"),
        Severity::Error,
        "unknown falls back to error"
    );
    let spec = ok(&swap("SPACE001 = \"warn\"", "SPACE001 = \"off\""));
    assert_eq!(spec.severity("SPACE001"), Severity::Off);
}

#[test]
fn lint_errors_are_located() {
    let e = err(&swap("SPACE001 = \"warn\"", "SPACE01 = \"warn\""));
    assert_eq!(e.key(), Some("SPACE01"));
    assert_eq!(e.suggestion(), Some("SPACE001"));
    assert!(detail(&e).contains("unknown rule id"));
    let e = err(&swap("SPACE001 = \"warn\"", "SPACE001 = \"loud\""));
    assert!(detail(&e).contains("severity must be error/warn/off"));
    let e = err(&swap("fix_tolerance = 0.15", "fix_tolerance = 1.5"));
    assert!(detail(&e).contains("fix_tolerance"));
    let e = err(&swap("fix_tolerance = 0.15", "fix_tolerance = 0"));
    assert!(detail(&e).contains("fix_tolerance"));
    let e = err(&swap("color_tolerance = 8.0", "color_tolerance = 0"));
    assert!(detail(&e).contains("color_tolerance"));
}

#[test]
fn lint_absent_defaults() {
    let text = swap(
        "[lint]\nSPACE001 = \"warn\"\nfix_tolerance = 0.15\ncolor_tolerance = 8.0\n",
        "",
    );
    let spec = ok(&text);
    assert!(spec.lint.rules.is_empty());
    assert!((spec.lint.fix_tolerance - 0.15).abs() < f64::EPSILON);
    assert!((spec.lint.color_tolerance - 8.0).abs() < f64::EPSILON);
}

#[test]
fn org_values_and_defaults() {
    let spec = ok(&swap("class_case = \"kebab\"", "class_case = \"camel\""));
    assert_eq!(spec.org.class_case, ClassCase::Camel);
    assert_eq!(spec.org.model, OrgModel::Buckets);
    assert!(spec.org.ignore.is_empty() && spec.org.entry.is_empty());
    let e = err(&swap("class_case = \"kebab\"", "class_case = \"pascal\""));
    assert!(e.key().is_none());
    assert_eq!(
        e.location().map(|l| l.line),
        Some(line_of(full(), "class_case")),
        "{e}"
    );
    let spec = ok(&with("[org2]\n").replace("[org2]\n", ""));
    assert!(spec.org.component_prefix && spec.org.tokens_only_custom_props);
    let spec = ok(&swap(
        "class_case = \"kebab\"",
        "model = \"utility-first\"\nignore = [\"a\"]\nentry = [\"b\"]",
    ));
    assert_eq!(spec.org.model, OrgModel::UtilityFirst);
    assert_eq!(spec.org.ignore, ["a"]);
    assert_eq!(spec.org.entry, ["b"]);
    assert!(
        err(&swap("class_case = \"kebab\"", "model = \"flat\""))
            .location()
            .is_some()
    );
}

#[test]
fn missing_required_section_is_named() {
    for section in ["project", "palette", "scales", "typography", "org"] {
        let start = full().find(&format!("[{section}]")).unwrap();
        let rest = &full()[start + 1..];
        let end = rest.find("\n[").map_or(full().len(), |i| start + 1 + i + 1);
        let mut text = full().to_owned();
        text.replace_range(start..end, "");
        if section == "palette" {
            text = text.replace("[palette.roles]\nbody = [\"ink\", \"paper\"]\n", "");
        }
        let e = err(&text);
        assert!(
            detail(&e).contains(&format!("missing required section [{section}]")),
            "{section}: {}",
            detail(&e)
        );
    }
}

#[test]
fn section_of_the_wrong_shape_is_invalid() {
    let text = swap("[project]\n", "project = 3\n[projectx]\n");
    assert_eq!(err(&text).kind(), SpecErrorKind::Invalid);
}

#[test]
fn typography_validation() {
    let e = err(&swap("weights = [400, 500, 700]", "weights = []"));
    assert!(detail(&e).contains("[typography].weights"));
    let e = err(&swap(
        "families = [\"Inter\", \"system-ui\", \"sans-serif\"]",
        "families = []",
    ));
    assert!(detail(&e).contains("[typography].families"));
}

#[test]
fn stacks_default_empty_match_case_insensitively_and_reject_strangers() {
    assert!(ok(full()).typography.stacks.is_empty());
    let spec = ok(&with(
        "[typography.stacks]\nsans = [\"inter\", \"SYSTEM-UI\"]",
    ));
    assert_eq!(spec.typography.stacks["sans"], ["inter", "SYSTEM-UI"]);
    let e = err(&with("[typography.stacks]\nsans = [\"Comic\"]"));
    assert!(detail(&e).contains("[typography.stacks].sans"));
    assert!(detail(&e).contains("not in declared families"));
    let e = err(&with("[typography.stacks]\nsans = []"));
    assert!(detail(&e).contains("must not be empty"));
}

#[test]
fn tokens_defaults_and_prefix_rules() {
    let spec = ok(full());
    assert_eq!(spec.tokens.color, "color");
    assert_eq!(spec.tokens.space, "space");
    assert_eq!(spec.tokens.font_size, "font-size");
    assert_eq!(spec.tokens.radius, "radius");
    assert_eq!(spec.tokens.layer, "layer");
    assert_eq!(spec.tokens.font_family, "font-family");
    assert_eq!(spec.tokens.size, "size");
    assert_eq!(spec.tokens.header, "");
    assert_eq!(spec.tokens.json_file, "");
    let e = err(&with("[tokens.prefixes]\ncolor = \"Bad_Prefix\""));
    assert!(detail(&e).contains("[tokens.prefixes].color"));
    for key in ["space", "font_size", "radius", "size"] {
        let e = err(&with(&format!("[tokens.prefixes]\n{key} = \"\"")));
        assert!(detail(&e).contains("prefix must not be empty"), "{key}");
    }
    let spec = ok(&with(
        "[tokens.prefixes]\ncolor = \"\"\nlayer = \"\"\nfont_family = \"\"",
    ));
    assert_eq!(naming::color_token(&spec.tokens, "ink"), "--ink");
    let e = err(&with("[tokens]\nbogus = 1"));
    assert_eq!(e.key(), Some("bogus"));
    let e = err(&with("[tokens]\nprefixes = { colour = \"c\" }"));
    assert_eq!(e.suggestion(), Some("color"));
}

#[test]
fn tokens_header_and_json_file() {
    let spec = ok(&with(
        "[tokens]\nheader = \"/* keep */\"\njson_file = \"tokens.json\"",
    ));
    assert_eq!(spec.tokens.header, "/* keep */");
    assert_eq!(spec.tokens.json_file, "tokens.json");
    for (header, needle) in [
        ("bare", "must start with '/*'"),
        ("/* open", "must end with '*/'"),
        ("/* a */ b */", "interior '*/'"),
    ] {
        let e = err(&with(&format!("[tokens]\nheader = \"{header}\"")));
        assert!(detail(&e).contains(needle), "{header}: {}", detail(&e));
    }
}

#[test]
fn jsx_and_tailwind_defaults_and_values() {
    let spec = ok(full());
    assert!(spec.jsx.globs.is_empty());
    assert_eq!(spec.tailwind.config, "");
    assert_eq!(spec.tailwind.tokens_file, "");
    assert!(!spec.tailwind.namespace_keys && !spec.tailwind.alpha_channels);
    assert_eq!(spec.tailwind.version, TailwindVersion::Auto);
    let spec = ok(&with(
        "[jsx]\nglobs = [\"src/**/*.tsx\"]\n[tailwind]\nconfig = \"tw.config.ts\"\ntokens_file = \"tw.json\"\nnamespace_keys = true\nalpha_channels = true\nversion = \"v4\"\ncss_entry = \"a.css\"",
    ));
    assert_eq!(spec.jsx.globs, ["src/**/*.tsx"]);
    assert!(spec.tailwind.namespace_keys && spec.tailwind.alpha_channels);
    assert_eq!(spec.tailwind.version, TailwindVersion::V4);
    assert_eq!(spec.tailwind.css_entry, "a.css");
    assert!(load(&with("[tailwind]\nversion = \"v9\"")).is_err());
}

// frob:tests crates/crunk-spec/src/model.rs::tokens_path
#[test]
fn path_base_law_project_file_keys_resolve_against_css_root_others_against_root() {
    let spec = ok(&with(
        "[tailwind]\nconfig = \"tw/tailwind.config.ts\"\ntokens_file = \"tailwind.tokens.json\"\n[tokens]\njson_file = \"out/tokens.json\"",
    ));
    // [project] tokens_file: against css_root.
    assert_eq!(spec.tokens_path(), PathBuf::from("/proj/styles/tokens.css"));
    // Every other *_file key: against the project root, never css_root.
    assert_eq!(
        spec.tailwind_tokens_path(),
        Some(PathBuf::from("/proj/tailwind.tokens.json"))
    );
    assert_eq!(
        spec.json_tokens_path(),
        Some(PathBuf::from("/proj/out/tokens.json"))
    );
    assert_eq!(
        spec.tailwind_config_path(),
        Some(PathBuf::from("/proj/tw/tailwind.config.ts"))
    );
    // Unset keys have no path.
    let bare = ok(full());
    assert_eq!(bare.tailwind_tokens_path(), None);
    assert_eq!(bare.json_tokens_path(), None);
    assert_eq!(bare.tailwind_config_path(), None);
}

#[test]
fn paths_collapse_dot_segments_lexically() {
    let spec = ok(&swap(
        "css_root = \"styles\"",
        "css_root = \"./a/../styles\"",
    ));
    assert_eq!(spec.css_root(), PathBuf::from("/proj/styles"));
    let spec = ok(&swap(
        "tokens_file = \"tokens.css\"",
        "tokens_file = \"../up.css\"",
    ));
    assert_eq!(spec.tokens_path(), PathBuf::from("/proj/up.css"));
}

#[test]
fn preset_comments_state_the_path_base_rule() {
    for (name, text) in crunk_spec::presets::PRESETS {
        assert!(text.contains("resolves against css_root"), "{name}");
        assert!(text.contains("project root"), "{name}");
        assert!(ok(text).palette.contains_key("ink"), "{name} must load");
    }
    assert_eq!(crunk_spec::presets::preset_names(), ["default", "mono"]);
    assert!(crunk_spec::presets::preset("nope").is_none());
}

#[test]
fn breakpoints_precedence() {
    // Absent, no tailwind: BP off.
    let spec = ok(full());
    assert!(spec.breakpoints.points.is_empty() && spec.breakpoints.base_required.is_empty());
    // Absent, tailwind declared: v3 defaults.
    let spec = ok(&with("[tailwind]\nconfig = \"tailwind.config.ts\""));
    assert_eq!(
        spec.breakpoints
            .points
            .iter()
            .map(|(k, v)| (k.as_str(), *v))
            .collect::<Vec<_>>(),
        [
            ("sm", 640),
            ("md", 768),
            ("lg", 1024),
            ("xl", 1280),
            ("2xl", 1536)
        ]
    );
    assert_eq!(
        spec.breakpoints.base_required,
        catalog::DEFAULT_BASE_REQUIRED
    );
    // Declared wins, keeping base_required split off.
    let spec = ok(&with(
        "[tailwind]\nconfig = \"tailwind.config.ts\"\n[breakpoints]\nsm = 600\nmd = 900\nbase_required = [\"flex\", \"w-\"]",
    ));
    assert_eq!(spec.breakpoints.points.len(), 2);
    assert_eq!(spec.breakpoints.points["sm"], 600);
    assert_eq!(spec.breakpoints.base_required, ["flex", "w-"]);
    // Declared without base_required: documented default list.
    let spec = ok(&with("[breakpoints]\nsm = 600"));
    assert_eq!(
        spec.breakpoints.base_required,
        catalog::DEFAULT_BASE_REQUIRED
    );
    // Bad values.
    assert!(detail(&err(&with("[breakpoints]\nsm = \"wide\""))).contains("integer px"));
    assert!(detail(&err(&with("[breakpoints]\nsm = 6.5"))).contains("integer px"));
    assert!(detail(&err(&with("[breakpoints]\nbase_required = [1]"))).contains("list of strings"));
}

// frob:tests crates/crunk-spec/src/catalog.rs::Severity.as_str
// frob:tests crates/crunk-spec/src/catalog.rs::Severity.parse
#[test]
fn catalog_rows() {
    let ids = catalog::rule_ids();
    assert_eq!(ids.len(), 30);
    assert!(ids.contains(&"SIZE001".to_owned()));
    assert_eq!(catalog::default_severity("SIZE001"), Some(Severity::Warn));
    for id in ["BP001", "BP002", "BP003"] {
        assert_eq!(catalog::default_severity(id), Some(Severity::Error));
    }
    assert_eq!(
        catalog::default_severity("GALLERY005"),
        Some(Severity::Warn)
    );
    assert!(catalog::is_rule_id("TW005") && !catalog::is_rule_id("TW006"));
    assert_eq!(Severity::parse("warn"), Some(Severity::Warn));
    assert_eq!(Severity::Off.to_string(), "off");
}

fn gallery(extra: &str) -> String {
    with(&format!(
        "[[platform]]\nid = \"desk\"\nrenderer = \"web\"\nengine = \"chromium\"\nviewport = {{ width = 1280, height = 800 }}\ntags = [\"d\"]\n\n[[platform]]\nid = \"mob\"\nrenderer = \"web\"\nengine = \"webkit\"\nviewport = {{ width = 390, height = 844 }}\ntags = [\"m\"]\n\n{extra}"
    ))
}

#[test]
fn screens_and_platforms_absent_default_empty() {
    let spec: DesignSpec = ok(full());
    assert!(spec.platforms.is_empty() && spec.screens.is_empty());
    assert!(spec.sessions.is_empty() && spec.mock_sets.is_empty());
}

#[test]
fn web_and_command_platforms_resolve_defaults() {
    let spec = ok(&gallery(
        "[[platform]]\nid = \"cmd\"\nrenderer = \"command\"\ncommand = \"run\"\n",
    ));
    let json = serde_json::to_value(&spec.platforms).unwrap();
    assert_eq!(json["desk"]["params"]["device_scale"], 1.0);
    assert_eq!(json["desk"]["params"]["settle_ms"], 500);
    assert_eq!(json["desk"]["params"]["java_script_enabled"], true);
    assert_eq!(
        json["desk"]["params"]["media"]["color_scheme"],
        "no-preference"
    );
    assert_eq!(
        json["desk"]["params"]["cpu_throttle"],
        serde_json::Value::Null
    );
    assert_eq!(json["cmd"]["params"]["command"], "run");
    assert_eq!(json["cmd"]["params"]["env"], serde_json::json!({}));
    assert_eq!(
        spec.platforms.keys().collect::<Vec<_>>(),
        ["desk", "mob", "cmd"]
    );
}

#[test]
fn platform_errors_are_named_and_located() {
    let e = err(&with("[[platform]]\nid = \"a\"\nrenderer = \"wbe\"\n"));
    assert!(
        detail(&e).contains("unknown renderer id `wbe`"),
        "{}",
        detail(&e)
    );
    assert_eq!(e.suggestion(), Some("web"));
    assert!(e.location().is_some());
    let dup = "[[platform]]\nid = \"a\"\nrenderer = \"command\"\ncommand = \"x\"\n";
    let e = err(&with(&format!("{dup}\n{dup}")));
    assert!(detail(&e).contains("duplicate platform id `a`"));
    let e = err(&with(
        "[[platform]]\nid = \"a\"\nrenderer = \"web\"\nviewport = { width = 1, height = 1 }\n",
    ));
    assert!(detail(&e).contains("requires `engine`"));
    let e = err(&with(
        "[[platform]]\nid = \"a\"\nrenderer = \"web\"\nengine = \"opera\"\nviewport = { width = 1, height = 1 }\n",
    ));
    assert!(e.location().is_some(), "{e}");
    let e = err(&with(
        "[[platform]]\nid = \"a\"\nrenderer = \"web\"\nengine = \"webkit\"\ncommand = \"x\"\nviewport = { width = 1, height = 1 }\n",
    ));
    assert!(detail(&e).contains("`command` is not a key of the `web` renderer"));
    let e = err(&with(
        "[[platform]]\nid = \"a\"\nrenderer = \"command\"\nengine = \"webkit\"\ncommand = \"x\"\n",
    ));
    assert!(detail(&e).contains("`engine` is not a key of the `command` renderer"));
    let e = err(&with(
        "[[platform]]\nid = \"a\"\nrenderer = \"command\"\ncommand = \"\"\n",
    ));
    assert!(detail(&e).contains("command must not be empty"));
    let e = err(&with("[[platform]]\nid = \"a\"\nrenderer = \"command\"\n"));
    assert!(detail(&e).contains("requires `command`"));
    let e = err(&with(
        "[[platform]]\nid = \"a\"\nrenderer = \"command\"\ncommand = \"x\"\nbogus = 1\n",
    ));
    assert_eq!(e.key(), Some("bogus"));
}

#[test]
fn platform_numeric_params_are_range_checked() {
    let base = |extra: &str| {
        with(&format!(
            "[[platform]]\nid = \"a\"\nrenderer = \"web\"\nengine = \"chromium\"\nviewport = {{ width = 10, height = 10 }}\n{extra}\n"
        ))
    };
    for (extra, needle) in [
        ("device_scale = 0", "device_scale"),
        ("cpu_throttle = 0.5", "cpu_throttle"),
        (
            "network_throttle = { download = 0, upload = 1 }",
            "download and upload",
        ),
        (
            "network_throttle = { download = 1, upload = 1, latency = -1 }",
            "latency",
        ),
    ] {
        let e = err(&base(extra));
        assert!(detail(&e).contains(needle), "{extra}: {}", detail(&e));
    }
    assert!(detail(&err(&with("[[platform]]\nid = \"a\"\nrenderer = \"web\"\nengine = \"chromium\"\nviewport = { width = 0, height = 10 }\n"))).contains("viewport"));
}

#[test]
fn screens_resolve_tags_and_report_dangling_references() {
    let ok_screen = "[[screen]]\nid = \"home\"\nentry = \"/\"\napplies_to = [\"tag:d\", \"mob\"]\n[[screen.states]]\nid = \"a\"\n[[screen.states]]\nid = \"b\"\napplies_to = [\"tag:m\"]\ndiff_against = \"a\"\n";
    let spec = ok(&gallery(ok_screen));
    assert_eq!(spec.screens["home"].states.len(), 2);

    let cases = [
        (
            "applies_to = [\"ghost\"]\n[[screen.states]]\nid = \"a\"\n",
            "undeclared platform id `ghost`",
        ),
        (
            "applies_to = [\"tag:zz\"]\n[[screen.states]]\nid = \"a\"\n",
            "unknown tag `tag:zz`",
        ),
        (
            "applies_to = [\"desk\"]\n[[screen.states]]\nid = \"a\"\napplies_to = [\"mob\"]\n",
            "not a subset of the screen's",
        ),
        (
            "[[screen.states]]\nid = \"a\"\nsession = \"s\"\n",
            "dangling session id `s`",
        ),
        (
            "[[screen.states]]\nid = \"a\"\nmock = \"m\"\n",
            "dangling mock id `m`",
        ),
        (
            "[[screen.states]]\nid = \"a\"\ndiff_against = \"z\"\n",
            "dangling sibling state id `z`",
        ),
        (
            "[[screen.states]]\nid = \"a\"\nactions = [{ kind = \"click\", selector = \"\" }]\n",
            "selector must not be empty",
        ),
        (
            "[[screen.states]]\nid = \"a\"\nnetwork = [{ url_pattern = \"u\", action = \"status\", status = 99 }]\n",
            "valid HTTP status",
        ),
        (
            "[[screen.states]]\nid = \"a\"\nnetwork = [{ url_pattern = \"u\", action = \"delay\", delay_ms = 0 }]\n",
            "delay_ms must be greater than 0",
        ),
        (
            "[[screen.states]]\nid = \"a\"\nactions = [{ kind = \"wait_for\", selector = \"x\", timeout_ms = 0 }]\n",
            "timeout_ms must be greater than 0",
        ),
    ];
    for (body, needle) in cases {
        let e = err(&gallery(&format!(
            "[[screen]]\nid = \"home\"\nentry = \"/\"\n{body}"
        )));
        assert!(detail(&e).contains(needle), "{needle}: {}", detail(&e));
        assert!(e.location().is_some(), "{needle} is located");
    }
    let e = err(&gallery(
        "[[screen]]\nid = \"home\"\nentry = \"/\"\nstates = []\n",
    ));
    assert!(detail(&e).contains("at least one state"));
    let e = err(&gallery(
        "[[screen]]\nid = \"home\"\nentry = \"/\"\n[[screen.states]]\nid = \"a\"\nactions = [{ kind = \"dance\", selector = \"x\" }]\n",
    ));
    assert_eq!(e.kind(), SpecErrorKind::Invalid);
    let dup = "[[screen]]\nid = \"home\"\nentry = \"/\"\n[[screen.states]]\nid = \"a\"\n";
    let e = err(&gallery(&format!("{dup}\n{dup}")));
    assert!(detail(&e).contains("duplicate screen id `home`"));
}

#[test]
fn rosters_and_duplicate_ids() {
    let spec = ok(&gallery(
        "[[session]]\nid = \"s\"\ndata = { role = \"admin\" }\n[[mock_set]]\nid = \"m\"\n[[screen]]\nid = \"h\"\nentry = \"/\"\n[[screen.states]]\nid = \"a\"\nsession = \"s\"\nmock = \"m\"\n",
    ));
    assert_eq!(
        spec.sessions["s"].data["role"],
        crunk_spec::Dyn::Str("admin".into())
    );
    let dup = "[[session]]\nid = \"s\"\n";
    let e = err(&with(&format!("{dup}{dup}")));
    assert!(detail(&e).contains("duplicate session id `s`"));
    let dup = "[[mock_set]]\nid = \"s\"\n";
    assert!(detail(&err(&with(&format!("{dup}{dup}")))).contains("duplicate mock_set id"));
}

#[test]
fn actions_round_trip_with_their_kind() {
    let spec = ok(&gallery(
        "[[screen]]\nid = \"h\"\nentry = \"/\"\n[[screen.states]]\nid = \"a\"\nactions = [{ kind = \"fill\", selector = \"i\", value = \"v\" }, { kind = \"wait_for\", selector = \"d\" }]\n",
    ));
    let actions = &spec.screens["h"].states[0].actions;
    assert_eq!(
        actions[0],
        Action::Fill {
            selector: "i".into(),
            value: "v".into()
        }
    );
    assert_eq!(
        actions[1],
        Action::WaitFor {
            selector: "d".into(),
            timeout_ms: None
        }
    );
    let json = serde_json::to_value(actions).unwrap();
    assert_eq!(json[1]["kind"], "wait_for");
}

#[test]
fn tables_owned_by_other_crates_are_left_to_their_owners() {
    /// A stand-in for gob-check's table, registered in this test binary's inventory.
    #[derive(Debug, gob_config::ConfigTable)]
    #[config(table = "check")]
    #[allow(dead_code, reason = "registered for its name only")]
    struct Check {
        #[config(default = 1)]
        level: u32,
    }
    let spec = ok(&with("[check]\nlevel = 2\n"));
    assert_eq!(spec.project.css_root, "styles");
    let e = err(&with("[chekc]\nlevel = 2\n"));
    assert_eq!(e.key(), Some("chekc"));
    assert_eq!(e.suggestion(), Some("check"));
}

#[test]
fn error_display_names_file_line_and_column() {
    let e = err(&swap("css_root = \"styles\"", "css_rot = \"styles\""));
    let text = e.to_string();
    assert!(
        text.starts_with("crunk.toml:2:1: [project]: unknown key `css_rot`"),
        "{text}"
    );
    assert!(text.ends_with("did you mean `css_root`?"), "{text}");
    assert_eq!(
        SpecError::Invalid {
            path: "x".into(),
            at: None,
            detail: "d".into(),
            key: None,
            suggestion: None
        }
        .to_string(),
        "x: d"
    );
}
