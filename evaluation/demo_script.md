# ResearchPilot Demo Video Script & Walkthrough

**Target Duration**: 3:30 – 4:30 Minutes  
**Audience**: Technical evaluators, hiring managers, and peer reviewers.

---

## ⏱️ Timeline & Step-by-Step Walkthrough

### Part 1: Project Overview & Motivation (0:00 – 0:35)
* **Visual**: Show the ResearchPilot dashboard in browser (`http://localhost:5173`).
* **Speaker Script**:
  > *"Welcome to ResearchPilot. Traditional AI chatbots frequently hallucinate facts, invent citations, or rely on outdated training cutoffs. ResearchPilot was built as a full-stack, citation-grounded AI research workspace. It autonomously breaks down complex research questions, queries the live web via Tavily, extracts clean article text with HTTPX and BeautifulSoup under strict SSRF protections, and synthesizes answers anchored to verifiable sources."*

---

### Part 2: Architecture & Workflow Overview (0:35 – 1:10)
* **Visual**: Quick overview of the architecture (or Mermaid diagram from README).
* **Speaker Script**:
  > *"The architecture is cleanly decoupled: a FastAPI backend powered by Python 3.13 and Pydantic v2, and a React 19 + TypeScript + Tailwind CSS frontend.
  The agent executes a deterministic 10-step pipeline:
  1. It plans the investigation dynamically.
  2. Executes concurrent searches.
  3. Scrapes and sanitizes web pages with SSRF safeguards.
  4. Deduplicates and scores evidence.
  5. Synthesizes findings with verified citations, discarding any hallucinated references."*

---

### Part 3: Live Query Execution & Report Walkthrough (1:10 – 2:30)
* **Visual**: Click one of the example queries: *"Compare the top three open-source vector databases for RAG applications."* Click **Research**.
* **Visual**: The UI displays the honest loading indicator (`Researching your question...`).
* **Visual**: Report renders. Highlight:
  - **Executive Summary**: Core takeaway displayed prominently.
  - **Agent Strategy & Plan**: Expandable execution steps showing the decomposed sub-queries.
  - **Comparative Table**: Responsive matrix automatically rendered for comparison queries.
  - **Key Findings**: Each finding anchored by citation tags (e.g. `[src-1]`).
  - **Verified Sources**: Click on a citation tag; page scrolls smoothly to the source card displaying publisher domain, title, and link (`target="_blank" rel="noopener noreferrer"`).
* **Speaker Script**:
  > *"Notice that the agent generated an explicit execution plan, rendered a comparative table because this was a comparison query, and attributed every claim to a specific source ID. Clicking any citation brings us directly to the verified source card."*

---

### Part 4: Confidence & Critical Evaluation (2:30 – 3:15)
* **Visual**: Scroll down to Confidence Assessment and Assumptions & Limitations.
* **Speaker Script**:
  > *"ResearchPilot doesn't hide uncertainty. Here, the Confidence Badge rates source reliability as High, Medium, or Low with an explicit qualitative explanation. If data gaps exist, they are surfaced in the Limitations card rather than swept under the rug. We can also click 'Copy as Markdown' to export the complete report to our clipboard."*

---

### Part 5: Error Handling & Resilience (3:15 – 3:55)
* **Visual**: Demonstrate validation and error states:
  1. Type a 1-character query (`"a"`) — show instant client-side validation warning and disabled button.
  2. Show the backend connection indicator in the header. If API keys are unconfigured, show the clear remediation instructions directing the user to edit `backend/.env`.
* **Speaker Script**:
  > *"Resilience is a core requirement. If credentials are missing, or if an upstream search provider times out, ResearchPilot never crashes or exposes Python stack traces. It returns human-readable error banners with exact remediation instructions."*

---

### Part 6: Automated Testing & Conclusion (3:55 – 4:25)
* **Visual**: Open terminal; run `.venv\Scripts\pytest -v` in `backend/` and `npm run build` in `frontend/`.
* **Speaker Script**:
  > *"The backend test suite includes 58 automated unit and integration tests covering SSRF security, citation validation, rate limiting, and failure recovery. The frontend builds cleanly with React 19 and TypeScript. ResearchPilot represents a reliable, source-grounded foundation for autonomous AI research."*

---

## 🛠️ Terminal Commands for Demo Setup

### Terminal 1 — Backend (FastAPI)
```bash
cd "c:\Users\rishi\Desktop\Research Pilot\backend"
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

### Terminal 2 — Frontend (Vite)
```bash
cd "c:\Users\rishi\Desktop\Research Pilot\frontend"
npm run dev
```

### Terminal 3 — Run Automated Verification
```bash
cd "c:\Users\rishi\Desktop\Research Pilot\backend"
.venv\Scripts\pytest -v

cd "c:\Users\rishi\Desktop\Research Pilot\frontend"
npm run build
```
