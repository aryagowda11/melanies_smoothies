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

# Pull both display name and search term from Snowflake
my_dataframe = session.table("smoothies.public.fruit_options").select(
    col('FRUIT_NAME'),
    col('SEARCH_ON')
)

# Collect into Python lists and lookup dictionary
rows = my_dataframe.collect()
fruit_display_list = [row.FRUIT_NAME for row in rows]
search_lookup = {row.FRUIT_NAME: row.SEARCH_ON for row in rows}

# Multiselect widget for ingredients (display names only)
ingredients_list = st.multiselect(
    'Choose up to 5 ingredients:',
    fruit_display_list,
    max_selections=5
)

# Order submission section
if ingredients_list and customer_name:
    ingredients_string = ' '.join(ingredients_list)
    my_insert_stmt = f"""
        INSERT INTO smoothies.public.orders (ingredients, name_on_order)
        VALUES ('{ingredients_string}', '{customer_name}')
    """

    if st.button('Submit Order'):
        session.sql(my_insert_stmt).collect()
        st.success(f"✅ Your Smoothie is ordered, {customer_name}!")

elif customer_name and not ingredients_list:
    st.info("👆 Choose some ingredients before submitting your order.")
elif ingredients_list and not customer_name:
    st.info("✍️ Please enter your name before submitting your order.")

# Nutrition info display section
if ingredients_list:
    for fruit_display_name in ingredients_list:
        # Use SEARCH_ON value for API, fallback to display name if missing
        search_term = search_lookup.get(fruit_display_name, fruit_display_name)

        st.subheader(f"{fruit_display_name} Nutrition Information")

        # Call SmoothieFroot API
        response = requests.get(f"https://my.smoothiefroot.com/api/fruit/{search_term.lower()}")

        if response.status_code == 200:
            st.dataframe(data=response.json(), use_container_width=True)
        else:
            st.warning(f"⚠️ Could not fetch data for {fruit_display_name} (searched for '{search_term}').")
