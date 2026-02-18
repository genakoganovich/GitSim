from dataclasses import dataclass
from typing import Dict, Any, List, Tuple

import yaml


@dataclass
class Command:
    name: str
    params: Dict[str, Any]


def format_command(cmd: Command) -> str:
    """commit(message='c1 on main')"""
    if not cmd.params:
        return f"{cmd.name}()"
    params_str = ", ".join(f"{k}={v!r}" for k, v in cmd.params.items())
    return f"{cmd.name}({params_str})"


def load_default_commands() -> List[Command]:
    """Текущий «зашитый» сценарий."""
    raw_commands: List[Tuple[str, Dict[str, Any]]] = [
        ("init", {}),
        ("commit", {"message": "c1 on main"}),
        ("commit", {"message": "c2 on main"}),
        ("branch", {"name": "feature"}),
        ("checkout", {"name": "feature"}),
        ("commit", {"message": "c3 on feature"}),
        ("checkout", {"name": "main"}),
        ("merge", {"branch_name": "feature", "message": "Merge feature into main"}),
    ]
    return [Command(name, params) for name, params in raw_commands]


def load_commands_from_yaml(path: str) -> List[Command]:
    """
    Ожидаемый формат YAML:

    commands:
      - name: init
        params: {}
      - name: commit
        params:
          message: "c1 on main"
    """
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    items = data.get("commands", [])
    commands: List[Command] = []
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Команда #{idx} в YAML должна быть объектом, а не {type(item)}")
        name = item.get("name")
        if not isinstance(name, str):
            raise ValueError(f"Команда #{idx} в YAML: поле 'name' обязательно и должно быть строкой")
        params = item.get("params") or {}
        if not isinstance(params, dict):
            raise ValueError(f"Команда #{idx} в YAML: 'params' должен быть объектом")
        commands.append(Command(name=name, params=params))
    return commands
