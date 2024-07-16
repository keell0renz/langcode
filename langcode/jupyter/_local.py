from jupyter_client.manager import KernelManager

from langcode.jupyter._protocol import (
    Jupyter,
    ExecutionEvent,
    ExecutionResult,
    Base64ImageString,
)

from typing import Union, Callable, Generator, List
import threading
import queue
import time
import re
import os

os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"


class LocalJupyter(Jupyter):
    """Local stateful Jupyter notebook interface."""

    def __init__(
        self,
        env: Union[str, None] = None,
        timeout: Union[int, None] = None,
        event_handler: Union[Callable[[ExecutionEvent], None], None] = None,
    ):

        self.timeout: Union[int, None] = timeout
        self.event_handler: Union[Callable[[ExecutionEvent], None], None] = (
            event_handler
        )

        self.closed = False

        if env:
            if os.path.isdir(env):
                raise ValueError(
                    f"The env path '{env}' is a directory, not a Python executable."
                )
            if not os.path.isfile(env) or not os.access(env, os.X_OK):
                raise ValueError(
                    f"The env path '{env}' is not a valid Python executable."
                )
            python_executable_path = env
        else:
            python_executable_path = "python3"  # Default to system Python

        km = KernelManager(
            kernel_name="python3",
            kernel_spec={
                "argv": [
                    python_executable_path,
                    "-m",
                    "ipykernel_launcher",
                    "-f",
                    "{connection_file}",
                ],
                "display_name": "Python 3",
                "language": "python",
            },
        )

        km.start_kernel()
        kc = km.client()
        kc.start_channels()
        self.km = km
        self.kc = kc

        self.kc.wait_for_ready()

        self.listener_thread: Union[threading.Thread, None] = None
        self.finish_flag = False

    def stream_cell(
        self, code: str, timeout: Union[int, None] = None
    ) -> Generator[ExecutionEvent, None, None]:
        """Run the cell and yield output including text, images, etc."""

        if self.closed:
            raise RuntimeError(
                "The Jupyter code interpreter has been closed! Instantiate a new one!"
            )

        self.kc.wait_for_ready()

        self.finish_flag = False

        message_queue: queue.Queue[dict] = queue.Queue()

        timeout = self.timeout if timeout is None else timeout

        self._execute_code(code, message_queue, timeout)

        return self._capture_output(message_queue)

    def run_cell(self, code: str, timeout: Union[int, None] = None) -> ExecutionResult:
        """Run the cell and output final code result."""

        if self.closed:
            raise RuntimeError(
                "The Jupyter code interpreter has been closed! Instantiate a new one!"
            )

        # self.kc.wait_for_ready()

        text = ""

        events: List[ExecutionEvent] = []

        error = False

        images: List[Base64ImageString] = []

        for event in self.stream_cell(code, timeout):
            events.append(event)

            if event.content_type == "image" and event.content_format in [
                "base64/png",
                "base64/jpeg",
            ]:
                images.append(
                    Base64ImageString(
                        content_format="jpeg" if event.content_format == "base64/jpeg" else "png",
                        content=event.content  # type: ignore
                    )
                )
            else:
                text += event.content

            if event.msg_type == "error":
                error = True

        return ExecutionResult(events, error, text, images)

    def _execute_code(self, code, message_queue, timeout):
        def iopub_message_listener():
            start_time = time.time()

            while not self.finish_flag or not message_queue.empty():
                try:
                    if (
                        timeout is not None
                        and (time.time() - start_time) * 1000 >= timeout
                    ):
                        message_queue.put({"signal": "timeout"})
                        self.finish_flag = True
                        self.km.interrupt_kernel()
                        break

                    msg = self.kc.iopub_channel.get_msg(timeout=0.1)
                except queue.Empty:
                    continue

                if (
                    msg["header"]["msg_type"] == "status"
                    and msg["content"]["execution_state"] == "idle"
                ):
                    self.finish_flag = True
                    break

                content = msg["content"]

                if msg["header"]["msg_type"] == "stream":
                    message_queue.put(
                        {
                            "signal": None,
                            "msg_type": "stream",
                            "content_type": "console",
                            "content_format": "output",
                            "content": content["text"],
                        }
                    )
                elif msg["header"]["msg_type"] == "error":
                    content = "\n".join(content["traceback"])
                    # Remove color codes
                    ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
                    content = ansi_escape.sub("", content)
                    message_queue.put(
                        {
                            "signal": None,
                            "msg_type": "error",
                            "content_type": "console",
                            "content_format": "output",
                            "content": content,
                        }
                    )
                elif msg["header"]["msg_type"] in ["display_data", "execute_result"]:
                    data = content["data"]
                    if "image/png" in data:
                        message_queue.put(
                            {
                                "signal": None,
                                "msg_type": msg["header"]["msg_type"],
                                "content_type": "image",
                                "content_format": "base64/png",
                                "content": data["image/png"],
                            }
                        )
                    elif "image/jpeg" in data:
                        message_queue.put(
                            {
                                "signal": None,
                                "msg_type": msg["header"]["msg_type"],
                                "content_type": "image",
                                "content_format": "base64/jpeg",
                                "content": data["image/jpeg"],
                            }
                        )
                    elif "text/html" in data:
                        message_queue.put(
                            {
                                "signal": None,
                                "msg_type": msg["header"]["msg_type"],
                                "content_type": "code",
                                "content_format": "html",
                                "content": data["text/html"],
                            }
                        )
                    elif "text/plain" in data:
                        message_queue.put(
                            {
                                "signal": None,
                                "msg_type": msg["header"]["msg_type"],
                                "content_type": "console",
                                "content_format": "output",
                                "content": data["text/plain"],
                            }
                        )
                    elif "application/javascript" in data:
                        message_queue.put(
                            {
                                "signal": None,
                                "msg_type": msg["header"]["msg_type"],
                                "content_type": "code",
                                "content_format": "javascript",
                                "content": data["application/javascript"],
                            }
                        )

        self.listener_thread = threading.Thread(target=iopub_message_listener)
        self.listener_thread.start()

        self.kc.execute(code, stop_on_error=True)

    def _capture_output(self, message_queue) -> Generator[ExecutionEvent, None, None]:
        while not self.finish_flag or not message_queue.empty():
            try:
                msg = message_queue.get(timeout=0.1)

                if msg["signal"] == "timeout":
                    raise TimeoutError("Timeout has elapsed during code execution!")

                event = ExecutionEvent(
                    msg_type=msg["msg_type"],
                    content_type=msg["content_type"],
                    content_format=msg["content_format"],
                    content=msg["content"],
                )

                if self.event_handler is not None:
                    self.event_handler(event)

                yield event
            except queue.Empty:
                continue

    def stop_execution(self):
        """Stops the current running execution process."""

        self.finish_flag = True
        if self.listener_thread is None:
            return
        if self.listener_thread.is_alive():
            self.km.interrupt_kernel()
            self.listener_thread.join()

    def restart(self):
        """Clears the cell state by restarting the kernel."""

        if self.closed:
            raise RuntimeError(
                "The Jupyter code interpreter has been closed! Instantiate a new one!"
            )

        self.stop_execution()
        self.km.restart_kernel(now=True)
        self.kc.wait_for_ready()

    def close(self):
        """Closes the Jupyter notebook and shutdowns the kernel."""

        self.closed = True

        self.stop_execution()
        self.kc.stop_channels()
        self.km.shutdown_kernel()
