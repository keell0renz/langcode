from jupyter_client.blocking.client import BlockingKernelClient
from jupyter_client.manager import KernelManager

from typing import Union
import threading
import queue
import time
import re
import os

os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"


class Jupyter:
    """A stateful Jupyter notebook for Python code execution."""

    def __init__(self, km: KernelManager, kc: BlockingKernelClient):
        self.km = km
        self.kc = kc

        self.kc.wait_for_ready()

        self.listener_thread: Union[threading.Thread, None] = None
        self.finish_flag = False

    @classmethod
    def local(cls, env: Union[str, None] = None):
        """Launch a local Jupyter environment."""

        if env:
            if os.path.isdir(env):
                raise ValueError(
                    f"The env path '{env}' is a directory, not a Python executable."
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

        return cls(km, kc)

    def stream_cell(self, code: str, timeout: Union[int, None] = None):
        """Run the cell and yield output including text, images, etc."""

        self.kc.wait_for_ready()

        self.finish_flag = False

        message_queue: queue.Queue = queue.Queue()

        self._execute_code(code, message_queue, timeout)

        return self._capture_output(message_queue)

    def run_cell(self, code: str, timeout: Union[int, None] = None):
        """Run the cell and output final code result."""

        self.kc.wait_for_ready()

        output = ""
        for chunk in self.stream_cell(code, timeout):
            if chunk["type"] == "console" and chunk["format"] == "output":
                output += chunk["content"]
            elif chunk["type"] == "timeout":
                raise TimeoutError("Timeout has passed!")

        return output

    def _execute_code(self, code, message_queue, timeout):
        def iopub_message_listener():
            start_time = time.time()

            while not self.finish_flag or not message_queue.empty():
                try:
                    if timeout is not None and (time.time() - start_time) * 1000 >= timeout:
                        message_queue.put(
                            {
                                "type": "timeout",
                                "format": "signal",
                                "content": "Timeout has passed!"
                            }
                        )
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
                            "type": "console",
                            "format": "output",
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
                            "type": "console",
                            "format": "output",
                            "content": content,
                        }
                    )
                elif msg["header"]["msg_type"] in ["display_data", "execute_result"]:
                    data = content["data"]
                    if "image/png" in data:
                        message_queue.put(
                            {
                                "type": "image",
                                "format": "base64.png",
                                "content": data["image/png"],
                            }
                        )
                    elif "image/jpeg" in data:
                        message_queue.put(
                            {
                                "type": "image",
                                "format": "base64.jpeg",
                                "content": data["image/jpeg"],
                            }
                        )
                    elif "text/html" in data:
                        message_queue.put(
                            {
                                "type": "code",
                                "format": "html",
                                "content": data["text/html"],
                            }
                        )
                    elif "text/plain" in data:
                        message_queue.put(
                            {
                                "type": "console",
                                "format": "output",
                                "content": data["text/plain"],
                            }
                        )
                    elif "application/javascript" in data:
                        message_queue.put(
                            {
                                "type": "code",
                                "format": "javascript",
                                "content": data["application/javascript"],
                            }
                        )

        self.listener_thread = threading.Thread(target=iopub_message_listener)
        self.listener_thread.start()

        self.kc.execute(code, stop_on_error=True)

    def _capture_output(self, message_queue):
        while not self.finish_flag or not message_queue.empty():
            try:
                msg = message_queue.get(timeout=0.1)
                yield msg
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

    def close(self):
        """Closes the Jupyter notebook and shutdowns the kernel."""

        self.stop_execution()
        self.kc.stop_channels()
        self.km.shutdown_kernel()
