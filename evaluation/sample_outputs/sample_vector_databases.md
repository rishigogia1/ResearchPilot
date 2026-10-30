# Sample Output: Open-Source Vector Databases Comparison

> [!NOTE]
> **Status: Illustrative Sample Output**
> This file demonstrates the structured schema format produced by the ResearchPilot agent pipeline. It is provided for reviewer reference and UI rendering verification.

---

```json
{
  "query": "Compare the top three open-source vector databases (Milvus, Qdrant, Chroma) for RAG applications.",
  "status": "completed",
  "executive_summary": "For RAG workloads, Qdrant offers the most versatile balance with native Rust performance and payload-based filtering; Milvus excels at massive billion-scale distributed deployments; while Chroma provides the simplest zero-config embedded experience for rapid local prototyping.",
  "findings": [
    {
      "heading": "Architectural Design & Scalability",
      "content": "Milvus is architected as a cloud-native, disaggregated distributed system with separate query, index, and data nodes, capable of scaling to billions of vectors [src-1]. Qdrant is written in Rust and uses a monolithic or cluster design with segment-based WAL and native payload filtering [src-2]. Chroma is designed as a developer-friendly embedded database (in-memory with DuckDB/SQLite or client-server) optimal for lightweight developer workflows [src-3].",
      "citations": ["src-1", "src-2", "src-3"]
    },
    {
      "heading": "Indexing Algorithms & Search Performance",
      "content": "Milvus and Qdrant utilize optimized HNSW implementations along with quantization (IVF-PQ, scalar quantization) to minimize memory footprints while preserving >95% recall at sub-10ms latencies [src-1, src-2]. Chroma delegates HNSW indexing to hnswlib, making it performant for sub-million vector spaces but less suited for ultra-high throughput distributed shards [src-3].",
      "citations": ["src-1", "src-2"]
    },
    {
      "heading": "Developer Experience & RAG Integration",
      "content": "Chroma provides native Python bindings and tight integrations with LangChain and LlamaIndex with zero setup, making it the fastest choice for hackathons and local evaluation [src-3]. Qdrant offers strong client libraries in Python, Go, Rust, and TypeScript with built-in hybrid dense-sparse vector search for BM25 combinations [src-2].",
      "citations": ["src-2", "src-3"]
    }
  ],
  "plan": [
    {
      "step_id": 1,
      "description": "Search for vector database architectural comparison benchmarks 2025",
      "search_query": "Milvus Qdrant Chroma vector database comparison benchmark RAG",
      "status": "completed"
    },
    {
      "step_id": 2,
      "description": "Inspect Qdrant payload filtering and performance specs",
      "search_query": "Qdrant vector search HNSW memory payload filtering",
      "status": "completed"
    },
    {
      "step_id": 3,
      "description": "Inspect Milvus distributed scaling architecture",
      "search_query": "Milvus distributed architecture scalability billion vectors",
      "status": "completed"
    }
  ],
  "sources": [
    {
      "source_id": "src-1",
      "url": "https://milvus.io/docs/overview.md",
      "title": "Milvus Architecture and Deployment Overview",
      "domain": "milvus.io",
      "snippet": "Milvus is an open-source vector database built for GenAI and semantic search at enterprise scale.",
      "credibility_note": "Official project documentation"
    },
    {
      "source_id": "src-2",
      "url": "https://qdrant.tech/documentation/overview/",
      "title": "Qdrant Vector Engine Documentation",
      "domain": "qdrant.tech",
      "snippet": "Qdrant is a vector similarity search engine and vector database written in Rust with advanced payload filtering.",
      "credibility_note": "Official project documentation"
    },
    {
      "source_id": "src-3",
      "url": "https://docs.trychroma.com/getting-started",
      "title": "Chroma Getting Started Documentation",
      "domain": "trychroma.com",
      "snippet": "Chroma is the open-source embedding database that makes it easy to build LLM apps with plug-and-play storage.",
      "credibility_note": "Official project documentation"
    }
  ],
  "citations": [
    {
      "citation_id": "cite-1",
      "source_id": "src-1",
      "url": "https://milvus.io/docs/overview.md",
      "source_title": "Milvus Architecture and Deployment Overview",
      "cited_claim": "Milvus disaggregated architecture scales to billions of vectors"
    },
    {
      "citation_id": "cite-2",
      "source_id": "src-2",
      "url": "https://qdrant.tech/documentation/overview/",
      "source_title": "Qdrant Vector Engine Documentation",
      "cited_claim": "Qdrant written in Rust with native payload filtering and hybrid search"
    },
    {
      "citation_id": "cite-3",
      "source_id": "src-3",
      "url": "https://docs.trychroma.com/getting-started",
      "source_title": "Chroma Getting Started Documentation",
      "cited_claim": "Chroma provides embedded developer-friendly RAG storage"
    }
  ],
  "confidence": {
    "score": 0.92,
    "level": "high",
    "explanation": "High confidence based on direct corroboration across official technical documentation and architectural whitepapers.",
    "limitations": [
      "Hardware-specific throughput numbers vary depending on CPU SIMD instruction sets (AVX-512) and GPU acceleration availability."
    ]
  },
  "assumptions": [
    "Workload assumption: Standard retrieval-augmented generation (RAG) with embedding dimensions between 384 and 1536 (e.g. OpenAI text-embedding-3 or BAAI bge)."
  ],
  "limitations": [
    "Cost benchmarks depend heavily on cloud infrastructure hosting models (managed cloud SaaS vs self-hosted Kubernetes)."
  ],
  "suggested_next_steps": [
    "Run in-memory recall benchmarks on your specific embedding dimension and corpus size.",
    "Evaluate hybrid dense-sparse search if exact keyword matching is required alongside semantic similarity."
  ],
  "execution_time_seconds": 4.18,
  "metadata": {
    "sources_evaluated": 3,
    "successful_searches": 3,
    "failed_searches": 0
  }
}
```
