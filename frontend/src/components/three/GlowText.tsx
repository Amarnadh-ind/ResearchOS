"use client";

import type { ReactNode } from "react";

interface GlowTextProps {
  children: ReactNode;
  color?: string;
  className?: string;
}

export function GlowText({ children, className = "" }: GlowTextProps) {
  return <span className={`gradient-text ${className}`}>{children}</span>;
}
