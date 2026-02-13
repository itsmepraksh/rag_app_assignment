import os
import unittest
from unittest.mock import patch

from langchain_core.documents import Document

from core.rag import RAGManager


class DummySplitter:
    def split_documents(self, docs):
        return docs


class DummyDB:
    def __init__(self):
        self.added_docs = []
        self.saved_path = None

    def add_documents(self, docs):
        self.added_docs.extend(docs)

    def save_local(self, path):
        self.saved_path = path


class TestDocumentProcessingPhase3(unittest.TestCase):
    def setUp(self):
        self.manager = RAGManager.__new__(RAGManager)
        self.manager.text_splitter = DummySplitter()
        self.manager.db = DummyDB()

    def test_build_pdf_documents_merges_text_and_ocr_by_page_metadata(self):
        pdf_path = os.path.abspath("tests/fixtures/sample_scanned_text.pdf")
        with (
            patch.object(
                self.manager,
                "_extract_pdf_text",
                return_value=[
                    {"page_number": 1, "text": "Policy text page one"},
                    {"page_number": 2, "text": ""},
                ],
            ),
            patch.object(
                self.manager,
                "_extract_pdf_images",
                return_value=[{"page_number": 2, "image_number": 1, "name": "scan1", "bytes": b"fake"}],
            ),
            patch.object(
                self.manager,
                "_ocr_images",
                return_value=[{"page_number": 2, "image_number": 1, "name": "scan1", "text": "Scanned OCR text"}],
            ),
        ):
            docs = self.manager._build_pdf_documents(pdf_path)

        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[0].metadata["source_type"], "pdf_text")
        self.assertEqual(docs[0].metadata["page_number"], 1)
        self.assertEqual(docs[1].metadata["source_type"], "pdf_ocr")
        self.assertEqual(docs[1].metadata["page_number"], 2)
        self.assertEqual(docs[1].metadata["filename"], "sample_scanned_text.pdf")
        self.assertTrue(docs[1].metadata["uploaded_at"])

    def test_process_file_supports_md_and_preserves_required_chunk_metadata(self):
        md_path = os.path.abspath("tests/fixtures/sample_notes.md")
        with patch.object(
            self.manager,
            "_build_text_documents",
            return_value=[
                Document(
                    page_content="hello from markdown",
                    metadata={
                        "source": md_path,
                        "filename": "sample_notes.md",
                        "page_number": 1,
                        "uploaded_at": "2026-02-13T00:00:00+00:00",
                        "source_type": "text",
                    },
                )
            ],
        ):
            chunks = self.manager.process_file(md_path)

        self.assertEqual(len(chunks), 1)
        meta = chunks[0].metadata
        self.assertEqual(meta["filename"], "sample_notes.md")
        self.assertEqual(meta["page_number"], 1)
        self.assertEqual(meta["source_type"], "text")
        self.assertIn("uploaded_at", meta)
        self.assertIn("chunk_id", meta)
        self.assertIn(":text:c1", meta["chunk_id"])

    def test_process_pdf_keeps_pdf_text_vs_pdf_ocr_source_types_in_chunks(self):
        pdf_path = os.path.abspath("tests/fixtures/sample_scanned_text.pdf")
        with patch.object(
            self.manager,
            "_build_pdf_documents",
            return_value=[
                Document(
                    page_content="text layer page one",
                    metadata={
                        "source": pdf_path,
                        "filename": "sample_scanned_text.pdf",
                        "page_number": 1,
                        "uploaded_at": "2026-02-13T00:00:00+00:00",
                        "source_type": "pdf_text",
                    },
                ),
                Document(
                    page_content="ocr layer page one",
                    metadata={
                        "source": pdf_path,
                        "filename": "sample_scanned_text.pdf",
                        "page_number": 1,
                        "uploaded_at": "2026-02-13T00:00:00+00:00",
                        "source_type": "pdf_ocr",
                    },
                ),
            ],
        ):
            chunks = self.manager.process_file(pdf_path)

        self.assertEqual(len(chunks), 2)
        source_types = {c.metadata["source_type"] for c in chunks}
        self.assertEqual(source_types, {"pdf_text", "pdf_ocr"})
        self.assertTrue(all("chunk_id" in c.metadata for c in chunks))


if __name__ == "__main__":
    unittest.main()
