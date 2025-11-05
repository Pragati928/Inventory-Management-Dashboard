import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.colored_header import colored_header

from db_functions_new import (
    connect_to_db,
    get_basic_info,
    get_additonal_tables,
    get_categories,
    get_suppliers,
    add_new_manual_id,
    get_monthly_sales,
    get_category_stock_distribution,
    get_all_products,
    get_product_history,
    place_reorder,
    get_pending_reorders,
    mark_reorder_as_received
)

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="Inventory Management Dashboard",
    layout="wide",
    page_icon="📦"
)

# -------------------- SIDEBAR --------------------
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1251/1251846.png", width=100)
st.sidebar.title("📊 Inventory Dashboard")

option = st.sidebar.radio(
    "Choose an Option:",
    ["📈 Basic Information", "⚙️ Operational Tasks"]
)

st.sidebar.markdown("---")
st.sidebar.info("👩‍💻 Pragati Kumari — Data Analyst | Portfolio Project")
st.sidebar.markdown("[🔗 LinkedIn](https://www.linkedin.com/in/pragati-kumari-b60352305/)")
st.sidebar.markdown("[💻 GitHub](https://github.com/Pragati928)")


# -------------------- MAIN TITLE --------------------
colored_header(
    label="📦 Inventory & Supply Chain Analytics Dashboard",
    description="Real-time insights into stock performance, supplier network, and reorder operations.",
    color_name="blue-70",
)

# -------------------- CONNECT TO DB --------------------
db = connect_to_db()
if not db:
    st.error("❌ Database connection failed. Please check your SQL Server settings.")
    st.stop()

cursor = db.cursor()

