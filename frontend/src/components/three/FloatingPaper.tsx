"use client";

import type { ReactNode } from "react";

interface FloatingPaperProps {
  children: ReactNode;
  className?: string;
}

export function FloatingPaper({ children, className = "" }: FloatingPaperProps) {
  return <div className={className}>{children}</div>;
}
