# ResearchPilot Evaluation Scoring Rubric

This rubric establishes a rigorous, quantitative 100-point framework for assessing AI research agent performance. 

> [!NOTE]
> This rubric defines the evaluation methodology and standard for assessing ResearchPilot runs. It serves as an objective grading guide for reviewers, not a claim that any untested run has achieved a specific score.

---

## 🎯 100-Point Scoring Breakdown

| Dimension | Points | Description & Criteria |
| :--- | :---: | :--- |
| **1. Factual Grounding & Correctness** | **25** | • Claims directly reflect evidence extracted from live web sources.<br/>• No hallucinated statistics, dates, benchmark numbers, or entities.<br/>• When facts differ across sources, conflicting views are reported.<br/>• 0 points if critical facts or numbers are fabricated. |
| **2. Source Quality & Citation Accuracy** | **20** | • Citations strictly point to sources collected during the actual run.<br/>• No phantom citation IDs or broken links.<br/>• Source domains are reputable and relevant to the domain.<br/>• Links open securely in new tabs with `rel="noopener noreferrer"`. |
| **3. Research Completeness** | **15** | • Addresses all facets of the user's research objective.<br/>• Includes structured executive summary and substantive thematic findings.<br/>• When comparison is requested, renders a clear comparative breakdown.<br/>• Surfaces meaningful next steps and follow-up topics. |
| **4. Planning & Orchestration** | **15** | • Query decomposition yields targeted, high-yield search keywords.<br/>• Subquestions logically partition the investigation scope.<br/>• Plan is generated dynamically (not hardcoded static templates).<br/>• Server-side query, source, and timeout limits are enforced. |
| **5. Reliability & Failure Handling** | **15** | • Sanitized error handling for missing credentials (503), timeouts (504), and upstream outages (502).<br/>• Partial tool failures continue without crashing the workflow.<br/>• Insufficient evidence is honestly identified without inventing answers.<br/>• SSRF defenses block private networks, localhost, and metadata IPs. |
| **6. Output Structure & Usability** | **10** | • Professional light-themed workspace typography and hierarchy.<br/>• Clear visual confidence rating (High / Medium / Low).<br/>• Export to Markdown feature works cleanly.<br/>• Responsive on mobile, tablet, and desktop without horizontal scroll. |

---

## 🏆 Grading Thresholds

* **Exemplary (90 - 100 points)**: Flawless factual alignment with sources; comprehensive subquestion coverage; robust citation anchoring; resilient error recovery; clean presentation.
* **Proficient (75 - 89 points)**: Substantive and grounded answer; minor omissions in secondary subquestions; valid citations; safe error handling.
* **Passing Threshold (70 points)**: Core research question answered accurately with verified sources; no fabricated claims; handles basic errors safely.
* **Unsatisfactory (< 70 points)**: Hallucinated citations or facts; unhandled crashes on provider errors; unresponsive or ungrounded synthesis.
