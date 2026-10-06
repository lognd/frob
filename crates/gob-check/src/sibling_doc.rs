//! Typed shape of the `gob.sibling/1` document and the generated `docs/schemas/sibling.json`
//! (sibling-contract.md section 3, products.md section 7).
//!
//! The emitter-built parts ([`SiblingDocument`], [`FindingRow`], [`RuleRecord`], ...) serialize
//! through these structs, so the schema and the document share one definition. The rows a product
//! supplies as JSON (`entities`, `bindings`, `exceptions`, `fidelity`, `packs`) stay `Value` on the
//! emitting side and carry their typed row struct only for the schema (`schemars(with)`).
//! Field order is the emission order: `serde_json` keeps insertion order, so reordering a field
//! changes the bytes of every sibling document.

use schemars::{JsonSchema, SchemaGenerator, generate::SchemaSettings};
use serde::Serialize;
use serde_json::{Value, json};

/// Half-open byte range inside the file named by the owning record.
#[derive(Debug, Clone, Copy, Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Range {
    /// Byte offset of the first byte.
    pub start: u32,
    /// Byte offset one past the last byte.
    pub end: u32,
}

/// Declared polarity of a rule (universal-model.md 4.2); serialized as the symbol.
#[derive(Debug, Clone, Copy, Serialize, JsonSchema)]
pub enum PolarityMark {
    /// Positive.
    #[serde(rename = "P+")]
    Plus,
    /// Negative.
    #[serde(rename = "P-")]
    Minus,
    /// Zero.
    P0,
    /// Neutral.
    Pn,
    /// Conditional.
    Pc,
}

/// The `compute` object: the `[compute]` knobs with defaults materialized (what the digest hashes).
#[derive(Debug, Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ComputeKnobs {
    /// `[compute] public_signatures`.
    pub public_signatures: String,
    /// `[compute] effects`.
    pub effects: String,
    /// `[compute] dynamic_calls`.
    pub dynamic_calls: String,
    /// `[compute] expansion_steps`.
    pub expansion_steps: u64,
    /// `[compute] normalization`.
    pub normalization: String,
    /// `[compute] notebook_order`.
    pub notebook_order: String,
}

/// Echo of the arguments the product honoured, so frob can verify its request was applied.
#[derive(Debug, Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Invocation {
    /// The verb that produced the document.
    #[schemars(extend("enum" = ["check"]))]
    pub verb: String,
    /// Repository root all paths are relative to; always `.`.
    #[schemars(extend("const" = "."))]
    pub root: String,
    /// The `--ticket-scope` paths the run honoured, or null when the run was unscoped.
    #[schemars(required)]
    pub ticket_scope: Option<Vec<String>>,
    /// The `--base` ref the run diffed against, or null when no diff-scoped rule ran.
    #[schemars(required)]
    pub base: Option<String>,
}

/// Run timing.
#[derive(Debug, Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Timing {
    /// Wall time of the run in milliseconds.
    pub elapsed_ms: u64,
}

/// Per-rule subject counts; a rule that ran with zero subjects appears with `subjects_examined` 0.
#[derive(Debug, Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct RuleRecord {
    /// Rule id.
    pub rule: String,
    /// Declared polarity.
    pub polarity: PolarityMark,
    /// Subjects examined across the whole run.
    pub subjects_examined: u64,
    /// Live findings of this rule.
    pub findings: u64,
    /// Suppressed findings of this rule.
    pub suppressed: u64,
    /// Unresolved sites of this rule.
    pub unresolved: u64,
}

