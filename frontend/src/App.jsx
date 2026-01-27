import { useState, useEffect } from 'react';
import { api } from './services/api';
import ScopeSelector from './components/ScopeSelector';
import CoverageDashboard from './components/CoverageDashboard';
import DeferredItemsList from './components/DeferredItemsList';
import MapTable from './components/MapTable';
import ManualManager from './components/ManualManager';
import './App.css';

function App() {
  const [audits, setAudits] = useState([]);
  const [selectedAudit, setSelectedAudit] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  // Phase 3: Active view tab
  const [activeView, setActiveView] = useState('questions'); // 'questions' | 'ownership' | 'scope' | 'coverage' | 'deferred' | 'map' | 'manuals'
  // Phase 2: Ownership state
  const [ownershipData, setOwnershipData] = useState(null);
  const [assigningOwnership, setAssigningOwnership] = useState(false);
  const [applicabilityMap, setApplicabilityMap] = useState({});

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
      setActiveView('questions');
      try {
        const applicability = await api.getApplicability(auditId);
        const map = {};
        (applicability.applicability || []).forEach((item) => {
          if (item.qid) map[item.qid] = item;
        });
        setApplicabilityMap(map);
      } catch (e) {
        setApplicabilityMap({});
      }
      // Also load ownership data if available
      try {
        const ownership = await api.getOwnershipAssignments(auditId);
        setOwnershipData(ownership);
      } catch (e) {
        setOwnershipData(null);
      }
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
        setOwnershipData(null);
      }
      await loadAudits();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleRunOwnership = async () => {
    if (!selectedAudit?.id) return;

    try {
      setAssigningOwnership(true);
      setError(null);
      const result = await api.runOwnershipAssignment(selectedAudit.id);
      setOwnershipData(result);
      setActiveView('ownership');
    } catch (err) {
      setError(err.message);
    } finally {
      setAssigningOwnership(false);
    }
  };

  const handleScopeChange = (selectedFunctions) => {
    // Refresh coverage view when scope changes
    setActiveView('coverage');
  };

  const handleViewDeferred = () => {
    setActiveView('deferred');
  };

  const handleToggleApplicability = async (qid, makeApplicable) => {
    if (!selectedAudit?.id || !qid) return;

    let reason = '';
    if (!makeApplicable) {
      reason = window.prompt('Reason for Not Applicable (optional):', '') || '';
    }

    try {
      await api.setApplicability(selectedAudit.id, qid, makeApplicable, reason);
      const applicability = await api.getApplicability(selectedAudit.id);
      const map = {};
      (applicability.applicability || []).forEach((item) => {
        if (item.qid) map[item.qid] = item;
      });
      setApplicabilityMap(map);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleAutoDetectApplicability = async () => {
    if (!selectedAudit?.id) return;
    try {
      await api.autoDetectApplicability(selectedAudit.id);
      const applicability = await api.getApplicability(selectedAudit.id);
      const map = {};
      (applicability.applicability || []).forEach((item) => {
        if (item.qid) map[item.qid] = item;
      });
      setApplicabilityMap(map);
    } catch (err) {
      setError(err.message);
    }
  };

  const dctLabel = (() => {
    const edition = selectedAudit?.data?.metadata?.dct_edition;
    const version = selectedAudit?.data?.metadata?.dct_version;
    if (edition && version) return `ED ${edition} (Version ${version})`;
    if (edition) return `ED ${edition}`;
    if (version) return `Version ${version}`;
    return 'Unknown';
  })();

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
            <div className="upload-note">
              QID counts vary by DCT edition/version; completeness is validated against the uploaded file.
            </div>
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
                      <span>Pages: {audit.summary.pages}</span>
                      <span>Questions: {audit.summary.questions}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="audit-details">
            {!selectedAudit && (
              <div className="empty-state">Select an audit to view details</div>
            )}
            {selectedAudit && typeof selectedAudit === 'object' && selectedAudit.data && (
              <>
                {/* Navigation Tabs */}
                <div className="details-tabs">
                  <button
                    className={`tab ${activeView === 'questions' ? 'active' : ''}`}
                    onClick={() => setActiveView('questions')}
                  >
                    Questions
                  </button>
                  <button
                    className={`tab ${activeView === 'ownership' ? 'active' : ''}`}
                    onClick={() => setActiveView('ownership')}
                  >
                    Ownership
                  </button>
                  <button
                    className={`tab ${activeView === 'scope' ? 'active' : ''}`}
                    onClick={() => setActiveView('scope')}
                  >
                    Scope
                  </button>
                  <button
                    className={`tab ${activeView === 'coverage' ? 'active' : ''}`}
                    onClick={() => setActiveView('coverage')}
                  >
                    Coverage
                  </button>
                  <button
                    className={`tab ${activeView === 'deferred' ? 'active' : ''}`}
                    onClick={() => setActiveView('deferred')}
                  >
                    Deferred
                  </button>
                  <button
                    className={`tab ${activeView === 'map' ? 'active' : ''}`}
                    onClick={() => setActiveView('map')}
                  >
                    MAP
                  </button>
                  <button
                    className={`tab ${activeView === 'manuals' ? 'active' : ''}`}
                    onClick={() => setActiveView('manuals')}
                  >
                    Manuals
                  </button>
                </div>

                <div className="audit-details-content">
                  {/* Questions View */}
                  {activeView === 'questions' && (
                    <>
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
                            <strong>DCT:</strong> {dctLabel}
                          </div>
                          <div>
                            <strong>Uploaded:</strong>{' '}
                            {new Date(selectedAudit.uploaded_at).toLocaleString()}
                          </div>
                        </div>
                      </div>

                      <div className="details-section">
                        <div className="questions-header">
                          <h3>Questions ({selectedAudit.data.questions?.length || 0})</h3>
                          <button
                            className="btn-secondary"
                            onClick={handleAutoDetectApplicability}
                          >
                            Auto-detect Applicability
                          </button>
                        </div>
                        <div className="questions-list">
                          {selectedAudit.data.questions?.map((q, idx) => {
                            const applicability = q.QID ? applicabilityMap[q.QID] : null;
                            const isApplicable = applicability ? applicability.is_applicable : true;

                            return (
                              <div key={idx} className={`question-item ${!isApplicable ? 'not-applicable' : ''}`}>
                                <div className="question-header">
                                  <span className="element-id">{q.Element_ID || 'N/A'}</span>
                                  {q.QID && <span className="qid">QID: {q.QID}</span>}
                                  {q.Question_Number && (
                                    <span className="qnum">Q{q.Question_Number}</span>
                                  )}
                                  {q.PDF_Page_Number && (
                                    <span className="page">Page {q.PDF_Page_Number}</span>
                                  )}
                                  {!isApplicable && (
                                    <span className="na-badge">Not Applicable</span>
                                  )}
                                  {q.QID && (
                                    <button
                                      className="btn-link"
                                      onClick={() => handleToggleApplicability(q.QID, !isApplicable)}
                                    >
                                      {isApplicable ? 'Mark N/A' : 'Mark Applicable'}
                                    </button>
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
                            );
                          })}
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
                    </>
                  )}

                  {/* Ownership View */}
                  {activeView === 'ownership' && (
                    <div className="details-section">
                      <h3>Ownership Assignments</h3>

                      {!ownershipData?.assignments?.length && (
                        <div className="ownership-empty">
                          <p>No ownership assignments yet.</p>
                          <button
                            onClick={handleRunOwnership}
                            disabled={assigningOwnership}
                            className="btn-primary"
                          >
                            {assigningOwnership ? 'Assigning...' : 'Run Ownership Assignment'}
                          </button>
                        </div>
                      )}

                      {ownershipData?.assignments?.length > 0 && (
                        <>
                          <div className="ownership-summary">
                            <h4>Summary</h4>
                            <div className="summary-grid">
                              <div>
                                <strong>Total Assigned:</strong> {ownershipData.summary?.total || 0}
                              </div>
                              {ownershipData.summary?.by_function && (
                                <div className="function-breakdown">
                                  {Object.entries(ownershipData.summary.by_function).map(([func, count]) => (
                                    <span key={func} className="function-count">
                                      {func}: {count}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                            <button
                              onClick={handleRunOwnership}
                              disabled={assigningOwnership}
                              className="btn-secondary"
                            >
                              {assigningOwnership ? 'Re-assigning...' : 'Re-run Assignment'}
                            </button>
                          </div>

                          <div className="ownership-list">
                            {ownershipData.assignments.map((a, idx) => (
                              <div key={idx} className="ownership-item">
                                <div className="ownership-header">
                                  <span className="qid">QID: {a.qid}</span>
                                  <span className={`confidence ${a.confidence_score?.toLowerCase()}`}>
                                    {a.confidence_score}
                                  </span>
                                </div>
                                <div className="ownership-function">
                                  <strong>Owner:</strong> {a.primary_function}
                                  {a.supporting_functions?.length > 0 && (
                                    <span className="supporting">
                                      (Supporting: {a.supporting_functions.join(', ')})
                                    </span>
                                  )}
                                </div>
                                <div className="ownership-rationale">
                                  {a.rationale}
                                </div>
                                {a.is_manual_override && (
                                  <div className="override-badge">Manual Override</div>
                                )}
                              </div>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  )}

                  {/* Scope Selection View */}
                  {activeView === 'scope' && (
                    <ScopeSelector
                      auditId={selectedAudit.id}
                      onScopeChange={handleScopeChange}
                    />
                  )}

                  {/* Coverage Dashboard View */}
                  {activeView === 'coverage' && (
                    <CoverageDashboard
                      auditId={selectedAudit.id}
                      onViewDeferred={handleViewDeferred}
                    />
                  )}

                  {/* Deferred Items View */}
                  {activeView === 'deferred' && (
                    <DeferredItemsList
                      auditId={selectedAudit.id}
                      onClose={() => setActiveView('coverage')}
                    />
                  )}

                  {/* MAP View */}
                  {activeView === 'map' && (
                    <MapTable auditId={selectedAudit.id} />
                  )}

                  {/* Manuals View */}
                  {activeView === 'manuals' && (
                    <ManualManager />
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
