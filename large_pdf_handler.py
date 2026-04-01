"""
Utilities for downloading and validating PDF documents, especially large files
that exceed the Bot API's 20MB download limit.

Combines Pyrogram-based downloads with PyPDF validation so we can safely process
large source documents without loading everything into memory.
"""
from __future__ import annotations

import asyncio
import io
import os
from dataclasses import dataclass
from typing import Optional, Union

from pypdf import PdfReader

from services.pyrogram_helper import PyrogramHelper


class LargePDFHandlerError(Exception):
    """Raised when a PDF cannot be downloaded or validated."""

    def __init__(self, message: str):
        super().__init__(message)
        self.user_message = message


@dataclass
class PDFSource:
    """Represents a downloaded PDF, either in-memory or on-disk."""

    storage: str  # 'bytes' or 'path'
    payload: Union[bytes, str]
    total_pages: int
    file_size: int = 0
    via_pyrogram: bool = False

    def is_file(self) -> bool:
        return self.storage == 'path'

    def get_reference(self) -> Union[bytes, str]:
        """Return bytes or filesystem path, whichever applies."""
        return self.payload

    def cleanup(self) -> None:
        """Remove temp file if this source was stored on disk."""
        if self.is_file() and isinstance(self.payload, str):
            try:
                if os.path.exists(self.payload):
                    os.remove(self.payload)
            except Exception:
                pass


class LargePDFHandler:
    """Centralizes large-PDF download + validation logic."""

    _threshold_bytes = int(os.getenv("LARGE_PDF_THRESHOLD_MB", "19")) * 1024 * 1024
    _lock = asyncio.Lock()

    @classmethod
    async def prepare_from_document(cls, update, context, document, status_message=None) -> PDFSource:
        """
        Download the PDF document using PTB. For directly uploaded files,
        PTB can handle files beyond 20MB without issues.
        """
        file_size = getattr(document, "file_size", 0) or 0

        # Always try PTB first for directly uploaded documents
        try:
            if status_message and file_size > 10 * 1024 * 1024:
                await status_message.edit_text("📄 Large PDF detected. Downloading (this may take a moment)...")
            return await cls._download_via_ptb(document, file_size)
        except Exception as ptb_error:
            error_str = str(ptb_error).lower()
            # Only use Pyrogram if PTB explicitly fails due to size (rare)
            if "too big" in error_str or "file is too big" in error_str or "409" in error_str:
                if status_message:
                    await status_message.edit_text("📄 Retrying with advanced download method...")
                return await cls._download_via_pyrogram(update, context, file_size)
            raise LargePDFHandlerError(f"Failed to download PDF: {ptb_error}") from ptb_error

    @classmethod
    async def from_path(cls, path: str, file_size: int = 0, via_pyrogram: bool = False) -> PDFSource:
        """Create a PDFSource from an existing file path (e.g., HTTP download)."""
        if not path or not os.path.exists(path):
            raise LargePDFHandlerError("Temporary PDF file not found after download.")

        total_pages = cls._count_pages_from_path(path)
        if total_pages <= 0:
            raise LargePDFHandlerError("PDF appears to be empty or unreadable.")
        return PDFSource(
            storage='path',
            payload=path,
            total_pages=total_pages,
            file_size=file_size or os.path.getsize(path),
            via_pyrogram=via_pyrogram,
        )

    @classmethod
    async def _download_via_ptb(cls, document, file_size: int) -> PDFSource:
        """Download using python-telegram-bot's File API."""
        telegram_file = await document.get_file()
        pdf_bytes = await telegram_file.download_as_bytearray()
        if isinstance(pdf_bytes, bytearray):
            pdf_bytes = bytes(pdf_bytes)

        total_pages = cls._count_pages_from_bytes(pdf_bytes)
        if total_pages <= 0:
            raise LargePDFHandlerError("PDF file appears to have no readable pages.")
        return PDFSource(
            storage='bytes',
            payload=pdf_bytes,
            total_pages=total_pages,
            file_size=file_size,
            via_pyrogram=False,
        )

    @classmethod
    async def _download_via_pyrogram(cls, update, context, file_size: int) -> PDFSource:
        """Use Pyrogram (user account) to download large files to disk."""
        chat_id = update.message.chat_id
        message_id = update.message.message_id

        bot_id = None
        bot_username = None
        try:
            bot_info = await context.bot.get_me()
            if bot_info:
                if bot_info.id:
                    bot_id = -bot_info.id
                if bot_info.username:
                    bot_username = bot_info.username
        except Exception:
            pass

        path = await PyrogramHelper.download_document_to_path(
            chat_id=chat_id,
            message_id=message_id,
            bot_id=bot_id,
            bot_username=bot_username,
        )
        if not path:
            raise LargePDFHandlerError("Failed to download file via Pyrogram.")

        return await cls.from_path(path, file_size=file_size, via_pyrogram=True)

    @staticmethod
    def _count_pages_from_bytes(pdf_bytes: bytes) -> int:
        """Use PyPDF to count pages in-memory."""
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            return len(reader.pages)
        except Exception as exc:
            raise LargePDFHandlerError(f"Unable to read PDF (PyPDF error: {exc})") from exc

    @staticmethod
    def _count_pages_from_path(path: str) -> int:
        """Use PyPDF to count pages from a filesystem path."""
        try:
            reader = PdfReader(path)
            return len(reader.pages)
        except Exception as exc:
            raise LargePDFHandlerError(f"Unable to read PDF (PyPDF error: {exc})") from exc

