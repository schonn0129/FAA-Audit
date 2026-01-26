import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

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

  const data = Object.entries(byFunction)
    .map(([name, info]) => ({
      name,
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
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderCustomLabel}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            layout="vertical"
            align="right"
            verticalAlign="middle"
            formatter={(value, entry) => {
              const item = data.find(d => d.name === value);
              return `${value} (${item?.value || 0})`;
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
