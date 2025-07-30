FROM python:3.11

WORKDIR /app

# Create a non-privileged user
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

# Switch to that user
#USER appuser

ADD main.py .
COPY *.py .
COPY *.json .

RUN mkdir -p www

# Copy and install dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "main.py"]
