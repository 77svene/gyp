import json
import logging
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class Message(BaseModel):
    role: str
    content: str

class OllamaClient:
    """
    Core Intelligence Integration using a local Ollama instance.
    Targets Qwen 3.5 9B (or fallback models) for reasoning, planning, and tool use.
    """
    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "qwen2.5"):
        self.base_url = base_url
        self.default_model = default_model
        self.client = httpx.AsyncClient(timeout=60.0)

    async def chat(self, messages: List[Message], model: Optional[str] = None, json_format: bool = False, temperature: float = 0.7) -> str:
        """Send a chat completion request to the local Ollama instance."""
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
            logger.error(f"HTTP error communicating with Ollama: {e.response.status_code} - {e.response.text}")
            # Fallback logic could be implemented here (e.g., switching to a smaller model)
            raise
        except Exception as e:
            logger.error(f"Error communicating with Ollama: {e}")
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
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from LLM: {response_text}")
            raise
        except Exception as e:
            logger.error(f"Validation error for structured output: {e}")
            raise

    async def close(self):
        """Close the underlying HTTP client."""
        await self.client.aclose()
