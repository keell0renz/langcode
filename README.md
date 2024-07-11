# 💻🔗 LangCode

⚡ Build code-executing autonomous agents ⚡

## Documentation

💻🔗 LangCode is a library which provides easy-to-use and reliable interface to a Python code-execution environment, such as Jupyter. LangCode can be used to build autonomous code-executing agents. LangCode supports text, image and code output of Jupyter. Also remote connection feature and jupyter server launcher is planned for the future versions.

### Example

```bash
pip install langcode
```

`INTERESTING`: You can find `claude_agent.ipynb` in `examples` which demonstrates a real-world application of LangCode using Claude 3.5 Sonnet

```python
from langcode.jupyter import Jupyter, ExecutionEvent, ExecutionResult

def process_execution_event(x: ExecutionEvent) -> None:
    ...

jupyter = Jupyter.local(
    env="...", # Set the execution environment.
    timeout=None, # Set global timeout (can be overriden later).
    event_handler: lambda x: process_execution_event(x) # Pass event handler if you need.
)

result: ExecutionResult = jupyter.run_cell(code="x = 10; x", timeout=None) # Final result.

for event in jupyter.stream_cell(code="import time; time.sleep(5)", timeout=1000): # Or stream events in real time.
    event: ExecutionEvent

    # This will raise TimeoutError after 1 second.

jupyter.restart() # You can also restart kernel to clear the cell state.

jupyter.close() # Close the notebook and Jupyter kernel.
```

You can also get images outputted by Jupyter kernel:

```python
code = """
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 2 * np.pi, 200)
y = np.sin(x)

fig, ax = plt.subplots()
ax.plot(x, y)
ax.set(xlabel='x', ylabel='sin(x)',
       title='A simple plot')

plt.show()

"""

result = jupyter.run_cell(code)

result.images
```

```python
[Base64ImageString(content_format='png', content='iVBORw0KGg...')]
```

You can also get images in `ExecutionEvent` data transfer object when you use `stream_cell`.

Also you can stop the execution in the process if you need:

```python
jupyter.stop_execution()
```

Here are the data transfer objects which represent execution results:

```python
@dataclass
class ExecutionEvent:
    """
    An execution event which can be outputted in real time into user UI iteratively.
    """

    msg_type: Literal["stream", "error", "display_data", "execute_result"]
    content_type: Literal["console", "image", "code"]
    content_format: Literal["output", "base64.png", "base64.jpeg", "html", "javascript"]
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

    images: List[ImageString]
    """Final list of `base64` images outputted during execution, can be injected into LLM."""
```

Got inspired and borrowed the code from [Open Interpreter](https://github.com/OpenInterpreter/open-interpreter) and [E2B Code Interpreter](https://github.com/e2b-dev/code-interpreter)
