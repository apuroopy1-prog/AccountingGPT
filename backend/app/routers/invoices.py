import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, Invoice
from app.schemas import InvoiceOut
from app.auth import get_current_user

UPLOAD_DIR = "/app/uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Allowed file magic bytes
ALLOWED_MAGIC = [
    b'\xff\xd8\xff',       # JPEG
    b'\x89PNG\r\n\x1a\n',  # PNG
    b'GIF87a',             # GIF87
    b'GIF89a',             # GIF89
    b'%PDF',               # PDF
    b'RIFF',               # WebP (starts with RIFF)
]

router = APIRouter()


def _is_allowed_file(contents: bytes) -> bool:
    return any(contents.startswith(magic) for magic in ALLOWED_MAGIC)


@router.post("/upload", response_model=InvoiceOut)
async def upload_invoice(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    if not _is_allowed_file(contents):
        raise HTTPException(status_code=400, detail="Only images (JPEG, PNG, GIF, WebP) and PDFs are accepted")

    ext = os.path.splitext(file.filename)[1].lower()
    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as f:
        f.write(contents)

    invoice = Invoice(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        status="pending",
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)

    # Trigger Celery OCR task
    from app.tasks.background_tasks import process_ocr_task
    process_ocr_task.delay(invoice.id)

    return invoice


@router.get("", response_model=list[InvoiceOut])
async def list_invoices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Invoice)
        .where(Invoice.user_id == current_user.id)
        .order_by(Invoice.uploaded_at.desc())
    )
    return result.scalars().all()


@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == current_user.id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice
