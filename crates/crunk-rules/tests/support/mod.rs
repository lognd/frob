//! A throwaway crunk project for rule tests: the default preset (or a case's own `crunk.toml`),
//! the case file, an empty generated tokens sheet, and the real ingest over them.
//!
//! The case's `config=no-tokens` leaves the tokens sheet out, so the definition set is incomplete;
//! `config=breakpoints` adds a `[breakpoints]` table (`breakpoints-scenes` also writes scenes at 768 and 1024); `config=tw-theme-*` declares a Tailwind config and a stand-in theme; `config=tokens-current` writes the generated token
//! files the spec renders, so TOKENS001 finds no drift; `config=tokens-divergent` then hand-edits one
//! generated value (EXPORT002); `config=uses-ink` adds a stylesheet reading `var(--color-ink)` (the
//! TOKEN rules that look at uses). The authored `design/tokens/*.toml` files load as the pipeline does.

// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

#![allow(
    dead_code,
    reason = "each test binary uses a different part of the support module"
)]

use std::fmt::Write as _;
use std::path::Path;

use crunk_ingest::{ProjectStyles, ingest_tree};
use crunk_rules::CrunkHost;
use crunk_rules::component_files::ComponentFacts;
use crunk_rules::content_files::ContentFacts;
use crunk_rules::review::{AckSignature, ReviewFacts, Subject, judge};
use crunk_rules::scene_docs::SceneDocFacts;
use crunk_rules::scene_files::SceneFacts;
use crunk_rules::screen_files::ScreenFacts;
use crunk_rules::tailwind::TailwindFacts;
use crunk_rules::token_files::TokenFacts;
use crunk_spec::DesignSpec;
use crunk_tailwind::runtime::{ClassDeclaration, ClassResult, ClassStatus};
use gob_cache::Cache;
use gob_lock::{ReviewEntry, ReviewVerdict};
use gob_rules::{Emitted, Finding, RepoRule, run_repo};
use gob_text::FileInterner;
use indexmap::IndexMap;

/// The spec and ingested styles of one test project; keeps the temp directory alive.
pub struct Project {
    pub spec: DesignSpec,
    pub styles: ProjectStyles,
    pub tailwind: TailwindFacts,
    pub reviews: Option<ReviewFacts>,
    pub tokens: Option<TokenFacts>,
    pub scenes: Option<SceneFacts>,
    // frob:ticket 01M5H30AMSB0THE4GW322D4K54
    pub scene_docs: Option<SceneDocFacts>,
    // frob:ticket 01M4CXR96GDDX460SZZVAAWD0R
    pub content: Option<ContentFacts>,
    pub screens: Option<ScreenFacts>,
    pub components: Option<ComponentFacts>,
    _dir: tempfile::TempDir,
}

impl CrunkHost for Project {
    fn spec(&self) -> Option<&DesignSpec> {
        Some(&self.spec)
    }
    fn styles(&self) -> Option<&ProjectStyles> {
        Some(&self.styles)
    }
    fn tailwind(&self) -> Option<&TailwindFacts> {
        Some(&self.tailwind)
    }
    fn reviews(&self) -> Option<&ReviewFacts> {
        self.reviews.as_ref()
    }
    fn tokens(&self) -> Option<&TokenFacts> {
        self.tokens.as_ref()
    }
    fn scenes(&self) -> Option<&SceneFacts> {
        self.scenes.as_ref()
    }
    fn scene_docs(&self) -> Option<&SceneDocFacts> {
        self.scene_docs.as_ref()
    }
    fn content(&self) -> Option<&ContentFacts> {
        self.content.as_ref()
    }
    fn screens(&self) -> Option<&ScreenFacts> {
        self.screens.as_ref()
    }
    fn components(&self) -> Option<&ComponentFacts> {
        self.components.as_ref()
    }
}

