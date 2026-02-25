#!/usr/bin/env python3
"""
Analysis script for WebArena Task 51 failure.
Reproduces the agent's calculation to understand the discrepancy.
"""

from datetime import datetime

def analyze_task_51():
    # The orders data the agent extracted from the page
    orders = [
        {"date": "5/17/23", "amount": 365.42, "status": "Canceled"},
        {"date": "5/2/23", "amount": 754.99, "status": "Pending"},
        {"date": "5/2/23", "amount": 2004.99, "status": "Pending"},
        {"date": "5/2/23", "amount": 1004.99, "status": "Pending"},
        {"date": "3/11/23", "amount": 65.32, "status": "Complete"},
        {"date": "3/10/23", "amount": 17.99, "status": "Complete"},
        {"date": "2/27/23", "amount": 762.18, "status": "Complete"},
        {"date": "2/24/23", "amount": 231.54, "status": "Canceled"},
        {"date": "2/11/23", "amount": 174.99, "status": "Canceled"},
        {"date": "2/9/23", "amount": 185.32, "status": "Complete"},
        {"date": "1/29/23", "amount": 440.64, "status": "Complete"},
        {"date": "1/16/23", "amount": 132.24, "status": "Complete"},
        {"date": "12/18/22", "amount": 97.15, "status": "Complete"},
        {"date": "12/14/22", "amount": 20.49, "status": "Complete"},
        {"date": "12/12/22", "amount": 53.29, "status": "Complete"},
        {"date": "12/4/22", "amount": 32.47, "status": "Complete"},  # Outside 6 month window
        {"date": "11/26/22", "amount": 218.17, "status": "Complete"}, # Outside 6 month window
        {"date": "11/20/22", "amount": 133.07, "status": "Complete"}, # Outside 6 month window
        {"date": "11/11/22", "amount": 51.94, "status": "Complete"},  # Outside 6 month window
        {"date": "10/22/22", "amount": 845.07, "status": "Complete"}, # Outside 6 month window
        {"date": "10/21/22", "amount": 345.84, "status": "Complete"}, # Outside 6 month window
        {"date": "10/18/22", "amount": 2126.32, "status": "Canceled"}, # Outside 6 month window
        {"date": "10/3/22", "amount": 18.99, "status": "Complete"},   # Outside 6 month window
        {"date": "9/29/22", "amount": 2890.53, "status": "Complete"}, # Outside 6 month window
        {"date": "9/1/22", "amount": 133.85, "status": "Complete"},   # Outside 6 month window
        {"date": "8/12/22", "amount": 77.66, "status": "Canceled"},   # Outside 6 month window
        {"date": "8/10/22", "amount": 38.99, "status": "Complete"},   # Outside 6 month window
        {"date": "8/4/22", "amount": 36.99, "status": "Complete"},    # Outside 6 month window
        {"date": "7/25/22", "amount": 354.66, "status": "Canceled"},  # Outside 6 month window
        {"date": "7/8/22", "amount": 40.16, "status": "Complete"},    # Outside 6 month window
        {"date": "6/30/22", "amount": 173.56, "status": "Canceled"},  # Outside 6 month window
        {"date": "5/22/22", "amount": 298.65, "status": "Complete"},  # Outside 6 month window
        {"date": "4/27/22", "amount": 24.86, "status": "Complete"},   # Outside 6 month window
        {"date": "4/5/22", "amount": 77.96, "status": "Complete"},    # Outside 6 month window
        {"date": "3/10/22", "amount": 206.59, "status": "Canceled"},  # Outside 6 month window
        {"date": "3/2/22", "amount": 115.18, "status": "Canceled"},   # Outside 6 month window
        {"date": "3/2/22", "amount": 52.35, "status": "Complete"},    # Outside 6 month window
    ]

    # Task: "over the past six month" from 6/12/2023
    # Start: 12/12/2022, End: 6/12/2023
    start_date = datetime(2022, 12, 12)
    end_date = datetime(2023, 6, 12)

    print(f"Date range: {start_date.strftime('%m/%d/%Y')} to {end_date.strftime('%m/%d/%Y')}")
    print()

    fulfilled_orders = []
    for order in orders:
        # Parse date (MM/DD/YY format)
        date_parts = order["date"].split("/")
        year = int(date_parts[2])
        # Handle 2-digit years
        if year < 100:
            year += 2000
        order_date = datetime(year, int(date_parts[0]), int(date_parts[1]))
        
        # Check if Complete status and within date range
        if order["status"] == "Complete" and start_date <= order_date <= end_date:
            fulfilled_orders.append((order, order_date))
            print(f"✓ {order['date']} - ${order['amount']:>8.2f} - {order['status']}")
        elif order["status"] == "Complete":
            print(f"✗ {order['date']} - ${order['amount']:>8.2f} - {order['status']} (outside date range)")

    # Calculate total
    total_spent = sum(order[0]["amount"] for order in fulfilled_orders)
    fulfilled_count = len(fulfilled_orders)

    print()
    print(f"Agent's Answer: {fulfilled_count} fulfilled orders, ${total_spent:.2f} total spent")
    print(f"Expected Answer: 12 orders, $1603.69 total spend")
    print()
    print(f"Count difference: {fulfilled_count - 12}")
    print(f"Amount difference: ${total_spent - 1603.69:.2f}")

if __name__ == "__main__":
    analyze_task_51()