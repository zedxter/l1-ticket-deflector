"""Configuration for the production L1 Ticket Deflector agent."""
import os

# LLM: set MOCK_MODE=1 to run the graph without an API key (to show the logic).
MOCK_MODE = os.getenv("MOCK_MODE", "0") == "1"

MODEL = os.getenv("DEFLECTOR_MODEL", "gpt-4o-mini")

HUMAN_REVIEW_SENSITIVITY = {"high", "critical"}

# Categories the agent may fully resolve on its own (low sensitivity).
AUTO_RESOLVE_SENSITIVITY = {"low"}

# Classifier confidence threshold; below this -> escalate to the general queue.
# (in production: confidence from the LLM, 0..1)
CONFIDENCE_THRESHOLD = 0.55

# Escalation strategy: who we hand high/critical to.
ESCALATION = {
    "high": "service_desk_l2",
    "critical": "security_ops",
}
