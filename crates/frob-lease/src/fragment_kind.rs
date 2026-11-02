//! The changelog fragment type, shared down from frob-release so lease scope rules need no upward edge.

/// Fragment type, declared in rendering order.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum FragmentKind {
    /// Lead notice: one paragraph above the type groups of a release section (at most one per section).
    Notice,
    /// New capability.
    Added,
    /// Changed behaviour.
    Changed,
    /// Bug fix.
    Fixed,
    /// Removed capability.
    Removed,
    /// Will be removed later.
    Deprecated,
    /// Security fix.
    Security,
}

impl FragmentKind {
    /// Every type in rendering order.
    pub const ALL: [FragmentKind; 7] = [
        FragmentKind::Notice,
        FragmentKind::Added,
        FragmentKind::Changed,
        FragmentKind::Fixed,
        FragmentKind::Removed,
        FragmentKind::Deprecated,
        FragmentKind::Security,
    ];

    /// The lowercase file-name segment.
    pub fn as_str(self) -> &'static str {
        match self {
            FragmentKind::Notice => "notice",
            FragmentKind::Added => "added",
            FragmentKind::Changed => "changed",
            FragmentKind::Fixed => "fixed",
            FragmentKind::Removed => "removed",
            FragmentKind::Deprecated => "deprecated",
            FragmentKind::Security => "security",
        }
    }

    /// The section heading, e.g. `Added`.
    pub fn title(self) -> &'static str {
        match self {
            FragmentKind::Notice => "Notice",
            FragmentKind::Added => "Added",
            FragmentKind::Changed => "Changed",
            FragmentKind::Fixed => "Fixed",
            FragmentKind::Removed => "Removed",
            FragmentKind::Deprecated => "Deprecated",
            FragmentKind::Security => "Security",
        }
    }

    /// Parse a file-name segment.
    pub fn parse(s: &str) -> Option<FragmentKind> {
        FragmentKind::ALL.into_iter().find(|k| k.as_str() == s)
    }

    /// Comma-separated valid segments, for error messages.
    pub fn valid_list() -> String {
        FragmentKind::ALL.map(FragmentKind::as_str).join(", ")
    }
}
