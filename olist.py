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
from matplotlib import pyplot as plt
import nltk
from wordcloud import WordCloud
from streamlit_folium import folium_static


### Functions

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

def dataframe_with_selections(df):
    df_with_selections = df.copy()            
    df_with_selections.insert(0, "Select", False)

    # Get dataframe row-selections from user with st.data_editor
    edited_df = st.data_editor(
        df_with_selections,
        hide_index=True,
        column_config={"Select": st.column_config.CheckboxColumn(required=True)},
        disabled=df.columns,
        key="selection",
    )

    # Filter the dataframe using the temporary column, then drop the column
    selected_rows = edited_df[edited_df.Select]
    return selected_rows.drop('Select', axis=1).iloc[0][0]

def create_table(table_name, df):
    duckdb.sql(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM {df}")

def active_tables():
    tables_list = sql('show tables').fetchall()
    tables = [table[0] for table in tables_list]
    return tables

def not_active_tables(tables):
    return [table for table in tables if table not in active_tables()]

### Variables

tables = ['orders', 'order_customers', 'order_payments', 'order_reviews', 'order_items', 'products', 'sellers', 'geolocation']

### Sidebar

with st.sidebar:
    st.header('Load tables')
    select_table = st.selectbox('Select tables to load :', not_active_tables(tables), placeholder='Tables', index=None)

    if 'orders' not in active_tables():
        # import orders_dataset
        orders_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/orders_dataset.csv").drop(columns = "Unnamed: 0")
        duckdb.sql("CREATE OR REPLACE TABLE orders AS SELECT * FROM orders_df")

    if 'order_customers' not in active_tables():
        start = time.time()
        # import orders_customers_dataset
        order_customers_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/orders_customers_dataset.csv").drop(columns = "Unnamed: 0")\
        .rename(columns={"customer_zip_code_prefix": "zip_code_prefix_id"})
        duckdb.sql("CREATE OR REPLACE TABLE order_customers AS SELECT * FROM order_customers_df")
        oc_time = time.time() - start

    if 'geolocation' not in active_tables():
        # import geolocation_dataset
        response = requests.get("https://github.com/WildCodeSchool/wilddata/raw/main/geolocation_dataset.zip")
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            z.extractall()
        geolocation_df = pd.read_csv("geolocation_dataset.csv").drop(columns = "Unnamed: 0")\
        .rename(columns={"geolocation_zip_code_prefix": "zip_code_prefix_id"})
        geolocation_df['geolocation_city'] = geolocation_df['geolocation_city'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
        duckdb.sql("CREATE OR REPLACE TABLE geolocation AS SELECT * FROM geolocation_df")

    if 'order_items' not in active_tables() and 'order_items' == select_table:
        # import order_items_dataset
        order_items_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/order_items_dataset.csv").drop(columns = "Unnamed: 0")
        duckdb.sql("CREATE OR REPLACE TABLE order_items AS SELECT * FROM order_items_df")

    if 'order_payments' not in active_tables() and 'order_payments' == select_table:
        start = time.time()
        # import order_payments_dataset
        order_payments_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/order_payments_dataset.csv").drop(columns = "Unnamed: 0")
        duckdb.sql("CREATE OR REPLACE TABLE order_payments AS SELECT * FROM order_payments_df")
        op_time = time.time() - start

    if 'order_reviews' not in active_tables():
        start = time.time()
        # import order_reviews_dataset
        order_reviews_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/order_reviews_dataset.csv").drop(columns = "Unnamed: 0")
        duckdb.sql("CREATE OR REPLACE TABLE order_reviews AS SELECT * FROM order_reviews_df")
        orv_time = time.time() - start

    if 'products' not in active_tables() and 'products' == select_table:
        # import products_dataset
        products_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/products_dataset.csv").drop(columns = "Unnamed: 0")
        duckdb.sql("CREATE OR REPLACE TABLE products AS SELECT * FROM products_df")

    if 'sellers' not in active_tables():
        # import sellers_dataset
        sellers_df = pd.read_csv("https://raw.githubusercontent.com/WildCodeSchool/wilddata/main/sellers_dataset.csv").drop(columns = "Unnamed: 0")\
        .rename(columns={"seller_zip_code_prefix": "zip_code_prefix_id"})
        duckdb.sql("CREATE OR REPLACE TABLE sellers AS SELECT * FROM sellers_df")
    
    st.write('---')
    st.header('Active tables')
    st.subheader("Select for view data : ")
    st.caption("Only the first is show !")
    
    try:
        selection = dataframe_with_selections(sql('show tables').df())
    except:
        pass


### Main

st.title('Olist')

if 'selection' in locals():
    st.header('Data :')
    st.write("Sample of 100 rows : ")
    st.dataframe(sql(f'{selection}', 'all').df().sample(100).sort_index())

#nb_customers
orders__customers = join_tables('orders', 'order_customers', 'customer').df()
orders__reviews = join_tables('orders', 'order_reviews', 'order').df()
orders__customers__reviews = join_tables('orders__customers', 'order_reviews', 'order').df()

nb_customers = sql('''
select count(distinct customer_unique_id) as nb_customers
    , year(order_purchase_timestamp::date) as year
from orders__customers__reviews
group by year(order_purchase_timestamp::date)
''').df()

st.subheader('Number of customers by year')
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="2016", value=nb_customers[nb_customers['year'] == 2016]['nb_customers'], delta=None)
with col2:
    st.metric(label="2017", value=nb_customers[nb_customers['year'] == 2017]['nb_customers'], delta=None)
with col3:
    st.metric(label="2018", value=nb_customers[nb_customers['year'] == 2018]['nb_customers'], delta=None)

customers__orders__day_delivery = sql('''
select *
    , DATEDIFF('day', order_purchase_timestamp::date, order_delivered_carrier_date::date) as day_delivered_carrier
    , DATEDIFF('day', order_purchase_timestamp::date, order_delivered_customer_date::date) as day_delivered_customer
    , DATEDIFF('day', order_purchase_timestamp::date, order_estimated_delivery_date::date) as day_estimated_delivery
from orders__customers__reviews
''')

nb_after_delivery_estimated = sql('''
select count(1) as nb
from customers__orders__day_delivery
where day_estimated_delivery < day_delivered_customer
''')

nb_before_delivery_estimated = sql('''
select count(1) as nb
from customers__orders__day_delivery
where day_estimated_delivery >= day_delivered_customer
''')

percent_after_delivery_estimated = round(
    nb_after_delivery_estimated.fetchall()[0][0]
    / (nb_before_delivery_estimated.fetchall()[0][0] + nb_after_delivery_estimated.fetchall()[0][0]) * 100
    , 2)

avg_review_score_after_delivery_estimated = sql('''
select avg(review_score) as avg
from customers__orders__day_delivery
where day_estimated_delivery < day_delivered_customer
''')

avg_day_delevery_carrier_after_delivery_estimated = sql('''
select avg(day_delivered_carrier) as avg
from customers__orders__day_delivery
where day_estimated_delivery < day_delivered_customer
''')

avg_review_score_before_delivery_estimated = sql('''
select avg(review_score) as avg
from customers__orders__day_delivery
where day_estimated_delivery >= day_delivered_customer
''')

avg_day_delevery_carrier_before_delivery_estimated = sql('''
select avg(day_delivered_carrier) as avg
from customers__orders__day_delivery
where day_estimated_delivery >= day_delivered_customer
''')

st.subheader('Delivery date')
col1, col2, col3 = st.columns(3)
with col1:
    st.write('Before date estimate')
    st.metric(label="Number of orders", value=nb_before_delivery_estimated.df()['nb'], delta=None)
    st.metric(label="Average of reviews", value=round(avg_review_score_before_delivery_estimated.df()['avg'],2), delta=None)
    st.metric(label="Average of days", value=round(avg_day_delevery_carrier_before_delivery_estimated.df()['avg'],2), delta=None)
with col2:
    st.write('After date estimate')
    st.metric(label="Number of orders", value=nb_after_delivery_estimated.df()['nb'], delta=None)
    st.metric(label="Average of reviews", value=round(avg_review_score_after_delivery_estimated.df()['avg'],2), delta=None)
    st.metric(label="Average of days", value=round(avg_day_delevery_carrier_after_delivery_estimated.df()['avg'],2), delta=None)
with col3:
    st.write('Percent of late')
    st.metric(label="%", value=percent_after_delivery_estimated, delta=None)
    st.metric(label="%", value= round(round(avg_review_score_after_delivery_estimated.df()['avg'],2)/ \
                                      round(avg_review_score_before_delivery_estimated.df()['avg'],2) * 100 - 100,2), delta=None)
    st.metric(label="%", value= round(round(avg_day_delevery_carrier_after_delivery_estimated.df()['avg'],2)/ \
                                      round(avg_day_delevery_carrier_before_delivery_estimated.df()['avg'],2) * 100 - 100,2), delta=None)

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
from orders__customers__reviews
where review_score is not null
group by month(review_creation_date::TIMESTAMP), year(review_creation_date::TIMESTAMP)
order by year(review_creation_date::TIMESTAMP), month(review_creation_date::TIMESTAMP)
''')

st.subheader('Reviews and orders by month')
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
fig.update_layout(
                xaxis=dict(title='Date', titlefont=dict(color='white'), tickfont=dict(color='White'), tickangle=-45),
                yaxis=dict(title='Reviews', titlefont=dict(color='white')),
                yaxis2=dict(title_text='Orders', titlefont=dict(color='white'), overlaying='y', side='right', tickfont=dict(color='lightskyblue'), gridcolor='lightskyblue'))

# Show the plot
st.plotly_chart(fig)


### Map
tab1, tab2 = st.tabs(["Sellers", "Customers"])

with tab1:
    st.header("Sellers")
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

    df = sellers_geo_clean.df()

    map_sellers = folium.Map(tiles ='cartodbpositron')
    marker_cluster = MarkerCluster().add_to(map_sellers)
    for i, row in df.iterrows():
        lat = df.at[i, 'lat']
        lng = df.at[i, 'lng']
        popup = 'City : ' + str(df.at[i, 'city'])
        icon_perso = folium.Icon(color="blue", icon='briefcase')
        folium.Marker(location=[lat,lng], icon=icon_perso, popup=popup).add_to(marker_cluster)
    map_sellers.fit_bounds(map_sellers.get_bounds())

    # call to render Folium map in Streamlit
    st_data = folium_static(map_sellers, width=725)

with tab2:
    st.header("Customers")
    customers = sql('''
    select
        customer_unique_id
        , zip_code_prefix_id
        , customer_city
        , customer_state
    from order_customers
    group by 1, 2, 3, 4
    ''')
    customers_geo_clean = sql('''
    select
        count(t1.customer_unique_id) as nb_customer
        , t1.zip_code_prefix_id as zipcode
        , avg(t2.geolocation_lat) as lat
        , avg(t2.geolocation_lng) as lng
        , t2.geolocation_city as city
    from customers t1
    left join geolocation t2
        on t1.zip_code_prefix_id =  t2.zip_code_prefix_id
    where geolocation_lat is not null
    group by zipcode, city
    ''')

    df = customers_geo_clean.df()
    map_customers = folium.Map(tiles ='cartodbpositron')
    marker_cluster = MarkerCluster().add_to(map_customers)
    for i, row in df.iterrows():
        lat = df.at[i, 'lat']
        lng = df.at[i, 'lng']
        popup = 'City : ' + str(df.at[i, 'city'])
        icon_perso = folium.Icon(color="blue", icon='user')
        folium.Marker(location=[lat,lng], icon=icon_perso, popup=popup).add_to(marker_cluster)
    map_customers.fit_bounds(map_customers.get_bounds())
    
    # call to render Folium map in Streamlit
    st_data = folium_static(map_customers, width=725)

### Word counter review

tab1, tab2 = st.tabs(["Wordcloud", "Word counter"])
        
# nltk.download('punkt')
# nltk.download('stopwords')

# review_mess = sql('''
#     select review_comment_message as text
#     from order_reviews
#     where review_comment_message is not null
#     ''').df()

# text = " ".join(i for i in review_mess.text)
# word_token = nltk.tokenize.word_tokenize(text, language='portuguese', preserve_line=False)
# Words = pd.DataFrame(nltk.FreqDist(word_token).values(), index = nltk.FreqDist(word_token).keys()).sort_values(by=0, ascending=False).head(20)
# Words.plot(kind="barh")
# word_token = nltk.word_tokenize(text.lower())
# Ponct = ['.', '..', '...', '....', '.....', '’','"',':',',', '(', ')','!','-','_','$','%','*','^','¨','<','>','?', ';', '/','+','='
#         ,'e','o','!', 'a', 'é','2', 'q', '1','3','4','5','6','7','8','20','100','10']
# tokens_clean = []

# for words in word_token:
#     if words not in nltk.corpus.stopwords.words("portuguese") and words not in Ponct:
#         tokens_clean.append(words)

# df_word_review = pd.DataFrame({'words' : nltk.FreqDist(tokens_clean).keys(), 'frequency': nltk.FreqDist(tokens_clean).values()})

with tab1:
    ### Wordcloud
    st.header("Wordcloud review")
    st.image('./img/wordcloud.png')
    # wordcloud = WordCloud(width=480, height=480, background_color="black", colormap="rainbow", max_words=50)
    # wordcloud.generate_from_frequencies(nltk.FreqDist(tokens_clean))
    # fig = plt.figure()
    # plt.imshow(wordcloud, interpolation="bilinear")
    # plt.axis("off")
    # plt.margins(x=0, y=0)
    # plt.show()
    # st.pyplot(fig)
with tab2:
    st.header("Word counter review")
    st.image('./img/wordcounter.png')

    # fig = px.bar(df_word_review.sort_values(by='frequency', ascending=False).head(20).sort_values(by='frequency', ascending=True), x='frequency', y='words')
    # fig.update_layout(title="Most frequent words in reviews", xaxis_title="Frequency", yaxis_title="Words")
    # st.plotly_chart(fig)