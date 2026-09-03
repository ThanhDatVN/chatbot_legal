"""Regression tests for streamed, atomic attachment download (defect D-12).

The defect: attachment bodies were accumulated in memory and written with a
non-atomic ``write_bytes``. A crash mid-write left a truncated PDF that looked
like a complete one, and the curl fallback buffered the whole payload in the
parent process.

``docs/large-data-processing-plan.md`` specifies the required behaviour: stream
in blocks while updating SHA-256, enforce the byte cap during streaming, fsync,
verify, then atomically rename into place.
"""

from __future__ import annotations

import hashlib
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from legal_crawler import STREAM_BLOCK_BYTES, SafeFetcher, verify_pdf  # noqa: E402

VALID_PDF = b"%PDF-1.4\n" + b"x" * 5000 + b"\ntrailer\n%%EOF\n"


def _fetcher() -> SafeFetcher:
    return SafeFetcher(user_agent="test", delay_seconds=0, timeout_seconds=5, max_redirects=3)


class StreamBodyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(__file__).resolve().parent / "_tmp_stream"
        self.tmp.mkdir(exist_ok=True)
        self.target = self.tmp / "out.pdf"

    def tearDown(self) -> None:
        for path in self.tmp.glob("*"):
            path.unlink()
        self.tmp.rmdir()

    def test_writes_file_and_returns_matching_digest(self):
        digest, size = _fetcher()._stream_body(
            io.BytesIO(VALID_PDF), self.target, max_bytes=10**6, declared_length=len(VALID_PDF)
        )
        self.assertEqual(size, len(VALID_PDF))
        self.assertEqual(digest, hashlib.sha256(VALID_PDF).hexdigest())
        self.assertEqual(self.target.read_bytes(), VALID_PDF)

    def test_digest_is_computed_incrementally_over_many_blocks(self):
        payload = b"%PDF-1.4\n" + b"y" * (STREAM_BLOCK_BYTES * 2 + 17) + b"\n%%EOF\n"
        digest, size = _fetcher()._stream_body(
            io.BytesIO(payload), self.target, max_bytes=10**8, declared_length=None
        )
        self.assertEqual(size, len(payload))
        self.assertEqual(digest, hashlib.sha256(payload).hexdigest())

    def test_oversize_body_is_rejected_and_leaves_no_file(self):
        with self.assertRaises(ValueError):
            _fetcher()._stream_body(
                io.BytesIO(b"z" * 5000), self.target, max_bytes=1000, declared_length=None
            )
        self.assertFalse(self.target.exists(), "target must not appear")
        self.assertFalse(list(self.tmp.glob("*.partial")), "partial must be cleaned up")

    def test_declared_length_over_cap_is_rejected_before_download(self):
        """Content-Length is checked first so an oversize body is never fetched."""
        with self.assertRaises(ValueError):
            _fetcher()._stream_body(
                io.BytesIO(b"z" * 10), self.target, max_bytes=1000, declared_length=999_999
            )
        self.assertFalse(self.target.exists())

    def test_short_read_is_rejected(self):
        """A truncated transfer must fail rather than land a partial file."""
        with self.assertRaises(ValueError):
            _fetcher()._stream_body(
                io.BytesIO(b"only-ten"), self.target, max_bytes=10**6, declared_length=500
            )
        self.assertFalse(self.target.exists())
        self.assertFalse(list(self.tmp.glob("*.partial")))

    def test_failure_midstream_leaves_no_partial(self):
        class Exploding(io.BytesIO):
            def read(self, size: int = -1) -> bytes:  # type: ignore[override]
                raise OSError("connection reset")

        with self.assertRaises(OSError):
            _fetcher()._stream_body(
                Exploding(), self.target, max_bytes=10**6, declared_length=None
            )
        self.assertFalse(self.target.exists())
        self.assertFalse(list(self.tmp.glob("*.partial")))


class VerifyPdfTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(__file__).resolve().parent / "_tmp_verify"
        self.tmp.mkdir(exist_ok=True)
        self.path = self.tmp / "f.pdf"

    def tearDown(self) -> None:
        for path in self.tmp.glob("*"):
            path.unlink()
        self.tmp.rmdir()

    def test_accepts_complete_pdf(self):
        self.path.write_bytes(VALID_PDF)
        verify_pdf(self.path)  # must not raise

    def test_rejects_wrong_magic(self):
        self.path.write_bytes(b"<html>not a pdf</html>")
        with self.assertRaises(ValueError):
            verify_pdf(self.path)

    def test_rejects_truncated_pdf_missing_eof(self):
        """The exact corruption a non-atomic write produces."""
        self.path.write_bytes(VALID_PDF[: len(VALID_PDF) // 2])
        with self.assertRaises(ValueError):
            verify_pdf(self.path)


if __name__ == "__main__":
    unittest.main()
