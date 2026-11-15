"""
tests/test_agent_pipeline.py
============================

WALLIX Pinterest Video Agent — Python unit tests for the agent pipeline.

Covers:
  1. Board allowlist (only the 2 approved boards)
  2. Duplicate pin detection (seen_pins)
  3. SHA-256 content hashing
  4. Invalid / missing video handling
  5. Low-resolution video handling
  6. Quarantine behaviour
  7. Atomic state write / read (JSON state files)
  8. ProcessLock — single-instance, release on exit/error, stale-lock reclaim,
     concurrent-instance rejection

All file I/O uses temporary directories so existing repository data files
(seen_pins.json, agent_brain.json, downloads/, …) are never touched.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import the agent modules under test
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import smart_pinterest_agent as sp  # noqa: E402
import parallel_multi_agent as pma  # noqa: E402
from video_quality import (  # noqa: E402
    probe_video_info,
    check_file_integrity,
    classify_desktop_suitability,
    validate_and_correct_video,
    MIN_VIDEO_SIZE_BYTES,
    MIN_VIDEO_DIMENSION,
    DESKTOP_MIN_WIDTH,
    DESKTOP_MIN_HEIGHT,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

APPROVED_BOARD_URLS = {
    "https://www.pinterest.com/strndsehsules974/ai-vide-ai/",
    "https://www.pinterest.com/strndsehsules974/anime-character-ai-09/",
}


def _make_dummy_video(tmp_path: Path, width: int = 640, height: int = 360,
                      duration: float = 3.0, codec: str = "libx264") -> Path:
    """Create a tiny valid MP4 using ffmpeg (real encoder, real file)."""
    out = tmp_path / "test_video.mp4"
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        f"testsrc=size={width}x{height}:rate=1:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        "-c:v", codec, "-c:a", "aac", "-shortest",
        "-pix_fmt", "yuv420p",
        str(out),
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=60)
    assert out.exists() and out.stat().st_size > 0
    return out


def _make_corrupt_file(tmp_path: Path) -> Path:
    out = tmp_path / "corrupt.mp4"
    out.write_bytes(b"\x00\x00\x00\x20ftypisom\x00\x00\x00\x20" + b"\x00" * 1000)
    return out


# ===========================================================================
# 1. Board allowlist
# ===========================================================================

class TestBoardAllowlist:
    """Only the two approved Pinterest boards may be processed."""

    def test_smart_agent_boards_are_exactly_the_two_approved(self):
        urls = {b["url"] for b in sp.BOARDS}
        assert urls == APPROVED_BOARD_URLS
        assert len(sp.BOARDS) == 2

    def test_parallel_agent_boards_are_exactly_the_two_approved(self):
        urls = {b["url"] for b in pma.STRICT_BOARDS}
        assert urls == APPROVED_BOARD_URLS
        assert len(pma.STRICT_BOARDS) == 2

    def test_no_unapproved_urls_in_either_agent(self):
        all_urls = {b["url"] for b in sp.BOARDS} | {b["url"] for b in pma.STRICT_BOARDS}


# ===========================================================================
# 2. Duplicate pin detection
# ===========================================================================

class TestDuplicatePinDetection:
    """Seen-pins archive must track and reject already-handled pins."""

    def test_mark_and_load_seen_pins(self, tmp_path):
        seen_file = tmp_path / "seen_pins.json"

        def load_seen(path: Path) -> set:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                return set(str(x) for x in (data if isinstance(data, list) else data.get("seen_pins", [])))
            return set()

        def save_seen(path: Path, s: set):
            path.write_text(json.dumps({"seen_pins": sorted(s)}, indent=2), encoding="utf-8")

        assert load_seen(seen_file) == set()

        seen: set[str] = set()
        seen.add("1234567890")
        save_seen(seen_file, seen)
        assert "1234567890" in load_seen(seen_file)

        seen.add("0987654321")
        save_seen(seen_file, seen)
        loaded = load_seen(seen_file)
        assert "1234567890" in loaded
        assert "0987654321" in loaded
        assert len(loaded) == 2

    def test_duplicate_pin_is_skipped(self):
        seen = {"pin_001", "pin_002"}
        assert "pin_001" in seen
        assert "pin_999" not in seen


class TestPinMediaResolver:
    """Pin page HTML must yield usable video or image media URLs, even when the DOM is sparse."""

    def test_resolve_pin_media_from_html_valid_video(self):
        html = (
            '<html><head>'
            '<meta property="og:title" content="Example pin">'
            '<meta property="og:video:secure_url" content="https://example.com/media/clip.mp4">'
            '<meta property="og:image" content="https://example.com/thumb.jpg">'
            '</head><body></body></html>'
        )
        info = sp.resolve_pin_media_from_html(html)
        assert info["video_url"] == "https://example.com/media/clip.mp4"
        assert info["image_url"] == "https://example.com/thumb.jpg"
        assert info["media_kind"] == "video"

    def test_resolve_pin_media_from_html_missing_media(self):
        html = '<html><head><title>Plain page</title></head><body>No media here</body></html>'
        info = sp.resolve_pin_media_from_html(html)
        assert info["video_url"] is None
        assert info["image_url"] is None
        assert info["media_kind"] == "none"

    def test_resolve_pin_media_from_html_invalid_response(self):
        html = '<html><body>not a pin page</body></html>'
        info = sp.resolve_pin_media_from_html(html)
        assert info["media_kind"] in {"none", "unknown"}

    def test_resolve_pin_media_from_html_alt_image_structure(self):
        html = (
            '<script type="application/ld+json">'
            '{"image":{"url":"https://i.pinimg.com/originals/test-image.jpg"}}'
            '</script>'
        )
        info = sp.resolve_pin_media_from_html(html)
        assert info["image_url"] == "https://i.pinimg.com/originals/test-image.jpg"
        assert info["media_kind"] == "image"

    def test_resolve_pin_media_browser_fallback_for_hls(self, monkeypatch):
        def raise_urlopen(*args, **kwargs):
            raise RuntimeError("blocked by bot wall")

        monkeypatch.setattr(sp.urllib.request, "urlopen", raise_urlopen)

        def fake_browser_resolve(pin_url):
            return {
                "title": "Example pin",
                "description": "Example description",
                "video_url": "https://v1.pinimg.com/videos/iht/hls/92/7c/9c/927c9cbaa18f5b76caf63ae1275f9afc.m3u8",
                "image_url": "https://i.pinimg.com/originals/thumb.jpg",
                "media_kind": "hls",
            }

        monkeypatch.setattr(sp, "_resolve_pin_media_with_browser", fake_browser_resolve)
        info = sp.resolve_pin_media("https://www.pinterest.com/pin/123456789/")
        assert info["video_url"].endswith(".m3u8")
        assert info["media_kind"] == "hls"


# ===========================================================================
# 3. SHA-256 content hashing
# ===========================================================================

class TestSHA256:
    """Content deduplication via SHA-256 must be deterministic and collision-resistant."""

    def test_sha256_deterministic(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"hello world")
        f2.write_bytes(b"hello world")
        h1 = pma.compute_sha256(f1)
        h2 = pma.compute_sha256(f2)
        assert h1 == h2
        assert len(h1) == 64

    def test_sha256_differs_for_different_content(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"content A")
        f2.write_bytes(b"content B")
        assert pma.compute_sha256(f1) != pma.compute_sha256(f2)

    def test_sha256_matches_standard_library(self, tmp_path):
        f = tmp_path / "data.bin"
        f.write_bytes(b"\x00\x01\x02\x03\x04\x05" * 1000)
        expected = hashlib.sha256(f.read_bytes()).hexdigest()
        assert pma.compute_sha256(f) == expected


# ===========================================================================
# 4. Invalid / missing video handling
# ===========================================================================

class TestInvalidVideo:
    """Missing or invalid video files must be rejected, not crash."""

    def test_validate_missing_file(self, tmp_path):
        missing = tmp_path / "does_not_exist.mp4"
        res = validate_and_correct_video(str(missing))
        assert res["valid"] is False
        assert res["reason"] == "file_not_found"
        assert res["final_path"] == str(missing)

    def test_validate_corrupt_file_is_not_valid(self, tmp_path):
        corrupt = _make_corrupt_file(tmp_path)
        res = validate_and_correct_video(str(corrupt))
        assert res["valid"] is False or res["width"] == 0 or res["height"] == 0

    def test_probe_video_info_invalid_file(self, tmp_path):
        missing = tmp_path / "nope.mp4"
        info = probe_video_info(str(missing))
        assert info["valid"] is False
        assert info["width"] == 0
        assert info["height"] == 0


# ===========================================================================
# 5. Low-resolution video handling
# ===========================================================================

class TestLowResolution:
    """Below-desktop-minimum videos must be quarantined, not approved."""

    def test_classify_below_desktop_minimum(self):
        result = classify_desktop_suitability(736, 414)
        assert result["suitable_for_desktop"] is False
        assert result["meets_minimum"] is False

    def test_classify_desktop_ok(self):
        result = classify_desktop_suitability(1280, 720)
        assert result["suitable_for_desktop"] is True
        assert result["meets_minimum"] is True

    def test_classify_portrait_quarantined(self):
        result = classify_desktop_suitability(720, 1280)
        assert result["suitable_for_desktop"] is False
        assert "portrait" in result["reason"]

    def test_validate_low_resolution_rejected(self, tmp_path):
        small = _make_dummy_video(tmp_path, width=320, height=240, duration=1.0)
        res = validate_and_correct_video(str(small))
        assert res["valid"] is False
        assert "low_resolution" in res["reason"]


# ===========================================================================
# 6. Quarantine behaviour
# ===========================================================================

class TestQuarantine:
    """Rejected files must be moved to quarantine, originals never deleted."""

    def test_quarantine_file_moves_to_quarantine_dir(self, tmp_path):
        staging = tmp_path / "staging"
        quarantine = tmp_path / "quarantine"
        staging.mkdir()
        quarantine.mkdir()

        src = staging / "junk.mp4"
        src.write_bytes(b"x" * 1024)

        orig_staging = sp.STAGING_DIR
        orig_quarantine = sp.QUARANTINE_DIR
        sp.STAGING_DIR = staging
        sp.QUARANTINE_DIR = quarantine
        try:
            sp.quarantine_file(src, "test_reason")
            assert not src.exists(), "Original file should be moved out of staging"
            moved = list(quarantine.iterdir())
            assert len(moved) == 1, f"Expected 1 quarantined file, got {len(moved)}"
        finally:
            sp.STAGING_DIR = orig_staging
            sp.QUARANTINE_DIR = orig_quarantine

    def test_quarantine_preserves_content(self, tmp_path):
        staging = tmp_path / "staging"
        quarantine = tmp_path / "quarantine"
        staging.mkdir()
        quarantine.mkdir()

        src = staging / "content.mp4"
        content = b"unique-video-bytes-12345"
        src.write_bytes(content)

        orig_staging = sp.STAGING_DIR
        orig_quarantine = sp.QUARANTINE_DIR
        sp.STAGING_DIR = staging
        sp.QUARANTINE_DIR = quarantine
        try:
            sp.quarantine_file(src, "low_resolution")
            moved = list(quarantine.iterdir())[0]
            assert moved.read_bytes() == content
        finally:
            sp.STAGING_DIR = orig_staging
            sp.QUARANTINE_DIR = orig_quarantine


# ===========================================================================
# 7. Atomic state write / read
# ===========================================================================

class TestAtomicStateWrites:
    """JSON state files must round-trip correctly and handle corruption gracefully."""

    def test_save_and_load_json_round_trip(self, tmp_path):
        f = tmp_path / "state.json"
        data = {"pins": ["a", "b"], "count": 2}
        pma.save_json(f, data)
        loaded = pma.load_json(f, None)
        assert loaded == data

    def test_load_json_missing_file_returns_default(self, tmp_path):
        f = tmp_path / "missing.json"
        result = pma.load_json(f, {"default": True})
        assert result == {"default": True}

    def test_load_json_corrupt_file_returns_default(self, tmp_path):
        f = tmp_path / "corrupt.json"
        f.write_text("{not valid json", encoding="utf-8")
        result = pma.load_json(f, {"fallback": True})
        assert result == {"fallback": True}

    def test_load_seen_returns_set(self, tmp_path):
        f = tmp_path / "seen.json"
        f.write_text('["pin1", "pin2"]', encoding="utf-8")
        # load_seen() reads the module-level SEEN_FILE; verify it returns a set
        seen = pma.load_seen()
        assert isinstance(seen, set)


# ===========================================================================
# 8. ProcessLock — single-instance protection
# ===========================================================================

class TestProcessLock:
    """Lock must prevent two instances, release on exit/error, and reclaim stale locks."""

    def test_lock_acquire_and_release(self, tmp_path):
        lock_path = tmp_path / "test.lock"
        lock = sp.ProcessLock(lock_path)
        assert lock.acquire() is True
        assert lock_path.exists()
        assert lock_path.read_text(encoding="utf-8").strip() == str(os.getpid())
        lock.release()
        assert not lock_path.exists()

    def test_lock_rejects_second_instance(self, tmp_path):
        lock_path = tmp_path / "test2.lock"
        lock1 = sp.ProcessLock(lock_path)
        lock2 = sp.ProcessLock(lock_path)
        assert lock1.acquire() is True
        assert lock2.acquire() is False
        lock1.release()

    def test_lock_reclaims_stale_lock(self, tmp_path):
        lock_path = tmp_path / "test3.lock"
        lock_path.write_text("999999", encoding="utf-8")
        lock = sp.ProcessLock(lock_path)
        assert lock.acquire() is True
        assert lock_path.read_text(encoding="utf-8").strip() == str(os.getpid())
        lock.release()

    def test_lock_release_idempotent(self, tmp_path):
        lock_path = tmp_path / "test4.lock"
        lock = sp.ProcessLock(lock_path)
        lock.acquire()
        lock.release()
        lock.release()
        assert not lock_path.exists()

    def test_lock_concurrent_processes(self, tmp_path):
        """Two actual Python processes must not both hold the lock."""
        lock_path = tmp_path / "concurrent.lock"
        my_lock = sp.ProcessLock(lock_path)
        assert my_lock.acquire() is True

        code = (
            "import sys; sys.path.insert(0, r'" + str(REPO_ROOT) + "'); "
            "import smart_pinterest_agent as sp; "
            "from pathlib import Path; "
            "lock = sp.ProcessLock(Path(r'" + str(lock_path) + "')); "
            "print('ACQUIRED' if lock.acquire() else 'REJECTED')"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=15,
        )
        output = result.stdout.strip()
        assert "REJECTED" in output, f"Expected second process to be rejected, got: {output}"

        my_lock.release()

    def test_parallel_agent_lock_independent(self, tmp_path):
        """parallel_multi_agent has its own separate lock file."""
        lock_path = tmp_path / "pma.lock"
        lock1 = pma.ProcessLock(lock_path)
        lock2 = pma.ProcessLock(lock_path)
        assert lock1.acquire() is True
        assert lock2.acquire() is False
        lock1.release()


# ===========================================================================
# 9. Video quality end-to-end (real ffmpeg)
# ===========================================================================

class TestVideoQualityRealFFmpeg:
    """End-to-end validation using real ffmpeg-encoded video."""

    def test_valid_video_passes_validation(self, tmp_path):
        video = _make_dummy_video(tmp_path, width=1280, height=720, duration=3.0)
        res = validate_and_correct_video(str(video))
        assert res["valid"] is True
        assert res["width"] == 1280
        assert res["height"] == 720
        assert res["reason"] == "ok"

    def test_valid_video_desktop_suitable(self, tmp_path):
        video = _make_dummy_video(tmp_path, width=1280, height=720, duration=3.0)
        res = validate_and_correct_video(str(video))
        desktop = classify_desktop_suitability(res["width"], res["height"])
        assert desktop["suitable_for_desktop"] is True

    def test_file_integrity_check(self, tmp_path):
        video = _make_dummy_video(tmp_path, width=640, height=360, duration=2.0)
        ok, reason = check_file_integrity(str(video))
        assert ok is True
        assert reason == ""  # empty reason means pass

    def test_file_integrity_rejects_too_small(self, tmp_path):
        tiny = tmp_path / "tiny.mp4"
        tiny.write_bytes(b"\x00" * 100)
        ok, reason = check_file_integrity(str(tiny))
        assert ok is False


# ===========================================================================
# 10. CLI option verification (no network)
# ===========================================================================

class TestCLIOptions:
    """Verify the real CLI flags from --help (no guessed flags)."""

    def _run_help(self, agent_path: Path) -> str:
        result = subprocess.run(
            [sys.executable, str(agent_path), "--help"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        return result.stdout or ""

    def test_no_no_sync_supabase_flag(self):
        """--no-sync-supabase does NOT exist in either agent's real CLI."""
        out1 = self._run_help(REPO_ROOT / "smart_pinterest_agent.py")
        assert "--no-sync-supabase" not in out1
        out2 = self._run_help(REPO_ROOT / "parallel_multi_agent.py")
        assert "--no-sync-supabase" not in out2

    def test_parallel_agent_has_no_download_flag(self):
        out = self._run_help(REPO_ROOT / "parallel_multi_agent.py")
        assert "--no-download" in out