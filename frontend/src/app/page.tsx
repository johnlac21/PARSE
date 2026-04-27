"use client";

import * as React from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type { Project } from "@/lib/types";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import { CreateProjectDialog } from "@/components/create-project-dialog";
import { ErrorBoundary } from "@/components/error-boundary";
import { Trash2, FolderPlus } from "lucide-react";

const TASK_MODALITY_LABELS: Record<Project["task_modality"], string> = {
  likert: "Likert Scale",
  recommendation_list: "Recommendation List",
  free_text: "Free Text",
};

function HomePageContent() {
  const [projects, setProjects] = React.useState<Project[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = React.useState(false);
  const [deleteTargetId, setDeleteTargetId] = React.useState<string | null>(null);

  const fetchProjects = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await api.getProjects();
      setProjects(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load projects");
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleDeleteConfirm = async () => {
    if (!deleteTargetId) return;
    try {
      await api.deleteProject(deleteTargetId);
      setDeleteTargetId(null);
      await fetchProjects();
    } catch {
      setError("Failed to delete project");
    }
  };

  const deleteTargetProject = projects.find((p) => p.id === deleteTargetId);

  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-900">
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-col gap-6 px-6 py-10 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-neutral-900 sm:text-4xl">
              PARSE Framework
            </h1>
            <p className="mt-1 text-sm text-neutral-500">
              Prompt Alteration Response-Shift Evaluation
            </p>
          </div>
          <Button
            onClick={() => setCreateDialogOpen(true)}
            className="shrink-0"
          >
            New Project
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-10">
        {error && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            {error}
          </div>
        )}
        {loading && (
          <p className="text-sm text-neutral-500">Loading projects…</p>
        )}
        {!loading && projects.length === 0 && !error && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-neutral-300 bg-neutral-50/50 py-16 px-6 text-center">
            <FolderPlus className="h-16 w-16 text-neutral-400 mb-4" aria-hidden />
            <h2 className="text-lg font-medium text-neutral-900">No projects yet</h2>
            <p className="mt-1 max-w-sm text-sm text-neutral-500">
              Create your first project to start evaluating prompts across variants and models.
            </p>
            <Button className="mt-6" onClick={() => setCreateDialogOpen(true)}>
              Create your first project
            </Button>
          </div>
        )}
        {!loading && projects.length > 0 && (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((p) => (
              <Link key={p.id} href={`/project/${p.id}/configure`}>
                <Card className="relative cursor-pointer transition-colors hover:bg-neutral-100/80 hover:border-neutral-300">
                  <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2 pr-10">
                    <CardTitle className="text-base font-semibold leading-tight text-neutral-900">
                      {p.name}
                    </CardTitle>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute right-2 top-2 h-8 w-8 text-neutral-400 hover:bg-red-100 hover:text-red-700"
                      aria-label="Delete project"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setDeleteTargetId(p.id);
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </CardHeader>
                  <CardContent className="space-y-1">
                    <div>
                      <Badge variant="secondary" className="font-normal text-neutral-600">
                        {TASK_MODALITY_LABELS[p.task_modality]}
                      </Badge>
                    </div>
                    <CardDescription className="text-xs text-neutral-500">
                      {formatDate(p.created_at)}
                      {p.prompt_count != null && (
                        <> · {p.prompt_count} prompt{p.prompt_count !== 1 ? "s" : ""}</>
                      )}
                    </CardDescription>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </main>

      <CreateProjectDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onCreated={fetchProjects}
      />

      <Dialog open={!!deleteTargetId} onOpenChange={(open) => !open && setDeleteTargetId(null)}>
        <DialogContent showClose={true}>
          <DialogHeader>
            <DialogTitle>Delete project</DialogTitle>
            <DialogDescription>
              Delete &quot;{deleteTargetProject?.name}&quot;? This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTargetId(null)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function HomePage() {
  return (
    <ErrorBoundary onRetry={() => window.location.reload()}>
      <HomePageContent />
    </ErrorBoundary>
  );
}
