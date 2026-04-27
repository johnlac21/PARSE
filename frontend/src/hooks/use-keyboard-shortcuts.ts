"use client";

import { useEffect } from "react";

/**
 * Global keyboard shortcuts:
 * - Escape: close topmost modal (handled by Radix Dialog by default)
 * - Cmd/Ctrl+S: optional save callback
 * - Cmd/Ctrl+Enter: optional submit callback
 */
export function useKeyboardShortcuts(options: {
  onSave?: () => void;
  onSubmit?: () => void;
  enabled?: boolean;
}) {
  const { onSave, onSubmit, enabled = true } = options;

  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const isMod = e.metaKey || e.ctrlKey;
      if (isMod && e.key === "s") {
        e.preventDefault();
        onSave?.();
        return;
      }
      if (isMod && e.key === "Enter") {
        e.preventDefault();
        onSubmit?.();
        return;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [enabled, onSave, onSubmit]);
}
