from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunbookSection:
    title: str
    content: str


class RunbookService:
    def __init__(
        self,
        runbook_path: str,
        domain: str,
        max_chars: int = 18000,
        category_map: dict[str, list[str]] | None = None,
    ):
        self.runbook_path = Path(runbook_path)
        self.domain = domain
        self.max_chars = max_chars
        self.category_map = category_map or {}
        self._content: str | None = None
        self._sections: list[RunbookSection] | None = None

    def reload(self) -> None:
        self._content = None
        self._sections = None
        self.load()

    def load(self) -> str:
        if self._content is None:
            if not self.runbook_path.exists():
                raise FileNotFoundError(f"Runbook not found: {self.runbook_path}")
            self._content = self.runbook_path.read_text(encoding="utf-8")
        return self._content

    def get_context_for_category(
        self, category: str, fallback_text: str | None = None
    ) -> str:
        base_sections = [
            "Purpose",
            "Safety Rules",
            "Agent Output Format",
            "Common Context to Gather",
            "Severity Model",
            "ServiceNow Incident Guidance",
            "Human Approval Matrix",
            "Agent Decision Rules",
        ]
        wanted_titles = base_sections + self.category_map.get(category, [])
        parts: list[str] = []
        for title in wanted_titles:
            sec = self.get_section_by_title(title)
            if sec:
                parts.append(f"# {sec.title}\n\n{sec.content.strip()}")
        if not parts and fallback_text:
            parts.append(f"# Fallback Context\n\n{fallback_text}")
        return self._truncate("\n\n---\n\n".join(parts))

    def get_section_by_title(self, title: str) -> RunbookSection | None:
        wanted = self._normalize(title)
        for sec in self._parse_sections():
            if self._normalize(sec.title) == wanted:
                return sec
        return None

    def _parse_sections(self):
        if self._sections is not None:
            return self._sections
        pattern = re.compile(
            r"^(#{1,2})\s+(.+?)\s*$([\s\S]*?)(?=^#{1,2}\s+|\Z)", re.MULTILINE
        )
        self._sections = [
            RunbookSection(m.group(2).strip(), m.group(3).strip())
            for m in pattern.finditer(self.load())
        ]
        return self._sections

    def _truncate(self, value: str) -> str:
        return (
            value
            if len(value) <= self.max_chars
            else value[: self.max_chars]
            + "\n\n[Runbook context truncated due to prompt-size limit.]"
        )

    @staticmethod
    def _normalize(title: str) -> str:
        title = title.lower().strip()
        title = re.sub(r"^\d+\.\s*", "", title)
        title = re.sub(r"[^a-z0-9]+", " ", title)
        return " ".join(title.split())
