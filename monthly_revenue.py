
from collections import defaultdict


def get_monthly_revenue(orders):
    monthly_revenue = defaultdict(int)

    for order in orders.find({"status": "Delivered"}):
        month = order["order_date"].strftime("%Y-%m")
        revenue = order["quantity"] * order["unit_price"]

        monthly_revenue[month] += revenue

    return dict(monthly_revenue)