/// A finding as the landed record plus the sibling's extras.
#[derive(Debug, Serialize, JsonSchema)]
#[schemars(extend(
    "unevaluatedProperties" = false,
    "required" = ["rule", "slug", "severity", "file", "line", "column", "message", "fingerprint", "fix", "required", "polarity", "subjects_examined", "reason", "maybe", "anchor", "entity", "remedy", "range"],
    "if" = {"properties": {"severity": {"const": "unresolved"}}, "required": ["severity"]},
    "then" = {"properties": {"reason": {"type": "string"}}},
    "else" = {"properties": {
        "maybe": {"maxItems": 0}, "reason": {"type": "null"}, "required": {"type": "null"}
    }},
))]
pub struct FindingRow {
    /// The landed finding record.
    #[serde(flatten)]
    pub record: gob_diagnostics::FindingRecord,
    /// Declared polarity of the rule (universal-model.md 4.2).
    pub polarity: PolarityMark,
    /// Subjects the rule examined in the scope this finding rolls up; zero only with a vacuous Unresolved.
    pub subjects_examined: u64,
    /// Unresolved reason code (kebab-case such as `vacuous`, `fidelity`); null unless severity is unresolved.
    #[schemars(regex(pattern = "^[a-z][a-z0-9-]*$"))]
    pub reason: Option<String>,
    /// For Unresolved on P+ rules: the maybe-set `hi` minus `lo`; empty otherwise.
    pub maybe: Vec<String>,
    /// Logical location such as `node/cli/owns[0]`, or null for a code location.
    #[schemars(regex(pattern = "^[a-z]+/[A-Za-z0-9_.:/\\[\\]-]+$"))]
    pub anchor: Option<String>,
    /// The `kind/name` of the entity the finding concerns, or null.
    #[schemars(regex(pattern = "^[a-z]+/[A-Za-z0-9_.:/\\[\\]-]+$"))]
    pub entity: Option<String>,
    /// The exact corrected command or edit, when one exists.
    pub remedy: Option<String>,
    /// Byte range of the span in `file`, or null.
    pub range: Option<Range>,
}

/// A finding parked by an exception.
#[derive(Debug, Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct SuppressedFinding {
    /// The finding as it would have been reported.
    pub finding: FindingRow,
    /// The `id` of the exception record that suppressed it.
    pub exception: String,
}

/// The `packs` array and its digest; both or neither are emitted.
#[derive(Debug, Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct PackRef {
    /// Pack id, `<namespace>/<name>`.
    pub name: String,
    /// Semantic version of the pack.
    pub version: String,
    /// Pack digest of packs.md 2.5.
    #[schemars(regex(pattern = "^blake3:[0-9a-f]{64}$"))]
    pub digest: String,
}

/// The data payload of `<product> check --json`.
#[derive(Debug, Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
#[schemars(extend("dependentRequired" = {"packs": ["packs_digest"], "packs_digest": ["packs"]}))]
pub struct SiblingDocument {
    /// Contract name and major.
    #[schemars(extend("const" = "gob.sibling/1"))]
    pub schema_version: String,
    /// Producing product.
    #[schemars(extend("enum" = ["grimble", "crunk"]))]
    pub product: String,
    /// Semantic version of the producing binary.
    pub product_version: String,
    /// blake3 of the canonical JSON of the `compute` object.
    #[schemars(regex(pattern = "^blake3:[0-9a-f]{64}$"))]
    pub compute_digest: String,
    /// The `[compute]` knobs with defaults materialized; what the digest hashes.
    #[schemars(with = "ComputeKnobs")]
    pub compute: Value,
    /// Echo of the arguments the product honoured.
    pub invocation: Invocation,
    /// One entry per language the run saw, sorted by language id.
    #[schemars(with = "Vec<Fidelity>")]
    pub fidelity: Vec<Value>,
    /// One entry per rule that ran, sorted by rule id.
    pub rules: Vec<RuleRecord>,
    /// Live findings, sorted by file, line, rule.
    pub findings: Vec<FindingRow>,
    /// Findings parked by an exception.
    pub suppressed: Vec<SuppressedFinding>,
    /// Every parsed exception, including those suppressing nothing.
    #[schemars(with = "Vec<ExceptionRecord>")]
    pub exceptions: Vec<Value>,
    /// Model entities; empty for a product with no model.
    #[schemars(with = "Vec<Entity>")]
    pub entities: Vec<Value>,
    /// Rows of B; empty for a product with no model.
    #[schemars(with = "Vec<Binding>")]
    pub bindings: Vec<Value>,
    /// Run timing.
    pub timing: Timing,
    /// Enabled data packs used by the run, sorted by name; omitted by products without packs.
    #[serde(skip_serializing_if = "Option::is_none")]
    #[schemars(with = "Option<Vec<PackRef>>")]
    pub packs: Option<Vec<Value>>,
    /// blake3 of the canonical JSON of the `packs` array; present exactly when `packs` is.
    #[serde(skip_serializing_if = "Option::is_none")]
    #[schemars(regex(pattern = "^blake3:[0-9a-f]{64}$"))]
    pub packs_digest: Option<String>,
}

