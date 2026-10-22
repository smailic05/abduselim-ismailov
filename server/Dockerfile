FROM python:3.13-slim

# pandoc converts Word files to HTML; LibreOffice handles old .doc files
RUN apt-get update \
 && (apt-get install -y --no-install-recommends pandoc libreoffice-writer-nogui \
     || apt-get install -y --no-install-recommends pandoc libreoffice-writer) \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY tools ./tools

ENV DATA_DIR=/data HOME=/tmp
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
