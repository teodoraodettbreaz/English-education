from __future__ import annotations

import json
import math
import os
import random
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, Sequence

from openai_messages_client import chat_completion


Message = dict[str, str]


class LLMError(RuntimeError):
    pass


class LLMConfigurationError(LLMError):
    pass


class LLMResponseError(LLMError):
    pass


class LLMBudgetExceeded(LLMError):
    pass


class LLMProvider(Protocol):


    model: str

    def complete(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: int | None = None,
    ) -> str:
        ...


def _estimate_tokens(text: str) -> int:


    if not text:
        return 0
    ascii_count = sum(1 for char in text if ord(char) < 128)
    non_ascii = len(text) - ascii_count
    return max(1, math.ceil(ascii_count / 4) + math.ceil(non_ascii / 1.5))


@dataclass(slots=True)
class CallRecord:
    model: str
    input_tokens_estimate: int
    output_tokens_estimate: int
    elapsed_ms: int
    attempt_count: int
    purpose: str = ""
    status: str = "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "input_tokens_estimate": self.input_tokens_estimate,
            "output_tokens_estimate": self.output_tokens_estimate,
            "elapsed_ms": self.elapsed_ms,
            "attempt_count": self.attempt_count,
            "purpose": self.purpose,
            "status": self.status,
        }


