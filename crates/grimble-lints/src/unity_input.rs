//! `UNITY301`: the legacy `Input` class used in a project whose active input handler is the Input
//! System.
//!
//! The handler is the `activeInputHandler` key of `ProjectSettings/ProjectSettings.asset`
//! ([`active_input_handler`]); the rule fires only when it is [`InputHandler::InputSystem`], since
//! `Both` keeps the legacy API working. In that mode Unity defines `ENABLE_INPUT_SYSTEM` and not
//! `ENABLE_LEGACY_INPUT_MANAGER`, so code under `#if ENABLE_LEGACY_INPUT_MANAGER` is dead and is
//! skipped. A file that declares its own `Input` symbol cannot be told apart from Unity's, so its
//! hits are Unknown (Unresolved), never Warn.

// frob:ticket 01M4D94ZPDYBATXNCVY3XRQ6RM

use gob_languages::Language;
use tree_sitter::Node;

use crate::res::{Certainty, ScanError, normalise, span, text};
use crate::unity_common::{Finding, walk};

/// The rule id reported on every finding.
pub const RULE: &str = "UNITY301";

/// Which input APIs the Unity project compiles in (`activeInputHandler`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InputHandler {
    /// 0: the legacy Input Manager only (the Unity default).
    Legacy,
    /// 1: the Input System package only.
    InputSystem,
    /// 2: both, so the legacy API still works.
    Both,
}

/// Members of the legacy `Input` class that do not exist under the Input System handler.
const LEGACY_MEMBERS: &[&str] = &[
    "GetKey",
    "GetKeyDown",
    "GetKeyUp",
    "GetButton",
    "GetButtonDown",
    "GetButtonUp",
    "GetAxis",
    "GetAxisRaw",
    "GetMouseButton",
    "GetMouseButtonDown",
    "GetMouseButtonUp",
    "GetTouch",
    "GetJoystickNames",
    "GetAccelerationEvent",
    "mousePosition",
    "mouseScrollDelta",
    "touches",
    "touchCount",
    "anyKey",
    "anyKeyDown",
    "acceleration",
    "accelerationEvents",
    "inputString",
];

/// The `#if` symbols Unity defines when the Input System is the only handler.
const INPUT_SYSTEM_DEFINES: &[(&str, bool)] = &[
    ("ENABLE_INPUT_SYSTEM", true),
    ("ENABLE_LEGACY_INPUT_MANAGER", false),
];

/// Reads `activeInputHandler` from the text of `ProjectSettings.asset`.
///
/// A missing key is [`InputHandler::Legacy`] (Unity omits nothing, but an old asset may); a value
/// that is not 0, 1 or 2 is `None` so the caller reports the rule not applicable.
pub fn active_input_handler(settings: &str) -> Option<InputHandler> {
    let value = settings.lines().find_map(|l| {
        l.trim()
            .strip_prefix("activeInputHandler:")
            .map(|v| v.trim().to_owned())
    });
    let handler = match value.as_deref() {
        None | Some("0") => Some(InputHandler::Legacy),
        Some("1") => Some(InputHandler::InputSystem),
        Some("2") => Some(InputHandler::Both),
        Some(_) => None,
    };
    tracing::debug!(?handler, "active input handler read");
    handler
}

/// True when the file declares its own `Input` (type, member, parameter, local or alias).
fn declares_input(language: Language, src: &str) -> Result<bool, ScanError> {
    let mut found = false;
    walk(language, src, &[], |n| {
        let named = |kind: &str| {
            n.child_by_field_name(kind)
                .is_some_and(|c| text(c, src) == "Input")
        };
        found |= match n.kind() {
            "class_declaration"
            | "struct_declaration"
            | "interface_declaration"
            | "enum_declaration"
            | "record_declaration"
            | "variable_declarator"
            | "parameter"
            | "property_declaration" => named("name"),
            "using_directive" => text(n, src).replace(' ', "").contains("Input="),
            _ => false,
        };
    })?;
    Ok(found)
}

/// True when the file has `using static UnityEngine.Input;`.
fn uses_static_input(language: Language, src: &str) -> Result<bool, ScanError> {
    let mut found = false;
    walk(language, src, &[], |n| {
        found |= n.kind() == "using_directive"
            && text(n, src)
                .split_whitespace()
                .collect::<String>()
                .contains("usingstaticUnityEngine.Input;");
    })?;
    Ok(found)
}

/// The legacy member a node reads, if it is `Input.<member>` or a bare static-import call.
fn legacy_member<'s>(n: Node<'_>, src: &'s str, bare: bool) -> Option<&'s str> {
    match n.kind() {
        "member_access_expression" => {
            let recv = normalise(text(n.child_by_field_name("expression")?, src));
            let name = text(n.child_by_field_name("name")?, src);
            (matches!(recv.as_str(), "Input" | "UnityEngine.Input")
                && LEGACY_MEMBERS.contains(&name))
            .then_some(name)
        }
        "invocation_expression" if bare => {
            let f = n.child_by_field_name("function")?;
            let name = text(f, src);
            (f.kind() == "identifier" && LEGACY_MEMBERS.contains(&name)).then_some(name)
        }
        _ => None,
    }
}

/// Legacy `Input` uses in `src` when the project handler is `handler`.
///
/// Nothing is reported unless `handler` is [`InputHandler::InputSystem`] or the language is not C#.
///
/// # Errors
///
/// [`ScanError::Parse`] when the file does not parse within the limits.
pub fn scan(
    language: Language,
    src: &str,
    handler: InputHandler,
) -> Result<Vec<Finding>, ScanError> {
    if handler != InputHandler::InputSystem {
        tracing::debug!(
            ?handler,
            "legacy input is available, UNITY301 not applicable"
        );
        return Ok(Vec::new());
    }
    let shadowed = declares_input(language, src)?;
    let bare = uses_static_input(language, src)?;
    let mut out = Vec::new();
    walk(language, src, INPUT_SYSTEM_DEFINES, |n| {
        if let Some(member) = legacy_member(n, src, bare) {
            let certainty = if shadowed {
                Certainty::Unknown
            } else {
                Certainty::Certain
            };
            out.push(Finding {
                rule: RULE,
                range: span(n.start_byte(), n.end_byte()),
                certainty,
                message: format!(
                    "Input.{member} is the legacy Input Manager API, but this project's active input handler is the Input System; use InputSystem actions or devices"
                ),
            });
        }
    })?;
    out.sort_by_key(|f| f.range.start());
    out.dedup_by_key(|f| f.range);
    tracing::debug!(findings = out.len(), shadowed, "legacy input scanned");
    Ok(out)
}
