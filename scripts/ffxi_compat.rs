//! Standalone differential harness. Reference modules are snapshotted outside
//! the repository by check_ffxi_compat.py after exact hash validation.

#[path = "reference/mod.rs"]
mod reference;

use banshee_bot_core::{brain, sched::control as core};
use reference::control as native;
use std::collections::BTreeMap;
use std::fmt::Debug;
use std::num::NonZeroU64;

struct Rng(u64);
impl Rng {
    fn next(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        self.0
    }
    fn pick(&mut self, count: usize) -> usize {
        (self.next() % count as u64) as usize
    }
}

fn same(left: impl Debug, right: impl Debug, context: impl Debug) {
    assert_eq!(format!("{left:?}"), format!("{right:?}"), "{context:?}");
}

fn parsers() -> usize {
    let mut corpus: Vec<Vec<u8>> = Vec::new();
    for prefix in ["", " ", "   ", "\t", "\r\n"] {
        for command in ["/fb", "/FB", "/fbar", "/fb2", "/fb/help", "say /fb", "!fb"] {
            for verb in [
                "",
                " help",
                " list",
                " summon",
                " dismiss",
                " follow",
                " stay",
                " rest",
                " attack",
                " pull",
                " assist",
                " role",
                " unknown",
                " ROLE",
                " fill",
                " rally",
                " pullback",
                " fallback",
                " formation",
                " spacing",
                " distance",
            ] {
                for args in [
                    "",
                    " all",
                    " Zoey",
                    " Zoey tank",
                    " Zoey HEALER",
                    " Zoey dps",
                    " Zoey Puller",
                    " All tank",
                    " 1040000 tank",
                    " Zoey support",
                    " Zoey tank extra",
                    " abcdefghijklmnop",
                    " abcdefghijklmnopq",
                    " Bad2",
                    " Néhà",
                    " owner=1",
                    "\tZoey",
                    "  Zoey   tank  ",
                ] {
                    corpus.push(format!("{prefix}{command}{verb}{args}").into_bytes());
                }
            }
        }
    }
    // These inputs intentionally remain in the historical profile too: a newer
    // core must not be mistaken for compatibility with the old unknown verbs.
    for verb in [
        "fill",
        "rally",
        "pullback",
        "fallback",
        "formation",
        "spacing",
        "distance",
    ] {
        for value in [
            "", "tank", "healer", "dps", "puller", "clear", "circle", "arrow", "line", "none", "0",
            "1.9", "2", "2.4", "2.5", "3.0", "03.0", "6", "6.1", "8", "8.1", "99.9", "100", "000",
            "3.", ".3", "3.00", "-3", "+3", "3e0", "NaN", "inf",
        ] {
            for tail in ["", " extra", " extra more", "\n", "\0"] {
                corpus.push(format!("/fb {verb} {value}{tail}").into_bytes());
                corpus.push(
                    format!(
                        " /FB {} {}{tail} ",
                        verb.to_uppercase(),
                        value.to_uppercase()
                    )
                    .into_bytes(),
                );
            }
        }
    }
    for verb in ["spacing", "distance"] {
        for n in 0..=1_001 {
            corpus.push(format!("/fb {verb} {}.{}", n / 10, n % 10).into_bytes());
        }
    }
    for length in [0, 1, 2, 3, 199, 200, 201, 202, 4096] {
        let mut padded = b"/fb role Zoey tank".to_vec();
        padded.resize(length, b' ');
        corpus.push(padded);
        corpus.push(vec![b'x'; length]);
    }
    for byte in 0..=u8::MAX {
        corpus.push([b"/fb".as_slice(), &[byte], b"follow"].concat());
        corpus.push([&[byte][..], b"/fb follow".as_slice()].concat());
        corpus.push([b"/fb role Zoe".as_slice(), &[byte], b" tank"].concat());
        corpus.push([b"/fb follow".as_slice(), &[byte]].concat());
    }
    let bases = corpus.clone();
    let mut rng = Rng(0x6f62_6f74_5f43_3101);
    for _ in 0..30_000 {
        let mut input = bases[rng.pick(bases.len())].clone();
        for _ in 0..=rng.pick(5) {
            match rng.pick(5) {
                0 if !input.is_empty() => {
                    let at = rng.pick(input.len());
                    input[at] = rng.next() as u8;
                }
                1 if !input.is_empty() => {
                    let at = rng.pick(input.len());
                    input.remove(at);
                }
                2 => {
                    let at = rng.pick(input.len() + 1);
                    input.insert(at, rng.next() as u8);
                }
                3 => input.resize(rng.pick(260), b' '),
                _ => input.make_ascii_uppercase(),
            }
        }
        corpus.push(input);
    }
    for input in &corpus {
        same(
            reference::command::parse(input),
            brain::command::parse(input),
            ("command", input),
        );
        same(
            reference::orders::parse(input),
            brain::orders::parse(input),
            ("orders", input),
        );
    }
    corpus.len()
}

