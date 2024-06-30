# 💻🔗 LangCode

## Concept

```python
from langcode.jupyter import Jupyter

jupyter = Jupyter.local(env="...")

jupyter.run_cell(
    code="print('Result!'); x = 1",
    timeout=10000 #ms
)
```

```txt
Result!
```

```python
jupyter.run_cell("x")
```

```txt
1
```
