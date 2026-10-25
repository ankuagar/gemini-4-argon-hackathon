"""
engine/argon_client.py
Wrapper around Google GenAI Interactions API for Gemini 4 Argon (`gemini-4-argon`).

Supports:
- Server-side state management via `previous_interaction_id` (with implicit 95% caching discount)
- Tunable reasoning depth via `thinking_level` ("low" | "medium" | "high")
- Observable `thought` step summaries and signatures (`thinking_summaries="auto"`)
- Unified 1M-token context window & long decode via `background=True` for >64K output tokens
- Structured JSON Schema outputs via `response_format`
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from google import genai


MODEL_ID = "gemini-4-argon"
FLASH_SUBAGENT_MODEL_ID = "gemini-3.8-flash"


@dataclass
class ThoughtRecord:
    summary_text: str
    has_signature: bool = True


@dataclass
class InteractionResult:
    interaction_id: str
    status: str
    output_text: str
    thoughts: List[ThoughtRecord] = field(default_factory=list)
    step_types: List[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    elapsed_seconds: float = 0.0
    thinking_level: str = "medium"
    used_background: bool = False


class ArgonClient:
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def interact(
        self,
        prompt: str,
        *,
        model: str = MODEL_ID,
        system_instruction: Optional[str] = None,
        thinking_level: str = "medium",
        max_output_tokens: int = 65536,
        previous_interaction_id: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        force_background: bool = False,
        on_poll: Optional[Callable[[str, float], None]] = None,
    ) -> InteractionResult:
        """
        Execute a turn on Gemini 4 Argon (`gemini-4-argon`) or Flash Subagent (`gemini-3.8-flash`) via the Interactions API.
        Automatically switches to `background=True` when `max_output_tokens > 65536`
        or `force_background=True`, polling until completion and joining all `model_output` steps.
        """
        start_time = time.monotonic()
        use_background = force_background or (max_output_tokens > 65536)

        gen_config: Dict[str, Any] = {
            "thinking_level": thinking_level,
            "thinking_summaries": "auto",
            "max_output_tokens": max_output_tokens,
        }

        kwargs: Dict[str, Any] = {
            "model": model,
            "input": prompt,
            "generation_config": gen_config,
        }
        if system_instruction:
            kwargs["system_instruction"] = system_instruction
        if previous_interaction_id:
            kwargs["previous_interaction_id"] = previous_interaction_id
        if use_background:
            kwargs["background"] = True
        if json_schema is not None:
            kwargs["response_format"] = {
                "type": "text",
                "mime_type": "application/json",
                "schema": json_schema,
            }

        interaction = self.client.interactions.create(**kwargs)

        if use_background:
            while interaction.status in ("in_progress", "queued"):
                elapsed = time.monotonic() - start_time
                if on_poll:
                    on_poll(interaction.status, elapsed)
                time.sleep(3)
                interaction = self.client.interactions.get(id=interaction.id)

        elapsed_total = round(time.monotonic() - start_time, 2)

        thoughts: List[ThoughtRecord] = []
        step_types: List[str] = []
        model_output_chunks: List[str] = []

        steps = getattr(interaction, "steps", None) or []
        for step in steps:
            s_type = getattr(step, "type", "unknown")
            step_types.append(s_type)
            if s_type == "thought":
                summary_parts: List[str] = []
                for block in getattr(step, "summary", None) or []:
                    if getattr(block, "type", None) == "text" and getattr(block, "text", None):
                        summary_parts.append(block.text)
                thoughts.append(
                    ThoughtRecord(
                        summary_text="\n".join(summary_parts).strip()
                        or "(Deep reasoning step completed with encrypted thought signature)",
                        has_signature=bool(getattr(step, "signature", None)),
                    )
                )
            elif s_type == "model_output":
                for block in getattr(step, "content", None) or []:
                    if getattr(block, "type", None) == "text" and getattr(block, "text", None):
                        model_output_chunks.append(block.text)

        # Join across all model_output steps (handles multi-hop long decode seamlessly)
        output_text = (
            "".join(model_output_chunks)
            if model_output_chunks
            else (getattr(interaction, "output_text", None) or "")
        )

        usage = getattr(interaction, "usage", None)
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        total_tokens = getattr(usage, "total_tokens", 0) or (input_tokens + output_tokens)

        return InteractionResult(
            interaction_id=interaction.id,
            status=getattr(interaction, "status", "completed"),
            output_text=output_text,
            thoughts=thoughts,
            step_types=step_types,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            elapsed_seconds=elapsed_total,
            thinking_level=thinking_level,
            used_background=use_background,
        )
