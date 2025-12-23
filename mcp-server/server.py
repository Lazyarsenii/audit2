#!/usr/bin/env python3
"""
Repo Auditor MCP Server

MCP Server providing repository analysis, cost estimation,
contract compliance checking, and document generation tools
for Claude Code and other AI assistants.

Usage:
    python server.py

Configure in Claude Desktop:
    {
        "mcpServers": {
            "repo-auditor": {
                "command": "python",
                "args": ["/path/to/repo-auditor/mcp-server/server.py"]
            }
        }
    }
"""

import asyncio
import json
import sys
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("Installing MCP SDK...", file=sys.stderr)
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp"])
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent


# ============================================================================
# Template Engine (from Documentator)
# ============================================================================

class TemplateEngine:
    """Simple template engine with variable substitution, conditionals, and loops."""

    def process(self, template: str, variables: Dict[str, Any]) -> str:
        """Process template with given variables."""
        content = template

        # Process variables
        for key, value in variables.items():
            import re
            pattern = rf'\{{\{{{key}(?::[^}}]*)?(?:\|[^}}]*)?\}}\}}'
            content = re.sub(pattern, str(value), content)

        # Process default values {{var|default}}
        content = self._process_defaults(content)

        # Process conditionals {{#if condition}}...{{/if}}
        content = self._process_conditionals(content, variables)

        # Process loops {{#each array as item}}...{{/each}}
        content = self._process_loops(content, variables)

        return content

    def _process_defaults(self, content: str) -> str:
        import re
        pattern = r'\{\{(\w+)(?::(\w+))?\|(.+?)\}\}'
        return re.sub(pattern, lambda m: m.group(3), content)

    def _process_conditionals(self, content: str, variables: Dict[str, Any]) -> str:
        import re
        pattern = r'\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}'
        def replacer(match):
            condition = match.group(1)
            block = match.group(2)
            return block if variables.get(condition) else ''
        return re.sub(pattern, replacer, content, flags=re.DOTALL)

    def _process_loops(self, content: str, variables: Dict[str, Any]) -> str:
        import re
        pattern = r'\{\{#each\s+(\w+)\s+as\s+(\w+)\}\}(.*?)\{\{/each\}\}'

        def replacer(match):
            array_name = match.group(1)
            item_name = match.group(2)
            block = match.group(3)

            array = variables.get(array_name, [])
            if not isinstance(array, list):
                return ''

            result = []
            for item in array:
                processed_block = block
                if isinstance(item, dict):
                    for key, value in item.items():
                        item_pattern = rf'\{{\{{{item_name}\.{key}\}}\}}'
                        processed_block = re.sub(item_pattern, str(value), processed_block)
                else:
                    item_pattern = rf'\{{\{{{item_name}\}}\}}'
                    processed_block = re.sub(item_pattern, str(item), processed_block)
                result.append(processed_block)

            return ''.join(result)

        return re.sub(pattern, replacer, content, flags=re.DOTALL)

    def extract_variables(self, content: str) -> List[str]:
        """Extract variable names from template."""
        import re
        pattern = r'\{\{(\w+)(?::(\w+))?(?:\|(.+?))?\}\}'
        variables = []
        for match in re.finditer(pattern, content):
            var_name = match.group(1)
            if var_name not in variables and not var_name.startswith('#'):
                variables.append(var_name)
        return variables


# ============================================================================
# Business Logic - Scoring & Analysis
# ============================================================================

@dataclass
class RepoHealthScore:
    documentation: int = 0  # 0-3
    structure: int = 0      # 0-3
    runability: int = 0     # 0-3
    history: int = 0        # 0-3

    @property
    def total(self) -> int:
        return self.documentation + self.structure + self.runability + self.history

    @property
    def max_total(self) -> int:
        return 12


