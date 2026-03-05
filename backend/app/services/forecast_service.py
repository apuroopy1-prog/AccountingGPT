def generate_forecast(history: list[dict]) -> list[dict]:
    """
    Generate a 12-month net cash flow forecast using Prophet.
    Returns empty list if fewer than 2 months of history exist.
    """
    if len(history) < 2:
        return []
    return _prophet_forecast(history)


def _prophet_forecast(history: list[dict]) -> list[dict]:
    try:
        import pandas as pd
        from prophet import Prophet

        df = pd.DataFrame(history)
        df["ds"] = pd.to_datetime(df["date"])
        # Forecast net cash flow (income + expenses combined), not just revenue
        df["y"] = df["amount"]
        df = df.groupby(df["ds"].dt.to_period("M")).agg({"y": "sum"}).reset_index()
        df["ds"] = df["ds"].dt.to_timestamp()

        n_months = len(df)
        if n_months < 2:
            return []

        # Tune seasonality based on how much data we have
        yearly = n_months >= 12   # need a full year to fit yearly seasonality
        # Allow at most (n_months // 3) changepoints so Prophet doesn't overfit sparse data
        n_changepoints = max(0, n_months // 3)

        model = Prophet(
            interval_width=0.8,
            yearly_seasonality=yearly,
            weekly_seasonality=False,
            daily_seasonality=False,
            n_changepoints=n_changepoints,
        )
        model.fit(df)

        future = model.make_future_dataframe(periods=12, freq="MS")
        forecast = model.predict(future)

        results = []
        for _, row in forecast.tail(12).iterrows():
            results.append({
                "ds": row["ds"].strftime("%Y-%m-%d"),
                "yhat": round(float(row["yhat"]), 2),
                "yhat_lower": round(float(row["yhat_lower"]), 2),
                "yhat_upper": round(float(row["yhat_upper"]), 2),
            })
        return results
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Prophet forecast failed: {e}")
        return []
