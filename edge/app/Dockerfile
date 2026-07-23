FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /edge

COPY app/requirements.txt .

# Force deep-sort-realtime to use the headless variant instead of pulling full opencv.
# NOTE: opencv-python and opencv-python-headless both ship a `cv2` module to the same
# site-packages path. Installing one after the other overwrites files on disk, and later
# uninstalling either package deletes whatever `cv2` files are *currently* there - including
# ones that now "belong" to the other package. So opencv-python must never be installed at
# all, not installed-then-removed. We install deep-sort-realtime with --no-deps and supply
# its other real dependency (scipy) ourselves.
RUN pip install \
    --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt && \
    pip install --no-cache-dir --no-deps deep-sort-realtime

# Pre-download DeepSORT MobileNet weights at build time (headless, no display needed)
ENV MPLBACKEND=Agg
RUN python -c "from deep_sort_realtime.deepsort_tracker import DeepSort; DeepSort(embedder='mobilenet')"

# Copy the full app package (model baked in via app/models/)
COPY app/ ./app/

RUN mkdir -p ./app/logs

CMD ["python", "-m", "app.main"]