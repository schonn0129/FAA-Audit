import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

const COLORS = [
  '#0088FE', // Blue - Maintenance Planning
  '#00C49F', // Teal - MOC
  '#FFBB28', // Yellow - DOM
  '#FF8042', // Orange - Aircraft Records
  '#8884D8', // Purple - Quality
  '#82CA9D', // Green - Training
  '#FF6B6B', // Red - Safety
];

/**
 * OwnershipPieChart Component
 *
 * Displays QID distribution by function owner as a pie chart.
 */
export default function OwnershipPieChart({ byFunction }) {
  if (!byFunction || Object.keys(byFunction).length === 0) {
    return <div className="chart-empty">No ownership data available</div>;
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
      name,
      shortName: shortLabelForFunction(name),
      value: info.total,
      percentage: info.percentage_of_audit
    }))
    .filter(item => item.value > 0)
    .sort((a, b) => b.value - a.value);

  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
    if (percent < 0.05) return null;
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={12}
        fontWeight="bold"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="chart-tooltip">
          <p className="tooltip-label">{data.name}</p>
          <p className="tooltip-value">{data.value} QIDs ({data.percentage}%)</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-container ownership-pie">
      <h4 className="chart-title">QID Distribution by Owner</h4>
      <div className="chart-row">
        <div className="chart-canvas">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={renderCustomLabel}
                outerRadius={105}
                fill="#8884d8"
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-legend" aria-label="QID distribution legend">
          {data.map((item, index) => (
            <div
              key={item.name}
              className="legend-row"
              title={item.name}
            >
              <span
                className="legend-swatch"
                style={{ backgroundColor: COLORS[index % COLORS.length] }}
              />
              <span className="legend-label">{item.shortName}</span>
              <span className="legend-value">{item.value}</span>
            </div>
          ))}
          <div className="legend-note">Hover the chart for full labels.</div>
        </div>
      </div>
    </div>
  );
}
