"""Enable `python -m open_notebook`"""

from .cli import app_typer

app_typer(prog_name="uv-workon")
