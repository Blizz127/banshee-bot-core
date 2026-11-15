//! Original differential cases for pure decimal and formation settings only.
//! The reference snapshot is external and pinned by check_ffxi_compat.py.
//! Native desired positions, rotation and movement are deliberately not called.

#[path = "reference/mod.rs"]
mod reference;

use banshee_bot_core::brain::formation as current;
use reference::formation as native;
use std::collections::BTreeMap;
use std::fmt::Debug;

#[derive(Default)]
struct Counts {
    comparisons: usize,
    decimal_cases: usize,
    configuration_cases: usize,
    coverage: BTreeMap<&'static str, usize>,
}

impl Counts {
    fn compare(&mut self, old: impl Debug, new: impl Debug, context: impl Debug) {
        assert_eq!(format!("{old:?}"), format!("{new:?}"), "{context:?}");
        self.comparisons += 1;
    }

    fn hit(&mut self, key: &'static str) {
        *self.coverage.entry(key).or_default() += 1;
    }

    fn decimal(&mut self, word: &[u8]) {
        let old = native::decimal(word);
        let new = current::decimal(word);
        self.compare(old, new, ("decimal", word));
        self.decimal_cases += 1;
        self.hit(if old.is_some() {
            "decimal.Some"
        } else {
            "decimal.None"
        });
    }

    fn setting(&mut self, config: native::Config, setting: native::Setting) {
        let old = config.with(setting);
        let new = current_config(config).with(current_setting(setting));
        self.compare(old, new, ("with", config, setting));
        self.configuration_cases += 1;
        self.hit(match (setting, old.is_some()) {
            (native::Setting::Shape(_), true) => "shape.Some",
            (native::Setting::Shape(_), false) => "shape.None",
            (native::Setting::Spacing(_), true) => "spacing.Some",
            (native::Setting::Spacing(_), false) => "spacing.None",
            (native::Setting::Distance(_), true) => "distance.Some",
            (native::Setting::Distance(_), false) => "distance.None",
        });
        if let Some(next) = old {
            // Only the supplied setting is validated. An unrelated invalid
            // field already in the config must survive an accepted update.
            if !(25..=60).contains(&next.spacing) || !(20..=80).contains(&next.distance) {
                self.hit("with.Some.preserves-unrelated-invalid-field");
            }
        }
    }
}

fn current_shape(shape: native::Shape) -> current::Shape {
    match shape {
        native::Shape::Circle => current::Shape::Circle,
        native::Shape::Arrow => current::Shape::Arrow,
        native::Shape::Line => current::Shape::Line,
        native::Shape::None => current::Shape::None,
    }
}

fn current_config(config: native::Config) -> current::Config {
    current::Config {
        shape: current_shape(config.shape),
        spacing: config.spacing,
        distance: config.distance,
    }
}

fn current_setting(setting: native::Setting) -> current::Setting {
    match setting {
        native::Setting::Shape(shape) => current::Setting::Shape(current_shape(shape)),
        native::Setting::Spacing(value) => current::Setting::Spacing(value),
        native::Setting::Distance(value) => current::Setting::Distance(value),
    }
}

struct Rng(u64);

impl Rng {
    fn next(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        self.0
    }

    fn pick(&mut self, length: usize) -> usize {
        (self.next() % length as u64) as usize
    }
}

fn decimals(counts: &mut Counts) {
    let directed = [
        "", "0", "00", "000", "1", "01", "09", "10", "99", "100", "0.0", "00.0", "00.9", "01.0",
        "09.9", "99.9", "100.0", "0.", ".0", ".", "..", "1..0", "1.00", "1.01", "1.0.0", "1.0.",
        " 2.5", "2.5 ", "+2.5", "-2.5", "2,5", "2_5", "0x25", "2e0", "2E+0", "NaN", "inf",
        "Infinity", "２.５", "2.５", "2.5y", "2.5\0", "\t2.5", "2.5\n", "1.9", "2.0", "2.1", "2.4",
        "2.5", "2.6", "5.9", "6.0", "6.1", "7.9", "8.0", "8.1", "20", "25", "60", "80", "65535",
    ];
    for word in directed {
        counts.decimal(word.as_bytes());
    }

    // Enumerate all one- and two-byte strings, including invalid UTF-8 and
    // controls, instead of restricting malformed input to text literals.
    for a in u8::MIN..=u8::MAX {
        counts.decimal(&[a]);
        for b in u8::MIN..=u8::MAX {
            counts.decimal(&[a, b]);
        }
    }

    // Exercise every accepted whole/fraction pair, with and without the
    // permitted two-digit leading-zero spelling.
    for whole in 0..=99 {
        for spelling in [whole.to_string(), format!("{whole:02}")] {
            counts.decimal(spelling.as_bytes());
            for fractional in 0..=9 {
                counts.decimal(format!("{spelling}.{fractional}").as_bytes());
            }
        }
    }
    for length in [3, 4, 5, 16, 200, 201, 4096] {
        counts.decimal(&vec![b'0'; length]);
        counts.decimal(&vec![b'.'; length]);
    }

    let mut rng = Rng(0x464f_524d_4154_494f);
    for _ in 0..20_000 {
        let mut word = directed[rng.pick(directed.len())].as_bytes().to_vec();
        for _ in 0..=rng.pick(4) {
            match rng.pick(5) {
                0 if !word.is_empty() => {
                    let index = rng.pick(word.len());
                    word[index] = rng.next() as u8;
                }
                1 if !word.is_empty() => {
                    let index = rng.pick(word.len());
                    word.remove(index);
                }
                2 => {
                    let index = rng.pick(word.len() + 1);
                    word.insert(index, rng.next() as u8);
                }
                3 => word.resize(rng.pick(32), b'0'),
                _ => word.push(b'.'),
            }
        }
        counts.decimal(&word);
    }
}

