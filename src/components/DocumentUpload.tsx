import React, { useState } from 'react';
import APIService from '../services/api';
import Dropdown from './Dropdown';
import { DropdownOption, DocumentUploadConfig, UploadProgress } from '../types';
import { useConfig } from '../contexts/ConfigContext';

interface DocumentUploadProps {
  onBack: () => void;
  apiService: APIService;
}

const indexTypeOptions: DropdownOption[] = [
  { value: 'global', label: 'Global' },
  { value: 'provider', label: 'Provider' },
];

const globalCategoryOptions: DropdownOption[] = [
  { value: 'accreditations', label: 'Accreditations' },
  { value: 'federal', label: 'Federal' },
  { value: 'state', label: 'State' },
];

const globalAccreditationOptions: DropdownOption[] = [
  { value: 'tjc', label: 'TJC' },
  { value: 'achc', label: 'ACHC' },
  { value: 'chap', label: 'CHAP' },
];

const globalFederalOptions: DropdownOption[] = [
  { value: 'cms', label: 'CMS' },
  { value: 'regulations', label: 'Regulations' },
];

const providerCategoryOptions: DropdownOption[] = [
  { value: 'accreditations', label: 'Accreditations' },
  { value: 'clinical-protocols', label: 'Clinical Protocols' },
  { value: 'hr-policies', label: 'HR Policies' },
];

const DocumentUpload: React.FC<DocumentUploadProps> = ({ onBack, apiService }) => {
  const { state } = useConfig();
  const [config, setConfig] = useState<DocumentUploadConfig>({
    indexType: 'global',
  });
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const [isUploading, setIsUploading] = useState(false);

  const isConfigReady = () => {
    if (config.indexType === 'global') {
      if (!config.globalCategory) return false;
      if (config.globalCategory === 'accreditations') return !!config.globalAccreditation;
      if (config.globalCategory === 'federal') return !!config.globalFederal;
      if (config.globalCategory === 'state') return !!config.globalState;
      return true;
    }
    // provider
    return !!config.providerCategory;
  };

  const isUploadReady = () => isConfigReady() && selectedFiles.length > 0;

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setSelectedFiles(files);
  };

  const handleUpload = async () => {
    if (!isUploadReady()) return;

    setIsUploading(true);
    setUploadStatus('Uploading...');

    try {
      const result = await apiService.uploadDocuments(
        selectedFiles,
        {
          indexType: config.indexType,
          globalCategory: config.globalCategory,
          globalAccreditation: config.globalAccreditation,
          globalFederal: config.globalFederal,
          globalState: config.globalState,
          providerCategory: config.providerCategory,
          providerId: state.providerId,
        },
        (progress) => {
          setUploadProgress(progress);
        }
      );

      if (result.success) {
        setUploadStatus('Upload completed successfully!');
        setSelectedFiles([]);
        setUploadProgress(null);
      } else {
        setUploadStatus(`Upload failed: ${result.error}`);
      }
    } catch (error) {
      setUploadStatus(`Upload failed: ${error}`);
    } finally {
      setIsUploading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-title">Document Upload</div>
        <div className="sidebar-subtitle">Index & Document Management</div>
      </div>

      <div className="sidebar-content">
        {/* Index Type Selection */}
        <div className="config-section">
          <div className="config-section-title">Index Configuration</div>
          <div className="config-group">
            <p className="config-label">Select Index Type</p>
            <Dropdown
              options={indexTypeOptions}
              value={config.indexType}
              onChange={(value) => setConfig({ ...config, indexType: value as 'global' | 'provider' })}
            />
          </div>
        </div>

        {/* Global Category Selection */}
        {config.indexType === 'global' && (
          <div className="config-section">
            <div className="config-group">
              <p className="config-label">Select Global Category</p>
              <Dropdown
                options={globalCategoryOptions}
                value={config.globalCategory || ''}
                onChange={(value) => setConfig({ ...config, globalCategory: value as any })}
              />
            </div>
          </div>
        )}

        {/* Global Accreditations Selection */}
        {config.indexType === 'global' && config.globalCategory === 'accreditations' && (
          <div className="config-section">
            <div className="config-group">
              <p className="config-label">Select Accreditation</p>
              <Dropdown
                options={globalAccreditationOptions}
                value={config.globalAccreditation || ''}
                onChange={(value) => setConfig({ ...config, globalAccreditation: value as any })}
              />
            </div>
          </div>
        )}

        {/* Global Federal Selection */}
        {config.indexType === 'global' && config.globalCategory === 'federal' && (
          <div className="config-section">
            <div className="config-group">
              <p className="config-label">Select Federal Category</p>
              <Dropdown
                options={globalFederalOptions}
                value={config.globalFederal || ''}
                onChange={(value) => setConfig({ ...config, globalFederal: value as any })}
              />
            </div>
          </div>
        )}

        {/* Global State Input */}
        {config.indexType === 'global' && config.globalCategory === 'state' && (
          <div className="config-section">
            <div className="config-group">
              <label className="config-label" htmlFor="stateInput">
                Enter State
              </label>
              <input
                type="text"
                className="config-input"
                id="stateInput"
                placeholder="Enter valid US state"
                value={config.globalState || ''}
                onChange={(e) => setConfig({ ...config, globalState: e.target.value })}
              />
            </div>
          </div>
        )}

        {/* Provider Category Selection */}
        {config.indexType === 'provider' && (
          <div className="config-section">
            <div className="config-group">
              <p className="config-label">Select Provider Category</p>
              <Dropdown
                options={providerCategoryOptions}
                value={config.providerCategory || ''}
                onChange={(value) => setConfig({ ...config, providerCategory: value as any })}
              />
            </div>
          </div>
        )}

        {/* File Upload Section */}
        <div className="config-section">
          <div className="config-section-title">Document Upload</div>
          <div className={`file-upload-area ${!isConfigReady() ? 'disabled' : ''}`}>
            <div className="file-upload-text">Select files to upload</div>
            <label
              htmlFor="fileInput"
              className={`file-upload-button ${!isConfigReady() ? 'disabled' : ''}`}
            >
              Choose Files
            </label>
            <input
              type="file"
              id="fileInput"
              className="file-upload-input"
              multiple
              accept=".pdf,.doc,.docx,.txt"
              disabled={!isConfigReady()}
              onChange={handleFileSelect}
            />
            <div className="selected-files">
              {selectedFiles.map((file, index) => (
                <div key={index} className="text-sm text-gray-600">
                  {file.name} ({formatFileSize(file.size)})
                </div>
              ))}
            </div>

            {/* Upload Progress */}
            {uploadProgress && (
              <div className="upload-progress">
                <div className="progress-bar-container">
                  <div
                    className="progress-bar"
                    style={{ width: `${uploadProgress.percentage}%` }}
                  />
                </div>
              </div>
            )}
            {uploadStatus && (
              <div className="upload-status">{uploadStatus}</div>
            )}
          </div>
        </div>
      </div>

      <div className="sidebar-footer">
        <div className="fixed-buttons">
          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={!isUploadReady() || isUploading}
          >
            {isUploading ? 'Uploading...' : 'Upload'}
          </button>
          <button className="btn btn-secondary" onClick={onBack}>
            Back
          </button>
        </div>
      </div>
    </div>
  );
};

export default DocumentUpload; 