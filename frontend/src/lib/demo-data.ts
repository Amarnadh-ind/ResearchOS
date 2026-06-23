"use client";

import { useResearchStore } from "@/stores/research-store";
import type { AgentEvent, Source, Citation, Paper } from "./types";

const DEMO_PROMPT =
  "A comprehensive study on Vision Transformer architectures for crop disease detection in precision agriculture: CropViT with multi-scale attention mechanisms and transfer learning from ImageNet-21k";

const DEMO_SOURCES: Source[] = [
  {
    url: "https://arxiv.org/abs/2301.08734",
    title: "CropViT: Vision Transformer for Crop Disease Detection",
    snippet:
      "Novel ViT architecture achieving 97.3% accuracy on PlantVillage dataset with multi-scale patch embedding and self-supervised pretraining.",
    relevance_score: 0.98,
  },
  {
    url: "https://doi.org/10.1016/j.compag.2023.108123",
    title: "Deep Learning for Plant Disease Diagnosis: A Comprehensive Survey",
    snippet:
      "Survey of 150+ methods across CNN, ViT, and hybrid architectures for agricultural plant disease identification.",
    relevance_score: 0.95,
  },
  {
    url: "https://ieeexplore.ieee.org/document/10123456",
    title: "Transfer Learning Strategies for Agricultural Image Classification",
    snippet:
      "Analysis of ImageNet pretraining benefits for crop disease classification with limited domain-specific data.",
    relevance_score: 0.92,
  },
  {
    url: "https://www.nature.com/articles/s41586-023-06789-1",
    title: "Multi-Scale Attention for Fine-Grained Plant Pathology",
    snippet:
      "Self-attention mechanism capturing lesion patterns at multiple spatial scales for early-stage disease detection.",
    relevance_score: 0.91,
  },
  {
    url: "https://github.com/cropvit/cropvit-official",
    title: "CropViT Official Repository",
    snippet:
      "Open-source implementation with pretrained weights, training scripts, and evaluation benchmarks for crop disease detection.",
    relevance_score: 0.89,
  },
  {
    url: "https://doi.org/10.1016/j.ai.2023.100456",
    title: "Self-Supervised Pretraining for Agricultural Vision Models",
    snippet:
      "对比学习预训练策略在农业视觉任务中的有效性验证，下游任务性能提升12-18%。",
    relevance_score: 0.87,
  },
  {
    url: "https://arxiv.org/abs/2211.12345",
    title: "Efficient ViT Variants for Edge Deployment in Smart Farming",
    snippet:
      "Lightweight Vision Transformer designs enabling real-time inference on mobile and edge devices in agricultural settings.",
    relevance_score: 0.85,
  },
  {
    url: "https://doi.org/10.1109/TGRS.2023.3287654",
    title: "Hyperspectral + RGB Fusion for Late Blight Detection in Potato",
    snippet:
      "Multi-modal sensor fusion approach combining RGB imagery with hyperspectral data for accurate late blight severity estimation.",
    relevance_score: 0.83,
  },
];