/// Detector answer for one atom in one language: `typed` and `lexical` are precisions, `none` is
/// no detector (unknown), `not_applicable` is declared impossible.
#[derive(Debug, Serialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Capability {
    /// Typed detector.
    Typed,
    /// Lexical detector.
    Lexical,
    /// No detector.
    None,
    /// Declared impossible.
    NotApplicable,
}

/// Fidelity level of universal-model.md 3.3.
#[derive(Debug, Serialize, JsonSchema)]
pub enum Level {
    /// Opaque.
    F0,
    /// Lexical.
    F1,
    /// Structural.
    F2,
    /// Typed.
    F3,
    /// Full.
    F4,
}

/// Fidelity of one language: level, capability precisions and the rules that do not apply.
#[derive(Debug, Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Fidelity {
    /// Language id as in the adapter registry.
    pub language: String,
    /// Adapter id.
    pub adapter: String,
    /// Adapter version.
    pub adapter_version: String,
    /// Fidelity level of universal-model.md 3.3.
    pub level: Level,
    /// Detector answer per capability atom, keyed by pack-qualified atom id.
    pub capabilities: std::collections::BTreeMap<String, Capability>,
    /// Rules whose whole scope is `NotApplicable` in this language (listed once, never findings).
    pub not_applicable_rules: Vec<String>,
}

/// Exception kind (exceptions.md section 1).
#[derive(Debug, Serialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum ExceptionKind {
    /// Accepted.
    Accept,
    /// Deferred.
    Defer,
    /// Hotfix.
    Hotfix,
    /// Baseline pool key.
    Baseline,
}

/// Exit state: `unresolved_exit` whenever `ticket` is set (only frob evaluates ticket-bound exits).
#[derive(Debug, Serialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum ExitState {
    /// Evaluated by the product.
    Evaluated,
    /// Left to frob.
    UnresolvedExit,
}

/// Outcome of the exits the product itself evaluated (date, digest, staleness).
#[derive(Debug, Serialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum ExceptionStatus {
    /// In force.
    Active,
    /// Past its digest.
    Stale,
    /// Needs reattestation.
    Reattest,
    /// Date passed.
    Expired,
}

/// One parsed exception, whether or not it currently suppresses a finding.
#[derive(Debug, Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
#[schemars(extend("allOf" = [
    {
        "if": {"properties": {"ticket": {"type": "string"}}, "required": ["ticket"]},
        "then": {"properties": {"exit_state": {"const": "unresolved_exit"}}},
        "else": {"properties": {"exit_state": {"const": "evaluated"}}},
    },
    {
        "if": {"properties": {"kind": {"const": "accept"}}, "required": ["kind"]},
        "then": {"properties": {"ticket": {"type": "null"}}},
    },
]))]
pub struct ExceptionRecord {
    /// Stable id: lowercase hex of the hash of kind, rule and site.
    #[schemars(regex(pattern = "^[0-9a-f]{16,64}$"))]
    pub id: String,
    /// Exception kind (exceptions.md section 1).
    pub kind: ExceptionKind,
    /// The excepted rule id.
    pub rule: String,
    /// Anchor, symref or glob the exception applies to.
    pub on: String,
    /// Repository-relative file holding the exception, or null for a baseline pool key.
    #[schemars(required)]
    pub file: Option<String>,
    /// 1-based line of the exception, or null.
    #[schemars(required)]
    pub line: Option<u32>,
    /// The reason text, verbatim.
    pub because: String,
    /// ISO date `YYYY-MM-DD` of the optional date exit, or null.
    #[schemars(regex(pattern = "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"))]
    #[schemars(required)]
    pub until: Option<String>,
    /// The `ticket=` value, verbatim and opaque: the sibling never resolves it.
    #[schemars(required)]
    pub ticket: Option<String>,
    /// Exit state of the exception.
    pub exit_state: ExitState,
    /// Outcome of the exits the product itself evaluated, or null when none was evaluated.
    #[schemars(required)]
    pub status: Option<ExceptionStatus>,
    /// Number of findings this exception suppressed in this run.
    pub suppresses: u32,
}

