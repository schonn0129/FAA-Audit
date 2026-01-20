import { useState, useEffect } from 'react';
import { api } from './services/api';
import './App.css';

function App() {
  const [audits, setAudits] = useState([]);
  const [selectedAudit, setSelectedAudit] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    // Check backend connection on mount
    api.healthCheck()
      .then(() => {
        console.log('Backend connection OK');
        loadAudits();
      })
      .catch((err) => {
        console.error('Backend connection failed:', err);
        setError('Cannot connect to backend server. Make sure it\'s running on http://localhost:5000');
      });
  }, []);

  const loadAudits = async () => {
    try {
      setLoading(true);
      const data = await api.getAudits();
      setAudits(data.records || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) {
      setError('No file selected');
      return;
    }

    console.log('File selected:', {
      name: file.name,
      type: file.type,
      size: file.size
    });

    // Check file type (case-insensitive)
    const fileName = file.name.toLowerCase();
    const fileType = file.type;
    
    if (!fileName.endsWith('.pdf') && fileType !== 'application/pdf' && fileType !== '') {
      setError(`Invalid file type. Expected PDF, got: ${file.name} (type: ${fileType || 'unknown'})`);
      return;
    }
    
    // Check file size (50MB limit)
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      setError(`File size (${(file.size / 1024 / 1024).toFixed(2)}MB) exceeds 50MB limit`);
      return;
    }
    
    if (file.size === 0) {
      setError('File is empty');
      return;
    }

    try {
      setUploading(true);
      setError(null);
      const result = await api.uploadPDF(file);
      await loadAudits();
      setSelectedAudit(result.id);
      await loadAuditDetails(result.id);
    } catch (err) {
      console.error('Upload error:', err);
      setError(err.message || 'Failed to upload file. Please try again.');
    } finally {
      setUploading(false);
      // Reset file input
      event.target.value = '';
    }
  };

  const loadAuditDetails = async (auditId) => {
    try {
      setLoading(true);
      const data = await api.getAudit(auditId);
      setSelectedAudit(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (auditId) => {
    if (!confirm('Are you sure you want to delete this audit?')) return;

    try {
      await api.deleteAudit(auditId);
      if (selectedAudit?.id === auditId) {
        setSelectedAudit(null);
      }
      await loadAudits();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>FAA DCT Audit Application</h1>
        <p>Upload and analyze FAA Data Collection Tool (DCT) documents</p>
      </header>

      <main className="app-main">
        {error && (
          <div className="error-banner">
            <strong>Error:</strong> {error}
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        <div className="upload-section">
          <h2>Upload PDF</h2>
          <div className="upload-area">
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileUpload}
              disabled={uploading}
              id="file-upload"
              style={{ display: 'none' }}
            />
            <label htmlFor="file-upload" className="upload-button">
              {uploading ? 'Uploading...' : 'Choose PDF File'}
            </label>
            {uploading && <div className="upload-progress">Processing PDF...</div>}
          </div>
        </div>

        <div className="content-grid">
          <div className="audits-list">
            <h2>Audit Records ({audits.length})</h2>
            {loading && <div className="loading">Loading...</div>}
            {audits.length === 0 && !loading && (
              <div className="empty-state">No audits uploaded yet</div>
            )}
            <div className="audit-items">
              {audits.map((audit) => (
                <div
                  key={audit.id}
                  className={`audit-item ${selectedAudit?.id === audit.id ? 'selected' : ''}`}
                  onClick={() => loadAuditDetails(audit.id)}
                >
                  <div className="audit-item-header">
                    <strong>{audit.filename}</strong>
                    <button
                      className="delete-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(audit.id);
                      }}
                    >
                      ×
                    </button>
                  </div>
                  <div className="audit-item-meta">
                    <span className="status">{audit.status}</span>
                    <span className="date">
                      {new Date(audit.uploaded_at).toLocaleDateString()}
                    </span>
                  </div>
                  {audit.summary && (
                    <div className="audit-item-summary">
                      <span>📄 {audit.summary.pages} pages</span>
                      <span>❓ {audit.summary.questions} questions</span>
                      <span>📊 {audit.summary.tables} tables</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="audit-details">
            <h2>Audit Details</h2>
            {!selectedAudit && (
              <div className="empty-state">Select an audit to view details</div>
            )}
            {selectedAudit && typeof selectedAudit === 'object' && selectedAudit.data && (
              <div className="audit-details-content">
                <div className="details-section">
                  <h3>Metadata</h3>
                  <div className="metadata-grid">
                    <div>
                      <strong>Filename:</strong> {selectedAudit.filename}
                    </div>
                    <div>
                      <strong>Status:</strong> {selectedAudit.status}
                    </div>
                    <div>
                      <strong>Pages:</strong> {selectedAudit.data.metadata?.page_count || 0}
                    </div>
                    <div>
                      <strong>Uploaded:</strong>{' '}
                      {new Date(selectedAudit.uploaded_at).toLocaleString()}
                    </div>
                  </div>
                </div>

                <div className="details-section">
                  <h3>Questions ({selectedAudit.data.questions?.length || 0})</h3>
                  <div className="questions-list">
                    {selectedAudit.data.questions?.map((q, idx) => (
                      <div key={idx} className="question-item">
                        <div className="question-header">
                          <span className="element-id">{q.Element_ID || 'N/A'}</span>
                          {q.QID && <span className="qid">QID: {q.QID}</span>}
                          {q.Question_Number && (
                            <span className="qnum">Q{q.Question_Number}</span>
                          )}
                          {q.PDF_Page_Number && (
                            <span className="page">Page {q.PDF_Page_Number}</span>
                          )}
                        </div>
                        <div className="question-text">
                          {q.Question_Text_Full || q.Question_Text_Condensed || 'No text'}
                        </div>
                        {q.Data_Collection_Guidance && (
                          <div className="question-guidance">
                            <strong>Guidance:</strong> {q.Data_Collection_Guidance}
                          </div>
                        )}
                        {q.Reference_Raw && (
                          <div className="question-references">
                            <strong>References:</strong> {q.Reference_Raw}
                            {q.Reference_CFR_List?.length > 0 && (
                              <div className="cfr-refs">
                                CFR: {q.Reference_CFR_List.join(', ')}
                              </div>
                            )}
                          </div>
                        )}
                        {q.Notes?.length > 0 && (
                          <div className="question-notes">
                            <strong>Notes:</strong> {q.Notes.join(', ')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {selectedAudit.data.findings?.length > 0 && (
                  <div className="details-section">
                    <h3>Findings ({selectedAudit.data.findings.length})</h3>
                    <div className="findings-list">
                      {selectedAudit.data.findings.map((f, idx) => (
                        <div key={idx} className="finding-item">
                          <strong>Finding {f.number}:</strong> {f.description}
                          {f.severity && <span className="severity">{f.severity}</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
