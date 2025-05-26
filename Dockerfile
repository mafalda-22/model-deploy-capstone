FROM python:3.12-slim

# 1. Install git & git-lfs so we can fetch your large files
RUN apt-get update \
 && apt-get install -y git git-lfs --no-install-recommends \
 && rm -rf /var/lib/apt/lists/* \
 && git lfs install

WORKDIR /opt/ml_in_app

# 2. Copy your code and pointers
COPY . .

# 3. Pull down the actual CSVs from LFS
RUN git lfs pull

# 4. Install Python deps
RUN pip install --no-cache-dir -r requirements_prod.txt

# 5. Expose & run
EXPOSE 5000
CMD ["python", "api_server_3.py"]
