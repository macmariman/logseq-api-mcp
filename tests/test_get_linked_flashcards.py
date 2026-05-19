"""Tests for get_linked_flashcards tool."""

from tests.conftest import FakeLogseqClient
from src.tools.get_linked_flashcards import (
    _run,
    _find_flashcards_in_blocks,
    _extract_flashcard_question,
)


class TestExtractFlashcardQuestion:
    def test_removes_card_tag(self):
        result = _extract_flashcard_question("What is Python? #card")
        assert "#card" not in result
        assert "What is Python?" in result

    def test_extracts_options(self):
        content = "Which is correct? #card\n+ [A] Option A\n+ [B] Option B"
        result = _extract_flashcard_question(content)
        assert "Option A" in result
        assert "Option B" in result


class TestFindFlashcards:
    def test_finds_card_blocks(self):
        blocks = [
            {
                "id": 1,
                "uuid": "u1",
                "content": "Q #card",
                "properties": {},
                "children": [],
            },
            {
                "id": 2,
                "uuid": "u2",
                "content": "Not a card",
                "properties": {},
                "children": [],
            },
        ]
        result = _find_flashcards_in_blocks(blocks, {"name": "Test"})
        assert len(result) == 1
        assert result[0]["block_uuid"] == "u1"

    def test_finds_nested_cards(self):
        blocks = [
            {
                "id": 1,
                "uuid": "u1",
                "content": "Parent",
                "properties": {},
                "children": [
                    {
                        "id": 2,
                        "uuid": "u2",
                        "content": "Nested #card",
                        "properties": {},
                        "children": [],
                    }
                ],
            }
        ]
        result = _find_flashcards_in_blocks(blocks, {"name": "Test"})
        assert len(result) == 1
        assert result[0]["block_uuid"] == "u2"


class TestGetLinkedFlashcards:
    async def test_page_not_found(self):
        client = FakeLogseqClient(
            {
                "get_page_linked_references": [],
                "get_all_pages": [],
            }
        )
        result = await _run(client, "Missing Page")
        assert "not found" in result[0].text

    async def test_no_flashcards_returns_message(self):
        all_pages = [
            {"id": 1, "uuid": "p1", "name": "mypage", "originalName": "mypage"}
        ]
        client = FakeLogseqClient(
            {
                "get_page_linked_references": [],
                "get_all_pages": all_pages,
                "get_page_blocks_tree": [
                    {
                        "id": 1,
                        "uuid": "b1",
                        "content": "Normal block",
                        "properties": {},
                        "children": [],
                    }
                ],
            }
        )
        result = await _run(client, "mypage")
        assert "No flashcards found" in result[0].text

    async def test_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_page_linked_references(self, page_name):
                raise RuntimeError("network error")

        result = await _run(ErrorClient(), "mypage")
        assert "❌ Error fetching linked flashcards" in result[0].text