# -------------------- BASIC INFORMATION --------------------
if option == "📈 Basic Information":
    st.subheader("📊 Overview Metrics")

    # --- Refresh button ---
    if st.button("🔄 Refresh Data"):
        st.experimental_rerun()

    basic_info = get_basic_info(cursor)

    # Layout for key metrics
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)

    col1.metric("🏢 Total Suppliers", basic_info["Total Suppliers"])
    col2.metric("📦 Total Products", basic_info["Total Products"])
    col3.metric("🗂️ Total Categories", basic_info["Total Categories Dealing"])
    col4.metric("💰 Sale Value (3M)", f"${basic_info['Total Sale Value (Last 3 Months)']:,}")
    col5.metric("📈 Restock Value (3M)", f"${basic_info['Total Restock Value (Last 3 Months)']:,}")
    col6.metric("⚠️ Below Reorder (No Pending)", basic_info["Below Reorder & No Pending Reorders"])

    style_metric_cards(border_left_color="#6C63FF", border_size_px=2)

    # ------------------- CHARTS -------------------
    st.markdown("### 📆 Monthly Sales Trend")
    sales = get_monthly_sales(cursor)
    sales_df = pd.DataFrame(sales)
    fig = px.line(
        sales_df,
        x="month",
        y="total_sales",
        title="Monthly Sales Trend (Last Year)",
        markers=True,
        color_discrete_sequence=["#636EFA"]
    )
    fig.update_traces(hovertemplate="Month: %{x}<br>Sales: %{y:$,.2f}")
    st.plotly_chart(fig, use_container_width=True)

    # ------------------- PIE CHART -------------------
    st.markdown("### 🏷️ Category-Wise Stock Distribution")
    stock = get_category_stock_distribution(cursor)
    stock_df = pd.DataFrame(stock)
    fig2 = px.pie(
        stock_df,
        names="category",
        values="total_stock",
        title="Current Stock Share by Category",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ------------------- DETAILED TABLES -------------------
    with st.expander("📋 View Detailed Tables"):
        tables = get_additonal_tables(cursor)
        for label, data in tables.items():
            st.markdown(f"#### {label}")
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
            st.divider()

# -------------------- OPERATIONAL TASKS --------------------
elif option == "⚙️ Operational Tasks":
    st.subheader("🧭 Manage Operations")
    selected_task = st.selectbox(
        "Select Task",
        ["Add New Product", "Product History", "Place Reorder", "Receive Reorder"],
        index=0
    )

    # ---------- Add New Product ----------
    if selected_task == "Add New Product":
        st.markdown("#### ➕ Add New Product")

        categories = get_categories(cursor)
        suppliers = get_suppliers(cursor)

        with st.form("Add_Product_Form"):
            col1, col2 = st.columns(2)
            product_name = col1.text_input("Product Name")
            product_category = col2.selectbox("Category", categories)

            col3, col4 = st.columns(2)
            product_price = col3.number_input("Price", min_value=0.00)
            product_stock = col4.number_input("Stock Quantity", min_value=0, step=1)

            col5, col6 = st.columns(2)
            product_level = col5.number_input("Reorder Level", min_value=0, step=1)
            supplier_ids = [s["supplier_id"] for s in suppliers]
            supplier_names = [s["supplier_name"] for s in suppliers]

            supplier_id = col6.selectbox(
                "Supplier",
                options=supplier_ids,
                format_func=lambda x: supplier_names[supplier_ids.index(x)]
            )

            submitted = st.form_submit_button("✅ Add Product")

            if submitted:
                if not product_name:
                    st.warning("⚠️ Please enter the product name.")
                else:
                    try:
                        add_new_manual_id(cursor, db, product_name, product_category, product_price, product_stock, product_level, supplier_id)
                        st.success(f"✅ Product '{product_name}' added successfully!")
                    except Exception as e:
                        st.error(f"❌ Error adding the product: {e}")

    # ---------- Product History ----------
    elif selected_task == "Product History":
        st.markdown("#### 📜 Product Inventory History")

        products = get_all_products(cursor)
        product_names = [p["product_name"] for p in products]
        product_ids = [p["product_id"] for p in products]

        selected_product_name = st.selectbox("Select Product", product_names)

        if selected_product_name:
            selected_product_id = product_ids[product_names.index(selected_product_name)]
            history_data = get_product_history(cursor, selected_product_id)
            if history_data:
                df = pd.DataFrame(history_data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("ℹ️ No history found for this product.")

    # ---------- Place Reorder ----------
    elif selected_task == "Place Reorder":
        st.markdown("#### 📦 Place Reorder")
        products = get_all_products(cursor)
        product_names = [p["product_name"] for p in products]
        product_ids = [p["product_id"] for p in products]

        selected_product_name = st.selectbox("Select Product", product_names)
        reorder_qty = st.number_input("Reorder Quantity", min_value=1, step=1)

        if st.button("📩 Place Reorder"):
            if not selected_product_name:
                st.error("⚠️ Please select a product.")
            else:
                selected_product_id = product_ids[product_names.index(selected_product_name)]
                try:
                    place_reorder(cursor, db, selected_product_id, reorder_qty)
                    st.success(f"✅ Reorder placed for '{selected_product_name}' (Qty: {reorder_qty})")
                except Exception as e:
                    st.error(f"❌ Error placing reorder: {e}")

    # ---------- Receive Reorder ----------
    elif selected_task == "Receive Reorder":
        st.markdown("#### 📥 Mark Reorder as Received")
        pending_reorders = get_pending_reorders(cursor)
        if not pending_reorders:
            st.info("🟢 No pending orders to receive.")
        else:
            reorder_labels = [f"ID {r['reorder_id']} — {r['product_name']}" for r in pending_reorders]
            reorder_ids = [r['reorder_id'] for r in pending_reorders]

            selected_label = st.selectbox("Select Reorder", reorder_labels)
            selected_reorder_id = reorder_ids[reorder_labels.index(selected_label)]

            if st.button("✅ Mark as Received"):
                try:
                    mark_reorder_as_received(cursor, db, selected_reorder_id)
                    st.success(f"✅ Reorder ID {selected_reorder_id} marked as received!")
                except Exception as e:
                    st.error(f"❌ Error updating reorder: {e}")
