# Import Python packages
import streamlit as st
from snowflake.snowpark.context import get_active_session
from snowflake.snowpark.functions import col  # 👈 Keep imports together

# App title and description
st.title(":cup_with_straw: Customize Your Smoothie :cup_with_straw:")
st.write("Choose the fruits you want in your custom Smoothie!")

# Add a name input box
customer_name = st.text_input("Enter your name for the order:")

# Get Snowflake session and pull fruit options
session = get_active_session()
my_dataframe = session.table("smoothies.public.fruit_options").select(col('FRUIT_NAME'))

# Create multiselect widget for ingredients
ingredients_list = st.multiselect('Choose up to 5 ingredients:', my_dataframe, max_selections=5)

# Only show order button if ingredients and name are entered
if ingredients_list and customer_name:
    # Join selected ingredients into one string
    ingredients_string = ' '.join(ingredients_list)

    # Create the insert SQL statement with both ingredients and name
    my_insert_stmt = f"""
        INSERT INTO smoothies.public.orders (ingredients, name_on_order)
        VALUES ('{ingredients_string}', '{customer_name}')
    """

    # Optional: Uncomment for debugging
    # st.write("SQL Query:", my_insert_stmt)
    # st.stop()

    # Submit button
    time_to_insert = st.button('Submit Order')
    if time_to_insert:
        session.sql(my_insert_stmt).collect()
        st.success(f"✅ Your Smoothie is ordered, {customer_name}!")
elif customer_name and not ingredients_list:
    st.info("👆 Choose some ingredients before submitting your order.")
elif ingredients_list and not customer_name:
    st.info("✍️ Please enter your name before submitting your order.")
