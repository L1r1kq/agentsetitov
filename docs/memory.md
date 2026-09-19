# Память — разбор для защиты

Тезис: **vanilla RAG не годится как единственная память агента.** Аргументы, сравнение MemGPT/GraphRAG/Zep/OpenClaw и недостатки HCM — [REPORT.md §8](REPORT.md).

Слои Agentse:

| Слой | Носитель | Контракт |
|---|---|---|
| Identity | SOUL, IDENTITY, AGENTS, USER | всегда в бутстрапе, бюджет символов |
| Semantic curated | MEMORY.md | только решения/факты, не чат |
| Episodic | SQLite FTS + daily md | поиск, не полный промпт |
| Graph | entities/relations + decay | multi-hop «кто связан» |
| Procedural | skills/*/SKILL.md | как делать, не что помнить |
| Working | LangGraph state | текущая задача |

Поиск: lexical + graph + recency. Эмбеддинги — опция, не религия.
