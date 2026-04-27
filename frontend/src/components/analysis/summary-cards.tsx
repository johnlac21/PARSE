"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileText, Cpu, GitBranch, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SummaryStat {
  label: string;
  value: string | number;
  sub?: string;
}

export interface SummaryCardsProps {
  stats: SummaryStat[];
  className?: string;
}

const ICON_MAP = {
  FileText,
  Cpu,
  GitBranch,
  CheckCircle,
} as const;

export function SummaryCards({ stats, className }: SummaryCardsProps) {
  const icons: (keyof typeof ICON_MAP)[] = [
    "FileText",
    "Cpu",
    "GitBranch",
    "CheckCircle",
  ];
  return (
    <div className={cn("grid gap-4 md:grid-cols-2 lg:grid-cols-4", className)}>
      {stats.map((s, i) => {
        const Icon = icons[i] ? ICON_MAP[icons[i]] : FileText;
        return (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{s.label}</CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-mono font-bold">{s.value}</div>
              {s.sub && (
                <p className="text-xs text-muted-foreground">{s.sub}</p>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