const DEMO_CITATIONS: Citation[] = [
  {
    key: "sharma2023cropvit",
    ieee_format:
      '[1] A. Sharma, R. Patel, and M. Kumar, "CropViT: Vision Transformer for Crop Disease Detection with Multi-Scale Attention," IEEE Trans. Agric. Technol., vol. 15, no. 3, pp. 412-425, 2023.',
    authors: ["A. Sharma", "R. Patel", "M. Kumar"],
    title: "CropViT: Vision Transformer for Crop Disease Detection with Multi-Scale Attention",
    url: "https://arxiv.org/abs/2301.08734",
    year: 2023,
    verified: true,
  },
  {
    key: "wang2023survey",
    ieee_format:
      '[2] L. Wang, J. Chen, and Y. Zhang, "Deep Learning for Plant Disease Diagnosis: A Comprehensive Survey," Comput. Electron. Agric., vol. 210, p. 108123, 2023.',
    authors: ["L. Wang", "J. Chen", "Y. Zhang"],
    title: "Deep Learning for Plant Disease Diagnosis: A Comprehensive Survey",
    url: "https://doi.org/10.1016/j.compag.2023.108123",
    year: 2023,
    verified: true,
  },
  {
    key: "kumar2023transfer",
    ieee_format:
      '[3] V. Kumar, S. Reddy, and P. Singh, "Transfer Learning Strategies for Agricultural Image Classification," IEEE Access, vol. 11, pp. 34567-34580, 2023.',
    authors: ["V. Kumar", "S. Reddy", "P. Singh"],
    title: "Transfer Learning Strategies for Agricultural Image Classification",
    url: "https://ieeexplore.ieee.org/document/10123456",
    year: 2023,
    verified: true,
  },
  {
    key: "zhang2023multiscale",
    ieee_format:
      '[4] H. Zhang, W. Li, and K. Tanaka, "Multi-Scale Attention for Fine-Grained Plant Pathology," Nature, vol. 620, pp. 112-120, 2023.',
    authors: ["H. Zhang", "W. Li", "K. Tanaka"],
    title: "Multi-Scale Attention for Fine-Grained Plant Pathology",
    url: "https://www.nature.com/articles/s41586-023-06789-1",
    year: 2023,
    verified: true,
  },
  {
    key: "patel2023selfsupervised",
    ieee_format:
      '[5] D. Patel and R. Gupta, "Self-Supervised Pretraining for Agricultural Vision Models," Artif. Intell. Agric., vol. 8, pp. 45-58, 2023.',
    authors: ["D. Patel", "R. Gupta"],
    title: "Self-Supervised Pretraining for Agricultural Vision Models",
    url: "https://doi.org/10.1016/j.ai.2023.100456",
    year: 2023,
    verified: true,
  },
  {
    key: "lee2023efficient",
    ieee_format:
      '[6] J. Lee and M. Park, "Efficient ViT Variants for Edge Deployment in Smart Farming," IEEE Internet Things J., vol. 10, no. 18, pp. 16234-16247, 2023.',
    authors: ["J. Lee", "M. Park"],
    title: "Efficient ViT Variants for Edge Deployment in Smart Farming",
    url: "https://arxiv.org/abs/2211.12345",
    year: 2023,
    verified: true,
  },
  {
    key: "garcia2023hyperspectral",
    ieee_format:
      '[7] M. Garcia, A. Rodriguez, and F. Chen, "Hyperspectral and RGB Fusion for Late Blight Detection in Potato," IEEE Trans. Geosci. Remote Sens., vol. 61, pp. 1-15, 2023.',
    authors: ["M. Garcia", "A. Rodriguez", "F. Chen"],
    title: "Hyperspectral and RGB Fusion for Late Blight Detection in Potato",
    url: "https://doi.org/10.1109/TGRS.2023.3287654",
    year: 2023,
    verified: true,
  },
];

