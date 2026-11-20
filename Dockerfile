FROM python:3.12-slim

WORKDIR /app

# Dependencies first (better layer caching).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY src/ ./src/

# One research run, then exit. Keys come from the environment at run time:
#   docker run --rm -e NEBIUS_API_KEY=... -e TAVILY_API_KEY=... <image> \
#       "Your research question here"
CMD ["python", "app.py"]
