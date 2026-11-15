//! Native navigation boundary. Coordinates and zones must be mapped explicitly
//! by each adapter; absence of a path never authorizes straight-line movement.

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Point3 {
    pub x: f32,
    pub y: f32,
    pub z: f32,
}

#[derive(Clone, Debug, PartialEq)]
pub enum Path {
    Complete(Vec<Point3>),
    Partial(Vec<Point3>),
    Unreachable,
    Unavailable,
}

/// Game adapter supplies collision/mesh queries, never client packet fields.
pub trait Navigation {
    type Zone;
    fn path(&self, zone: &Self::Zone, start: Point3, end: Point3) -> Path;
    fn grounded(&self, zone: &Self::Zone, point: Point3) -> Option<Point3>;
}
