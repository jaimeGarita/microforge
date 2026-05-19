"""Jinja template rendering for generated projects."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape


class TemplateRenderer:
    """Render text templates from a filesystem template directory."""

    def __init__(self, template_dir: Path):
        self.environment = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(disabled_extensions=("j2",)),
            keep_trailing_newline=True,
            lstrip_blocks=True,
            trim_blocks=True,
            undefined=StrictUndefined,
        )

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        template = self.environment.get_template(template_name)
        return template.render(**context)