@dataclass(slots=True)
class CallBudget:


    max_calls: int = 128
    max_input_tokens: int = 65_536
    max_output_tokens: int = 32_768
    max_total_tokens: int = 80_000
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    records: list[CallRecord] = field(default_factory=list)

    def check_before_call(
        self,
        messages: Sequence[Message],
        max_tokens: int,
        *,
        reserved_attempts: int = 1,
    ) -> int:
        input_estimate = _estimate_tokens(
            "\n".join(message.get("content", "") for message in messages)
        )
        reserved_attempts = max(1, reserved_attempts)
        if self.calls + reserved_attempts > self.max_calls:
            raise LLMBudgetExceeded("LLM call limit reached.")
        if self.input_tokens + input_estimate * reserved_attempts > self.max_input_tokens:
            raise LLMBudgetExceeded("LLM input-token budget reached.")
        if self.output_tokens + max_tokens > self.max_output_tokens:
            raise LLMBudgetExceeded("Requested output would exceed the output-token budget.")
        if (
            self.input_tokens
            + self.output_tokens
            + input_estimate * reserved_attempts
            > self.max_total_tokens
        ):
            raise LLMBudgetExceeded("LLM total-token budget reached.")
        return input_estimate

    def record(
        self,
        *,
        model: str,
        input_tokens: int,
        output_text: str,
        elapsed_ms: int,
        attempt_count: int,
        purpose: str = "",
        status: str = "ok",
    ) -> None:
        output_tokens = _estimate_tokens(output_text)
        charged_input = input_tokens * max(1, attempt_count)
        if self.input_tokens + self.output_tokens + charged_input + output_tokens > self.max_total_tokens:
            raise LLMBudgetExceeded("Model response exceeded the remaining total-token budget.")
        self.calls += max(1, attempt_count)
        self.input_tokens += charged_input
        self.output_tokens += output_tokens
        self.records.append(
            CallRecord(
                model=model,
                input_tokens_estimate=input_tokens,
                output_tokens_estimate=output_tokens,
                elapsed_ms=elapsed_ms,
                attempt_count=attempt_count,
                purpose=purpose,
                status=status,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "limits": {
                "max_calls": self.max_calls,
                "max_input_tokens": self.max_input_tokens,
                "max_output_tokens": self.max_output_tokens,
                "max_total_tokens": self.max_total_tokens,
            },
            "used": {
                "calls": self.calls,
                "input_tokens_estimate": self.input_tokens,
                "output_tokens_estimate": self.output_tokens,
                "total_tokens_estimate": self.input_tokens + self.output_tokens,
            },
            "records": [record.to_dict() for record in self.records],
        }


@dataclass(slots=True)
class QwenProvider:


    api_key: str = field(repr=False)
    base_url: str = "https://run.v3.cm/v1"
    model: str = "qwen3.7-flash"
    default_timeout: int = 180
    retries: int = 2
    backoff_seconds: float = 0.5
    last_attempt_count: int = field(default=0, init=False)

    @classmethod
    def from_env(cls) -> "QwenProvider":
        api_key = os.environ.get("PATHLEX_LLM_API_KEY") or os.environ.get("V_API_KEY")
        if not api_key:
            raise LLMConfigurationError(
                "Missing LLM API key. Set PATHLEX_LLM_API_KEY (or V_API_KEY)."
            )
        return cls(
            api_key=api_key,
            base_url=(
                os.environ.get("PATHLEX_LLM_BASE_URL")
                or os.environ.get("V_API_BASE_URL")
                or "https://run.v3.cm/v1"
            ),
            model=os.environ.get("PATHLEX_LLM_MODEL", "qwen3.7-flash"),
            default_timeout=int(os.environ.get("PATHLEX_LLM_TIMEOUT", "180")),
            retries=max(0, int(os.environ.get("PATHLEX_LLM_RETRIES", "2"))),
        )

    def complete(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: int | None = None,
    ) -> str:
        if not messages:
            raise LLMResponseError("At least one message is required.")
        final_error: Exception | None = None
        for attempt in range(1, self.retries + 2):
            self.last_attempt_count = attempt
            try:
                response = chat_completion(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout or self.default_timeout,
                )
                if not isinstance(response, str) or not response.strip():
                    raise LLMResponseError("The model returned an empty response.")
                return response.strip()
            except (TimeoutError, OSError, RuntimeError, KeyError, ValueError) as exc:
                final_error = exc
                if attempt > self.retries:
                    break
                delay = self.backoff_seconds * (2 ** (attempt - 1))
                delay += random.random() * min(0.25, delay / 4)
                time.sleep(delay)
        message = str(final_error) if final_error else "unknown provider failure"

        raise LLMError(f"LLM request failed after {self.last_attempt_count} attempt(s): {message}")


@dataclass(slots=True)
class BudgetedProvider:


    provider: LLMProvider
    budget: CallBudget = field(default_factory=CallBudget)
    model: str = field(init=False)

    def __post_init__(self) -> None:
        self.model = self.provider.model

    def complete(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: int | None = None,
        purpose: str = "",
    ) -> str:
        reserved_attempts = max(1, int(getattr(self.provider, "retries", 0)) + 1)
        input_estimate = self.budget.check_before_call(
            messages, max_tokens, reserved_attempts=reserved_attempts
        )
        started = time.monotonic()
        try:
            response = self.provider.complete(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
        except Exception:
            elapsed_ms = round((time.monotonic() - started) * 1000)
            self.budget.record(
                model=self.model,
                input_tokens=input_estimate,
                output_text="",
                elapsed_ms=elapsed_ms,
                attempt_count=getattr(self.provider, "last_attempt_count", 1),
                purpose=purpose,
                status="failed",
            )
            raise
        elapsed_ms = round((time.monotonic() - started) * 1000)
        self.budget.record(
            model=self.model,
            input_tokens=input_estimate,
            output_text=response,
            elapsed_ms=elapsed_ms,
            attempt_count=getattr(self.provider, "last_attempt_count", 1),
            purpose=purpose,
        )
        return response


@dataclass(slots=True)
class ScriptedTestProvider:


    responder: Callable[[Sequence[Message]], str] | None = None
    responses: list[str] = field(default_factory=list)
    model: str = "ENGINEERING_TEST_DOUBLE"
    calls: list[list[Message]] = field(default_factory=list)
    is_test_double: bool = field(default=True, init=False)
    last_attempt_count: int = field(default=1, init=False)

    def complete(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: int | None = None,
    ) -> str:
        del temperature, max_tokens, timeout
        copied = [dict(message) for message in messages]
        self.calls.append(copied)
        if self.responder is not None:
            result = self.responder(copied)
        elif self.responses:
            result = self.responses.pop(0)
        else:
            raise LLMResponseError("Engineering test provider has no scripted response.")
        if not isinstance(result, str) or not result.strip():
            raise LLMResponseError("Engineering test provider returned an empty response.")
        return result


_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def extract_json(text: str) -> Any:


    if not isinstance(text, str) or not text.strip():
        raise LLMResponseError("Cannot parse an empty model response.")
    cleaned = _FENCE_RE.sub("", text.strip()).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    starts = [(cleaned.find("{"), "{"), (cleaned.find("["), "[")]
    starts = [(index, token) for index, token in starts if index >= 0]
    if not starts:
        raise LLMResponseError("Model response does not contain JSON.")
    start, opening = min(starts, key=lambda pair: pair[0])
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(cleaned)):
        char = cleaned[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                candidate = cleaned[start : index + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError as exc:
                    raise LLMResponseError(f"Malformed JSON response: {exc.msg}") from exc
    raise LLMResponseError("Model response contains incomplete JSON.")


def require_object(value: Any, *, context: str = "model response") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LLMResponseError(f"{context} must be a JSON object.")
    return value


def complete_json(
    provider: LLMProvider,
    messages: Sequence[Message],
    *,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    timeout: int | None = None,
    purpose: str = "",
) -> dict[str, Any]:


    if isinstance(provider, BudgetedProvider):
        raw = provider.complete(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            purpose=purpose,
        )
    else:
        raw = provider.complete(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
    return require_object(extract_json(raw), context=purpose or "model response")

