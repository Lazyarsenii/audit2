from app.services.estimation_suite import EstimationSuite


def test_estimate_all_returns_complete_bundle():
    suite = EstimationSuite()

    result = suite.estimate_all(loc=2000, complexity=1.2, hourly_rate=50)

    assert result.loc == 2000
    assert result.pert is not None
    assert result.ai_efficiency is not None
    # For 2000 LOC we expect 7 methodologies (SEI SLIM excluded for small projects)
    assert len(result.methodologies) >= 7
    assert result.min_cost <= result.max_cost
    assert result.average_cost > 0

    payload = result.to_dict()
    assert payload["summary"]["methodologies_count"] == len(result.methodologies)
    assert payload["pert"]["confidence_intervals"]["68%"]


def test_calculate_pert_custom_builds_cost_ranges():
    suite = EstimationSuite()

    pert = suite.calculate_pert_custom(
        optimistic_days=5,
        most_likely_days=10,
        pessimistic_days=15,
        hourly_rate=100,
    )

    assert pert["inputs"] == {
        "optimistic": 40.0,
        "most_likely": 80.0,
        "pessimistic": 120.0,
    }
    assert pert["expected"] == 80.0
    assert pert["standard_deviation"] == 13.33
    assert pert["cost"]["expected"] == 8000.0
    assert pert["cost"]["range_68"]["min"] == 6666.67
    assert pert["cost"]["range_68"]["max"] == 9333.33