@dataclass
class TechDebtScore:
    architecture: int = 0      # 0-3
    code_quality: int = 0      # 0-3
    testing: int = 0           # 0-3
    infrastructure: int = 0    # 0-3
    security: int = 0          # 0-3

    @property
    def total(self) -> int:
        return (self.architecture + self.code_quality +
                self.testing + self.infrastructure + self.security)

    @property
    def max_total(self) -> int:
        return 15


@dataclass
class CostEstimate:
    min_hours: int
    typical_hours: int
    max_hours: int
    hourly_rate: float
    currency: str

    @property
    def min_cost(self) -> float:
        return self.min_hours * self.hourly_rate

    @property
    def typical_cost(self) -> float:
        return self.typical_hours * self.hourly_rate

    @property
    def max_cost(self) -> float:
        return self.max_hours * self.hourly_rate


# Evaluation Profiles
PROFILES = {
    'eu_standard': {
        'name': 'EU Standard R&D',
        'region': 'EU',
        'currency': 'EUR',
        'hourly': {'junior': 35, 'middle': 55, 'senior': 85},
        'requirements': {'repo_health': 6, 'tech_debt': 6, 'readiness': 60},
    },
    'ua_standard': {
        'name': 'Ukraine R&D',
        'region': 'UA',
        'currency': 'USD',
        'hourly': {'junior': 15, 'middle': 30, 'senior': 50},
        'requirements': {'repo_health': 5, 'tech_debt': 5, 'readiness': 50},
    },
    'eu_enterprise': {
        'name': 'EU Enterprise',
        'region': 'EU',
        'currency': 'EUR',
        'hourly': {'junior': 45, 'middle': 70, 'senior': 110},
        'requirements': {'repo_health': 9, 'tech_debt': 10, 'readiness': 80},
    },
    'us_standard': {
        'name': 'US Standard',
        'region': 'US',
        'currency': 'USD',
        'hourly': {'junior': 50, 'middle': 85, 'senior': 130},
        'requirements': {'repo_health': 6, 'tech_debt': 6, 'readiness': 60},
    },
    'startup': {
        'name': 'Startup/MVP',
        'region': 'Global',
        'currency': 'USD',
        'hourly': {'junior': 25, 'middle': 45, 'senior': 70},
        'requirements': {'repo_health': 3, 'tech_debt': 3, 'readiness': 30},
    },
}

# Contract Profiles
CONTRACTS = {
    'standard': {
        'name': 'Standard (No specific requirements)',
        'requirements': [],
    },
    'global_fund': {
        'name': 'Global Fund R13',
        'compliance': ['HIPAA', 'ISO 22301', 'GDPR'],
        'requirements': [
            {'metric': 'documentation', 'min': 2, 'blocking': True},
            {'metric': 'security', 'min': 2, 'blocking': True},
            {'metric': 'testing', 'min': 2, 'blocking': False},
        ],
    },
    'gdpr': {
        'name': 'EU GDPR Compliant',
        'compliance': ['GDPR'],
        'requirements': [
            {'metric': 'security', 'min': 2, 'blocking': True},
            {'metric': 'documentation', 'min': 2, 'blocking': True},
        ],
    },
    'hipaa': {
        'name': 'HIPAA Healthcare',
        'compliance': ['HIPAA', 'HITECH'],
        'requirements': [
            {'metric': 'security', 'min': 3, 'blocking': True},
            {'metric': 'testing', 'min': 2, 'blocking': True},
            {'metric': 'documentation', 'min': 2, 'blocking': True},
        ],
    },
}


