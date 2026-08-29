from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextChunk:
    index: int
    text: str
    start_char: int
    end_char: int


class ChunkingService:
    def __init__(self, *, max_chars: int, overlap_chars: int) -> None:
        if overlap_chars >= max_chars:
            raise ValueError("Chunk overlap must be smaller than chunk size")
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def split(self, text: str) -> list[TextChunk]:
        if not text:
            return []

        chunks: list[TextChunk] = []
        start = 0
        length = len(text)
        while start < length:
            end = min(start + self.max_chars, length)
            if end < length:
                end = self._best_boundary(text, start, end)
            raw_chunk = text[start:end]
            stripped = raw_chunk.strip()
            if stripped:
                left_trim = len(raw_chunk) - len(raw_chunk.lstrip())
                right_trim = len(raw_chunk) - len(raw_chunk.rstrip())
                chunks.append(
                    TextChunk(
                        index=len(chunks),
                        text=stripped,
                        start_char=start + left_trim,
                        end_char=end - right_trim,
                    )
                )
            if end >= length:
                break
            next_start = max(0, end - self.overlap_chars)
            if next_start <= start:
                next_start = end
            start = self._next_word_boundary(text, next_start, end)
        return chunks

    def _best_boundary(self, text: str, start: int, hard_end: int) -> int:
        soft_start = start + int(self.max_chars * 0.6)
        for separator in ("\n\n", ". ", "\n", " "):
            boundary = text.rfind(separator, soft_start, hard_end)
            if boundary != -1:
                return boundary + len(separator)
        return hard_end

    @staticmethod
    def _next_word_boundary(text: str, candidate: int, previous_end: int) -> int:
        if candidate <= 0 or candidate >= len(text) or text[candidate - 1].isspace():
            return candidate
        boundary = text.find(" ", candidate, previous_end)
        return boundary + 1 if boundary != -1 else candidate
