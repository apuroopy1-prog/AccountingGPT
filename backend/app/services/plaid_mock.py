import random
import uuid
from datetime import datetime, timedelta

CATEGORIES = ["Software", "Travel", "Meals", "Office Supplies", "Utilities", "Payroll", "Revenue", "Consulting"]
MERCHANTS = {
    "Software": ["AWS", "GitHub", "Notion", "Slack", "Figma"],
    "Travel": ["Delta Airlines", "Marriott", "Uber", "Lyft"],
    "Meals": ["Chipotle", "Starbucks", "DoorDash", "Grubhub"],
    "Office Supplies": ["Staples", "Amazon", "Office Depot"],
    "Utilities": ["AT&T", "Comcast", "PG&E"],
    "Payroll": ["ADP Payroll", "Gusto"],
    "Revenue": ["Client Payment", "Invoice Settlement", "Contract Payment"],
    "Consulting": ["Consulting Fee", "Advisory Revenue"],
}


def generate_mock_transactions(user_id: int, count: int = 30) -> list[dict]:
    transactions = []
    today = datetime.utcnow()

    for i in range(count):
        category = random.choice(CATEGORIES)
        merchant = random.choice(MERCHANTS[category])
        is_income = category in ("Revenue", "Consulting")
        amount = round(random.uniform(500, 15000) if is_income else -random.uniform(20, 3000), 2)
        date = today - timedelta(days=random.randint(0, 90))

        transactions.append({
            "user_id": user_id,
            "transaction_id": "mock-" + str(uuid.uuid4()),
            "date": date,
            "description": f"{merchant} - {category}",
            "amount": amount,
            "category": category,
            "merchant": merchant,
            "account": random.choice(["Business Checking", "Business Savings", "Credit Card"]),
        })

    return transactions
