import os
import re
import json
import logging
import pytesseract
from PIL import Image

try:
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

logger = logging.getLogger(__name__)


def extract_text_from_file(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        if not PDF_SUPPORT:
            return "PDF support unavailable (pdf2image not installed)"
        images = convert_from_path(file_path)
        texts = [pytesseract.image_to_string(img) for img in images]
        return "\n".join(texts)
    else:
        img = Image.open(file_path)
        return pytesseract.image_to_string(img)


def _parse_invoice_fields_regex(text: str) -> dict:
    """Original regex-based fallback parser."""
    data = {}

    invoice_match = re.search(r"(?:invoice|inv)[#\s:]+([A-Z0-9\-]+)", text, re.IGNORECASE)
    if invoice_match:
        data["invoice_number"] = invoice_match.group(1)

    amount_match = re.search(r"(?:total|amount due)[:\s$]*([0-9,]+\.?\d{0,2})", text, re.IGNORECASE)
    if amount_match:
        data["total_amount"] = amount_match.group(1).replace(",", "")

    date_match = re.search(r"(?:date)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text, re.IGNORECASE)
    if date_match:
        data["date"] = date_match.group(1)

    email_match = re.search(r"[\w.\-]+@[\w.\-]+\.\w+", text)
    if email_match:
        data["email"] = email_match.group(0)

    return data


def parse_invoice_fields(text: str) -> dict:
    """Extract structured fields from raw OCR text using Claude AI, with regex fallback."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set, falling back to regex parser")
        return _parse_invoice_fields_regex(text)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=(
                "You are an invoice data extraction assistant. "
                "Extract structured fields from the provided OCR text of an invoice. "
                "Return ONLY a valid JSON object with no markdown, no explanation, no code fences. "
                "Use these exact keys: invoice_number, vendor, total_amount, date, due_date, "
                "line_items, tax, currency. "
                "Set a key to null if the information is not present. "
                "For line_items, return a JSON array of objects with keys: description, quantity, unit_price, amount. "
                "For total_amount and tax, return numeric strings without currency symbols."
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Extract invoice fields from this OCR text:\n\n{text}",
                }
            ],
        )

        raw = message.content[0].text.strip()
        parsed = json.loads(raw)

        if isinstance(parsed.get("line_items"), list):
            parsed["line_items"] = json.dumps(parsed["line_items"])

        return {k: v for k, v in parsed.items() if v is not None}

    except Exception as exc:
        logger.error(f"Claude invoice parsing failed: {exc}, falling back to regex")
        return _parse_invoice_fields_regex(text)
