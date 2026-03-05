"""
Reports router — PDF and Excel export for transactions and financial summary.

  GET /reports/transactions?format=pdf|excel
  GET /reports/summary?format=pdf|excel
"""
import io
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth import get_current_user
from app.database import get_db
from app.models import Transaction, User

router = APIRouter()


@router.get("/transactions")
async def export_transactions(
    format: str = Query("pdf", pattern="^(pdf|excel)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.date.desc())
    )
    transactions = result.scalars().all()

    from app.services.report_service import generate_transactions_pdf, generate_transactions_excel

    if format == "pdf":
        data = generate_transactions_pdf(transactions)
        media_type = "application/pdf"
        filename = "transactions.pdf"
    else:
        data = generate_transactions_excel(transactions)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "transactions.xlsx"

    return StreamingResponse(
        io.BytesIO(data),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/summary")
async def export_summary(
    format: str = Query("pdf", pattern="^(pdf|excel)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction).where(Transaction.user_id == current_user.id)
    )
    txns = result.scalars().all()

    income = sum(t.amount for t in txns if t.amount > 0)
    expenses = sum(abs(t.amount) for t in txns if t.amount < 0)

    monthly: dict = defaultdict(float)
    for t in txns:
        monthly[t.date.strftime("%Y-%m")] += t.amount

    summary = {
        "total_income": round(income, 2),
        "total_expenses": round(expenses, 2),
        "net": round(income - expenses, 2),
        "transaction_count": len(txns),
        "monthly_breakdown": dict(sorted(monthly.items())[-6:]),
    }

    from app.services.report_service import generate_summary_pdf, generate_summary_excel

    if format == "pdf":
        data = generate_summary_pdf(summary)
        media_type = "application/pdf"
        filename = "summary.pdf"
    else:
        data = generate_summary_excel(summary)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "summary.xlsx"

    return StreamingResponse(
        io.BytesIO(data),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/send-now")
async def send_report_now(
    current_user: User = Depends(get_current_user),
):
    """Manually trigger a monthly PDF report email for the current user."""
    from app.tasks.background_tasks import generate_monthly_report_task
    generate_monthly_report_task.delay(current_user.id)
    return {"detail": "Monthly report is being generated and will be emailed shortly."}
