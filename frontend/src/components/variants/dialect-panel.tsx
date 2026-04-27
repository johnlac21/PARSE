"use client";

/**
 * Dialect/Language tab content.
 * API key config (browser-only state), dialect multi-select, advanced options, cost estimate.
 */

import * as React from "react";
import { Info, Eye, EyeOff, ChevronDown, ChevronRight, Loader2, Check, X } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SelectGroup,
  SelectLabel,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

// ——— Constants ———

const API_PROVIDERS = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "ollama", label: "Ollama (Local - Free)" },
] as const;

const OPENAI_MODELS = [
  { value: "gpt-4o-mini", label: "gpt-4o-mini (recommended, cheap)" },
  { value: "gpt-4o", label: "gpt-4o" },
];

const ANTHROPIC_MODELS = [
  { value: "claude-3-5-haiku-latest", label: "claude-haiku (recommended)" },
  { value: "claude-sonnet-4-20250514", label: "claude-sonnet" },
];

const OLLAMA_MODELS = [
  { value: "llama3.2", label: "llama3.2" },
  { value: "llama3.1", label: "llama3.1" },
  { value: "mistral", label: "mistral" },
  { value: "phi3", label: "phi3" },
];

type DialectType = "English Dialect" | "Language";

const DIALECT_GROUPS: { group: string; items: { id: string; name: string; type: DialectType }[] }[] = [
  {
    group: "English Varieties",
    items: [
      { id: "aave", name: "AAVE", type: "English Dialect" },
      { id: "gen-z", name: "Gen Z Internet Slang", type: "English Dialect" },
      { id: "indian-english", name: "Indian English", type: "English Dialect" },
      { id: "british-english", name: "British English", type: "English Dialect" },
      { id: "southern-us", name: "Southern US English", type: "English Dialect" },
    ],
  },
  {
    group: "Languages",
    items: [
      { id: "simplified-chinese", name: "Simplified Chinese", type: "Language" },
      { id: "spanish", name: "Spanish", type: "Language" },
      { id: "french", name: "French", type: "Language" },
      { id: "arabic", name: "Arabic", type: "Language" },
      { id: "hindi", name: "Hindi", type: "Language" },
      { id: "japanese", name: "Japanese", type: "Language" },
      { id: "korean", name: "Korean", type: "Language" },
      { id: "portuguese", name: "Portuguese", type: "Language" },
      { id: "german", name: "German", type: "Language" },
    ],
  },
];

const OPENAI_PLACEHOLDER = "sk-...";
const ANTHROPIC_PLACEHOLDER = "sk-ant-...";
const OLLAMA_DEFAULT_BASE = "http://localhost:11434";

// Approximate GPT-4o-mini blended $/1M tokens for cost estimate
const GPT4O_MINI_ESTIMATE_PER_1M = 0.25;

export interface DialectPanelProps {
  /** Number of prompts (for cost estimate). */
  promptCount?: number;
  /** Detected CSV columns (for constrained rewriting parameter columns). */
  parameterColumns?: string[];
  /** Optional callback when dialect selection changes (for parent sync). */
  onSelectionChange?: (selectedIds: string[]) => void;
  className?: string;
}

