"""External API pricing — pure functions, DB/HTTP side effect yok.

cost_tracker.py bu modulden import eder. Ayrik tutma sebebi:
  - Unit test edilebilirlik (SQLAlchemy gerekmez)
  - Framework-agnostic (core/ kurali)
  - Fiyat degisince tek bir dosyayi guncelle
"""

# Claude — 2026-04 public pricing ($/M tokens)
CLAUDE_PRICES: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6":         {"in": 3.0,  "out": 15.0},
    "claude-opus-4-7":           {"in": 15.0, "out": 75.0},
    "claude-haiku-4-5-20251001": {"in": 0.8,  "out": 4.0},
}
CLAUDE_DEFAULT = CLAUDE_PRICES["claude-sonnet-4-6"]

# OpenAI
OPENAI_TTS_PER_M_CHAR = 15.0   # tts-1
OPENAI_STT_PER_MIN    = 0.006  # whisper-1

# Apify Google Maps actor — tahmini
APIFY_PER_PLACE  = 0.0035
APIFY_PER_REVIEW = 0.001


def claude_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    rate = CLAUDE_PRICES.get(model, CLAUDE_DEFAULT)
    return (input_tokens * rate["in"] + output_tokens * rate["out"]) / 1_000_000


def openai_tts_cost(chars: int) -> float:
    return chars * OPENAI_TTS_PER_M_CHAR / 1_000_000


def openai_stt_cost(seconds: float) -> float:
    return (seconds / 60.0) * OPENAI_STT_PER_MIN


def apify_cost(places: int, reviews: int = 0) -> float:
    return places * APIFY_PER_PLACE + reviews * APIFY_PER_REVIEW
