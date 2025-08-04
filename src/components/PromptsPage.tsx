import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import APIService from '../services/api';
import Dropdown from './Dropdown';
import { DropdownOption, PromptTemplate } from '../types';

const promptTypeOptions: DropdownOption[] = [
  { value: 'main', label: 'Main Prompts', active: true },
  { value: 'use-case', label: 'Use Case Prompts' },
  { value: 'role-based', label: 'Role Based Prompts' },
  { value: 'discipline-based', label: 'Discipline Based Prompts' },
];

const statusOptions: DropdownOption[] = [
  { value: 'active', label: 'Active', active: true },
  { value: 'inactive', label: 'Inactive' },
];

const PromptsPage: React.FC = () => {
  const navigate = useNavigate();
  const [apiService] = useState(() => new APIService());
  const [selectedPromptType, setSelectedPromptType] = useState('main');
  const [prompts, setPrompts] = useState<PromptTemplate[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptTemplate | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  // Create form state
  const [createForm, setCreateForm] = useState({
    name: '',
    version: 'v1',
    status: 'active',
    description: '',
    content: '',
    type: 'main',
  });

  const loadPrompts = useCallback(async () => {
    setLoading(true);
    try {
      const result = await apiService.getPrompts(selectedPromptType);
      if (result.success) {
        setPrompts(result.data || []);
      } else {
        setError(result.error || 'Failed to load prompts');
      }
    } catch (error) {
      setError('Failed to load prompts');
    } finally {
      setLoading(false);
    }
  }, [selectedPromptType, apiService]);

  useEffect(() => {
    loadPrompts();
  }, [loadPrompts]);

  const handlePromptSelect = async (promptId: string) => {
    try {
      const result = await apiService.getPrompt(promptId);
      if (result.success) {
        setSelectedPrompt(result.data);
      } else {
        setError(result.error || 'Failed to load prompt');
      }
    } catch (error) {
      setError('Failed to load prompt');
    }
  };

  const handleCreatePrompt = async () => {
    try {
      const result = await apiService.createPrompt(createForm);
      if (result.success) {
        setShowCreateForm(false);
        setCreateForm({
          name: '',
          version: 'v1',
          status: 'active',
          description: '',
          content: '',
          type: 'main',
        });
        loadPrompts();
      } else {
        setError(result.error || 'Failed to create prompt');
      }
    } catch (error) {
      setError('Failed to create prompt');
    }
  };

  const handleUpdatePrompt = async () => {
    if (!selectedPrompt) return;

    try {
      const result = await apiService.updatePrompt(selectedPrompt.id, selectedPrompt);
      if (result.success) {
        loadPrompts();
      } else {
        setError(result.error || 'Failed to update prompt');
      }
    } catch (error) {
      setError('Failed to update prompt');
    }
  };

  const handleDeletePrompt = async (promptId: string) => {
    if (!window.confirm('Are you sure you want to delete this prompt?')) return;

    try {
      const result = await apiService.deletePrompt(promptId);
      if (result.success) {
        if (selectedPrompt?.id === promptId) {
          setSelectedPrompt(null);
        }
        loadPrompts();
      } else {
        setError(result.error || 'Failed to delete prompt');
      }
    } catch (error) {
      setError('Failed to delete prompt');
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-title">System Prompts</div>
          <div className="sidebar-subtitle">Manage your prompt templates</div>
        </div>

        <div className="sidebar-content">
          <div className="config-section">
            <div className="config-section-title">Prompt Type</div>
            <div className="config-group">
              <p className="config-label">Select Prompt Type</p>
              <Dropdown
                options={promptTypeOptions}
                value={selectedPromptType}
                onChange={setSelectedPromptType}
              />
            </div>
          </div>

          {/* Create New Prompt Form */}
          {showCreateForm && (
            <div className="create-form">
              <div className="config-section">
                <div className="config-section-title">Prompt Details</div>
                <div className="config-group">
                  <p className="config-label">Select Prompt Type</p>
                  <Dropdown
                    options={promptTypeOptions}
                    value={createForm.type}
                    onChange={(value) => setCreateForm({ ...createForm, type: value })}
                  />
                </div>

                <div className="config-group">
                  <label className="config-label" htmlFor="newPromptName">
                    Name
                  </label>
                  <input
                    type="text"
                    className="config-input"
                    id="newPromptName"
                    placeholder="Enter prompt name"
                    value={createForm.name}
                    onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                  />
                </div>

                <div className="config-row">
                  <div className="config-group">
                    <label className="config-label" htmlFor="newPromptVersion">
                      Version
                    </label>
                    <input
                      type="text"
                      className="config-input"
                      id="newPromptVersion"
                      placeholder="v1"
                      value={createForm.version}
                      onChange={(e) => setCreateForm({ ...createForm, version: e.target.value })}
                    />
                  </div>

                  <div className="config-group">
                    <p className="config-label">Status</p>
                    <Dropdown
                      options={statusOptions}
                      value={createForm.status}
                      onChange={(value) => setCreateForm({ ...createForm, status: value })}
                    />
                  </div>
                </div>

                <div className="config-group">
                  <label className="config-label" htmlFor="newPromptDescription">
                    Description
                  </label>
                  <input
                    type="text"
                    className="config-input"
                    id="newPromptDescription"
                    placeholder="Brief Description"
                    value={createForm.description}
                    onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Scrollable section */}
          <div className="scrollable-content">
            <div className="prompts-list">
              {loading ? (
                <div className="loading">Loading prompts...</div>
              ) : prompts.length === 0 ? (
                <div className="text-center py-8 text-gray-500">No prompts found</div>
              ) : (
                prompts.map((prompt) => (
                  <div
                    key={prompt.id}
                    className={`p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors ${
                      selectedPrompt?.id === prompt.id ? 'bg-primary-50 border-primary-200' : ''
                    }`}
                    onClick={() => handlePromptSelect(prompt.id)}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-gray-900">{prompt.name}</h4>
                        <p className="text-sm text-gray-600">{prompt.description}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-gray-500">v{prompt.version}</span>
                          <span
                            className={`text-xs px-2 py-1 rounded ${
                              prompt.status === 'active'
                                ? 'bg-green-100 text-green-700'
                                : 'bg-gray-100 text-gray-700'
                            }`}
                          >
                            {prompt.status}
                          </span>
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeletePrompt(prompt.id);
                        }}
                        className="text-red-500 hover:text-red-700 text-sm"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="sidebar-footer">
          <div className="fixed-buttons">
            <button
              className="btn btn-primary"
              onClick={() => setShowCreateForm(!showCreateForm)}
            >
              + New Prompt
            </button>
            <button className="btn btn-secondary" onClick={() => navigate('/')}>
              Back
            </button>
            {showCreateForm && (
              <>
                <button className="btn btn-primary" onClick={handleCreatePrompt}>
                  Create
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => setShowCreateForm(false)}
                >
                  Cancel
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="prompts-main">
        <div className="editor-container">
          {selectedPrompt ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-gray-900">{selectedPrompt.name}</h2>
                <button
                  className="btn btn-primary"
                  onClick={handleUpdatePrompt}
                >
                  Save Changes
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="config-label">Content</label>
                  <textarea
                    className="config-input min-h-[400px]"
                    value={selectedPrompt.content}
                    onChange={(e) => setSelectedPrompt({ ...selectedPrompt, content: e.target.value })}
                    placeholder="Enter prompt content..."
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <h3>Select a prompt to edit</h3>
              <p>Choose a prompt from the sidebar to view and edit its content</p>
            </div>
          )}
        </div>
      </div>

      {/* Error Messages */}
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
    </div>
  );
};

export default PromptsPage; 