# streamlit_app.py  (Python 3.9 compatible)

import streamlit as st
import pandas as pd
import requests
from snowflake.snowpark.functions import col

# ---------------- App header ----------------
st.title("🥤 Customize Your Smoothie 🥤")
st.write("Choose the fruits you want in your custom Smoothie!")

# ---------------- Name input ----------------
customer_name = st.text_input("Enter your name for the order:")

# ---------------- Snowflake connection ----------------
# Ensure .streamlit/secrets.toml has:
# [connections.snowflake]
# account = "..."
# user = "..."
# password = "..."
# role = "..."
# warehouse = "..."
# database = "SMOOTHIES"
# schema = "PUBLIC"
cnx = st.connection("snowflake")
session = cnx.session()

# ---- quick diagnostics (shown collapsed) ----
with st.expander("🔎 Connection diagnostics", expanded=False):
    try:
        ctx = session.sql(
            "select current_role() as role, current_database() as db, "
            "current_schema() as schema, current_warehouse() as wh"
        ).collect()[0]
        st.write(dict(ctx))
        # Check the table & columns exist
        sample = session.sql(
            "select FRUIT_NAME, SEARCH_ON from SMOOTHIES.PUBLIC.FRUIT_OPTIONS limit 3"
        ).collect()
        st.write("Sample fruit_options rows:", [dict(r) for r in sample])
    except Exception as e:
        st.warning(f"Diagnostics couldn't read fruit_options: {e}")

# ---------------- Fruit options + search key lookup ----------------
# Expect table: SMOOTHIES.PUBLIC.FRUIT_OPTIONS with columns:
#   FRUIT_NAME (string), SEARCH_ON (string)
try:
    fruit_rows = (
        session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
        .select(col("FRUIT_NAME"), col("SEARCH_ON"))
        .collect()
    )
except Exception as e:
    st.error(
        "Failed to read SMOOTHIES.PUBLIC.FRUIT_OPTIONS. "
        "Verify the table and column names (FRUIT_NAME, SEARCH_ON) and your role/database/schema."
    )
    st.stop()

# Build mapping of display name -> API key (falls back to FRUIT_NAME)
fruit_lookup = {}
for r in fruit_rows:
    fname = r["FRUIT_NAME"]
    skey = (r["SEARCH_ON"] or "").strip() if r["SEARCH_ON"] is not None else ""
    fruit_lookup[fname] = skey if skey else fname

fruit_options = list(fruit_lookup.keys())

# ---------------- Ingredient picker ----------------
ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    options=fruit_options,
    max_selections=5,
)

# ---------------- Submit order ----------------
if st.button("Submit Order"):
    if not customer_name:
        st.info("✍️ Please enter your name before submitting your order.")
    elif not ingredients_list:
        st.info("👆 Choose some ingredients before submitting your order.")
    else:
        ingredients_string = ", ".join(ingredients_list)

        # Escape single quotes for raw SQL
        safe_name = customer_name.replace("'", "''")
        safe_ingredients = ingredients_string.replace("'", "''")

        # ORDERS columns you shared:
        # ORDER_UID (default), ORDER_FILLED (default FALSE),
        # NAME_ON_ORDER, INGREDIENTS, ORDER_TS (default)
        insert_sql = f"""
            INSERT INTO SMOOTHIES.PUBLIC.ORDERS (INGREDIENTS, NAME_ON_ORDER)
            VALUES ('{safe_ingredients}', '{safe_name}')
        """

        try:
            session.sql(insert_sql).collect()
            st.success(f"✅ Your Smoothie is ordered, {customer_name}!")
        except Exception as e:
            st.error(f"Order failed: {e}")

# ---------------- Nutrition info (uses SEARCH_ON) ----------------
if ingredients_list:
    st.subheader("Nutrition info")
    records = []

    for fruit in ingredients_list:
        search_on = fruit_lookup.get(fruit, fruit)

        try:
            # Swap URL if you have your own endpoint
            resp = requests.get(
                f"https://fruityvice.com/api/fruit/{search_on}",
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            # Normalize & annotate
            if isinstance(data, dict):
                data["fruit_display"] = fruit
                data["search_on"] = search_on
                records.append(data)
            elif isinstance(data, list) and data:
                d0 = data[0]
                if isinstance(d0, dict):
                    d0["fruit_display"] = fruit
                    d0["search_on"] = search_on
                    records.append(d0)
                else:
                    records.append(
                        {"value": d0, "fruit_display": fruit, "search_on": search_on}
                    )
        except Exception as e:
            st.warning(f"Could not fetch nutrition for {fruit} ({search_on}): {e}")

    if records:
        st.dataframe(pd.json_normalize(records), use_container_width=True)
    else:
        st.write("No nutrition data to display yet.")
