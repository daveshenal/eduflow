import React, { useState, useEffect, useCallback } from 'react';
import { useConfig } from '../contexts/ConfigContext';
import APIService from '../services/api';
import Dropdown from './Dropdown';
import ToastMessage, { ToastPayload } from './ToastMessage';
import { DropdownOption, PromptTemplate } from '../types';

const allowedNameOptions: DropdownOption[] = [
  { value: 'main_prompt', label: 'Main Prompt', active: true },
  { value: 'developer_chatbot', label: 'Developer Chatbot' },
  { value: 'curr_planner', label: 'Curriculum Planner' },
  { value: 'pdf_generator', label: 'PDF Generator' },
  { value: 'voice_script', label: 'Voice Script' },
];

const statusOptions: DropdownOption[] = [
  { value: 'active', label: 'Active', active: true },
  { value: 'inactive', label: 'Inactive' },
];

const displayPromptName = (name: string): string => {
  if (!name) return '';
  return name
    .split('_')
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(' ');
};

// Prompt Editor Component
const PromptEditor: React.FC<{ onBack: () => void }> = ({ onBack }) => {
  const { state } = useConfig();
  const [apiService] = useState(() => new APIService(state.backendUrl));
  const [prompts, setPrompts] = useState<PromptTemplate[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptTemplate | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [toast, setToast] = useState<ToastPayload | null>(null);

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
    setToast({ text, type });
  };

  const loadPrompts = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await apiService.getPrompts();
      if (!res.success) throw new Error(res.error || 'Failed to load prompts');
      const data = Array.isArray(res.data) ? res.data : [];
      const mapped: PromptTemplate[] = data.map((p: any) => ({
        id: p.id,
        name: p.name,
        version: p.version,
        status: p.status,
        description: p.description || '',
        content: p.prompt || '',
        type: (p.type as PromptTemplate['type']) || 'main',
      }));
      setPrompts(mapped);
    } catch (error) {
      setError('Database connection failed');
      setPrompts([]);
    } finally {
      setLoading(false);
    }
  }, [apiService]);

  useEffect(() => {
    apiService.setBaseUrl(state.backendUrl);
  }, [state.backendUrl, apiService]);

  useEffect(() => {
    loadPrompts();
    setSelectedPrompt(null);
  }, [loadPrompts]);

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
      const payload = {
        name: createForm.name,
        version: createForm.version,
        description: createForm.description || '',
        prompt: createForm.content,
      };
      const res = await apiService.createPrompt(payload);
      if (!res.success) throw new Error(res.error || 'Failed to create prompt');

      const created = res.data;
      if (createForm.status === 'active') {
        await apiService.activatePrompt(created.name, created.version);
        created.status = 'active';
      }

      const mapped: PromptTemplate = {
        id: created.id,
        name: created.name,
        version: created.version,
        status: created.status,
        description: created.description || '',
        content: created.prompt || '',
        type: (created.type as PromptTemplate['type']) || 'main',
      };

      setPrompts(prev => [mapped, ...prev]);
      setShowCreateForm(false);
      setCreateForm({ name: '', version: 'v1', status: 'active', description: '', content: '' });
      handlePromptSelect(mapped);
      showMessage('Prompt created successfully!', 'success');
    } catch (error) {
      showMessage('Failed to create prompt', 'error');
    }
  };

  const handleUpdatePrompt = async () => {
    if (!selectedPrompt) return;

    try {
      const updatePayload: { prompt?: string; description?: string } = {
        prompt: editForm.content,
        description: editForm.description,
      };
      const res = await apiService.updatePrompt(
        selectedPrompt.name,
        selectedPrompt.version,
        updatePayload
      );
      if (!res.success) throw new Error(res.error || 'Failed to save prompt');

      const updated = res.data;
      if (editForm.status === 'active') {
        await apiService.activatePrompt(updated.name, updated.version);
        updated.status = 'active';
      }

      const mapped: PromptTemplate = {
        id: updated.id,
        name: updated.name,
        version: updated.version,
        status: updated.status,
        description: updated.description || '',
        content: updated.prompt || '',
        type: (updated.type as PromptTemplate['type']) || 'main',
      };

      setSelectedPrompt(mapped);
      setPrompts(prev => prev.map(p => p.id === mapped.id ? mapped : p));
      showMessage('Prompt saved successfully!', 'success');
    } catch (error) {
      showMessage('Failed to save prompt', 'error');
    }
  };

  const handleDeletePrompt = async () => {
    if (!selectedPrompt) return;

    if (!window.confirm(`Are you sure you want to delete "${displayPromptName(selectedPrompt.name)}"?`)) {
      return;
    }

    try {
      const res = await apiService.deletePrompt(selectedPrompt.name, selectedPrompt.version);
      if (!res.success) throw new Error(res.error || 'Failed to delete prompt');

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
    const first = allowedNameOptions[0]?.value || '';
    setCreateForm({ name: first, version: 'v1', status: 'active', description: '', content: '' });
  };

  const handleCancelCreate = () => {
    setShowCreateForm(false);
    setCreateForm({ name: '', version: 'v1', status: 'active', description: '', content: '' });
  };

  return (
    <div className="app-container">
      {/* Toast Notification */}
      <ToastMessage message={toast} onClear={() => setToast(null)} />

      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-title">System Prompts</div>
          <div className="sidebar-subtitle">Manage your prompt templates</div>
        </div>

        <div className="sidebar-content">
          {showCreateForm && (
            <div className="config-section">
              <div className="config-section-title">Prompt Details</div>

              <div className="config-group">
                <p className="config-label">Prompt Name</p>
                <Dropdown
                  options={allowedNameOptions}
                  value={createForm.name}
                  onChange={(val) => setCreateForm({ ...createForm, name: val })}
                />
              </div>

              <div className="config-row" style={{ display: 'flex', gap: '1rem' }}>
                <div className="config-group" style={{ flex: 1 }}>
                  <label className="config-label" htmlFor="newPromptVersion">Version</label>
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
                <label className="config-label" htmlFor="newPromptDescription">Description</label>
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
                        {displayPromptName(prompt.name)}
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
                          borderRadius: '4px',
                          backgroundColor: prompt.status === 'active' ? '#d1fae5' : '#f3f4f6',
                          color: prompt.status === 'active' ? '#065f46' : '#4b5563',
                        }}
                      >
                        {prompt.status.charAt(0).toUpperCase() + prompt.status.slice(1)}
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
                <button className="btn btn-primary" onClick={handleShowCreateForm}>Add New</button>
                <button className="btn btn-secondary" onClick={onBack}>Back</button>
              </>
            ) : (
              <>
                <button className="btn btn-primary" onClick={handleCreatePrompt}>Create</button>
                <button className="btn btn-secondary" onClick={handleCancelCreate}>Cancel</button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="right-container">
        {selectedPrompt ? (
          <>
            <div className="main-header">
              <div className="header-title">{displayPromptName(selectedPrompt.name)}</div>
            </div>

            <div className="editor-container">
              <div className="form-row" style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '20px' }}>
                <div className="form-group" style={{ width: '100px' }}>
                  <p className="config-label">Status</p>
                  <Dropdown
                    options={statusOptions}
                    value={editForm.status}
                    onChange={(value) => setEditForm({ ...editForm, status: value })}
                  />
                </div>
                <div className="form-group" style={{ width: '40%', minWidth: '250px' }}>
                  <label htmlFor="editPromptDescription" className="config-label">Description</label>
                  <input
                    type="text"
                    className="config-input"
                    style={{ marginBottom: '0px' }}
                    id="editPromptDescription"
                    value={editForm.description}
                    onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  />
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end', marginLeft: 'auto' }}>
                  <button className="btn btn-primary" onClick={handleUpdatePrompt}>Update</button>
                  <button className="btn btn-secondary" onClick={handleDeletePrompt}>Delete</button>
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
                    style={{ minHeight: '460px', resize: 'none', padding: '1.5rem 2.5rem', fontFamily: 'monospace' }}
                  />
                  <button
                    className="copy-button"
                    onClick={() => copyToClipboard(editForm.content)}
                    style={{
                      position: 'absolute',
                      top: '15px',
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
            <div className="main-header">
              <div className="header-title">Create New Prompt</div>
            </div>

            <div className="editor-container">
              <div className="form-group" style={{ flex: 1 }}>
                <label htmlFor="createPromptContent" className="config-label">System Prompt Content</label>
                <div className="textarea-container" style={{ position: 'relative' }}>
                  <textarea
                    className="config-input"
                    id="createPromptContent"
                    placeholder="Enter your system prompt content here..."
                    value={createForm.content}
                    onChange={(e) => setCreateForm({ ...createForm, content: e.target.value })}
                    style={{ minHeight: '540px', resize: 'none' }}
                  />
                  <button
                    className="copy-button"
                    onClick={() => copyToClipboard(createForm.content)}
                    style={{
                      position: 'absolute',
                      top: '15px',
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
        ) : (
          <div>
            <div className="main-header">
              <div className="header-title">Prompt Manager - Edit System Prompts</div>
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
    </div>
  );
};

export default PromptEditor;