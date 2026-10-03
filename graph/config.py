"""Конфигурация боевого агента L1 Ticket Deflector."""
import os

# LLM: включи MOCK_MODE=1, чтобы прогнать граф без API-ключа (для показа логики).
MOCK_MODE = os.getenv("MOCK_MODE", "0") == "1"

MODEL = os.getenv("DEFLECTOR_MODEL", "gpt-4o-mini")

HUMAN_REVIEW_SENSITIVITY = {"high", "critical"}

# Категории, которые агент имеет право решать полностью сам (low sensitivity).
AUTO_RESOLVE_SENSITIVITY = {"low"}

# Порог уверенности классификатора; ниже — эскалация в общую очередь.
# (в боевой версии — confidence от LLM, 0..1)
CONFIDENCE_THRESHOLD = 0.55

# Стратегия эскалации: кому передаём high/critical.
ESCALATION = {
    "high": "service_desk_l2",
    "critical": "security_ops",
}
