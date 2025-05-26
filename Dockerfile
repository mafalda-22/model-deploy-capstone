# Use a slim base image
FROM python:3.12-slim

# Create and switch to a non-root user for security
RUN useradd --create-home appuser
WORKDIR /home/appuser

# Install Python dependencies first (cacheable layer)
COPY requirements_prod.txt .
RUN pip install --no-cache-dir -r requirements_prod.txt

# Copy your application code, the feature DB, and pickles/JSON
COPY --chown=appuser:appuser . .

# Expose the port your Flask app uses
EXPOSE 5000

# Run as non-root
USER appuser

# Launch your API server:
# If you're OK with Flask's built-in server (dev mode), use:
CMD ["python", "api_server_3.py"]
