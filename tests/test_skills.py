from pathlib import Path


def test_skills_exist():
    root = Path(__file__).resolve().parents[1] / "skills"
    expected = [
        "planning",
        "research",
        "critique",
        "sandbox-code",
        "memory-curation",
        "eval-design",
    ]
    for name in expected:
        skill = root / name / "SKILL.md"
        assert skill.exists(), name
        text = skill.read_text(encoding="utf-8")
        assert "name:" in text
        assert len(text) > 200


def test_soul_files():
    ws = Path(__file__).resolve().parents[1] / "workspace"
    for name in ("SOUL.md", "IDENTITY.md", "AGENTS.md", "USER.md", "MEMORY.md"):
        assert (ws / name).exists()
        assert len((ws / name).read_text(encoding="utf-8")) > 200
