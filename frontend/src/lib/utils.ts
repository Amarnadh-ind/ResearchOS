import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatTimestamp(ts: string): string {
  const date = new Date(ts);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen - 3) + "...";
}

/**
 * Preview helper — returns a short preview of text for activity display.
 * Full content is kept in backend and available via Sources/Paper/Diagnostics tabs.
 */
export function preview(text: string | undefined | null, limit: number = 250): string {
  if (!text) return "";
  return text.length > limit ? text.slice(0, limit) + "..." : text;
}

