from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, Transaction
from app.schemas import ForecastPoint
from app.auth import get_current_user
from app.services.forecast_service import generate_forecast

router = APIRouter()


@router.get("", response_model=list[ForecastPoint])
async def get_forecast(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a 12-month revenue forecast using Prophet."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.date.asc())
    )
    transactions = result.scalars().all()

    # Convert to list of dicts for the service
    history = [{"date": t.date, "amount": t.amount} for t in transactions]
    forecast_points = generate_forecast(history)
    return forecast_points
