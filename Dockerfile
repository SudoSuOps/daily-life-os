# DailyLifeOS — portable on any hardware shell (ZimaCube / Synology / UGREEN / mini-PC / Jetson).
# Stdlib-only Python; no network code in the data path. PHI lives in the mounted volume, on the box.
FROM python:3.12-slim
WORKDIR /app
COPY core/ ./core/
COPY ld.py seed_demo.py ./
# data dir is config-driven; mount a volume here. Never a vendor-specific path.
ENV LD_DATA_DIR=/data
VOLUME ["/data"]
ENTRYPOINT ["python3", "ld.py"]
CMD ["status"]
