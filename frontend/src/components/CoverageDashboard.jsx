import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { OwnershipPieChart, ScopeBarChart, RiskHeatmap } from './charts';

/**
 * CoverageDashboard Component
 *
 * Displays coverage metrics for an audit based on its scope configuration.
 * Includes visualizations: pie chart, bar chart, and risk heatmap.
 */
export default function CoverageDashboard({ auditId, onViewDeferred }) {
  const [metrics, setMetrics] = useState(null);
  const [ownership, setOwnership] = useState(null);
  const [mapData, setMapData] = useState(null);
  const [riskData, setRiskData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadAllData();
  }, [auditId]);

  const loadAllData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch all data in parallel
      const [metricsRes, ownershipRes, mapRes] = await Promise.all([
        api.getCoverageMetrics(auditId),
        api.getOwnershipAssignments(auditId).catch(() => ({ assignments: [] })),
        api.getAuditMap(auditId).catch(() => ({ map_rows: [] }))
      ]);

      setMetrics(metricsRes);
      setOwnership(ownershipRes);
      setMapData(mapRes);

      // Compute risk data from ownership and MAP
      const computed = computeRiskData(ownershipRes.assignments || [], mapRes.map_rows || []);
      setRiskData(computed);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Compute risk matrix data by combining ownership confidence and manual references.
   */
  const computeRiskData = (assignments, mapRows) => {
    // Create lookup for manual references by QID
    const manualRefsByQid = {};
    mapRows.forEach(row => {
      const hasRefs = !!(row.AIP_Reference || row.GMM_Reference || row.Other_Manual_References);
      manualRefsByQid[row.QID] = hasRefs;
    });

    // Initialize counters
    let highConfWithRefs = 0;
    let highConfNoRefs = 0;
    let medConfWithRefs = 0;
    let medConfNoRefs = 0;
    let lowConfWithRefs = 0;
    let lowConfNoRefs = 0;
    const needsReview = [];

    assignments.forEach(assignment => {
      const confidence = assignment.confidence_score || 'Low';
      const hasRefs = manualRefsByQid[assignment.qid] ?? false;

      if (confidence === 'High') {
        if (hasRefs) highConfWithRefs++;
        else {
          highConfNoRefs++;
          needsReview.push({
            qid: assignment.qid,
            confidence,
            issue: 'Missing manual references'
          });
        }
      } else if (confidence === 'Medium') {
        if (hasRefs) medConfWithRefs++;
        else {
          medConfNoRefs++;
          needsReview.push({
            qid: assignment.qid,
            confidence,
            issue: 'Missing manual references'
          });
        }
      } else {
        if (hasRefs) {
          lowConfWithRefs++;
          needsReview.push({
            qid: assignment.qid,
            confidence,
            issue: 'Low confidence assignment'
          });
        } else {
          lowConfNoRefs++;
          needsReview.push({
            qid: assignment.qid,
            confidence,
            issue: 'Low confidence + missing refs'
          });
        }
      }
    });

    // Total at risk = medium-no-refs + low (both)
    const totalAtRisk = medConfNoRefs + lowConfWithRefs + lowConfNoRefs;

    return {
      highConfWithRefs,
      highConfNoRefs,
      medConfWithRefs,
      medConfNoRefs,
      lowConfWithRefs,
      lowConfNoRefs,
      totalAtRisk,
      needsReview: needsReview.sort((a, b) => {
        // Sort by risk level: Low conf no refs first
        const riskOrder = { 'Low confidence + missing refs': 0, 'Low confidence assignment': 1, 'Missing manual references': 2 };
        return (riskOrder[a.issue] || 3) - (riskOrder[b.issue] || 3);
      })
    };
  };

  if (loading) {
    return <div className="coverage-dashboard loading">Loading coverage metrics...</div>;
  }

  if (error) {
    return (
      <div className="coverage-dashboard error">
        <div className="error-message">{error}</div>
        <button onClick={loadAllData} className="btn-secondary">Retry</button>
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
        <h3>Coverage Dashboard</h3>
        <button onClick={loadAllData} className="btn-secondary btn-small">
          Refresh
        </button>
      </div>

      {/* Executive Summary */}
      <div className="executive-summary">
        <div className="summary-card primary">
          <div className="card-value">{overall_percentage}%</div>
          <div className="card-label">Coverage</div>
        </div>
        <div className="summary-card">
          <div className="card-value">{in_scope_count}</div>
          <div className="card-label">In Scope</div>
        </div>
        <div className="summary-card">
          <div className="card-value">{deferred_count}</div>
          <div className="card-label">Deferred</div>
        </div>
        <div className="summary-card">
          <div className="card-value">{metrics.total_qids}</div>
          <div className="card-label">Total QIDs</div>
        </div>
      </div>

      {/* Accountability Check */}
      <div className={`accountability-check ${accountability_check.all_qids_assigned ? 'success' : 'warning'}`}>
        <span className="check-icon">
          {accountability_check.all_qids_assigned ? '\u2713' : '\u26A0'}
        </span>
        <span className="check-message">{accountability_check.message}</span>
      </div>

      {/* Charts Grid */}
      <div className="charts-grid">
        {/* Pie Chart - QID Distribution */}
        <div className="chart-wrapper">
          <OwnershipPieChart byFunction={by_function} />
        </div>

        {/* Bar Chart - In-Scope vs Deferred */}
        <div className="chart-wrapper">
          <ScopeBarChart
            byFunction={by_function}
            inScopeFunctions={in_scope_functions}
          />
        </div>
      </div>

      {/* Risk Heatmap - Full Width */}
      <div className="chart-wrapper full-width">
        <RiskHeatmap
          riskData={riskData}
          onCellClick={(cell) => {
            console.log('Risk cell clicked:', cell);
            // Future: filter/show specific QIDs
          }}
        />
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

      {/* PDF Export Section (Phase 6) */}
      <div className="pdf-export-section">
        <button
          onClick={() => {
            // Cache-bust the GET so Safari/Chrome won't reuse an old PDF for the same URL.
            const url = api.getCompliancePdfExportUrl(auditId);
            const cacheBustedUrl = `${url}?t=${Date.now()}`;
            window.open(cacheBustedUrl, '_blank', 'noopener,noreferrer');
          }}
          className="btn-primary btn-export-pdf"
        >
          Export PDF Compliance Package
        </button>
        <p className="export-note">
          Generates a complete compliance package with Executive Summary, Ownership Table,
          In-Scope MAP, Deferred Items Log, Methodology Appendix, and Sign-off Page.
        </p>
      </div>
    </div>
  );
}
