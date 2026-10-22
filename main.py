
from pymongo import MongoClient
from analytics.monthly_revenue import get_monthly_revenue

client = MongoClient("mongodb://localhost:27017/")
db = client["mongomirror"]

monthly_revenue = get_monthly_revenue(db["orders"])
total_revenue = sum(monthly_revenue.values())

print("MONTHLY REVENUE SUMMARY")
print("-" * 45)

for month, revenue in sorted(monthly_revenue.items()):
    percentage = revenue / total_revenue * 100
    print(f"{month} | ₹{revenue} | {percentage:.2f}%")

print("-" * 45)
print(f"Total Delivered Revenue: ₹{total_revenue}")

client.close()
