# Import Python packages
import streamlit as st
from snowflake.snowpark.functions import col
import requests

# App title and description
st.title(":cup_with_straw: Customize Your Smoothie :cup_with_straw:")
st.write("Choose the fruits you want in your custom Smoothie!")

# Add a name input box
customer_name = st.text_input("Enter your name for the order:")

# Get Snowflake session and pull fruit options
cnx = st.connection("snowflake")
session = cnx.session()
my_dataframe = session.table("smoothies.public.fruit_options").select(col('FRUIT_NAME'))

# Convert Snowpark DataFrame to list of fruit names
fruit_options = [row.FRUIT_NAME for row in my_dataframe.collect()]

# Create multiselect widget for ingredients
ingredients_list = st.multiselect('Choose up to 5 ingredients:', fruit_options, max_selections=5)

# Only show order button if ingredients and name are entered
if ingredients_list and customer_name:
    ingredients_string = ' '.join(ingredients_list)

    # Create the insert SQL statement
    my_insert_stmt = f"""
        INSERT INTO smoothies.public.orders (ingredients, name_on_order)
        VALUES ('{ingredients_string}', '{customer_name}')
    """

    # Submit button
    if st.button('Submit Order'):
        session.sql(my_insert_stmt).collect()
        st.success(f"✅ Your Smoothie is ordered, {customer_name}!")

elif customer_name and not ingredients_list:
    st.info("👆 Choose some ingredients before submitting your order.")
elif ingredients_list and not customer_name:
    st.info("✍️ Please enter your name before submitting your order.")

# Show fruit info if ingredients selected
if ingredients_list:
    for fruit_chosen in ingredients_list:
        response = requests.get(f"https://my.smoothiefroot.com/api/fruit/{fruit_chosen.lower()}")
        if response.status_code == 200:
            st.dataframe(data=response.json(), use_container_width=True)
        else:
            st.warning(f"⚠️ Could not fetch data for {fruit_chosen}.")
