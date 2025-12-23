"""
Prompts for Repo Auditor LLM Tasks
"""

# =============================================================================
# README Quality Analysis
# =============================================================================

README_QUALITY_SYSTEM = """You are a technical documentation expert.
Analyze README files for completeness and quality.
Respond in JSON format only."""

README_QUALITY_PROMPT = """Analyze this README file and rate its quality:

```markdown
{readme_content}
```

Rate each aspect 0-10 and provide brief feedback:
{{
  "scores": {{
    "project_description": <0-10>,
    "installation_guide": <0-10>,
    "usage_examples": <0-10>,
    "api_documentation": <0-10>,
    "contributing_guide": <0-10>,
    "license_info": <0-10>
  }},
  "overall_score": <0-100>,
  "missing_sections": ["list of missing sections"],
  "improvements": ["top 3 improvement suggestions"]
}}"""

# =============================================================================
# Code Quality Analysis
# =============================================================================

CODE_QUALITY_SYSTEM = """You are a senior software engineer reviewing code quality.
Focus on maintainability, readability, and best practices.
Respond in JSON format only."""

CODE_QUALITY_PROMPT = """Analyze this code for quality issues:

Language: {language}
File: {filename}

```{language}
{code_content}
```

Provide analysis:
{{
  "complexity": {{
    "score": <0-10, 10=simple>,
    "issues": ["list of complexity issues"]
  }},
  "maintainability": {{
    "score": <0-10>,
    "issues": ["list of maintainability issues"]
  }},
  "code_smells": [
    {{"type": "smell type", "location": "line/function", "severity": "high/medium/low"}}
  ],
  "suggestions": ["top 3 improvement suggestions"]
}}"""

# =============================================================================
# Tech Debt Analysis
# =============================================================================

TECH_DEBT_SYSTEM = """You are a technical debt analyst.
Identify and categorize technical debt in codebases.
Respond in JSON format only."""

TECH_DEBT_PROMPT = """Analyze this codebase summary for technical debt:

Repository: {repo_name}
Languages: {languages}
Structure:
{structure}

Known Issues:
{known_issues}

Provide tech debt analysis:
{{
  "debt_items": [
    {{
      "category": "architecture/code/testing/documentation/infrastructure",
      "description": "description",
      "impact": "high/medium/low",
      "effort_hours": <estimated hours>,
      "priority": 1-5
    }}
  ],
  "total_debt_hours": <sum of all effort_hours>,
  "critical_items": ["list of high-impact items"],
  "quick_wins": ["list of low-effort high-impact items"]
}}"""

# =============================================================================
# TZ (Technical Specification) Generation
# =============================================================================

TZ_GENERATION_SYSTEM = """You are a technical specification writer.
Create clear, actionable technical specifications for software improvements.
Write in Russian (Ukrainian project context) or English based on preference."""

TZ_GENERATION_PROMPT = """Generate a Technical Specification (ТЗ) for improving this project:

Project: {project_name}
Current State:
- Repo Health Score: {repo_health}/12
- Tech Debt Score: {tech_debt}/15
- Readiness: {readiness}%

Issues to Address:
{issues}

Target Standards:
- Project Type: {project_type}
- Required Repo Health: {required_repo_health}
- Required Tech Debt: {required_tech_debt}
- Required Readiness: {required_readiness}%

Generate a detailed ТЗ with:
1. Цілі та завдання (Goals)
2. Поточний стан (Current state analysis)
3. Вимоги до виконання (Requirements)
4. Етапи виконання (Implementation phases)
5. Критерії приймання (Acceptance criteria)
6. Оцінка трудовитрат (Effort estimate)
"""

# =============================================================================
# Recommendations
# =============================================================================

RECOMMENDATIONS_SYSTEM = """You are a software development consultant.
Provide actionable recommendations for improving projects.
Focus on practical, prioritized improvements."""

RECOMMENDATIONS_PROMPT = """Based on this project analysis, provide recommendations:

Project: {project_name}
Analysis Results:
{analysis_summary}

Gaps to Target:
- Repo Health: {health_gap} points needed
- Tech Debt: {debt_gap} points needed
- Readiness: {readiness_gap}% needed

Provide prioritized recommendations:
{{
  "immediate_actions": [
    {{"action": "description", "impact": "high/medium/low", "effort": "hours"}}
  ],
  "short_term": [
    {{"action": "description", "impact": "high/medium/low", "effort": "hours"}}
  ],
  "long_term": [
    {{"action": "description", "impact": "high/medium/low", "effort": "hours"}}
  ],
  "estimated_total_hours": <number>,
  "priority_order": ["ordered list of actions"]
}}"""

# =============================================================================
# Security Review
# =============================================================================

SECURITY_REVIEW_SYSTEM = """You are a security engineer reviewing code for vulnerabilities.
Focus on OWASP Top 10 and common security issues.
Respond in JSON format only."""

SECURITY_REVIEW_PROMPT = """Review this code for security issues:

Language: {language}
File: {filename}

```{language}
{code_content}
```

Identify security issues:
{{
  "vulnerabilities": [
    {{
      "type": "OWASP category or description",
      "severity": "critical/high/medium/low",
      "location": "line or function",
      "description": "explanation",
      "fix": "recommended fix"
    }}
  ],
  "security_score": <0-10, 10=secure>,
  "recommendations": ["security improvement suggestions"]
}}"""

# =============================================================================
# Architecture Analysis
# =============================================================================

ARCHITECTURE_SYSTEM = """You are a software architect reviewing system architecture.
Analyze structure, patterns, and architectural decisions.
Respond in JSON format only."""

ARCHITECTURE_PROMPT = """Analyze the architecture of this project:

Project: {project_name}
Structure:
{structure}

Dependencies:
{dependencies}

Provide architectural analysis:
{{
  "architecture_type": "monolith/microservices/serverless/hybrid",
  "patterns_detected": ["list of design patterns"],
  "layers": ["identified architectural layers"],
  "strengths": ["architectural strengths"],
  "weaknesses": ["architectural weaknesses"],
  "recommendations": ["improvement suggestions"],
  "scalability_score": <0-10>,
  "maintainability_score": <0-10>
}}"""
