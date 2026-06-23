"use client";

import { useRef, useEffect, useState } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface ParticleFieldProps {
  count?: number;
  mouseX: number;
  mouseY: number;
}

function mulberry32(seed: number) {
  return function () {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function generateParticles(count: number) {
  const rng = mulberry32(42);
  const positions = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  const sizes = new Float32Array(count);

  const palette = [
    new THREE.Color("#6366f1"),
    new THREE.Color("#8b5cf6"),
    new THREE.Color("#06b6d4"),
    new THREE.Color("#ec4899"),
    new THREE.Color("#22c55e"),
  ];

  for (let i = 0; i < count; i++) {
    const theta = rng() * Math.PI * 2;
    const phi = Math.acos(2 * rng() - 1);
    const r = 3 + rng() * 12;

    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    positions[i * 3 + 2] = r * Math.cos(phi) - 5;

    const color = palette[Math.floor(rng() * palette.length)];
    colors[i * 3] = color.r;
    colors[i * 3 + 1] = color.g;
    colors[i * 3 + 2] = color.b;

    sizes[i] = rng() * 2.5 + 0.5;
  }

  return { positions, colors, sizes };
}

export function ParticleField({ count = 800, mouseX, mouseY }: ParticleFieldProps) {
  const ref = useRef<THREE.Points>(null);
  const [particleData, setParticleData] = useState<{ positions: Float32Array; colors: Float32Array; sizes: Float32Array }>(() => generateParticles(count));

  useEffect(() => {
    const data = generateParticles(count);
    queueMicrotask(() => setParticleData(data));
  }, [count]);

  useFrame((state) => {
    if (!ref.current || !particleData) return;
    const t = state.clock.elapsedTime;

    ref.current.rotation.y = t * 0.015;
    ref.current.rotation.x = Math.sin(t * 0.01) * 0.1;

    ref.current.rotation.y += mouseX * 0.02;
    ref.current.rotation.x += mouseY * 0.01;

    const sizeAttr = ref.current.geometry.getAttribute("size");
    if (sizeAttr) {
      for (let i = 0; i < count; i++) {
        const base = particleData.sizes[i];
        sizeAttr.array[i] = base + Math.sin(t * 0.5 + i * 0.1) * 0.3;
      }
      sizeAttr.needsUpdate = true;
    }
  });

  if (!particleData) return null;

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[particleData.positions, 3]}
        />
        <bufferAttribute
          attach="attributes-color"
          args={[particleData.colors, 3]}
        />
        <bufferAttribute
          attach="attributes-size"
          args={[particleData.sizes, 1]}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.04}
        vertexColors
        transparent
        opacity={0.6}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
}
