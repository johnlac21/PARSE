# PARSE Frontend

Next.js 14 (App Router) application for the PARSE UI: project management, prompt upload, variant configuration, run execution, and analysis views.

## Tech Stack

- **Next.js 14** (App Router), **TypeScript**, **React**
- **Tailwind CSS** for styling
- **shadcn/ui** for components (`components/ui/`)
- **Zustand** for client state (`store/project-store.ts`)
- **API client** in `lib/api-client.ts` (typed methods for all backend endpoints)

## Project Structure

```
src/
├── app/                          # App Router pages and layouts
│   ├── layout.tsx                 # Root layout (providers, toasts)
│   ├── page.tsx                  # Home: project list, create project
│   └── project/[id]/
│       ├── layout.tsx             # Project shell (sidebar, header)
│       ├── page.tsx               # Project overview
│       ├── configure/             # Upload prompts, grammar/typo/dialect, generate variants
│       │   └── page.tsx
│       ├── run/                   # Select model, start run, progress (SSE + 2s polling fallback)
│       │   └── page.tsx
│       └── results/               # Analysis tabs and export
│           └── page.tsx
├── components/
│   ├── ui/                        # shadcn primitives (button, card, tabs, etc.)
│   ├── layout/                    # Sidebar, header
│   ├── upload/                    # CSV/JSONL upload, column mapper
│   ├── variants/                  # Grammar panel, typo panel, dialect panel, variant preview
│   ├── analysis/                  # Analysis tables, charts, export, run selector
│   ├── providers.tsx             # Theme/query providers
│   ├── error-boundary.tsx
│   ├── global-error-toast.tsx
│   └── create-project-dialog.tsx
├── hooks/
│   ├── use-project.tsx           # Load project and runs by id
│   ├── use-keyboard-shortcuts.ts
│   └── use-sse.ts                # SSE subscription (run progress)
├── lib/
│   ├── api-client.ts             # Typed API client (api.createProject, api.runInstability, etc.)
│   ├── types.ts                  # Shared TS types (Project, Run, Prompt, AnalysisResult, etc.)
│   └── utils.ts                  # cn() and helpers
└── store/
    └── project-store.ts          # Zustand store: currentProject, runs, selectedRunIds, etc.
```

## Component Structure

### Layout
- **Sidebar** (`layout/sidebar.tsx`): Navigation links (Overview, Configure, Run, Results).
- **Header** (`layout/header.tsx`): Project title and context.

### Upload & configure
- **csv-upload** / **column-mapper**: File drop, column detection, map columns to `prompt_id`, `prompt_text`, `variant`, metadata.
- **grammar-panel**, **typo-panel**, **dialect-panel**: Select features and options; grammar applicability is auto-scanned on upload and shown at top (“X of N grammar variants apply”; N = 189 grammar features, all with real transforms matching documented examples); optional “Re-scan applicability” link; variant generation via Generate & Continue.
- **variant-preview**: Shows sample variants before generating.

### Analysis
- **run-selector**: Multi-select which runs to include in analysis (completed runs). Results page auto-selects all completed runs when none selected so data loads immediately.
- **summary-cards**: Total prompts, models, variants, completion rate.
- **completeness-table**: Valid/total and valid rate per model per variant; uses `api.runCompleteness`.
- **difference-table**: LPM difference rate, SE, p-value, significance; uses `api.runDifference`; export buttons (LaTeX/CSV/JSON).
- **directional-bias-table**: Mean difference vs baseline, SE, p-value; uses `api.runDirectionalBias`; export buttons.
- **heatmap-chart**: Heatmap of difference/directional/completeness by variant and model.
- **bar-chart** (DifferenceBarChart): Bar chart of difference by variant for a selected model.
- **raw-data-table**: Paginated raw results with filters (run, variant, model); uses `api.getRawResults`.
- **export-buttons**: Shared export UI (table type + format); calls `api.exportResults` and triggers download.

Data flow: Results page loads completeness, difference, and directional bias in parallel when `projectId` or `selectedRunIds` change. Each table receives flattened rows (from `flattenCompleteness`, `flattenDifference`, `flattenDirectionalBias`) and optional `projectId`/`runIds` for export.

## How to Add a New Analysis View

1. **Backend**  
   Add an analysis endpoint (e.g. `POST /api/analysis/my-metric`) that accepts `project_id` and `run_ids` and returns a structure (e.g. per model, per variant). Optionally add export support in `analysis/export.py` and `POST /api/analysis/export` (e.g. new `table_type`).

2. **API client**  
   In `lib/api-client.ts`, add a method that calls the new endpoint, e.g.:
   ```ts
   async runMyMetric(projectId: string, runIds: string[]): Promise<MyMetricResponse> {
     return this.fetch<MyMetricResponse>('/api/analysis/my-metric', {
       method: 'POST',
       body: JSON.stringify({ project_id: projectId, run_ids: runIds }),
     });
   }
   ```
   Add or extend types in `lib/types.ts` for the response.

3. **Flatten helper (optional)**  
   If the response is nested (e.g. `model_id -> variant_id -> { value, se }`), add a small helper (e.g. in the new component file or a shared analysis util) to flatten to rows: `{ model, variant, value, se, ... }` for tables and charts.

4. **Results page state and fetch**  
   In `app/project/[id]/results/page.tsx`:
   - Add state: `const [myMetricData, setMyMetricData] = useState<...>({});` and `myMetricLoading`.
   - In a `useEffect` that depends on `projectId` and `selectedIdsArray`, call `api.runMyMetric(projectId, selectedIdsArray)` and set `myMetricData` / loading.

5. **New tab and component**  
   In the same results page:
   - Add a `<TabsTrigger value="my-metric">My Metric</TabsTrigger>` and `<TabsContent value="my-metric">` with your new component.
   - Create a component (e.g. `components/analysis/my-metric-table.tsx`) that accepts the flattened rows (and optionally `projectId`, `runIds` for export), shows a table or chart, and uses `ExportButtons` if you added export support.

6. **Export (optional)**  
   If you added a new `table_type` for export, use `ExportButtons` with `tableType="my_metric"` and the same `projectId`/`runIds`; ensure the backend returns the correct shape for that table type.

Keeping the pattern (fetch in results page → flatten → pass to table/chart component) keeps analysis views consistent and avoids duplicating run selection logic.