const DEMO_PAPER: Paper = {
  title:
    "CropViT: Vision Transformer with Multi-Scale Attention for Crop Disease Detection in Precision Agriculture",
  authors: [
    "Arjun Sharma",
    "Riya Patel",
    "Mohan Kumar",
    "Priya Singh",
  ],
  abstract:
    "Accurate and timely detection of crop diseases is critical for ensuring food security and minimizing agricultural losses. This paper presents CropViT, a novel Vision Transformer architecture specifically designed for crop disease detection that addresses the limitations of existing CNN-based approaches. CropViT introduces a multi-scale patch embedding module that captures disease symptoms at multiple spatial resolutions, combined with a hierarchical self-attention mechanism that models long-range dependencies across leaf regions. We further propose a domain-adaptive pretraining strategy that leverages self-supervised contrastive learning on unlabeled agricultural imagery before fine-tuning on labeled disease datasets. Extensive experiments on the PlantVillage benchmark dataset demonstrate that CropViT achieves 97.3% top-1 accuracy, outperforming state-of-the-art CNN models (EfficientNet-B7: 95.1%, ResNet-152: 93.8%) and vanilla ViT (94.6%) by significant margins. Ablation studies confirm the contribution of each proposed component, with multi-scale attention providing a 2.1% improvement and self-supervised pretraining contributing an additional 1.8% gain. Furthermore, we present CropViT-Lite, a distilled variant optimized for edge deployment on mobile devices, achieving 94.8% accuracy with 8.2x fewer parameters. Our approach demonstrates the potential of transformer architectures for precision agriculture applications.",
  keywords: [
    "Vision Transformer",
    "crop disease detection",
    "precision agriculture",
    "multi-scale attention",
    "transfer learning",
    "plant pathology",
    "deep learning",
  ],
  sections: [
    {
      heading: "I. Introduction",
      content:
        "Agriculture is the backbone of global food production, yet crop diseases continue to pose significant threats to food security worldwide. The Food and Agriculture Organization (FAO) estimates that plant diseases cause annual losses exceeding $220 billion globally [1]. Traditional disease identification relies on manual inspection by trained experts, a process that is labor-intensive, time-consuming, and susceptible to human error, particularly in large-scale farming operations.\n\nRecent advances in deep learning have enabled automated plant disease detection through convolutional neural networks (CNNs). However, CNNs inherently process images through local receptive fields, limiting their ability to capture long-range spatial relationships that are crucial for identifying systemic disease patterns across entire leaf surfaces. Vision Transformers (ViTs), which leverage self-attention mechanisms to model global dependencies, have shown remarkable success in natural image classification [2]. Yet, their direct application to agricultural imagery faces challenges related to limited domain-specific training data and the fine-grained nature of disease symptoms.\n\nThis paper introduces CropViT, a Vision Transformer architecture purpose-built for crop disease detection. Our key contributions include: (1) a multi-scale patch embedding module that captures disease symptoms at multiple spatial resolutions; (2) a hierarchical self-attention mechanism optimized for agricultural imagery; and (3) a domain-adaptive self-supervised pretraining strategy that effectively leverages unlabeled agricultural data. We validate our approach on the PlantVillage dataset, demonstrating state-of-the-art performance across 38 disease classes spanning 14 crop species.",
      subsections: [
        {
          heading: "A. Related Work",
          content:
            "Prior work in automated plant disease detection can be broadly categorized into CNN-based and transformer-based approaches. Mohanty et al. [3] demonstrated the feasibility of deep learning for plant disease classification using AlexNet and GoogLeNet. Subsequent works improved upon this foundation: EfficientNet [4] achieved 95.1% accuracy through compound scaling, while attention-augmented CNNs [5] introduced channel and spatial attention modules.\n\nVision Transformers have recently been applied to agricultural domains. Athanasiou et al. [6] adapted DeiT for plant disease detection but reported only marginal improvements over CNN baselines. Li et al. [7] proposed AgriViT with position-aware patch embedding but did not address the multi-scale nature of disease symptoms. Our work differs fundamentally by introducing a hierarchical attention mechanism specifically designed for the fine-grained spatial patterns characteristic of plant diseases.",
        },
      ],
    },
    {
      heading: "II. Methodology",
      content:
        "CropViT consists of three main components: (1) a multi-scale patch embedding module, (2) a hierarchical transformer encoder, and (3) a classification head with auxiliary loss. Given an input image x of size 224 × 224 × 3, we first extract patches at three scales: 16 × 16 (fine), 32 × 32 (medium), and 64 × 64 (coarse). Each scale produces a sequence of patch embeddings via learnable linear projections.\n\nThe multi-scale patch embedding module addresses a fundamental limitation of standard ViTs: disease symptoms manifest at varying spatial scales, from small lesions spanning a few pixels to large necrotic regions covering entire leaf sections. By operating at multiple scales simultaneously, CropViT captures both fine-grained local details and global structural patterns.\n\nThe hierarchical transformer encoder processes multi-scale embeddings through shared self-attention layers with scale-aware positional encodings. Cross-scale interaction is facilitated through a feature fusion module that aggregates multi-scale representations before the final classification layer. We employ pre-norm transformer blocks with the AdamW optimizer and cosine learning rate scheduling.",
      subsections: [
        {
          heading: "A. Multi-Scale Patch Embedding",
          content:
            "Let {P_f, P_m, P_c} denote patch sequences at fine (16×16), medium (32×32), and coarse (64×64) scales, respectively. Each patch P_i^s is projected via a learned linear layer W_s ∈ R^{d×(s²·3)} to produce embeddings of dimension d = 768. Positional encodings are added to preserve spatial information:\n\nz_i^s = P_i^s · W_s + E_pos^s\n\nwhere E_pos^s ∈ R^{N_s × d} is a scale-specific learnable positional embedding. This design allows the model to learn scale-specific spatial hierarchies while maintaining a unified embedding dimension across scales.",
        },
        {
          heading: "B. Hierarchical Self-Attention",
          content:
            "The multi-scale embeddings are processed through L = 12 transformer layers. At each layer, cross-scale attention is computed as:\n\nAttention(Q, K, V) = softmax(QK^T / √d_k) V\n\nwhere Q, K, V are linear projections of the concatenated multi-scale embeddings. This enables information flow between scales, allowing fine-grained lesion features to inform global disease pattern recognition. The computational complexity remains O(N²d) where N = N_f + N_m + N_c is the total number of patches across all scales.",
        },
      ],
    },
    {
      heading: "III. Experimental Setup",
      content:
        "We evaluate CropViT on the PlantVillage dataset comprising 54,306 images across 38 disease classes for 14 crop species. The dataset is split into 70% training, 15% validation, and 15% test sets with stratified sampling. Data augmentation includes random horizontal/vertical flips, rotation (±15°), color jitter, and random erasing.\n\nWe compare against the following baselines: ResNet-152 [8], EfficientNet-B7 [4], DeiT-Base [9], ViT-Base [10], and AgriViT [7]. All models are trained for 300 epochs with AdamW optimizer (lr = 1e-4, weight decay = 0.05), cosine learning rate schedule, and label smoothing (ε = 0.1). For self-supervised pretraining, we use 100K unlabeled agricultural images collected from open datasets.\n\nEvaluation metrics include top-1 accuracy, top-5 accuracy, F1-score (macro), precision, recall, and computational cost (FLOPs, parameters, inference time). We also report per-class accuracy for critical disease categories.",
      subsections: [],
    },
    {
      heading: "IV. Results and Discussion",
      content:
        "CropViT achieves 97.3% top-1 accuracy on the PlantVillage test set, representing a 2.7% improvement over the best-performing baseline (ViT-Base at 94.6%). The multi-scale attention mechanism contributes 2.1% of this gain, while self-supervised pretraining accounts for an additional 1.8%. CropViT-Lite, optimized for edge deployment, achieves 94.8% accuracy with only 28M parameters (8.2x reduction from CropViT-Base).\n\nPer-class analysis reveals particularly strong performance on diseases with distinctive spatial patterns: Tomato Late Blight (99.1%), Potato Early Blight (98.7%), and Corn Northern Leaf Blight (98.2%). The model shows reduced but still competitive performance on diseases with subtle symptoms: Grape Leaf Blight (93.4%) and Strawberry Leaf Scorch (94.1%).\n\nAblation studies demonstrate the importance of each component: removing multi-scale attention reduces accuracy by 2.1%, removing self-supervised pretraining reduces accuracy by 1.8%, and using standard ViT patch embedding (single scale) reduces accuracy by 3.4%. The combination of all proposed components yields the best performance.",
      subsections: [
        {
          heading: "A. Comparison with State-of-the-Art",
          content:
            "Table I summarizes the performance comparison across all methods. CropViT outperforms all baselines by significant margins while maintaining competitive computational cost. The multi-scale attention adds only 12% additional FLOPs compared to standard ViT, a favorable trade-off given the 2.7% accuracy improvement. CropViT-Lite achieves the best accuracy-efficiency trade-off among all mobile-optimized variants.",
        },
      ],
    },
    {
      heading: "V. Conclusion",
      content:
        "This paper presented CropViT, a Vision Transformer architecture purpose-built for crop disease detection that achieves state-of-the-art performance on the PlantVillage benchmark. The proposed multi-scale patch embedding and hierarchical self-attention mechanism effectively capture disease symptoms at varying spatial resolutions, while domain-adaptive self-supervised pretraining addresses the challenge of limited labeled agricultural data.\n\nOur results demonstrate that transformer architectures, when properly adapted for the agricultural domain, can significantly outperform CNN-based approaches for plant disease classification. The CropViT-Lite variant enables practical deployment on resource-constrained edge devices, opening possibilities for real-time disease detection in precision farming applications.\n\nFuture work will focus on: (1) extending CropViT to multi-modal inputs (RGB + hyperspectral); (2) developing few-shot learning capabilities for emerging disease variants; and (3) integrating temporal modeling for disease progression tracking across growing seasons.",
      subsections: [],
    },
  ],
  references: [
    "[1] FAO, \"The State of the World's Biodiversity for Food and Agriculture,\" Food and Agriculture Organization of the United Nations, 2023.",
    "[2] A. Dosovitskiy et al., \"An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale,\" in Proc. ICLR, 2021.",
    "[3] S. P. Mohanty et al., \"Using Deep Learning for Image-Based Plant Disease Detection,\" Frontiers in Plant Science, vol. 7, 2016.",
    "[4] M. Tan and Q. V. Le, \"EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks,\" in Proc. ICML, 2019.",
    "[5] S. Woo et al., \"CBAM: Convolutional Block Attention Module,\" in Proc. ECCV, 2018.",
    "[6] K. Athanasiou et al., \"Vision Transformers for Plant Disease Detection,\" in Proc. CVPR Workshops, 2022.",
    "[7] Y. Li et al., \"AgriViT: Position-Aware Vision Transformer for Agricultural Image Classification,\" IEEE Trans. Agric. Technol., 2023.",
    "[8] K. He et al., \"Deep Residual Learning for Image Recognition,\" in Proc. CVPR, 2016.",
    "[9] H. Touvron et al., \"Training data-efficient image transformers & distillation through attention,\" in Proc. ICML, 2021.",
    "[10] A. Dosovitskiy et al., \"An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale,\" in Proc. ICLR, 2021.",
  ],
  content_markdown: "",
};

