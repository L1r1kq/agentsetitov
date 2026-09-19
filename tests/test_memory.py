from agentse.memory.store import HierarchicalMemory


def test_fact_and_search(tmp_path, monkeypatch):
    from agentse.config import Settings

    settings = Settings()
    object.__setattr__(settings, "workspace", tmp_path / "ws")
    object.__setattr__(settings, "data_dir", tmp_path / "data")
    settings.ensure_dirs()
    mem = HierarchicalMemory(settings)
    mem.remember_fact("выбрали Ollama как движок", [("ollama", "engine")])
    mem.relate("ollama", "serves", "qwen2.5:1.5b", "дефолтная модель")
    mem.write_episodic("s1", "note", "обсуждали почему RAG недостаточен")
    hits = mem.search("ollama rag")
    assert hits
    layers = {h.layer for h in hits}
    assert "identity" in layers or "graph" in layers or "episodic" in layers
    neighbors = mem.graph_neighbors("ollama")
    assert any("qwen2.5" in n for n in neighbors)
    mem.close()


def test_decay(tmp_path):
    from agentse.config import Settings

    settings = Settings()
    object.__setattr__(settings, "workspace", tmp_path / "ws")
    object.__setattr__(settings, "data_dir", tmp_path / "data")
    object.__setattr__(settings, "memory_decay", 0.5)
    settings.ensure_dirs()
    mem = HierarchicalMemory(settings)
    mem.upsert_entity("rag", "concept")
    before = mem.conn.execute("SELECT strength FROM entities WHERE name='rag'").fetchone()[0]
    mem.decay()
    after = mem.conn.execute("SELECT strength FROM entities WHERE name='rag'").fetchone()[0]
    assert after < before
    mem.close()
