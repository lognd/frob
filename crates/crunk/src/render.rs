//! `render --engine solve`: write one layout-solve JSON per `(screen, state, platform)` cell.
//!
//! Scenes are `design/scenes/<screen>.<state>.scene.html`, falling back to
//! `design/scenes/<screen>.scene.html` for every state of the screen. Each cell is solved by the
//! T1 driver ([`crunk_layout::solve::solve_scene_html`]) at its platform's viewport with the
//! spec's design tokens, and written to `<out>/<screen>/<state>/<platform>.layout.json`. Cells
//! are solved on `--jobs` worker threads but always reported and written in cell order, so the
//! output is identical for every `--jobs` value. `--engine browser` needs the `gallery` feature
//! and refuses with `E-GALLERY-NOT-BUILT` and the remedy in the default build. [`Plan`] and
//! [`solve_all`] are shared with `snapshot`.

// frob:ticket 01M5XCWYMSEMEQPNZ7EFHHY9Z7

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};

use crunk_layout::solve::solve_scene_html;
use crunk_layout::style::TokenMap;
use crunk_layout::text::TextMeasurer;
use crunk_spec::DesignSpec;
use crunk_spec::model::RendererParams;
use crunk_tokens::TokenSet;
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use crate::PRODUCT;

/// Default directory `render` writes under, relative to the project root.
const DEFAULT_OUT: &str = ".crunk/render";
/// Default directory holding the scene files, relative to the project root.
pub(crate) const DEFAULT_SCENES: &str = "design/scenes";

/// Solve the scenes of the selected cells and write their layout-solve JSON.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "render",
    product = "crunk",
    idempotent = true,
    exits(ok, negative, refused, usage, internal)
)]
pub struct Render {
    engine: String,
    out: String,
    select: SelectArgs,
}

/// Which cells to act on, where the scenes live and how many workers solve them.
#[derive(Debug, Clone, Default, clap::Args)]
#[command(about = None, long_about = None)]
pub(crate) struct SelectArgs {
    #[arg(long, value_name = "SCREEN", help = "Only this screen")]
    pub screen: Option<String>,
    #[arg(long, value_name = "STATE", help = "Only this state id")]
    pub state: Option<String>,
    #[arg(long, value_name = "PLATFORM", help = "Only this platform")]
    pub platform: Option<String>,
    #[arg(
        long,
        value_name = "DIR",
        default_value = DEFAULT_SCENES,
        help = "Scene directory, relative to the project root"
    )]
    pub scenes: String,
    #[arg(
        long,
        value_name = "N",
        help = "Worker threads (default: available cores); output order never depends on it"
    )]
    pub jobs: Option<usize>,
}

/// `render` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct RenderArgs {
    #[arg(
        long,
        value_name = "ENGINE",
        default_value = "solve",
        value_parser = ["solve", "browser"],
        help = "solve (the scene solver) or browser (needs the gallery feature)"
    )]
    engine: String,
    #[arg(
        long,
        value_name = "DIR",
        default_value = DEFAULT_OUT,
        help = "Output directory, relative to the project root"
    )]
    out: String,
    #[command(flatten)]
    select: SelectArgs,
}

/// One written layout-solve file.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct RenderedCell {
    /// Screen id.
    pub screen: String,
    /// State id.
    pub state: String,
    /// Platform id.
    pub platform: String,
    /// The file written, relative to the project root.
    pub path: String,
    /// Nodes in the solve.
    pub nodes: usize,
}

/// Output of `render`.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, JsonSchema)]
pub struct RenderData {
    /// The engine that ran.
    pub engine: String,
    /// Files written, in cell order.
    pub cells: Vec<RenderedCell>,
}

/// One `(screen, state, platform)` cell with its scene file and viewport.
#[derive(Debug, Clone)]
pub(crate) struct Item {
    pub screen: String,
    pub state: String,
    pub platform: String,
    pub scene: PathBuf,
    pub viewport: (f32, f32),
}

