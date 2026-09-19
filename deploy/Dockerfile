FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY workspace /app/workspace
COPY skills /app/skills
COPY evals /app/evals

RUN pip install --no-cache-dir -e .

RUN useradd -m -u 10001 agentse && chown -R agentse:agentse /app
USER agentse

EXPOSE 8080 9108
CMD ["python", "-m", "agentse", "serve"]
