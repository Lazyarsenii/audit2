#!/usr/bin/env python3
"""
Repo Auditor MCP Server for Claude Desktop.

This server exposes repo-auditor functionality as MCP tools that can be
used directly from Claude Desktop or any MCP-compatible client.

Installation in Claude Desktop:
1. Add to claude_desktop_config.json:
   {
     "mcpServers": {
       "repo-auditor": {
         "command": "python3",
         "args": ["/path/to/repo-auditor/backend/mcp_server.py"],
         "env": {}
       }
     }
   }

2. Restart Claude Desktop

Usage:
- "Analyze repository at /path/to/repo"
- "Check readiness of project at /path"
- "Generate acceptance report for /path with EU profile"
"""
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("/tmp/repo-auditor-mcp.log"), logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("repo-auditor-mcp")


class MCPServer:
    """MCP Server implementation for Repo Auditor."""

    def __init__(self):
        self.tools = {
            "analyze_repo": self.analyze_repo,
            "check_readiness": self.check_readiness,
            "list_profiles": self.list_profiles,
            "generate_report": self.generate_report,
            "get_metrics": self.get_metrics,
            "quick_scan": self.quick_scan,
        }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request."""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        logger.info(f"Received request: {method}")

        try:
            if method == "initialize":
                return self._init_response(request_id)
            elif method == "tools/list":
                return self._tools_list_response(request_id)
            elif method == "tools/call":
                return await self._handle_tool_call(request_id, params)
            else:
                return self._error_response(request_id, -32601, f"Method not found: {method}")
        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            return self._error_response(request_id, -32603, str(e))

    def _init_response(self, request_id: Any) -> Dict[str, Any]:
        """Return initialization response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "repo-auditor",
                    "version": "1.0.0"
                }
            }
        }

    def _tools_list_response(self, request_id: Any) -> Dict[str, Any]:
        """Return list of available tools."""
        tools = [
            {
                "name": "analyze_repo",
                "description": "Run full repository analysis including scoring, cost estimation, and report generation",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the repository to analyze"
                        },
                        "profile": {
                            "type": "string",
                            "description": "Evaluation profile to use (e.g., 'eu_standard', 'ua_standard', 'startup')",
                            "default": "eu_standard"
                        },
                        "generate_reports": {
                            "type": "boolean",
                            "description": "Whether to generate report documents",
                            "default": True
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "check_readiness",
                "description": "Check if a project is ready for formal evaluation and get recommendations",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the repository"
                        },
                        "profile": {
                            "type": "string",
                            "description": "Evaluation profile for acceptance criteria",
                            "default": "eu_standard"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "quick_scan",
                "description": "Quick repository scan with basic metrics (faster than full analysis)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the repository"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "list_profiles",
                "description": "List all available evaluation profiles with pricing and requirements",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "region": {
                            "type": "string",
                            "description": "Filter by region (eu, ua, us, asia, global)",
                            "enum": ["eu", "ua", "us", "asia", "global"]
                        }
                    }
                }
            },
            {
                "name": "generate_report",
                "description": "Generate specific report type for a completed analysis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "analysis_id": {
                            "type": "string",
                            "description": "Analysis ID from previous analysis"
                        },
                        "report_type": {
                            "type": "string",
                            "description": "Type of report to generate",
                            "enum": ["review", "summary", "acceptance", "act"]
                        },
                        "profile": {
                            "type": "string",
                            "description": "Evaluation profile for formatting"
                        }
                    },
                    "required": ["analysis_id", "report_type"]
                }
            },
            {
                "name": "get_metrics",
                "description": "Get raw metrics from a previous analysis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "analysis_id": {
                            "type": "string",
                            "description": "Analysis ID"
                        },
                        "category": {
                            "type": "string",
                            "description": "Filter by category (documentation, structure, etc.)"
                        }
                    },
                    "required": ["analysis_id"]
                }
            }
        ]

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools}
        }

    async def _handle_tool_call(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            return self._error_response(request_id, -32602, f"Unknown tool: {tool_name}")

        try:
            result = await self.tools[tool_name](**arguments)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2, default=str)
                        }
                    ]
                }
            }
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}", exc_info=True)
            return self._error_response(request_id, -32603, f"Tool execution failed: {e}")

    def _error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        """Return error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message}
        }

    # =========================================================================
    # TOOL IMPLEMENTATIONS
    # =========================================================================

    async def analyze_repo(
        self,
        path: str,
        profile: str = "eu_standard",
        generate_reports: bool = True,
    ) -> Dict[str, Any]:
        """Run full repository analysis."""
        from app.metrics.pipeline import AnalysisPipeline, PipelineConfig
        from app.config.evaluation_profiles import profile_manager

        logger.info(f"Analyzing repository: {path}")

        # Get profile
        eval_profile = profile_manager.get(profile)
        if not eval_profile:
            return {"error": f"Profile not found: {profile}"}

        # Configure pipeline
        config = PipelineConfig(
            region_mode=eval_profile.region.value.upper(),
            generate_reports=generate_reports,
            report_types=["review", "summary"],
        )

        # Run analysis
        pipeline = AnalysisPipeline(config)
        result = await pipeline.run(
            repo_path=path,
            repo_url=f"file://{path}",
        )

        # Calculate cost using profile
        if result.scoring_result:
            hours = result.scoring_result.forward_estimate.hours_typical.total
            cost = eval_profile.pricing.calculate_cost(hours)
        else:
            cost = None

        return {
            "analysis_id": result.analysis_id,
            "status": result.status,
            "duration_seconds": result.duration_seconds,
            "profile_used": profile,
            "scores": {
                "repo_health": result.scoring_result.repo_health.to_dict() if result.scoring_result else None,
                "tech_debt": result.scoring_result.tech_debt.to_dict() if result.scoring_result else None,
            },
            "classification": {
                "product_level": result.scoring_result.product_level.value if result.scoring_result else None,
                "complexity": result.scoring_result.complexity.value if result.scoring_result else None,
                "verdict": result.scoring_result.verdict if result.scoring_result else None,
            },
            "cost_estimation": cost,
            "metrics_count": result.metrics_count,
            "tasks_count": len(result.scoring_result.tasks) if result.scoring_result else 0,
            "reports_generated": list(result.reports.keys()),
            "report_files": [str(p) for p in result.report_files],
            "errors": result.errors,
        }

    async def check_readiness(
        self,
        path: str,
        profile: str = "eu_standard",
    ) -> Dict[str, Any]:
        """Check project readiness for evaluation."""
        from app.metrics.pipeline import AnalysisPipeline, PipelineConfig
        from app.services.readiness_assessor import readiness_assessor
        from app.config.evaluation_profiles import profile_manager

        logger.info(f"Checking readiness: {path}")

        # Get profile
        eval_profile = profile_manager.get(profile)
        if not eval_profile:
            return {"error": f"Profile not found: {profile}"}

        # Run quick analysis
        config = PipelineConfig(generate_reports=False)
        pipeline = AnalysisPipeline(config)
        result = await pipeline.run(repo_path=path, repo_url=f"file://{path}")

        if result.status == "failed":
            return {"error": f"Analysis failed: {result.errors}"}

        # Run readiness assessment
        sr = result.scoring_result
        structure_data = result.metrics.to_flat_dict() if result.metrics else {}
        static_metrics = result.metrics.to_flat_dict() if result.metrics else {}

        assessment = readiness_assessor.assess(
            repo_health=sr.repo_health,
            tech_debt=sr.tech_debt,
            product_level=sr.product_level,
            complexity=sr.complexity,
            structure_data=structure_data,
            static_metrics=static_metrics,
        )

        # Check against profile acceptance criteria
        criteria = eval_profile.acceptance
        meets_criteria = (
            sr.repo_health.total >= criteria.min_repo_health and
            sr.tech_debt.total >= criteria.min_tech_debt and
            assessment.readiness_score >= criteria.min_readiness
        )

        return {
            "path": path,
            "profile": profile,
            "readiness_level": assessment.readiness_level.value,
            "readiness_score": assessment.readiness_score,
            "meets_profile_criteria": meets_criteria,
            "profile_requirements": {
                "min_repo_health": criteria.min_repo_health,
                "min_tech_debt": criteria.min_tech_debt,
                "min_readiness": criteria.min_readiness,
            },
            "actual_scores": {
                "repo_health": sr.repo_health.total,
                "tech_debt": sr.tech_debt.total,
            },
            "checks_passed": assessment.passed_checks,
            "checks_failed": assessment.failed_checks,
            "blockers_count": assessment.blockers_count,
            "estimated_fix_hours": assessment.estimated_fix_hours,
            "summary": assessment.summary,
            "next_steps": assessment.next_steps,
            "recommendations": [
                {
                    "title": r.title,
                    "priority": r.priority.value,
                    "effort_hours": r.effort_hours,
                }
                for r in assessment.recommendations[:5]  # Top 5
            ],
        }

    async def quick_scan(self, path: str) -> Dict[str, Any]:
        """Quick repository scan with basic metrics."""
        from app.metrics.collectors import metrics_aggregator

        logger.info(f"Quick scan: {path}")

        # Run collectors only (no scoring)
        metrics = await metrics_aggregator.collect_all(
            repo_path=Path(path),
            analysis_id="quick",
            repo_url=f"file://{path}",
        )

        # Extract key metrics
        flat = metrics.to_flat_dict()

        return {
            "path": path,
            "metrics_collected": len(metrics.metrics),
            "summary": {
                "has_readme": flat.get("repo.docs.has_readme", False),
                "has_tests": flat.get("repo.structure.has_tests", False),
                "has_ci": flat.get("repo.infra.has_ci", False),
                "has_docker": flat.get("repo.run.has_dockerfile", False),
                "loc_total": flat.get("repo.size.loc_total", 0),
                "files_total": flat.get("repo.size.files_total", 0),
                "commits_total": flat.get("repo.git.commits_total", 0),
                "authors_count": flat.get("repo.git.authors_count", 0),
            }
        }

    async def list_profiles(self, region: Optional[str] = None) -> Dict[str, Any]:
        """List available evaluation profiles."""
        from app.config.evaluation_profiles import profile_manager, Region

        if region:
            profiles = profile_manager.list_by_region(Region(region))
        else:
            profiles = profile_manager.list()

        return {
            "profiles": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "region": p.region.value,
                    "standard": p.standard.value,
                    "currency": p.pricing.currency.value,
                    "hourly_rates": p.pricing.hourly_rates.to_dict(),
                    "acceptance_criteria": {
                        "min_repo_health": p.acceptance.min_repo_health,
                        "min_tech_debt": p.acceptance.min_tech_debt,
                        "min_readiness": p.acceptance.min_readiness,
                    }
                }
                for p in profiles
            ],
            "count": len(profiles),
        }

    async def generate_report(
        self,
        analysis_id: str,
        report_type: str,
        profile: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate specific report for analysis."""
        from app.metrics.storage import metrics_store

        logger.info(f"Generating {report_type} report for {analysis_id}")

        # Get metrics
        metrics = await metrics_store.get(analysis_id)
        if not metrics:
            return {"error": f"Analysis not found: {analysis_id}"}

        # TODO: Implement report generation based on type
        return {
            "analysis_id": analysis_id,
            "report_type": report_type,
            "status": "generated",
            "message": "Report generation not yet implemented",
        }

    async def get_metrics(
        self,
        analysis_id: str,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get raw metrics from analysis."""
        from app.metrics.storage import metrics_store

        metrics = await metrics_store.get(analysis_id)
        if not metrics:
            return {"error": f"Analysis not found: {analysis_id}"}

        all_metrics = metrics.to_flat_dict()

        if category:
            filtered = {k: v for k, v in all_metrics.items() if category in k}
            return {"analysis_id": analysis_id, "category": category, "metrics": filtered}

        return {"analysis_id": analysis_id, "metrics": all_metrics}


async def main():
    """Main entry point for MCP server."""
    server = MCPServer()

    logger.info("Repo Auditor MCP Server starting...")

    # Read from stdin, write to stdout
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, asyncio.get_event_loop())

    buffer = ""
    while True:
        try:
            chunk = await reader.read(4096)
            if not chunk:
                break

            buffer += chunk.decode()

            # Process complete JSON-RPC messages
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue

                try:
                    request = json.loads(line)
                    response = await server.handle_request(request)
                    response_str = json.dumps(response) + "\n"
                    writer.write(response_str.encode())
                    await writer.drain()
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")

        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            break

    logger.info("MCP Server shutting down")


if __name__ == "__main__":
    asyncio.run(main())
