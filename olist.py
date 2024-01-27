import streamlit as st
import pandas as pd
import zipfile
import io
import requests
import duckdb
import time
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import folium
from folium.plugins import MarkerCluster


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

<<<<<<< HEAD
def dataframe_with_selections(df):
    df_with_selections = df.copy()
    df_with_selections.insert(0, "Select", False)

    # Get dataframe row-selections from user with st.data_editor
    edited_df = st.data_editor(
        df_with_selections,
        hide_index=True,
        column_config={"Select": st.column_config.CheckboxColumn(required=True)},
        disabled=df.columns,
    )

    # Filter the dataframe using the temporary column, then drop the column
    selected_rows = edited_df[edited_df.Select]
    return selected_rows.drop('Select', axis=1).iloc[0][0]

st.title('Olist')

tables_list = sql('show tables').fetchall()
tables = [table[0] for table in tables_list]

col1, col2, col3 = st.columns(3)

with col1:
    order = st.toggle('orders', value=True)
    oc = st.toggle('order_customers')
    op = st.toggle('order_payments')
    orv = st.toggle('order_reviews')

with col2:
    oi = st.toggle('order_items')
    prod = st.toggle('products')
    sel = st.toggle('sellers')
    geo = st.toggle('geolocation')

with col3:
    try:
        selection = dataframe_with_selections(sql('show tables').df())
    except:
        pass

if 'order_customers' not in tables and oc:
    start = time.time()
    # import orders_customers_dataset
    order_customers_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/orders_customers_dataset.csv").drop(columns = "Unnamed: 0")\
    .rename(columns={"customer_zip_code_prefix": "zip_code_prefix_id"})
    duckdb.sql("CREATE OR REPLACE TABLE order_customers AS SELECT * FROM order_customers_df")
    oc_time = time.time() - start

