---
jupytext:
  text_representation:
    format_name: myst
kernelspec:
  display_name: Python 3
  name: python3
---

# Usage

An example for using ipython directives or jupytext

Simple python example:

```python
from uv_workon import example_function

a = 1
b = 2
print(example_function(a, b))
```

<!-- prettier-ignore-start -->
see, e.g., {py:meth}`~uv_workon.example_function`
<!-- prettier-ignore-end -->

## Executable

### jupytext

```{code-cell} ipython3

from uv_workon import example_function

a = 1
b = 2
```

```{code-cell} ipython3
print(example_function(a, b))
```

<!-- ### ipython directive -->

<!-- ipython example... -->

<!-- ```{eval-rst} -->
<!-- .. ipython:: python -->

<!--     from uv_workon import example_function -->

<!--     a = 1 -->
<!--     b = 2 -->
<!--     print(example_function(a, b)) -->
<!-- ``` -->