#[cfg(native_latest)]
fn new_grammar() -> usize {
    let mut checks = 0;
    for (line, command, order) in [
        ("/fb fill", "Ok(Some(Fill(None)))", "Ok(None)"),
        ("/FB FILL TANK", "Ok(Some(Fill(Some(Tank))))", "Ok(None)"),
        (
            "/fb fill healer",
            "Ok(Some(Fill(Some(Healer))))",
            "Ok(None)",
        ),
        ("/fb fill dps", "Ok(Some(Fill(Some(Dps))))", "Ok(None)"),
        ("/fb fill puller extra", "Err(InvalidName)", "Ok(None)"),
        ("/fb fill tank extra", "Err(TooManyArguments)", "Ok(None)"),
        ("/fb rally", "Ok(Some(Rally { clear: false }))", "Ok(None)"),
        (
            "/fb rally CLEAR",
            "Ok(Some(Rally { clear: true }))",
            "Ok(None)",
        ),
        ("/fb rally invalid extra", "Err(InvalidName)", "Ok(None)"),
        ("/fb rally clear extra", "Err(TooManyArguments)", "Ok(None)"),
        ("/fb pullback", "Ok(Some(PullBack))", "Ok(None)"),
        ("/fb fallback", "Ok(Some(FallBack))", "Ok(None)"),
        ("/fb fallback all", "Err(TooManyArguments)", "Ok(None)"),
        ("/fb pullback tank", "Err(TooManyArguments)", "Ok(None)"),
        (
            "/fb formation",
            "Err(UnknownSubcommand)",
            "Err(MissingArgument)",
        ),
        (
            "/fb spacing",
            "Err(UnknownSubcommand)",
            "Err(MissingArgument)",
        ),
        (
            "/fb distance",
            "Err(UnknownSubcommand)",
            "Err(MissingArgument)",
        ),
        (
            "/fb formation triangle extra",
            "Err(UnknownSubcommand)",
            "Err(Grammar(TooManyArguments))",
        ),
        (
            "/fb spacing NaN extra",
            "Err(UnknownSubcommand)",
            "Err(Grammar(TooManyArguments))",
        ),
        (
            "/fb distance NaN",
            "Err(UnknownSubcommand)",
            "Err(InvalidGeometry)",
        ),
        (
            "/fb formation CIRCLE",
            "Err(UnknownSubcommand)",
            "Ok(Some(Geometry(Shape(Circle))))",
        ),
        (
            "/fb formation arrow",
            "Err(UnknownSubcommand)",
            "Ok(Some(Geometry(Shape(Arrow))))",
        ),
        (
            "/fb formation line",
            "Err(UnknownSubcommand)",
            "Ok(Some(Geometry(Shape(Line))))",
        ),
        (
            "/fb formation none",
            "Err(UnknownSubcommand)",
            "Ok(Some(Geometry(Shape(None))))",
        ),
        (
            "/fb spacing 2.4",
            "Err(UnknownSubcommand)",
            "Err(InvalidGeometry)",
        ),
        (
            "/fb spacing 2.5",
            "Err(UnknownSubcommand)",
            "Ok(Some(Geometry(Spacing(25))))",
        ),
        (
            "/fb spacing 6.0",
            "Err(UnknownSubcommand)",
            "Ok(Some(Geometry(Spacing(60))))",
        ),
        (
            "/fb spacing 6.1",
            "Err(UnknownSubcommand)",
            "Err(InvalidGeometry)",
        ),
        (
            "/fb distance 1.9",
            "Err(UnknownSubcommand)",
            "Err(InvalidGeometry)",
        ),
        (
            "/fb distance 2",
            "Err(UnknownSubcommand)",
            "Ok(Some(Geometry(Distance(20))))",
        ),
        (
            "/fb distance 8.0",
            "Err(UnknownSubcommand)",
            "Ok(Some(Geometry(Distance(80))))",
        ),
        (
            "/fb distance 8.1",
            "Err(UnknownSubcommand)",
            "Err(InvalidGeometry)",
        ),
        (
            "/fb spacing 03.0",
            "Err(UnknownSubcommand)",
            "Ok(Some(Geometry(Spacing(30))))",
        ),
        (
            "/fb spacing 003",
            "Err(UnknownSubcommand)",
            "Err(InvalidGeometry)",
        ),
        (
            "/fb fill\n",
            "Err(InvalidText)",
            "Err(Grammar(InvalidText))",
        ),
    ] {
        let old_command = reference::command::parse(line.as_bytes());
        let old_order = reference::orders::parse(line.as_bytes());
        assert_eq!(
            format!("{old_command:?}"),
            command,
            "directed command: {line}"
        );
        assert_eq!(format!("{old_order:?}"), order, "directed order: {line}");
        same(old_command, brain::command::parse(line.as_bytes()), line);
        same(old_order, brain::orders::parse(line.as_bytes()), line);
        checks += 2;
    }
    checks
}

