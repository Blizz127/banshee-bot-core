//! FFXI compatibility grammar; no game action or permission is produced here.

pub const MAX_COMMAND_BYTES: usize = 200;
pub const MAX_NAME_BYTES: usize = 16;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Target {
    All,
    Name(String),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Command {
    Help,
    List,
    Summon(Target),
    Dismiss(Target),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ParseError {
    TooLong,
    InvalidText,
    UnknownSubcommand,
    TooManyArguments,
    InvalidName,
}

pub(crate) fn valid_name(name: &[u8]) -> bool {
    !name.is_empty() && name.len() <= MAX_NAME_BYTES && name.iter().all(u8::is_ascii_alphabetic)
}

/// Identify unrelated chat before enforcing command limits. Recognized malformed
/// commands are errors for private native feedback, never public bot dialogue.
pub fn parse(input: &[u8]) -> Result<Option<Command>, ParseError> {
    let line = input.trim_ascii_start();
    let recognized = line
        .get(..3)
        .is_some_and(|prefix| prefix.eq_ignore_ascii_case(b"/fb"))
        && line
            .get(3)
            .is_none_or(|b| b.is_ascii_whitespace() || b.is_ascii_control());
    if !recognized {
        return Ok(None);
    }
    if input.len() > MAX_COMMAND_BYTES {
        return Err(ParseError::TooLong);
    }
    if !input.iter().all(|b| matches!(b, 0x20..=0x7e)) {
        return Err(ParseError::InvalidText);
    }

    let tokens: Vec<_> = line
        .split(|b| *b == b' ')
        .filter(|s| !s.is_empty())
        .collect();
    let Some(verb) = tokens.get(1) else {
        return Ok(Some(Command::Help));
    };
    let verb = verb.to_ascii_lowercase();
    let command = match verb.as_slice() {
        b"help" | b"list" => {
            if tokens.len() != 2 {
                return Err(ParseError::TooManyArguments);
            }
            if verb == b"help" {
                Command::Help
            } else {
                Command::List
            }
        }
        b"summon" | b"dismiss" => {
            if tokens.len() > 3 {
                return Err(ParseError::TooManyArguments);
            }
            let target = match tokens.get(2) {
                None => Target::All,
                Some(name) if name.eq_ignore_ascii_case(b"all") => Target::All,
                Some(name) if valid_name(name) => {
                    Target::Name(String::from_utf8_lossy(name).into_owned())
                }
                Some(_) => return Err(ParseError::InvalidName),
            };
            if verb == b"summon" {
                Command::Summon(target)
            } else {
                Command::Dismiss(target)
            }
        }
        _ => return Err(ParseError::UnknownSubcommand),
    };
    Ok(Some(command))
}