fn configurations(counts: &mut Counts) {
    use native::{Config, Setting, Shape};

    counts.compare(
        Config::default(),
        current::Config::default(),
        "default config",
    );
    counts.hit("default");
    let configs = [
        Config::default(),
        Config {
            shape: Shape::Arrow,
            spacing: 25,
            distance: 80,
        },
        Config {
            shape: Shape::Line,
            spacing: 60,
            distance: 20,
        },
        Config {
            shape: Shape::None,
            spacing: 40,
            distance: 50,
        },
        Config {
            shape: Shape::Circle,
            spacing: 0,
            distance: 30,
        },
        Config {
            shape: Shape::Arrow,
            spacing: 30,
            distance: 0,
        },
        Config {
            shape: Shape::Line,
            spacing: u16::MAX,
            distance: u16::MAX,
        },
        Config {
            shape: Shape::None,
            spacing: 24,
            distance: 81,
        },
    ];
    let shapes = [Shape::Circle, Shape::Arrow, Shape::Line, Shape::None];
    for config in configs {
        for shape in shapes {
            counts.setting(config, Setting::Shape(shape));
        }
        for value in u16::MIN..=u16::MAX {
            counts.setting(config, Setting::Spacing(value));
            counts.setting(config, Setting::Distance(value));
        }
    }
    assert_eq!(counts.coverage["shape.Some"], 32);
    assert_eq!(counts.coverage["spacing.Some"], 8 * 36);
    assert_eq!(counts.coverage["distance.Some"], 8 * 61);
    assert_eq!(counts.coverage.get("shape.None"), None);

    // Carry both accepted configurations through a sequence, retaining the
    // previous one when an update is refused. This also checks that updates
    // preserve earlier accepted shape, spacing and distance settings.
    for start in configs {
        let mut old = start;
        let mut new = current_config(start);
        for setting in [
            Setting::Shape(Shape::None),
            Setting::Spacing(25),
            Setting::Distance(80),
            Setting::Spacing(24),
            Setting::Distance(81),
            Setting::Shape(Shape::Arrow),
            Setting::Spacing(60),
            Setting::Distance(20),
            Setting::Spacing(61),
            Setting::Distance(19),
            Setting::Shape(Shape::Line),
            Setting::Spacing(30),
            Setting::Distance(30),
            Setting::Shape(Shape::Circle),
        ] {
            let old_result = old.with(setting);
            let new_result = new.with(current_setting(setting));
            counts.compare(old_result, new_result, ("sequence result", old, setting));
            old = old_result.unwrap_or(old);
            new = new_result.unwrap_or(new);
            counts.compare(old, new, ("sequence retained state", setting));
            counts.hit(if old_result.is_some() {
                "sequence.Some"
            } else {
                "sequence.None"
            });
        }
    }
}

fn main() {
    let mut counts = Counts::default();
    decimals(&mut counts);
    configurations(&mut counts);
    for key in [
        "default",
        "decimal.Some",
        "decimal.None",
        "shape.Some",
        "spacing.Some",
        "spacing.None",
        "distance.Some",
        "distance.None",
        "with.Some.preserves-unrelated-invalid-field",
        "sequence.Some",
        "sequence.None",
    ] {
        assert!(
            counts.coverage.get(key).copied().unwrap_or(0) > 0,
            "missing {key}"
        );
    }
    println!(
        "{{\"status\":\"PASS\",\"scope\":\"decimal and config only; native desired positions excluded\",\"comparisons\":{},\"decimal_cases\":{},\"configuration_cases\":{},\"coverage\":{:?}}}",
        counts.comparisons, counts.decimal_cases, counts.configuration_cases, counts.coverage
    );
}
