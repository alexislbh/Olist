import streamlit as st
import pandas as pd
import zipfile
import io
import requests
import duckdb
import time

def sql(query, select='query'):
    if select == 'all':
        return duckdb.sql(f"select * from {query}")
    else:
        return duckdb.sql(f"{query}")

def join_tables(t1, t2, item):
    table = 'TempTable'
    duckdb.sql(f'''
        CREATE OR REPLACE TABLE {table} AS
        select t1.*
        , t2.*
        from {t1} t1
        left join {t2} t2
            on t1.{item}_id=t2.{item}_id
        ''')
    duckdb.sql(f'ALTER TABLE {table} DROP COLUMN "{item}_id:1"')
    return duckdb.sql(f"select * from {table}")


start = time.time()

# import orders_customers_dataset
order_customers_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/orders_customers_dataset.csv").drop(columns = "Unnamed: 0")\
.rename(columns={"customer_zip_code_prefix": "zip_code_prefix_id"})
duckdb.sql("CREATE OR REPLACE TABLE order_customers AS SELECT * FROM order_customers_df")

# import geolocatio_dataset
response = requests.get("https://github.com/WildCodeSchool/wilddata/raw/main/geolocation_dataset.zip")
with zipfile.ZipFile(io.BytesIO(response.content)) as z:
    z.extractall()
geolocation_df = pd.read_csv("geolocation_dataset.csv").drop(columns = "Unnamed: 0")\
.rename(columns={"geolocation_zip_code_prefix": "zip_code_prefix_id"})
geolocation_df['geolocation_city'] = geolocation_df['geolocation_city'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
duckdb.sql("CREATE OR REPLACE TABLE geolocation AS SELECT * FROM geolocation_df")

# import order_items_dataset
order_items_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/order_items_dataset.csv").drop(columns = "Unnamed: 0")
duckdb.sql("CREATE OR REPLACE TABLE order_items AS SELECT * FROM order_items_df")

# import order_payments_dataset
order_payments_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/order_payments_dataset.csv").drop(columns = "Unnamed: 0")
duckdb.sql("CREATE OR REPLACE TABLE order_payments AS SELECT * FROM order_payments_df")

# import order_reviews_dataset
order_reviews_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/order_reviews_dataset.csv").drop(columns = "Unnamed: 0")
duckdb.sql("CREATE OR REPLACE TABLE order_reviews AS SELECT * FROM order_reviews_df")

# import orders_dataset
orders_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/orders_dataset.csv").drop(columns = "Unnamed: 0")
duckdb.sql("CREATE OR REPLACE TABLE orders AS SELECT * FROM orders_df")

# import products_dataset
products_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/products_dataset.csv").drop(columns = "Unnamed: 0")
duckdb.sql("CREATE OR REPLACE TABLE products AS SELECT * FROM products_df")

# import sellers_dataset
sellers_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/sellers_dataset.csv").drop(columns = "Unnamed: 0")\
.rename(columns={"seller_zip_code_prefix": "zip_code_prefix_id"})
duckdb.sql("CREATE OR REPLACE TABLE sellers AS SELECT * FROM sellers_df")

print(time.time() - start)

st.dataframe(sql('show tables').df().name)
st.dataframe(sql('select * from geolocation').df().head(10))