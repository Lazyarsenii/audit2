'use client';

import { useState, useEffect } from 'react';
import { API_BASE, apiFetch } from '@/lib/api';

interface Providers {
  ollama: boolean;
  anthropic: boolean;
  openai: boolean;
  google: boolean;
}

export default function LLMPage() {
  const [providers, setProviders] = useState<Providers | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string>('');
  const [error, setError] = useState<string>('');

  // Form states
  const [activeTab, setActiveTab] = useState<'readme' | 'code' | 'tz' | 'query'>('readme');
  const [readmeContent, setReadmeContent] = useState('# My Project\n\nA sample project.\n\n## Installation\n\n```bash\nnpm install\n```');
  const [codeContent, setCodeContent] = useState('def hello():\n    print("Hello World")');
  const [codeLanguage, setCodeLanguage] = useState('python');
  const [queryPrompt, setQueryPrompt] = useState('');

  // TZ form
  const [tzForm, setTzForm] = useState({
    project_name: 'Test Project',
    repo_health: 5,
    tech_debt: 4,
    readiness: 50,
    issues: 'Missing tests, No CI/CD, Outdated dependencies',
    project_type: 'R&D',
    required_repo_health: 8,
    required_tech_debt: 8,
    required_readiness: 75,
  });

  useEffect(() => {
    fetchProviders();
  }, []);

  const fetchProviders = async () => {
    try {
      const res = await apiFetch(`${API_BASE}/api/llm/providers`);
      const data = await res.json();
      setProviders(data);
    } catch (err) {
      setError('Failed to fetch providers');
    }
  };

  const analyzeReadme = async () => {
    setLoading(true);
    setError('');
    setResult('');
    try {
      const res = await apiFetch(`${API_BASE}/api/llm/analyze/readme`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: readmeContent }),
      });
      const data = await res.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (err) {
      setError('Failed to analyze README');
    }
    setLoading(false);
  };

  const analyzeCode = async () => {
    setLoading(true);
    setError('');
    setResult('');
    try {
      const res = await apiFetch(`${API_BASE}/api/llm/analyze/code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: codeContent,
          language: codeLanguage,
          filename: `test.${codeLanguage === 'python' ? 'py' : codeLanguage}`,
        }),
      });
      const data = await res.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (err) {
      setError('Failed to analyze code');
    }
    setLoading(false);
  };

  const generateTZ = async () => {
    setLoading(true);
    setError('');
    setResult('');
    try {
      const res = await apiFetch(`${API_BASE}/api/llm/generate/tz`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tzForm),
      });
      const data = await res.json();
      setResult(data.tz || JSON.stringify(data, null, 2));
    } catch (err) {
      setError('Failed to generate TZ');
    }
    setLoading(false);
  };

  const sendQuery = async () => {
    if (!queryPrompt.trim()) return;
    setLoading(true);
    setError('');
    setResult('');
    try {
      const res = await apiFetch(`${API_BASE}/api/llm/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: queryPrompt,
          task_type: 'simple_analysis',
        }),
      });
      const data = await res.json();
      setResult(data.response || JSON.stringify(data, null, 2));
    } catch (err) {
      setError('Failed to send query');
    }
    setLoading(false);
  };

  const ProviderStatus = ({ name, available }: { name: string; available: boolean }) => (
    <div className={`px-3 py-1 rounded-full text-sm ${available ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'}`}>
      {name}: {available ? 'Active' : 'Inactive'}
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">LLM Testing</h1>
        <p className="text-gray-600 mb-6">Test LLM integration for repository analysis</p>

        {/* Provider Status */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <h2 className="font-semibold mb-3">Provider Status</h2>
          <div className="flex gap-3 flex-wrap">
            {providers ? (
              <>
                <ProviderStatus name="Ollama" available={providers.ollama} />
                <ProviderStatus name="Anthropic" available={providers.anthropic} />
                <ProviderStatus name="OpenAI" available={providers.openai} />
                <ProviderStatus name="Google" available={providers.google} />
              </>
            ) : (
              <span className="text-gray-500">Loading...</span>
            )}
            <button
              onClick={fetchProviders}
              className="ml-auto text-blue-600 hover:text-blue-800 text-sm"
            >
              Refresh
            </button>
          </div>
          {providers && !Object.values(providers).some(v => v) && (
            <p className="text-amber-600 text-sm mt-2">
              No providers available. Start Ollama or add API keys to .env
            </p>
          )}
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow">
          <div className="border-b flex">
            {(['readme', 'code', 'tz', 'query'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-6 py-3 font-medium ${
                  activeTab === tab
                    ? 'border-b-2 border-blue-500 text-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab === 'readme' && 'README Analysis'}
                {tab === 'code' && 'Code Analysis'}
                {tab === 'tz' && 'Generate TZ'}
                {tab === 'query' && 'Simple Query'}
              </button>
            ))}
          </div>

          <div className="p-6">
            {/* README Analysis */}
            {activeTab === 'readme' && (
              <div>
                <label className="block font-medium mb-2">README Content</label>
                <textarea
                  value={readmeContent}
                  onChange={(e) => setReadmeContent(e.target.value)}
                  className="w-full h-48 p-3 border rounded-lg font-mono text-sm"
                  placeholder="Paste README content..."
                />
                <button
                  onClick={analyzeReadme}
                  disabled={loading}
                  className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? 'Analyzing...' : 'Analyze README'}
                </button>
              </div>
            )}

            {/* Code Analysis */}
            {activeTab === 'code' && (
              <div>
                <div className="flex gap-4 mb-4">
                  <div className="flex-1">
                    <label className="block font-medium mb-2">Language</label>
                    <select
                      value={codeLanguage}
                      onChange={(e) => setCodeLanguage(e.target.value)}
                      className="w-full p-2 border rounded-lg"
                    >
                      <option value="python">Python</option>
                      <option value="javascript">JavaScript</option>
                      <option value="typescript">TypeScript</option>
                      <option value="go">Go</option>
                      <option value="java">Java</option>
                    </select>
                  </div>
                </div>
                <label className="block font-medium mb-2">Code</label>
                <textarea
                  value={codeContent}
                  onChange={(e) => setCodeContent(e.target.value)}
                  className="w-full h-48 p-3 border rounded-lg font-mono text-sm"
                  placeholder="Paste code..."
                />
                <button
                  onClick={analyzeCode}
                  disabled={loading}
                  className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? 'Analyzing...' : 'Analyze Code'}
                </button>
              </div>
            )}

            {/* TZ Generation */}
            {activeTab === 'tz' && (
              <div>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block font-medium mb-2">Project Name</label>
                    <input
                      value={tzForm.project_name}
                      onChange={(e) => setTzForm({ ...tzForm, project_name: e.target.value })}
                      className="w-full p-2 border rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block font-medium mb-2">Project Type</label>
                    <select
                      value={tzForm.project_type}
                      onChange={(e) => setTzForm({ ...tzForm, project_type: e.target.value })}
                      className="w-full p-2 border rounded-lg"
                    >
                      <option value="MVP">MVP</option>
                      <option value="Startup">Startup</option>
                      <option value="R&D">R&D</option>
                      <option value="Production">Production</option>
                      <option value="Enterprise">Enterprise</option>
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div>
                    <label className="block font-medium mb-2">Current Health ({tzForm.repo_health}/12)</label>
                    <input
                      type="range"
                      min="0"
                      max="12"
                      value={tzForm.repo_health}
                      onChange={(e) => setTzForm({ ...tzForm, repo_health: parseInt(e.target.value) })}
                      className="w-full"
                    />
                  </div>
                  <div>
                    <label className="block font-medium mb-2">Current Tech Debt ({tzForm.tech_debt}/15)</label>
                    <input
                      type="range"
                      min="0"
                      max="15"
                      value={tzForm.tech_debt}
                      onChange={(e) => setTzForm({ ...tzForm, tech_debt: parseInt(e.target.value) })}
                      className="w-full"
                    />
                  </div>
                  <div>
                    <label className="block font-medium mb-2">Current Readiness ({tzForm.readiness}%)</label>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={tzForm.readiness}
                      onChange={(e) => setTzForm({ ...tzForm, readiness: parseInt(e.target.value) })}
                      className="w-full"
                    />
                  </div>
                </div>
                <div className="mb-4">
                  <label className="block font-medium mb-2">Known Issues</label>
                  <textarea
                    value={tzForm.issues}
                    onChange={(e) => setTzForm({ ...tzForm, issues: e.target.value })}
                    className="w-full h-24 p-3 border rounded-lg"
                    placeholder="List known issues..."
                  />
                </div>
                <button
                  onClick={generateTZ}
                  disabled={loading}
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  {loading ? 'Generating...' : 'Generate TZ'}
                </button>
              </div>
            )}

            {/* Simple Query */}
            {activeTab === 'query' && (
              <div>
                <label className="block font-medium mb-2">Query</label>
                <textarea
                  value={queryPrompt}
                  onChange={(e) => setQueryPrompt(e.target.value)}
                  className="w-full h-32 p-3 border rounded-lg"
                  placeholder="Ask anything..."
                />
                <button
                  onClick={sendQuery}
                  disabled={loading || !queryPrompt.trim()}
                  className="mt-4 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                >
                  {loading ? 'Sending...' : 'Send Query'}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="mt-4 bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-2">Result</h3>
            <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-auto max-h-96 text-sm">
              {result}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
