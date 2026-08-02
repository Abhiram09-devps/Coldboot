FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates/ templates/
COPY static/ static/

# Generate a random secret key at build time isn't ideal (same key baked into
# every container run from this image). Pass SECRET_KEY at `docker run` time
# instead -- see README.md.
ENV SECRET_KEY=change-this-at-runtime

EXPOSE 5000

# Use shell form so $PORT (set automatically by Render, and by many other
# PaaS providers) is expanded at container start. Falls back to 5000 if
# PORT isn't set, e.g. when running the image locally.
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 app:app
