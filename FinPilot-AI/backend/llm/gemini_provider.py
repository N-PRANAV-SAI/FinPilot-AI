"""Gemini LLM provider implementation."""
import logging
from config.settings import settings
from backend.llm.llm_provider import LLMProvider

log = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Google Gemini provider with error handling and fallback behavior."""

    def __init__(self):
        self._configured = False
        self._genai = None
        self.model = None
        self.model_name = getattr(settings, "llm_model", "gemini-3.8-flash")

        api_key = getattr(settings, "gemini_api_key", "")
        if not api_key or not str(api_key).strip():
            log.info("GEMINI_API_KEY is not configured. AI explanations will use local intelligence fallback.")
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=str(api_key).strip())
            self._genai = genai
            self.model = genai.GenerativeModel(self.model_name)
            self._configured = True
            log.info("Initialized GeminiProvider with model: %s", self.model_name)
        except Exception as exc:
            log.warning("Google Generative AI client configuration deferred: %s", exc)
            self._configured = False

    def is_available(self) -> bool:
        """Check if GEMINI_API_KEY is configured, client is ready, and network is online."""
        if not (self._configured and self._genai):
            return False
        try:
            from backend.data.providers.yfinance_provider import is_dns_online
            return is_dns_online()
        except Exception:
            return True

    def generate(self, prompt: str) -> str:
        """Generate response text from Gemini API with automatic model fallback."""
        if not self.is_available():
            return "Note: Gemini API key is not configured or offline. Local financial analysis engine generated this response."
        fallback_models = [self.model_name, "gemini-3.8-flash", "gemini-flash-latest", "gemini-3.5-flash"]
        # Deduplicate while preserving order
        unique_models = list(dict.fromkeys(fallback_models))
        
        last_error = None
        for candidate in unique_models:
            try:
                model = self._genai.GenerativeModel(candidate)
                response = model.generate_content(prompt)
                text = getattr(response, "text", "") or ""
                if not text:
                    return "The LLM returned an empty response. Please check your query or try again."
                return text
            except Exception as exc:
                last_error = exc
                log.warning("Gemini generation failed with model %s: %s. Trying next candidate...", candidate, exc)
                continue
                
        log.error("All Gemini model candidates failed: %s", last_error)
        raise RuntimeError(f"Gemini generation error across models: {last_error}") from last_error
