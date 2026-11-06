"""Local language checks for generated prose; no API calls or model downloads."""
import re
from functools import lru_cache

from langdetect import DetectorFactory, LangDetectException
from langdetect.detector_factory import PROFILES_DIRECTORY


@lru_cache(maxsize=1)
def _factory():
    factory = DetectorFactory()
    factory.seed = 0
    factory.load_profile(PROFILES_DIRECTORY)
    return factory


@lru_cache(maxsize=512)
def foreign_prose(text: str) -> bool:
    """Flag confident foreign sentences, including after a Spanish introduction.

    Short names, acronyms, code and quotations are not reliable language samples.
    This is a guard, not a claim of perfect language identification.
    """
    clean = re.sub(r"https?://\S+|`[^`]*`", " ", text)
    if re.match(r"^[¿\s]*(?:what|why|how|which|when|where|who|explain|discuss|outline|identify|evaluate|justify)\b", clean, re.I):
        return True
    if clean.strip().casefold() in {"introduction", "methodology", "conclusions", "results", "objectives", "limitations", "references", "background"}:
        return True
    for part in re.split(r"[.!?\n:]\s*", clean):
        words = re.findall(r"[^\W\d_]+", part, re.UNICODE)
        if len(words) < 6 or sum(map(len, words)) < 28:
            continue
        try:
            detector = _factory().create()
            detector.append(part[:4000])
            candidates = detector.get_probabilities()
        except LangDetectException:
            continue
        if candidates and candidates[0].lang != "es" and candidates[0].prob >= .95:
            return True
    return False


def require_spanish(*texts: str) -> None:
    if any(foreign_prose(text) for text in texts if text):
        raise ValueError("El contenido generado debe estar en español")
