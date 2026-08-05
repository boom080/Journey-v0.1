import hashlib
import math
import re

EMBEDDING_VERSION = "journey-hash-chargram-1"
EMBEDDING_DIMENSIONS = 96


def _tokens(text: str) -> list[str]:
    normalized = re.sub(r"\s+", "", text.lower())
    characters = [character for character in normalized if character.isalnum()]
    bigrams = [normalized[index : index + 2] for index in range(max(0, len(normalized) - 1))]
    return characters + bigrams


def embed_text(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for token in _tokens(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
        vector[index] += -1.0 if digest[4] & 1 else 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    return [round(value / norm, 8) for value in vector] if norm else vector


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True))
