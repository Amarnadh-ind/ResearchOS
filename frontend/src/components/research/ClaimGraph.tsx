"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { Network } from "lucide-react";
import type { AgentEvent } from "@/lib/types";
import { AGENT_CONFIG } from "@/lib/types";

interface ClaimGraphProps {
  events: AgentEvent[];
}

interface GraphNode {
  id: string;
  label: string;
  type: "agent" | "claim" | "source";
  color: string;
  x: number;
  y: number;
}

interface GraphEdge {
  from: string;
  to: string;
}

export function ClaimGraph({ events }: ClaimGraphProps) {
  const { nodes, edges } = useMemo(() => {
    const nodes: GraphNode[] = [];
    const edges: GraphEdge[] = [];
    const seenAgents = new Set<string>();

    // Center node
    nodes.push({
      id: "research",
      label: "Research",
      type: "agent",
      color: "var(--color-accent)",
      x: 250,
      y: 200,
    });

    const completedEvents = events.filter((e) => e.type === "completed");

    completedEvents.forEach((event, idx) => {
      if (seenAgents.has(event.agent)) return;
      seenAgents.add(event.agent);

      const config = AGENT_CONFIG[event.agent];
      if (!config) return;

      const angle = (idx / Math.max(completedEvents.length, 1)) * Math.PI * 2 - Math.PI / 2;
      const radius = 140;
      const x = 250 + Math.cos(angle) * radius;
      const y = 200 + Math.sin(angle) * radius;

      nodes.push({
        id: event.agent,
        label: config.label,
        type: "agent",
        color: config.color,
        x,
        y,
      });

      edges.push({ from: "research", to: event.agent });

      // Add data nodes for agents with output data
      const data = event.data || {};
      if (data.results || data.pages || data.claims || data.citations) {
        const countKey = Object.keys(data)[0];
        const count = data[countKey];
        if (typeof count === "number" && count > 0) {
          const dataId = `${event.agent}_data`;
          const dx = 250 + Math.cos(angle) * (radius + 55);
          const dy = 200 + Math.sin(angle) * (radius + 55);

          nodes.push({
            id: dataId,
            label: `${count}`,
            type: "claim",
            color: config.color,
            x: dx,
            y: dy,
          });
          edges.push({ from: event.agent, to: dataId });
        }
      }
    });

    return { nodes, edges };
  }, [events]);

  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-[var(--color-text-muted)] text-sm gap-2">
        <Network className="w-8 h-8 opacity-30" />
        <span>Graph builds as agents complete</span>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full min-h-[400px]">
      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 500 400">
        {/* Edges */}
        {edges.map((edge, i) => {
          const fromNode = nodes.find((n) => n.id === edge.from);
          const toNode = nodes.find((n) => n.id === edge.to);
          if (!fromNode || !toNode) return null;

          return (
            <motion.line
              key={`edge-${i}`}
              x1={fromNode.x}
              y1={fromNode.y}
              x2={toNode.x}
              y2={toNode.y}
              stroke="var(--color-border)"
              strokeWidth="1"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 0.5 }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
            />
          );
        })}

        {/* Nodes */}
        {nodes.map((node, i) => (
          <motion.g
            key={node.id}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.4, delay: i * 0.08 }}
          >
            <circle
              cx={node.x}
              cy={node.y}
              r={node.type === "claim" ? 14 : node.id === "research" ? 24 : 20}
              fill={node.id === "research" ? "var(--color-bg-tertiary)" : "var(--color-bg-card)"}
              stroke={node.color}
              strokeWidth={node.id === "research" ? 2 : 1.5}
            />
            {node.type !== "claim" && (
              <text
                x={node.x}
                y={node.y - 28}
                textAnchor="middle"
                fill={node.color}
                fontSize="9"
                fontFamily="var(--font-sans)"
                fontWeight={500}
              >
                {node.label}
              </text>
            )}
            {node.type === "agent" && node.id !== "research" && (
              <text
                x={node.x}
                y={node.y + 4}
                textAnchor="middle"
                fontSize="12"
              >
                {AGENT_CONFIG[node.id]?.icon || "⚙️"}
              </text>
            )}
            {node.id === "research" && (
              <text x={node.x} y={node.y + 5} textAnchor="middle" fontSize="14">
                🧬
              </text>
            )}
            {node.type === "claim" && (
              <text
                x={node.x}
                y={node.y + 4}
                textAnchor="middle"
                fill="var(--color-text-primary)"
                fontSize="8"
                fontFamily="var(--font-mono)"
              >
                {node.label}
              </text>
            )}
          </motion.g>
        ))}
      </svg>
    </div>
  );
}