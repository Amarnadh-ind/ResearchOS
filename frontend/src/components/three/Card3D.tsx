"use client";

import type { ReactNode } from "react";

interface Card3DProps {
  children: ReactNode;
  glowColor?: string;
  intensity?: number;
  className?: string;
}

export function Card3D({ children, className = "" }: Card3DProps) {
  return (
    <div className={`relative ${className}`}>
      {children}
    </div>
  );
}
