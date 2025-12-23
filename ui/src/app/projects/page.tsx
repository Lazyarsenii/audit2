'use client';

import { useState, useEffect } from 'react';
import { API_BASE, apiFetch } from '@/lib/api';

type ProjectStatus = 'active' | 'completed' | 'on_hold' | 'archived';
type ActivityType = 'project_created' | 'project_updated' | 'status_changed' | 'analysis_started' | 'analysis_completed' | 'analysis_failed' | 'document_generated' | 'comment_added';

interface Activity {
  id: string;
  activity_type: ActivityType;
  title: string;
  description: string | null;
  created_at: string;
}

interface Project {
  id: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  client_name: string | null;
  contract_number: string | null;
  repository_urls: string[];
  budget_hours: number | null;
  hourly_rate: number | null;
  currency: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  analysis_count: number;
  completed_analysis_count: number;
  recent_activities: Activity[];
}

interface NewProject {
  name: string;
  description: string;
  client_name: string;
  contract_number: string;
  repository_urls: string[];
  budget_hours: number | null;
  hourly_rate: number | null;
  currency: string;
  tags: string[];
}

const statusConfig: Record<ProjectStatus, { label: string; color: string; bg: string }> = {
  active: { label: 'Active', color: 'text-green-700', bg: 'bg-green-100' },
  completed: { label: 'Completed', color: 'text-blue-700', bg: 'bg-blue-100' },
  on_hold: { label: 'On Hold', color: 'text-yellow-700', bg: 'bg-yellow-100' },
  archived: { label: 'Archived', color: 'text-slate-500', bg: 'bg-slate-100' },
};