/// Entity kind.
#[derive(Debug, Serialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum EntityKind {
    /// A node.
    Node,
    /// A flow.
    Flow,
    /// A contract.
    Contract,
    /// A claim.
    Claim,
    /// A vmodel.
    Vmodel,
    /// A boundary.
    Boundary,
    /// A pack.
    Pack,
}

/// A frob directive attached to an entity by the position rule of grmb-spec 8.1.
#[derive(Debug, Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Directive {
    /// Only `frob:` directives are handed over; grimble consumes its own.
    #[schemars(extend("enum" = ["frob"]))]
    pub namespace: String,
    /// Directive verb such as `ticket`, `doc`, `tests`.
    pub verb: String,
    /// Raw argument text after the verb, for frob's own directive parser.
    pub args: String,
    /// 1-based line of the comment.
    pub line: u32,
    /// Byte range of the comment.
    pub range: Range,
}

/// A model entity with its span, facet digests and attached frob directives.
#[derive(Debug, Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Entity {
    /// `kind/full-name`, the `design:` link target.
    #[schemars(regex(pattern = "^[a-z]+/[A-Za-z0-9_.:/\\[\\]-]+$"))]
    pub anchor: String,
    /// Entity kind.
    pub kind: EntityKind,
    /// Full name including namespace prefixes.
    pub name: String,
    /// The model module name.
    pub module: String,
    /// Repository-relative path of the declaring .grmb file.
    pub file: String,
    /// 1-based line of the declaration.
    pub line: u32,
    /// Byte range of the declaration.
    pub range: Range,
    /// Body facet digest, or null when unavailable.
    #[schemars(regex(pattern = "^blake3:[0-9a-f]{64}$"))]
    #[schemars(required)]
    pub body_digest: Option<String>,
    /// Doc facet digest, or null when unavailable.
    #[schemars(regex(pattern = "^blake3:[0-9a-f]{64}$"))]
    #[schemars(required)]
    pub doc_digest: Option<String>,
    /// Digest scheme version of the two digests.
    pub digest_scheme: u32,
    /// Transitional names (grmb-spec 4), so old `design:` links still resolve.
    pub renamed_from: Vec<String>,
    /// frob directives attached to this entity.
    pub directives: Vec<Directive>,
}

/// Role of a binding row (binding.md 1.2).
#[derive(Debug, Serialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum Role {
    /// Owns.
    Owns,
    /// Producer.
    Producer,
    /// Consumer.
    Consumer,
    /// Shape.
    Shape,
    /// Runnable.
    Runnable,
    /// Ref.
    Ref,
    /// Evidence.
    Evidence,
}

/// Status of a binding row.
#[derive(Debug, Serialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum BindingStatus {
    /// Must.
    Must,
    /// May.
    May,
    /// Unknown.
    Unknown,
}

/// A row of the relation B, projected for display.
#[derive(Debug, Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Binding {
    /// Anchor of the entity.
    #[schemars(regex(pattern = "^[a-z]+/[A-Za-z0-9_.:/\\[\\]-]+$"))]
    pub entity: String,
    /// Role (binding.md 1.2).
    pub role: Role,
    /// Symref of the bound identity, or null for the hidden remainder of rank 4.
    #[schemars(required)]
    pub identity: Option<String>,
    /// Source rank (binding.md section 2).
    #[schemars(range(min = 1, max = 4))]
    pub rank: u8,
    /// Status of the row.
    pub status: BindingStatus,
    /// Clause anchor or directive site that gave the row.
    #[schemars(required)]
    pub anchor: Option<String>,
    /// Residual reason code for rank 4 rows, null otherwise.
    #[schemars(regex(pattern = "^[a-z][a-z0-9-]*$"))]
    #[schemars(required)]
    pub reason: Option<String>,
}

