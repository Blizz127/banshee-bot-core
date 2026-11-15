use banshee_bot_core::nav::metrics::{
    measure_complete_path, ProjectionOutcome, RouteError, MAX_ROUTE_POINTS,
};
use banshee_bot_core::nav::{Path, Point3};

fn point(x: f32, y: f32, z: f32) -> Point3 {
    Point3 { x, y, z }
}

#[test]
fn three_dimensional_projections_and_bent_polyline_are_distinct_metrics() {
    let start = point(-3.0, 0.0, -4.0);
    let end = point(0.0, 15.0, 4.0);
    let points = vec![
        point(0.0, 0.0, 0.0),
        point(0.0, 3.0, 0.0),
        point(0.0, 3.0, 4.0),
    ];
    let result = measure_complete_path(start, end, &Path::Complete(points.clone()), None).unwrap();

    assert_eq!(result.requested_start, start);
    assert_eq!(result.requested_end, end);
    assert_eq!(result.reported_start, points[0]);
    assert_eq!(result.reported_end, points[2]);
    assert_eq!(result.start_projection_distance, 5.0);
    assert_eq!(result.end_projection_distance, 12.0);
    assert_eq!(result.max_projection_distance, 12.0);
    assert!((result.requested_separation - 298.0_f64.sqrt()).abs() < 1e-12);
    assert_eq!(result.reported_endpoint_separation, 5.0);
    assert_eq!(result.path_length, 7.0);
    assert_eq!(result.point_count, 3);
    assert!(!result.reported_endpoints_equal_requested);
    assert_eq!(result.projection_limit, None);
    assert_eq!(result.projection, ProjectionOutcome::Unassessed);
}

#[test]
fn vertical_projection_checks_both_endpoints_and_the_exact_limit_boundary() {
    let start = point(1.0, -3.0, 2.0);
    let end = point(1.0, 10.0, 2.0);
    let path = Path::Complete(vec![point(1.0, 0.0, 2.0), point(1.0, 6.0, 2.0)]);
    for (limit, outcome) in [
        (None, ProjectionOutcome::Unassessed),
        (Some(4.0), ProjectionOutcome::WithinLimit),
        (Some(f64::MAX), ProjectionOutcome::WithinLimit),
        (
            Some(f64::from_bits(4.0_f64.to_bits() - 1)),
            ProjectionOutcome::LimitExceeded,
        ),
        (Some(0.0), ProjectionOutcome::LimitExceeded),
    ] {
        let result = measure_complete_path(start, end, &path, limit).unwrap();
        assert_eq!(result.start_projection_distance, 3.0);
        assert_eq!(result.end_projection_distance, 4.0);
        assert_eq!(result.max_projection_distance, 4.0);
        assert_eq!(result.requested_separation, 13.0);
        assert_eq!(result.reported_endpoint_separation, 6.0);
        assert_eq!(result.path_length, 6.0);
        assert_eq!(result.projection_limit, limit);
        assert_eq!(result.projection, outcome);
    }
}

#[test]
fn two_identical_points_and_zero_limit_are_valid_without_an_epsilon() {
    let p = point(1.0, 2.0, 3.0);
    let path = Path::Complete(vec![p, p]);
    let result = measure_complete_path(p, p, &path, Some(0.0)).unwrap();
    assert_eq!(result.start_projection_distance, 0.0);
    assert_eq!(result.end_projection_distance, 0.0);
    assert_eq!(result.max_projection_distance, 0.0);
    assert_eq!(result.requested_separation, 0.0);
    assert_eq!(result.reported_endpoint_separation, 0.0);
    assert_eq!(result.path_length, 0.0);
    assert!(result.reported_endpoints_equal_requested);
    assert_eq!(result.projection, ProjectionOutcome::WithinLimit);

    let nearby = point(f32::from_bits(1.0_f32.to_bits() + 1), p.y, p.z);
    let projected = measure_complete_path(nearby, p, &path, Some(0.0)).unwrap();
    assert!(projected.start_projection_distance > 0.0);
    assert!(!projected.reported_endpoints_equal_requested);
    assert_eq!(projected.projection, ProjectionOutcome::LimitExceeded);
}

#[test]
fn every_noncomplete_variant_is_refused() {
    let p = point(0.0, 0.0, 0.0);
    for path in [
        Path::Partial(vec![p, p]),
        Path::Partial(vec![point(f32::NAN, 0.0, 0.0)]),
        Path::Unreachable,
        Path::Unavailable,
    ] {
        assert_eq!(
            measure_complete_path(p, p, &path, None),
            Err(RouteError::NotComplete)
        );
    }
}

