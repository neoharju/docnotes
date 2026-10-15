"""Validation for user uploads"""

from werkzeug.datastructures import FileStorage

_MAX_FILENAME_LENGTH = 255
_PDF_MAGIC = b"%PDF-"


class UploadError(ValueError):
    """Failed upload validation"""


def read_pdf(file: FileStorage | None, max_bytes: int) -> bytes:
    """Validate an uploaded PDF [very basic validation]"""

    if file is None or not file.filename:
        raise UploadError("No file was selected")

    if len(file.filename) > _MAX_FILENAME_LENGTH:
        raise UploadError(f"File name must be max {_MAX_FILENAME_LENGTH} characters")

    data: bytes = file.read(max_bytes + 1)
    # NOTE: File exists already, would be better to validate beforehand
    #       from content-length and then during recieving, and lastly here.
    if len(data) > max_bytes:
        limit = max_bytes // (1024 * 1024)
        raise UploadError(f"PDF file upload limit is {limit} MB.")

    if not data.startswith(_PDF_MAGIC):
        raise UploadError("File is not a valid PDF")

    return data
