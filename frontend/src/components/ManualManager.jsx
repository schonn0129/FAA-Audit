import { useEffect, useState } from 'react';
import { api } from '../services/api';

function ManualManager() {
  const [manuals, setManuals] = useState([]);
  const [manualType, setManualType] = useState('AIP');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const loadManuals = async () => {
    try {
      const data = await api.getManuals();
      setManuals(data.manuals || []);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    loadManuals();
  }, []);

  const handleManualUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Manual upload requires a PDF file.');
      event.target.value = '';
      return;
    }

    try {
      setUploading(true);
      setError(null);
      await api.uploadManual(file, manualType);
      await loadManuals();
    } catch (err) {
      setError(err.message || 'Failed to upload manual');
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  };

  return (
    <div className="manual-manager">
      <div className="manual-header">
        <div>
          <h3>Company Manuals</h3>
          <p className="manual-subtitle">
            Upload AIP/GMM manuals to auto-suggest MAP references.
          </p>
        </div>
      </div>

      {error && <div className="manual-error">Error: {error}</div>}

      <div className="manual-upload">
        <div className="manual-field">
          <label htmlFor="manualType">Manual Type</label>
          <select
            id="manualType"
            value={manualType}
            onChange={(e) => setManualType(e.target.value)}
          >
            <option value="AIP">AIP</option>
            <option value="GMM">GMM</option>
            <option value="Other">Other</option>
          </select>
        </div>
        <div className="manual-field">
          <label htmlFor="manualUpload">Upload PDF</label>
          <input
            type="file"
            id="manualUpload"
            accept=".pdf,application/pdf"
            onChange={handleManualUpload}
            disabled={uploading}
          />
        </div>
        {uploading && <div className="manual-loading">Processing manual...</div>}
      </div>

      <div className="manual-list">
        <h4>Uploaded Manuals</h4>
        {manuals.length === 0 && (
          <div className="manual-empty">No manuals uploaded yet.</div>
        )}
        {manuals.map((manual) => (
          <div key={manual.id} className="manual-item">
            <div className="manual-item-main">
              <strong>{manual.filename}</strong>
              <span className="manual-type">{manual.manual_type}</span>
            </div>
            <div className="manual-item-meta">
              <span>Pages: {manual.page_count || 0}</span>
              <span>Sections: {manual.section_count || 0}</span>
              <span>Uploaded: {new Date(manual.upload_date).toLocaleDateString()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ManualManager;
