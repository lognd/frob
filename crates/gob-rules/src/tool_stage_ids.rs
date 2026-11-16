//! The declared ids external tool stages may emit (org audit R5).
//!
//! A tool stage (gob-check `tool_parse.rs`) names ids in two roles: the frob rule a finding maps
//! to ([`FROB_IDS`]) and the tool's own native id used as a map key ([`NATIVE_IDS`]). Both lists
//! are declared here once; a test scans the emitting source and fails on any undeclared id.

// frob:ticket 01M61MM4H8E5N93CRKFTREB77M

/// Frob rule ids a tool stage can map a finding to (including sibling-product `CI` ids).
pub const FROB_IDS: &[&str] = &[
    "A11Y001",
    "CI001",
    "CI003",
    "CI006",
    "CI007",
    "CI010",
    "CI013",
    "CI014",
    "CI015",
    "CONC001",
    "DEAD001",
    "ERR001",
    "ERR003",
    "FMT001",
    "LINT001",
    "LOGIC001",
    "NEAT002",
    "REACT001",
    "SPELL001",
    "TESTQ001",
    "TOOL002",
    "TYPING001",
    "UNITY101",
    "VERSION001",
    "WCSS001",
    "WCSS002",
    "WCSS003",
];

/// Native ids of external tools that a stage's id map keys on.
pub const NATIVE_IDS: &[&str] = &[
    "BLE001", "CS0168", "CS0219", "CS8019", "E722", "F401", "F841", "IDE0005", "IDE0051",
    "IDE0052", "IDE0060", "PLR2004", "RS0016", "RS0017", "S110",
];

/// True when `id` is a declared tool-stage id, frob or native.
pub fn is_declared_stage_id(id: &str) -> bool {
    FROB_IDS.contains(&id) || NATIVE_IDS.contains(&id)
}
