"""
PDF Audit Benchmark
Generates 10 sample papers, measures success rate, render times,
and identifies remaining failures.

Usage:
    python scripts/pdf_audit_benchmark.py
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.pdf_generator import PDFGenerator, _load_katex

SAMPLE_PAPERS = [
    {
        "title": "Deep Learning Approaches for Natural Language Processing",
        "abstract": "This paper surveys recent advances in deep learning for natural language processing tasks including text classification, machine translation, and question answering.",
        "authors": ["Alice Zhang", "Bob Chen"],
        "keywords": ["Deep Learning", "NLP", "Transformer", "Attention"],
        "affiliation": "ResearchOS AI Lab",
        "email": "alice@researchos.ai",
        "sections": [
            {
                "heading": "I. Introduction",
                "content": "Natural language processing has been revolutionized by deep learning techniques. This paper provides a comprehensive survey of recent advances in neural network architectures for NLP tasks including text classification, machine translation, and question answering. We review transformer-based models, attention mechanisms, and pre-training paradigms that have achieved state-of-the-art results across multiple benchmarks.",
                "subsections": []
            },
            {
                "heading": "II. Background",
                "content": "The evolution of NLP has progressed from rule-based systems to statistical methods and finally to deep learning approaches. Early neural models such as recurrent neural networks and long short-term memory networks enabled sequence modeling, but were limited by computational constraints. The introduction of the transformer architecture in 2017 marked a paradigm shift, enabling parallel processing and capturing long-range dependencies.",
                "subsections": [
                    {
                        "heading": "A. Transformer Architecture",
                        "content": "The transformer architecture relies on self-attention mechanisms to process sequences. Multi-head attention allows the model to focus on different representation subspaces, while positional encodings provide sequence order information."
                    }
                ]
            },
            {
                "heading": "III. Methodology",
                "content": "We evaluate several state-of-the-art models on standard NLP benchmarks. Our experimental setup includes pre-trained language models fine-tuned for specific tasks. We measure performance using accuracy, F1 score, and inference time.",
                "subsections": []
            }
        ],
        "references": ["[1] A. Vaswani et al., 'Attention Is All You Need,' NeurIPS 2017.", "[2] J. Devlin et al., 'BERT: Pre-training of Deep Bidirectional Transformers,' NAACL 2019."]
    },
    {
        "title": "Quantum Computing for Optimization Problems",
        "abstract": "This paper explores quantum computing approaches for solving combinatorial optimization problems with applications in logistics and finance.",
        "authors": ["Carol Wang", "David Park"],
        "keywords": ["Quantum Computing", "Optimization", "QAOA", "VQE"],
        "affiliation": "ResearchOS Quantum Lab",
        "email": "carol@researchos.ai",
        "sections": [
            {
                "heading": "I. Introduction",
                "content": "Quantum computing offers theoretical advantages for solving optimization problems that are intractable for classical computers. This paper examines quantum approximate optimization algorithms and variational quantum eigensolvers.",
                "subsections": []
            }
        ],
        "references": ["[1] E. Farhi et al., 'A Quantum Approximate Optimization Algorithm,' arXiv:1411.4028."]
    },
    {
        "title": "Federated Learning for Privacy-Preserving Healthcare Analytics",
        "abstract": "Federated learning enables collaborative model training across healthcare institutions without sharing sensitive patient data.",
        "authors": ["Eve Martinez", "Frank Lee"],
        "keywords": ["Federated Learning", "Privacy", "Healthcare", "Differential Privacy"],
        "affiliation": "ResearchOS Health AI",
        "email": "eve@researchos.ai",
        "sections": [
            {
                "heading": "I. Introduction",
                "content": "Healthcare data is highly sensitive and regulated by privacy laws. Federated learning allows multiple institutions to collaboratively train machine learning models without centrally aggregating patient data.",
                "subsections": []
            }
        ],
        "references": ["[1] B. McMahan et al., 'Communication-Efficient Learning of Deep Networks from Decentralized Data,' AISTATS 2017."]
    },
    {
        "title": "Autonomous Vehicle Perception Systems: A Survey",
        "abstract": "Comprehensive survey of perception systems for autonomous vehicles including object detection, semantic segmentation, and sensor fusion.",
        "authors": ["Grace Kim", "Henry Brown"],
        "keywords": ["Autonomous Vehicles", "Perception", "LIDAR", "Sensor Fusion"],
        "affiliation": "ResearchOS Robotics",
        "email": "grace@researchos.ai",
        "sections": [
            {
                "heading": "I. Introduction",
                "content": "Autonomous vehicles rely on sophisticated perception systems to understand their environment. This survey covers recent advances in object detection, semantic segmentation, and multi-sensor fusion techniques.",
                "subsections": [
                    {
                        "heading": "A. LIDAR-based Detection",
                        "content": "LIDAR sensors provide accurate 3D point cloud data for object detection. Recent approaches use voxel-based and point-based neural networks."
                    }
                ]
            },
            {
                "heading": "II. Sensor Fusion",
                "content": "Combining data from cameras, LIDAR, and radar improves perception robustness. Early fusion, late fusion, and intermediate fusion approaches each offer different trade-offs.",
                "subsections": []
            }
        ],
        "references": ["[1] Y. Wang et al., 'PointPillars: Fast Encoders for Object Detection from Point Clouds,' CVPR 2019."]
    },
    {
        "title": "Reinforcement Learning for Robotic Manipulation",
        "abstract": "This paper presents advances in reinforcement learning algorithms for complex robotic manipulation tasks including grasping and assembly.",
        "authors": ["Ivan Torres", "Julia Adams"],
        "keywords": ["Reinforcement Learning", "Robotics", "Manipulation", "Sim-to-Real"],
        "affiliation": "ResearchOS Robotics",
        "email": "ivan@researchos.ai",
        "sections": [
            {
                "heading": "I. Introduction",
                "content": "Reinforcement learning provides a framework for robots to acquire complex manipulation skills through interaction. This paper surveys recent algorithmic advances.",
                "subsections": []
            }
        ],
        "references": ["[1] S. Levine et al., 'Learning Hand-Eye Coordination for Robotic Grasping with Deep Learning,' ICRA 2016."]
    },
    {
        "title": "Graph Neural Networks for Molecular Property Prediction",
        "abstract": "Applications of graph neural networks for predicting molecular properties with applications in drug discovery and materials science.",
        "authors": ["Kevin Sato", "Lisa Thompson"],
        "keywords": ["Graph Neural Networks", "Molecular Modeling", "Drug Discovery", "Message Passing"],
        "affiliation": "ResearchOS Chemistry AI",
        "email": "kevin@researchos.ai",
        "sections": [
            {
                "heading": "I. Introduction",
                "content": "Predicting molecular properties is fundamental to drug discovery and materials design. Graph neural networks naturally operate on molecular graph structures.",
                "subsections": []
            }
        ],
        "references": ["[1] J. Gilmer et al., 'Neural Message Passing for Quantum Chemistry,' ICML 2017."]
    },
    {
        "title": "Edge Computing for Real-Time Video Analytics",
        "abstract": "This paper explores edge computing architectures for real-time video analytics, including model compression and hardware acceleration.",
        "authors": ["Mike Chen", "Nancy Wilson"],
        "keywords": ["Edge Computing", "Video Analytics", "Model Compression", "Hardware Acceleration"],
        "affiliation": "ResearchOS Systems Lab",
        "email": "mike@researchos.ai",
        "sections": [
            {
                "heading": "I. Introduction",
                "content": "Real-time video analytics requires processing large volumes of visual data with low latency. Edge computing brings computation closer to data sources.",
                "subsections": []
            }
        ],
        "references": ["[1] W. Shi et al., 'Edge Computing: Vision and Challenges,' IEEE Internet of Things Journal 2016."]
    },
    {
        "title": "Generative AI for Code Synthesis",
        "abstract": "Survey of generative AI models for automated code synthesis, including large language models and program synthesis techniques.",
        "authors": ["Omar Hassan", "Patricia Murphy"],
        "keywords": ["Code Generation", "LLM", "Program Synthesis", "Transformer"],
        "affiliation": "ResearchOS AI Lab",
        "email": "omar@researchos.ai",
        "sections": [
            {
                "heading": "I. Introduction",
                "content": "Automated code synthesis has advanced significantly with large language models trained on massive code corpora. This survey covers model architectures, training methods, and evaluation benchmarks.",
                "subsections": []
            }
        ],
        "references": ["[1] M. Chen et al., 'Evaluating Large Language Models Trained on Code,' arXiv:2107.03374."]
    },
    {
        "title": "Blockchain Scalability: Layer-2 Solutions and Sharding",
        "abstract": "Analysis of blockchain scalability solutions including layer-2 protocols, sharding, and consensus mechanism improvements.",
        "authors": ["Quinn Roberts", "Rachel Green"],
        "keywords": ["Blockchain", "Scalability", "Layer-2", "Sharding", "Consensus"],
        "affiliation": "ResearchOS Distributed Systems",
        "email": "quinn@researchos.ai",
        "sections": [
            {
                "heading": "I. Introduction",
                "content": "Blockchain networks face fundamental scalability challenges in transaction throughput and confirmation latency. This paper analyzes layer-2 solutions and sharding approaches.",
                "subsections": []
            }
        ],
        "references": ["[1] J. Poon and T. Dryja, 'The Bitcoin Lightning Network,' 2016."]
    },
    {
        "title": "Neural Radiance Fields for 3D Scene Reconstruction",
        "abstract": "Review of neural radiance field methods for novel view synthesis and 3D scene reconstruction from sparse image inputs.",
        "authors": ["Sam Turner", "Tina Lopez"],
        "keywords": ["NeRF", "3D Reconstruction", "Novel View Synthesis", "Volume Rendering"],
        "affiliation": "ResearchOS Computer Vision",
        "email": "sam@researchos.ai",
        "sections": [
            {
                "heading": "I. Introduction",
                "content": "Neural radiance fields represent scenes as continuous volumetric functions that can be rendered from arbitrary viewpoints. This review covers NeRF variants and applications.",
                "subsections": []
            }
        ],
        "references": ["[1] B. Mildenhall et al., 'NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis,' ECCV 2020."]
    },
]


async def run_benchmark():
    results = []

    katex_css, katex_js, katex_auto = _load_katex()
    katex_ok = bool(katex_css and katex_js and katex_auto)

    for i, paper in enumerate(SAMPLE_PAPERS):
        pdf_bytes = b""
        start = time.monotonic()
        error = None
        try:
            pdf_bytes = await PDFGenerator.compile_paper_to_pdf(
                paper, layout="2 Column", font="Times New Roman"
            )
        except Exception as e:
            error = str(e)

        elapsed = time.monotonic() - start
        success = error is None and len(pdf_bytes) > 0

        results.append({
            "index": i + 1,
            "title": paper["title"][:60],
            "success": success,
            "elapsed_s": round(elapsed, 2),
            "size_bytes": len(pdf_bytes),
            "error": error[:120] if error else None,
        })

        status = "PASS" if success else "FAIL"
        print(f"  [{status}] Paper {i+1:2d}: {paper['title'][:50]:50s} "
              f"{elapsed:6.1f}s  {len(pdf_bytes):>8,} bytes"
              + (f"  ERROR: {error[:80]}" if error else ""))

    successes = sum(1 for r in results if r["success"])
    total = len(results)
    success_rate = (successes / total) * 100
    avg_time = sum(r["elapsed_s"] for r in results) / total if total else 0

    print(f"\n{'='*70}")
    print("  PDF AUDIT RESULTS")
    print(f"{'='*70}")
    print(f"  KaTeX files valid:     {'YES' if katex_ok else 'NO'}")
    print(f"  KaTeX CSS size:        {len(katex_css):>8,} bytes")
    print(f"  KaTeX JS size:         {len(katex_js):>8,} bytes")
    print(f"  KaTeX Auto-Render size:{len(katex_auto):>8,} bytes")
    print()
    print(f"  Total papers generated: {total}")
    print(f"  Successful:             {successes}")
    print(f"  Failed:                 {total - successes}")
    print(f"  Success rate:           {success_rate:.1f}%")
    print(f"  Average render time:    {avg_time:.1f}s")
    print(f"  Min render time:        {min(r['elapsed_s'] for r in results):.1f}s")
    print(f"  Max render time:        {max(r['elapsed_s'] for r in results):.1f}s")
    print(f"  Total render time:      {sum(r['elapsed_s'] for r in results):.1f}s")

    failures = [r for r in results if not r["success"]]
    if failures:
        print("\n  REMAINING FAILURES:")
        for f in failures:
            print(f"    - Paper {f['index']}: {f['title']}")
            print(f"      Error: {f['error']}")

    print(f"\n{'='*70}")
    print("  RECOMMENDATIONS")
    print(f"{'='*70}")
    if not katex_ok:
        print("  - Install KaTeX files in backend/static/katex/")
    if failures:
        print("  - Fix Playwright/Chromium installation for failed papers")
    if success_rate < 95:
        print("  - Improve error handling and fallback chain")
    if avg_time > 30:
        print("  - Reduce PDF render timeout or optimize HTML template")
    print("\n  Target: >95% success rate")
    print(f"  Result: {success_rate:.1f}% {'MET' if success_rate >= 95 else 'NOT MET'}")

    return results, success_rate, katex_ok


async def main():
    print("=" * 70)
    print("  PDF AUDIT BENCHMARK")
    print("  Generating 10 sample papers...")
    print("=" * 70)
    print()

    results, success_rate, katex_ok = await run_benchmark()

    print("\n  Done.")


if __name__ == "__main__":
    asyncio.run(main())
