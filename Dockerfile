FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN rm -f mensabot.db
    # Should be either created fresh or mounted from the host

CMD ["python", "mensabot.py"]