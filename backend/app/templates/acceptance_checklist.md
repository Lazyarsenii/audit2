# Project Acceptance Checklist

**Project:** {{ repo_name }}
**Date:** {{ date }}
**Profile:** {{ profile_name }}
**Evaluator:** _______________

---

## 1. Documentation Requirements

| Requirement | Required | Present | Status |
|-------------|----------|---------|--------|
{% for doc in required_docs %}
| {{ doc.name }} | {{ doc.required }} | {{ doc.present }} | {{ doc.status }} |
{% endfor %}

**Documentation Score:** {{ doc_score }}/{{ doc_max }}

---

## 2. Technical Requirements

| Requirement | Threshold | Actual | Status |
|-------------|-----------|--------|--------|
| Repo Health Score | ≥ {{ acceptance.min_repo_health }} | {{ scores.repo_health }} | {{ status_repo_health }} |
| Tech Debt Score | ≥ {{ acceptance.min_tech_debt }} | {{ scores.tech_debt }} | {{ status_tech_debt }} |
| Readiness Score | ≥ {{ acceptance.min_readiness }}% | {{ readiness_score }}% | {{ status_readiness }} |
| Tests Present | {{ acceptance.required_tests }} | {{ has_tests }} | {{ status_tests }} |
| CI/CD Configured | {{ acceptance.required_ci }} | {{ has_ci }} | {{ status_ci }} |
| Docker Setup | {{ acceptance.required_docker }} | {{ has_docker }} | {{ status_docker }} |
| Critical Issues | ≤ {{ acceptance.max_critical_issues }} | {{ critical_issues }} | {{ status_security }} |

---

## 3. Blocking Issues

{% if blockers %}
The following issues MUST be resolved before acceptance:

{% for blocker in blockers %}
- [ ] **{{ blocker.title }}**: {{ blocker.description }}
{% endfor %}
{% else %}
[PASS] No blocking issues found.
{% endif %}

---

## 4. Recommendations (Non-blocking)

{% if recommendations %}
{% for rec in recommendations %}
- {{ rec.priority }}: {{ rec.title }} (~{{ rec.effort_hours }}h)
{% endfor %}
{% else %}
No additional recommendations.
{% endif %}

---

## 5. Classification

| Attribute | Value |
|-----------|-------|
| Product Level | {{ product_level }} |
| Complexity | {{ complexity }} |
| Verdict | {{ verdict }} |

---

## 6. Cost Estimation

| Metric | Value |
|--------|-------|
| Estimated Hours | {{ hours }} |
| Cost ({{ currency }}) | {{ cost_formatted }} |
| Rate Applied | {{ profile_name }} |

---

## 7. Decision

- [ ] **ACCEPTED** - Project meets all requirements
- [ ] **ACCEPTED WITH CONDITIONS** - See notes below
- [ ] **REJECTED** - Does not meet minimum requirements

### Conditions/Notes:
_________________________________________________________
_________________________________________________________

---

## Signatures

**Evaluator:** _________________________ Date: _________

**Project Lead:** _________________________ Date: _________

**Approved By:** _________________________ Date: _________
