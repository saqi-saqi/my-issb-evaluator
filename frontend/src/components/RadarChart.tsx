import React from 'react';
import { RadarDataPoint } from '../types';

interface RadarChartProps {
  data: RadarDataPoint[];
  size?: number;
}

const formatDimensionLabel = (subject: string): string => {
  const clean = subject.replace(/\n/g, ' ').trim();
  if (clean.includes('Intellect')) return 'Intellect';
  if (clean.includes('Emotional')) return 'Emotional Composure';
  if (clean.includes('Social')) return 'Social Adaptability';
  if (clean.includes('Communication') || clean.includes('Expression')) return 'Expression';
  if (clean.includes('Motivation')) return 'Motivation';
  return clean;
};

export const RadarChart: React.FC<RadarChartProps> = ({ data, size = 320 }) => {
  if (!data || data.length === 0) return null;

  const center = size / 2;
  const radius = size * 0.35;
  const totalAxes = data.length;
  const angleSlice = (Math.PI * 2) / totalAxes;

  // Concentric levels (25%, 50%, 75%, 100%)
  const levels = [0.25, 0.5, 0.75, 1.0];

  // Coordinates for level rings
  const getCoordinates = (angle: number, r: number) => {
    return {
      x: center + r * Math.sin(angle),
      y: center - r * Math.cos(angle),
    };
  };

  // Build polygon points for candidate scores
  const scorePoints = data.map((d, i) => {
    const angle = i * angleSlice;
    const r = (Math.max(10, Math.min(100, d.score)) / 100) * radius;
    const coords = getCoordinates(angle, r);
    return `${coords.x},${coords.y}`;
  }).join(' ');

  return (
    <div className="flex flex-col items-center justify-center p-2">
      <svg width={size} height={size} className="overflow-visible select-none">
        <defs>
          <filter id="radarEmeraldGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Concentric Pentagonal Web Rings */}
        {levels.map((lvl, idx) => {
          const ringPoints = Array.from({ length: totalAxes }).map((_, i) => {
            const angle = i * angleSlice;
            const c = getCoordinates(angle, radius * lvl);
            return `${c.x},${c.y}`;
          }).join(' ');

          return (
            <polygon
              key={idx}
              points={ringPoints}
              fill="none"
              stroke="#1a2736"
              strokeWidth="1"
            />
          );
        })}

        {/* Axis Spokes from Center to outer vertices */}
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
              stroke="#1a2736"
              strokeWidth="1"
            />
          );
        })}

        {/* Candidate Score Filled Polygon with Neon Emerald Accent */}
        <polygon
          points={scorePoints}
          fill="rgba(0, 229, 153, 0.18)"
          stroke="#00e599"
          strokeWidth="2"
          filter="url(#radarEmeraldGlow)"
        />

        {/* Data Vertices (Dots) and Labels */}
        {data.map((d, i) => {
          const angle = i * angleSlice;
          const r = (Math.max(10, Math.min(100, d.score)) / 100) * radius;
          const point = getCoordinates(angle, r);
          const labelPoint = getCoordinates(angle, radius + 22);

          return (
            <g key={i}>
              <circle
                cx={point.x}
                cy={point.y}
                r="3.5"
                fill="#00e599"
                stroke="#060b11"
                strokeWidth="1.5"
              />
              <text
                x={labelPoint.x}
                y={labelPoint.y}
                textAnchor="middle"
                dominantBaseline="central"
                fill="#8da2ba"
                fontSize="11"
                fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
                fontWeight="500"
              >
                {formatDimensionLabel(d.subject || d.dimension)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};

