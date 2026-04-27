"use client";

/**
 * Listens for unhandled promise rejections (e.g. API errors) and shows a red toast with the error message.
 */

import { useEffect } from "react";
import { toast } from "sonner";

export function GlobalErrorToast() {
  useEffect(() => {
    const onRejection = (e: PromiseRejectionEvent) => {
      const err = e.reason;
      const message =
        err?.message && typeof err.message === "string"
          ? err.message
          : "An error occurred";
      toast.error(message);
    };
    window.addEventListener("unhandledrejection", onRejection);
    return () => window.removeEventListener("unhandledrejection", onRejection);
  }, []);
  return null;
}
