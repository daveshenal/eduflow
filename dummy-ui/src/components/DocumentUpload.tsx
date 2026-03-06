import React, { useState } from 'react';
import APIService from '../services/api';
import { UploadProgress } from '../types';
import { useConfig } from '../contexts/ConfigContext';

interface DocumentUploadProps {
  onBack: () => void;
  apiService: APIService;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({ onBack, apiService }) => {
  const { state } = useConfig();
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const [isUploading, setIsUploading] = useState(false);

  const isUploadReady = () => !!state.providerId && selectedFiles.length > 0;

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
        state.providerId,
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
        <div className="sidebar-subtitle">Upload files into knowledgebase index</div>
      </div>

      <div className="sidebar-content">
        <div className="config-section">
          <div className="config-section-title">Index Configuration</div>
          <div className="config-group">
            <label className="config-label" htmlFor="indexIdInput">
              Index ID (must match backend index_id)
            </label>
            <input
              type="text"
              className="config-input"
              id="indexIdInput"
              placeholder="Enter index_id (e.g. demo)"
              value={state.providerId}
              readOnly
            />
            <p className="text-xs text-gray-500 mt-1">
              Configure this value from the main sidebar under "Index ID".
            </p>
          </div>
        </div>

        {/* File Upload Section */}
        <div className="config-section">
          <div className="config-section-title">Document Upload</div>
          <div className={`file-upload-area ${!state.providerId ? 'disabled' : ''}`}>
            <div className="file-upload-text">Select files to upload</div>
            <label
              htmlFor="fileInput"
              className={`file-upload-button ${!state.providerId ? 'disabled' : ''}`}
            >
              Choose Files
            </label>
            <input
              type="file"
              id="fileInput"
              className="file-upload-input"
              multiple
              accept=".pdf,.doc,.docx,.txt"
              disabled={!state.providerId}
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