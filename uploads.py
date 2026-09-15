"""Validation for user uploads"""

from werkzeug.datastructures import FileStorage


class UploadError(ValueError):
    """Failed upload validation"""


def read_pdf(file: FileStorage | None, max_bytes: int) -> bytes:
    """Validate an uploaded PDF [very basic validation]"""

    MAX_PDF_BYTES = max_bytes
    PDF_MAGIC = b"%PDF-"

    if file is None or file.filename == "":
        raise UploadError("No file was selected")

    data: bytes = file.read(MAX_PDF_BYTES + 1)
    # NOTE: File exists already, would be better to validate beforehand
    #       from content-length and then during recieving, and lastly here.
    if len(data) > MAX_PDF_BYTES:
        limit = MAX_PDF_BYTES // (1024 * 1024)
        raise UploadError(f"PDF file upload limit is {limit} MB.")

    if not data.startswith(PDF_MAGIC):
        raise UploadError("File is not a valid PDF")

    return data
