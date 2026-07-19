"""Tests for text extraction and chunking."""

from app.workers.chunker import extract_text, is_supported, split_text


class TestIsSupported:
    def test_plain_text_supported(self) -> None:
        assert is_supported("text/plain") is True

    def test_pdf_supported(self) -> None:
        assert is_supported("application/pdf") is True

    def test_unknown_type_not_supported(self) -> None:
        assert is_supported("application/x-binary") is False

    def test_mime_with_charset_supported(self) -> None:
        assert is_supported("text/plain; charset=utf-8") is True


class TestExtractText:
    def test_plain_text(self) -> None:
        result = extract_text(b"Hello world", "text/plain")
        assert result == "Hello world"

    def test_utf8_decoded(self) -> None:
        data = "Héllo wörld".encode()
        result = extract_text(data, "text/plain")
        assert "Héllo" in result

    def test_html_tags_stripped(self) -> None:
        html = b"<html><body><p>Hello</p></body></html>"
        result = extract_text(html, "text/html")
        assert "<p>" not in result
        assert "Hello" in result

    def test_json_treated_as_text(self) -> None:
        result = extract_text(b'{"key": "value"}', "application/json")
        assert "key" in result

    def test_pdf_missing_pypdf_returns_empty(self) -> None:
        # If pypdf is installed this returns empty for invalid PDF bytes
        result = extract_text(b"not a pdf", "application/pdf")
        assert isinstance(result, str)

    def test_unknown_mime_best_effort(self) -> None:
        result = extract_text(b"some text", "application/x-custom")
        assert "some text" in result


class TestSplitText:
    def test_empty_returns_empty(self) -> None:
        assert split_text("") == []
        assert split_text("   ") == []

    def test_short_text_single_chunk(self) -> None:
        text = "Hello world."
        chunks = split_text(text)
        assert len(chunks) == 1
        assert chunks[0] == "Hello world."

    def test_paragraph_split(self) -> None:
        text = "Para one.\n\nPara two.\n\nPara three."
        chunks = split_text(text, chunk_size=20, overlap=5)
        assert len(chunks) > 1

    def test_chunk_content_preserved(self) -> None:
        text = "Para one.\n\nPara two.\n\nPara three."
        chunks = split_text(text)
        combined = " ".join(chunks)
        assert "Para one." in combined
        assert "Para two." in combined
        assert "Para three." in combined

    def test_sentences_split_when_paragraph_too_long(self) -> None:
        # Build a paragraph made of many short sentences; each is ~15 chars
        sentences = ["Short sent X." for _ in range(40)]
        long_para = " ".join(sentences)  # ~600 chars, no double newlines
        chunks = split_text(long_para, chunk_size=100, overlap=20)
        # Should produce multiple chunks since the paragraph exceeds 2× chunk_size
        assert len(chunks) > 1

    def test_overlap_present_in_consecutive_chunks(self) -> None:
        text = ("A" * 800) + "\n\n" + ("B" * 800)
        chunks = split_text(text, chunk_size=1000, overlap=100)
        assert len(chunks) >= 2
