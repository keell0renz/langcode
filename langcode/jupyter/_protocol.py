"""
Defines a protocol interface for Jupyter code interpreter API.
"""

from typing import Protocol, Literal, List, Union, Generator
from dataclasses import dataclass


@dataclass
class ExecutionEvent:
    """
    An execution event which can be outputted in real time into user UI iteratively.
    """

    msg_type: Literal["stream", "error", "display_data", "execute_result"]
    content_type: Literal["console", "image", "code"]
    content_format: Literal["output", "base64.png", "base65.jpeg", "html", "javascript"]
    content: str


@dataclass
class Base64ImageString:
    """Represents an image in `base64` form, either `png` or `jpeg`."""

    content_format: Literal["png", "jpeg"]
    content: str


@dataclass
class ExecutionResult:
    """
    Final result of code execution inside Jupyter notebook.
    """

    events: List[ExecutionEvent]
    """List of all `ExecutionEvent` events outputted during execution."""

    error: bool
    """Signals whether an error has occured during execution, `True` if error occured."""

    text: str
    """Final text, excluding images, which can be injected into LLM."""

    images: List[Base64ImageString]
    """Final list of `base64` images outputted during execution, can be injected into LLM."""


class Jupyter(Protocol):
    """
    Protocol describing Jupyter code interpreter class.
    """

    def stream_cell(
        self, code: str, timeout: Union[int, None] = None
    ) -> Generator[ExecutionEvent, None, None]:
        raise NotImplementedError()

    def run_cell(self, code: str, timeout: Union[int, None] = None) -> ExecutionResult:
        raise NotImplementedError()

    def stop_execution(self) -> None:
        raise NotImplementedError()

    def restart(self) -> None:
        raise NotImplementedError()

    def close(self) -> None:
        raise NotImplementedError()
