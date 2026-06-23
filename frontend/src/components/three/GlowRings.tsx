"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface GlowRingProps {
  radius: number;
  color: string;
  speed: number;
  tilt?: number;
  thickness?: number;
  mouseX: number;
  mouseY: number;
}

function GlowRing({ radius, color, speed, tilt = 0, thickness = 0.008, mouseX, mouseY }: GlowRingProps) {
  const ref = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (!ref.current) return;
    const t = state.clock.elapsedTime;
    ref.current.rotation.z = t * speed;
    ref.current.rotation.x = tilt + mouseX * 0.03;
    ref.current.rotation.y = mouseY * 0.02;
  });

  return (
    <mesh ref={ref}>
      <torusGeometry args={[radius, thickness, 32, 128]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={0.2}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </mesh>
  );
}

export function GlowRings({ mouseX, mouseY }: { mouseX: number; mouseY: number }) {
  return (
    <group position={[0, 0, -3]}>
      <GlowRing radius={2.5} color="#6366f1" speed={0.08} tilt={0.3} mouseX={mouseX} mouseY={mouseY} />
      <GlowRing radius={3.2} color="#8b5cf6" speed={-0.05} tilt={0.6} thickness={0.005} mouseX={mouseX} mouseY={mouseY} />
      <GlowRing radius={4.0} color="#06b6d4" speed={0.03} tilt={0.8} thickness={0.004} mouseX={mouseX} mouseY={mouseY} />
      <GlowRing radius={1.8} color="#ec4899" speed={-0.12} tilt={1.1} thickness={0.006} mouseX={mouseX} mouseY={mouseY} />
    </group>
  );
}