#[derive(Clone, Copy, Debug)]
enum TokenPick {
    Current,
    Previous,
    Zero,
    WrongBinding,
    WrongEpoch,
}

#[derive(Clone, Copy, Debug)]
enum Step {
    Begin(u8, u64),
    Order(u64),
    CanOrder(u64),
    Binding(Option<u64>),
    Invite,
    Arrival(TokenPick),
    Reconciled(TokenPick),
    Abandoned(TokenPick),
    GearFinished(TokenPick),
    Dismissed(TokenPick),
    InviteFinished(TokenPick, Option<u64>),
    Admit(Option<TokenPick>, bool),
}

struct Pair {
    old: native::Clock,
    new: core::Clock,
    previous: Option<native::Token>,
    steps: usize,
    methods: BTreeMap<&'static str, usize>,
    phases: BTreeMap<String, usize>,
}

impl Pair {
    fn new(detached: bool) -> Self {
        let old = if detached {
            native::Clock::initially_detached()
        } else {
            native::Clock::default()
        };
        let new = if detached {
            core::Clock::initially_detached()
        } else {
            core::Clock::default()
        };
        same(old.snapshot(), new.snapshot(), ("initial state", detached));
        Self {
            old,
            new,
            previous: None,
            steps: 0,
            methods: BTreeMap::new(),
            phases: BTreeMap::new(),
        }
    }
    fn token(&self, pick: TokenPick) -> native::Token {
        let current = self.old.snapshot().token.unwrap_or(native::Token {
            binding_revision: 0,
            epoch: 0,
        });
        match pick {
            TokenPick::Current => current,
            TokenPick::Previous => self.previous.unwrap_or(native::Token {
                binding_revision: 0,
                epoch: 0,
            }),
            TokenPick::Zero => native::Token {
                binding_revision: 0,
                epoch: 0,
            },
            TokenPick::WrongBinding => native::Token {
                binding_revision: current.binding_revision.wrapping_add(1),
                ..current
            },
            TokenPick::WrongEpoch => native::Token {
                epoch: current.epoch.wrapping_add(1),
                ..current
            },
        }
    }
    fn step(&mut self, step: Step) {
        fn new_token(t: native::Token) -> core::Token {
            core::Token {
                binding_revision: t.binding_revision,
                epoch: t.epoch,
            }
        }
        fn binding(n: u64) -> NonZeroU64 {
            NonZeroU64::new(n).expect("trace bindings are positive")
        }
        let before = self.old.snapshot();
        let context = (self.steps, step, before);
        let method = match step {
            Step::Begin(op, rev) => {
                let old_op = [
                    native::Operation::Gear,
                    native::Operation::Summon,
                    native::Operation::Dismiss,
                    #[cfg(native_latest)]
                    native::Operation::Fallback,
                ][op as usize];
                let new_op = [
                    core::Operation::Gear,
                    core::Operation::Summon,
                    core::Operation::Dismiss,
                    #[cfg(native_latest)]
                    core::Operation::Fallback,
                ][op as usize];
                same(
                    self.old.begin(old_op, binding(rev)),
                    self.new.begin(new_op, binding(rev)),
                    context,
                );
                "begin"
            }
            Step::Order(rev) => {
                same(
                    self.old.order(binding(rev)),
                    self.new.order(binding(rev)),
                    context,
                );
                "order"
            }
            Step::CanOrder(rev) => {
                same(
                    self.old.can_order(binding(rev)),
                    self.new.can_order(binding(rev)),
                    context,
                );
                "can_order"
            }
            Step::Binding(rev) => {
                same(
                    self.old.binding_changed(rev.map(binding)),
                    self.new.binding_changed(rev.map(binding)),
                    context,
                );
                "binding_changed"
            }
            Step::Invite => {
                same(
                    self.old.human_invitation(),
                    self.new.human_invitation(),
                    context,
                );
                "human_invitation"
            }
            Step::Arrival(pick) => {
                let t = self.token(pick);
                same(
                    self.old.summon_arrived(t),
                    self.new.summon_arrived(new_token(t)),
                    context,
                );
                "summon_arrived"
            }
            Step::Reconciled(pick) => {
                let t = self.token(pick);
                same(
                    self.old.summon_reconciled(t),
                    self.new.summon_reconciled(new_token(t)),
                    context,
                );
                "summon_reconciled"
            }
            Step::Abandoned(pick) => {
                let t = self.token(pick);
                same(
                    self.old.summon_abandoned(t),
                    self.new.summon_abandoned(new_token(t)),
                    context,
                );
                "summon_abandoned"
            }
            Step::GearFinished(pick) => {
                let t = self.token(pick);
                same(
                    self.old.gear_finished(t),
                    self.new.gear_finished(new_token(t)),
                    context,
                );
                "gear_finished"
            }
            Step::Dismissed(pick) => {
                let t = self.token(pick);
                same(
                    self.old.dismiss_completed(t),
                    self.new.dismiss_completed(new_token(t)),
                    context,
                );
                "dismiss_completed"
            }
            Step::InviteFinished(pick, rev) => {
                let t = self.token(pick);
                same(
                    self.old.invitation_finished(t, rev.map(binding)),
                    self.new.invitation_finished(new_token(t), rev.map(binding)),
                    context,
                );
                "invitation_finished"
            }
            Step::Admit(pick, accept) => {
                let t = pick.map(|p| self.token(p));
                same(
                    self.old.admit(t, accept),
                    self.new.admit(t.map(new_token), accept),
                    context,
                );
                "admit"
            }
        };
        same(self.old.snapshot(), self.new.snapshot(), context);
        if self.old.snapshot() != before {
            self.previous = before.token;
        }
        *self.methods.entry(method).or_default() += 1;
        *self
            .phases
            .entry(format!("{:?}", self.old.snapshot().phase))
            .or_default() += 1;
        self.steps += 1;
    }
}

