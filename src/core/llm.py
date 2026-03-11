import json
import logging
from typing import List, Optional

import httpx
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.core.config import settings

logger = logging.getLogger(__name__)

class Message(BaseModel):
    role: str
    content: str

class OllamaClient:
    """
    Core Intelligence Integration using a local Ollama instance.
    Targets Qwen 3.5 9B (or fallback models) for reasoning, planning, and tool use.
    """
    def __init__(self, base_url: Optional[str] = None, default_model: Optional[str] = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.default_model = default_model or settings.DEFAULT_LLM_MODEL
        self.client = httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS)

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(settings.LLM_MAX_RETRIES),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        reraise=True
    )
    async def chat(self, messages: List[Message], model: Optional[str] = None, json_format: bool = False, temperature: float = 0.7) -> str:
        """Send a chat completion request to the local Ollama instance with retry."""
        target_model = model or self.default_model
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": target_model,
            "messages": [m.model_dump() for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        if json_format:
            payload["format"] = "json"

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error communicating with Ollama (retrying): {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.warning(f"Error communicating with Ollama (retrying): {e}")
            raise

    async def generate_structured_output(self, prompt: str, schema: BaseModel, model: Optional[str] = None) -> BaseModel:
        """
        Uses prompt engineering to enforce structured JSON output matching a Pydantic schema.
        Note: Ollama supports native JSON mode, but we still need to validate against the schema.
        """
        schema_json = schema.model_json_schema()
        system_prompt = (
            f"You are a helpful assistant designed to output strict JSON. "
            f"Adhere to this JSON schema: {json.dumps(schema_json)}"
        )

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=prompt)
        ]

        response_text = await self.chat(messages, model=model, json_format=True, temperature=0.1)

        try:
            # Parse the JSON and validate against the Pydantic model
            parsed_data = json.loads(response_text)
            return schema(**parsed_data)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from LLM: {response_text}")
            raise
        except Exception as e:
            logger.error(f"Validation error for structured output: {e}")
            raise

    async def close(self):
        """Close the underlying HTTP client."""
        await self.client.aclose()