export function DialectPanel({
  promptCount = 0,
  parameterColumns = [],
  onSelectionChange,
  className,
}: DialectPanelProps) {
  // API config — apiKey never persisted
  const [apiProvider, setApiProvider] = React.useState<string>("openai");
  const [apiKey, setApiKey] = React.useState("");
  const [showApiKey, setShowApiKey] = React.useState(false);
  const [baseUrl, setBaseUrl] = React.useState(OLLAMA_DEFAULT_BASE);
  const [generationModel, setGenerationModel] = React.useState("gpt-4o-mini");
  const [connectionTested, setConnectionTested] = React.useState(false);
  const [connectionSuccess, setConnectionSuccess] = React.useState<boolean | null>(null);
  const [testLoading, setTestLoading] = React.useState(false);

  // Dialect selection
  const [selectedDialects, setSelectedDialects] = React.useState<Set<string>>(new Set());

  // Advanced
  const [advancedOpen, setAdvancedOpen] = React.useState(false);
  const [constrainedRewriting, setConstrainedRewriting] = React.useState(false);
  const [parameterColumnsSelected, setParameterColumnsSelected] = React.useState<string[]>([]);
  const [crossVariants, setCrossVariants] = React.useState(false);

  const isOllama = apiProvider === "ollama";

  // Sync model when provider changes
  React.useEffect(() => {
    if (apiProvider === "openai") setGenerationModel("gpt-4o-mini");
    else if (apiProvider === "anthropic") setGenerationModel("claude-3-5-haiku-latest");
    else if (apiProvider === "ollama") setGenerationModel("llama3.2");
  }, [apiProvider]);

  const currentModels = isOllama
    ? OLLAMA_MODELS
    : apiProvider === "anthropic"
      ? ANTHROPIC_MODELS
      : OPENAI_MODELS;

  const apiKeyPlaceholder = apiProvider === "anthropic" ? ANTHROPIC_PLACEHOLDER : OPENAI_PLACEHOLDER;

  const toggleDialect = React.useCallback((id: string) => {
    setSelectedDialects((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  React.useEffect(() => {
    const ids = Array.from(selectedDialects);
    onSelectionChange?.(ids);
  }, [selectedDialects, onSelectionChange]);

  const toggleParameterColumn = React.useCallback((col: string) => {
    setParameterColumnsSelected((prev) =>
      prev.includes(col) ? prev.filter((c) => c !== col) : [...prev, col]
    );
  }, []);

  const testConnection = React.useCallback(async () => {
    setTestLoading(true);
    setConnectionSuccess(null);
    try {
      if (apiProvider === "ollama") {
        const res = await fetch(`${baseUrl.replace(/\/$/, "")}/api/tags`);
        if (!res.ok) throw new Error("Ollama not reachable");
        setConnectionSuccess(true);
      } else if (apiProvider === "openai") {
        const res = await fetch("https://api.openai.com/v1/models", {
          headers: { Authorization: `Bearer ${apiKey.trim()}` },
        });
        if (!res.ok) throw new Error("Invalid API key or network error");
        setConnectionSuccess(true);
      } else if (apiProvider === "anthropic") {
        const res = await fetch("https://api.anthropic.com/v1/messages", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-api-key": apiKey.trim(),
            "anthropic-version": "2023-06-01",
          },
          body: JSON.stringify({
            model: "claude-3-5-haiku-20241022",
            max_tokens: 1,
            messages: [{ role: "user", content: "Hi" }],
          }),
        });
        if (!res.ok) throw new Error("Invalid API key or network error");
        setConnectionSuccess(true);
      }
      setConnectionTested(true);
    } catch (e) {
      setConnectionSuccess(false);
      setConnectionTested(true);
    } finally {
      setTestLoading(false);
    }
  }, [apiProvider, apiKey, baseUrl]);

  // Cost estimate
  const dialectCount = selectedDialects.size;
  const passes = 2;
  const tokensPerPass = 500;
  const estimatedTokens = promptCount * dialectCount * passes * tokensPerPass;
  const estimatedCost =
    isOllama ? null : (estimatedTokens / 1_000_000) * GPT4O_MINI_ESTIMATE_PER_1M;

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      {/* 1. Info Banner */}
      <div
        role="alert"
        className="flex gap-3 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-200"
      >
        <Info className="h-5 w-5 shrink-0 text-blue-600 dark:text-blue-400" />
        <p>
          Dialect and language variants require LLM API calls for generation. You&apos;ll need to
          provide an API key. Your key is stored in your browser only and never saved to our
          servers.
        </p>
      </div>

      {/* 2. API Key Configuration */}
      <div className="space-y-4 rounded-lg border border-border bg-card p-4">
        <div className="space-y-2">
          <Label className="text-sm font-medium">Provider</Label>
          <Select value={apiProvider} onValueChange={setApiProvider}>
            <SelectTrigger className="w-full max-w-xs">
              <SelectValue placeholder="Select provider" />
            </SelectTrigger>
            <SelectContent>
              {API_PROVIDERS.map((p) => (
                <SelectItem key={p.value} value={p.value}>
                  {p.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {isOllama ? (
          <div className="space-y-2">
            <Label className="text-sm font-medium">Ollama base URL</Label>
            <Input
              type="url"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder={OLLAMA_DEFAULT_BASE}
              className="font-mono"
            />
          </div>
        ) : (
          <div className="space-y-2">
            <Label className="text-sm font-medium">API Key</Label>
            <div className="relative max-w-md">
              <Input
                type={showApiKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={apiKeyPlaceholder}
                className="pr-10 font-mono"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-0 top-0 h-full px-3"
                onClick={() => setShowApiKey((v) => !v)}
                aria-label={showApiKey ? "Hide API key" : "Show API key"}
              >
                {showApiKey ? (
                  <EyeOff className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <Eye className="h-4 w-4 text-muted-foreground" />
                )}
              </Button>
            </div>
          </div>
        )}

        <div className="space-y-2">
          <Label className="text-sm font-medium">Model for generation</Label>
          <Select value={generationModel} onValueChange={setGenerationModel}>
            <SelectTrigger className="w-full max-w-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectLabel>
                  {apiProvider === "openai"
                    ? "OpenAI"
                    : apiProvider === "anthropic"
                      ? "Anthropic"
                      : "Ollama"}
                </SelectLabel>
                {currentModels.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </div>

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={testConnection}
          disabled={
            testLoading ||
            (isOllama ? !baseUrl.trim() : !apiKey.trim())
          }
        >
          {testLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Testing…
            </>
          ) : (
            "Test Connection"
          )}
        </Button>
        {connectionTested && connectionSuccess !== null && (
          <div className="flex items-center gap-2 text-sm">
            {connectionSuccess ? (
              <>
                <Check className="h-4 w-4 text-green-600 dark:text-green-400" />
                <span className="text-green-700 dark:text-green-300">Connection successful</span>
              </>
            ) : (
              <>
                <X className="h-4 w-4 text-red-600 dark:text-red-400" />
                <span className="text-red-700 dark:text-red-300">Connection failed</span>
              </>
            )}
          </div>
        )}
      </div>

      {/* 3. Dialect/Language Selection */}
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="px-4 py-2 border-b border-border bg-muted/30">
          <span className="text-sm font-medium">Dialect / Language</span>
          <p className="text-xs text-muted-foreground mt-0.5">
            Select one or more variants to generate
          </p>
        </div>
        <div className="max-h-[320px] overflow-y-auto bg-card">
          {DIALECT_GROUPS.map(({ group, items }) => (
            <div key={group}>
              <div className="sticky top-0 bg-muted/50 px-4 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide border-b border-border">
                {group}
              </div>
              {items.map((item) => (
                <label
                  key={item.id}
                  className={cn(
                    "flex items-center gap-3 border-b border-border p-3 last:border-b-0 cursor-pointer hover:bg-muted/30 transition-colors"
                  )}
                >
                  <input
                    type="checkbox"
                    checked={selectedDialects.has(item.id)}
                    onChange={() => toggleDialect(item.id)}
                    className="h-4 w-4 rounded border-input text-primary focus:ring-2 focus:ring-ring focus:ring-offset-2"
                  />
                  <span className="font-medium text-sm">{item.name}</span>
                  <Badge variant="secondary" className="text-xs">
                    {item.type}
                  </Badge>
                </label>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* 4. Advanced Options (collapsible) */}
      <div className="rounded-lg border border-border overflow-hidden bg-card">
        <button
          type="button"
          className="flex w-full items-center gap-2 px-4 py-3 text-left text-sm font-medium hover:bg-muted/50 transition-colors"
          onClick={() => setAdvancedOpen((o) => !o)}
          aria-expanded={advancedOpen}
        >
          {advancedOpen ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
          Advanced options
        </button>
        {advancedOpen && (
          <div className="border-t border-border px-4 py-3 space-y-4">
            <div className="flex items-center justify-between gap-4">
              <Label htmlFor="constrained-rewriting" className="text-sm font-medium cursor-pointer">
                Constrained Rewriting (for CI-style prompts)
              </Label>
              <Switch
                id="constrained-rewriting"
                checked={constrainedRewriting}
                onCheckedChange={setConstrainedRewriting}
              />
            </div>
            {constrainedRewriting && parameterColumns.length > 0 && (
              <div className="space-y-2 pl-1">
                <Label className="text-xs text-muted-foreground">
                  Parameter columns to translate separately
                </Label>
                <div className="flex flex-wrap gap-2">
                  {parameterColumns.map((col) => (
                    <label
                      key={col}
                      className="flex items-center gap-2 rounded-md border border-border px-2 py-1.5 text-sm cursor-pointer hover:bg-muted/50"
                    >
                      <input
                        type="checkbox"
                        checked={parameterColumnsSelected.includes(col)}
                        onChange={() => toggleParameterColumn(col)}
                        className="h-3.5 w-3.5 rounded border-input text-primary"
                      />
                      <span>{col}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
            {constrainedRewriting && parameterColumns.length === 0 && (
              <p className="text-xs text-muted-foreground pl-1">
                Upload a CSV to see detected columns for parameter translation.
              </p>
            )}
            <div className="flex items-center justify-between gap-4">
              <Label htmlFor="cross-variants" className="text-sm font-medium cursor-pointer">
                Also generate Dialect + Typo cross-variants
              </Label>
              <Switch
                id="cross-variants"
                checked={crossVariants}
                onCheckedChange={setCrossVariants}
              />
            </div>
          </div>
        )}
      </div>

      {/* 5. Cost Estimate */}
      {dialectCount > 0 && (
        <div className="rounded-lg border border-border bg-card p-4 space-y-1">
          <p className="text-sm text-muted-foreground">
            {promptCount} prompts × {dialectCount} dialect{dialectCount !== 1 ? "s" : ""} × 2 passes
            × ~500 tokens ≈ {estimatedTokens.toLocaleString()} tokens
          </p>
          {isOllama ? (
            <p className="text-sm font-medium text-green-700 dark:text-green-300">
              Estimated cost: Free (local processing)
            </p>
          ) : (
            <p className="text-sm font-medium">
              Estimated cost: ~${(estimatedCost ?? 0).toFixed(2)} (using GPT-4o-mini pricing)
            </p>
          )}
        </div>
      )}
    </div>
  );
}
