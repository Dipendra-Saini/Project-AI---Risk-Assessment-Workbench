from dataclasses import dataclass
from functools import lru_cache
from string import Template

import yaml

from raw.settings import get_settings


@dataclass(frozen=True)
class Prompt:
    id: str
    version: str
    model_tier: str
    max_output_tokens: int
    temperature: float
    system: str
    user: str

    def render(self, variables: dict[str, str]) -> tuple[str, str]:
        return Template(self.system).substitute(variables), Template(self.user).substitute(variables)


@lru_cache
def load_prompt(prompt_id: str) -> Prompt:
    path = get_settings().prompts_dir / f"{prompt_id}.yaml"
    d = yaml.safe_load(path.read_text())
    return Prompt(
        id=d["id"],
        version=str(d["version"]),
        model_tier=d["model_tier"],
        max_output_tokens=int(d["max_output_tokens"]),
        temperature=float(d.get("temperature", 0)),
        system=d["system"],
        user=d["user"],
    )
