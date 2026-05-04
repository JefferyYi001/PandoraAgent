"""
Skill loader - parses SKILL.md frontmatter and extracts prompt content
"""

import os
import re
import yaml

from utils.logger import logger


class SkillLoader:
    """Loads a skill from a SKILL.md file with YAML frontmatter"""

    @staticmethod
    def load(path: str) -> dict:
        """Parse SKILL.md and return skill metadata"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to load skill from {path}: {e}")
            return {}

        # Parse frontmatter
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
        if not match:
            logger.warning(f"No frontmatter found in {path}, using defaults")
            return {"name": os.path.basename(os.path.dirname(path)), "prompt": content}

        frontmatter = yaml.safe_load(match.group(1)) or {}
        body = match.group(2).strip()

        return {
            "name": frontmatter.get("name", os.path.basename(os.path.dirname(path))),
            "description": frontmatter.get("description", ""),
            "trigger": frontmatter.get("trigger", ""),
            "prompt": body,
        }
