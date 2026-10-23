FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml /app/
COPY touchstone /app/touchstone
RUN pip install --no-cache-dir .
WORKDIR /runs
ENTRYPOINT ["touchstone"]
CMD ["oracle", "--out", "/runs/oracle"]
