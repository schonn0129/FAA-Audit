/**
 * RiskHeatmap Component
 *
 * Displays a risk matrix showing QIDs categorized by:
 * - Confidence level (High, Medium, Low)
 * - Manual reference status (Has refs, Missing refs)
 *
 * Questions with weak manual references (missing AIP/GMM) are flagged.
 * Low confidence assignments are also highlighted.
 */
export default function RiskHeatmap({ riskData, onCellClick }) {
  if (!riskData) {
    return <div className="chart-empty">No risk data available</div>;
  }

  const {
    highConfWithRefs = 0,
    highConfNoRefs = 0,
    medConfWithRefs = 0,
    medConfNoRefs = 0,
    lowConfWithRefs = 0,
    lowConfNoRefs = 0,
    totalAtRisk = 0,
    needsReview = []
  } = riskData;

  const getRiskColor = (confidence, hasRefs) => {
    if (confidence === 'High' && hasRefs) return '#4CAF50'; // Green
    if (confidence === 'High' && !hasRefs) return '#FFC107'; // Yellow
    if (confidence === 'Medium' && hasRefs) return '#FFC107'; // Yellow
    if (confidence === 'Medium' && !hasRefs) return '#FF9800'; // Orange
    if (confidence === 'Low' && hasRefs) return '#FF9800'; // Orange
    if (confidence === 'Low' && !hasRefs) return '#F44336'; // Red
    return '#9E9E9E';
  };

  const getRiskLevel = (confidence, hasRefs) => {
    if (confidence === 'High' && hasRefs) return 'Low Risk';
    if (confidence === 'High' && !hasRefs) return 'Medium Risk';
    if (confidence === 'Medium' && hasRefs) return 'Medium Risk';
    if (confidence === 'Medium' && !hasRefs) return 'Elevated Risk';
    if (confidence === 'Low' && hasRefs) return 'Elevated Risk';
    if (confidence === 'Low' && !hasRefs) return 'High Risk';
    return 'Unknown';
  };

  const cells = [
    { confidence: 'High', hasRefs: true, count: highConfWithRefs },
    { confidence: 'High', hasRefs: false, count: highConfNoRefs },
    { confidence: 'Medium', hasRefs: true, count: medConfWithRefs },
    { confidence: 'Medium', hasRefs: false, count: medConfNoRefs },
    { confidence: 'Low', hasRefs: true, count: lowConfWithRefs },
    { confidence: 'Low', hasRefs: false, count: lowConfNoRefs },
  ];

  const handleCellClick = (cell) => {
    if (onCellClick && cell.count > 0) {
      onCellClick(cell);
    }
  };

  return (
    <div className="chart-container risk-heatmap">
      <h4 className="chart-title">Risk Assessment Matrix</h4>
      <p className="chart-subtitle">
        Questions with weak manual references flagged for review
      </p>

      <div className="heatmap-grid">
        {/* Header row */}
        <div className="heatmap-cell header corner"></div>
        <div className="heatmap-cell header">Has Manual Refs</div>
        <div className="heatmap-cell header">Missing Refs</div>

        {/* High confidence row */}
        <div className="heatmap-cell row-header">High Confidence</div>
        <div
          className="heatmap-cell data clickable"
          style={{ backgroundColor: getRiskColor('High', true) }}
          onClick={() => handleCellClick(cells[0])}
          title={getRiskLevel('High', true)}
        >
          <span className="cell-count">{highConfWithRefs}</span>
        </div>
        <div
          className="heatmap-cell data clickable"
          style={{ backgroundColor: getRiskColor('High', false) }}
          onClick={() => handleCellClick(cells[1])}
          title={getRiskLevel('High', false)}
        >
          <span className="cell-count">{highConfNoRefs}</span>
        </div>

        {/* Medium confidence row */}
        <div className="heatmap-cell row-header">Medium Confidence</div>
        <div
          className="heatmap-cell data clickable"
          style={{ backgroundColor: getRiskColor('Medium', true) }}
          onClick={() => handleCellClick(cells[2])}
          title={getRiskLevel('Medium', true)}
        >
          <span className="cell-count">{medConfWithRefs}</span>
        </div>
        <div
          className="heatmap-cell data clickable"
          style={{ backgroundColor: getRiskColor('Medium', false) }}
          onClick={() => handleCellClick(cells[3])}
          title={getRiskLevel('Medium', false)}
        >
          <span className="cell-count">{medConfNoRefs}</span>
        </div>

        {/* Low confidence row */}
        <div className="heatmap-cell row-header">Low Confidence</div>
        <div
          className="heatmap-cell data clickable"
          style={{ backgroundColor: getRiskColor('Low', true) }}
          onClick={() => handleCellClick(cells[4])}
          title={getRiskLevel('Low', true)}
        >
          <span className="cell-count">{lowConfWithRefs}</span>
        </div>
        <div
          className="heatmap-cell data clickable"
          style={{ backgroundColor: getRiskColor('Low', false) }}
          onClick={() => handleCellClick(cells[5])}
          title={getRiskLevel('Low', false)}
        >
          <span className="cell-count">{lowConfNoRefs}</span>
        </div>
      </div>

      {/* Legend */}
      <div className="heatmap-legend">
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#4CAF50' }}></span>
          <span>Low Risk</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#FFC107' }}></span>
          <span>Medium Risk</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#FF9800' }}></span>
          <span>Elevated Risk</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#F44336' }}></span>
          <span>High Risk</span>
        </div>
      </div>

      {/* Summary */}
      <div className="risk-summary">
        <div className="summary-stat warning">
          <span className="stat-value">{totalAtRisk}</span>
          <span className="stat-label">QIDs Require Review</span>
        </div>
        <p className="summary-note">
          High-risk items have low confidence AND missing manual references.
          Review these before audit submission.
        </p>
      </div>

      {/* Needs Review List (collapsed by default) */}
      {needsReview.length > 0 && (
        <details className="needs-review-section">
          <summary className="review-toggle">
            View {needsReview.length} items needing review
          </summary>
          <div className="review-list">
            {needsReview.slice(0, 10).map((item, idx) => (
              <div key={idx} className="review-item">
                <span className="review-qid">{item.qid}</span>
                <span className={`review-confidence ${item.confidence.toLowerCase()}`}>
                  {item.confidence}
                </span>
                <span className="review-issue">{item.issue}</span>
              </div>
            ))}
            {needsReview.length > 10 && (
              <div className="review-more">
                + {needsReview.length - 10} more items
              </div>
            )}
          </div>
        </details>
      )}
    </div>
  );
}
