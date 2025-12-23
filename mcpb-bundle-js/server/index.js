#!/usr/bin/env node
/**
 * Quick Auditor MCP Server
 * Uses the deployed API for repository analysis and work report generation.
 */

const https = require('https');
const readline = require('readline');

const API_BASE = 'audit2-production.up.railway.app';

class QuickAuditorMCP {
  constructor() {
    this.tools = [
      {
        name: 'analyze_repository',
        description: 'Analyze a GitHub repository and get metrics, health score, tech debt, and cost estimation',
        inputSchema: {
          type: 'object',
          properties: {
            repo_url: {
              type: 'string',
              description: 'GitHub repository URL (e.g., https://github.com/user/repo)'
            }
          },
          required: ['repo_url']
        }
      },
      {
        name: 'generate_work_report_url',
        description: 'Get a URL to generate work report PDF for a repository',
        inputSchema: {
          type: 'object',
          properties: {
            repo_url: {
              type: 'string',
              description: 'GitHub repository URL'
            },
            start_date: {
              type: 'string',
              description: 'Report start date (YYYY-MM-DD)'
            },
            end_date: {
              type: 'string',
              description: 'Report end date (YYYY-MM-DD)'
            },
            consultant_name: {
              type: 'string',
              description: 'Name of the consultant/developer'
            },
            organization: {
              type: 'string',
              description: 'Organization name'
            },
            worker_type: {
              type: 'string',
              description: "Worker type: 'worker' (max 8h/day) or 'team' (no daily limit)",
              enum: ['worker', 'team']
            }
          },
          required: ['repo_url']
        }
      },
      {
        name: 'get_api_help',
        description: 'Get help information about the Work Report API',
        inputSchema: {
          type: 'object',
          properties: {},
          required: []
        }
      }
    ];
  }

  async handleRequest(request) {
    const { method, params, id } = request;

    try {
      switch (method) {
        case 'initialize':
          return this.initResponse(id);
        case 'tools/list':
          return this.toolsListResponse(id);
        case 'tools/call':
          return await this.handleToolCall(id, params);
        default:
          return this.errorResponse(id, -32601, `Method not found: ${method}`);
      }
    } catch (e) {
      return this.errorResponse(id, -32603, e.message);
    }
  }

  initResponse(id) {
    return {
      jsonrpc: '2.0',
      id,
      result: {
        protocolVersion: '2024-11-05',
        capabilities: { tools: {} },
        serverInfo: { name: 'quick-auditor', version: '1.0.0' }
      }
    };
  }

  toolsListResponse(id) {
    return {
      jsonrpc: '2.0',
      id,
      result: { tools: this.tools }
    };
  }

  async handleToolCall(id, params) {
    const { name, arguments: args } = params;

    try {
      let result;
      switch (name) {
        case 'analyze_repository':
          result = await this.analyzeRepository(args.repo_url);
          break;
        case 'generate_work_report_url':
          result = await this.generateWorkReportUrl(args);
          break;
        case 'get_api_help':
          result = await this.getApiHelp();
          break;
        default:
          return this.errorResponse(id, -32602, `Unknown tool: ${name}`);
      }

      return {
        jsonrpc: '2.0',
        id,
        result: {
          content: [{
            type: 'text',
            text: JSON.stringify(result, null, 2)
          }]
        }
      };
    } catch (e) {
      return this.errorResponse(id, -32603, `Tool failed: ${e.message}`);
    }
  }

  errorResponse(id, code, message) {
    return {
      jsonrpc: '2.0',
      id,
      error: { code, message }
    };
  }

  // Tool implementations
  async analyzeRepository(repoUrl) {
    const data = JSON.stringify({ repo_url: repoUrl });

    return new Promise((resolve, reject) => {
      const req = https.request({
        hostname: API_BASE,
        path: '/api/quick-audit',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(data)
        },
        timeout: 120000
      }, (res) => {
        let body = '';
        res.on('data', chunk => body += chunk);
        res.on('end', () => {
          try {
            const result = JSON.parse(body);
            resolve({
              repository: result.repo_name || 'Unknown',
              metrics: {
                total_loc: result.static_metrics?.total_loc || 0,
                files_count: result.static_metrics?.files_count || 0,
                languages: Object.keys(result.static_metrics?.languages || {}),
                commits: result.git_metrics?.total_commits || 0,
                contributors: result.git_metrics?.authors_count || 0
              },
              scores: {
                repo_health: `${result.repo_health?.total || 0}/12`,
                tech_debt: `${result.tech_debt?.total || 0}/15`
              },
              cost_estimate: result.cost_estimate || {},
              work_report_hours: Math.round((result.cost_estimate?.hours_typical || 0) / 10)
            });
          } catch (e) {
            reject(new Error(`Failed to parse response: ${e.message}`));
          }
        });
      });

      req.on('error', reject);
      req.on('timeout', () => reject(new Error('Request timeout')));
      req.write(data);
      req.end();
    });
  }

  async generateWorkReportUrl(args) {
    const params = new URLSearchParams();
    params.append('repo_url', args.repo_url);
    if (args.start_date) params.append('start_date', args.start_date);
    if (args.end_date) params.append('end_date', args.end_date);
    if (args.consultant_name) params.append('consultant_name', args.consultant_name);
    if (args.organization) params.append('organization', args.organization);
    if (args.worker_type) params.append('worker_type', args.worker_type);

    return {
      message: 'Use this curl command to generate and download the work report PDF:',
      curl_command: `curl -X POST "https://${API_BASE}/api/work-report" -H "Content-Type: application/json" -d '${JSON.stringify({
        repo_url: args.repo_url,
        start_date: args.start_date,
        end_date: args.end_date,
        consultant_name: args.consultant_name,
        organization: args.organization,
        worker_type: args.worker_type || 'worker'
      })}' -o work_report.pdf`,
      web_ui: `https://${API_BASE}/quick`,
      note: 'Or use the Web UI to generate the report interactively'
    };
  }

  async getApiHelp() {
    return new Promise((resolve, reject) => {
      https.get(`https://${API_BASE}/api/work-report/help`, (res) => {
        let body = '';
        res.on('data', chunk => body += chunk);
        res.on('end', () => {
          try {
            resolve(JSON.parse(body));
          } catch (e) {
            resolve({
              web_ui: `https://${API_BASE}/quick`,
              api_docs: `https://${API_BASE}/docs`
            });
          }
        });
      }).on('error', () => {
        resolve({
          web_ui: `https://${API_BASE}/quick`,
          api_docs: `https://${API_BASE}/docs`
        });
      });
    });
  }
}

// Main MCP server loop
async function main() {
  const server = new QuickAuditorMCP();

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
  });

  rl.on('line', async (line) => {
    if (!line.trim()) return;

    try {
      const request = JSON.parse(line);
      const response = await server.handleRequest(request);
      console.log(JSON.stringify(response));
    } catch (e) {
      // Ignore parse errors
    }
  });
}

main().catch(console.error);