/// A solved cell: the canonical JSON text and its node count.
#[derive(Debug, Clone)]
pub(crate) struct Solved {
    pub json: String,
    pub nodes: usize,
}

/// Everything needed to solve the selected cells.
#[derive(Debug)]
pub(crate) struct Plan {
    pub root: PathBuf,
    pub tokens: TokenMap,
    pub items: Vec<Item>,
    pub jobs: usize,
    /// Cells skipped with the reason (platforms without a viewport).
    pub skipped: Vec<String>,
}

fn usage(message: String) -> CliError {
    tracing::info!(%message, "render: usage error");
    CliError::Usage(message)
}

fn refusal(code: &str, message: impl Into<String>) -> Refusal {
    Refusal::new(code, RefusalClass::GuardNeedsAction, message)
}

/// The `(screen, state, platform)` triples of `spec` passing `select`, in declaration order.
fn triples(spec: &DesignSpec, select: &SelectArgs) -> Vec<(String, String, String)> {
    let keep = |want: &Option<String>, have: &str| want.as_deref().is_none_or(|w| w == have);
    spec.cell_triples()
        .into_iter()
        .filter(|(screen, state, platform)| {
            keep(&select.screen, screen)
                && keep(&select.state, state)
                && keep(&select.platform, platform)
        })
        .collect()
}

/// The scene file for a screen state under `dir`, state-specific first.
fn scene_for(dir: &Path, screen: &str, state: &str) -> Option<PathBuf> {
    [
        dir.join(format!("{screen}.{state}.scene.html")),
        dir.join(format!("{screen}.scene.html")),
    ]
    .into_iter()
    .find(|p| p.is_file())
}

fn token_map(spec: &DesignSpec) -> Result<TokenMap, Refusal> {
    let set = TokenSet::from_spec(spec).map_err(|e| {
        refusal("E-TOKENS", e.to_string())
            .with_remedy("rename one of the colliding entries in crunk.toml")
    })?;
    Ok(TokenMap::from_pairs(
        set.css_entries()
            .into_iter()
            .map(|(name, value)| (name.to_owned(), value)),
    ))
}

/// Locate the project root, load its spec and build the token map.
fn load(ctx: &Context) -> Result<(PathBuf, DesignSpec, TokenMap), Refusal> {
    let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
    let spec = crunk_spec::load_spec(&root).map_err(|e| {
        tracing::info!(error = %e, "render: spec did not load");
        refusal(
            "E-SPEC",
            format!("crunk.toml is not a valid design spec: {e}"),
        )
        .with_remedy("fix crunk.toml as described, then rerun")
    })?;
    let tokens = token_map(&spec)?;
    Ok((root, spec, tokens))
}

#[allow(clippy::cast_precision_loss)]
/// The viewport of `platform` in pixels, or `None` when it is not a web platform.
fn viewport_for(spec: &DesignSpec, platform: &str) -> Option<(f32, f32)> {
    match spec.platforms.get(platform).map(|p| &p.params) {
        Some(RendererParams::Web(w)) => Some((w.viewport.width as f32, w.viewport.height as f32)),
        _ => None,
    }
}

/// The usage hint naming a screen/state that has no scene file and the paths tried.
fn missing_scene_hint(select: &SelectArgs, screen: &str, state: &str) -> String {
    format!(
        "screen '{screen}' state '{state}' has no scene file (expected {d}/{screen}.{state}.scene.html or {d}/{screen}.scene.html)",
        d = select.scenes
    )
}

/// How one wanted cell resolved: a renderable item, a missing-scene hint, or a skip note.
enum Resolved {
    Item(Item),
    Missing(String),
    Skipped(String),
}

/// Resolve one wanted cell against its scene file and platform viewport.
fn resolve_cell(
    dir: &Path,
    spec: &DesignSpec,
    select: &SelectArgs,
    (screen, state, platform): (String, String, String),
) -> Resolved {
    let Some(scene) = scene_for(dir, &screen, &state) else {
        return Resolved::Missing(missing_scene_hint(select, &screen, &state));
    };
    let Some(viewport) = viewport_for(spec, &platform) else {
        tracing::info!(%screen, %state, %platform, "render: platform has no viewport, skipped");
        return Resolved::Skipped(format!(
            "{screen}/{state} on {platform}: platform has no viewport, skipped"
        ));
    };
    Resolved::Item(Item {
        screen,
        state,
        platform,
        scene,
        viewport,
    })
}

