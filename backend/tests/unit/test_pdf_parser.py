import pytest
import io
from unittest.mock import patch, MagicMock


def test_extract_text_returns_documents():
    mock_pdf_content = b"%PDF-1.4 mock"
    file_like = io.BytesIO(mock_pdf_content)

    with patch("app.services.ingestion.pdf_parser.PdfReader") as mock_reader:
        page = MagicMock()
        page.extract_text.return_value = "Stoic wisdom on page one."
        mock_reader.return_value.pages = [page]

        from app.services.ingestion.pdf_parser import extract_text_from_pdf
        docs = extract_text_from_pdf(file_like, metadata={"tradition": "stoic", "author": "Marcus"})

    assert len(docs) == 1
    assert docs[0].page_content == "Stoic wisdom on page one."
    assert docs[0].metadata["tradition"] == "stoic"
    assert docs[0].metadata["page"] == 1


def test_extract_text_skips_empty_pages():
    file_like = io.BytesIO(b"%PDF mock")
    with patch("app.services.ingestion.pdf_parser.PdfReader") as mock_reader:
        p1, p2 = MagicMock(), MagicMock()
        p1.extract_text.return_value = "Text here."
        p2.extract_text.return_value = "   "  # whitespace only
        mock_reader.return_value.pages = [p1, p2]
        from app.services.ingestion.pdf_parser import extract_text_from_pdf
        docs = extract_text_from_pdf(file_like, metadata={})
    assert len(docs) == 1
