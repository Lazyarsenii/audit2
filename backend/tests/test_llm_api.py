"""
Tests for LLM API Endpoints
"""
import pytest


class TestLLMAPIEndpoints:
    """Test LLM API endpoints"""

    def test_get_providers(self, client):
        """Test GET /api/llm/providers"""
        response = client.get("/api/llm/providers")
        assert response.status_code == 200
        data = response.json()
        assert "ollama" in data
        assert "anthropic" in data
        assert "openai" in data
        assert "google" in data

    def test_analyze_readme_empty(self, client):
        """Test POST /api/llm/analyze/readme with empty content"""
        response = client.post(
            "/api/llm/analyze/readme",
            json={"content": ""}
        )
        assert response.status_code == 400

    def test_analyze_readme_valid(self, client):
        """Test POST /api/llm/analyze/readme with valid content"""
        response = client.post(
            "/api/llm/analyze/readme",
            json={"content": "# Project\n\nA test project with README."}
        )
        assert response.status_code == 200
        data = response.json()
        # Without LLM providers, returns default
        assert "overall_score" in data

    def test_analyze_code_empty(self, client):
        """Test POST /api/llm/analyze/code with empty code"""
        response = client.post(
            "/api/llm/analyze/code",
            json={"code": "", "language": "python", "filename": "test.py"}
        )
        assert response.status_code == 400

    def test_analyze_code_valid(self, client):
        """Test POST /api/llm/analyze/code with valid code"""
        response = client.post(
            "/api/llm/analyze/code",
            json={
                "code": "def hello():\n    print('Hello')",
                "language": "python",
                "filename": "test.py"
            }
        )
        assert response.status_code == 200

    def test_security_review_valid(self, client):
        """Test POST /api/llm/analyze/security"""
        response = client.post(
            "/api/llm/analyze/security",
            json={
                "code": "password = 'secret123'",
                "language": "python",
                "filename": "config.py"
            }
        )
        assert response.status_code == 200

    def test_generate_tz(self, client):
        """Test POST /api/llm/generate/tz"""
        response = client.post(
            "/api/llm/generate/tz",
            json={
                "project_name": "Test Project",
                "repo_health": 5,
                "tech_debt": 3,
                "readiness": 50,
                "issues": "Missing tests",
                "project_type": "R&D",
                "required_repo_health": 8,
                "required_tech_debt": 8,
                "required_readiness": 75
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "tz" in data

    def test_generate_recommendations(self, client):
        """Test POST /api/llm/generate/recommendations"""
        response = client.post(
            "/api/llm/generate/recommendations",
            json={
                "project_name": "Test Project",
                "analysis_summary": "Low test coverage, missing documentation",
                "health_gap": 3,
                "debt_gap": 5,
                "readiness_gap": 25
            }
        )
        assert response.status_code == 200

    def test_simple_query(self, client):
        """Test POST /api/llm/query"""
        response = client.post(
            "/api/llm/query",
            json={
                "prompt": "What is Python?",
                "task_type": "simple_analysis"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data

    def test_simple_query_invalid_task_type(self, client):
        """Test POST /api/llm/query with invalid task type"""
        response = client.post(
            "/api/llm/query",
            json={
                "prompt": "Test",
                "task_type": "invalid_type"
            }
        )
        # Should use default task type
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