const DEMO_EVENTS: AgentEvent[] = [
  {
    agent: "planner",
    type: "planning_complete",
    data: {
      sub_questions: [
        "What are the current state-of-the-art Vision Transformer architectures for image classification?",
        "How do ViTs compare to CNNs for fine-grained plant disease detection?",
        "What data augmentation and pretraining strategies are effective for limited agricultural datasets?",
        "What are the practical deployment constraints for real-time inference in smart farming?",
      ],
      search_queries: [
        "Vision Transformer crop disease detection 2023",
        "CropViT plant pathology deep learning",
        "multi-scale attention mechanism agricultural imaging",
      ],
      methodology: "Systematic literature review with quantitative benchmark analysis",
      expected_sections: [
        "Introduction",
        "Related Work",
        "Methodology",
        "Experiments",
        "Results",
        "Conclusion",
      ],
      key_concepts: [
        "Vision Transformer",
        "multi-scale attention",
        "crop disease",
        "precision agriculture",
        "transfer learning",
      ],
    },
    timestamp: new Date(Date.now() - 300000).toISOString(),
    session_id: "demo-session-001",
  },
  {
    agent: "search",
    type: "search_complete",
    data: {
      query: "Vision Transformer crop disease detection 2023",
      results_count: 8,
      top_results: [
        { title: "CropViT: Vision Transformer for Crop Disease Detection", url: "https://arxiv.org/abs/2301.08734" },
        { title: "Deep Learning for Plant Disease Diagnosis: A Survey", url: "https://doi.org/10.1016/j.compag.2023.108123" },
      ],
    },
    timestamp: new Date(Date.now() - 280000).toISOString(),
    session_id: "demo-session-001",
  },
  {
    agent: "browser",
    type: "browse_complete",
    data: {
      url: "https://arxiv.org/abs/2301.08734",
      title: "CropViT: Vision Transformer for Crop Disease Detection",
      content_length: 12500,
      extracted_sections: ["Abstract", "Introduction", "Methodology", "Experiments"],
    },
    timestamp: new Date(Date.now() - 240000).toISOString(),
    session_id: "demo-session-001",
  },
  {
    agent: "reader",
    type: "read_complete",
    data: {
      documents_processed: 8,
      key_findings: [
        "CropViT achieves 97.3% accuracy on PlantVillage dataset",
        "Multi-scale attention provides 2.1% improvement over standard ViT",
        "Self-supervised pretraining on unlabeled agricultural data yields 1.8% gain",
        "CropViT-Lite variant achieves 94.8% accuracy with 8.2x fewer parameters",
      ],
      summary: "Comprehensive analysis of 8 research papers on Vision Transformers for agricultural image classification. Key finding: domain-adaptive architectures with multi-scale attention significantly outperform generic ViT models.",
    },
    timestamp: new Date(Date.now() - 200000).toISOString(),
    session_id: "demo-session-001",
  },
  {
    agent: "claim_extractor",
    type: "claims_extracted",
    data: {
      claims: [
        {
          claim: "CropViT achieves 97.3% top-1 accuracy on PlantVillage benchmark",
          evidence: "Experimental results demonstrate consistent superiority over baselines",
          confidence: 0.95,
          source: "sharma2023cropvit",
        },
        {
          claim: "Multi-scale patch embedding captures disease symptoms at multiple spatial resolutions",
          evidence: "Ablation study shows 2.1% accuracy improvement from multi-scale component",
          confidence: 0.92,
          source: "sharma2023cropvit",
        },
        {
          claim: "Self-supervised pretraining on unlabeled agricultural data improves downstream performance by 1.8%",
          evidence: "Comparison of supervised-only vs. self-supervised + fine-tuning approaches",
          confidence: 0.88,
          source: "patel2023selfsupervised",
        },
      ],
      total_claims: 12,
      high_confidence: 8,
    },
    timestamp: new Date(Date.now() - 160000).toISOString(),
    session_id: "demo-session-001",
  },
  {
    agent: "critic",
    type: "critique_complete",
    data: {
      critiques: [
        {
          type: "methodology",
          assessment: "Strong",
          detail: "Rigorous experimental setup with proper train/val/test splits and statistical significance testing",
          suggestions: ["Consider reporting confidence intervals for key metrics"],
        },
        {
          type: "reproducibility",
          assessment: "Good",
          detail: "Hyperparameters and architecture details are clearly specified",
          suggestions: ["Release pretrained model weights and training code"],
        },
      ],
      overall_quality: "high",
      validation_passed: true,
    },
    timestamp: new Date(Date.now() - 120000).toISOString(),
    session_id: "demo-session-001",
  },
  {
    agent: "novelty",
    type: "novelty_complete",
    data: {
      novelty_score: 0.78,
      contributions: [
        "Multi-scale patch embedding for agricultural imagery",
        "Domain-adaptive self-supervised pretraining strategy",
        "CropViT-Lite for edge deployment in smart farming",
      ],
      research_gaps: [
        "Limited exploration of temporal modeling for disease progression",
        "Need for few-shot learning approaches for emerging disease variants",
      ],
    },
    timestamp: new Date(Date.now() - 80000).toISOString(),
    session_id: "demo-session-001",
  },
  {
    agent: "citation",
    type: "citations_complete",
    data: {
      total_citations: 7,
      verified: 7,
      format: "IEEE",
    },
    timestamp: new Date(Date.now() - 60000).toISOString(),
    session_id: "demo-session-001",
  },
  {
    agent: "writer",
    type: "writing_complete",
    data: {
      word_count: 5280,
      sections: 5,
      title: "CropViT: Vision Transformer with Multi-Scale Attention for Crop Disease Detection in Precision Agriculture",
    },
    timestamp: new Date(Date.now() - 30000).toISOString(),
    session_id: "demo-session-001",
  },
  {
    agent: "ieee_formatter",
    type: "formatting_complete",
    data: {
      format: "IEEE",
      columns: 2,
      page_count: 8,
      references_formatted: 10,
    },
    timestamp: new Date(Date.now() - 10000).toISOString(),
    session_id: "demo-session-001",
  },
];

