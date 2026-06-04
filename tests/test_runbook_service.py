from pathlib import Path
from src.services.runbook_service import RunbookService

def test_runbook_section_selection(tmp_path: Path):
    runbook = tmp_path / "runbook.md"
    runbook.write_text("# Purpose\n\nPurpose text\n\n## Safety Rules\n\nRules\n\n## Agent Output Format\n\nFormat\n\n## High CPU Utilization\n\nCPU guidance\n", encoding="utf-8")
    service = RunbookService(str(runbook), "database", category_map={"aurora_high_cpu": ["High CPU Utilization"]})
    context = service.get_context_for_category("aurora_high_cpu")
    assert "Purpose text" in context
    assert "CPU guidance" in context
