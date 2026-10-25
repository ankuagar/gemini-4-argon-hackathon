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

import json
import threading
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

    @property
    def text(self) -> str:
        return self.output_text

    @property
    def latency_seconds(self) -> float:
        return self.elapsed_seconds

    @property
    def parsed_json(self) -> Optional[Dict[str, Any]]:
        raw = (self.output_text or "").strip()
        if not raw:
            return None
        if raw.startswith("```"):
            lines = raw.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            raw = "\n".join(lines).strip()
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None


class ArgonClient:
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self._traffic_lock = threading.Lock()
        self.live_traffic: List[Dict[str, Any]] = []
        self._call_seq = 0

    def get_live_traffic(self, limit: int = 30) -> List[Dict[str, Any]]:
        now = time.time()
        with self._traffic_lock:
            items = list(self.live_traffic[-limit:])
        out: List[Dict[str, Any]] = []
        for item in reversed(items):
            snap = dict(item)
            if snap.get("status") == "IN_FLIGHT":
                snap["elapsed_seconds"] = round(max(0.1, now - snap.get("started_at", now)), 1)
            out.append(snap)
        return out

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
        response_schema: Optional[Dict[str, Any]] = None,
        force_background: bool = False,
        on_poll: Optional[Callable[[str, float], None]] = None,
        video_base64: Optional[str] = None,
        video_mime_type: str = "video/mp4",
        phase_label: Optional[str] = None,
    ) -> InteractionResult:
        """
        Execute a turn on Gemini 4 Argon (`gemini-4-argon`) or Flash Subagent (`gemini-3.8-flash`) via the Interactions API.
        Supports both text and multimodal video+text inputs (`type="video"`).
        Automatically switches to `background=True` when `max_output_tokens > 65536`
        or `force_background=True`, polling until completion and joining all `model_output` steps.
        """
        start_time = time.monotonic()
        wall_start = time.time()
        use_background = force_background or (max_output_tokens > 65536)
        effective_schema = json_schema if json_schema is not None else response_schema

        gen_config: Dict[str, Any] = {
            "thinking_level": thinking_level,
            "thinking_summaries": "auto",
            "max_output_tokens": max_output_tokens,
        }

        if video_base64:
            input_payload: Any = [
                {"type": "video", "data": video_base64, "mime_type": video_mime_type},
                {"type": "text", "text": prompt},
            ]
        else:
            input_payload = prompt

        kwargs: Dict[str, Any] = {
            "model": model,
            "input": input_payload,
            "generation_config": gen_config,
        }
        if system_instruction:
            kwargs["system_instruction"] = system_instruction
        if previous_interaction_id:
            kwargs["previous_interaction_id"] = previous_interaction_id
        if use_background:
            kwargs["background"] = True
        if effective_schema is not None:
            kwargs["response_format"] = {
                "type": "text",
                "mime_type": "application/json",
                "schema": effective_schema,
            }

        prev_arg = f', previous_interaction_id="{previous_interaction_id}"' if previous_interaction_id else ""
        bg_arg = ", background=True" if use_background else ""
        vid_arg = f', input=[{{"type": "video", "mime_type": "{video_mime_type}"}}, {{"type": "text"}}]' if video_base64 else ""
        sdk_call_str = (
            f'client.interactions.create(model="{model}"{vid_arg}, '
            f'generation_config={{"thinking_level": "{thinking_level}", "max_output_tokens": {max_output_tokens}}}'
            f'{prev_arg}{bg_arg})'
        )
        clean_prompt_preview = " ".join(prompt.strip().split())[:220]

        with self._traffic_lock:
            self._call_seq += 1
            call_record: Dict[str, Any] = {
                "call_id": f"api-{self._call_seq}",
                "seq": self._call_seq,
                "status": "IN_FLIGHT",
                "started_at": wall_start,
                "timestamp_iso": time.strftime("%H:%M:%S", time.localtime(wall_start)),
                "model": model,
                "thinking_level": thinking_level,
                "max_output_tokens": max_output_tokens,
                "previous_interaction_id": previous_interaction_id,
                "background": use_background,
                "prompt_chars": len(prompt),
                "prompt_preview": clean_prompt_preview,
                "sdk_call": sdk_call_str,
                "interaction_id": None,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "thought_steps": 0,
                "elapsed_seconds": 0.0,
                "output_preview": "",
            }
            self.live_traffic.append(call_record)

        try:
            interaction = self.client.interactions.create(**kwargs)

            if use_background:
                while interaction.status in ("in_progress", "queued"):
                    elapsed = time.monotonic() - start_time
                    with self._traffic_lock:
                        call_record["interaction_id"] = getattr(interaction, "id", None)
                        call_record["elapsed_seconds"] = round(elapsed, 1)
                    if on_poll:
                        on_poll(interaction.status, elapsed)
                    time.sleep(3)
                    interaction = self.client.interactions.get(id=interaction.id)
        except Exception as exc:
            with self._traffic_lock:
                call_record["status"] = "ERROR"
                call_record["elapsed_seconds"] = round(time.monotonic() - start_time, 2)
                call_record["output_preview"] = f"API Error: {exc}"
            raise

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

        with self._traffic_lock:
            call_record["status"] = "COMPLETED"
            call_record["interaction_id"] = interaction.id
            call_record["input_tokens"] = input_tokens
            call_record["output_tokens"] = output_tokens
            call_record["total_tokens"] = total_tokens
            call_record["thought_steps"] = len(thoughts)
            call_record["elapsed_seconds"] = elapsed_total
            call_record["output_preview"] = " ".join(output_text.strip().split())[:260]

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
