"""
SkillManager - loads builtin skills from SKILL.md files, generates prompt fragments
"""

import os
import glob

from agent.skills.loader import SkillLoader
from utils.logger import logger


class SkillManager:
    _instance = None
    _skills: list[dict] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None
        cls._skills = []

    def load_skills(self, skills_dir: str = None) -> None:
        """Load all SKILL.md files from builtin directory"""
        from config.settings import get_settings
        settings = get_settings()
        dir_path = skills_dir or settings.skills_dir

        pattern = os.path.join(dir_path, "**", "SKILL.md")
        for path in glob.glob(pattern, recursive=True):
            skill = SkillLoader.load(path)
            if skill:
                self._skills.append(skill)
                logger.info(f"Loaded skill: {skill['name']}")

        logger.info(f"Loaded {len(self._skills)} skills")

    def list_skills(self) -> list[dict]:
        return [{"name": s["name"], "description": s["description"], "trigger": s["trigger"]}
                for s in self._skills]

    def generate_prompt(self) -> str:
        """Generate skills prompt fragment for LLM"""
        if not self._skills:
            return ""
        lines = ["## Available Skills", ""]
        for skill in self._skills:
            lines.append(f"### {skill['name']}")
            lines.append(skill["prompt"])
            lines.append("")
        return "\n".join(lines)

    def get_skill(self, name: str) -> dict | None:
        for skill in self._skills:
            if skill["name"] == name:
                return skill
        return None
