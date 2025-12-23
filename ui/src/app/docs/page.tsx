'use client';

import { useState } from 'react';

type TabType = 'overview' | 'methodology' | 'scoring' | 'guide';

export default function DocsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  const tabs: { id: TabType; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'methodology', label: 'Methodology' },
    { id: 'scoring', label: 'Scoring System' },
    { id: 'guide', label: 'User Guide' },
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Documentation</h1>
        <p className="text-slate-600">
          Methodology, scoring approach, and usage instructions.
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200 mb-8">
        <nav className="flex gap-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-3 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Overview */}
      {activeTab === 'overview' && (
        <div className="prose prose-slate max-w-none">
          <h2>What is Repo Auditor?</h2>
          <p>
            Repo Auditor is a professional tool for automated repository analysis and evaluation.
            It provides objective assessment of code quality, technical debt, and development costs.
          </p>

          <h3>Key Features</h3>
          <ul>
            <li><strong>Automated Analysis</strong> - Static code analysis, structure evaluation, dependency scanning</li>
            <li><strong>Objective Scoring</strong> - Quantified metrics based on industry standards</li>
            <li><strong>Cost Estimation</strong> - Effort and cost projections using historical data</li>
            <li><strong>Document Generation</strong> - Reports, acts of work, invoices</li>
            <li><strong>Project Management</strong> - Track multiple projects and their progress</li>
          </ul>

          <h3>Use Cases</h3>
          <ul>
            <li>Due diligence for software acquisitions</li>
            <li>Project handover assessments</li>
            <li>Technical debt quantification</li>
            <li>Development cost estimation</li>
            <li>Vendor evaluation and auditing</li>
          </ul>
        </div>
      )}

      {/* Methodology */}
      {activeTab === 'methodology' && (
        <div className="prose prose-slate max-w-none">
          <h2>Evaluation Methodology</h2>
          <p>
            Our methodology is based on established software engineering practices and
            industry standards for code quality assessment.
          </p>

          <h3>Analysis Pipeline</h3>
          <ol>
            <li>
              <strong>Repository Fetch</strong> - Clone or access the repository
            </li>
            <li>
              <strong>Structure Analysis</strong> - Evaluate project organization, file structure, configuration
            </li>
            <li>
              <strong>Static Analysis</strong> - Code metrics, complexity, duplication
            </li>
            <li>
              <strong>Dependency Scan</strong> - Security vulnerabilities, outdated packages
            </li>
            <li>
              <strong>Scoring</strong> - Apply scoring rubrics to collected metrics
            </li>
            <li>
              <strong>Cost Estimation</strong> - Calculate effort using complexity-based models
            </li>
          </ol>

          <h3>References and Standards</h3>
          <div className="not-prose">
            <div className="space-y-4">
              {[
                {
                  title: 'COCOMO II',
                  desc: 'Constructive Cost Model for software effort estimation',
                  url: 'https://en.wikipedia.org/wiki/COCOMO',
                },
                {
                  title: 'Cyclomatic Complexity',
                  desc: 'McCabe complexity metric for code maintainability',
                  url: 'https://en.wikipedia.org/wiki/Cyclomatic_complexity',
                },
                {
                  title: 'OWASP Dependency-Check',
                  desc: 'Security vulnerability detection in dependencies',
                  url: 'https://owasp.org/www-project-dependency-check/',
                },
                {
                  title: 'Semgrep',
                  desc: 'Static analysis for security and code quality',
                  url: 'https://semgrep.dev/',
                },
                {
                  title: 'ISO/IEC 25010',
                  desc: 'Software quality model standard',
                  url: 'https://iso25000.com/index.php/en/iso-25000-standards/iso-25010',
                },
              ].map((ref) => (
                <a
                  key={ref.title}
                  href={ref.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-4 bg-white border border-slate-200 rounded-lg hover:border-primary-300 transition-colors"
                >
                  <div className="font-medium text-slate-900">{ref.title}</div>
                  <div className="text-sm text-slate-500">{ref.desc}</div>
                  <div className="text-xs text-primary-600 mt-1">{ref.url}</div>
                </a>
              ))}
            </div>
          </div>

          <h3 className="mt-8">Objectivity Principles</h3>
          <ul>
            <li>All metrics are automatically collected - no manual bias</li>
            <li>Scoring rubrics are transparent and documented</li>
            <li>Results are reproducible across runs</li>
            <li>Historical data calibrates estimates</li>
          </ul>
        </div>
      )}

      {/* Scoring System */}
      {activeTab === 'scoring' && (
        <div className="prose prose-slate max-w-none">
          <h2>Scoring System</h2>
          <p>
            The scoring system evaluates repositories across two main dimensions:
            Repository Health and Technical Debt.
          </p>

          <h3>Repository Health (0-12 points)</h3>
          <p>Measures operational readiness and maintainability.</p>
          
          <div className="not-prose">
            <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Metric</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Max</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Criteria</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  <tr>
                    <td className="px-4 py-3 text-sm font-medium">Documentation</td>
                    <td className="px-4 py-3 text-sm">3</td>
                    <td className="px-4 py-3 text-sm text-slate-600">README, API docs, inline comments</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-sm font-medium">Structure</td>
                    <td className="px-4 py-3 text-sm">3</td>
                    <td className="px-4 py-3 text-sm text-slate-600">Project organization, naming, config</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-sm font-medium">Runability</td>
                    <td className="px-4 py-3 text-sm">3</td>
                    <td className="px-4 py-3 text-sm text-slate-600">Build scripts, Docker, CI/CD</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-sm font-medium">Commit History</td>
                    <td className="px-4 py-3 text-sm">3</td>
                    <td className="px-4 py-3 text-sm text-slate-600">Quality, frequency, messages</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <h3 className="mt-8">Technical Debt (0-15 points)</h3>
          <p>Higher score = less debt = better quality.</p>
          
          <div className="not-prose">
            <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Metric</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Max</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Criteria</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  <tr>
                    <td className="px-4 py-3 text-sm font-medium">Architecture</td>
                    <td className="px-4 py-3 text-sm">3</td>
                    <td className="px-4 py-3 text-sm text-slate-600">Modularity, separation of concerns</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-sm font-medium">Code Quality</td>
                    <td className="px-4 py-3 text-sm">3</td>
                    <td className="px-4 py-3 text-sm text-slate-600">Complexity, duplication, style</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-sm font-medium">Testing</td>
                    <td className="px-4 py-3 text-sm">3</td>
                    <td className="px-4 py-3 text-sm text-slate-600">Coverage, test quality, CI tests</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-sm font-medium">Infrastructure</td>
                    <td className="px-4 py-3 text-sm">3</td>
                    <td className="px-4 py-3 text-sm text-slate-600">Deployment, monitoring, logging</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-sm font-medium">Security</td>
                    <td className="px-4 py-3 text-sm">3</td>
                    <td className="px-4 py-3 text-sm text-slate-600">Vulnerabilities, dependencies</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <h3 className="mt-8">Complexity Classes</h3>
          <div className="not-prose grid grid-cols-3 gap-4">
            {[
              { size: 'S', label: 'Small', hours: '< 160h', desc: 'Simple projects, single dev' },
              { size: 'M', label: 'Medium', hours: '160-500h', desc: 'Standard projects, small team' },
              { size: 'L', label: 'Large', hours: '> 500h', desc: 'Complex projects, larger team' },
            ].map((c) => (
              <div key={c.size} className="bg-white border border-slate-200 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-primary-600">{c.size}</div>
                <div className="font-medium text-slate-900">{c.label}</div>
                <div className="text-sm text-slate-500">{c.hours}</div>
                <div className="text-xs text-slate-400 mt-1">{c.desc}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* User Guide */}
      {activeTab === 'guide' && (
        <div className="prose prose-slate max-w-none">
          <h2>User Guide</h2>

          <h3>Quick Start</h3>
          <ol>
            <li>Click <strong>Start Analysis</strong> or go to <strong>Workflow</strong></li>
            <li>Enter repository URL (GitHub, GitLab, or local path)</li>
            <li>Select evaluation profile (EU, UA, US rates)</li>
            <li>Optionally select contract requirements</li>
            <li>Choose output documents</li>
            <li>Click <strong>Start Analysis</strong></li>
          </ol>

          <h3>Workflow Steps</h3>
          <div className="not-prose space-y-4">
            {[
              {
                step: 1,
                title: 'Setup',
                desc: 'Configure repository URL, branch, evaluation profile, and document selection.',
              },
              {
                step: 2,
                title: 'Analyze',
                desc: 'Automated analysis runs. Takes 1-5 minutes depending on repository size.',
              },
              {
                step: 3,
                title: 'Review',
                desc: 'Review scores, metrics, and cost estimates. Verify results meet requirements.',
              },
              {
                step: 4,
                title: 'Documents',
                desc: 'Generate selected documents: reports, acts, invoices.',
              },
              {
                step: 5,
                title: 'Complete',
                desc: 'Download generated documents. Start new analysis or return to dashboard.',
              },
            ].map((item) => (
              <div key={item.step} className="flex gap-4 bg-white border border-slate-200 rounded-lg p-4">
                <div className="w-8 h-8 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center font-bold flex-shrink-0">
                  {item.step}
                </div>
                <div>
                  <div className="font-medium text-slate-900">{item.title}</div>
                  <div className="text-sm text-slate-600">{item.desc}</div>
                </div>
              </div>
            ))}
          </div>

          <h3 className="mt-8">Evaluation Profiles</h3>
          <p>Profiles define hourly rates and minimum requirements:</p>
          <ul>
            <li><strong>EU Standard</strong> - European R&D rates (EUR 35-85/hr)</li>
            <li><strong>Ukraine R&D</strong> - Ukrainian market rates (USD 15-50/hr)</li>
            <li><strong>EU Enterprise</strong> - Higher rates for enterprise projects</li>
            <li><strong>US Standard</strong> - US market rates</li>
            <li><strong>Startup/MVP</strong> - Reduced requirements for early-stage</li>
          </ul>

          <h3>Tips</h3>
          <ul>
            <li>Use <strong>Projects</strong> to organize related repositories</li>
            <li>Check <strong>Docs</strong> to understand scoring criteria</li>
            <li>Review results before generating documents</li>
            <li>Configure <strong>Settings</strong> for custom profiles</li>
          </ul>
        </div>
      )}
    </div>
  );
}
