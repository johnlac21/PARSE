"use client";

import * as React from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Run } from "@/lib/types";

export interface RunSelectorProps {
  runs: Run[];
  selectedRunIds: Set<string>;
  onSelectionChange: (ids: Set<string>) => void;
  className?: string;
}

export function RunSelector({
  runs,
  selectedRunIds,
  onSelectionChange,
  className,
}: RunSelectorProps) {
  const completedRuns = React.useMemo(
    () => runs.filter((r) => r.status === "completed"),
    [runs]
  );

  const toggleRun = (runId: string) => {
    const next = new Set(selectedRunIds);
    if (next.has(runId)) next.delete(runId);
    else next.add(runId);
    onSelectionChange(next);
  };

  const selectAll = () => {
    onSelectionChange(new Set(completedRuns.map((r) => r.id)));
  };

  const deselectAll = () => {
    onSelectionChange(new Set());
  };

  const formatDate = (s: string) => {
    try {
      const d = new Date(s);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return s;
    }
  };

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card p-4 shadow-sm",
        className
      )}
    >
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground">
          Runs to include in analysis
        </h3>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={selectAll}
            disabled={completedRuns.length === 0}
          >
            Select All
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={deselectAll}
            disabled={selectedRunIds.size === 0}
          >
            Deselect All
          </Button>
        </div>
      </div>
      {completedRuns.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No completed runs yet. Run queries from the Run Queries page.
        </p>
      ) : (
        <ul className="max-h-48 space-y-2 overflow-y-auto">
          {completedRuns.map((run) => (
            <li
              key={run.id}
              className="flex items-center gap-3 rounded-md border border-transparent px-2 py-1.5 hover:bg-muted/50"
            >
              <Checkbox
                id={`run-${run.id}`}
                checked={selectedRunIds.has(run.id)}
                onCheckedChange={() => toggleRun(run.id)}
                aria-label={`Select run ${run.model_id}`}
              />
              <label
                htmlFor={`run-${run.id}`}
                className="flex flex-1 cursor-pointer items-center justify-between text-sm"
              >
                <span className="font-medium text-foreground">
                  {run.model_id}
                </span>
                <span className="text-muted-foreground">
                  {formatDate(run.started_at)} · {run.status} · {run.completed_prompts} prompts
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
