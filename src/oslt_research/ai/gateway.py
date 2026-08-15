from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class ModelGatewayError(RuntimeError):
    """Raised when model use is disabled or violates the qualified gateway policy."""


@dataclass(frozen=True)
class ModelRequest:
    task_id: str
    system_prompt: str
    user_payload: str
    response_schema: dict[str, Any]
    sensitive_data_approved: bool = False


@dataclass(frozen=True)
class ModelResponse:
    model_alias: str
    output: dict[str, Any]
    input_tokens: int
    output_tokens: int
    trace_id: str


class ModelGateway(ABC):
    """The sole permitted model-provider boundary.

    Provider SDKs may be introduced only in this module after OSLT-specific qualification,
    configuration review, prompt fencing, tracing and environment-specific data approval.
    """

    @abstractmethod
    async def complete(self, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError


class DisabledModelGateway(ModelGateway):
    async def complete(self, request: ModelRequest) -> ModelResponse:
        raise ModelGatewayError(
            "MODEL_GATEWAY_DISABLED: qualification and explicit configuration are required"
        )
