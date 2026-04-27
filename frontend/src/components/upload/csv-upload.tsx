"use client";

/**
 * Drag-and-drop CSV/JSONL upload for project prompts.
 * Calls api.uploadPrompts(projectId, file); shows results and preview or column mapping when detection fails.
 */

import * as React from "react";
import { Upload } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { api, apiBaseUrl } from "@/lib/api-client";
import { ColumnMapper, type ColumnMappingResult } from "@/components/upload/column-mapper";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const ACCEPT = ".csv,.jsonl";

export interface CsvUploadProps {
  projectId: string;
  onSuccess: (result: {
    prompts_loaded: number;
    columns_detected: string[];
    sample: Record<string, unknown>[];
  }) => void;
  className?: string;
}

export function CsvUpload({ projectId, onSuccess, className }: CsvUploadProps) {
  const [isDragging, setIsDragging] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [uploading, setUploading] = React.useState(false);
  const [loadingDefault, setLoadingDefault] = React.useState(false);
  const [remapping, setRemapping] = React.useState(false);
  const [file, setFile] = React.useState<File | null>(null);
  const [result, setResult] = React.useState<{
    prompts_loaded: number;
    columns_detected: string[];
    sample: Record<string, unknown>[];
  } | null>(null);
  const [showMapper, setShowMapper] = React.useState(false);

  const busy = uploading || loadingDefault;

  const loadBundled = React.useCallback(
    async () => {
      setError(null);
      setResult(null);
      setShowMapper(false);
      setFile(null);
      setLoadingDefault(true);
      try {
        const res = await api.loadDefaultDataset(projectId, "privacy_bias");
        setResult(res);
        if (res.prompts_loaded > 0) {
          onSuccess(res);
        } else if (res.columns_detected.length > 0) {
          setShowMapper(true);
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Load failed";
        if (msg === "Failed to fetch") {
          const fullMsg = `Could not reach the server at ${apiBaseUrl}. Check: (1) Backend is running (e.g. uvicorn in the backend folder). (2) NEXT_PUBLIC_API_URL in frontend .env is correct. (3) In DevTools → Network, see if the request is blocked or CORS.`;
          setError(fullMsg);
          toast.error(fullMsg);
        } else {
          setError(msg);
          toast.error(msg);
        }
      } finally {
        setLoadingDefault(false);
      }
    },
    [projectId, onSuccess]
  );

  const handleFiles = React.useCallback(
    async (files: FileList | null) => {
      if (!files?.length) return;
      setError(null);
      setResult(null);
      setShowMapper(false);
      const f = files[0];
      const ext = f.name.toLowerCase().split(".").pop();
      if (ext !== "csv" && ext !== "jsonl") {
        setError("Only .csv and .jsonl files are accepted.");
        return;
      }
      setFile(f);
      setUploading(true);
      try {
        const res = await api.uploadPrompts(projectId, f);
        setResult(res);
        if (res.prompts_loaded > 0) {
          onSuccess(res);
        } else if (res.columns_detected.length > 0) {
          setShowMapper(true);
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Upload failed";
        if (msg === "Failed to fetch") {
          const fullMsg = `Could not reach the server at ${apiBaseUrl}. Check: (1) Backend is running (e.g. uvicorn in the backend folder). (2) NEXT_PUBLIC_API_URL in frontend .env is correct. (3) In DevTools → Network, see if the request is blocked or CORS.`;
          setError(fullMsg);
          toast.error(fullMsg);
        } else {
          setError(msg);
          toast.error(msg);
        }
      } finally {
        setUploading(false);
      }
    },
    [projectId, onSuccess]
  );

  const handleMap = React.useCallback(
    async (mapping: ColumnMappingResult) => {
      if (!result) return;
      setError(null);
      setRemapping(true);
      try {
        const res = await api.mapColumnsUpload(projectId, {
          prompt_id_column: mapping.prompt_id_column,
          prompt_text_column: mapping.prompt_text_column,
          variant_column: mapping.variant_column ?? undefined,
          metadata_columns: mapping.metadata_columns,
        });
        setResult(res);
        setShowMapper(false);
        onSuccess(res);
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Re-map failed";
        if (msg === "Failed to fetch") {
          const fullMsg = `Could not reach the server at ${apiBaseUrl}. Check the backend is running and NEXT_PUBLIC_API_URL is correct.`;
          setError(fullMsg);
          toast.error(fullMsg);
        } else {
          setError(msg);
          toast.error(msg);
        }
      } finally {
        setRemapping(false);
      }
    },
    [projectId, result, onSuccess]
  );

  const handleSuccessAck = () => {
    if (result) onSuccess(result);
  };

  // After a successful upload (loaded > 0), show summary and preview; parent may not have called onSuccess yet
  if (result && result.prompts_loaded > 0 && !showMapper) {
    const cols = result.columns_detected;
    const preview = result.sample.slice(0, 5);
    return (
      <div className={cn("space-y-4", className)}>
        <p className="text-sm text-muted-foreground">
          Loaded {result.prompts_loaded} prompts. Columns detected:{" "}
          {cols.join(", ")}
        </p>
        <div className="overflow-x-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                {cols.map((c) => (
                  <TableHead key={c}>{c}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {preview.map((row, i) => (
                <TableRow key={i}>
                  {cols.map((col) => (
                    <TableCell key={col} className="max-w-[200px] truncate">
                      {row[col] != null ? String(row[col]) : "—"}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <p className="text-xs text-muted-foreground">First 5 rows</p>
      </div>
    );
  }

  if (showMapper && result) {
    return (
      <div className={cn("space-y-4", className)}>
        {file && (
          <p className="text-sm text-muted-foreground">
            {file.name} ({(file.size / 1024).toFixed(1)} KB)
          </p>
        )}
        <p className="text-sm text-muted-foreground">
          No prompt text column was detected. Map your columns below.
        </p>
        <ColumnMapper
          columns={result.columns_detected}
          sample={result.sample}
          onMap={handleMap}
        />
        {remapping && (
          <p className="text-sm text-muted-foreground">Re-mapping…</p>
        )}
        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}
      </div>
    );
  }

  // Buttons and "or" come first in DOM order so they are the first focusable / visual upload affordances; dropzone follows.
  return (
    <div className={cn("w-full space-y-4", className)}>
      <div className="mx-auto w-full max-w-2xl space-y-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:justify-center">
          <Button
            type="button"
            variant="default"
            disabled={busy}
            onClick={() => {
              void loadBundled();
            }}
          >
            Load Privacy Bias (200 CI vignettes)
          </Button>
        </div>
        {loadingDefault && (
          <p className="text-center text-sm text-muted-foreground">Loading…</p>
        )}
        <div
          className="flex items-center gap-3"
          aria-hidden="true"
        >
          <div className="h-px flex-1 bg-border" />
          <span className="shrink-0 text-xs text-muted-foreground">or</span>
          <div className="h-px flex-1 bg-border" />
        </div>
      </div>
      <div
        className={cn(
          "flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border bg-muted/30 p-12 transition-colors",
          isDragging && "border-primary bg-muted/50",
        )}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
      >
        <input
          type="file"
          accept={ACCEPT}
          className="hidden"
          id="csv-upload-input"
          onChange={(e) => handleFiles(e.target.files)}
          disabled={busy}
        />
        <label
          htmlFor="csv-upload-input"
          className={cn(
            "flex flex-col items-center gap-2",
            busy ? "cursor-not-allowed opacity-60" : "cursor-pointer",
          )}
        >
          <Upload className="h-10 w-10 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">
            Drop CSV or JSONL file here, or click to browse
          </span>
        </label>
        {file && uploading && (
          <p className="mt-2 text-sm text-muted-foreground">
            {file.name} ({(file.size / 1024).toFixed(1)} KB) — uploading…
          </p>
        )}
        {error && (
          <p className="mt-2 text-sm text-destructive">{error}</p>
        )}
      </div>
    </div>
  );
}
