import logging
import re
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse
from pydantic import BaseModel, Field

from app.schemas.research import EvidenceSource
from app.tools.web_search import SearchResultItem
from app.tools.webpage_reader import ExtractedPage

logger = logging.getLogger("researchpilot.agent.evidence")


class ProcessedEvidenceBundle(BaseModel):
    """Cleaned, deduplicated, and budgeted evidence ready for synthesis."""
    sources: List[EvidenceSource] = Field(default_factory=list)
    total_sources_evaluated: int = 0
    retained_sources_count: int = 0
    is_insufficient: bool = False
    context_text: str = ""
    subquestion_evidence_map: Dict[str, List[str]] = Field(default_factory=dict)
    limitations: List[str] = Field(default_factory=list)


class EvidenceProcessor:
    """
    Evidence processing pipeline.
    Combines search engine snippets and page extracts, applies explainable relevance filtering,
    deduplicates sources, preserves citation attribution, and budgets LLM context.
    """

    MIN_CONTENT_LENGTH = 40
    PER_SOURCE_CONTEXT_LIMIT = 2500
    TOTAL_CONTEXT_BUDGET = 14000

    def process(
        self,
        query: str,
        subquestions: List[str],
        search_results: List[SearchResultItem],
        extracted_pages: List[ExtractedPage],
        max_sources: int = 5,
    ) -> ProcessedEvidenceBundle:
        """Process and filter raw web results into clean grounded evidence."""
        logger.info(
            "Processing evidence for query: '%s' (search_results=%d, pages=%d)",
            query,
            len(search_results),
            len(extracted_pages),
        )

        # Index extracted pages by normalized URL
        pages_by_url: Dict[str, ExtractedPage] = {p.url: p for p in extracted_pages}
        for p in extracted_pages:
            if p.final_url:
                pages_by_url[p.final_url] = p

        # Tokenize query words for transparent relevance scoring
        query_words = set(re.findall(r"\b\w{3,}\b", query.lower()))
        subq_words_map = {
            sq: set(re.findall(r"\b\w{3,}\b", sq.lower())) for sq in subquestions
        }

        candidates = []
        seen_urls: Set[str] = set()

        for sr in search_results:
            if not sr.url or sr.url in seen_urls:
                continue
            seen_urls.add(sr.url)

            # Check if we have extracted page content
            page = pages_by_url.get(sr.url)
            page_text = ""
            title = sr.title

            if page and page.content and not page.error:
                page_text = page.content.strip()
                if page.title:
                    title = page.title
            elif sr.snippet:
                # Fallback to search snippet if page extract failed
                page_text = sr.snippet.strip()

            # Filter out empty or noise content
            if len(page_text) < self.MIN_CONTENT_LENGTH:
                continue

            # Transparent relevance heuristic based on query term overlap
            text_lower = (title + " " + page_text).lower()
            matched_terms = [w for w in query_words if w in text_lower]
            relevance_score = len(matched_terms)

            # Map to closest matching subquestion
            best_subq = ""
            best_subq_score = -1
            for sq, words in subq_words_map.items():
                sq_matches = sum(1 for w in words if w in text_lower)
                if sq_matches > best_subq_score:
                    best_subq_score = sq_matches
                    best_subq = sq

            candidates.append({
                "url": sr.url,
                "title": title,
                "domain": sr.domain or urlparse(sr.url).netloc,
                "snippet": sr.snippet or (page_text[:200] + "..."),
                "raw_content": page_text,
                "relevance_score": relevance_score,
                "matched_terms": matched_terms,
                "subquestion": best_subq,
                "published_date": sr.published_date,
            })

        # Sort candidates by relevance score descending
        candidates.sort(key=lambda c: c["relevance_score"], reverse=True)

        # Select top sources within bounded limit
        selected_candidates = candidates[:max_sources]

        # Check for insufficient evidence
        if not selected_candidates:
            logger.warning("No valid evidence remained after filtering for query '%s'", query)
            return ProcessedEvidenceBundle(
                sources=[],
                total_sources_evaluated=len(search_results),
                retained_sources_count=0,
                is_insufficient=True,
                context_text="",
                limitations=["No accessible web sources provided sufficient content on this topic."],
            )

        sources: List[EvidenceSource] = []
        context_blocks: List[str] = []
        subq_evidence_map: Dict[str, List[str]] = {sq: [] for sq in subquestions}
        current_budget = 0

        for idx, cand in enumerate(selected_candidates):
            source_id = f"src-{idx + 1}"
            content_capped = cand["raw_content"][: self.PER_SOURCE_CONTEXT_LIMIT]

            # Enforce total context budget
            if current_budget + len(content_capped) > self.TOTAL_CONTEXT_BUDGET:
                remaining = max(200, self.TOTAL_CONTEXT_BUDGET - current_budget)
                content_capped = content_capped[:remaining] + "\n...[context capped]"

            current_budget += len(content_capped)

            credibility_note = (
                f"Web source ({cand['domain']}). Matched {len(cand['matched_terms'])} query terms. "
                "Content retrieved via direct page inspection."
            )

            source = EvidenceSource(
                source_id=source_id,
                url=cand["url"],
                title=cand["title"],
                domain=cand["domain"],
                snippet=cand["snippet"],
                raw_content=content_capped,
                credibility_note=credibility_note,
            )
            sources.append(source)

            if cand["subquestion"]:
                subq_evidence_map.setdefault(cand["subquestion"], []).append(source_id)

            # Build formatted block for LLM prompt
            block = (
                f"--- SOURCE ID: [{source_id}] ---\n"
                f"TITLE: {cand['title']}\n"
                f"URL: {cand['url']}\n"
                f"DOMAIN: {cand['domain']}\n"
                f"CONTENT:\n{content_capped}\n"
            )
            context_blocks.append(block)

            if current_budget >= self.TOTAL_CONTEXT_BUDGET:
                break

        full_context = "\n\n".join(context_blocks)

        limitations = []
        if len(sources) < 2:
            limitations.append("Only a single source provided extractable evidence on this topic.")
        if any(c["raw_content"] == c["snippet"] for c in selected_candidates):
            limitations.append("Some sources were analyzed using search engine snippets due to page access restrictions.")

        return ProcessedEvidenceBundle(
            sources=sources,
            total_sources_evaluated=len(search_results),
            retained_sources_count=len(sources),
            is_insufficient=False,
            context_text=full_context,
            subquestion_evidence_map=subq_evidence_map,
            limitations=limitations,
        )


evidence_processor = EvidenceProcessor()
