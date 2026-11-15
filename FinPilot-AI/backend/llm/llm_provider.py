"""Abstract LLM provider interface for FinPilot AI."""
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Base interface for Large Language Model providers.
    
    Allows swapping Gemini for other providers (e.g., Anthropic, OpenAI, local)
    without modifying the application logic.
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a response given a text prompt."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if credentials and network configuration are available."""
        ...
