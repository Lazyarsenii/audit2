'use client';

import { useState, useEffect } from 'react';
import { API_BASE, apiFetch, setApiKey, clearApiKey, hasApiKey } from '@/lib/api';

interface Profile {
  name: string;
  description: string;
  config: Record<string, any>;
}

import { getMethodologies, setMethodologyEnabled, CostMethodology } from '@/lib/profiles';

type TabType = 'profiles' | 'methodologies' | 'integrations' | 'contracts' | 'templates' | 'system';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('profiles');
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<Profile | null>(null);
  const [profileJson, setProfileJson] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [contractFile, setContractFile] = useState<File | null>(null);
  const [contractType, setContractType] = useState('service');
  const [uploading, setUploading] = useState(false);

  const [systemSettings, setSystemSettings] = useState({
    debug: false,
    rateLimit: 60,
    apiKeyRequired: false,
  });

  // API Key authentication
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [apiKeySet, setApiKeySet] = useState(false);

  // Integration tokens
  const [githubToken, setGithubToken] = useState('');
  const [gitlabToken, setGitlabToken] = useState('');
  const [showGithubToken, setShowGithubToken] = useState(false);
  const [showGitlabToken, setShowGitlabToken] = useState(false);

  // Cost methodologies
  const [methodologies, setMethodologiesState] = useState<CostMethodology[]>([]);

  useEffect(() => {
    fetchProfiles();
    fetchSystemSettings();
    // Load saved tokens from localStorage
    const savedGithubToken = localStorage.getItem('github_token');
    const savedGitlabToken = localStorage.getItem('gitlab_token');
    if (savedGithubToken) setGithubToken(savedGithubToken);
    if (savedGitlabToken) setGitlabToken(savedGitlabToken);

    // Check API key status
    setApiKeySet(hasApiKey());

    // Handle hash navigation for integrations tab
    if (window.location.hash === '#integrations') {
      setActiveTab('integrations');
    }

    // Load methodologies
    setMethodologiesState(getMethodologies());
  }, []);

  const fetchProfiles = async () => {
    try {
      const res = await apiFetch(`${API_BASE}/api/settings/profiles`);
      if (res.ok) {
        const data = await res.json();
        setProfiles(data.profiles || []);
      }
    } catch (err) {
      console.error('Failed to fetch profiles:', err);
    }
  };

  const fetchSystemSettings = async () => {
    try {
      const res = await apiFetch(`${API_BASE}/api/settings/system`);
      if (res.ok) {
        const data = await res.json();
        setSystemSettings(data);
      }
    } catch (err) {
      console.error('Failed to fetch system settings:', err);
    }
  };

  const handleProfileSelect = (profile: Profile) => {
    setSelectedProfile(profile);
    setProfileJson(JSON.stringify(profile.config, null, 2));
  };

  const handleProfileSave = async () => {
    if (!selectedProfile) return;
    setLoading(true);
    setMessage(null);

    try {
      const config = JSON.parse(profileJson);
      const res = await apiFetch(`${API_BASE}/api/settings/profiles/${selectedProfile.name}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...selectedProfile, config }),
      });

      if (res.ok) {
        setMessage({ type: 'success', text: 'Profile saved successfully' });
        fetchProfiles();
      } else {
        const err = await res.json();
        setMessage({ type: 'error', text: err.detail || 'Failed to save profile' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Invalid JSON format' });
    }

    setLoading(false);
  };

  const handleContractUpload = async () => {
    if (!contractFile) return;
    setUploading(true);
    setMessage(null);

    const formData = new FormData();
    formData.append('file', contractFile);
    formData.append('contract_type', contractType);

    try {
      const res = await apiFetch(`${API_BASE}/api/settings/upload-contract`, {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        const termsCount = data.extracted_terms ? data.extracted_terms.length : 0;
        setMessage({
          type: 'success',
          text: `Contract uploaded! Extracted ${termsCount} terms`,
        });
        setContractFile(null);
      } else {
        const err = await res.json();
        setMessage({ type: 'error', text: err.detail || 'Upload failed' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to upload contract' });
    }

    setUploading(false);
  };

  const handleSystemSave = async () => {
    setLoading(true);
    setMessage(null);

    try {
      const res = await apiFetch(`${API_BASE}/api/settings/system`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(systemSettings),
      });

      if (res.ok) {
        setMessage({ type: 'success', text: 'System settings saved' });
      } else {
        const err = await res.json();
        setMessage({ type: 'error', text: err.detail || 'Failed to save' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to save system settings' });
    }

    setLoading(false);
  };

  const handleSaveApiKey = () => {
    if (apiKeyInput) {
      setApiKey(apiKeyInput);
      setApiKeySet(true);
      setApiKeyInput('');
      setMessage({ type: 'success', text: 'API key saved' });
    }
  };

  const handleClearApiKey = () => {
    clearApiKey();
    setApiKeySet(false);
    setMessage({ type: 'success', text: 'API key removed' });
  };

  const handleSaveGithubToken = () => {
    if (githubToken) {
      localStorage.setItem('github_token', githubToken);
      setMessage({ type: 'success', text: 'GitHub token saved locally' });
    } else {
      localStorage.removeItem('github_token');
      setMessage({ type: 'success', text: 'GitHub token removed' });
    }
  };

  const handleSaveGitlabToken = () => {
    if (gitlabToken) {
      localStorage.setItem('gitlab_token', gitlabToken);
      setMessage({ type: 'success', text: 'GitLab token saved locally' });
    } else {
      localStorage.removeItem('gitlab_token');
      setMessage({ type: 'success', text: 'GitLab token removed' });
    }
  };

  const handleMethodologyToggle = (id: string, enabled: boolean) => {
    setMethodologyEnabled(id, enabled);
    setMethodologiesState(getMethodologies());
    const methodName = methodologies.find(m => m.id === id)?.name || id;
    setMessage({
      type: 'success',
      text: `${methodName} ${enabled ? 'enabled' : 'disabled'}`
    });
  };

  const tabs: { id: TabType; label: string }[] = [
    { id: 'profiles', label: 'Profiles' },
    { id: 'methodologies', label: 'Methodologies' },
    { id: 'integrations', label: 'Integrations' },
    { id: 'contracts', label: 'Upload Contract' },
    { id: 'templates', label: 'Templates' },
    { id: 'system', label: 'System' },
  ];

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Settings</h1>
        <p className="text-slate-600">
          Manage profiles, templates, contracts, and system configuration.
        </p>
      </div>

      <div className="border-b border-slate-200 mb-6">
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
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

      {message && (
        <div
          className={`mb-6 p-4 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-50 border border-green-200 text-green-700'
              : 'bg-red-50 border border-red-200 text-red-700'
          }`}
        >
          {message.text}
        </div>
      )}

      {activeTab === 'profiles' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg border border-slate-200 p-4">
            <h3 className="font-semibold text-slate-900 mb-4">Available Profiles</h3>
            <div className="space-y-2">
              {profiles.length === 0 ? (
                <p className="text-slate-500 text-sm">No profiles found</p>
              ) : (
                profiles.map((profile) => (
                  <button
                    key={profile.name}
                    onClick={() => handleProfileSelect(profile)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      selectedProfile && selectedProfile.name === profile.name
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className="font-medium">{profile.name}</div>
                    <div className="text-sm text-slate-500">{profile.description}</div>
                  </button>
                ))
              )}
            </div>
            <button
              onClick={() => {
                const newProfile: Profile = {
                  name: `profile_${Date.now()}`,
                  description: 'New profile',
                  config: {},
                };
                setSelectedProfile(newProfile);
                setProfileJson('{}');
              }}
              className="w-full mt-4 py-2 border-2 border-dashed border-slate-300 rounded-lg text-slate-500 hover:border-primary-400 hover:text-primary-600"
            >
              + New Profile
            </button>
          </div>

          <div className="lg:col-span-2 bg-white rounded-lg border border-slate-200 p-4">
            <h3 className="font-semibold text-slate-900 mb-4">
              {selectedProfile ? `Edit: ${selectedProfile.name}` : 'Select a Profile'}
            </h3>
            {selectedProfile ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
                  <input
                    type="text"
                    value={selectedProfile.name}
                    onChange={(e) =>
                      setSelectedProfile({ ...selectedProfile, name: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                  <input
                    type="text"
                    value={selectedProfile.description}
                    onChange={(e) =>
                      setSelectedProfile({ ...selectedProfile, description: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Configuration (JSON)</label>
                  <textarea
                    value={profileJson}
                    onChange={(e) => setProfileJson(e.target.value)}
                    rows={12}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono text-sm"
                  />
                </div>
                <button
                  onClick={handleProfileSave}
                  disabled={loading}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {loading ? 'Saving...' : 'Save Profile'}
                </button>
              </div>
            ) : (
              <div className="text-center text-slate-500 py-12">
                Select a profile to edit or create a new one
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'methodologies' && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-slate-200 p-6">
            <h3 className="font-semibold text-slate-900 mb-2">Cost Calculation Methodologies</h3>
            <p className="text-sm text-slate-600 mb-6">
              Enable or disable methodologies used for cost estimation. Enabled methodologies will be used to calculate project costs.
            </p>

            <div className="space-y-4">
              {methodologies.map((methodology) => (
                <div
                  key={methodology.id}
                  className={`p-4 rounded-lg border transition-colors ${
                    methodology.enabled
                      ? 'border-primary-200 bg-primary-50'
                      : 'border-slate-200 bg-slate-50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-slate-900">{methodology.name}</span>
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full ${
                            methodology.confidence === 'High'
                              ? 'bg-green-100 text-green-700'
                              : methodology.confidence === 'Medium'
                              ? 'bg-yellow-100 text-yellow-700'
                              : 'bg-gray-100 text-gray-700'
                          }`}
                        >
                          {methodology.confidence}
                        </span>
                      </div>
                      <p className="text-sm text-slate-600 mt-1">{methodology.description}</p>
                      <div className="flex gap-4 mt-2 text-xs text-slate-500">
                        <span>Formula: <code className="bg-slate-100 px-1 rounded">{methodology.formula}</code></span>
                        <span>Source: {methodology.source}</span>
                      </div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer ml-4">
                      <input
                        type="checkbox"
                        checked={methodology.enabled}
                        onChange={(e) => handleMethodologyToggle(methodology.id, e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-medium text-blue-900 mb-2">How Methodologies Work</h4>
            <p className="text-sm text-blue-800">
              Each methodology calculates cost based on different factors (lines of code, words, pages).
              Enabled methodologies are averaged to provide the final estimate. High confidence methodologies
              are based on industry standards (Gartner, IEEE, COCOMO).
            </p>
          </div>
        </div>
      )}

      {activeTab === 'integrations' && (
        <div className="space-y-6 max-w-2xl">
          {/* API Key Authentication */}
          <div className="bg-white rounded-lg border border-slate-200 p-6">
            <h3 className="font-semibold text-slate-900 mb-2">API Authentication</h3>
            <p className="text-sm text-slate-600 mb-6">
              Enter the API key to access protected endpoints. Get the key from your administrator.
            </p>

            <div className="space-y-4">
              {apiKeySet ? (
                <div className="flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-center gap-3">
                    <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-green-800 font-medium">API key is configured</span>
                  </div>
                  <button
                    onClick={handleClearApiKey}
                    className="px-3 py-1.5 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 rounded"
                  >
                    Remove
                  </button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <input
                      type={showApiKey ? 'text' : 'password'}
                      value={apiKeyInput}
                      onChange={(e) => setApiKeyInput(e.target.value)}
                      placeholder="ra_xxxxxxxxxxxxxxxxxxxx"
                      className="w-full px-4 py-2 pr-10 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    />
                    <button
                      type="button"
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    >
                      {showApiKey ? (
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                        </svg>
                      ) : (
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      )}
                    </button>
                  </div>
                  <button
                    onClick={handleSaveApiKey}
                    disabled={!apiKeyInput}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                  >
                    Save
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-lg border border-slate-200 p-6">
            <h3 className="font-semibold text-slate-900 mb-2">Git Provider Tokens</h3>
            <p className="text-sm text-slate-600 mb-6">
              Store access tokens to analyze private repositories. Tokens are saved locally in your browser.
            </p>

            {/* GitHub Token */}
            <div className="space-y-4 mb-8">
              <div className="flex items-center gap-3 mb-3">
                <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                </svg>
                <span className="font-medium text-slate-900">GitHub</span>
              </div>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <input
                    type={showGithubToken ? 'text' : 'password'}
                    value={githubToken}
                    onChange={(e) => setGithubToken(e.target.value)}
                    placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                    className="w-full px-4 py-2 pr-10 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowGithubToken(!showGithubToken)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showGithubToken ? (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>
                <button
                  onClick={handleSaveGithubToken}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                >
                  Save
                </button>
              </div>
              <p className="text-xs text-slate-500">
                Create a token at{' '}
                <a
                  href="https://github.com/settings/tokens"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-600 hover:underline"
                >
                  github.com/settings/tokens
                </a>
                {' '}with &quot;repo&quot; scope for private repositories.
              </p>
            </div>

            {/* GitLab Token */}
            <div className="space-y-4 pt-6 border-t border-slate-200">
              <div className="flex items-center gap-3 mb-3">
                <svg className="w-6 h-6 text-orange-600" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 01-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 014.82 2a.43.43 0 01.58 0 .42.42 0 01.11.18l2.44 7.49h8.1l2.44-7.51A.42.42 0 0118.6 2a.43.43 0 01.58 0 .42.42 0 01.11.18l2.44 7.51L23 13.45a.84.84 0 01-.35.94z"/>
                </svg>
                <span className="font-medium text-slate-900">GitLab</span>
              </div>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <input
                    type={showGitlabToken ? 'text' : 'password'}
                    value={gitlabToken}
                    onChange={(e) => setGitlabToken(e.target.value)}
                    placeholder="glpat-xxxxxxxxxxxxxxxxxxxx"
                    className="w-full px-4 py-2 pr-10 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowGitlabToken(!showGitlabToken)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showGitlabToken ? (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>
                <button
                  onClick={handleSaveGitlabToken}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                >
                  Save
                </button>
              </div>
              <p className="text-xs text-slate-500">
                Create a token at{' '}
                <a
                  href="https://gitlab.com/-/profile/personal_access_tokens"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-600 hover:underline"
                >
                  gitlab.com/-/profile/personal_access_tokens
                </a>
                {' '}with &quot;read_repository&quot; scope.
              </p>
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-medium text-blue-900 mb-2">Security Note</h4>
            <p className="text-sm text-blue-800">
              Tokens are stored only in your browser&apos;s localStorage and are never sent to our servers
              except when making direct requests to Git providers. For enhanced security, consider
              using tokens with minimal required permissions.
            </p>
          </div>
        </div>
      )}

      {activeTab === 'contracts' && (
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="font-semibold text-slate-900 mb-4">Upload Contract or Policy</h3>
          <p className="text-slate-600 mb-6">
            Upload contracts or financial policies to extract terms and integrate with analysis metrics.
          </p>

          <div className="space-y-4 max-w-xl">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Contract Type</label>
              <select
                value={contractType}
                onChange={(e) => setContractType(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
              >
                <option value="service">Service Agreement</option>
                <option value="nda">NDA</option>
                <option value="policy">Financial Policy</option>
                <option value="sla">SLA</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">File</label>
              <input
                type="file"
                accept=".pdf,.docx,.doc,.txt"
                onChange={(e) => setContractFile(e.target && e.target.files ? e.target.files[0] : null)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
              />
              <p className="text-xs text-slate-500 mt-1">Supported formats: PDF, DOCX, DOC, TXT</p>
            </div>

            <button
              onClick={handleContractUpload}
              disabled={!contractFile || uploading}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {uploading ? 'Uploading...' : 'Upload & Parse'}
            </button>
          </div>

          <div className="mt-8 pt-6 border-t border-slate-200">
            <h4 className="font-medium text-slate-900 mb-3">How it works</h4>
            <ul className="space-y-2 text-slate-600 text-sm">
              <li className="flex items-start gap-2">
                <span className="text-primary-500">1.</span>
                Upload your contract or policy document
              </li>
              <li className="flex items-start gap-2">
                <span className="text-primary-500">2.</span>
                System extracts key terms (rates, deadlines, deliverables)
              </li>
              <li className="flex items-start gap-2">
                <span className="text-primary-500">3.</span>
                Terms are stored and can be used in analysis metrics
              </li>
              <li className="flex items-start gap-2">
                <span className="text-primary-500">4.</span>
                Generate documents based on contract terms
              </li>
            </ul>
          </div>
        </div>
      )}

      {activeTab === 'templates' && (
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="font-semibold text-slate-900 mb-4">Document Templates</h3>
          <p className="text-slate-600 mb-6">
            Manage templates for generated documents (acts, invoices, contracts).
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { name: 'Act of Work (Ukrainian)', type: 'act', lang: 'uk' },
              { name: 'Act of Work (English)', type: 'act', lang: 'en' },
              { name: 'Invoice (Ukrainian)', type: 'invoice', lang: 'uk' },
              { name: 'Invoice (English)', type: 'invoice', lang: 'en' },
              { name: 'Service Agreement', type: 'contract', lang: 'en' },
            ].map((template) => (
              <div
                key={`${template.type}-${template.lang}`}
                className="p-4 border border-slate-200 rounded-lg hover:border-primary-300 transition-colors"
              >
                <div className="font-medium text-slate-900">{template.name}</div>
                <div className="text-sm text-slate-500 mt-1">
                  Type: {template.type} | Lang: {template.lang}
                </div>
                <button className="text-sm text-primary-600 hover:text-primary-700 mt-2">
                  Edit Template
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'system' && (
        <div className="bg-white rounded-lg border border-slate-200 p-6 max-w-xl">
          <h3 className="font-semibold text-slate-900 mb-4">System Settings</h3>

          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium text-slate-900">Debug Mode</div>
                <div className="text-sm text-slate-500">Enable detailed logging and API docs</div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={systemSettings.debug}
                  onChange={(e) =>
                    setSystemSettings({ ...systemSettings, debug: e.target.checked })
                  }
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[\'\'] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              </label>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium text-slate-900">Require API Key</div>
                <div className="text-sm text-slate-500">Protect API with authentication</div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={systemSettings.apiKeyRequired}
                  onChange={(e) =>
                    setSystemSettings({ ...systemSettings, apiKeyRequired: e.target.checked })
                  }
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[\'\'] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              </label>
            </div>

            <div>
              <label className="block font-medium text-slate-900 mb-1">Rate Limit (requests/min)</label>
              <input
                type="number"
                value={systemSettings.rateLimit}
                onChange={(e) =>
                  setSystemSettings({ ...systemSettings, rateLimit: parseInt(e.target.value) || 60 })
                }
                className="w-32 px-3 py-2 border border-slate-300 rounded-lg"
              />
            </div>

            <button
              onClick={handleSystemSave}
              disabled={loading}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {loading ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
