import React from 'react';
import { RadarDataPoint } from '../types';

interface RadarChartProps {
  data: RadarDataPoint[];
  size?: number;
}

export const RadarChart: React.FC<RadarChartProps> = ({ data, size = 380 }) => {
  if (!data || data.length === 0) return null;

  const center = size / 2;
  const radius = size * 0.38;
  const totalAxes = data.length;
  const angleSlice = (Math.PI * 2) / totalAxes;

  // Concentric levels (20%, 40%, 60%, 80%, 100%)
  const levels = [0.2, 0.4, 0.6, 0.8, 1.0];

  // Coordinates for level rings
  const getCoordinates = (angle: number, r: number) => {
    return {
      x: center + r * Math.sin(angle),
      y: center - r * Math.cos(angle),
    };
  };

  // Build the polygon points for candidate scores
  const scorePoints = data.map((d, i) => {
    const angle = i * angleSlice;
    const r = (d.score / 100) * radius;
    const coords = getCoordinates(angle, r);
    return `${coords.x},${coords.y}`;
  }).join(' ');

  return (
    <div className="flex flex-col items-center justify-center">
      <svg width={size} height={size} className="overflow-visible select-none">
        <defs>
          <radialGradient id="radarGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#10B981" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#059669" stopOpacity="0.05" />
          </radialGradient>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Concentric Web Rings */}
        {levels.map((lvl, idx) => {
          const ringPoints = Array.from({ length: totalAxes }).map((_, i) => {
            const angle = i * angleSlice;
            const c = getCoordinates(angle, radius * lvl);
            return `${c.x},${c.y}`;
          }).join(' ');

          return (
            <g key={idx}>
              <polygon
                points={ringPoints}
                fill="none"
                stroke="#1E293B"
                strokeWidth={idx === levels.length - 1 ? "1.5" : "0.75"}
                strokeDasharray={idx === levels.length - 1 ? "none" : "3,3"}
              />
              <text
                x={center + 4}
                y={center - radius * lvl + 10}
                fill="#475569"
                fontSize="9"
                fontFamily="monospace"
              >
                {Math.round(lvl * 100)}
              </text>
            </g>
          );
        })}

        {/* Axis Spokes from Center */}
        {data.map((_, i) => {
          const angle = i * angleSlice;
          const target = getCoordinates(angle, radius);
          return (
            <line
              key={i}
              x1={center}
              y1={center}
              x2={target.x}
              y2={target.y}
              stroke="#1E293B"
              strokeWidth="1"
            />
          );
        })}

        {/* Candidate Score Filled Polygon */}
        <polygon
          points={scorePoints}
          fill="url(#radarGlow)"
          stroke="#10B981"
          strokeWidth="2.5"
          filter="url(#glow)"
        />

        {/* Data Vertices (Dots) and Score Tags */}
        {data.map((d, i) => {
          const angle = i * angleSlice;
          const r = (d.score / 100) * radius;
          const point = getCoordinates(angle, r);
          const labelPoint = getCoordinates(angle, radius + 26);

          return (
            <g key={i}>
              <circle
                cx={point.x}
                cy={point.y}
                r="4.5"
                fill="#10B981"
                stroke="#0B132B"
                strokeWidth="2"
              />
              <text
                x={labelPoint.x}
                y={labelPoint.y}
                textAnchor="middle"
                dominantBaseline="central"
                fill="#CBD5E1"
                fontSize="11"
                fontWeight="600"
              >
                {d.subject.split('\n')[0]}
              </text>
              <text
                x={labelPoint.x}
                y={labelPoint.y + 13}
                textAnchor="middle"
                dominantBaseline="central"
                fill="#10B981"
                fontSize="10"
                fontFamily="monospace"
                fontWeight="bold"
              >
                {d.score.toFixed(0)}%
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};