fn clocks() -> (
    usize,
    BTreeMap<&'static str, usize>,
    BTreeMap<String, usize>,
) {
    use Step::*;
    use TokenPick::*;
    let directed = [
        Admit(None, false),
        Admit(Some(Zero), true),
        Binding(Some(7)),
        CanOrder(7),
        Order(7),
        Admit(Some(Current), false),
        CanOrder(8),
        Order(8),
        Begin(1, 7),
        Admit(Some(Current), false),
        Dismissed(Current),
        Order(7),
        Binding(None),
        Arrival(Current),
        Abandoned(Previous),
        Abandoned(Current),
        Invite,
        Admit(Some(Current), false),
        Admit(Some(Current), true),
        InviteFinished(Current, None),
        InviteFinished(Previous, Some(7)),
        Invite,
        InviteFinished(Current, Some(7)),
        Begin(0, 7),
        GearFinished(Previous),
        GearFinished(Current),
        Begin(1, 7),
        Binding(Some(8)),
        Reconciled(Previous),
        Reconciled(Current),
        Begin(1, 8),
        Arrival(Current),
        Begin(2, 8),
        Dismissed(Current),
        Invite,
        InviteFinished(Current, Some(u64::MAX)),
        Order(u64::MAX),
        Binding(Some(u64::MAX)),
        Begin(1, u64::MAX),
        Binding(Some(7)),
        Abandoned(Current),
        Begin(1, 7),
        Reconciled(Current),
        Binding(None),
    ];
    let mut total = 0;
    let mut methods = BTreeMap::new();
    let mut phases = BTreeMap::new();
    let mut rng = Rng(0x636f_6e74_726f_6c31);
    for trace in 0..128 {
        let mut pair = Pair::new(trace % 2 == 1);
        for step in directed {
            pair.step(step);
        }
        #[cfg(native_latest)]
        for step in [
            Invite,
            InviteFinished(Current, Some(7)),
            Begin(3, 7),
            Admit(Some(Current), false),
            Admit(Some(Current), true),
            Admit(Some(Previous), false),
            CanOrder(7),
            CanOrder(8),
            Begin(3, 8),
            Begin(0, 7),
            Begin(1, 7),
            Begin(2, 7),
            Arrival(Current),
            GearFinished(Current),
            Dismissed(Current),
            Abandoned(Current),
            Begin(3, 7),
            Binding(Some(7)),
            Admit(Some(Previous), false),
            Order(8),
            Order(7),
            Admit(Some(Previous), false),
            Admit(Some(Current), false),
            Begin(3, 7),
            Binding(Some(8)),
            Admit(Some(Previous), false),
            Admit(Some(Current), false),
            Begin(3, 8),
            Binding(None),
            Admit(Some(Previous), false),
            Invite,
            InviteFinished(Current, Some(7)),
            Begin(3, 7),
            Order(7),
            Begin(1, 7),
            Begin(3, 7),
            Binding(Some(8)),
            Reconciled(Current),
            Begin(3, 8),
            Binding(None),
        ] {
            pair.step(step);
        }
        for _ in 0..256 {
            let pick = [Current, Current, Previous, Zero, WrongBinding, WrongEpoch][rng.pick(6)];
            let rev = [1, 7, 8, u64::MAX][rng.pick(4)];
            let optional_rev = (rng.pick(3) != 0).then_some(rev);
            let step = match rng.pick(14) {
                0 => Begin(rng.pick(if cfg!(native_latest) { 4 } else { 3 }) as u8, rev),
                1 => Order(rev),
                2 => CanOrder(rev),
                3 => Binding(optional_rev),
                4 => Invite,
                5 => Arrival(pick),
                6 => Reconciled(pick),
                7 => Abandoned(pick),
                8 => GearFinished(pick),
                9 => Dismissed(pick),
                10 => InviteFinished(pick, optional_rev),
                11 => Admit(None, rng.pick(2) != 0),
                _ => Admit(Some(pick), rng.pick(2) != 0),
            };
            pair.step(step);
        }
        total += pair.steps;
        for (name, count) in pair.methods {
            *methods.entry(name).or_default() += count;
        }
        for (name, count) in pair.phases {
            *phases.entry(name).or_default() += count;
        }
    }
    for required in [
        "Legacy",
        "Active",
        "Detached",
        "Invited",
        "Fenced(Gear)",
        "Fenced(Summon)",
        "Fenced(Dismiss)",
    ] {
        assert!(
            phases.get(required).copied().unwrap_or(0) > 0,
            "phase not covered: {required}"
        );
    }
    assert_eq!(
        methods.len(),
        12,
        "every public operation must be exercised"
    );
    #[cfg(native_latest)]
    assert!(
        phases.get("Fenced(Fallback)").copied().unwrap_or(0) > 0,
        "fallback phase not exercised"
    );
    (total, methods, phases)
}

fn main() {
    let command_cases = parsers();
    let (clock_steps, methods, phases) = clocks();
    #[cfg(native_latest)]
    let new_grammar_checks = new_grammar();
    #[cfg(not(native_latest))]
    let new_grammar_checks = 0;
    println!("{{\"status\":\"PASS\",\"command_cases\":{command_cases},\"parser_comparisons\":{},\"new_grammar_precedence_comparisons\":{new_grammar_checks},\"clock_traces\":128,\"clock_steps\":{clock_steps},\"clock_result_and_snapshot_comparisons\":{},\"clock_methods\":{methods:?},\"clock_phases\":{phases:?}}}", command_cases * 2, clock_steps * 2);
}
