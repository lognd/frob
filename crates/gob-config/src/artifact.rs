//! Inventory of generated artifacts: products register pages and schemas, `cargo dev gen` iterates.

/// Which `cargo dev gen` family an artifact belongs to.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ArtifactFamily {
    /// A configuration reference page (`cargo dev gen config`).
    Config,
    /// A JSON Schema file (`cargo dev gen schemas`).
    Schemas,
}

/// The body a product renders for one artifact; the generator adds the header comment.
#[derive(Debug, Clone, PartialEq)]
pub enum ArtifactBody {
    /// Markdown text without the generated-file header.
    Markdown(String),
    /// A JSON document; the generator inserts its `$comment` field.
    Json(serde_json::Value),
}

/// A registered generated file: repo-relative path, family and renderer.
#[derive(Debug, Clone, Copy)]
pub struct ArtifactEntry {
    /// Repo-relative output path.
    pub path: &'static str,
    /// Generator family that selects this artifact.
    pub family: ArtifactFamily,
    /// Pure renderer of the body.
    pub render: fn() -> ArtifactBody,
}

inventory::collect!(ArtifactEntry);

/// Every artifact registered by a linked product, in registration order.
pub fn all_artifacts() -> impl Iterator<Item = &'static ArtifactEntry> {
    inventory::iter::<ArtifactEntry>.into_iter()
}