/// Pair each wanted cell with its scene file and viewport; cells on viewport-less platforms are skipped.
fn resolve_items(
    root: &Path,
    spec: &DesignSpec,
    select: &SelectArgs,
    wanted: Vec<(String, String, String)>,
) -> Result<(Vec<Item>, Vec<String>), CliError> {
    let dir = root.join(&select.scenes);
    let mut items = Vec::new();
    let mut missing = Vec::new();
    let mut skipped = Vec::new();
    for cell in wanted {
        match resolve_cell(&dir, spec, select, cell) {
            Resolved::Item(item) => items.push(item),
            Resolved::Missing(hint) if !missing.contains(&hint) => missing.push(hint),
            Resolved::Missing(_) => {}
            Resolved::Skipped(note) => skipped.push(note),
        }
    }
    if !missing.is_empty() {
        return Err(usage(missing.join("; ")));
    }
    Ok((items, skipped))
}

/// Load the spec and resolve the cells `select` names into a [`Plan`].
///
/// # Errors
///
/// Exit 3 when the spec or its tokens do not load; exit 2 when no cell matches or a selected
/// screen has no scene file (the message names it and the paths tried).
pub(crate) fn plan(ctx: &Context, select: &SelectArgs) -> Result<Plan, CliError> {
    let (root, spec, tokens) = load(ctx)?;
    let wanted = triples(&spec, select);
    if wanted.is_empty() {
        return Err(usage(
            "no (screen, state, platform) cell matches the filters".to_owned(),
        ));
    }
    let (items, skipped) = resolve_items(&root, &spec, select, wanted)?;
    let jobs = select
        .jobs
        .unwrap_or_else(|| std::thread::available_parallelism().map_or(1, usize::from))
        .clamp(1, items.len().max(1));
    tracing::info!(cells = items.len(), jobs, "render: plan ready");
    Ok(Plan {
        root,
        tokens,
        items,
        jobs,
        skipped,
    })
}

/// Solve one cell: parse its scene, solve at its viewport, serialize canonically.
fn solve_one(item: &Item, tokens: &TokenMap, fonts: &mut TextMeasurer) -> Result<Solved, String> {
    let text = std::fs::read_to_string(&item.scene)
        .map_err(|e| format!("read {}: {e}", item.scene.display()))?;
    let doc = crunk_scene::parse_scene_html(&text).map_err(|e| format!("parse scene: {e}"))?;
    let solved = solve_scene_html(&doc, tokens, item.viewport, fonts).map_err(|e| e.to_string())?;
    for note in &solved.notes {
        tracing::debug!(screen = %item.screen, state = %item.state, ?note, "render: solve note");
    }
    let json = solved.doc.to_json().map_err(|e| e.to_string())?;
    Ok(Solved {
        json,
        nodes: solved.doc.nodes.len(),
    })
}

/// Solve every item of `plan` on `plan.jobs` workers; results are in item order.
pub(crate) fn solve_all(plan: &Plan) -> Vec<Result<Solved, String>> {
    let next = AtomicUsize::new(0);
    let mut results: Vec<Option<Result<Solved, String>>> = vec![None; plan.items.len()];
    let done = std::sync::Mutex::new(&mut results);
    std::thread::scope(|scope| {
        for worker in 0..plan.jobs {
            let (next, done) = (&next, &done);
            scope.spawn(move || {
                let mut fonts = TextMeasurer::new();
                loop {
                    let i = next.fetch_add(1, Ordering::Relaxed);
                    let Some(item) = plan.items.get(i) else { break };
                    tracing::debug!(worker, i, screen = %item.screen, "render: solving cell");
                    let r = solve_one(item, &plan.tokens, &mut fonts);
                    if let Ok(mut slots) = done.lock() {
                        slots[i] = Some(r);
                    }
                }
            });
        }
    });
    results
        .into_iter()
        .map(|r| r.unwrap_or_else(|| Err("cell was not solved".to_owned())))
        .collect()
}

