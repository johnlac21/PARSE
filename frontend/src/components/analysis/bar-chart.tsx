"use client";

import * as React from "react";
import {
  Bar,
  BarChart as RechartsBarChart,
  Cell,
  ErrorBar,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { cn } from "@/lib/utils";
import type { DifferenceRow } from "@/components/analysis/difference-table";

export interface DifferenceBarChartProps {
  /** Difference rows for the selected model (or all; filter by selectedModel). */
  rows: DifferenceRow[];
  /** Model to show; if not set, first model in data is used. */
  selectedModel: string | null;
  onModelChange?: (model: string) => void;
  loading?: boolean;
  className?: string;
}

const BAR_COLOR = "hsl(var(--primary))";
const BAR_COLOR_HOVER = "hsl(var(--primary) / 0.85)";

export function DifferenceBarChart({
  rows,
  selectedModel,
  onModelChange,
  loading,
  className,
}: DifferenceBarChartProps) {
  const modelOptions = React.useMemo(() => {
    const set = new Set(rows.map((r) => r.model));
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [rows]);

  const effectiveModel =
    selectedModel && modelOptions.includes(selectedModel)
      ? selectedModel
      : modelOptions[0] ?? null;

  React.useEffect(() => {
    if (effectiveModel && selectedModel !== effectiveModel && onModelChange) {
      onModelChange(effectiveModel);
    }
  }, [effectiveModel, selectedModel, onModelChange]);

  const chartData = React.useMemo(() => {
    if (!effectiveModel) return [];
    const filtered = rows
      .filter((r) => r.model === effectiveModel)
      .sort((a, b) => a.variant.localeCompare(b.variant));
    return filtered.map((r) => {
      const ratePct = r.differenceRate * 100;
      const ciLowerPct = r.ciLower * 100;
      const ciUpperPct = r.ciUpper * 100;
      return {
        variant: r.variant,
        rate: r.differenceRate,
        ratePct,
        ciLower: r.ciLower,
        ciUpper: r.ciUpper,
        ciLowerPct,
        ciUpperPct,
        errorAsymmetric: [
          ratePct - ciLowerPct,
          ciUpperPct - ratePct,
        ] as [number, number],
        pValue: r.pValue,
        significance: r.significance,
      };
    });
  }, [rows, effectiveModel]);

  const [hoveredIndex, setHoveredIndex] = React.useState<number | null>(null);

  if (loading) {
    return (
      <div
        className={cn(
          "flex h-[320px] items-center justify-center rounded-lg border border-border bg-muted/30 text-muted-foreground",
          className
        )}
      >
        Loading chart…
      </div>
    );
  }

  if (modelOptions.length === 0) {
    return (
      <div
        className={cn(
          "flex h-[320px] items-center justify-center rounded-lg border border-border bg-muted/30 text-muted-foreground",
          className
        )}
      >
        No difference data. Select runs and ensure analysis has been run.
      </div>
    );
  }

  return (
    <div className={cn("space-y-2", className)}>
      {modelOptions.length > 1 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium">Model:</span>
          <select
            value={effectiveModel ?? ""}
            onChange={(e) => onModelChange?.(e.target.value)}
            className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          >
            {modelOptions.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="h-[320px] w-full rounded-lg border border-border bg-card p-2">
        <ResponsiveContainer width="100%" height="100%">
          <RechartsBarChart
            data={chartData}
            margin={{ top: 8, right: 8, bottom: 24, left: 8 }}
            layout="vertical"
          >
            <XAxis
              type="number"
              domain={[0, "auto"]}
              tickFormatter={(v) => `${Number(v).toFixed(0)}%`}
              fontSize={12}
            />
            <YAxis
              type="category"
              dataKey="variant"
              width={120}
              tick={{ fontSize: 11 }}
              tickLine={false}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.[0]?.payload) return null;
                const d = payload[0].payload;
                return (
                  <div className="rounded-md border border-border bg-popover px-3 py-2 text-sm shadow-md">
                    <div className="font-medium">{d.variant}</div>
                    <div>
                      Difference: {(d.rate * 100).toFixed(2)}%
                    </div>
                    <div className="text-muted-foreground">
                      95% CI: [{d.ciLowerPct.toFixed(2)}%, {d.ciUpperPct.toFixed(2)}%]
                    </div>
                    {d.pValue != null && (
                      <div>
                        p = {d.pValue.toFixed(3)}
                        {d.significance ? ` ${d.significance}` : ""}
                      </div>
                    )}
                  </div>
                );
              }}
            />
            <Bar
              dataKey="ratePct"
              name="Difference %"
              fill={BAR_COLOR}
              radius={[0, 4, 4, 0]}
              maxBarSize={32}
              onMouseEnter={(_, index) => setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              {chartData.map((_, index) => (
                <Cell
                  key={index}
                  fill={
                    hoveredIndex === index ? BAR_COLOR_HOVER : BAR_COLOR
                  }
                />
              ))}
              <ErrorBar
                dataKey="errorAsymmetric"
                stroke="var(--foreground)"
                strokeWidth={1.5}
                width={4}
              />
            </Bar>
          </RechartsBarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