# Document Templates
DOCUMENT_TEMPLATES = {
    'act_of_work_uk': '''# АКТ
# виконаних робіт

**Дата:** {{date}}
**Номер:** {{act_number}}

## Сторони

**Виконавець:** {{contractor_name}}
{{contractor_details}}

**Замовник:** {{client_name}}
{{client_details}}

## Опис виконаних робіт

{{#each work_items as item}}
| {{item.description}} | {{item.quantity}} {{item.unit}} | {{item.price}} {{currency}} |
{{/each}}

## Підсумок

**Загальна вартість:** {{total_amount}} {{currency}}
**ПДВ ({{tax_rate}}%):** {{tax_amount}} {{currency}}
**До сплати:** {{grand_total}} {{currency}}

## Підписи

Виконавець: _________________ / {{contractor_representative}} /

Замовник: _________________ / {{client_representative}} /
''',

    'act_of_work_en': '''# ACT
# of Completed Work

**Date:** {{date}}
**Number:** {{act_number}}

## Parties

**Contractor:** {{contractor_name}}
{{contractor_details}}

**Client:** {{client_name}}
{{client_details}}

## Description of Work Performed

{{#each work_items as item}}
| {{item.description}} | {{item.quantity}} {{item.unit}} | {{item.price}} {{currency}} |
{{/each}}

## Summary

**Total Amount:** {{total_amount}} {{currency}}
**VAT ({{tax_rate}}%):** {{tax_amount}} {{currency}}
**Grand Total:** {{grand_total}} {{currency}}

## Signatures

Contractor: _________________ / {{contractor_representative}} /

Client: _________________ / {{client_representative}} /
''',

    'invoice': '''# INVOICE

**Invoice Number:** {{invoice_number}}
**Date:** {{date}}
**Due Date:** {{due_date}}

## From
**{{contractor_name}}**
{{contractor_address}}
Tax ID: {{contractor_tax_id}}
IBAN: {{contractor_iban}}
Bank: {{contractor_bank}}
SWIFT: {{contractor_swift}}

## To
**{{client_name}}**
{{client_address}}
Tax ID: {{client_tax_id}}

## Services

| Description | Qty | Unit Price | Amount |
|-------------|-----|------------|--------|
{{#each items as item}}
| {{item.description}} | {{item.quantity}} | {{item.unit_price}} {{currency}} | {{item.amount}} {{currency}} |
{{/each}}

## Summary

| | |
|---|---|
| Subtotal | {{subtotal}} {{currency}} |
| VAT ({{tax_rate}}%) | {{tax_amount}} {{currency}} |
| **Total Due** | **{{total}} {{currency}}** |

## Payment Instructions

Please transfer the amount to:
- IBAN: {{contractor_iban}}
- Bank: {{contractor_bank}}
- SWIFT: {{contractor_swift}}
- Reference: {{invoice_number}}

Thank you for your business!
''',

    'analysis_report': '''# Repository Analysis Report

**Repository:** {{repo_url}}
**Analysis Date:** {{date}}
**Profile:** {{profile_name}}

## Executive Summary

{{summary}}

## Repository Health Score: {{health_total}}/12

| Metric | Score | Max |
|--------|-------|-----|
| Documentation | {{health_documentation}} | 3 |
| Structure | {{health_structure}} | 3 |
| Runability | {{health_runability}} | 3 |
| Commit History | {{health_history}} | 3 |

## Technical Debt Score: {{debt_total}}/15

| Metric | Score | Max |
|--------|-------|-----|
| Architecture | {{debt_architecture}} | 3 |
| Code Quality | {{debt_code_quality}} | 3 |
| Testing | {{debt_testing}} | 3 |
| Infrastructure | {{debt_infrastructure}} | 3 |
| Security | {{debt_security}} | 3 |

## Cost Estimate

- **Complexity:** {{complexity}}
- **Estimated Hours:** {{min_hours}} - {{max_hours}} hours
- **Cost Range:** {{min_cost}} - {{max_cost}} {{currency}}

## Recommendations

{{#if recommendations}}
{{#each recommendations as rec}}
### {{rec.title}}
**Priority:** {{rec.priority}}
**Effort:** {{rec.hours}} hours

{{rec.description}}

{{/each}}
{{/if}}

---
*Generated by Repo Auditor*
''',
}


# ============================================================================
# MCP Server
# ============================================================================

