"""Typed errors for external dependencies; the API maps them to safe messages."""

from __future__ import annotations


class CiteAgentError(Exception):
    code = "internal_error"
    message = "Hệ thống gặp lỗi không mong muốn. Vui lòng thử lại."
    status = 500


class SnapshotUnavailable(CiteAgentError):
    code = "snapshot_unavailable"
    message = "Kho tài liệu chưa được nạp. Vui lòng chạy bước ingest và index."
    status = 503


class VectorStoreUnavailable(CiteAgentError):
    code = "retrieval_unavailable"
    message = "Không thể truy xuất kho tài liệu lúc này."
    status = 503


class EmbeddingFailure(CiteAgentError):
    code = "embedding_failure"
    message = "Không thể mã hóa câu hỏi để tìm kiếm."
    status = 503


class LLMUnavailable(CiteAgentError):
    code = "llm_unavailable"
    message = "Mô hình ngôn ngữ đang không phản hồi. Vui lòng thử lại sau."
    status = 503


class SourceNotFound(CiteAgentError):
    code = "source_not_found"
    message = "Không tìm thấy đoạn nguồn được yêu cầu."
    status = 404


class InvalidSource(CiteAgentError):
    code = "invalid_source"
    message = "Yêu cầu nguồn không hợp lệ."
    status = 400
