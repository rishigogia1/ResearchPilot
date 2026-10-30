import pytest
from app.agent.evidence_processor import EvidenceProcessor
from app.tools.web_search import SearchResultItem
from app.tools.webpage_reader import ExtractedPage


def test_evidence_processor_normal_flow():
    processor = EvidenceProcessor()

    search_results = [
        SearchResultItem(
            title="Fusion Net Energy Gain",
            url="https://example.org/fusion-gain",
            snippet="NIF lab achieved 3.15 MJ output from 2.05 MJ laser energy.",
            domain="example.org",
        ),
        SearchResultItem(
            title="Tokamak Magnetic Confinement",
            url="https://example.org/tokamak",
            snippet="ITER assembly advances with central solenoid installation.",
            domain="example.org",
        ),
    ]

    extracted_pages = [
        ExtractedPage(
            url="https://example.org/fusion-gain",
            final_url="https://example.org/fusion-gain",
            title="Fusion Net Energy Gain in Inertial Confinement",
            content="Researchers at Lawrence Livermore National Laboratory repeatedly demonstrated ignition with net energy gain.",
            content_length=110,
            http_status=200,
            content_type="text/html",
        )
    ]

    bundle = processor.process(
        query="nuclear fusion energy gain results",
        subquestions=["What net gain was achieved?", "Which facilities demonstrated ignition?"],
        search_results=search_results,
        extracted_pages=extracted_pages,
        max_sources=5,
    )

    assert bundle.is_insufficient is False
    assert len(bundle.sources) == 2
    # Verify source IDs are sequential
    assert bundle.sources[0].source_id == "src-1"
    assert bundle.sources[1].source_id == "src-2"
    # Verify extracted content was used for source 1
    assert "repeatedly demonstrated ignition" in bundle.sources[0].raw_content
    # Verify snippet fallback was used for source 2 (since not in extracted_pages)
    assert "ITER assembly advances" in bundle.sources[1].raw_content
    assert len(bundle.context_text) > 0


def test_evidence_processor_insufficient_evidence():
    processor = EvidenceProcessor()
    # Empty search results
    bundle = processor.process(
        query="obscure query with zero results",
        subquestions=["Subquestion 1"],
        search_results=[],
        extracted_pages=[],
    )

    assert bundle.is_insufficient is True
    assert len(bundle.sources) == 0
    assert len(bundle.limitations) > 0
    assert "No accessible web sources" in bundle.limitations[0]


def test_evidence_processor_filters_noise_content():
    processor = EvidenceProcessor()
    # Content with < MIN_CONTENT_LENGTH
    search_results = [
        SearchResultItem(
            title="Empty Result",
            url="https://example.org/empty",
            snippet="Short",
            domain="example.org",
        )
    ]

    bundle = processor.process(
        query="test query",
        subquestions=["subquestion"],
        search_results=search_results,
        extracted_pages=[],
    )

    assert bundle.is_insufficient is True
    assert len(bundle.sources) == 0