class RepoAuditorMCPServer:
    """MCP Server for Repo Auditor business logic."""

    def __init__(self):
        self.server = Server("repo-auditor")
        self.template_engine = TemplateEngine()
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="list_profiles",
                    description="List available evaluation profiles with hourly rates and requirements",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    }
                ),
                Tool(
                    name="list_contracts",
                    description="List available contract compliance profiles",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    }
                ),
                Tool(
                    name="estimate_cost",
                    description="Estimate development cost based on complexity and profile",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "complexity": {
                                "type": "string",
                                "enum": ["S", "M", "L"],
                                "description": "Project complexity: S (<160h), M (160-500h), L (>500h)"
                            },
                            "profile_id": {
                                "type": "string",
                                "description": "Evaluation profile ID (eu_standard, ua_standard, etc.)"
                            },
                            "tech_debt_multiplier": {
                                "type": "number",
                                "description": "Tech debt adjustment (1.0-1.5)",
                                "default": 1.0
                            }
                        },
                        "required": ["complexity", "profile_id"]
                    }
                ),
                Tool(
                    name="check_readiness",
                    description="Assess project readiness for audit based on scores",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "health_documentation": {"type": "integer", "minimum": 0, "maximum": 3},
                            "health_structure": {"type": "integer", "minimum": 0, "maximum": 3},
                            "health_runability": {"type": "integer", "minimum": 0, "maximum": 3},
                            "health_history": {"type": "integer", "minimum": 0, "maximum": 3},
                            "debt_architecture": {"type": "integer", "minimum": 0, "maximum": 3},
                            "debt_code_quality": {"type": "integer", "minimum": 0, "maximum": 3},
                            "debt_testing": {"type": "integer", "minimum": 0, "maximum": 3},
                            "debt_infrastructure": {"type": "integer", "minimum": 0, "maximum": 3},
                            "debt_security": {"type": "integer", "minimum": 0, "maximum": 3},
                            "profile_id": {"type": "string", "default": "eu_standard"}
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="check_compliance",
                    description="Check if scores meet contract requirements",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "contract_id": {
                                "type": "string",
                                "description": "Contract profile ID"
                            },
                            "documentation": {"type": "integer", "minimum": 0, "maximum": 3},
                            "security": {"type": "integer", "minimum": 0, "maximum": 3},
                            "testing": {"type": "integer", "minimum": 0, "maximum": 3},
                        },
                        "required": ["contract_id"]
                    }
                ),
                Tool(
                    name="generate_document",
                    description="Generate a document from template with variables",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "template_id": {
                                "type": "string",
                                "enum": ["act_of_work_uk", "act_of_work_en", "invoice", "analysis_report"],
                                "description": "Document template to use"
                            },
                            "variables": {
                                "type": "object",
                                "description": "Variables to fill in the template"
                            }
                        },
                        "required": ["template_id", "variables"]
                    }
                ),
                Tool(
                    name="get_template_variables",
                    description="Get list of variables required by a document template",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "template_id": {
                                "type": "string",
                                "enum": ["act_of_work_uk", "act_of_work_en", "invoice", "analysis_report"]
                            }
                        },
                        "required": ["template_id"]
                    }
                ),
                Tool(
                    name="calculate_scores",
                    description="Calculate overall scores and readiness percentage",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "health_documentation": {"type": "integer", "minimum": 0, "maximum": 3},
                            "health_structure": {"type": "integer", "minimum": 0, "maximum": 3},
                            "health_runability": {"type": "integer", "minimum": 0, "maximum": 3},
                            "health_history": {"type": "integer", "minimum": 0, "maximum": 3},
                            "debt_architecture": {"type": "integer", "minimum": 0, "maximum": 3},
                            "debt_code_quality": {"type": "integer", "minimum": 0, "maximum": 3},
                            "debt_testing": {"type": "integer", "minimum": 0, "maximum": 3},
                            "debt_infrastructure": {"type": "integer", "minimum": 0, "maximum": 3},
                            "debt_security": {"type": "integer", "minimum": 0, "maximum": 3},
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_scoring_rubric",
                    description="Get detailed scoring rubric for evaluation metrics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "metric": {
                                "type": "string",
                                "enum": ["documentation", "structure", "runability", "history",
                                        "architecture", "code_quality", "testing", "infrastructure", "security"],
                                "description": "Metric to get rubric for (optional, returns all if not specified)"
                            }
                        },
                        "required": []
                    }
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent]:
            try:
                if name == "list_profiles":
                    return await self._list_profiles()
                elif name == "list_contracts":
                    return await self._list_contracts()
                elif name == "estimate_cost":
                    return await self._estimate_cost(arguments)
                elif name == "check_readiness":
                    return await self._check_readiness(arguments)
                elif name == "check_compliance":
                    return await self._check_compliance(arguments)
                elif name == "generate_document":
                    return await self._generate_document(arguments)
                elif name == "get_template_variables":
                    return await self._get_template_variables(arguments)
                elif name == "calculate_scores":
                    return await self._calculate_scores(arguments)
                elif name == "get_scoring_rubric":
                    return await self._get_scoring_rubric(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _list_profiles(self) -> List[TextContent]:
        result = "# Available Evaluation Profiles\n\n"
        for profile_id, profile in PROFILES.items():
            result += f"## {profile['name']} (`{profile_id}`)\n"
            result += f"- **Region:** {profile['region']}\n"
            result += f"- **Currency:** {profile['currency']}\n"
            result += f"- **Hourly Rates:**\n"
            result += f"  - Junior: {profile['hourly']['junior']}/hr\n"
            result += f"  - Middle: {profile['hourly']['middle']}/hr\n"
            result += f"  - Senior: {profile['hourly']['senior']}/hr\n"
            result += f"- **Min Requirements:**\n"
            result += f"  - Repo Health: {profile['requirements']['repo_health']}/12\n"
            result += f"  - Tech Debt: {profile['requirements']['tech_debt']}/15\n"
            result += f"  - Readiness: {profile['requirements']['readiness']}%\n\n"
        return [TextContent(type="text", text=result)]

    async def _list_contracts(self) -> List[TextContent]:
        result = "# Available Contract Profiles\n\n"
        for contract_id, contract in CONTRACTS.items():
            result += f"## {contract['name']} (`{contract_id}`)\n"
            if 'compliance' in contract:
                result += f"- **Compliance:** {', '.join(contract['compliance'])}\n"
            if contract.get('requirements'):
                result += "- **Requirements:**\n"
                for req in contract['requirements']:
                    blocking = " (BLOCKING)" if req.get('blocking') else ""
                    result += f"  - {req['metric']}: min {req['min']}/3{blocking}\n"
            result += "\n"
        return [TextContent(type="text", text=result)]

    async def _estimate_cost(self, args: dict) -> List[TextContent]:
        complexity = args.get('complexity', 'M')
        profile_id = args.get('profile_id', 'eu_standard')
        multiplier = args.get('tech_debt_multiplier', 1.0)

        profile = PROFILES.get(profile_id)
        if not profile:
            return [TextContent(type="text", text=f"Unknown profile: {profile_id}")]

        # Base hours by complexity
        hours = {
            'S': {'min': 80, 'typical': 120, 'max': 160},
            'M': {'min': 160, 'typical': 320, 'max': 500},
            'L': {'min': 500, 'typical': 800, 'max': 1200},
        }

        h = hours.get(complexity, hours['M'])
        rate = profile['hourly']['middle']
        currency = profile['currency']

        min_h = int(h['min'] * multiplier)
        typ_h = int(h['typical'] * multiplier)
        max_h = int(h['max'] * multiplier)

        result = f"""# Cost Estimate

**Profile:** {profile['name']}
**Complexity:** {complexity}
**Tech Debt Multiplier:** {multiplier}x

## Hours
- Minimum: {min_h} hours
- Typical: {typ_h} hours
- Maximum: {max_h} hours

## Cost ({currency}, middle rate {rate}/hr)
- Minimum: {min_h * rate:,.0f} {currency}
- Typical: {typ_h * rate:,.0f} {currency}
- Maximum: {max_h * rate:,.0f} {currency}

## Breakdown by Phase (typical)
| Phase | Hours | Cost |
|-------|-------|------|
| Analysis | {int(typ_h * 0.1)} | {int(typ_h * 0.1 * rate):,} {currency} |
| Design | {int(typ_h * 0.15)} | {int(typ_h * 0.15 * rate):,} {currency} |
| Development | {int(typ_h * 0.45)} | {int(typ_h * 0.45 * rate):,} {currency} |
| QA/Testing | {int(typ_h * 0.2)} | {int(typ_h * 0.2 * rate):,} {currency} |
| Documentation | {int(typ_h * 0.1)} | {int(typ_h * 0.1 * rate):,} {currency} |
"""
        return [TextContent(type="text", text=result)]

    async def _check_readiness(self, args: dict) -> List[TextContent]:
        profile_id = args.get('profile_id', 'eu_standard')
        profile = PROFILES.get(profile_id, PROFILES['eu_standard'])

        health = RepoHealthScore(
            documentation=args.get('health_documentation', 0),
            structure=args.get('health_structure', 0),
            runability=args.get('health_runability', 0),
            history=args.get('health_history', 0),
        )

        debt = TechDebtScore(
            architecture=args.get('debt_architecture', 0),
            code_quality=args.get('debt_code_quality', 0),
            testing=args.get('debt_testing', 0),
            infrastructure=args.get('debt_infrastructure', 0),
            security=args.get('debt_security', 0),
        )

        # Calculate readiness
        health_pct = (health.total / health.max_total) * 100
        debt_pct = (debt.total / debt.max_total) * 100
        readiness = (health_pct + debt_pct) / 2

        # Check against profile requirements
        req = profile['requirements']
        health_ok = health.total >= req['repo_health']
        debt_ok = debt.total >= req['tech_debt']
        readiness_ok = readiness >= req['readiness']

        # Determine level
        if readiness >= 95:
            level = "EXEMPLARY"
            emoji = "🌟"
        elif readiness >= 80:
            level = "READY"
            emoji = "✅"
        elif readiness >= 60:
            level = "ALMOST READY"
            emoji = "🔶"
        elif readiness >= 40:
            level = "NEEDS WORK"
            emoji = "⚠️"
        else:
            level = "NOT READY"
            emoji = "❌"

        result = f"""# Readiness Assessment

{emoji} **Level: {level}**
**Readiness Score:** {readiness:.1f}%
**Profile:** {profile['name']}

## Repository Health: {health.total}/{health.max_total} {'✅' if health_ok else '❌'}
| Metric | Score | Status |
|--------|-------|--------|
| Documentation | {health.documentation}/3 | {'✓' if health.documentation >= 2 else '✗'} |
| Structure | {health.structure}/3 | {'✓' if health.structure >= 2 else '✗'} |
| Runability | {health.runability}/3 | {'✓' if health.runability >= 2 else '✗'} |
| History | {health.history}/3 | {'✓' if health.history >= 2 else '✗'} |

## Technical Debt: {debt.total}/{debt.max_total} {'✅' if debt_ok else '❌'}
| Metric | Score | Status |
|--------|-------|--------|
| Architecture | {debt.architecture}/3 | {'✓' if debt.architecture >= 2 else '✗'} |
| Code Quality | {debt.code_quality}/3 | {'✓' if debt.code_quality >= 2 else '✗'} |
| Testing | {debt.testing}/3 | {'✓' if debt.testing >= 2 else '✗'} |
| Infrastructure | {debt.infrastructure}/3 | {'✓' if debt.infrastructure >= 2 else '✗'} |
| Security | {debt.security}/3 | {'✓' if debt.security >= 2 else '✗'} |

## Profile Requirements Check
- Health ≥ {req['repo_health']}/12: {'✅ PASS' if health_ok else '❌ FAIL'}
- Debt ≥ {req['tech_debt']}/15: {'✅ PASS' if debt_ok else '❌ FAIL'}
- Readiness ≥ {req['readiness']}%: {'✅ PASS' if readiness_ok else '❌ FAIL'}

## Verdict
**{'READY FOR EVALUATION' if (health_ok and debt_ok and readiness_ok) else 'NOT READY - Address issues above'}**
"""
        return [TextContent(type="text", text=result)]

    async def _check_compliance(self, args: dict) -> List[TextContent]:
        contract_id = args.get('contract_id', 'standard')
        contract = CONTRACTS.get(contract_id)

        if not contract:
            return [TextContent(type="text", text=f"Unknown contract: {contract_id}")]

        scores = {
            'documentation': args.get('documentation', 0),
            'security': args.get('security', 0),
            'testing': args.get('testing', 0),
        }

        if not contract.get('requirements'):
            return [TextContent(type="text", text=f"# {contract['name']}\n\n✅ No specific requirements - COMPLIANT")]

        passed = []
        failed = []
        blocking_failed = []

        for req in contract['requirements']:
            metric = req['metric']
            min_score = req['min']
            actual = scores.get(metric, 0)
            blocking = req.get('blocking', False)

            if actual >= min_score:
                passed.append(f"- ✅ {metric}: {actual}/{min_score}")
            else:
                msg = f"- ❌ {metric}: {actual}/{min_score} (gap: {min_score - actual})"
                if blocking:
                    blocking_failed.append(msg + " **BLOCKING**")
                else:
                    failed.append(msg)

        compliance_pct = len(passed) / len(contract['requirements']) * 100 if contract['requirements'] else 100

        if blocking_failed:
            verdict = "NON_COMPLIANT"
            emoji = "❌"
        elif failed:
            verdict = "PARTIAL"
            emoji = "⚠️"
        else:
            verdict = "COMPLIANT"
            emoji = "✅"

        result = f"""# Contract Compliance Check

**Contract:** {contract['name']}
**Compliance Standards:** {', '.join(contract.get('compliance', ['None']))}

## Result: {emoji} {verdict}
**Compliance:** {compliance_pct:.0f}%

## Requirements
### Passed ({len(passed)})
{chr(10).join(passed) if passed else 'None'}

### Failed ({len(failed) + len(blocking_failed)})
{chr(10).join(blocking_failed) if blocking_failed else ''}
{chr(10).join(failed) if failed else ''}
{'' if (failed or blocking_failed) else 'None'}
"""
        return [TextContent(type="text", text=result)]

    async def _generate_document(self, args: dict) -> List[TextContent]:
        template_id = args.get('template_id')
        variables = args.get('variables', {})

        template = DOCUMENT_TEMPLATES.get(template_id)
        if not template:
            return [TextContent(type="text", text=f"Unknown template: {template_id}")]

        # Add default date if not provided
        if 'date' not in variables:
            variables['date'] = datetime.now().strftime('%Y-%m-%d')

        result = self.template_engine.process(template, variables)
        return [TextContent(type="text", text=result)]

    async def _get_template_variables(self, args: dict) -> List[TextContent]:
        template_id = args.get('template_id')

        template = DOCUMENT_TEMPLATES.get(template_id)
        if not template:
            return [TextContent(type="text", text=f"Unknown template: {template_id}")]

        variables = self.template_engine.extract_variables(template)

        result = f"# Template Variables: {template_id}\n\n"
        result += "## Required Variables\n"
        for var in variables:
            result += f"- `{var}`\n"

        return [TextContent(type="text", text=result)]

    async def _calculate_scores(self, args: dict) -> List[TextContent]:
        health = RepoHealthScore(
            documentation=args.get('health_documentation', 0),
            structure=args.get('health_structure', 0),
            runability=args.get('health_runability', 0),
            history=args.get('health_history', 0),
        )

        debt = TechDebtScore(
            architecture=args.get('debt_architecture', 0),
            code_quality=args.get('debt_code_quality', 0),
            testing=args.get('debt_testing', 0),
            infrastructure=args.get('debt_infrastructure', 0),
            security=args.get('debt_security', 0),
        )

        health_pct = (health.total / health.max_total) * 100
        debt_pct = (debt.total / debt.max_total) * 100
        overall = (health_pct + debt_pct) / 2

        result = f"""# Score Summary

## Repository Health: {health.total}/{health.max_total} ({health_pct:.0f}%)
## Technical Debt: {debt.total}/{debt.max_total} ({debt_pct:.0f}%)
## Overall Readiness: {overall:.0f}%

## Classification
- **Health Level:** {'Good' if health_pct >= 75 else 'Moderate' if health_pct >= 50 else 'Needs Improvement'}
- **Debt Level:** {'Low Debt' if debt_pct >= 75 else 'Moderate Debt' if debt_pct >= 50 else 'High Debt'}
"""
        return [TextContent(type="text", text=result)]

    async def _get_scoring_rubric(self, args: dict) -> List[TextContent]:
        metric = args.get('metric')

        rubrics = {
            'documentation': """## Documentation (0-3)
- **0**: No README, no docs
- **1**: Basic README exists
- **2**: Good README + some API docs
- **3**: Comprehensive docs, tutorials, examples""",

            'structure': """## Structure (0-3)
- **0**: Chaotic, no clear organization
- **1**: Basic structure, some organization
- **2**: Good structure, clear separation
- **3**: Excellent structure, follows best practices""",

            'runability': """## Runability (0-3)
- **0**: Cannot run, missing dependencies
- **1**: Can run with manual setup
- **2**: Docker or scripts provided
- **3**: One-command setup, CI/CD ready""",

            'history': """## Commit History (0-3)
- **0**: Few commits, no history
- **1**: Some commits, unclear messages
- **2**: Regular commits, decent messages
- **3**: Clean history, semantic commits, tags""",

            'architecture': """## Architecture (0-3)
- **0**: Monolithic, tightly coupled
- **1**: Some separation exists
- **2**: Good modularity, clear boundaries
- **3**: Clean architecture, loosely coupled""",

            'code_quality': """## Code Quality (0-3)
- **0**: No standards, high complexity
- **1**: Some standards, moderate issues
- **2**: Good standards, low complexity
- **3**: Excellent quality, clean code""",

            'testing': """## Testing (0-3)
- **0**: No tests
- **1**: Some unit tests exist
- **2**: Good coverage, some integration tests
- **3**: Comprehensive tests, CI integration""",

            'infrastructure': """## Infrastructure (0-3)
- **0**: No deployment config
- **1**: Basic deployment docs
- **2**: Docker/K8s configs, some monitoring
- **3**: Full IaC, monitoring, logging""",

            'security': """## Security (0-3)
- **0**: Known vulnerabilities, no scans
- **1**: Some security measures
- **2**: No critical issues, updated deps
- **3**: Security-first, audited, compliant""",
        }

        if metric and metric in rubrics:
            return [TextContent(type="text", text=f"# Scoring Rubric\n\n{rubrics[metric]}")]

        result = "# Complete Scoring Rubric\n\n"
        result += "## Repository Health (0-12 total)\n\n"
        for m in ['documentation', 'structure', 'runability', 'history']:
            result += rubrics[m] + "\n\n"

        result += "## Technical Debt (0-15 total)\n\n"
        for m in ['architecture', 'code_quality', 'testing', 'infrastructure', 'security']:
            result += rubrics[m] + "\n\n"

        return [TextContent(type="text", text=result)]

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, self.server.create_initialization_options())


async def main():
    server = RepoAuditorMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