/// Edge kind of the graph export.
#[derive(Debug, Serialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum EdgeKind {
    /// Flow.
    Flow,
    /// Claim operand.
    ClaimOperand,
    /// V-model link.
    VmodelLink,
    /// Include.
    Include,
    /// Extend.
    Extend,
}

/// A model edge for the graph export.
#[derive(Debug, Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Edge {
    /// Edge kind.
    pub kind: EdgeKind,
    /// Anchor of the source entity or file.
    pub from: String,
    /// Anchor of the target entity or file.
    pub to: String,
    /// Clause anchor the edge was declared at.
    #[schemars(required)]
    pub anchor: Option<String>,
    /// Anchor of the flow's contract, for `flow` edges.
    #[schemars(required)]
    pub contract: Option<String>,
}

/// The data payload of `grimble graph --json`.
#[derive(Debug, Serialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct GraphDocument {
    /// Graph contract name and major.
    #[schemars(extend("const" = "grimble.graph/1"))]
    pub schema_version: String,
    /// Always grimble.
    #[schemars(extend("const" = "grimble"))]
    pub product: String,
    /// Semantic version of the producing binary.
    pub product_version: String,
    /// As in `SiblingDocument`.
    #[schemars(regex(pattern = "^blake3:[0-9a-f]{64}$"))]
    pub compute_digest: String,
    /// The model module name.
    pub module: String,
    /// Same records as SiblingDocument.entities.
    pub entities: Vec<Entity>,
    /// Same records as SiblingDocument.bindings.
    pub bindings: Vec<Binding>,
    /// Model edges.
    pub edges: Vec<Edge>,
}

/// The strict schema of `<product> check --json` and `graph --json` stdout.
///
/// The envelope wrapper (`SiblingOutput`) is fixed text; the two payload documents and every row
/// type come from the derives above.
pub fn schema() -> Value {
    let mut generator = SchemaGenerator::new(SchemaSettings::draft2020_12());
    let sibling = generator.subschema_for::<SiblingDocument>();
    let graph = generator.subschema_for::<GraphDocument>();
    let to = |s: schemars::Schema| serde_json::to_value(s).unwrap_or(Value::Null);
    let defs_value = Value::Object(generator.take_definitions(true));
    json!({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "SiblingOutput",
        "description": "Stdout of a sibling product's `check --json` or `graph --json`: the envelope with the sibling document as `data`.",
        "type": "object",
        "required": ["already", "data", "error", "findings", "ok", "schema_version", "verb", "warnings"],
        "properties": {
            "already": {"type": "boolean", "description": "Always false for a read-only verb."},
            "data": {
                "description": "The verb payload; null only when ok is false.",
                "oneOf": [to(sibling), to(graph), {"type": "null"}],
            },
            "error": {
                "description": "Error body when ok is false.",
                "anyOf": [{"$ref": "envelope.json#/$defs/EnvelopeError"}, {"type": "null"}],
            },
            "findings": {
                "type": "array", "maxItems": 0,
                "description": "Always empty: the document's own `findings` is authoritative.",
            },
            "ok": {
                "type": "boolean",
                "description": "True when the product ran to completion; findings do not make it false.",
            },
            "schema_version": {"const": 1, "description": "Envelope layout version."},
            "verb": {"type": "string", "description": "Dotted verb path, `check` or `graph`."},
            "warnings": {"type": "array", "items": {"type": "string"}, "description": "Non-fatal notices."},
        },
        "if": {"properties": {"ok": {"const": true}}, "required": ["ok"]},
        "then": {"properties": {"data": {"type": "object"}, "error": {"type": "null"}}},
        "else": {"properties": {"data": {"type": "null"}, "error": {"type": "object"}}},
        "$defs": defs_value,
    })
}

gob_config::inventory::submit! {
    gob_config::ArtifactEntry {
        path: "docs/schemas/sibling.json",
        family: gob_config::ArtifactFamily::Schemas,
        render: || gob_config::ArtifactBody::Json(schema()),
    }
}
