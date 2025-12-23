"""
Remote MCP Server endpoint for Claude Web Connector.

This provides an SSE-based MCP server that Claude can connect to directly.
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Tool definitions
TOOLS = [
    {
        "name": "analyze_repository",
        "description": "Analyze a GitHub repository and get metrics including lines of code, file count, languages used, commit history, contributors, repository health score, technical debt score, and cost estimation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_url": {
                    "type": "string",
                    "description": "GitHub repository URL (e.g., https://github.com/user/repo)"
                }
            },
            "required": ["repo_url"]
        }
    },
    {
        "name": "generate_work_report",
        "description": "Generate a work report with task breakdown for a repository. Returns a URL to download the PDF report.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_url": {
                    "type": "string",
                    "description": "GitHub repository URL"
                },
                "start_date": {
                    "type": "string",
                    "description": "Report start date in YYYY-MM-DD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "Report end date in YYYY-MM-DD format"
                },
                "consultant_name": {
                    "type": "string",
                    "description": "Name of the consultant or developer"
                },
                "organization": {
                    "type": "string",
                    "description": "Organization name"
                },
                "worker_type": {
                    "type": "string",
                    "description": "Worker type: 'worker' for single worker with max 8 hours per day, or 'team' for team with no daily limit",
                    "enum": ["worker", "team"]
                }
            },
            "required": ["repo_url"]
        }
    },
    {
        "name": "get_quick_stats",
        "description": "Get quick statistics about a GitHub repository without full analysis. Returns basic metrics like LOC, file count, and main languages.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_url": {
                    "type": "string",
                    "description": "GitHub repository URL"
                }
            },
            "required": ["repo_url"]
        }
    }
]


async def analyze_repository(repo_url: str) -> Dict[str, Any]:
    """Analyze a GitHub repository."""
    from app.api.routes.quick_audit import quick_audit, QuickAuditRequest

    try:
        request = QuickAuditRequest(repo_url=repo_url)
        result = await quick_audit(request)

        # Format for readability
        return {
            "repository": result.get("repo_name", "Unknown"),
            "analysis_time": result.get("analysis_time", "Unknown"),
            "metrics": {
                "total_lines_of_code": result.get("static_metrics", {}).get("total_loc", 0),
                "files_count": result.get("static_metrics", {}).get("files_count", 0),
                "languages": list(result.get("static_metrics", {}).get("languages", {}).keys()),
                "commits": result.get("git_metrics", {}).get("total_commits", 0),
                "contributors": result.get("git_metrics", {}).get("authors_count", 0),
            },
            "scores": {
                "repository_health": f"{result.get('repo_health', {}).get('total', 0)}/12",
                "technical_debt": f"{result.get('tech_debt', {}).get('total', 0)}/15",
            },
            "cost_estimate": {
                "hours_estimate": round(result.get("cost_estimate", {}).get("hours_typical", 0)),
                "cost_ukraine": f"${round(result.get('cost_estimate', {}).get('cost_ua_typical', 0)):,}",
                "cost_eu": f"€{round(result.get('cost_estimate', {}).get('cost_eu_typical', 0)):,}",
            },
            "work_report_hours": round(result.get("cost_estimate", {}).get("hours_typical", 0) / 10),
        }
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return {"error": str(e)}


async def generate_work_report(
    repo_url: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    consultant_name: Optional[str] = None,
    organization: Optional[str] = None,
    worker_type: str = "worker"
) -> Dict[str, Any]:
    """Generate work report and return download info."""
    base_url = "https://audit2-production.up.railway.app"

    # Build the API call instructions
    payload = {"repo_url": repo_url, "worker_type": worker_type}
    if start_date:
        payload["start_date"] = start_date
    if end_date:
        payload["end_date"] = end_date
    if consultant_name:
        payload["consultant_name"] = consultant_name
    if organization:
        payload["organization"] = organization

    return {
        "message": "Work report can be generated using the API or Web UI",
        "web_ui": f"{base_url}/quick",
        "api_endpoint": f"{base_url}/api/work-report",
        "curl_command": f'curl -X POST "{base_url}/api/work-report" -H "Content-Type: application/json" -d \'{json.dumps(payload)}\' -o work_report.pdf',
        "parameters": payload
    }


async def get_quick_stats(repo_url: str) -> Dict[str, Any]:
    """Get quick stats for a repository."""
    # Just call analyze but return less data
    result = await analyze_repository(repo_url)
    if "error" in result:
        return result

    return {
        "repository": result.get("repository"),
        "lines_of_code": result.get("metrics", {}).get("total_lines_of_code", 0),
        "files": result.get("metrics", {}).get("files_count", 0),
        "languages": result.get("metrics", {}).get("languages", []),
        "health_score": result.get("scores", {}).get("repository_health"),
    }


async def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a tool call and return results."""
    try:
        if name == "analyze_repository":
            return await analyze_repository(arguments.get("repo_url", ""))
        elif name == "generate_work_report":
            return await generate_work_report(
                repo_url=arguments.get("repo_url", ""),
                start_date=arguments.get("start_date"),
                end_date=arguments.get("end_date"),
                consultant_name=arguments.get("consultant_name"),
                organization=arguments.get("organization"),
                worker_type=arguments.get("worker_type", "worker")
            )
        elif name == "get_quick_stats":
            return await get_quick_stats(arguments.get("repo_url", ""))
        else:
            return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/mcp")
async def mcp_sse(request: Request):
    """
    MCP Server-Sent Events endpoint for Claude Web Connector.

    This endpoint handles the MCP protocol over SSE.
    """
    async def event_generator():
        # Send initial connection event
        yield {
            "event": "open",
            "data": json.dumps({
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "quick-auditor", "version": "1.0.0"}
            })
        }

        # Keep connection alive
        while True:
            if await request.is_disconnected():
                break

            # Send heartbeat
            yield {
                "event": "ping",
                "data": ""
            }

            import asyncio
            await asyncio.sleep(30)

    return EventSourceResponse(event_generator())


@router.post("/mcp")
async def mcp_post(request: Request):
    """
    MCP POST endpoint for tool calls.

    Handles JSON-RPC requests from Claude.
    """
    try:
        body = await request.json()
        method = body.get("method", "")
        params = body.get("params", {})
        request_id = body.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "quick-auditor", "version": "1.0.0"}
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": TOOLS}
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            result = await handle_tool_call(tool_name, arguments)

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result, indent=2, ensure_ascii=False)
                    }]
                }
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }

    except Exception as e:
        logger.error(f"MCP error: {e}")
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32603, "message": str(e)}
        }


@router.get("/mcp/info")
async def mcp_info():
    """Get MCP server information."""
    return {
        "name": "Quick Auditor",
        "version": "1.0.0",
        "description": "Analyze GitHub repositories and generate work reports",
        "tools": [{"name": t["name"], "description": t["description"]} for t in TOOLS],
        "connector_url": "https://audit2-production.up.railway.app/api/mcp"
    }
