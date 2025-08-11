# Import Python packages
import streamlit as st
from snowflake.snowpark.functions import col
import pandas as pd
import requests

# App title and description
st.title(":cup_with_straw: Customize Your Smoothie :cup_with_straw:")
st.write("Choose the fruits you want in your custom Smoothie!")

# Name input
customer_name = st.text_input("Enter your name for the order:")

# Snowflake connection/session
cnx = st.connection("snowflake")
session = cnx.session()

# Fruit options -> list[str]
fruit_rows = (
    session.table("smoothies.public.fruit_options")
    .select(col("FRUIT_NAME"))
    .collect()
)
fruit_options = [r["FRUIT_NAME"] for r in fruit_rows]

# Multiselect (limit 5)
ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    options=fruit_options,
    max_selections=5,
)

# Submit order
if st.button("Submit Order"):
    if not customer_name:
        st.info("✍️ Please enter your name before submitting your order.")
    elif not ingredients_list:
        st.info("👆 Choose some ingredients before submitting your order.")
    else:
        ingredients_string = ", ".join(ingredients_list)

        # Escape single quotes for SQL
        safe_name = customer_name.replace("'", "''")
        safe_ingredients = ingredients_string.replace("'", "''")

        insert_sql = f"""
            INSERT INTO smoothies.public.orders (ingredients, name_on_order)
            VALUES ('{safe_ingredients}', '{safe_name}')
        """

        try:
            session.sql(insert_sql).collect()
            st.success(f"✅ Your Smoothie is ordered, {customer_name}!")
        except Exception as e:
            st.error(f"Order failed: {e}")

# Show nutrition info for selected fruits
if ingredients_list:
    st.subheader("Nutrition info")
    records = []
    for fruit in ingredients_list:
        try:
            resp = requests.get(
                f"https://my.smoothiefroot.com/api/fruit/{fruit.lower()}",
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            # Normalize to a flat dict and include the fruit name
            if isinstance(data, dict):
                data["fruit"] = fruit
                records.append(data)
            elif isinstance(data, list) and data:
                d = data[0]
                if isinstance(d, dict):
                    d["fruit"] = fruit
                    records.append(d)
        except Exception as e:
            st.warning(f"Could not fetch nutrition for {fruit}: {e}")

    if records:
        st.dataframe(pd.json_normalize(records), use_container_width=True)
    else:
        st.write("No nutrition data to display yet.")
