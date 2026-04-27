"use client";

/**
 * Horizontal bar at top of content area.
 * Shows breadcrumbs: "Projects > [Project Name] > Configure" with clean separators.
 */

import Link from "next/link";
import { cn } from "@/lib/utils";
import { ChevronRight } from "lucide-react";

export interface HeaderProps {
  projectName: string;
  breadcrumbs: { label: string; href?: string }[];
  className?: string;
}

export function Header({
  projectName,
  breadcrumbs,
  className,
}: HeaderProps) {
  const segments = [
    { label: "Projects", href: "/" },
    { label: projectName },
    ...breadcrumbs,
  ];

  return (
    <header
      className={cn(
        "flex h-14 items-center gap-2 border-b border-border bg-background px-6",
        className
      )}
    >
      {segments.map((item, i) => (
        <span key={i} className="flex items-center gap-2">
          {i > 0 && (
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
          )}
          {item.href ? (
            <Link
              href={item.href}
              className="text-sm font-medium text-muted-foreground hover:text-foreground"
            >
              {item.label}
            </Link>
          ) : (
            <span className="text-sm font-medium text-foreground">
              {item.label}
            </span>
          )}
        </span>
      ))}
    </header>
  );
}
