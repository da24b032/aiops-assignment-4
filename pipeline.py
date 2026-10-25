"""Core captioning workflow (no Streamlit imports) plus all metric updates.
Because it is UI-free, the metrics can be exercised from a plain Python script."""
import io
import os
import time
import zipfile
from typing import Callable, Optional

from PIL import Image, UnidentifiedImageError

import metrics as m
from captioner import shrink_and_rgb

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
MAX_ZIP_IMAGES = int(os.getenv("MAX_ZIP_IMAGES", "100"))
MAX_ZIP_UNCOMPRESSED = int(os.getenv("MAX_ZIP_UNCOMPRESSED_MB", "200")) * 1024 * 1024


def _run_one(captioner, data: bytes, mode: str, ip: str, sid: str):
    """Run one image through decode -> resize -> model. Returns (caption, None) or (None, message)."""
    m.IMG_BYTES_HIST.labels(mode).observe(len(data))
    m.UPLOAD_BYTES_TOTAL.labels(mode).inc(len(data))
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        m.IMAGE_PIXELS_SUMMARY.labels(mode).observe(img.width * img.height)
        img = shrink_and_rgb(img)
    except (UnidentifiedImageError, OSError, ValueError):
        m.ERR_COUNT.labels(mode, "bad_image").inc()
        m.IMG_COUNT.labels(mode, "error", ip).inc()
        return None, "not a valid image"

    started = time.perf_counter()
    try:
        text = captioner.caption(img)
    except Exception as exc:  # model failure
        m.ERR_COUNT.labels(mode, "inference").inc()
        m.IMG_COUNT.labels(mode, "error", ip).inc()
        return None, f"inference failed: {exc}"
    dt = time.perf_counter() - started

    m.INFER_HIST.labels(mode).observe(dt)
    m.INFER_SUMMARY.labels(mode).observe(dt)
    m.INFERENCE_SECONDS_TOTAL.labels(mode).inc(dt)
    m.CAPTION_LENGTH_SUMMARY.labels(mode).observe(len(text))
    m.CAPTION_CHARS_TOTAL.labels(mode).inc(len(text))
    m.IMG_COUNT.labels(mode, "success", ip).inc()
    m.LAST_OK_TS.set_to_current_time()
    return text, None


def handle_single_upload(captioner, data: bytes, ip: str, sid: str):
    mode = "single"
    m.SESSION_COUNT.labels(sid, mode).inc()
    m.IN_FLIGHT.labels(mode).inc()
    started = time.perf_counter()
    try:
        text, err = _run_one(captioner, data, mode, ip, sid)
        m.REQ_COUNT.labels(mode, "success" if err is None else "error", ip).inc()
        return text, err
    finally:
        m.REQ_HIST.labels(mode).observe(time.perf_counter() - started)
        m.IN_FLIGHT.labels(mode).dec()


def handle_zip_upload(
    captioner,
    zip_bytes: bytes,
    ip: str,
    sid: str,
    progress: Optional[Callable[[int, int, str], None]] = None,
):
    """Caption every image in a ZIP. Returns (rows, error); rows = [{'file', 'caption', 'error'}]."""
    mode = "bulk"
    m.SESSION_COUNT.labels(sid, mode).inc()
    m.ZIP_BYTES_SUMMARY.observe(len(zip_bytes))
    m.IN_FLIGHT.labels(mode).inc()
    started = time.perf_counter()
    status = "success"
    try:
        try:
            archive = zipfile.ZipFile(io.BytesIO(zip_bytes))
        except zipfile.BadZipFile:
            status = "error"
            m.ERR_COUNT.labels(mode, "bad_zip").inc()
            return [], "Not a valid ZIP file"

        picked = []
        total = 0
        for info in archive.infolist():
            low = info.filename.lower()
            if info.is_dir() or "__macosx" in low or os.path.basename(low).startswith("."):
                continue
            if not low.endswith(IMAGE_EXTS):
                m.ZIP_SKIPS.labels("not_image").inc()
                continue
            total += info.file_size
            if total > MAX_ZIP_UNCOMPRESSED:  # zip-bomb guard
                m.ZIP_SKIPS.labels("too_large").inc()
                status = "error"
                m.ERR_COUNT.labels(mode, "zip_too_large").inc()
                return [], f"ZIP expands beyond {MAX_ZIP_UNCOMPRESSED // 2**20} MB limit"
            picked.append(info)
        if len(picked) > MAX_ZIP_IMAGES:
            m.ZIP_SKIPS.labels("over_limit").inc(len(picked) - MAX_ZIP_IMAGES)
            picked = picked[:MAX_ZIP_IMAGES]
        if not picked:
            status = "error"
            m.ERR_COUNT.labels(mode, "empty_zip").inc()
            return [], "No images found in the ZIP"

        m.BULK_BATCH_SIZE.observe(len(picked))
        rows, n = [], len(picked)
        m.BULK_LEFT.set(n)
        m.BULK_DONE_RATIO.set(0)
        for i, info in enumerate(picked, 1):
            text, err = _run_one(captioner, archive.read(info), mode, ip, sid)
            rows.append({"file": info.filename, "caption": text or "", "error": err or ""})
            m.BULK_DONE_RATIO.set(i / n)
            m.BULK_LEFT.set(n - i)
            if progress:
                progress(i, n, info.filename)
        if any(r["error"] for r in rows):
            status = "partial"
        return rows, None
    finally:
        m.BULK_DONE_RATIO.set(0)
        m.BULK_LEFT.set(0)
        m.REQ_COUNT.labels(mode, status, ip).inc()
        m.REQ_HIST.labels(mode).observe(time.perf_counter() - started)
        m.IN_FLIGHT.labels(mode).dec()
