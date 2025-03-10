import typer

from .cli import app_typer

click_app = typer.main.get_command(app_typer)
