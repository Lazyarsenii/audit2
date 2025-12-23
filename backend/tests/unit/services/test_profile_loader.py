from app.services.profile_loader import ProfileLoader


def test_list_and_load_scoring_templates():
    loader = ProfileLoader()

    templates = loader.list_scoring_templates()
    template_ids = {t["id"] for t in templates}

    assert "standard_rnd" in template_ids
    assert "regulated_healthcare" in template_ids

    template = loader.load_scoring_template("standard_rnd")
    assert template is not None
    assert template.label == "Standard R&D Scoring"


def test_weighted_scores_and_thresholds():
    loader = ProfileLoader()

    scores = loader.get_weighted_scores(
        template_id="regulated_healthcare",
        repo_health={
            "documentation": 1,
            "structure": 1,
            "runability": 1,
            "history": 0,
        },
        tech_debt={
            "architecture": 1,
            "code_quality": 1,
            "testing": 1,
            "infrastructure": 0,
            "security": 1,
        },
    )

    assert scores["repo_health_weighted"] == 3.5
    assert scores["tech_debt_weighted"] == 6.0
    violation_metrics = {(v["category"], v["metric"]) for v in scores["violations"]}
    assert ("repo_health", "documentation") in violation_metrics
    assert ("tech_debt", "testing") in violation_metrics
