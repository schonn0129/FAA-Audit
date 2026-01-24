import { useState, useEffect } from 'react';
import { api } from '../services/api';

/**
 * DeferredItemsList Component
 *
 * Displays deferred (out-of-scope) items for an audit.
 * These items maintain their ownership assignments and are documented
 * for PMI accountability.
 */
export default function DeferredItemsList({ auditId, onClose }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedFunctions, setExpandedFunctions] = useState({});
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadDeferredItems();
  }, [auditId]);

  const loadDeferredItems = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getDeferredItems(auditId);
      setReport(data);
      // Expand all functions by default
      const expanded = {};
      Object.keys(data.summary_by_function || {}).forEach(func => {
        expanded[func] = true;
      });
      setExpandedFunctions(expanded);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleFunction = (func) => {
    setExpandedFunctions(prev => ({
      ...prev,
      [func]: !prev[func]
    }));
  };

  const expandAll = () => {
    const expanded = {};
    Object.keys(report?.summary_by_function || {}).forEach(func => {
      expanded[func] = true;
    });
    setExpandedFunctions(expanded);
  };

  const collapseAll = () => {
    setExpandedFunctions({});
  };

  if (loading) {
    return <div className="deferred-list loading">Loading deferred items...</div>;
  }

  if (error) {
    return (
      <div className="deferred-list error">
        <div className="error-message">{error}</div>
        <button onClick={loadDeferredItems} className="btn-secondary">Retry</button>
      </div>
    );
  }

  if (!report) {
    return <div className="deferred-list">No report available</div>;
  }

  const { deferred_items, summary_by_function, total_deferred, scope_rationale, out_of_scope_functions } = report;

  // Filter items by search query
  const filteredItems = searchQuery
    ? deferred_items.filter(item =>
        item.qid?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.question_text_condensed?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.primary_function?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : deferred_items;

  // Group items by function
  const itemsByFunction = {};
  filteredItems.forEach(item => {
    const func = item.primary_function || 'Unknown';
    if (!itemsByFunction[func]) {
      itemsByFunction[func] = [];
    }
    itemsByFunction[func].push(item);
  });

  return (
    <div className="deferred-list">
      <div className="deferred-header">
        <h3>Deferred Items Report</h3>
        {onClose && (
          <button onClick={onClose} className="btn-close">&times;</button>
        )}
      </div>

      <div className="deferred-summary">
        <div className="summary-stat">
          <span className="stat-value">{total_deferred}</span>
          <span className="stat-label">Total Deferred</span>
        </div>
        <div className="summary-stat">
          <span className="stat-value">{out_of_scope_functions?.length || 0}</span>
          <span className="stat-label">Functions Deferred</span>
        </div>
      </div>

      {scope_rationale && (
        <div className="scope-rationale">
          <strong>Scope Rationale:</strong> {scope_rationale}
        </div>
      )}

      <div className="deferred-controls">
        <div className="search-box">
          <input
            type="text"
            placeholder="Search QID or question text..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="btn-clear-search"
            >
              &times;
            </button>
          )}
        </div>
        <div className="expand-controls">
          <button onClick={expandAll} className="btn-secondary btn-small">
            Expand All
          </button>
          <button onClick={collapseAll} className="btn-secondary btn-small">
            Collapse All
          </button>
        </div>
      </div>

      {searchQuery && (
        <div className="search-results-count">
          Showing {filteredItems.length} of {total_deferred} items
        </div>
      )}

      <div className="deferred-by-function">
        {Object.entries(itemsByFunction)
          .sort((a, b) => b[1].length - a[1].length)
          .map(([func, items]) => (
            <div key={func} className="function-group">
              <div
                className="function-header"
                onClick={() => toggleFunction(func)}
              >
                <span className="expand-icon">
                  {expandedFunctions[func] ? '\u25BC' : '\u25B6'}
                </span>
                <span className="function-name">{func}</span>
                <span className="function-count">{items.length} items</span>
              </div>

              {expandedFunctions[func] && (
                <div className="function-items">
                  <table className="items-table">
                    <thead>
                      <tr>
                        <th>QID</th>
                        <th>Question</th>
                        <th>Confidence</th>
                        <th>Deferral Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((item, idx) => (
                        <tr key={item.qid || idx}>
                          <td className="col-qid">{item.qid || '-'}</td>
                          <td className="col-question">
                            {item.question_text_condensed || item.question_text_full?.substring(0, 100) || '-'}
                          </td>
                          <td className="col-confidence">
                            <span className={`confidence-badge ${item.confidence_score?.toLowerCase() || 'unknown'}`}>
                              {item.confidence_score || '-'}
                            </span>
                          </td>
                          <td className="col-reason">{item.deferral_reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
      </div>

      {total_deferred === 0 && (
        <div className="no-deferred">
          <p>No deferred items. All functions are in scope.</p>
        </div>
      )}

      <div className="deferred-footer">
        <p className="accountability-note">
          <strong>PMI Accountability:</strong> All {total_deferred} deferred items have
          documented owners and are tracked for future audit cycles.
        </p>
        <div className="deferred-functions">
          <strong>Deferred Functions:</strong>
          <div className="function-tags">
            {out_of_scope_functions?.map(func => (
              <span key={func} className="function-tag deferred">{func}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
