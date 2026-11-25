import pandas as pd
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)

suppliers = [
    ("SUP-101", "Bharat Forge Components", "Powertrain", "Pune, India"),
    ("SUP-102", "Chennai Precision Castings", "Stamping & Castings", "Chennai, India"),
    ("SUP-103", "Minda Auto Electronics", "Electronics", "NCR, India"),
    ("SUP-104", "Sundram Fasteners Ltd", "Fasteners", "Chennai, India"),
    ("SUP-105", "RheinMetall Automotive", "Powertrain", "Frankfurt, Germany"),
    ("SUP-106", "Shenzhen EV Connectors", "Electronics", "Shenzhen, China"),
    ("SUP-107", "Thai Summit Stamping", "Stamping & Castings", "Rayong, Thailand"),
    ("SUP-108", "Bosch Chassis Systems", "Electronics", "Bengaluru, India"),
    ("SUP-109", "Sona Comstar Gears", "Powertrain", "Gurugram, India"),
    ("SUP-110", "Varroc Polymer Tech", "Plastics & Trim", "Pune, India"),
    ("SUP-111", "Nippon Auto Bearings", "Powertrain", "Osaka, Japan"),
    ("SUP-112", "Apex Industrial Fasteners", "Fasteners", "Ludhiana, India"),
]

profiles = {
    "SUP-101": {"delay_prob": 0.08, "ppm_rate": 0.0008, "price_drift": 0.01},
    "SUP-102": {"delay_prob": 0.12, "ppm_rate": 0.0012, "price_drift": 0.02},
    "SUP-103": {"delay_prob": 0.10, "ppm_rate": 0.0010, "price_drift": 0.015},
    "SUP-104": {"delay_prob": 0.05, "ppm_rate": 0.0004, "price_drift": 0.005},
    "SUP-105": {"delay_prob": 0.18, "ppm_rate": 0.0015, "price_drift": 0.04},
    "SUP-106": {"delay_prob": 0.35, "ppm_rate": 0.0085, "price_drift": 0.09},
    "SUP-107": {"delay_prob": 0.28, "ppm_rate": 0.0060, "price_drift": 0.06},
    "SUP-108": {"delay_prob": 0.06, "ppm_rate": 0.0005, "price_drift": 0.01},
    "SUP-109": {"delay_prob": 0.09, "ppm_rate": 0.0009, "price_drift": 0.02},
    "SUP-110": {"delay_prob": 0.24, "ppm_rate": 0.0055, "price_drift": 0.05},
    "SUP-111": {"delay_prob": 0.07, "ppm_rate": 0.0003, "price_drift": 0.01},
    "SUP-112": {"delay_prob": 0.40, "ppm_rate": 0.0095, "price_drift": 0.08},
}

base_prices = {s[0]: np.random.uniform(250, 2500) for s in suppliers}
rows = []
start_date = datetime(2025, 11, 1)

for i in range(1, 801):
    sup_id, sup_name, cat, region = suppliers[np.random.randint(0, len(suppliers))]
    prof = profiles[sup_id]
    
    days_offset = np.random.randint(0, 365)
    order_date = start_date + timedelta(days=days_offset)
    promised_date = order_date + timedelta(days=np.random.randint(14, 30))
    
    if np.random.rand() < prof["delay_prob"]:
        delay = np.random.randint(2, 14)
    else:
        delay = np.random.randint(-2, 1)
    actual_date = promised_date + timedelta(days=delay)
    
    units_received = np.random.randint(500, 5000)
    defective_units = np.random.binomial(units_received, prof["ppm_rate"])
    
    month_factor = days_offset / 365.0
    baseline_price = round(base_prices[sup_id], 2)
    unit_price = round(baseline_price * (1 + prof["price_drift"] * month_factor + np.random.uniform(-0.01, 0.01)), 2)
    
    rows.append({
        "po_id": f"PO-2026-{1000 + i}",
        "supplier_id": sup_id,
        "supplier_name": sup_name,
        "category": cat,
        "region": region,
        "order_date": order_date.strftime("%Y-%m-%d"),
        "promised_date": promised_date.strftime("%Y-%m-%d"),
        "actual_delivery_date": actual_date.strftime("%Y-%m-%d"),
        "units_received": units_received,
        "defective_units": defective_units,
        "baseline_unit_price": baseline_price,
        "unit_price": unit_price
    })

df = pd.DataFrame(rows)

# Inject missing values & duplicates for pandas cleaning
df.loc[np.random.choice(df.index, 18, replace=False), "defective_units"] = np.nan
df.loc[np.random.choice(df.index, 12, replace=False), "actual_delivery_date"] = np.nan
df.loc[np.random.choice(df.index, 10, replace=False), "region"] = None
duplicates = df.sample(20, random_state=42)
df_messy = pd.concat([df, duplicates], ignore_index=True)

df_messy.to_csv("raw_purchasing_data.csv", index=False)
df_messy.to_excel("raw_purchasing_data.xlsx", index=False)
print(f"Success! Generated {len(df_messy)} rows in raw_purchasing_data.csv and .xlsx")
