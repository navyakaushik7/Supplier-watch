import pandas as pd
import tomllib
from sqlalchemy import create_engine, text

def run_etl():
    df = pd.read_csv("raw_purchasing_data.csv")
    initial_rows = len(df)
    
    # Remove duplicates
    df = df.drop_duplicates(subset=["po_id"], keep="first").copy()
    duplicates_removed = initial_rows - len(df)
    
    # Fill missing values
    missing_defects = df["defective_units"].isna().sum()
    df["defective_units"] = df["defective_units"].fillna(0).astype(int)
    
    supplier_region_map = df.dropna(subset=["region"]).set_index("supplier_id")["region"].to_dict()
    missing_regions = df["region"].isna().sum()
    df["region"] = df["region"].fillna(df["supplier_id"].map(supplier_region_map))
    
    open_orders_dropped = df["actual_delivery_date"].isna().sum()
    df = df.dropna(subset=["actual_delivery_date"]).copy()
    
    # Standardize dates & flags
    for col in ["order_date", "promised_date", "actual_delivery_date"]:
        df[col] = pd.to_datetime(df[col])
    
    df["is_on_time"] = (df["actual_delivery_date"] <= df["promised_date"]).astype(int)
    df["total_spend"] = (df["units_received"] * df["unit_price"]).round(2)
    
    print("=== Data Cleaning Audit Report ===")
    print(f"Initial Raw Rows       : {initial_rows}")
    print(f"Duplicates Removed     : {duplicates_removed}")
    print(f"Missing Defects Filled : {missing_defects}")
    print(f"Missing Regions Mapped : {missing_regions}")
    print(f"Open Orders Excluded   : {open_orders_dropped}")
    print(f"Clean Valid Records    : {len(df)}")
    
    # Connect to Neon PostgreSQL
    with open(".streamlit/secrets.toml", "rb") as f:
        secrets = tomllib.load(f)
    db_url = secrets["connections"]["postgresql"]["url"]
    engine = create_engine(db_url)
    
    suppliers_df = df[["supplier_id", "supplier_name", "category", "region"]].drop_duplicates()
    orders_df = df[[
        "po_id", "supplier_id", "order_date", "promised_date", "actual_delivery_date",
        "units_received", "defective_units", "baseline_unit_price", "unit_price",
        "is_on_time", "total_spend"
    ]]
    
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS purchase_orders CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS suppliers CASCADE;"))
    
    suppliers_df.to_sql("suppliers", engine, if_exists="replace", index=False)
    orders_df.to_sql("purchase_orders", engine, if_exists="replace", index=False)
    print("Success! Loaded normalized tables into PostgreSQL!")

if __name__ == "__main__":
    run_etl()
