from typing import Callable, Union

from langcode.jupyter._protocol import Jupyter as _Jupyter
from langcode.jupyter._protocol import ExecutionEvent
from langcode.jupyter._local import LocalJupyter


class Jupyter(_Jupyter):
    """
    Jupyter notebook interface for code execution.
    """

    @classmethod
    def local(
        cls,
        env: Union[str, None] = None,
        timeout: Union[int, None] = None,
        event_handler: Union[Callable[[ExecutionEvent], None], None] = None,
    ) -> "Jupyter":
        return LocalJupyter(env, timeout, event_handler) # type: ignore
