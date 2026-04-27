"use client";

/**
 * Project navigation sidebar.
 * Collapses to hamburger menu on mobile; full sidebar on md+.
 */

import * as React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Upload, Play, BarChart3, ArrowLeft, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface SidebarProps {
  projectId: string;
  currentPath: string;
  projectName?: string;
  className?: string;
}

const navItems = [
  { href: "configure", label: "Upload & Configure", icon: Upload },
  { href: "run", label: "Run Queries", icon: Play },
  { href: "results", label: "Results", icon: BarChart3 },
] as const;

const SIDEBAR_WIDTH = 240;

export function Sidebar({
  projectId,
  currentPath,
  projectName,
  className,
}: SidebarProps) {
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const base = `/project/${projectId}`;

  const navContent = (
    <>
      {projectName && (
        <p
          className="truncate text-sm font-medium text-foreground"
          title={projectName}
        >
          {projectName}
        </p>
      )}
      <nav className="mt-4 flex flex-col gap-0.5">
        {navItems.map(({ href, label, icon: Icon }) => {
          const path = `${base}/${href}`;
          const isActive =
            currentPath === path || currentPath?.startsWith(path + "/");
          return (
            <Link
              key={href}
              href={path}
              onClick={() => setMobileOpen(false)}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "border-l-2 border-primary bg-muted font-medium text-foreground"
                  : "border-l-2 border-transparent text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="truncate">{label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto border-t border-border pt-4">
        <Link
          href="/"
          onClick={() => setMobileOpen(false)}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4 shrink-0" />
          Back to Projects
        </Link>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile: hamburger button */}
      <div className="fixed left-0 top-0 z-50 flex h-14 w-full items-center border-b border-border bg-card px-4 md:hidden">
        <Button
          variant="ghost"
          size="icon"
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
          onClick={() => setMobileOpen((o) => !o)}
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>
        {projectName && (
          <span className="ml-2 truncate text-sm font-medium">{projectName}</span>
        )}
      </div>

      {/* Mobile: overlay when open */}
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close menu"
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar: hidden on mobile unless open; full on md+ */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-40 flex h-screen w-[240px] flex-col border-r border-border bg-card transition-transform duration-200 md:translate-x-0",
          "max-md:translate-x-0 max-md:shadow-lg",
          mobileOpen ? "translate-x-0" : "max-md:-translate-x-full",
          className
        )}
        style={{ paddingTop: "env(safe-area-inset-top, 0)" }}
      >
        <div className="flex flex-col gap-1 p-4 pt-14 md:pt-4 flex-1 min-h-0">
          {navContent}
        </div>
      </aside>
    </>
  );
}
