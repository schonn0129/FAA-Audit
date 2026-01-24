import { useState, useEffect } from 'react';
import { api } from '../services/api';

/**
 * CoverageDashboard Component
 *
 * Displays coverage metrics for an audit based on its scope configuration.
 * Shows in-scope vs. deferred breakdown by function.
 */
export default function CoverageDashboard({ auditId, onViewDeferred }) {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadMetrics();
  }, [auditId]);

  const loadMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getCoverageMetrics(auditId);
      setMetrics(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="coverage-dashboard loading">Loading coverage metrics...</div>;
  }

  if (error) {
    return (
      <div className="coverage-dashboard error">
        <div className="error-message">{error}</div>
        <button onClick={loadMetrics} className="btn-secondary">Retry</button>
      </div>
    );
  }

  if (!metrics) {
    return <div className="coverage-dashboard">No metrics available</div>;
  }

  const { coverage, accountability_check, in_scope_functions } = metrics;
  const { overall_percentage, in_scope_count, deferred_count, by_function } = coverage;

  return (
    <div className="coverage-dashboard">
      <div className="coverage-header">
        <h3>Coverage Metrics</h3>
        <button onClick={loadMetrics} className="btn-secondary btn-small">
          Refresh
        </button>
      </div>

      {/* Overall Coverage */}
      <div className="coverage-overview">
        <div className="coverage-percentage">
          <div className="percentage-circle" data-percentage={overall_percentage}>
            <span className="percentage-value">{overall_percentage}%</span>
            <span className="percentage-label">Coverage</span>
          </div>
        </div>
        <div className="coverage-counts">
          <div className="count-item in-scope">
            <span className="count-value">{in_scope_count}</span>
            <span className="count-label">In Scope</span>
          </div>
          <div className="count-item deferred">
            <span className="count-value">{deferred_count}</span>
            <span className="count-label">Deferred</span>
          </div>
          <div className="count-item total">
            <span className="count-value">{metrics.total_qids}</span>
            <span className="count-label">Total QIDs</span>
          </div>
        </div>
      </div>

      {/* Coverage Bar */}
      <div className="coverage-bar-container">
        <div className="coverage-bar">
          <div
            className="coverage-bar-fill in-scope"
            style={{ width: `${overall_percentage}%` }}
          />
          <div
            className="coverage-bar-fill deferred"
            style={{ width: `${100 - overall_percentage}%` }}
          />
        </div>
        <div className="coverage-bar-legend">
          <span className="legend-item in-scope">In Scope ({overall_percentage}%)</span>
          <span className="legend-item deferred">Deferred ({(100 - overall_percentage).toFixed(1)}%)</span>
        </div>
      </div>

      {/* Accountability Check */}
      <div className={`accountability-check ${accountability_check.all_qids_assigned ? 'success' : 'warning'}`}>
        <span className="check-icon">
          {accountability_check.all_qids_assigned ? '\u2713' : '\u26A0'}
        </span>
        <span className="check-message">{accountability_check.message}</span>
      </div>

      {/* Function Breakdown */}
      <div className="function-breakdown">
        <h4>Breakdown by Function</h4>
        <div className="function-table">
          <div className="table-header">
            <span className="col-function">Function</span>
            <span className="col-status">Status</span>
            <span className="col-count">QIDs</span>
            <span className="col-percent">% of Audit</span>
          </div>
          {Object.entries(by_function)
            .sort((a, b) => b[1].total - a[1].total)
            .map(([func, data]) => (
              <div key={func} className={`table-row ${data.in_scope ? 'in-scope' : 'deferred'}`}>
                <span className="col-function">{func}</span>
                <span className="col-status">
                  <span className={`status-badge ${data.in_scope ? 'in-scope' : 'deferred'}`}>
                    {data.in_scope ? 'In Scope' : 'Deferred'}
                  </span>
                </span>
                <span className="col-count">{data.total}</span>
                <span className="col-percent">{data.percentage_of_audit}%</span>
              </div>
            ))}
        </div>
      </div>

      {/* In-Scope Functions Summary */}
      <div className="scope-summary">
        <h4>Functions In Scope ({in_scope_functions.length})</h4>
        <div className="scope-tags">
          {in_scope_functions.map(func => (
            <span key={func} className="scope-tag">{func}</span>
          ))}
        </div>
      </div>

      {/* View Deferred Button */}
      {deferred_count > 0 && (
        <div className="deferred-action">
          <button
            onClick={onViewDeferred}
            className="btn-primary"
          >
            View {deferred_count} Deferred Items
          </button>
          <p className="deferred-note">
            Deferred items remain documented with their assigned owners for PMI accountability.
          </p>
        </div>
      )}
    </div>
  );
}