const activityIcons: Record<ActivityType, string> = {
  project_created: '🆕',
  project_updated: '✏️',
  status_changed: '🔄',
  analysis_started: '🚀',
  analysis_completed: '✅',
  analysis_failed: '❌',
  document_generated: '📄',
  comment_added: '💬',
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<ProjectStatus | 'all'>('all');
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  
  const [newProject, setNewProject] = useState<NewProject>({
    name: '',
    description: '',
    client_name: '',
    contract_number: '',
    repository_urls: [],
    budget_hours: null,
    hourly_rate: null,
    currency: 'USD',
    tags: [],
  });
  const [repoInput, setRepoInput] = useState('');
  const [tagInput, setTagInput] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchProjects();
  }, [filter, search]);

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filter !== 'all') params.append('status', filter);
      if (search) params.append('search', search);
      
      const res = await apiFetch(`${API_BASE}/api/projects?${params}`);
      if (res.ok) {
        const data = await res.json();
        setProjects(data.projects);
      }
    } catch (err) {
      console.error('Failed to fetch projects:', err);
    }
    setLoading(false);
  };

  const handleCreateProject = async () => {
    if (!newProject.name.trim()) return;
    setSaving(true);

    try {
      const res = await apiFetch(`${API_BASE}/api/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newProject),
      });

      if (res.ok) {
        setShowModal(false);
        setNewProject({
          name: '',
          description: '',
          client_name: '',
          contract_number: '',
          repository_urls: [],
          budget_hours: null,
          hourly_rate: null,
          currency: 'USD',
          tags: [],
        });
        fetchProjects();
      }
    } catch (err) {
      console.error('Failed to create project:', err);
    }
    setSaving(false);
  };

  const handleStatusChange = async (projectId: string, newStatus: ProjectStatus) => {
    try {
      const res = await apiFetch(`${API_BASE}/api/projects/${projectId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });

      if (res.ok) {
        fetchProjects();
      }
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const addRepo = () => {
    if (repoInput.trim() && !newProject.repository_urls.includes(repoInput.trim())) {
      setNewProject({
        ...newProject,
        repository_urls: [...newProject.repository_urls, repoInput.trim()],
      });
      setRepoInput('');
    }
  };

  const removeRepo = (url: string) => {
    setNewProject({
      ...newProject,
      repository_urls: newProject.repository_urls.filter((r) => r !== url),
    });
  };

  const addTag = () => {
    if (tagInput.trim() && !newProject.tags.includes(tagInput.trim())) {
      setNewProject({
        ...newProject,
        tags: [...newProject.tags, tagInput.trim()],
      });
      setTagInput('');
    }
  };

  const removeTag = (tag: string) => {
    setNewProject({
      ...newProject,
      tags: newProject.tags.filter((t) => t !== tag),
    });
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getProgress = (project: Project) => {
    if (project.analysis_count === 0) return 0;
    return Math.round((project.completed_analysis_count / project.analysis_count) * 100);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Projects</h1>
          <p className="text-slate-600">Manage your audit projects and track progress.</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium"
        >
          + New Project
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-6">
        <div className="flex gap-2">
          {(['all', 'active', 'on_hold', 'completed', 'archived'] as const).map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                filter === status
                  ? 'bg-primary-100 text-primary-700'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {status === 'all' ? 'All' : statusConfig[status].label}
            </button>
          ))}
        </div>
        <input
          type="text"
          placeholder="Search projects..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm w-64"
        />
      </div>

      {/* Project Cards */}
      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading projects...</div>
      ) : projects.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-slate-200">
          <div className="text-slate-400 text-5xl mb-4">📁</div>
          <h3 className="text-lg font-medium text-slate-900 mb-1">No projects yet</h3>
          <p className="text-slate-500 mb-4">Create your first project to get started</p>
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Create Project
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <div
              key={project.id}
              className="bg-white rounded-lg border border-slate-200 hover:border-slate-300 hover:shadow-md transition-all"
            >
              {/* Card Header */}
              <div className="p-4 border-b border-slate-100">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold text-slate-900 truncate flex-1">
                    {project.name}
                  </h3>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      statusConfig[project.status].bg
                    } ${statusConfig[project.status].color}`}
                  >
                    {statusConfig[project.status].label}
                  </span>
                </div>
                {project.description && (
                  <p className="text-sm text-slate-500 line-clamp-2">{project.description}</p>
                )}
                {project.client_name && (
                  <p className="text-xs text-slate-400 mt-1">Client: {project.client_name}</p>
                )}
              </div>

              {/* Stats */}
              <div className="p-4 border-b border-slate-100">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-500">Analyses</span>
                  <span className="font-medium">
                    {project.completed_analysis_count} / {project.analysis_count}
                  </span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2">
                  <div
                    className="bg-primary-500 h-2 rounded-full transition-all"
                    style={{ width: `${getProgress(project)}%` }}
                  />
                </div>
                {project.budget_hours && (
                  <div className="flex justify-between text-xs text-slate-400 mt-2">
                    <span>Budget: {project.budget_hours}h</span>
                    {project.hourly_rate && (
                      <span>
                        {project.hourly_rate} {project.currency}/h
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Recent Activity */}
              <div className="p-4 border-b border-slate-100">
                <h4 className="text-xs font-medium text-slate-500 uppercase mb-2">
                  Recent Activity
                </h4>
                {project.recent_activities.length === 0 ? (
                  <p className="text-xs text-slate-400">No activity yet</p>
                ) : (
                  <div className="space-y-1.5">
                    {project.recent_activities.slice(0, 3).map((activity) => (
                      <div key={activity.id} className="flex items-start gap-2 text-xs">
                        <span>{activityIcons[activity.activity_type]}</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-slate-600 truncate">{activity.title}</p>
                          <p className="text-slate-400">{formatDate(activity.created_at)}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Tags & Actions */}
              <div className="p-4">
                {project.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {project.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-xs"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
                <div className="flex gap-2">
                  <a
                    href={`/new?project=${project.id}`}
                    className="flex-1 py-1.5 text-center text-sm bg-primary-50 text-primary-600 rounded hover:bg-primary-100"
                  >
                    New Analysis
                  </a>
                  <select
                    value={project.status}
                    onChange={(e) =>
                      handleStatusChange(project.id, e.target.value as ProjectStatus)
                    }
                    className="px-2 py-1.5 text-sm border border-slate-200 rounded"
                  >
                    <option value="active">Active</option>
                    <option value="on_hold">On Hold</option>
                    <option value="completed">Completed</option>
                    <option value="archived">Archived</option>
                  </select>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-200">
              <h2 className="text-xl font-semibold text-slate-900">Create New Project</h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Project Name *
                </label>
                <input
                  type="text"
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  placeholder="e.g., Client Website Audit"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Description
                </label>
                <textarea
                  value={newProject.description}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                  rows={2}
                  placeholder="Brief project description..."
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Client Name
                  </label>
                  <input
                    type="text"
                    value={newProject.client_name}
                    onChange={(e) => setNewProject({ ...newProject, client_name: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Contract #
                  </label>
                  <input
                    type="text"
                    value={newProject.contract_number}
                    onChange={(e) =>
                      setNewProject({ ...newProject, contract_number: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Repository URLs
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={repoInput}
                    onChange={(e) => setRepoInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addRepo())}
                    placeholder="https://github.com/org/repo"
                    className="flex-1 px-3 py-2 border border-slate-300 rounded-lg"
                  />
                  <button
                    onClick={addRepo}
                    type="button"
                    className="px-3 py-2 bg-slate-100 rounded-lg hover:bg-slate-200"
                  >
                    Add
                  </button>
                </div>
                {newProject.repository_urls.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {newProject.repository_urls.map((url) => (
                      <div
                        key={url}
                        className="flex items-center justify-between px-2 py-1 bg-slate-50 rounded text-sm"
                      >
                        <span className="truncate">{url}</span>
                        <button
                          onClick={() => removeRepo(url)}
                          className="text-red-500 hover:text-red-700 ml-2"
                        >
                          x
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Budget (hours)
                  </label>
                  <input
                    type="number"
                    value={newProject.budget_hours || ''}
                    onChange={(e) =>
                      setNewProject({
                        ...newProject,
                        budget_hours: e.target.value ? parseInt(e.target.value) : null,
                      })
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Hourly Rate
                  </label>
                  <input
                    type="number"
                    value={newProject.hourly_rate || ''}
                    onChange={(e) =>
                      setNewProject({
                        ...newProject,
                        hourly_rate: e.target.value ? parseInt(e.target.value) : null,
                      })
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Currency</label>
                  <select
                    value={newProject.currency}
                    onChange={(e) => setNewProject({ ...newProject, currency: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                  >
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                    <option value="UAH">UAH</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Tags</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                    placeholder="Add tag..."
                    className="flex-1 px-3 py-2 border border-slate-300 rounded-lg"
                  />
                  <button
                    onClick={addTag}
                    type="button"
                    className="px-3 py-2 bg-slate-100 rounded-lg hover:bg-slate-200"
                  >
                    Add
                  </button>
                </div>
                {newProject.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {newProject.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-1 bg-primary-100 text-primary-700 rounded text-sm flex items-center gap-1"
                      >
                        {tag}
                        <button
                          onClick={() => removeTag(tag)}
                          className="text-primary-500 hover:text-primary-700"
                        >
                          x
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="p-6 border-t border-slate-200 flex justify-end gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-slate-600 hover:text-slate-900"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateProject}
                disabled={!newProject.name.trim() || saving}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {saving ? 'Creating...' : 'Create Project'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
