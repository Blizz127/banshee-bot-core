//! Existing FFXI order vocabulary only. Parsing does not select or authorize a
//! bot. The native order planner still handles owner/party/session/claim checks.

use super::command;
pub use crate::roles::Role;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Order {
    Follow,
    Stay,
    Rest,
    Attack,
    Pull,
    Assist,
    Role { name: String, role: Role },
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ParseError {
    Grammar(command::ParseError),
    MissingArgument,
    InvalidRole,
}

/// Preserve first-slice ownership of its successes AND argument errors.
/// No chat, model output or parsed name is evidence of authority.
pub fn parse(input: &[u8]) -> Result<Option<Order>, ParseError> {
    use command::ParseError as Grammar;
    match command::parse(input) {
        Err(Grammar::UnknownSubcommand) => {}
        Err(error @ (Grammar::TooLong | Grammar::InvalidText)) => {
            return Err(ParseError::Grammar(error))
        }
        _ => return Ok(None),
    }
    let words: Vec<_> = input
        .split(|b| *b == b' ')
        .filter(|s| !s.is_empty())
        .collect();
    let verb = words[1].to_ascii_lowercase();
    let simple = match verb.as_slice() {
        b"follow" => Some(Order::Follow),
        b"stay" => Some(Order::Stay),
        b"rest" => Some(Order::Rest),
        b"attack" => Some(Order::Attack),
        b"pull" => Some(Order::Pull),
        b"assist" => Some(Order::Assist),
        _ => None,
    };
    if let Some(order) = simple {
        return if words.len() == 2 {
            Ok(Some(order))
        } else {
            Err(ParseError::Grammar(Grammar::TooManyArguments))
        };
    }
    if verb != b"role" {
        return Err(ParseError::Grammar(Grammar::UnknownSubcommand));
    }
    if words.len() < 4 {
        return Err(ParseError::MissingArgument);
    }
    if words.len() > 4 {
        return Err(ParseError::Grammar(Grammar::TooManyArguments));
    }
    let name = words[2];
    if !command::valid_name(name) || name.eq_ignore_ascii_case(b"all") {
        return Err(ParseError::Grammar(Grammar::InvalidName));
    }
    let role = match words[3].to_ascii_lowercase().as_slice() {
        b"tank" => Role::Tank,
        b"healer" => Role::Healer,
        b"dps" => Role::Dps,
        b"puller" => Role::Puller,
        _ => return Err(ParseError::InvalidRole),
    };
    Ok(Some(Order::Role {
        name: String::from_utf8_lossy(name).into_owned(),
        role,
    }))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn compatibility_precedence_and_scope() {
        for unrelated in [
            b"/fbar".as_slice(),
            b"/fb summon Bad2",
            b"/fb list all",
            b"/fb help",
        ] {
            assert_eq!(parse(unrelated), Ok(None));
        }
        assert_eq!(
            parse(b"\t/fb follow"),
            Err(ParseError::Grammar(command::ParseError::InvalidText))
        );
        assert_eq!(
            parse(b"/fb follow all"),
            Err(ParseError::Grammar(command::ParseError::TooManyArguments))
        );
        assert_eq!(
            parse(b"/fb role All tank"),
            Err(ParseError::Grammar(command::ParseError::InvalidName))
        );
        assert_eq!(
            parse(b"/fb role Zoey support"),
            Err(ParseError::InvalidRole)
        );
        assert_eq!(
            parse(b" /FB  ROLE Zoey Healer "),
            Ok(Some(Order::Role {
                name: "Zoey".into(),
                role: Role::Healer
            }))
        );
        let mut padded = b"/fb pull".to_vec();
        padded.resize(200, b' ');
        assert_eq!(parse(&padded), Ok(Some(Order::Pull)));
        padded.push(0);
        assert_eq!(
            parse(&padded),
            Err(ParseError::Grammar(command::ParseError::TooLong))
        );
    }
}
