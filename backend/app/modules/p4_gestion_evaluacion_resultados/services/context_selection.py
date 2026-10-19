"""Select bounded evidence locally, without making additional embedding/LLM calls."""
import re
import unicodedata

STOPWORDS = {"para", "como", "esta", "este", "esto", "sobre", "entre", "desde", "porque", "cuales", "cuando", "donde", "tiene", "puede", "datos"}


def terms(text: str) -> set[str]:
    normalized = "".join(char for char in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(char))
    return {word for word in re.findall(r"[a-z0-9]+", normalized) if len(word) > 3 and word not in STOPWORDS}


def select_evaluation_context(chunks: list[str], question: str, expected_points: list[str] | None, max_chars: int) -> str:
    if max_chars < 1:
        return ""
    if sum(map(len, chunks)) + max(0, len(chunks)-1)*2 <= max_chars:
        return "\n\n".join(chunks)
    query = terms(question + " " + " ".join(expected_points or []))
    ranked = sorted(enumerate(chunks), key=lambda item: (-len(query & terms(item[1])), item[0]))
    selected = []
    remaining = max_chars
    for index, chunk in ranked:
        if remaining <= 2:
            break
        text = chunk[:remaining]
        selected.append((index, text))
        remaining -= len(text) + 2
    return "\n\n".join(text for _, text in sorted(selected))[:max_chars]
