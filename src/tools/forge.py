import ast
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from src.core.event_bus import EventBus
from src.core.events import CapabilityGapEvent
from src.core.llm import Message, OllamaClient
from src.knowledge.graph import KnowledgeGraph

logger = logging.getLogger(__name__)

class ToolForge:
    """
    Dynamic Capability Expansion System.
    Analyzes CapabilityGapEvents, designs solutions, generates code (primarily Python),
    validates it via static analysis/sandboxing, and integrates it into the running ecosystem.
    """
    def __init__(self, event_bus: EventBus, llm_client: OllamaClient, kg: KnowledgeGraph, tools_dir: str = "src/tools/generated"):
        self.event_bus = event_bus
        self.llm = llm_client
        self.kg = kg
        self.tools_dir = tools_dir

        # Ensure the tools directory exists
        os.makedirs(self.tools_dir, exist_ok=True)
        init_file = os.path.join(self.tools_dir, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("")

        # Register for gap events
        self.event_bus.subscribe("system.capability_gap.*", self.handle_capability_gap)

    async def handle_capability_gap(self, event: CapabilityGapEvent):
        """Triggered when an agent reports an unmet operational need."""
        logger.info(f"ToolForge received capability gap: {event.gap_category} (Priority: {event.priority_assessment})")

        # In a real system, we'd queue these based on priority. Here we process immediately.
        try:
            # 1. Gap Analysis and Solution Design
            design = await self._analyze_and_design(event)
            if not design:
                logger.warning(f"Failed to design solution for gap: {event.gap_category}")
                return

            # 2. Implementation Generation (Python)
            code = await self._generate_implementation(design, event.functional_requirements)
            if not code:
                logger.warning(f"Failed to generate code for gap: {event.gap_category}")
                return

            # 3. Automated Testing and Validation (Static Analysis)
            if not self._validate_code(code):
                logger.warning(f"Generated code failed validation for gap: {event.gap_category}")
                # We could implement iterative refinement here (feeding errors back to LLM)
                return

            # 4. Ecosystem Integration Deployment
            # Note: In a production system, this code must be executed in a restricted sandbox
            # (e.g., via Docker container, WASM, or a specialized restricted Python environment).
            # For safety in this prototype, we save the generated file but DO NOT load/execute it dynamically.

            module_name = f"tool_{uuid.uuid4().hex[:8]}"
            filepath = os.path.join(self.tools_dir, f"{module_name}.py")

            with open(filepath, "w") as f:
                f.write(code)

            logger.info(f"Generated new capability saved to {filepath}. Manual review required before loading.")

            # Register the new pending capability in the Knowledge Graph
            await self.kg.create_node("Capability", {
                "name": design.get('class_name', 'UnknownTool'),
                "category": event.gap_category,
                "module_path": filepath,
                "requirements_met": event.functional_requirements,
                "status": "pending_review"  # Explicitly require review due to RCE risk
            })

        except Exception as e:
            logger.error(f"ToolForge encountered error processing gap: {e}", exc_info=True)

    async def _analyze_and_design(self, event: CapabilityGapEvent) -> Optional[Dict[str, Any]]:
        """Transform vague capability deficiencies into precise technical specifications."""
        prompt = f"""
        Analyze the following capability gap and provide a technical design for a Python module to solve it.
        Category: {event.gap_category}
        Requirements: {event.functional_requirements}
        Context: {event.payload.get('reasoning', '')}

        Provide your design as a JSON object containing:
        - class_name: The name of the main class (must end in 'Adapter' or 'Tool').
        - description: What it does.
        - required_libraries: List of standard or common pip libraries needed.
        - public_methods: List of dicts with 'name' and 'description'.
        """
        # Simplification: requesting JSON directly instead of structured output wrapper for speed here
        try:
            response = await self.llm.chat([Message(role="user", content=prompt)], json_format=True)
            import json
            return json.loads(response)
        except Exception as e:
            logger.error(f"Design analysis failed: {e}")
            return None

    async def _generate_implementation(self, design: Dict[str, Any], requirements: List[str]) -> Optional[str]:
        """Generate Python code based on the design specification."""
        prompt = f"""
        Write a complete, self-contained Python 3 script implementing the following design.
        Class Name: {design.get('class_name')}
        Description: {design.get('description')}
        Methods: {design.get('public_methods')}
        Original Requirements: {requirements}

        Rules:
        1. Include necessary imports (only standard library or very common ones like `requests` or `aiohttp`).
        2. Provide docstrings for the class and methods.
        3. Do NOT include any markdown formatting (like ```python ... ```), output ONLY the raw Python code.
        4. Make the implementation robust with basic error handling.
        """
        try:
            # We explicitly ask for non-json format because we want raw python code
            code = await self.llm.chat([Message(role="user", content=prompt)], temperature=0.2)
            # Basic cleanup in case the LLM ignored rule 3
            if code.startswith("```python"):
                code = code[9:]
            if code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]
            return code.strip()
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            return None

    def _validate_code(self, code: str) -> bool:
        """Automated testing and validation (Basic Static Analysis)."""
        try:
            # Check for syntax errors
            ast.parse(code)

            # Very basic security check (reject arbitrary command execution)
            dangerous_imports = ['os.system', 'subprocess', 'eval(', 'exec(']
            for dangerous in dangerous_imports:
                if dangerous in code:
                    logger.warning(f"Generated code failed security validation: contains {dangerous}")
                    return False

            return True
        except SyntaxError as e:
            logger.error(f"Generated code failed syntax validation: {e}")
            return False
        except Exception as e:
            logger.error(f"Validation encountered an error: {e}")
            return False
