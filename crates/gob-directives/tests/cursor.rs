//! `Cursor` reads typed positionals and keyed values; `FromArgs` consumes the rest.

// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use gob_directives::{ArgError, ArgKind, ArgList, Cursor, FromArg, FromArgs, Keyed, Token};
use gob_text::{TextRange, TextSize};

fn range() -> TextRange {
    TextRange::empty(TextSize::new(0))
}

fn token(value: &str) -> Token {
    Token {
        value: value.to_owned(),
        range: range(),
        quoted: false,
    }
}

fn args(positional: &[&str], keyed: &[(&str, &str)]) -> ArgList {
    ArgList {
        positional: positional.iter().map(|v| token(v)).collect(),
        keyed: keyed
            .iter()
            .map(|(k, v)| Keyed {
                key: (*k).to_owned(),
                key_range: range(),
                value: token(v),
            })
            .collect(),
    }
}

/// A `FromArgs` that joins every remaining token with a dash.
#[derive(Debug, PartialEq, Eq)]
struct Joined(String);

impl FromArgs for Joined {
    const KIND: ArgKind = <String as FromArg>::KIND;

    fn from_tokens(name: &str, tokens: &[Token]) -> Result<Self, ArgError> {
        if tokens.is_empty() {
            return Err(ArgError::Missing {
                name: name.to_owned(),
            });
        }
        let parts: Vec<&str> = tokens.iter().map(|t| t.value.as_str()).collect();
        Ok(Self(parts.join("-")))
    }
}

// frob:tests crates/gob-directives/src/args.rs::Cursor.positional
// frob:tests crates/gob-directives/src/args.rs::Cursor.positional_opt
#[test]
fn positionals_advance_and_report_missing_and_invalid() {
    let list = args(&["7", "x"], &[]);
    let mut c = Cursor::new(&list);
    assert_eq!(c.positional::<u32>("n"), Ok(7));
    assert!(matches!(
        c.positional::<u32>("n"),
        Err(ArgError::Invalid { .. })
    ));
    assert_eq!(c.positional_opt::<String>("s"), Ok(None));
    assert!(matches!(
        c.positional::<String>("s"),
        Err(ArgError::Missing { .. })
    ));
}

// frob:tests crates/gob-directives/src/args.rs::Cursor.keyed
// frob:tests crates/gob-directives/src/args.rs::Cursor.keyed_opt
#[test]
fn keyed_values_parse_or_report() {
    let list = args(&[], &[("n", "3"), ("flag", "maybe")]);
    let mut c = Cursor::new(&list);
    assert_eq!(c.keyed::<u32>("n"), Ok(3));
    assert_eq!(c.keyed_opt::<u32>("absent"), Ok(None));
    assert!(matches!(
        c.keyed::<u32>("absent"),
        Err(ArgError::Missing { .. })
    ));
    assert!(matches!(
        c.keyed_opt::<bool>("flag"),
        Err(ArgError::Invalid { .. })
    ));
}

// frob:tests crates/gob-directives/src/args.rs::Cursor.rest
// frob:tests crates/gob-directives/src/args.rs::FromArgs.from_tokens
#[test]
fn rest_hands_the_remaining_positionals_to_from_tokens() {
    let list = args(&["a", "b", "c"], &[]);
    let mut c = Cursor::new(&list);
    assert_eq!(c.positional::<String>("first"), Ok("a".to_owned()));
    assert_eq!(c.rest::<Joined>("tail"), Ok(Joined("b-c".to_owned())));
    assert!(matches!(
        c.rest::<Joined>("tail"),
        Err(ArgError::Missing { .. })
    ));
}

// frob:tests crates/gob-directives/src/args.rs::Cursor.list
#[test]
fn list_collects_the_remaining_positionals() {
    let ok = args(&["1", "2"], &[]);
    let mut c = Cursor::new(&ok);
    assert_eq!(Cursor::list::<u32>(&mut c, "n"), Ok(vec![1, 2]));
}

// frob:tests crates/gob-directives/src/args.rs::Cursor.list
// frob:tests crates/gob-directives/src/args.rs::ArgError.range
#[test]
fn a_list_error_points_at_a_range() {
    let list = args(&["1", "2", "x"], &[]);
    let mut c = Cursor::new(&list);
    let err = Cursor::list::<u32>(&mut c, "n").expect_err("x is not a number");
    assert_eq!(ArgError::range(&err), Some(range()));
}

// frob:tests crates/gob-directives/src/args.rs::ArgError.range
#[test]
fn a_missing_arg_has_no_range() {
    let missing = ArgError::Missing { name: "n".into() };
    assert_eq!(ArgError::range(&missing), None);
}
