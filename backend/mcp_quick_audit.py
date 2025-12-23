#!/usr/bin/env python3
"""
Simple MCP Server for Quick Audit with Work Report generation.

For Claude Desktop integration.

Installation:
1. Copy this to your claude_desktop_config.json (usually in %APPDATA%/Claude/):
   {
     "mcpServers": {
       "quick-auditor": {
         "command": "python",
         "args": ["C:/Users/verkh/Downloads/auditor-main/auditor-main/backend/mcp_quick_audit.py"],
         "env": {}
       }
     }
   }

2. Restart Claude Desktop

Usage in Claude:
- "Analyze project at C:/path/to/project"
- "Generate work report for C:/path/to/project from 2024-12-01 to 2024-12-31"
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

# Suppress logs to stderr for clean MCP communication
import logging
logging.basicConfig(level=logging.WARNING)


class QuickAuditMCP:
    """Simple MCP Server for Quick Audit."""

    def __init__(self):
        self.tools = {
            "analyze_local_project": self.analyze_local_project,
            "generate_work_report": self.generate_work_report,
            "get_project_stats": self.get_project_stats,
        }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request."""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

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
            return self._error_response(request_id, -32603, str(e))

    def _init_response(self, request_id: Any) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "quick-auditor", "version": "1.0.0"}
            }
        }

    def _tools_list_response(self, request_id: Any) -> Dict[str, Any]:
        tools = [
            {
                "name": "analyze_local_project",
                "description": "Analyze a local project directory and get metrics, scores, and cost estimation",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Full path to the project directory (e.g., C:/Projects/myapp)"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "generate_work_report",
                "description": "Generate a work report PDF with task breakdown for a local project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Full path to the project directory"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Report start date (YYYY-MM-DD)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Report end date (YYYY-MM-DD)"
                        },
                        "consultant_name": {
                            "type": "string",
                            "description": "Name of the consultant/developer",
                            "default": "Developer"
                        },
                        "organization": {
                            "type": "string",
                            "description": "Organization name",
                            "default": "Organization"
                        },
                        "worker_type": {
                            "type": "string",
                            "description": "Worker type: 'worker' (max 8h/day) or 'team' (no limit)",
                            "enum": ["worker", "team"],
                            "default": "worker"
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Where to save the PDF report (optional, defaults to project directory)"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "get_project_stats",
                "description": "Get quick statistics about a local project (LOC, files, languages)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Full path to the project directory"
                        }
                    },
                    "required": ["path"]
                }
            }
        ]
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools}
        }

    async def _handle_tool_call(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
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
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result, indent=2, default=str, ensure_ascii=False)
                    }]
                }
            }
        except Exception as e:
            return self._error_response(request_id, -32603, f"Tool failed: {e}")

    def _error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message}
        }

    # =========================================================================
    # TOOL IMPLEMENTATIONS
    # =========================================================================

    async def analyze_local_project(self, path: str) -> Dict[str, Any]:
        """Analyze a local project directory."""
        from app.analyzers.static_analyzer import static_analyzer
        from app.analyzers.git_analyzer import git_analyzer
        from app.core.scoring.repo_health import calculate_repo_health
        from app.core.scoring.tech_debt import calculate_tech_debt
        from app.services.cocomo_estimator import cocomo_estimator

        repo_path = Path(path)
        if not repo_path.exists():
            return {"error": f"Path does not exist: {path}"}

        # Run analysis
        static_metrics = await static_analyzer.analyze(repo_path)
        git_metrics = await git_analyzer.analyze(repo_path)

        combined = {**static_metrics, **git_metrics}
        repo_health = calculate_repo_health(combined)
        tech_debt = calculate_tech_debt(static_metrics, [])

        # Cost estimation
        loc = static_metrics.get("total_loc", 0)
        estimate = cocomo_estimator.estimate(
            loc=loc,
            tech_debt_score=tech_debt.total,
        )

        return {
            "project_name": repo_path.name,
            "path": str(repo_path),
            "metrics": {
                "total_loc": static_metrics.get("total_loc", 0),
                "files_count": static_metrics.get("files_count", 0),
                "languages": list(static_metrics.get("languages", {}).keys()),
                "commits": git_metrics.get("total_commits", 0),
                "contributors": git_metrics.get("authors_count", 0),
            },
            "scores": {
                "repo_health": f"{repo_health.total}/12",
                "tech_debt": f"{tech_debt.total}/15",
            },
            "cost_estimate": {
                "hours": round(estimate.hours_typical),
                "cost_ua": f"${round(estimate.cost_ua_typical):,}",
                "cost_eu": f"€{round(estimate.cost_eu_typical):,}",
            },
            "work_report_hours": round(estimate.hours_typical / 10),
        }

    async def generate_work_report(
        self,
        path: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        consultant_name: str = "Developer",
        organization: str = "Organization",
        worker_type: str = "worker",
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate work report PDF."""
        from app.analyzers.static_analyzer import static_analyzer
        from app.analyzers.git_analyzer import git_analyzer
        from app.core.scoring.repo_health import calculate_repo_health
        from app.core.scoring.tech_debt import calculate_tech_debt
        from app.services.cocomo_estimator import cocomo_estimator
        from app.services.work_report_generator import (
            work_report_generator, WorkReportConfig, WorkerType
        )

        repo_path = Path(path)
        if not repo_path.exists():
            return {"error": f"Path does not exist: {path}"}

        # Parse dates
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            today = datetime.now()
            start = today.replace(day=1)

        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            next_month = start.replace(day=28) + timedelta(days=4)
            end = next_month - timedelta(days=next_month.day)

        # Analyze
        static_metrics = await static_analyzer.analyze(repo_path)
        git_metrics = await git_analyzer.analyze(repo_path)

        combined = {**static_metrics, **git_metrics}
        repo_health = calculate_repo_health(combined)
        tech_debt = calculate_tech_debt(static_metrics, [])

        # Estimate
        loc = static_metrics.get("total_loc", 0)
        estimate = cocomo_estimator.estimate(loc=loc, tech_debt_score=tech_debt.total)

        # Build analysis dict
        analysis = {
            "repo_name": repo_path.name,
            "static_metrics": static_metrics,
            "git_metrics": git_metrics,
            "repo_health": repo_health.to_dict(),
            "tech_debt": tech_debt.to_dict(),
            "cost_estimate": estimate.to_dict(),
        }

        # Work hours = COCOMO / 10
        work_hours = estimate.hours_typical / 10

        # Config
        wtype = WorkerType.WORKER if worker_type == "worker" else WorkerType.TEAM
        config = WorkReportConfig(
            start_date=start,
            end_date=end,
            consultant_name=consultant_name,
            organization=organization,
            project_name=repo_path.name,
            worker_type=wtype,
        )

        # Generate tasks
        tasks = work_report_generator.generate_tasks_from_analysis(
            analysis, work_hours, config
        )

        # Generate PDF
        pdf_bytes = work_report_generator.generate_pdf_report(tasks, config, analysis)

        # Save
        if output_path:
            save_path = Path(output_path)
        else:
            save_path = repo_path / f"{repo_path.name}_work_report.pdf"

        with open(save_path, "wb") as f:
            f.write(pdf_bytes)

        return {
            "success": True,
            "project": repo_path.name,
            "period": f"{start.strftime('%d.%m.%Y')} - {end.strftime('%d.%m.%Y')}",
            "worker_type": worker_type,
            "total_hours": round(sum(t.hours for t in tasks)),
            "tasks_count": len(tasks),
            "report_saved_to": str(save_path),
        }

    async def get_project_stats(self, path: str) -> Dict[str, Any]:
        """Get quick project statistics."""
        from app.analyzers.static_analyzer import static_analyzer

        repo_path = Path(path)
        if not repo_path.exists():
            return {"error": f"Path does not exist: {path}"}

        metrics = await static_analyzer.analyze(repo_path)

        return {
            "project": repo_path.name,
            "total_loc": metrics.get("total_loc", 0),
            "files_count": metrics.get("files_count", 0),
            "languages": metrics.get("languages", {}),
            "has_tests": any("test" in str(f).lower() for f in repo_path.rglob("*")),
            "has_readme": (repo_path / "README.md").exists() or (repo_path / "readme.md").exists(),
        }


async def main():
    """Main MCP server loop."""
    server = QuickAuditMCP()

    # Read from stdin, write to stdout (MCP protocol)
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
                except json.JSONDecodeError:
                    pass

        except Exception:
            break


if __name__ == "__main__":
    asyncio.run(main())
