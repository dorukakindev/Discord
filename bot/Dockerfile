FROM python:3.12-slim

WORKDIR /opt/lexicanum
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# data/ (index.json, guilds.json, log_channels.json) image içine girer;
# .env ve work/ dışarıdan mount edilir.
CMD ["python", "lexicanum.py"]
