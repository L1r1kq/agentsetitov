# TOOLS.md

Инструменты, которые существуют на самом деле. Если инструмента нет в этом списке — его нет.

| Имя | Контракт | Ограничение |
|---|---|---|
| memory_search | query, limit? | гибрид слоёв, не «просто эмбеддинги» |
| memory_write | fact, session_id?, kind? | kind=fact\|decision\|preference попадает в MEMORY.md |
| memory_get | path | только workspace |
| graph_neighbors | name | рёбра сущности |
| skill_load | name | skills/<name>/SKILL.md |
| workspace_read | path | workspace-root |
| workspace_write | path, content | нельзя SOUL.md / IDENTITY.md |
| sandbox_exec | code | Python без import/os/сети |
| calculate | expression | AST-whitelist арифметика |

Нет веб-поиска в дефолте: на 8 ГБ и в учебной изоляции внешний веб — отдельный сознательный риск (утечка промпта, недоверенный текст в душу).
