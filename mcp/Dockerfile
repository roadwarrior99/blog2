FROM public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY mcp_server.py mcp_server.py

# DB is mounted at runtime via volume
ENV MCP_DB_PATH=/data/vacuumflask.db
ENV MCP_TRANSPORT=sse
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8001

EXPOSE 8001

CMD ["python3", "mcp_server.py"]