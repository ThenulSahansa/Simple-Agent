"""Create focused subagents that use the same chat-completion client as the agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence


DEFAULT_MODEL = "openai/gpt-oss-20b"
DEFAULT_MAX_TOKENS = 1024


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value.strip()


@dataclass(frozen=True)
class Subagent:
    """A configured specialist that can answer a task through a chat client."""

    name: str
    instructions: str
    model: str = DEFAULT_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS
    tools: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _require_text(self.name, "name"))
        object.__setattr__(
            self,
            "instructions",
            _require_text(self.instructions, "instructions"),
        )
        object.__setattr__(self, "model", _require_text(self.model, "model"))
        if not isinstance(self.max_tokens, int) or self.max_tokens < 1:
            raise ValueError("max_tokens must be a positive integer.")
        object.__setattr__(self, "tools", tuple(self.tools))

    @property
    def system_prompt(self) -> str:
        return (
            f"You are the {self.name} subagent. Work only within your assigned "
            f"specialty and follow these instructions:\n{self.instructions}"
        )

    def run(
        self,
        client: Any,
        task: str,
        *,
        context: Optional[str] = None,
    ) -> str:
        """Run this subagent and return the model's text response."""
        task_text = _require_text(task, "task")
        messages = [{"role": "system", "content": self.system_prompt}]
        user_content = task_text
        if context is not None:
            user_content += f"\n\nContext:\n{_require_text(context, 'context')}"
        messages.append({"role": "user", "content": user_content})

        request: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
        }
        if self.tools:
            request["tools"] = list(self.tools)
            request["tool_choice"] = "auto"

        response = client.chat.completions.create(**request)
        choices = getattr(response, "choices", None)
        if not choices:
            raise RuntimeError(f"Subagent {self.name!r} returned no choices.")
        content = getattr(choices[0].message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(f"Subagent {self.name!r} returned no text response.")
        return content


class SubagentCreator:
    """Factory for creating consistently configured specialist subagents."""

    def __init__(
        self,
        *,
        default_model: str = DEFAULT_MODEL,
        default_max_tokens: int = DEFAULT_MAX_TOKENS,
        tools: Sequence[Mapping[str, Any]] = (),
    ) -> None:
        self.default_model = _require_text(default_model, "default_model")
        if not isinstance(default_max_tokens, int) or default_max_tokens < 1:
            raise ValueError("default_max_tokens must be a positive integer.")
        self.default_max_tokens = default_max_tokens
        self.tools = tuple(tools)

    def create(
        self,
        name: str,
        instructions: str,
        *,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> Subagent:
        """Create a subagent, inheriting factory defaults when omitted."""
        return Subagent(
            name=name,
            instructions=instructions,
            model=self.default_model if model is None else model,
            max_tokens=(
                self.default_max_tokens if max_tokens is None else max_tokens
            ),
            tools=self.tools if tools is None else tuple(tools),
        )


def create_subagent(
    name: str,
    instructions: str,
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    tools: Sequence[Mapping[str, Any]] = (),
) -> Subagent:
    """Convenience function for creating one subagent."""
    return Subagent(
        name=name,
        instructions=instructions,
        model=model,
        max_tokens=max_tokens,
        tools=tuple(tools),
    )


__all__ = [
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_MODEL",
    "Subagent",
    "SubagentCreator",
    "create_subagent",
]