/// What the stand-in compiler knows about one utility: the declarations Tailwind v3 would emit for
/// the shapes the tests use (arbitrary values, a few default scale keys and colours), or `None`
/// for anything else, which reads as "not Tailwind syntax". No node is involved.
fn stub_compile(name: &str) -> Option<Vec<(&'static str, String)>> {
    let stem = name.rsplit_once('/').map_or(name, |(stem, _)| stem);
    if let Some((prefix, value)) = stem.strip_suffix(']').and_then(|b| b.split_once("-[")) {
        let value = value.replace('_', " ");
        let value = value
            .strip_prefix("color:")
            .or_else(|| value.strip_prefix("length:"))
            .unwrap_or(&value)
            .to_owned();
        let prop = match prefix {
            "p" => "padding",
            "m" => "margin",
            "gap" => "gap",
            "inset" => "inset",
            "rounded" => "border-radius",
            "w" => "width",
            "h" => "height",
            "min-w" => "min-width",
            "min-h" => "min-height",
            "max-h" => "max-height",
            "z" | "-z" => "z-index",
            "bg" => "background-color",
            "text" if value.starts_with('#') => "color",
            "text" => "font-size",
            _ => return None,
        };
        return Some(vec![(prop, value)]);
    }
    let (prefix, key) = stem.split_once('-')?;
    let spacing = |prop: &'static str| -> Option<Vec<(&'static str, String)>> {
        let n: f64 = key.parse().ok()?;
        let value = if n == 0.0 {
            "0px".to_owned()
        } else {
            format!("{}rem", n / 4.0)
        };
        Some(vec![(prop, value)])
    };
    match prefix {
        "p" => spacing("padding"),
        "m" => spacing("margin"),
        "inset" => spacing("inset"),
        "z" => Some(vec![("z-index", key.to_owned())]),
        "rounded" if key == "lg" => Some(vec![("border-radius", "0.5rem".to_owned())]),
        "bg" | "text" => {
            let hex = crunk_tailwind::defaults::V3_COLOR_HEXES
                .iter()
                .find_map(|(n, hex)| (*n == key).then_some(*hex))?;
            let prop = if prefix == "bg" {
                "background-color"
            } else {
                "color"
            };
            Some(vec![(prop, hex.to_owned())])
        }
        _ => None,
    }
}

/// The facts for `styles`: every utility compiled by [`stub_compile`], and the theme a case selects
/// with `config=tw-theme-broken` (`brand` maps to an undefined token), `tw-theme-plain` (`brand` is a
/// literal colour) or `tw-theme-alpha` (`brand` carries an `<alpha-value>` placeholder).
fn tailwind_facts(
    spec: &DesignSpec,
    styles: &ProjectStyles,
    config: Option<&str>,
) -> TailwindFacts {
    let mut theme = IndexMap::new();
    match config {
        Some("tw-theme-broken") => {
            theme.insert("brand".to_owned(), "var(--color-missing)".to_owned());
        }
        Some("tw-theme-plain") => {
            theme.insert("brand".to_owned(), "#2f6fed".to_owned());
        }
        Some("tw-theme-alpha") => {
            theme.insert(
                "brand".to_owned(),
                "rgb(var(--brand-rgb) / <alpha-value>)".to_owned(),
            );
        }
        _ => {}
    }
    let names: std::collections::BTreeSet<&str> = styles
        .sheets
        .iter()
        .flat_map(|s| s.utilities.iter().map(|u| u.name.as_str()))
        .collect();
    let results = names
        .into_iter()
        .map(|name| {
            let declarations: Vec<ClassDeclaration> = stub_compile(name)
                .unwrap_or_default()
                .into_iter()
                .map(|(property, value)| ClassDeclaration {
                    property: property.to_owned(),
                    value,
                    selector: format!(".{name}"),
                    at_rules: Vec::new(),
                })
                .collect();
            let status = if declarations.is_empty() {
                ClassStatus::Invalid
            } else {
                ClassStatus::Valid
            };
            ClassResult {
                candidate: name.to_owned(),
                status,
                declarations,
            }
        })
        .collect();
    TailwindFacts::new(spec, theme, results, None)
}

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// The default preset's `crunk.toml`, for tests that tweak a table.
pub const DEFAULT_SPEC: &str = include_str!("../../../crunk-spec/src/presets/default.toml");

/// The `[breakpoints]` table a case selects with `config=breakpoints` (the default preset has none,
/// which keeps the BP rules off).
pub const BREAKPOINTS_TABLE: &str = "\n[breakpoints]\nsm = 640\nmd = 768\nlg = 1024\n";

/// Build a project holding `file` with `text` under the default preset.
pub fn project_with_spec(spec_text: &str, file: &str, text: &str) -> Project {
    build(spec_text.to_owned(), file, text, None)
}

/// Build a project holding `file` with `text`; `crunk.toml` as `file` replaces the preset.
pub fn project(file: &str, text: &str, config: Option<&str>) -> Project {
    let spec_text = if file == "crunk.toml" {
        text.to_owned()
    } else {
        DEFAULT_SPEC.to_owned()
    };
    build(spec_text, file, text, config)
}

// frob:ticket 01M5HM3VTW5FAZQ3TXM8XH739S
/// The `config=no-radii` cases drop the preset's radii; `no-radii-decided` also declares a radius decision.
fn apply_radii_config(spec_text: &mut String, config: Option<&str>) {
    if matches!(config, Some("no-radii" | "no-radii-decided")) {
        *spec_text = spec_text.replace("radii = [0, 4, 8, 16]", "radii = []");
    }
    if config == Some("no-radii-decided") {
        spec_text.push_str("\n[decisions]\nradius = \"square on purpose\"\n");
    }
}

