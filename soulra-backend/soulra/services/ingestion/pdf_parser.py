from typing import IO
from pypdf import PdfReader
from langchain_core.documents import Document


def extract_text_from_pdf(
    file: IO[bytes],
    metadata: dict,
) -> list[Document]:
    reader = PdfReader(file)
    documents = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            documents.append(
                Document(
                    page_content=text,
                    metadata={**metadata, "page": i},
                )
            )
    return documents
