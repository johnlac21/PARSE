"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import type { DifferenceRow } from "@/components/analysis/difference-table";
import type { DirectionalBiasRow } from "@/components/analysis/directional-bias-table";
import type { CompletenessRow } from "@/components/analysis/completeness-table";

export type HeatmapMetric = "difference" | "directional" | "completeness";

export interface HeatmapChartProps {
  differenceRows: DifferenceRow[];
  directionalRows: DirectionalBiasRow[];
  completenessRows: CompletenessRow[];
  loading?: boolean;
  className?: string;
}

const CELL_SIZE = 44;
const LEGEND_WIDTH = 100;

function interpolateColor(
  t: number,
  low = "#ffffff",
  mid = "#facc15",
  high = "#dc2626"
): string {
  if (!Number.isFinite(t) || t <= 0) return low;
  if (t >= 1) return high;
  if (t <= 0.5) {
    const s = t * 2;
    return blendHex(low, mid, s);
  }
  return blendHex(mid, high, (t - 0.5) * 2);
}

function blendHex(a: string, b: string, t: number): string {
  const parse = (hex: string) => {
    const n = hex.replace("#", "");
    return [n.slice(0, 2), n.slice(2, 4), n.slice(4, 6)].map((x) =>
      parseInt(x, 16)
    );
  };
  const c1 = parse(a);
  const c2 = parse(b);
  const out = c1.map((v, i) =>
    Math.round(v + (c2[i] - v) * t)
  );
  return `#${out.map((x) => x.toString(16).padStart(2, "0")).join("")}`;
}

function getCellValue(
  metric: HeatmapMetric,
  model: string,
  variant: string,
  data: {
    differenceRows: DifferenceRow[];
    directionalRows: DirectionalBiasRow[];
    completenessRows: CompletenessRow[];
  }
): {
  value: number;
  display: string;
  pValue?: number;
  significance?: string;
  extra?: string;
} | null {
  if (metric === "difference") {
    const r = data.differenceRows.find(
      (x) => x.model === model && x.variant === variant
    );
    if (!r) return null;
    return {
      value: r.differenceRate,
      display: r.differenceRate.toFixed(2),
      pValue: r.pValue,
      significance: r.significance,
    };
  }
  if (metric === "directional") {
    const r = data.directionalRows.find(
      (x) => x.model === model && x.variant === variant
    );
    if (!r) return null;
    const magnitude = Math.abs(r.meanDiff);
    return {
      value: magnitude,
      display: r.meanDiff.toFixed(3),
      pValue: r.pValue,
      significance: r.significance,
      extra: `Direction: ${r.direction}`,
    };
  }
  const r = data.completenessRows.find(
    (x) => x.model === model && x.variant === variant
  );
  if (!r) return null;
  return {
    value: r.validRate,
    display: (r.validRate * 100).toFixed(1) + "%",
    extra: `Valid: ${r.valid}/${r.total}`,
  };
}

function getScaleDomain(
  metric: HeatmapMetric,
  values: number[]
): [number, number] {
  const finite = values.filter(Number.isFinite);
  if (finite.length === 0) return [0, 1];
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  if (min === max) return [min, max + 0.01];
  return [min, max];
}

