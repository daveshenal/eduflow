import React, { useState, useEffect, useCallback } from 'react';
import { useConfig } from '../contexts/ConfigContext';
import APIService from '../services/api';
import Dropdown from './Dropdown';
import { DropdownOption, PromptTemplate } from '../types';

const promptTypeOptions: DropdownOption[] = [
  { value: 'base_prompts', label: 'Main Prompts', active: true },
  { value: 'use_case_prompts', label: 'Use Case Prompts' },
  { value: 'role_prompts', label: 'Role Based Prompts' },
  { value: 'discipline_prompts', label: 'Discipline Based Prompts' },
];

const statusOptions: DropdownOption[] = [
  { value: 'active', label: 'Active', active: true },
  { value: 'inactive', label: 'Inactive' },
];

// Prompt Editor Component
const PromptEditor: React.FC<{ onBack: () => void }> = ({ onBack }) => {
  const { state } = useConfig();
  const [apiService] = useState(() => new APIService(state.backendUrl));
  const [selectedPromptType, setSelectedPromptType] = useState('base_prompts');
  const [prompts, setPrompts] = useState<PromptTemplate[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptTemplate | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Create form state
  const [createForm, setCreateForm] = useState({
    name: '',
    version: 'v1',
    status: 'active',
    description: '',
    content: '',
  });

  // Edit form state
  const [editForm, setEditForm] = useState({
    name: '',
    version: '',
    status: 'active',
    description: '',
    content: '',
  });

  const showMessage = (text: string, type: 'success' | 'error') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const loadPrompts = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${state.backendUrl}/${selectedPromptType}/`);
      if (!response.ok) throw new Error('Failed to load prompts');
      
      const data = await response.json();
      setPrompts(data || []);
    } catch (error) {
      setError('Database connection failed');
      setPrompts([]);
    } finally {
      setLoading(false);
    }
  }, [selectedPromptType, state.backendUrl]);

  useEffect(() => {
    apiService.setBaseUrl(state.backendUrl);
  }, [state.backendUrl, apiService]);

  useEffect(() => {
    loadPrompts();
    setSelectedPrompt(null);
  }, [loadPrompts]);

  const handlePromptTypeChange = (newType: string) => {
    setSelectedPromptType(newType);
    setSelectedPrompt(null);
  };

  const handlePromptSelect = (prompt: PromptTemplate) => {
    setSelectedPrompt(prompt);
    setEditForm({
      name: prompt.name,
      version: prompt.version,
      status: prompt.status,
      description: prompt.description || '',
      content: prompt.content || '',
    });
  };

  const handleCreatePrompt = async () => {
    if (!createForm.name.trim()) {
      showMessage('Please enter a prompt name', 'error');
      return;
    }

    try {
      const response = await fetch(`${state.backendUrl}/${selectedPromptType}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(createForm),
      });

      if (!response.ok) throw new Error('Failed to create prompt');

      const newPrompt = await response.json();
      setPrompts(prev => [newPrompt, ...prev]);
      setShowCreateForm(false);
      setCreateForm({
        name: '',
        version: 'v1',
        status: 'active',
        description: '',
        content: '',
      });
      handlePromptSelect(newPrompt);
      showMessage('Prompt created successfully!', 'success');
    } catch (error) {
      showMessage('Failed to create prompt', 'error');
    }
  };

  const handleUpdatePrompt = async () => {
    if (!selectedPrompt) return;

    try {
      const response = await fetch(`${state.backendUrl}/${selectedPromptType}/${selectedPrompt.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(editForm),
      });

      if (!response.ok) throw new Error('Failed to save prompt');

      const updatedPrompt = await response.json();
      setSelectedPrompt(updatedPrompt);
      
      // Update in prompts array
      setPrompts(prev => prev.map(p => p.id === updatedPrompt.id ? updatedPrompt : p));
      
      showMessage('Prompt saved successfully!', 'success');
    } catch (error) {
      showMessage('Failed to save prompt', 'error');
    }
  };

  const handleDeletePrompt = async () => {
    if (!selectedPrompt) return;
    
    if (!window.confirm(`Are you sure you want to delete "${selectedPrompt.name}"?`)) {
      return;
    }

    try {
      const response = await fetch(`${state.backendUrl}/${selectedPromptType}/${selectedPrompt.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Failed to delete prompt');

      setPrompts(prev => prev.filter(p => p.id !== selectedPrompt.id));
      setSelectedPrompt(null);
      showMessage('Prompt deleted successfully!', 'success');
    } catch (error) {
      showMessage('Failed to delete prompt', 'error');
    }
  };

  const copyToClipboard = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      showMessage('Copied to clipboard!', 'success');
    } catch (error) {
      showMessage('Failed to copy to clipboard', 'error');
    }
  };

  const handleShowCreateForm = () => {
    setShowCreateForm(true);
    setSelectedPrompt(null);
    setCreateForm({
      name: '',
      version: 'v1',
      status: 'active',
      description: '',
      content: '',
    });
  };

  const handleCancelCreate = () => {
    setShowCreateForm(false);
    setCreateForm({
      name: '',
      version: 'v1',
      status: 'active',
      description: '',
      content: '',
    });
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
          {!showCreateForm && (
            <div className="config-section">
              <div className="config-section-title">Prompt Type</div>
              <div className="config-group">
                <p className="config-label">Select Prompt Type</p>
                <Dropdown
                  options={promptTypeOptions}
                  value={selectedPromptType}
                  onChange={handlePromptTypeChange}
                />
              </div>
            </div>
          )}

          {/* Create New Prompt Form */}
          {showCreateForm && (
            <div className="config-section">
              <div className="config-section-title">Prompt Details</div>
              
              <div className="config-group">
                <p className="config-label">Select Prompt Type</p>
                <Dropdown
                  options={promptTypeOptions}
                  value={selectedPromptType}
                  onChange={setSelectedPromptType}
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

              <div className="config-row" style={{ display: 'flex', gap: '1rem' }}>
                <div className="config-group" style={{ flex: 1 }}>
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

                <div className="config-group" style={{ flex: 1 }}>
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
          )}

          {/* Scrollable section */}
          {!showCreateForm && (
            <div className="scrollable-content">
              <div className="prompts-list">
                {loading ? (
                  <div className="loading">Loading prompts...</div>
                ) : error ? (
                  <div className="error">{error}</div>
                ) : prompts.length === 0 ? (
                  <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
                    No prompts found
                  </div>
                ) : (
                  prompts.map((prompt) => (
                    <div
                      key={prompt.id}
                      className={`prompt-item ${selectedPrompt?.id === prompt.id ? 'active' : ''}`}
                      onClick={() => handlePromptSelect(prompt)}
                      style={{
                        padding: '12px',
                        border: '1px solid #e5e7eb',
                        borderColor: selectedPrompt?.id === prompt.id ? '#f96559' : '#e5e7eb',
                        borderRadius: '8px',
                        marginBottom: '8px',
                        cursor: 'pointer',
                        backgroundColor: 'white',
                      }}
                    >
                      <div className="prompt-item-name" style={{ fontWeight: '500', marginBottom: '4px' }}>
                        {prompt.name}
                      </div>
                      <div className="prompt-item-version" style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>
                        Version: {prompt.version}
                      </div>
                      <div className="prompt-item-desc" style={{ fontSize: '14px', color: '#4b5563', marginBottom: '8px' }}>
                        {prompt.description || 'No description'}
                      </div>
                      <span 
                        className={`prompt-item-status status-${prompt.status}`}
                        style={{
                          fontSize: '12px',
                          padding: '2px 8px',
                          borderRadius: '12px',
                          backgroundColor: prompt.status === 'active' ? '#d1fae5' : '#f3f4f6',
                          color: prompt.status === 'active' ? '#065f46' : '#4b5563',
                        }}
                      >
                        {prompt.status}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        <div className="sidebar-footer">
          <div className="fixed-buttons">
            {!showCreateForm ? (
              <>
                <button className="btn btn-primary" onClick={handleShowCreateForm}>
                  Add New
                </button>
                <button className="btn btn-secondary" onClick={onBack}>
                  Back
                </button>
              </>
            ) : (
              <>
                <button className="btn btn-primary" onClick={handleCreatePrompt}>
                  Create
                </button>
                <button className="btn btn-secondary" onClick={handleCancelCreate}>
                  Cancel
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="chat-container">
        {selectedPrompt ? (
          <>
            <div className="chat-header">
              <div className="chat-title">{selectedPrompt.name}</div>
    
            </div>

            <div className="editor-container" style={{ padding: '20px' }}>
              <div className="form-row" style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '20px' }}>
                <div className="form-group" style={{ maxWidth: '20%' }}>
                  <label htmlFor="editPromptName" className="config-label">Name</label>
                  <input
                    type="text"
                    className="config-input"
                    id="editPromptName"
                    value={editForm.name}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  />
                </div>
                <div className="form-group" style={{ maxWidth: '7.5%' }}>
                  <label htmlFor="editPromptVersion" className="config-label">Version</label>
                  <input
                    type="text"
                    className="config-input"
                    id="editPromptVersion"
                    value={editForm.version}
                    onChange={(e) => setEditForm({ ...editForm, version: e.target.value })}
                  />
                </div>
                <div className="form-group" style={{ maxWidth: '7.5%' }}>
                  <label className="config-label">Status</label>
                  <select
                    className="config-input"
                    value={editForm.status}
                    onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                  >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
                <div className="form-group" style={{ flex: 1 }}>
                  <label htmlFor="editPromptDescription" className="config-label">Description</label>
                  <input
                    type="text"
                    className="config-input"
                    id="editPromptDescription"
                    value={editForm.description}
                    onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  />
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end'}}>
                <button
                  className="btn btn-primary"
                  onClick={handleUpdatePrompt}
                >
                  Save
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={handleDeletePrompt}
                >
                  Delete
                </button>
              </div>
              </div>

              <div className="form-group" style={{ flex: 1 }}>
                <label htmlFor="editPromptContent" className="config-label">System Prompt Content</label>
                <div className="textarea-container" style={{ position: 'relative' }}>
                  <textarea
                    className="config-input"
                    id="editPromptContent"
                    placeholder="Enter your system prompt here..."
                    value={editForm.content}
                    onChange={(e) => setEditForm({ ...editForm, content: e.target.value })}
                    style={{ minHeight: '490px', resize: 'none', padding: '1.5rem 2.5rem', fontFamily: 'monospace' }}
                  />
                  <button
                    className="copy-button"
                    onClick={() => copyToClipboard(editForm.content)}
                    style={{
                      position: 'absolute',
                      top: '10px',
                      right: '15px',
                      padding: '4px 8px',
                      fontSize: '12px',
                      backgroundColor: '#f3f4f6',
                      border: '1px solid #d1d5db',
                      borderRadius: '4px',
                      cursor: 'pointer',
                    }}
                  >
                    Copy
                  </button>
                </div>
              </div>
            </div>
          </>
        ) : showCreateForm ? (
          <>
            <div className="chat-header">
              <div className="chat-title">Create New Prompt</div>
            </div>

            <div className="editor-container" style={{ padding: '20px' }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label htmlFor="createPromptContent" className="config-label">System Prompt Content</label>
                <div className="textarea-container" style={{ position: 'relative' }}>
                  <textarea
                    className="config-input"
                    id="createPromptContent"
                    placeholder="Enter your system prompt content here..."
                    value={createForm.content}
                    onChange={(e) => setCreateForm({ ...createForm, content: e.target.value })}
                    style={{ minHeight: '580px', resize: 'none' }}
                  />
                  <button
                    className="copy-button"
                    onClick={() => copyToClipboard(createForm.content)}
                    style={{
                      position: 'absolute',
                      top: '10px',
                      right: '10px',
                      padding: '4px 8px',
                      fontSize: '12px',
                      backgroundColor: '#f3f4f6',
                      border: '1px solid #d1d5db',
                      borderRadius: '4px',
                      cursor: 'pointer',
                    }}
                  >
                    Copy
                  </button>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div>
          <div className="chat-header">
            <div className="chat-title">Prompt Manager - Edit System Prompts</div>
          </div>

          <div className="editor-container">
            <div className="empty-state" style={{ textAlign: 'center', padding: '15rem', color: '#6b7280' }}>
              <h3 style={{ fontSize: '18px', fontWeight: '500', marginBottom: '8px' }}>Select a prompt to edit</h3>
              <p>Choose a prompt from the sidebar to view and edit its content</p>
            </div>
          </div>
          </div>
        )}
      </div>

      {/* Success/Error Messages */}
      {message && (
        <div
          style={{
            position: 'fixed',
            top: '20px',
            right: '10px',
            zIndex: 1000,
            padding: '10px 10px',
            borderRadius: '6px',
            fontWeight: '500',
            backgroundColor: message.type === 'success' ? '#10b981' : '#ef4444',
            color: 'white',
            animation: 'slideIn 0.3s ease',
          }}
        >
          {message.text}
        </div>
      )}
    </div>
  );
};

export default PromptEditor; 