import csv
import hashlib
import io
import os
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db
from app.models import User, Transaction
from app.schemas import TransactionOut
from app.auth import get_current_user
from app.services.plaid_mock import generate_mock_transactions

# Simple in-memory anomaly cache: {user_id: {"anomalies": [...], "ts": float}}
_anomaly_cache: dict = {}

from app.services.cache_invalidation import register_cache, invalidate_user_caches
register_cache("anomalies", _anomaly_cache)

router = APIRouter()


@router.post("/sync", response_model=list[TransactionOut])
async def sync_bank_feed(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Simulate syncing transactions from Plaid (mock data)."""
    mock_txns = generate_mock_transactions(current_user.id, count=30)

    # Upsert: skip duplicates
    for txn_data in mock_txns:
        result = await db.execute(
            select(Transaction).where(Transaction.transaction_id == txn_data["transaction_id"])
        )
        if result.scalar_one_or_none() is None:
            db.add(Transaction(**txn_data))

    await db.commit()

    from app.services.rag_service import rag_service
    rag_service.invalidate(current_user.id)
    invalidate_user_caches(current_user.id)

    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.date.desc())
    )
    return result.scalars().all()


@router.get("", response_model=list[TransactionOut])
async def list_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.date.desc())
    )
    return result.scalars().all()


@router.post("/upload", response_model=dict)
async def upload_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a CSV file with columns: date, description, amount
    Optional columns: category, merchant, account
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")

    try:
        text = contents.decode("utf-8-sig")  # utf-8-sig strips BOM if present
        reader = csv.DictReader(io.StringIO(text))
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read CSV file")

    # Normalize header names to lowercase and strip spaces
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    headers = [h.lower().strip() for h in reader.fieldnames]

    required = {"date", "description", "amount"}
    missing = required - set(headers)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required columns: {', '.join(sorted(missing))}. "
                   f"Required: date, description, amount. Optional: category, merchant, account"
        )

    inserted = 0
    skipped = 0
    errors = []

    for i, raw_row in enumerate(reader, start=2):  # start=2 because row 1 is header
        row = {k.lower().strip(): v.strip() for k, v in raw_row.items() if k}
        try:
            # Parse date — try common formats
            date_str = row.get("date", "")
            parsed_date = None
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y"):
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            if parsed_date is None:
                errors.append(f"Row {i}: unrecognised date '{date_str}'")
                continue

            # Parse amount — strip currency symbols and commas
            amount_str = row.get("amount", "").replace("$", "").replace(",", "").strip()
            amount = float(amount_str)

            description = row.get("description", "").strip()
            if not description:
                errors.append(f"Row {i}: empty description")
                continue

            # Generate a stable transaction_id from content so re-uploads skip duplicates
            raw_id = f"{current_user.id}-{date_str}-{description}-{amount_str}"
            transaction_id = "csv-" + hashlib.md5(raw_id.encode()).hexdigest()

            result = await db.execute(
                select(Transaction).where(Transaction.transaction_id == transaction_id)
            )
            if result.scalar_one_or_none() is not None:
                skipped += 1
                continue

            db.add(Transaction(
                user_id=current_user.id,
                transaction_id=transaction_id,
                date=parsed_date,
                description=description,
                amount=amount,
                category=row.get("category") or None,
                merchant=row.get("merchant") or None,
                account=row.get("account") or None,
            ))
            inserted += 1

        except ValueError as e:
            errors.append(f"Row {i}: {e}")
            continue

    await db.commit()

    if inserted > 0:
        from app.services.rag_service import rag_service
        rag_service.invalidate(current_user.id)
        invalidate_user_caches(current_user.id)

    return {
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors[:10],  # cap at 10 error messages
    }


@router.post("/upload-pdf", response_model=dict)
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a bank statement PDF. Claude extracts transactions from the text.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    contents = await file.read()
    if len(contents) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(status_code=413, detail="File too large (max 20MB)")

    # Extract structured content from PDF (tables preferred, fallback to text)
    try:
        import pdfplumber
        import io as _io

        table_rows: list[str] = []
        fallback_text = ""

        with pdfplumber.open(_io.BytesIO(contents)) as pdf:
            for page in pdf.pages:
                # Try structured table extraction first — preserves column boundaries
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            if row:
                                # Join cells with pipe separator so Claude can see column structure
                                cell_strs = [str(c).strip() if c else "" for c in row]
                                table_rows.append(" | ".join(cell_strs))
                else:
                    # Fallback: raw text
                    text = page.extract_text()
                    if text:
                        fallback_text += text + "\n"

        pdf_content = "\n".join(table_rows) if table_rows else fallback_text

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {e}")

    if not pdf_content.strip():
        raise HTTPException(status_code=400, detail="PDF appears to be empty or image-only (scanned). Try a digital bank statement.")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="AI service not configured")

    # Ask Claude to extract transactions
    import json
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    extraction_mode = "table (pipe-separated columns)" if table_rows else "raw text"

    # Prompt engineering for accurate bank statement parsing.
    # Contact author for implementation details.
    prompt = (
        f"Extract all transactions from this bank statement ({extraction_mode}) as a JSON array.\n"
        "Each object: date (YYYY-MM-DD), description, amount (negative=debit, positive=credit), category, account.\n"
        "Return ONLY the JSON array.\n\n"
        f"Content:\n{pdf_content[:14000]}"
    )

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rstrip("`").strip()
        extracted = json.loads(raw)
        if not isinstance(extracted, list):
            raise ValueError("Expected a list")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"AI could not parse transactions from this PDF: {e}")

    inserted = 0
    skipped = 0
    errors = []

    for i, txn in enumerate(extracted):
        try:
            date_str = str(txn.get("date", "")).strip()
            parsed_date = None
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y"):
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            if parsed_date is None:
                errors.append(f"Item {i+1}: bad date '{date_str}'")
                continue

            amount = float(txn.get("amount", 0))
            description = str(txn.get("description", "")).strip()
            if not description:
                errors.append(f"Item {i+1}: empty description")
                continue

            raw_id = f"{current_user.id}-{date_str}-{description}-{amount}"
            transaction_id = "pdf-" + hashlib.md5(raw_id.encode()).hexdigest()

            result = await db.execute(
                select(Transaction).where(Transaction.transaction_id == transaction_id)
            )
            if result.scalar_one_or_none() is not None:
                skipped += 1
                continue

            db.add(Transaction(
                user_id=current_user.id,
                transaction_id=transaction_id,
                date=parsed_date,
                description=description,
                amount=amount,
                category=str(txn.get("category", "")).strip() or None,
                account=str(txn.get("account", "Bank Statement")).strip() or "Bank Statement",
            ))
            inserted += 1

        except Exception as e:
            errors.append(f"Item {i+1}: {e}")
            continue

    await db.commit()

    if inserted > 0:
        from app.services.rag_service import rag_service
        rag_service.invalidate(current_user.id)
        invalidate_user_caches(current_user.id)

    return {
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors[:10],
    }


@router.delete("/clear-mock", response_model=dict)
async def clear_mock_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all mock (sync) transactions for the current user."""
    result = await db.execute(
        delete(Transaction).where(
            Transaction.user_id == current_user.id,
            Transaction.transaction_id.like("mock-%"),
        )
    )
    await db.commit()
    from app.services.rag_service import rag_service
    rag_service.invalidate(current_user.id)
    invalidate_user_caches(current_user.id)
    return {"deleted": result.rowcount}


@router.get("/summary")
async def transaction_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return KPI summary for dashboard."""
    result = await db.execute(
        select(Transaction).where(Transaction.user_id == current_user.id)
    )
    txns = result.scalars().all()

    income = sum(t.amount for t in txns if t.amount > 0)
    expenses = sum(abs(t.amount) for t in txns if t.amount < 0)

    # Monthly breakdown (last 6 months)
    from collections import defaultdict
    monthly: dict = defaultdict(float)
    for t in txns:
        key = t.date.strftime("%Y-%m")
        monthly[key] += t.amount

    return {
        "total_income": round(income, 2),
        "total_expenses": round(expenses, 2),
        "net": round(income - expenses, 2),
        "transaction_count": len(txns),
        "monthly_breakdown": dict(sorted(monthly.items())[-6:]),
    }


@router.get("/anomalies")
async def get_anomalies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detect anomalies in transactions using Claude. Cached 30 minutes per user."""
    cached = _anomaly_cache.get(current_user.id)
    if cached and (time.time() - cached["ts"]) < 1800:
        return {"anomalies": cached["anomalies"]}

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="AI service not configured")

    result = await db.execute(
        select(Transaction).where(Transaction.user_id == current_user.id)
    )
    txns = result.scalars().all()
    if not txns:
        return {"anomalies": []}

    txn_list = [
        {
            "id": t.id,
            "date": t.date.strftime("%Y-%m-%d"),
            "description": t.description,
            "amount": t.amount,
            "category": t.category or "Uncategorized",
            "merchant": t.merchant or "",
        }
        for t in txns[-100:]  # cap at 100 recent
    ]

    import json
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{
            "role": "user",
            # Anomaly detection prompt — contact author for implementation details.
            "content": (
                f"Analyze these transactions for anomalies:\n{json.dumps(txn_list, indent=2)}\n\n"
                "Return a JSON array of objects with fields: "
                "type, description, transaction_id, severity ('high'|'medium'|'low'). "
                "Return [] if no anomalies. Return only the JSON array."
            ),
        }],
    )

    try:
        anomalies = json.loads(message.content[0].text)
        if not isinstance(anomalies, list):
            raise ValueError
    except Exception:
        anomalies = []

    _anomaly_cache[current_user.id] = {"anomalies": anomalies, "ts": time.time()}
    return {"anomalies": anomalies}