// frob:ticket 01M5HM3W18AJZET52BZBEJFYD4
/// The `config=roles-semantic` case adds danger, warning and success roles to the preset's `body` role.
fn apply_roles_config(spec_text: &mut String, config: Option<&str>) {
    if config == Some("roles-semantic") {
        *spec_text = spec_text.replace(
            "body = [\"ink\", \"paper\"]",
            "body = [\"ink\", \"paper\"]\ndanger = [\"ink\", \"paper\"]\nwarning = [\"ink\", \"paper\"]\nsuccess = [\"ink\", \"paper\"]",
        );
    }
}

fn build(mut spec_text: String, file: &str, text: &str, config: Option<&str>) -> Project {
    let dir = tempfile::tempdir().expect("tempdir");
    if config.is_some_and(|c| c.starts_with("tw-theme-")) {
        spec_text.push_str("\n[tailwind]\nconfig = \"tailwind.config.js\"\n");
    }
    // frob:ticket 01M4CXT4Z45GR5QE71B10FRR8N
    if let Some(key) = config.and_then(|c| c.strip_prefix("decide-")) {
        spec_text.push_str("\n[decisions]\n");
        spec_text.push_str(key);
        spec_text.push_str(" = \"chosen on purpose\"\n");
    }
    apply_radii_config(&mut spec_text, config);
    apply_roles_config(&mut spec_text, config);
    if config == Some("palette-indigo") {
        spec_text = spec_text.replace("accent = \"#2f6fed\"", "accent = \"#6366f1\"");
    }
    if config == Some("breakpoints") {
        spec_text.push_str(BREAKPOINTS_TABLE);
    }
    if matches!(config, Some("breakpoints-scenes")) {
        spec_text.push_str(BREAKPOINTS_TABLE);
    }
    if config.is_some_and(|c| c.starts_with("review-")) {
        spec_text.push_str(&review_tables(config));
    }
    // frob:ticket 01M4D95WWXAWJF1M9ST8RX5YZG
    if let Some(kind) = config.and_then(|c| c.strip_prefix("game-")) {
        spec_text.push_str(&game_table(kind));
    }
    if [".tsx", ".jsx", ".ts"].iter().any(|e| file.ends_with(e)) {
        spec_text.push_str("\n[jsx]\nglobs = [\"src/**/*\"]\n");
    }
    write(dir.path(), "crunk.toml", &spec_text);
    if file != "crunk.toml" {
        write(dir.path(), file, text);
    }
    if config != Some("no-tokens")
        && !matches!(config, Some("tokens-current" | "tokens-divergent"))
        && file != "styles/tokens.css"
    {
        write(dir.path(), "styles/tokens.css", ":root {}\n");
    }
    let spec = crunk_spec::parse_spec(&spec_text, &dir.path().join("crunk.toml"), dir.path())
        .expect("spec parses");
    if matches!(config, Some("tokens-current" | "tokens-divergent")) {
        for rendered in crunk_tokens::export::render_managed(&spec).expect("render") {
            std::fs::create_dir_all(rendered.path.parent().expect("parent")).expect("mkdir");
            std::fs::write(&rendered.path, rendered.content).expect("write generated file");
        }
    }
    if config == Some("tokens-divergent") {
        let css = dir.path().join("styles/tokens.css");
        let text = std::fs::read_to_string(&css).expect("read generated css");
        assert!(
            text.contains("--space-16: 16px;"),
            "the preset renders --space-16"
        );
        std::fs::write(&css, text.replace("--space-16: 16px;", "--space-16: 17px;")).expect("edit");
    }
    // frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8
    if config == Some("uses-ink") {
        write(
            dir.path(),
            "styles/use.css",
            ".a { color: var(--color-ink); }\n",
        );
    }
    // frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62
    if config == Some("breakpoints-scenes") {
        for width in [768, 1024] {
            write(
                dir.path(),
                &format!("design/scenes/w{width}.scene.json"),
                &format!(
                    "{{\"viewport\":{{\"width\":{width},\"height\":300}},\"root\":{{\"id\":\"root\",\"kind\":\"box\",\"style\":{{\"width\":{width},\"height\":300}}}}}}"
                ),
            );
        }
    }
    write_content(dir.path(), config);
    let styles = ingest_tree(&spec, &Cache::null()).expect("ingest").styles;
    let tokens = Some(TokenFacts::load(&spec));
    let scenes = Some(SceneFacts::load(&spec));
    // frob:ticket 01M5H30AMSB0THE4GW322D4K54
    let scene_docs = Some(SceneDocFacts::load(&spec));
    // frob:ticket 01M4CXR96GDDX460SZZVAAWD0R
    let content = Some(ContentFacts::load(&spec));
    // frob:ticket 01M4CXR89ERNB60CEDG60E2DXH
    let screens = Some(ScreenFacts::load(&spec));
    // frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F
    let components = Some(ComponentFacts::load(&spec));
    let tailwind = tailwind_facts(&spec, &styles, config);
    let reviews = config.and_then(|c| review_facts(&spec, c));
    Project {
        spec,
        styles,
        tailwind,
        reviews,
        tokens,
        scenes,
        scene_docs,
        content,
        screens,
        components,
        _dir: dir,
    }
}

/// Run the repo rule `R` over `host` and anchor the emissions the way the pipeline does.
pub fn run<R: RepoRule<Project> + Default>(host: &Project) -> Vec<Finding> {
    let emitted: Vec<Emitted> = run_repo::<R, Project>(&R::default(), host);
    let mut files = FileInterner::new();
    emitted
        .into_iter()
        .map(|e| e.into_located_finding(R::DEF, &mut files))
        .collect()
}

// frob:ticket 01M4CXSM408E7A05DWKENDB7V4
// frob:ticket 01M4D95WWXAWJF1M9ST8RX5YZG
/// The `[game]` table a `config=game-*` case adds: `game-complete` declares every coverage key,
/// `game-no-volume` every key but `volume_channels`.
fn game_table(kind: &str) -> String {
    let keys: Vec<String> = crunk_spec::table::GAME_COVERAGE_KEYS
        .iter()
        .map(|(k, _)| *k)
        .filter(|k| !(kind == "no-volume" && *k == "volume_channels"))
        .map(|k| format!("\"{k}\""))
        .collect();
    format!("\n[game]\ncoverage = [{}]\n", keys.join(", "))
}

/// The `[review]` policy and the reviewed screen `home` a `config=review-*` case adds.
fn review_tables(config: Option<&str>) -> String {
    let mut text = String::from(
        "\n[[screen]]\nid = \"home\"\nentry = \"/\"\nreview = \"human\"\n[[screen.states]]\nid = \"default\"\n",
    );
    if matches!(config, Some("review-unlisted" | "review-unsigned")) {
        let signed = config == Some("review-unsigned");
        let _ = write!(
            text,
            "\n[review]\nrequire_signed = {signed}\n[[review.reviewers]]\nid = \"alice@example.com\"\nkeys = [\"KEY1\"]\n"
        );
    }
    text
}

/// The current subject of the case's screen: one token input.
fn review_subject(token_digest: &str) -> Subject {
    Subject {
        id: "screen/home/default".to_owned(),
        screen: "home".to_owned(),
        inputs: [("token:--color-bg".to_owned(), token_digest.to_owned())].into(),
    }
}

/// The judged review of the case's screen for the `review-*` case named `config`.
fn review_facts(spec: &DesignSpec, config: &str) -> Option<ReviewFacts> {
    if !config.starts_with("review-") {
        return None;
    }
    let now = review_subject("new");
    let recorded = |subject: &Subject, reviewer: &str, verdict| ReviewEntry {
        digest: subject.digest(),
        verdict,
        reviewer: reviewer.to_owned(),
        at: "2026-10-13T00:00:00Z".to_owned(),
        note: Some("spacing is off".to_owned()),
        render: None,
        non_interactive: false,
        inputs: subject.inputs.clone(),
    };
    let alice = "Alice <alice@example.com>";
    let (entry, signature) = match config {
        "review-missing" => (None, None),
        "review-stale" => (
            Some(recorded(
                &review_subject("old"),
                alice,
                ReviewVerdict::Approved,
            )),
            None,
        ),
        "review-unlisted" => (
            Some(recorded(
                &now,
                "Mallory <m@example.com>",
                ReviewVerdict::Approved,
            )),
            None,
        ),
        "review-unsigned" => (
            Some(recorded(&now, alice, ReviewVerdict::Approved)),
            Some(AckSignature::Unsigned("commit is not signed".to_owned())),
        ),
        "review-rejected" => (Some(recorded(&now, alice, ReviewVerdict::Rejected)), None),
        _ => (Some(recorded(&now, alice, ReviewVerdict::Approved)), None),
    };
    Some(ReviewFacts {
        findings: vec![judge(
            &now,
            entry.as_ref(),
            &spec.review,
            signature.as_ref(),
        )],
        unreadable: None,
    })
}

/// Write the `content-en` config's copy file (one key, `home.hero`) under `root`.
fn write_content(root: &Path, config: Option<&str>) {
    // frob:ticket 01M5HM3W7MK7255AGEN27SXEXP
    if config == Some("content-voice") {
        write(
            root,
            "design/content/voice.toml",
            "voice = \"plain and warm\"\n",
        );
    }
    if config == Some("content-en") {
        write(
            root,
            "design/content/en.toml",
            "locale = \"en\"\n\n[[key]]\nid = \"home.hero\"\ntext = \"Welcome back\"\nmax_chars = 20\n",
        );
    }
}