export function HeatmapChart({
  differenceRows,
  directionalRows,
  completenessRows,
  loading,
  className,
}: HeatmapChartProps) {
  const [metric, setMetric] = React.useState<HeatmapMetric>("difference");
  const [hovered, setHovered] = React.useState<{
    model: string;
    variant: string;
    x: number;
    y: number;
  } | null>(null);

  const data = React.useMemo(
    () => ({
      differenceRows,
      directionalRows,
      completenessRows,
    }),
    [differenceRows, directionalRows, completenessRows]
  );

  const { variants, models, valueMap, domain } = React.useMemo(() => {
    const variantSet = new Set<string>();
    const modelSet = new Set<string>();
    const values: number[] = [];

    if (metric === "difference") {
      differenceRows.forEach((r) => {
        variantSet.add(r.variant);
        modelSet.add(r.model);
        values.push(r.differenceRate);
      });
    } else if (metric === "directional") {
      directionalRows.forEach((r) => {
        variantSet.add(r.variant);
        modelSet.add(r.model);
        values.push(Math.abs(r.meanDiff));
      });
    } else {
      completenessRows.forEach((r) => {
        variantSet.add(r.variant);
        modelSet.add(r.model);
        values.push(r.validRate);
      });
    }

    const variants = Array.from(variantSet).sort((a, b) => a.localeCompare(b));
    const models = Array.from(modelSet).sort((a, b) => a.localeCompare(b));

    const valueMap = new Map<string, ReturnType<typeof getCellValue>>();
    variants.forEach((v) => {
      models.forEach((m) => {
        const cell = getCellValue(metric, m, v, data);
        if (cell) valueMap.set(`${m}|${v}`, cell);
      });
    });

    const domain = getScaleDomain(metric, values);
    return { variants, models, valueMap, domain };
  }, [metric, differenceRows, directionalRows, completenessRows, data]);

  const valueToColor = React.useCallback(
    (value: number) => {
      const [min, max] = domain;
      const range = max - min;
      const t = range === 0 ? 0 : (value - min) / range;
      if (metric === "completeness") {
        return interpolateColor(1 - t, "#dc2626", "#facc15", "#ffffff");
      }
      return interpolateColor(t, "#ffffff", "#facc15", "#dc2626");
    },
    [domain, metric]
  );

  const metricLabel = {
    difference: "Difference Rate",
    directional: "Directional Bias (magnitude)",
    completeness: "Completeness Rate",
  };

  if (loading) {
    return (
      <div
        className={cn(
          "flex items-center justify-center rounded-lg border border-border bg-muted/30 p-8 text-muted-foreground",
          className
        )}
      >
        Loading heatmap…
      </div>
    );
  }

  if (variants.length === 0 || models.length === 0) {
    return (
      <div
        className={cn(
          "flex items-center justify-center rounded-lg border border-border bg-muted/30 p-8 text-muted-foreground",
          className
        )}
      >
        No data for heatmap. Select completed runs and ensure analysis data is
        available.
      </div>
    );
  }

  const gridWidth = models.length * CELL_SIZE;
  const gridHeight = variants.length * CELL_SIZE;

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm font-medium">Metric:</span>
        {(["difference", "directional", "completeness"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMetric(m)}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              metric === m
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            )}
          >
            {metricLabel[m]}
          </button>
        ))}
      </div>

      <div
        className="overflow-x-auto overflow-y-auto rounded-lg border border-border bg-card"
        onMouseMove={(e) => {
          if (hovered)
            setHovered((h) =>
              h ? { ...h, x: e.clientX, y: e.clientY } : null
            );
        }}
        onMouseLeave={() => setHovered(null)}
      >
        <div className="inline-flex min-w-0">
          <div
            className="grid gap-px p-px"
            style={{
              gridTemplateRows: `auto repeat(${variants.length}, ${CELL_SIZE}px)`,
              gridTemplateColumns: `auto repeat(${models.length}, ${CELL_SIZE}px)`,
            }}
          >
            {/* Corner */}
            <div className="bg-muted/50" style={{ minWidth: 120, minHeight: 24 }} />
            {/* Column headers */}
            {models.map((m) => (
              <div
                key={m}
                className="flex items-center justify-center truncate bg-muted/50 px-1 py-1 text-xs font-medium"
                style={{ minWidth: CELL_SIZE, minHeight: 24 }}
                title={m}
              >
                <span className="truncate">{m}</span>
              </div>
            ))}
            {/* Rows: variant label + cells */}
            {variants.map((variant, vi) => (
              <React.Fragment key={variant}>
                <div
                  className="flex items-center truncate bg-muted/50 px-2 py-1 text-xs font-medium"
                  style={{ minWidth: 120, minHeight: CELL_SIZE }}
                  title={variant}
                >
                  <span className="truncate">{variant}</span>
                </div>
                {models.map((model) => {
                  const key = `${model}|${variant}`;
                  const cell = valueMap.get(key);
                  const isHovered =
                    hovered?.model === model && hovered?.variant === variant;
                  const color = cell
                    ? valueToColor(cell.value)
                    : "var(--muted)";
                  return (
                    <div
                      key={key}
                      className={cn(
                        "flex items-center justify-center border border-transparent text-xs tabular-nums transition-shadow",
                        isHovered && "ring-2 ring-primary ring-offset-1"
                      )}
                      style={{
                        minWidth: CELL_SIZE,
                        minHeight: CELL_SIZE,
                        backgroundColor: color,
                        color: cell
                          ? (() => {
                              const v = cell.value;
                              if (metric === "completeness")
                                return v > 0.5 ? "#1a1a1a" : "#fff";
                              const [min, max] = domain;
                              const mid = (min + max) / 2;
                              return v > mid ? "#fff" : "#1a1a1a";
                            })()
                          : "var(--muted-foreground)",
                      }}
                      onMouseEnter={(e) =>
                        setHovered({
                          model,
                          variant,
                          x: e.clientX,
                          y: e.clientY,
                        })
                      }
                    >
                      {cell ? cell.display : "—"}
                    </div>
                  );
                })}
              </React.Fragment>
            ))}
          </div>

          {/* Legend */}
          <div
            className="flex flex-col items-center gap-1 border-l border-border bg-muted/30 px-2 py-3"
            style={{ minWidth: LEGEND_WIDTH }}
          >
            <span className="text-xs font-medium">Value</span>
            <div
              className="h-32 w-4 shrink-0 rounded border border-border"
              style={{
                background: `linear-gradient(to top, ${
                  metric === "completeness"
                    ? "#dc2626, #facc15, #ffffff"
                    : "#ffffff, #facc15, #dc2626"
                })`,
              }}
            />
            <div className="flex w-full flex-col text-[10px] text-muted-foreground">
              <span>{domain[1].toFixed(2)}</span>
              <span className="mt-auto">{domain[0].toFixed(2)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tooltip */}
      {hovered && (() => {
        const cell = valueMap.get(`${hovered.model}|${hovered.variant}`);
        if (!cell) return null;
        const left = Math.min(hovered.x + 12, typeof window !== "undefined" ? window.innerWidth - 240 : hovered.x + 12);
        const top = Math.min(hovered.y + 12, typeof window !== "undefined" ? window.innerHeight - 140 : hovered.y + 12);
        return (
          <div
            className="pointer-events-none fixed z-50 max-w-xs rounded-md border border-border bg-popover px-3 py-2 text-sm shadow-md"
            style={{ left, top }}
          >
            <div className="font-medium">Model: {hovered.model}</div>
            <div className="font-medium">Variant: {hovered.variant}</div>
            <div>
              {metric === "difference" && (
                <>
                  Instability: {cell.display}
                  {cell.pValue != null && (
                    <span>, p={cell.pValue.toFixed(3)}{cell.significance ? ` ${cell.significance}` : ""}</span>
                  )}
                </>
              )}
              {metric === "directional" && (
                <>
                  Mean diff: {cell.display}
                  {cell.extra && <span> ({cell.extra})</span>}
                  {cell.pValue != null && (
                    <span>, p={cell.pValue.toFixed(3)}{cell.significance ? ` ${cell.significance}` : ""}</span>
                  )}
                </>
              )}
              {metric === "completeness" && (
                <>
                  Completeness: {cell.display}
                  {cell.extra && <span> ({cell.extra})</span>}
                </>
              )}
            </div>
          </div>
        );
      })()}
    </div>
  );
}