/// The project-relative file for a cell under `base`: `<base>/<screen>/<state>/<platform>.layout.json`.
pub(crate) fn cell_file(base: &str, item: &Item) -> PathBuf {
    Path::new(base)
        .join(&item.screen)
        .join(&item.state)
        .join(format!("{}.layout.json", item.platform))
}

/// Create the parent directories of `path`.
fn create_parent(path: &Path) -> Result<(), String> {
    let parent = path.parent().unwrap_or_else(|| Path::new("."));
    std::fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))
}

/// Create parent directories, then write `text` atomically.
pub(crate) fn write_file(path: &Path, text: &str) -> Result<(), String> {
    create_parent(path)?;
    gob_fs::write_atomic(path, text.as_bytes())
        .map_err(|e| format!("write {}: {e}", path.display()))
}

/// `/`-joined text of a relative path, stable across platforms.
pub(crate) fn posix(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}

/// Refuse: the browser engine is not built into this binary.
#[cfg(not(feature = "gallery"))]
fn browser(verb: &str) -> Outcome<RenderData> {
    use gob_diagnostics::RemedyCommand;
    tracing::info!(verb, "render: browser engine not built in");
    Err(refusal(
        "E-GALLERY-NOT-BUILT",
        "--engine browser is not built into this crunk binary",
    )
    .with_command(
        RemedyCommand::new("cargo", "install")
            .arg("crunk")
            .flag("features", "gallery"),
    )
    .into())
}

/// Refuse: the browser engine's layout boxes are not wired to `render` yet.
#[cfg(feature = "gallery")]
fn browser(verb: &str) -> Outcome<RenderData> {
    tracing::info!(verb, "render: browser engine has no layout output yet");
    Err(refusal(
        "E-ENGINE-UNSUPPORTED",
        "--engine browser does not write layout-solve JSON yet",
    )
    .with_remedy("use --engine solve, or `crunk gallery render` for screenshots")
    .into())
}

impl Command for Render {
    type Data = RenderData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<RenderArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<RenderArgs>(m)?;
        Ok(Self {
            engine: a.engine,
            out: a.out,
            select: a.select,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<RenderData> {
        if self.engine == "browser" {
            return browser("render");
        }
        let plan = plan(ctx, &self.select)?;
        let results = solve_all(&plan);
        let mut data = RenderData {
            engine: self.engine.clone(),
            cells: Vec::new(),
        };
        let mut text = plan.skipped.clone();
        let mut failures = Vec::new();
        for (item, result) in plan.items.iter().zip(results) {
            let label = format!("{}/{} on {}", item.screen, item.state, item.platform);
            let rel = cell_file(&self.out, item);
            let wrote = result.and_then(|s| {
                write_file(&plan.root.join(&rel), &s.json)?;
                Ok(s.nodes)
            });
            match wrote {
                Ok(nodes) => {
                    tracing::info!(cell = %label, nodes, "render: cell written");
                    text.push(format!("{label}: {}", posix(&rel)));
                    data.cells.push(RenderedCell {
                        screen: item.screen.clone(),
                        state: item.state.clone(),
                        platform: item.platform.clone(),
                        path: posix(&rel),
                        nodes,
                    });
                }
                Err(e) => {
                    tracing::info!(cell = %label, error = %e, "render: cell failed");
                    failures.push(format!("{label}: {e}"));
                }
            }
        }
        if failures.is_empty() {
            return Ok(Payload::new(data).with_rendered(text));
        }
        let value = serde_json::to_value(&data).map_err(CliError::internal)?;
        Err(CliError::Gate {
            message: format!("render: {} cell(s) failed", failures.len()),
            data: value,
            warnings: failures,
        })
    }
}
