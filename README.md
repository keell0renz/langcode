# 💻🔗 LangCode

## Concept

Currently it is in the prototype stage, and below you can see the vision for this project.

Now you can experiment with LangCode locally in a basic way.

### Jupyter Interface (Concept)

```python
from langcode.jupyter import Jupyter

jupyter = Jupyter.local(
    cwd="./",
    env="...",
    timeout=None,
    event_handler: lambda x: process_execution_event(x)
)

jupyter.cwd("./../../")

jupyter.environ["..."] = "..."

result: ExecutionResult = jupyter.run_cell(code="...", timeout=...)

for event in jupyter.stream_cell(code="...", timeout=...):
    event: ExecutionEvent

jupyter.close()
```

Remote connections coming soon...

```python
jupyter = Jupyter.from_remote(
    url="https://localhost:8888",
    timeout=None,
    event_handler: lambda x: process_execution_event(x)
)
```

Got inspired and borrowed the code from [Open Interpreter](https://github.com/OpenInterpreter/open-interpreter) and [E2B Code Interpreter](https://github.com/e2b-dev/code-interpreter)
