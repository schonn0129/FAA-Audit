import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

/**
 * ScopeBarChart Component
 *
 * Displays in-scope vs deferred QIDs by function as a stacked/grouped bar chart.
 */
export default function ScopeBarChart({ byFunction, inScopeFunctions }) {
  if (!byFunction || Object.keys(byFunction).length === 0) {
    return <div className="chart-empty">No scope data available</div>;
  }

  const shortLabelForFunction = (name) => {
    const normalized = (name || '').toLowerCase();
    if (normalized.includes('maintenance planning')) return 'MP';
    if (normalized.includes('maintenance operations center')) return 'MOC';
    if (normalized.includes('director of maintenance')) return 'DOM';
    if (normalized.includes('aircraft records')) return 'Records';
    if (normalized.includes('quality')) return 'Quality';
    if (normalized.includes('training')) return 'Training';
    if (normalized.includes('safety')) return 'Safety';
    return name;
  };

  const data = Object.entries(byFunction)
    .map(([name, info]) => ({
      name: shortLabelForFunction(name),
      fullName: name,
      inScope: info.in_scope ? info.total : 0,
      deferred: info.in_scope ? 0 : info.total,
      total: info.total,
      isInScope: info.in_scope
    }))
    .filter(item => item.total > 0)
    .sort((a, b) => b.total - a.total);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const item = data.find(d => d.name === label);
      return (
        <div className="chart-tooltip">
          <p className="tooltip-label">{item?.fullName || label}</p>
          <p className="tooltip-value in-scope">In Scope: {payload[0]?.value || 0}</p>
          <p className="tooltip-value deferred">Deferred: {payload[1]?.value || 0}</p>
          <p className="tooltip-total">Total: {item?.total || 0}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-container scope-bar">
      <h4 className="chart-title">In-Scope vs Deferred by Function</h4>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart
          data={data}
          margin={{ top: 20, right: 20, left: 10, bottom: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="name"
            interval={0}
            tick={{ fontSize: 11 }}
          />
          <YAxis
            label={{ value: 'QID Count', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Bar dataKey="inScope" name="In Scope" fill="#4CAF50" stackId="a" />
          <Bar dataKey="deferred" name="Deferred" fill="#9E9E9E" stackId="a" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