const DEMO_VALIDATION = {
  page_count_achieved: true,
  actual_pages: 8,
  requested_pages: 8,
  topic_relevance_passed: true,
  relevance_score: 0.94,
  sources_met: true,
  actual_sources: 8,
  min_sources: 5,
  citation_coverage_passed: true,
  cited_paragraphs: 12,
  total_paragraphs: 14,
  ieee_formatting_passed: true,
  validation_passed: true,
};

const DEMO_AGENT_TIMINGS: Record<string, { started: number; completed?: number }> = {
  planner: { started: Date.now() - 300000, completed: Date.now() - 280000 },
  search: { started: Date.now() - 280000, completed: Date.now() - 240000 },
  browser: { started: Date.now() - 240000, completed: Date.now() - 200000 },
  reader: { started: Date.now() - 200000, completed: Date.now() - 160000 },
  claim_extractor: { started: Date.now() - 160000, completed: Date.now() - 120000 },
  critic: { started: Date.now() - 120000, completed: Date.now() - 80000 },
  novelty: { started: Date.now() - 80000, completed: Date.now() - 60000 },
  citation: { started: Date.now() - 60000, completed: Date.now() - 30000 },
  writer: { started: Date.now() - 30000, completed: Date.now() - 10000 },
  ieee_formatter: { started: Date.now() - 10000, completed: Date.now() },
};

export function loadDemoData() {
  const store = useResearchStore.getState();

  store.setSessionId("demo-session-001");
  store.setPrompt(DEMO_PROMPT);
  store.setStatus("completed");
  store.setSources(DEMO_SOURCES);
  store.setCitations(DEMO_CITATIONS);
  store.setPaper(DEMO_PAPER);
  store.setValidation(DEMO_VALIDATION);

  // Set agent timings
  const state = useResearchStore.getState();
  const timings = { ...state.agentTimings, ...DEMO_AGENT_TIMINGS };
  useResearchStore.setState({ agentTimings: timings });

  // Set started/completed timestamps
  useResearchStore.setState({
    startedAt: Date.now() - 300000,
    completedAt: Date.now(),
  });

  // Set agents to completed
  store.agents.forEach((agent) => {
    store.updateAgentStatus(agent.agent, "completed");
  });

  // Add events
  DEMO_EVENTS.forEach((event) => {
    store.addEvent(event);
  });

  // Set active panel
  store.setActivePanel("paper");
}

export function clearDemoData() {
  const store = useResearchStore.getState();
  store.reset();
}
