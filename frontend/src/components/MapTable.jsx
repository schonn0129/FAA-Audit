import { useEffect, useState } from 'react';
import { api } from '../services/api';

function MapTable({ auditId }) {
  const [mapData, setMapData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [manualLink, setManualLink] = useState({
    qid: '',
    manual_type: 'AIP',
    section: '',
    reference: '',
    notes: ''
  });
  const [manualLinkStatus, setManualLinkStatus] = useState(null);
  const [removeLink, setRemoveLink] = useState({
    qid: '',
    manual_type: 'ANY',
    section: '',
    reference: ''
  });
  const [removeLinkStatus, setRemoveLinkStatus] = useState(null);

  const loadMap = () => {
    if (!auditId) return;
    setLoading(true);
    setError(null);
    api.getAuditMap(auditId)
      .then(setMapData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (!auditId) return;
    loadMap();
  }, [auditId]);

  const handleExport = (format) => {
    const url = api.getAuditMapExportUrl(auditId, format);
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const handleAddManualLink = async (event) => {
    event.preventDefault();
    setManualLinkStatus(null);
    if (!manualLink.qid || !manualLink.section) {
      setManualLinkStatus('QID and section are required.');
      return;
    }
    try {
      await api.addManualLink(auditId, manualLink);
      setManualLinkStatus('Manual reference added.');
      setManualLink((prev) => ({ ...prev, section: '', reference: '', notes: '' }));
      loadMap();
    } catch (err) {
      setManualLinkStatus(err.message);
    }
  };

  const handleRemoveManualLink = async (event) => {
    event.preventDefault();
    setRemoveLinkStatus(null);
    if (!removeLink.qid || !removeLink.section) {
      setRemoveLinkStatus('QID and section are required.');
      return;
    }
    try {
      await api.removeManualLink(auditId, removeLink);
      setRemoveLinkStatus('Manual reference removed.');
      setRemoveLink((prev) => ({ ...prev, section: '', reference: '' }));
      loadMap();
    } catch (err) {
      setRemoveLinkStatus(err.message);
    }
  };

  if (loading) return <div className="map-table loading">Loading MAP...</div>;
  if (error) return <div className="map-table error">Error: {error}</div>;
  if (!mapData) return <div className="map-table">No MAP data available</div>;

  const {
    map_rows = [],
    in_scope_functions = [],
    total_rows = 0,
    in_scope_total = 0,
    not_applicable_count = 0,
    manuals_used = []
  } = mapData;

  return (
    <div className="map-table">
      <div className="map-header">
        <div>
          <h3>Mapping Audit Package (MAP)</h3>
          <p className="map-subtitle">
            In-scope QIDs: {total_rows} across {in_scope_functions.length} functions
          </p>
          {not_applicable_count > 0 && (
            <p className="map-subtitle">
              Not Applicable: {not_applicable_count} of {in_scope_total || total_rows}
            </p>
          )}
        </div>
        <div className="map-actions">
          <button className="btn-secondary" onClick={() => handleExport('csv')}>
            Export CSV
          </button>
          <button className="btn-primary" onClick={() => handleExport('xlsx')}>
            Export Excel
          </button>
        </div>
      </div>

      {manuals_used.length > 0 && (
        <div className="map-manuals">
          <strong>Manuals Used (latest by type):</strong>
          <div className="map-manuals-list">
            {manuals_used.map((manual) => (
              <span key={manual.id} className="map-manual-tag">
                {manual.manual_type}: {manual.filename}
                {manual.version ? ` (v${manual.version})` : ''}
              </span>
            ))}
          </div>
        </div>
      )}

      {in_scope_functions.length > 0 && (
        <div className="map-scope-tags">
          {in_scope_functions.map((func) => (
            <span key={func} className="scope-tag">{func}</span>
          ))}
        </div>
      )}

      <div className="map-manual-entry">
        <div className="map-manual-entry-header">
          <strong>Add Manual Reference</strong>
          <span className="map-manual-entry-hint">Multiple sections can be added per QID.</span>
        </div>
        <form className="map-manual-entry-form" onSubmit={handleAddManualLink}>
          <input
            type="text"
            placeholder="QID (e.g., 00004334)"
            value={manualLink.qid}
            onChange={(e) => setManualLink({ ...manualLink, qid: e.target.value.trim() })}
          />
          <select
            value={manualLink.manual_type}
            onChange={(e) => setManualLink({ ...manualLink, manual_type: e.target.value })}
          >
            <option value="AIP">AIP</option>
            <option value="GMM">GMM</option>
            <option value="Other">Other</option>
          </select>
          <input
            type="text"
            placeholder="Section (e.g., 5.2.1)"
            value={manualLink.section}
            onChange={(e) => setManualLink({ ...manualLink, section: e.target.value })}
          />
          <input
            type="text"
            placeholder="Reference text (optional)"
            value={manualLink.reference}
            onChange={(e) => setManualLink({ ...manualLink, reference: e.target.value })}
          />
          <input
            type="text"
            placeholder="Notes (optional)"
            value={manualLink.notes}
            onChange={(e) => setManualLink({ ...manualLink, notes: e.target.value })}
          />
          <button type="submit" className="btn-secondary">Add Reference</button>
        </form>
        {manualLinkStatus && <div className="map-manual-entry-status">{manualLinkStatus}</div>}
      </div>

      <div className="map-manual-entry">
        <div className="map-manual-entry-header">
          <strong>Remove Manual Reference</strong>
          <span className="map-manual-entry-hint">Removals prevent auto-suggestions from reappearing.</span>
        </div>
        <form className="map-manual-entry-form" onSubmit={handleRemoveManualLink}>
          <input
            type="text"
            placeholder="QID (e.g., 00004334)"
            value={removeLink.qid}
            onChange={(e) => setRemoveLink({ ...removeLink, qid: e.target.value.trim() })}
          />
          <select
            value={removeLink.manual_type}
            onChange={(e) => setRemoveLink({ ...removeLink, manual_type: e.target.value })}
          >
            <option value="ANY">Any Manual</option>
            <option value="AIP">AIP</option>
            <option value="GMM">GMM</option>
            <option value="Other">Other</option>
          </select>
          <input
            type="text"
            placeholder="Section (e.g., 3.1.1)"
            value={removeLink.section}
            onChange={(e) => setRemoveLink({ ...removeLink, section: e.target.value })}
          />
          <input
            type="text"
            placeholder="Reference text (optional)"
            value={removeLink.reference}
            onChange={(e) => setRemoveLink({ ...removeLink, reference: e.target.value })}
          />
          <button type="submit" className="btn-secondary">Remove Reference</button>
        </form>
        {removeLinkStatus && <div className="map-manual-entry-status">{removeLinkStatus}</div>}
      </div>

      <div className="map-table-container">
        <table>
          <thead>
            <tr>
              <th>QID</th>
              <th>Question Text</th>
              <th>AIP Reference</th>
              <th>GMM Reference</th>
              <th>Other Manual References</th>
              <th>Evidence Required</th>
              <th>Applicability Status</th>
              <th>Applicability Reason</th>
              <th>Audit Finding</th>
              <th>Compliance Status</th>
            </tr>
          </thead>
          <tbody>
            {map_rows.map((row, idx) => (
              <tr key={`${row.QID || 'qid'}-${idx}`}>
                <td className="qid">{row.QID}</td>
                <td className="question-text">{row.Question_Text}</td>
                <td>{row.AIP_Reference}</td>
                <td>{row.GMM_Reference}</td>
                <td>{row.Other_Manual_References}</td>
                <td>{row.Evidence_Required}</td>
                <td>{row.Applicability_Status}</td>
                <td>{row.Applicability_Reason}</td>
                <td>{row.Audit_Finding}</td>
                <td>{row.Compliance_Status}</td>
              </tr>
            ))}
            {map_rows.length === 0 && (
              <tr>
                <td colSpan={10} className="empty-cell">
                  No MAP rows for current scope.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default MapTable;
