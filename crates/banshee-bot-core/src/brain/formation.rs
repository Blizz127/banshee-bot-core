//! Formation settings in integer tenths, preserving the FFXI command contract.
//! Coordinates, orientation, placement and movement belong to the native adapter.

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Shape {
    Circle,
    Arrow,
    Line,
    None,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Setting {
    Shape(Shape),
    Spacing(u16),
    Distance(u16),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Config {
    pub shape: Shape,
    pub spacing: u16,
    pub distance: u16,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            shape: Shape::Circle,
            spacing: 30,
            distance: 30,
        }
    }
}

impl Config {
    /// Check the requested value without revalidating unrelated retained fields.
    pub fn with(self, setting: Setting) -> Option<Self> {
        match setting {
            Setting::Shape(shape) => Some(Self { shape, ..self }),
            Setting::Spacing(spacing) => (25..=60)
                .contains(&spacing)
                .then_some(Self { spacing, ..self }),
            Setting::Distance(distance) => (20..=80)
                .contains(&distance)
                .then_some(Self { distance, ..self }),
        }
    }
}

/// Accept one or two whole digits, optionally followed by a single tenth.
/// Range checks for spacing and distance happen when applying the setting.
pub fn decimal(word: &[u8]) -> Option<u16> {
    fn digit(byte: u8) -> Option<u16> {
        byte.is_ascii_digit().then(|| u16::from(byte - b'0'))
    }

    match word {
        [ones] => Some(digit(*ones)? * 10),
        [tens, ones] => Some(digit(*tens)? * 100 + digit(*ones)? * 10),
        [ones, b'.', tenth] => Some(digit(*ones)? * 10 + digit(*tenth)?),
        [tens, ones, b'.', tenth] => {
            Some(digit(*tens)? * 100 + digit(*ones)? * 10 + digit(*tenth)?)
        }
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn decimal_is_exact_and_keeps_the_native_leading_zero_grammar() {
        for whole in 0..100 {
            for text in [whole.to_string(), format!("{whole:02}")] {
                assert_eq!(decimal(text.as_bytes()), Some(whole * 10));
                for tenth in 0..10 {
                    let text = format!("{text}.{tenth}");
                    assert_eq!(decimal(text.as_bytes()), Some(whole * 10 + tenth));
                }
            }
        }
        for text in [
            "", ".5", "2.", "2.50", "002", "002.5", "100", "-3", "+3", " 3", "3 ", "3e0", "3y",
            "3..0", "NaN", "inf", "2/5", "٣", "3\0", "\t3",
        ] {
            assert_eq!(decimal(text.as_bytes()), None, "{text:?}");
        }
        assert_eq!(decimal(&[0xff]), None);
    }

    #[test]
    fn settings_preserve_defaults_and_apply_only_the_selected_field() {
        let base = Config::default();
        assert_eq!(base.shape, Shape::Circle);
        assert_eq!((base.spacing, base.distance), (30, 30));
        for (setting, expected) in [
            (Setting::Spacing(24), None),
            (
                Setting::Spacing(25),
                Some(Config {
                    spacing: 25,
                    ..base
                }),
            ),
            (
                Setting::Spacing(60),
                Some(Config {
                    spacing: 60,
                    ..base
                }),
            ),
            (Setting::Spacing(61), None),
            (Setting::Distance(19), None),
            (
                Setting::Distance(20),
                Some(Config {
                    distance: 20,
                    ..base
                }),
            ),
            (
                Setting::Distance(80),
                Some(Config {
                    distance: 80,
                    ..base
                }),
            ),
            (Setting::Distance(81), None),
            (Setting::Spacing(u16::MAX), None),
            (Setting::Distance(0), None),
        ] {
            assert_eq!(base.with(setting), expected);
        }
        // Native callers can construct Config directly; only the new setting
        // is validated by this compatibility API.
        let retained = Config {
            spacing: 0,
            distance: u16::MAX,
            ..base
        };
        for shape in [Shape::Circle, Shape::Arrow, Shape::Line, Shape::None] {
            assert_eq!(
                retained.with(Setting::Shape(shape)),
                Some(Config { shape, ..retained })
            );
        }
        assert_eq!(
            retained.with(Setting::Spacing(25)),
            Some(Config {
                spacing: 25,
                ..retained
            })
        );
    }
}
