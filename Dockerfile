FROM python:3.11-slim

# Node is needed for the Filesystem MCP server (npx) in live mode
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/vendorguard

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY ui ./ui
COPY data ./data
COPY knowledge ./knowledge

ENV PORT=8080 \
    VENDORGUARD_KNOWLEDGE_DIR=/srv/vendorguard/knowledge

CMD streamlit run ui/streamlit_app.py --server.port=$PORT --server.address=0.0.0.0 \
    --server.headless=true --browser.gatherUsageStats=false
