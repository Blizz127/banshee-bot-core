//! Optional measurement of a supplied complete path, with no native calls or
//! execution authority. Distances use the supplied `f32` coordinates promoted
//! to `f64`; their basis differs from a serialized native polyline and its
//! rounding. Units and calibration remain the adapter's responsibility.
//!
//! Completeness here is the supplied `Path::Complete` classification, not proof
//! of connectivity, topology, collision clearance or walkability. The point
//! limit bounds only this measurement: native query buffer capacities remain
//! adapter-owned. It neither allocates native entries nor truncates native output.

use super::{Path, Point3};

/// Maximum supplied points accepted by this pure measurement, not a native
/// query buffer capacity.
pub const MAX_ROUTE_POINTS: usize = 256;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ProjectionOutcome {
    Unassessed,
    WithinLimit,
    LimitExceeded,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RouteError {
    InvalidProjectionLimit,
    NonFiniteRequestedPoint,
    NotComplete,
    TooFewPoints,
    TooManyPoints,
    NonFiniteRoutePoint,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct RouteMetrics {
    pub requested_start: Point3,
    pub requested_end: Point3,
    pub reported_start: Point3,
    pub reported_end: Point3,
    pub start_projection_distance: f64,
    pub end_projection_distance: f64,
    pub max_projection_distance: f64,
    pub requested_separation: f64,
    pub reported_endpoint_separation: f64,
    pub path_length: f64,
    pub point_count: usize,
    pub reported_endpoints_equal_requested: bool,
    pub projection_limit: Option<f64>,
    pub projection: ProjectionOutcome,
}

fn finite(point: Point3) -> bool {
    point.x.is_finite() && point.y.is_finite() && point.z.is_finite()
}

fn distance(a: Point3, b: Point3) -> f64 {
    // Promote each operand before subtracting: opposite finite f32 extremes
    // overflow f32 subtraction, while all such 3D distances fit in f64.
    let dx = f64::from(a.x) - f64::from(b.x);
    let dy = f64::from(a.y) - f64::from(b.y);
    let dz = f64::from(a.z) - f64::from(b.z);
    dx.hypot(dy).hypot(dz)
}

/// Measure a supplied complete polyline in the coordinates' original units.
///
/// Validation order is projection limit, requested endpoints, path variant,
/// point count, then every route point. No distance is computed before all
/// route points pass validation. Two identical finite points are accepted.
///
/// An omitted limit is unassessed. A measured displacement equal to the limit
/// is within it; no epsilon is applied. Exceeding a valid limit returns metrics
/// with `LimitExceeded`, not an error or an authorization to move.
pub fn measure_complete_path(
    start: Point3,
    end: Point3,
    path: &Path,
    max_projection_distance: Option<f64>,
) -> Result<RouteMetrics, RouteError> {
    if let Some(limit) = max_projection_distance {
        if !limit.is_finite() || limit < 0.0 {
            return Err(RouteError::InvalidProjectionLimit);
        }
    }
    if !finite(start) || !finite(end) {
        return Err(RouteError::NonFiniteRequestedPoint);
    }
    let Path::Complete(points) = path else {
        return Err(RouteError::NotComplete);
    };
    if points.len() < 2 {
        return Err(RouteError::TooFewPoints);
    }
    if points.len() > MAX_ROUTE_POINTS {
        return Err(RouteError::TooManyPoints);
    }
    if points.iter().any(|point| !finite(*point)) {
        return Err(RouteError::NonFiniteRoutePoint);
    }

    let reported_start = points[0];
    let reported_end = points[points.len() - 1];
    let start_projection_distance = distance(start, reported_start);
    let end_projection_distance = distance(end, reported_end);
    let maximum = start_projection_distance.max(end_projection_distance);
    let projection = match max_projection_distance {
        None => ProjectionOutcome::Unassessed,
        Some(limit) if maximum <= limit => ProjectionOutcome::WithinLimit,
        Some(_) => ProjectionOutcome::LimitExceeded,
    };
    // At most 255 finite-f32 segments cannot overflow an f64 sum.
    let path_length = points
        .windows(2)
        .map(|pair| distance(pair[0], pair[1]))
        .sum();

    Ok(RouteMetrics {
        requested_start: start,
        requested_end: end,
        reported_start,
        reported_end,
        start_projection_distance,
        end_projection_distance,
        max_projection_distance: maximum,
        requested_separation: distance(start, end),
        reported_endpoint_separation: distance(reported_start, reported_end),
        path_length,
        point_count: points.len(),
        reported_endpoints_equal_requested: reported_start == start && reported_end == end,
        projection_limit: max_projection_distance,
        projection,
    })
}
