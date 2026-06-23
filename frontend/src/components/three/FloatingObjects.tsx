"use client";

import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface FloatingObjectsProps {
  mouseX: number;
  mouseY: number;
}

interface FloatingShape {
  geometry: "dodecahedron" | "icosahedron" | "torus" | "octahedron" | "tetrahedron" | "torusKnot";
  position: [number, number, number];
  scale: number;
  color: string;
  speed: number;
  rotAxis: [number, number, number];
}

const SHAPES: FloatingShape[] = [
  { geometry: "dodecahedron", position: [-3.5, 1.8, -2], scale: 0.45, color: "#6366f1", speed: 0.15, rotAxis: [1, 0.5, 0] },
  { geometry: "icosahedron", position: [3.8, -1.2, -3], scale: 0.55, color: "#8b5cf6", speed: 0.12, rotAxis: [0, 1, 0.3] },
  { geometry: "torus", position: [-2, -2, -4], scale: 0.35, color: "#06b6d4", speed: 0.18, rotAxis: [0.5, 1, 0] },
  { geometry: "octahedron", position: [4.5, 2.2, -2.5], scale: 0.3, color: "#ec4899", speed: 0.2, rotAxis: [1, 1, 0.5] },
  { geometry: "tetrahedron", position: [-4.2, -0.5, -3.5], scale: 0.28, color: "#22c55e", speed: 0.22, rotAxis: [0, 0.5, 1] },
  { geometry: "torusKnot", position: [1.5, 2.8, -5], scale: 0.22, color: "#f59e0b", speed: 0.1, rotAxis: [0.3, 1, 0.2] },
  { geometry: "dodecahedron", position: [2.5, -2.5, -4.5], scale: 0.18, color: "#14b8a6", speed: 0.25, rotAxis: [1, 0, 1] },
  { geometry: "icosahedron", position: [-1.5, 3.2, -6], scale: 0.4, color: "#6366f1", speed: 0.08, rotAxis: [0.2, 0.8, 1] },
];

function FloatingShape({ shape, mouseX, mouseY }: { shape: FloatingShape; mouseX: number; mouseY: number }) {
  const ref = useRef<THREE.Mesh>(null);
  const initialPos = useMemo(() => new THREE.Vector3(...shape.position), [shape.position]);

  useFrame((state) => {
    if (!ref.current) return;
    const t = state.clock.elapsedTime;

    // Slow rotation
    ref.current.rotation.x += shape.speed * 0.01 * shape.rotAxis[0];
    ref.current.rotation.y += shape.speed * 0.01 * shape.rotAxis[1];
    ref.current.rotation.z += shape.speed * 0.01 * shape.rotAxis[2];

    // Floating bob
    ref.current.position.y = initialPos.y + Math.sin(t * shape.speed + initialPos.x) * 0.3;
    ref.current.position.x = initialPos.x + Math.cos(t * shape.speed * 0.7 + initialPos.y) * 0.15;

    // Subtle mouse parallax
    ref.current.position.x += mouseX * 0.08;
    ref.current.position.y += mouseY * 0.05;
  });

  const geometry = useMemo(() => {
    switch (shape.geometry) {
      case "dodecahedron":
        return <dodecahedronGeometry args={[1, 0]} />;
      case "icosahedron":
        return <icosahedronGeometry args={[1, 0]} />;
      case "torus":
        return <torusGeometry args={[1, 0.4, 16, 32]} />;
      case "octahedron":
        return <octahedronGeometry args={[1, 0]} />;
      case "tetrahedron":
        return <tetrahedronGeometry args={[1, 0]} />;
      case "torusKnot":
        return <torusKnotGeometry args={[0.8, 0.3, 64, 16]} />;
    }
  }, [shape.geometry]);

  return (
    <mesh ref={ref} position={shape.position} scale={shape.scale}>
      {geometry}
      <meshStandardMaterial
        color={shape.color}
        transparent
        opacity={0.35}
        roughness={0.3}
        metalness={0.6}
        wireframe
      />
    </mesh>
  );
}

export function FloatingObjects({ mouseX, mouseY }: FloatingObjectsProps) {
  return (
    <group>
      {SHAPES.map((shape, i) => (
        <FloatingShape key={i} shape={shape} mouseX={mouseX} mouseY={mouseY} />
      ))}
    </group>
  );
}
