import { useEffect, useState } from 'react';
import { api } from '../services/api';

function MapTable({ auditId }) {
  const [mapData, setMapData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!auditId) return;

    setLoading(true);
    setError(null);

    api.getAuditMap(auditId)
      .then(setMapData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [auditId]);

  const handleExport = (format) => {
    const url = api.getAuditMapExportUrl(auditId, format);
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  if (loading) return <div className="map-table loading">Loading MAP...</div>;
  if (error) return <div className="map-table error">Error: {error}</div>;
  if (!mapData) return <div className="map-table">No MAP data available</div>;

  const {
    map_rows = [],
    in_scope_functions = [],
    total_rows = 0,
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
                <td>{row.Audit_Finding}</td>
                <td>{row.Compliance_Status}</td>
              </tr>
            ))}
            {map_rows.length === 0 && (
              <tr>
                <td colSpan={8} className="empty-cell">
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