if 'geolocation' not in tables and geo:
    # import geolocation_dataset
    response = requests.get("https://github.com/WildCodeSchool/wilddata/raw/main/geolocation_dataset.zip")
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        z.extractall()
    geolocation_df = pd.read_csv("geolocation_dataset.csv").drop(columns = "Unnamed: 0")\
    .rename(columns={"geolocation_zip_code_prefix": "zip_code_prefix_id"})
    geolocation_df['geolocation_city'] = geolocation_df['geolocation_city'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
    duckdb.sql("CREATE OR REPLACE TABLE geolocation AS SELECT * FROM geolocation_df")

if 'order_items' not in tables and oi:
    # import order_items_dataset
    order_items_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/order_items_dataset.csv").drop(columns = "Unnamed: 0")
    duckdb.sql("CREATE OR REPLACE TABLE order_items AS SELECT * FROM order_items_df")

if 'order_payments' not in tables and op:
    start = time.time()
    # import order_payments_dataset
    order_payments_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/order_payments_dataset.csv").drop(columns = "Unnamed: 0")
    duckdb.sql("CREATE OR REPLACE TABLE order_payments AS SELECT * FROM order_payments_df")
    op_time = time.time() - start

if 'order_reviews' not in tables and orv:
    start = time.time()
    # import order_reviews_dataset
    order_reviews_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/order_reviews_dataset.csv").drop(columns = "Unnamed: 0")
    duckdb.sql("CREATE OR REPLACE TABLE order_reviews AS SELECT * FROM order_reviews_df")
    orv_time = time.time() - start

if 'orders' not in tables and order:
    # import orders_dataset
    orders_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/orders_dataset.csv").drop(columns = "Unnamed: 0")
    duckdb.sql("CREATE OR REPLACE TABLE orders AS SELECT * FROM orders_df")

if 'products' not in tables and prod:
    # import products_dataset
    products_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/products_dataset.csv").drop(columns = "Unnamed: 0")
    duckdb.sql("CREATE OR REPLACE TABLE products AS SELECT * FROM products_df")

if 'sellers' not in tables and sel:
    # import sellers_dataset
    sellers_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/sellers_dataset.csv").drop(columns = "Unnamed: 0")\
    .rename(columns={"seller_zip_code_prefix": "zip_code_prefix_id"})
    duckdb.sql("CREATE OR REPLACE TABLE sellers AS SELECT * FROM sellers_df")

if 'selection' in locals():
    st.write("Your selection:")
    st.dataframe(sql(f'{selection}', 'all').df())

orders__reviews = join_tables("orders", "order_reviews", "order")

review_by_month = sql('''
select avg(review_score) as avg_review
    , concat(CASE month(review_creation_date::TIMESTAMP)
            WHEN 1 THEN 'Jan'
            WHEN 2 THEN 'Feb'
            WHEN 3 THEN 'Mar'
            WHEN 4 THEN 'Apr'
            WHEN 5 THEN 'May'
            WHEN 6 THEN 'Jun'
            WHEN 7 THEN 'Jul'
            WHEN 8 THEN 'Aug'
            WHEN 9 THEN 'Sep'
            WHEN 10 THEN 'Oct'
            WHEN 11 THEN 'Nov'
            WHEN 12 THEN 'Dec'
            ELSE 'N/A'END
        ,'-', year(review_creation_date::TIMESTAMP)) as date
    , count(order_id) as nb_orders
from orders__reviews
where review_score is not null
group by month(review_creation_date::TIMESTAMP), year(review_creation_date::TIMESTAMP)
order by year(review_creation_date::TIMESTAMP), month(review_creation_date::TIMESTAMP)
''')

# Create a Plotly figure
X = review_by_month.df().date
Y = review_by_month.df().nb_orders
Z = review_by_month.df().avg_review

fig=make_subplots(specs=[[{"secondary_y":True}]])

# Add line traces
fig.add_trace(go.Scatter(x=X, y=Y, mode='lines', name='nb orders'),secondary_y=True)

# Add bar trace
fig.add_trace(go.Bar(x=X, y=Z, name='avg review', opacity=0.4, width=0.3),secondary_y=False)

# Update layout
fig.update_layout(title='Reviews and orders by month',
                  xaxis_title='Date',
                  yaxis=dict(title='Reviews', titlefont=dict(color='black')),
                  yaxis2=dict(title_text='Orders', titlefont=dict(color='black'), overlaying='y', side='right'))

# Show the plot
st.plotly_chart(fig, use_container_width=True)

sellers__geolocation = join_tables('sellers', 'geolocation', 'zip_code_prefix')
sellers_geo_clean = sql('''
select
    count(seller_id)
    , count(zip_code_prefix_id) as zipcode
    , avg(geolocation_lat) as lat
    , avg(geolocation_lng) as lng
    , geolocation_city as city
from sellers__geolocation
where geolocation_lat is not null
group by city
''')
sellers_geo_clean.df()

df = sellers_geo_clean.df()

from streamlit_folium import st_folium, folium_static



map = folium.Map(tiles ='cartodbpositron')
marker_cluster = MarkerCluster().add_to(map)
for i, row in df.iterrows():
    lat = df.at[i, 'lat']
    lng = df.at[i, 'lng']
    popup = 'City : ' + str(df.at[i, 'city'])
    icon_perso = folium.Icon(color="blue", icon='briefcase')
    folium.Marker(location=[lat,lng], icon=icon_perso, popup=popup).add_to(marker_cluster)
map.fit_bounds(map.get_bounds())

# call to render Folium map in Streamlit
st_data = folium_static(map, width=725)
=======


response = requests.get("https://github.com/WildCodeSchool/wilddata/raw/main/geolocation_dataset.zip")
with zipfile.ZipFile(io.BytesIO(response.content)) as z:
    z.extractall()
geolocation_df = pd.read_csv("geolocation_dataset.csv").drop(columns = "Unnamed: 0")\
.rename(columns={"geolocation_zip_code_prefix": "zip_code_prefix_id"})
geolocation_df['geolocation_city'] = geolocation_df['geolocation_city'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
duckdb.sql("CREATE OR REPLACE TABLE geolocation AS SELECT * FROM geolocation_df")

st.dataframe(sql('show tables').df().name)
st.dataframe(sql('select * from geolocation').df().head(10))
>>>>>>> 2b9978e (update)