#[test]
fn invalid_limits_and_requested_points_follow_the_documented_validation_order() {
    let p = point(0.0, 0.0, 0.0);
    let bad = point(f32::NAN, 0.0, 0.0);
    for limit in [-1.0, f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        assert_eq!(
            measure_complete_path(bad, p, &Path::Unavailable, Some(limit)),
            Err(RouteError::InvalidProjectionLimit)
        );
    }
    for invalid in [
        bad,
        point(0.0, f32::INFINITY, 0.0),
        point(0.0, 0.0, f32::NEG_INFINITY),
    ] {
        assert_eq!(
            measure_complete_path(invalid, p, &Path::Unavailable, None),
            Err(RouteError::NonFiniteRequestedPoint)
        );
        assert_eq!(
            measure_complete_path(p, invalid, &Path::Complete(vec![p, p]), Some(0.0)),
            Err(RouteError::NonFiniteRequestedPoint)
        );
    }
}

#[test]
fn point_count_bounds_are_inclusive_and_checked_before_route_coordinates() {
    let p = point(0.0, 0.0, 0.0);
    for points in [vec![], vec![point(f32::NAN, 0.0, 0.0)]] {
        assert_eq!(
            measure_complete_path(p, p, &Path::Complete(points), None),
            Err(RouteError::TooFewPoints)
        );
    }
    assert_eq!(MAX_ROUTE_POINTS, 256);
    let too_many = vec![point(f32::NAN, 0.0, 0.0); MAX_ROUTE_POINTS + 1];
    assert_eq!(
        measure_complete_path(p, p, &Path::Complete(too_many), None),
        Err(RouteError::TooManyPoints)
    );
    let points: Vec<_> = (0..MAX_ROUTE_POINTS)
        .map(|x| point(x as f32, 0.0, 0.0))
        .collect();
    let end = points[MAX_ROUTE_POINTS - 1];
    let result = measure_complete_path(p, end, &Path::Complete(points), None).unwrap();
    assert_eq!(result.point_count, 256);
    assert_eq!(result.path_length, 255.0);
    assert!(result.reported_endpoints_equal_requested);
}

#[test]
fn every_route_point_must_be_finite_including_interior_points() {
    let p = point(0.0, 0.0, 0.0);
    for invalid in [
        point(f32::NAN, 0.0, 0.0),
        point(0.0, f32::INFINITY, 0.0),
        point(0.0, 0.0, f32::NEG_INFINITY),
    ] {
        for index in 0..3 {
            let mut points = vec![p, p, p];
            points[index] = invalid;
            assert_eq!(
                measure_complete_path(p, p, &Path::Complete(points), None),
                Err(RouteError::NonFiniteRoutePoint)
            );
        }
    }
}

#[test]
fn opposite_f32_extremes_and_the_bounded_polyline_sum_stay_finite_in_f64() {
    let low = point(-f32::MAX, -f32::MAX, -f32::MAX);
    let high = point(f32::MAX, f32::MAX, f32::MAX);
    let points: Vec<_> = (0..MAX_ROUTE_POINTS)
        .map(|i| if i % 2 == 0 { low } else { high })
        .collect();
    let result = measure_complete_path(low, high, &Path::Complete(points), Some(0.0)).unwrap();
    let segment = 2.0 * f64::from(f32::MAX) * 3.0_f64.sqrt();
    assert!((result.requested_separation / segment - 1.0).abs() < 1e-15);
    assert!((result.reported_endpoint_separation / segment - 1.0).abs() < 1e-15);
    assert!((result.path_length / (segment * 255.0) - 1.0).abs() < 1e-13);
    for metric in [
        result.start_projection_distance,
        result.end_projection_distance,
        result.max_projection_distance,
        result.requested_separation,
        result.reported_endpoint_separation,
        result.path_length,
    ] {
        assert!(metric.is_finite());
    }
    assert_eq!(result.projection, ProjectionOutcome::WithinLimit);

    let projected =
        measure_complete_path(high, low, &Path::Complete(vec![low, high]), None).unwrap();
    for displacement in [
        projected.start_projection_distance,
        projected.end_projection_distance,
        projected.max_projection_distance,
    ] {
        assert!(displacement.is_finite());
        assert!((displacement / segment - 1.0).abs() < 1e-15);
    }
}
