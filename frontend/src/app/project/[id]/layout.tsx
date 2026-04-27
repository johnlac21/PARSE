"use client";

/**
 * Shared layout for all project pages: fetches project + prompts into store on mount,
 * fixed sidebar (240px) + content area with header.
 */

import * as React from "react";
import { useParams, usePathname } from "next/navigation";
import { api } from "@/lib/api-client";
import { useProjectStore } from "@/store/project-store";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ErrorBoundary } from "@/components/error-boundary";

const BREADCRUMB_BY_SEGMENT: Record<string, string> = {
  configure: "Configure",
  run: "Run Queries",
  results: "Results",
};

function ProjectDataLoader({
  projectId,
  children,
}: {
  projectId: string;
  children: React.ReactNode;
}) {
  const {
    setProject,
    setPrompts,
    setPromptCount,
    setSamplePrompts,
    setRuns,
    setProjectLoading,
    setVariantsGenerated,
    setSelectedRuns,
    setActiveRunIds,
  } = useProjectStore();

  React.useEffect(() => {
    setProject(null);
    setPrompts([]);
    setPromptCount(0);
    setSamplePrompts([]);
    setRuns([]);
    setSelectedRuns([]);
    setActiveRunIds([]);
    setVariantsGenerated(false);
    setProjectLoading(true);

    let cancelled = false;
    api
      .getProject(projectId)
      .then((project) => {
        if (cancelled) return;
        useProjectStore.getState().setProject(project);
        return api.getPrompts(projectId);
      })
      .then((result) => {
        if (cancelled || !result) return;
        useProjectStore.getState().setPrompts(result.prompts);
        useProjectStore.getState().setPromptCount(result.total);
        useProjectStore.getState().setSamplePrompts(result.prompts.slice(0, 10));
        return api.getProjectRuns(projectId);
      })
      .then((runs) => {
        if (cancelled) return;
        if (runs) useProjectStore.getState().setRuns(runs);
      })
      .catch(() => {
        if (!cancelled) useProjectStore.getState().setProject(null);
      })
      .finally(() => {
        if (!cancelled) useProjectStore.getState().setProjectLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [projectId, setProject, setPrompts, setPromptCount, setSamplePrompts, setRuns, setProjectLoading, setVariantsGenerated, setSelectedRuns, setActiveRunIds]);

  return <>{children}</>;
}

function ProjectLayoutInner({
  projectId,
  children,
}: {
  projectId: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname() ?? "";
  const project = useProjectStore((s) => s.currentProject);

  const segment = pathname
    .replace(`/project/${projectId}/`, "")
    .split("/")[0];
  const breadcrumbLabel =
    BREADCRUMB_BY_SEGMENT[segment] ?? (segment ? segment : "Project");

  return (
    <div className="flex min-h-screen">
      <Sidebar
        projectId={projectId}
        currentPath={pathname}
        projectName={project?.name}
      />
      <div className="flex flex-1 flex-col min-w-0 md:ml-[240px] pt-14 md:pt-0">
        <Header
          projectName={project?.name ?? "…"}
          breadcrumbs={[{ label: breadcrumbLabel }]}
        />
        <main className="flex-1 p-4 md:p-6 overflow-x-hidden">
          <ErrorBoundary onRetry={() => window.location.reload()}>
            {children}
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}

export default function ProjectLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const projectId = (params?.id as string) ?? null;

  if (!projectId) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-muted-foreground">Project not found.</p>
      </div>
    );
  }

  return (
    <ProjectDataLoader projectId={projectId}>
      <ProjectLayoutInner projectId={projectId}>{children}</ProjectLayoutInner>
    </ProjectDataLoader>
  );
}
