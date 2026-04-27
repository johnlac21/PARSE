"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const TASK_MODALITY_OPTIONS = [
  { value: "likert", label: "Likert Scale (1-5)" },
  { value: "recommendation_list", label: "Recommendation List" },
  { value: "free_text", label: "Free Text / Open-ended" },
] as const;

interface CreateProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated?: () => void;
}

export function CreateProjectDialog({
  open,
  onOpenChange,
  onCreated,
}: CreateProjectDialogProps) {
  const router = useRouter();
  const [name, setName] = React.useState("");
  const [taskModality, setTaskModality] = React.useState<string>("likert");
  const [creating, setCreating] = React.useState(false);

  const handleCreate = async () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setCreating(true);
    try {
      const project = await api.createProject(trimmed, taskModality);
      onOpenChange(false);
      setName("");
      setTaskModality("likert");
      onCreated?.();
      router.push(`/project/${project.id}/configure`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent showClose={true}>
        <DialogHeader>
          <DialogTitle>New Project</DialogTitle>
          <DialogDescription>
            Create a project and choose the task modality for evaluation.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="project-name">Project Name</Label>
            <Input
              id="project-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My evaluation project"
              required
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="task-modality">Task Modality</Label>
            <Select value={taskModality} onValueChange={setTaskModality}>
              <SelectTrigger id="task-modality">
                <SelectValue placeholder="Select modality" />
              </SelectTrigger>
              <SelectContent>
                {TASK_MODALITY_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={creating}
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreate}
            disabled={creating || !name.trim()}
          >
            {creating ? "Creating…" : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
