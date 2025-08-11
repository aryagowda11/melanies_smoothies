# streamlit_app.py

import re
import requests
import pandas as pd
import streamlit as st
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

# ---- quick diagnostics (optional) ----
with st.expander("🔎 Connection diagnostics", expanded=False):
    try:
        ctx = session.sql(
            "select current_role() as role, current_database() as db, "
            "current_schema() as schema, current_warehouse() as wh"
        ).collect()[0]
        st.write(dict(ctx))
        sample = session.sql(
            "select FRUIT_ID, FRUIT_NAME from SMOOTHIES.PUBLIC.FRUIT_OPTIONS limit 5"
        ).collect()
        st.write("Sample FRUIT_OPTIONS rows:", [dict(r) for r in sample])
    except Exception as e:
        st.warning(f"Diagnostics couldn't read FRUIT_OPTIONS: {e}")

# ---------------- Fetch fruit options ----------------
# Table: SMOOTHIES.PUBLIC.FRUIT_OPTIONS (FRUIT_ID, FRUIT_NAME)
try:
    fruit_rows = (
        session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
        .select(col("FRUIT_ID"), col("FRUIT_NAME"))
        .collect()
    )
except Exception as e:
    st.error(
        "Failed to read SMOOTHIES.PUBLIC.FRUIT_OPTIONS. "
        "Verify the table/columns and your role/database/schema."
    )
    st.stop()

fruit_options = [r["FRUIT_NAME"] for r in fruit_rows]

# ---------------- Helper: derive API key from FRUIT_NAME ----------------
def derive_api_key(name: str) -> str:
    """
    Best-effort mapping to Fruityvice-style names.
    - lowercase
    - remove non-letters
    - handle common plurals (berries, apples, etc.)
    - map multi-word names to a single token when sensible
    """
    n = name.strip().lower()

    # Handle known multi-word cases early
    known_map = {
        "dragon fruit": "dragonfruit",
        "ugli fruit": "ugli",
        "vanilla fruit": "vanilla",
        "yerba mate": "yerba",          # likely not supported; best effort
        "ziziphus jujube": "jujube",    # likely not supported; best effort
        "cantaloupe": "cantaloupe",
        "honeydew": "honeydew",
        "jackfruit": "jackfruit",
    }
    if n in known_map:
        return known_map[n]

    # Normalize to letters and spaces
    n = re.sub(r"[^a-z\s]", "", n)

    # Take first token for two-word things like "lime" from "lime"
    tokens = n.split()
    base = tokens[0] if tokens else n

    # Plural → singular for common cases
    if base.endswith("ies"):           # berries -> berry
        base = base[:-3] + "y"
    elif base.endswith("es") and base[-3:] not in ("ses", "xes"):
        # apples -> apple, limes -> lime; leave 'ses' like 'oranges' -> 'orange' works too
        base = base[:-1] if base.endswith("ses") else base[:-1]  # keep simple
    elif base.endswith("s"):
        base = base[:-1]

    return base

# Build lookup: displayed fruit -> api key
fruit_lookup = {name: derive_api_key(name) for name in fruit_options}

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

# ---------------- Nutrition info (derived keys) ----------------
if ingredients_list:
    st.subheader("Nutrition info")
    records = []

    for fruit in ingredients_list:
        search_on = fruit_lookup.get(fruit, fruit.lower())

        try:
            # Fruityvice public demo API (supports a limited set of fruits)
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
                d0 = data[0] if isinstance(data[0], dict) else {"value": data[0]}
                d0["fruit_display"] = fruit
                d0["search_on"] = search_on
                records.append(d0)

        except Exception as e:
            st.warning(
                f"Could not fetch nutrition for {fruit} (key: {search_on}). "
                f"The public API may not support this fruit. Error: {e}"
            )

    if records:
        st.dataframe(pd.json_normalize(records), use_container_width=True)
    else:
        st.write("No nutrition data to display yet.")
