from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import BudgetGoal, Transaction, User
from app.schemas import BudgetGoalCreate, BudgetGoalOut

router = APIRouter()


@router.get("", response_model=list[BudgetGoalOut])
async def list_budgets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BudgetGoal).where(BudgetGoal.user_id == current_user.id)
    )
    goals = result.scalars().all()

    # Compute current month spend per category
    now = datetime.utcnow()
    txn_result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == current_user.id,
            Transaction.amount < 0,
        )
    )
    txns = txn_result.scalars().all()
    category_spend: dict = {}
    for t in txns:
        if t.date.year == now.year and t.date.month == now.month:
            key = (t.category or "Uncategorized").strip().lower()
            category_spend[key] = category_spend.get(key, 0) + abs(t.amount)

    out = []
    for g in goals:
        spent = category_spend.get(g.category.strip().lower(), 0.0)
        out.append(BudgetGoalOut(
            id=g.id,
            category=g.category,
            monthly_limit=g.monthly_limit,
            spent=round(spent, 2),
            created_at=g.created_at,
        ))
    return out


@router.post("", response_model=BudgetGoalOut)
async def create_budget(
    body: BudgetGoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    goal = BudgetGoal(
        user_id=current_user.id,
        category=body.category,
        monthly_limit=body.monthly_limit,
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return BudgetGoalOut(
        id=goal.id,
        category=goal.category,
        monthly_limit=goal.monthly_limit,
        spent=0.0,
        created_at=goal.created_at,
    )


@router.delete("/{goal_id}")
async def delete_budget(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BudgetGoal).where(BudgetGoal.id == goal_id, BudgetGoal.user_id == current_user.id)
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Budget goal not found")
    await db.delete(goal)
    await db.commit()
    return {"message": "Deleted"}
