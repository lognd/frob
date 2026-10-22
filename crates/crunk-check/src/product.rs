//! crunk as a [`gob_check::Product`]: the design spec and the ingested styles as inputs, the rules
//! of the `product_rules!` list as the rule set.

use std::sync::Arc;

use crunk_ingest::{INGEST_VERSION, ProjectStyles};
use gob_check::{
    CheckError, CollectCx, Collected, FileCheck, NoScope, Product, RepoGroup, RuleSet, Snapshot,
};
use gob_rules::{BoundException, Finding, Resolved, apply_exceptions};
use gob_text::FileInterner;

use crunk_rules::CrunkHost;
use crunk_rules::tailwind::TailwindFacts;
use crunk_spec::DesignSpec;

use crate::{PRODUCT, product_rules};

/// Language tags whose files can carry `crunk:waive` comments (CSS, TS/TSX style props, HTML).
const STYLE_TAGS: [&str; 6] = ["css", "tsx", "jsx", "ts", "js", "html"];

/// Thread-safe facts the pipeline reads for applicability and cache keys (none yet).
#[derive(Debug, Clone, Copy, Default)]
pub struct CrunkShared;

/// Everything crunk's rules read besides the walk: the validated design spec, when `crunk.toml`
/// has one, and the styles ingested under it.
#[derive(Debug, Default)]
pub struct CrunkInputs {
    /// `None` when `crunk.toml` is absent or invalid; the spec rules are then not applicable.
    pub spec: Option<DesignSpec>,
    /// `None` when there is no spec or the ingest could not start (a `css_root` that is a file).
    pub styles: Option<ProjectStyles>,
    /// The Tailwind theme and compiled utilities; `None` when there are no styles to scan.
    pub tailwind: Option<TailwindFacts>,
    // frob:ticket 01M4CXSM408E7A05DWKENDB7V4
    /// Judged human-review subjects (crunk.md 4.1); `None` when there is no spec.
    pub reviews: Option<crunk_rules::review::ReviewFacts>,
    // frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8
    /// The authored `design/tokens/*.toml` files, compiled one by one.
    pub tokens: Option<crunk_rules::token_files::TokenFacts>,
    // frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62
    /// The authored `design/scenes/*.scene.json` files, parsed and solved (T1).
    pub scenes: Option<crunk_rules::scene_files::SceneFacts>,
    // frob:ticket 01M5H30AMSB0THE4GW322D4K54
    /// The authored `design/scenes/*.scene.html` files, parsed (the SCENE rules' input).
    pub scene_docs: Option<crunk_rules::scene_docs::SceneDocFacts>,
    // frob:ticket 01M4CXR96GDDX460SZZVAAWD0R
    /// The authored `design/content/*.toml` copy files (the CONTENT rules' input).
    pub content: Option<crunk_rules::content_files::ContentFacts>,
    // frob:ticket 01M4CXR89ERNB60CEDG60E2DXH
    /// The authored `design/screens/*.screen.toml` files, parsed (the STATE rules' input).
    pub screens: Option<crunk_rules::screen_files::ScreenFacts>,
    /// The authored `design/components/*.component.toml` files, parsed (the COMP rules' input).
    // frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F
    pub components: Option<crunk_rules::component_files::ComponentFacts>,
}

impl CrunkHost for CrunkInputs {
    fn spec(&self) -> Option<&DesignSpec> {
        self.spec.as_ref()
    }

    fn styles(&self) -> Option<&ProjectStyles> {
        self.styles.as_ref()
    }

    fn tailwind(&self) -> Option<&TailwindFacts> {
        self.tailwind.as_ref()
    }

    // frob:ticket 01M4CXSM408E7A05DWKENDB7V4
    fn reviews(&self) -> Option<&crunk_rules::review::ReviewFacts> {
        self.reviews.as_ref()
    }

    fn tokens(&self) -> Option<&crunk_rules::token_files::TokenFacts> {
        self.tokens.as_ref()
    }

    // frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62
    fn scenes(&self) -> Option<&crunk_rules::scene_files::SceneFacts> {
        self.scenes.as_ref()
    }

    // frob:ticket 01M4CXR89ERNB60CEDG60E2DXH
    fn screens(&self) -> Option<&crunk_rules::screen_files::ScreenFacts> {
        self.screens.as_ref()
    }
    fn scene_docs(&self) -> Option<&crunk_rules::scene_docs::SceneDocFacts> {
        self.scene_docs.as_ref()
    }
    fn content(&self) -> Option<&crunk_rules::content_files::ContentFacts> {
        self.content.as_ref()
    }

    fn components(&self) -> Option<&crunk_rules::component_files::ComponentFacts> {
        self.components.as_ref()
    }
}

/// The host the declared rules judge: crunk's inputs.
fn host<'a>(_: &'a Crunk, snap: &'a Snapshot<Crunk>) -> &'a (dyn CrunkHost + 'static) {
    &snap.inputs
}

/// The waivers of every style-bearing file: the `crunk:waive` comments that carry a reason.
fn waiver_exceptions(snap: &Snapshot<Crunk>) -> Vec<BoundException> {
    let mut bound = Vec::new();
    for entry in snap
        .core
        .entries
        .iter()
        .filter(|e| STYLE_TAGS.contains(&e.language.tag()))
    {
        let Ok(text) = snap.core.text(&entry.path) else {
            tracing::debug!(path = %entry.path, "waivers: cannot read file");
            continue;
        };
        if text.contains("crunk:waive") {
            bound.extend(crunk_rules::waiver::exceptions(&entry.path, &text));
        }
    }
    tracing::debug!(waivers = bound.len(), "crunk waivers bound");
    bound
}

/// The crunk product driving the shared check pipeline.
#[derive(Debug, Clone, Copy, Default)]
pub struct Crunk;

impl Product for Crunk {
    type Shared = CrunkShared;
    type Inputs = CrunkInputs;
    type Scope = NoScope;

