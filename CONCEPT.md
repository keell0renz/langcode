# Local Jupyter Notebook

```python
from langcode.jupyter import Jupyter

jupyter = Jupyter.local(
    cwd="/.../.../...",
    python_env="...",
    env_vars={...},
    timeout=None,
    event_handler: lambda x: process_execution_event(x)
)

jupyter.list_kernels() -> list[Kernel]

kernel_object: Kernel = jupyter.kernel.new("name") # cannot use "default"

jupyter.kernel("name").close() # cannot close "default"

jupyter.kernel("name").interrupt()

jupyter.kernel("name").run_cell( 
    code="...",
    timeout=1000
) -> ExecutionResult

# Usage with no .kernel(...) is using "default" kernel.

jupyter.cwd("...") # Sets current working directory

jupyter.env({...}) # Extends env variables

jupyter.run_cell( # uses default kernel, also supports magic commands
    code="...",
    timeout=1000
) -> ExecutionResult 

for event in jupyter.stream_cell(code="..."):
    event: ExecutionEvent

jupyter.close() # closes all kernels, closes connection and kernel if .local()
```

## Remote Jupyter Notebook

```python
from langcode.jupyter import Jupyter

jupyter = Jupyter.from_remote(
    url="https://localhost:8888",
    timeout=None,
    event_handler: lambda x: process_execution_event(x)
)

...
```

## Self-Hosted Jupyter Server

```txt
root@linux# langcode run jupyter --host localhost:8888 --env ~/.../.../python3 --cwd ~/.../.../ --vars ./env.local
```

Got inspired and borrowed the code from [Open Interpreter](https://github.com/OpenInterpreter/open-interpreter) and [E2B Code Interpreter](https://github.com/e2b-dev/code-interpreter)