    fn name(&self) -> &'static str {
        PRODUCT
    }

    // frob:ticket 01M4FD0EP322SV5ZNXD5SQT8RX
    fn telemetry_dir(&self, root: &std::path::Path) -> std::path::PathBuf {
        // The shared cache dir lives under the git dir, so a check never leaves a file in the worktree.
        gob_cache::shared_dir(root, &self.state_dir())
            .unwrap_or_else(|| root.join(self.state_dir()))
    }

    fn collect(&self, cx: &mut CollectCx<'_>) -> Result<Collected<Self>, CheckError> {
        let spec = match crunk_spec::load_spec(&cx.core.root) {
            Ok(spec) => Some(spec),
            Err(err @ crunk_spec::SpecError::Missing { reason: None, .. }) => {
                tracing::info!(%err, "crunk collect: no crunk.toml; spec rules do not apply");
                None
            }
            Err(err) => {
                tracing::warn!(%err, "crunk collect: crunk.toml is unusable; the check refuses to run");
                return Err(CheckError::Config(err.into_config_error()));
            }
        };
        let styles = spec.as_ref().and_then(|spec| {
            match crunk_ingest::ingest_tree(spec, cx.cache) {
                Ok(ingested) => {
                    tracing::info!(
                        sheets = ingested.styles.sheets.len(),
                        parsed = ingested.stats.parsed,
                        cached = ingested.stats.cached,
                        "crunk collect: styles ingested"
                    );
                    Some(ingested.styles)
                }
                Err(err) => {
                    tracing::warn!(%err, "crunk collect: ingest failed; style rules do not apply");
                    None
                }
            }
        });
        let tailwind = spec
            .as_ref()
            .zip(styles.as_ref())
            .map(|(spec, styles)| crate::tailwind::collect(spec, styles, &self.state_dir()));
        // frob:ticket 01M4CXSM408E7A05DWKENDB7V4
        let reviews = spec.as_ref().map(|spec| {
            crate::review::gather(spec, &crate::review::GitSignatures::new(&cx.core.root))
        });
        // frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8
        let tokens = spec
            .as_ref()
            .map(crunk_rules::token_files::TokenFacts::load);
        // frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62
        let scenes = spec
            .as_ref()
            .map(crunk_rules::scene_files::SceneFacts::load);
        // frob:ticket 01M5H30AMSB0THE4GW322D4K54
        let scene_docs = spec
            .as_ref()
            .map(crunk_rules::scene_docs::SceneDocFacts::load);
        // frob:ticket 01M4CXR96GDDX460SZZVAAWD0R
        let content = spec
            .as_ref()
            .map(crunk_rules::content_files::ContentFacts::load);
        // frob:ticket 01M4CXR89ERNB60CEDG60E2DXH
        let screens = spec
            .as_ref()
            .map(crunk_rules::screen_files::ScreenFacts::load);
        // frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F
        let components = spec
            .as_ref()
            .map(crunk_rules::component_files::ComponentFacts::load);
        Ok(Collected {
            shared: CrunkShared,
            inputs: CrunkInputs {
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
            },
            findings: Vec::new(),
        })
    }

    fn rule_set(&self) -> RuleSet<Self> {
        RuleSet::new().bind(product_rules::rules(), host)
    }

    fn file_checks(&self) -> Vec<Arc<dyn FileCheck<Self>>> {
        Vec::new()
    }

    fn repo_groups(&self) -> Vec<RepoGroup<Self>> {
        Vec::new()
    }

    fn repo_digest(&self, snap: &Snapshot<Self>) -> Vec<u8> {
        let mut digest = format!("crunk/rules/8/ingest/{INGEST_VERSION}").into_bytes();
        if let Some(spec) = &snap.inputs.spec {
            digest.extend(serde_json::to_vec(spec).unwrap_or_default());
        }
        if let Some(facts) = &snap.inputs.tailwind {
            digest.extend(facts.fingerprint().into_bytes());
        }
        if let Some(facts) = &snap.inputs.reviews {
            // frob:ticket 01M4CXSM408E7A05DWKENDB7V4
            digest.extend(format!("{facts:?}").into_bytes());
        }
        if let Some(facts) = &snap.inputs.tokens {
            // frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8
            digest.extend(facts.fingerprint().into_bytes());
        }
        if let Some(facts) = &snap.inputs.scenes {
            // frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62
            digest.extend(facts.fingerprint().into_bytes());
        }
        if let Some(facts) = &snap.inputs.scene_docs {
            // frob:ticket 01M5H30AMSB0THE4GW322D4K54
            digest.extend(facts.fingerprint().into_bytes());
        }
        if let Some(facts) = &snap.inputs.content {
            // frob:ticket 01M4CXR96GDDX460SZZVAAWD0R
            digest.extend(facts.fingerprint().into_bytes());
        }
        if let Some(facts) = &snap.inputs.screens {
            // frob:ticket 01M4CXR89ERNB60CEDG60E2DXH
            digest.extend(facts.fingerprint().into_bytes());
        }
        if let Some(facts) = &snap.inputs.components {
            // frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F
            digest.extend(facts.fingerprint().into_bytes());
        }
        if let Some(spec) = &snap.inputs.spec {
            // TOKENS001 reads the generated files from disk, outside the walk.
            digest
                .extend(format!("{:?}", crunk_rules::tokens_drift::check(spec).ok()).into_bytes());
        }
        digest
    }

    fn resolve_exceptions(
        &self,
        snap: &Snapshot<Self>,
        files: &FileInterner,
        raw: Vec<Finding>,
    ) -> Resolved {
        let ctx = gob_rules::ExceptionCtx { files };
        let resolved = apply_exceptions(raw, &waiver_exceptions(snap), &ctx);
        let findings = match &snap.inputs.spec {
            Some(spec) => crunk_rules::lint::apply(spec, resolved.findings),
            None => resolved.findings,
        };
        Resolved {
            findings,
            suppressed: resolved.suppressed,
        }
    }
}
