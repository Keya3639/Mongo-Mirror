
import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo import MongoClient

# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="MongoMirror | Business Intelligence",
    page_icon="🍃",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================================================
# LIGHT GREEN THEME
# ==================================================

st.markdown("""
<style>
    .stApp {
        background-color: #F5F8F5;
        color: #20382C;
    }

    [data-testid="stSidebar"] {
        background-color: #EAF2EB;
        border-right: 1px solid #D8E5D9;
    }

    [data-testid="stSidebar"] > div {
        padding-top: 1.5rem;
    }

    .brand-title {
        font-size: 27px;
        font-weight: 800;
        color: #00684A;
        letter-spacing: -1px;
        margin-bottom: 0;
    }

    .brand-caption {
        color: #648071;
        font-size: 12px;
        margin-top: 3px;
    }

    .section-caption {
        color: #648071;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #DDE8DF;
        padding: 19px;
        border-radius: 13px;
        box-shadow: 0 2px 8px rgba(25, 70, 45, 0.035);
    }

    [data-testid="stMetricLabel"] {
        color: #648071;
    }

    [data-testid="stMetricValue"] {
        color: #174B35;
        font-weight: 750;
    }

    h1, h2, h3 {
        color: #20382C;
    }

    div[data-testid="stPlotlyChart"] {
        background-color: #FFFFFF;
        border: 1px solid #E0E9E1;
        border-radius: 12px;
        padding: 8px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #DDE8DF;
        border-radius: 10px;
    }

    .footer-note {
        color: #789083;
        font-size: 12px;
        text-align: center;
        padding: 20px 0 5px 0;
    }

    div.stButton > button {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==================================================
# DATABASE CONNECTION AND DATA LOADING
# ==================================================

@st.cache_data(ttl=30)
def load_data():
    client = MongoClient(
        "mongodb://localhost:27017/",
        serverSelectionTimeoutMS=5000
    )

    try:
        db = client["mongomirror"]

        orders = list(db["orders"].find({}, {"_id": 0}))
        products = list(db["products"].find({}, {"_id": 0}))
        customers = list(db["customers"].find({}, {"_id": 0}))

        return orders, products, customers

    finally:
        client.close()


try:
    all_orders, all_products, all_customers = load_data()

except Exception as error:
    st.error(
        "Could not connect to MongoDB. "
        "Please ensure your local MongoDB server is running."
    )
    st.code(str(error))
    st.stop()

if not all_orders:
    st.warning("No orders found in the MongoDB database.")
    st.stop()

orders_df = pd.DataFrame(all_orders)
products_df = pd.DataFrame(all_products)
customers_df = pd.DataFrame(all_customers)

# ==================================================
# ENRICH ORDER DATA
# ==================================================

product_lookup = {
    p["product_id"]: p
    for p in all_products
    if "product_id" in p
}

customer_lookup = {
    c["customer_id"]: c
    for c in all_customers
    if "customer_id" in c
}

orders_df["product_name"] = orders_df["product_id"].map(
    lambda pid: product_lookup.get(pid, {}).get(
        "name", "Unknown Product"
    )
)

orders_df["category"] = orders_df["product_id"].map(
    lambda pid: product_lookup.get(pid, {}).get(
        "category", "Unknown Category"
    )
)

orders_df["customer_name"] = orders_df["customer_id"].map(
    lambda cid: customer_lookup.get(cid, {}).get(
        "name", f"Customer {cid}"
    )
)

orders_df["revenue"] = (
    orders_df["quantity"] * orders_df["unit_price"]
)

orders_df["order_date"] = pd.to_datetime(
    orders_df["order_date"],
    errors="coerce"
)

orders_df = orders_df.dropna(subset=["order_date"])

if orders_df.empty:
    st.warning("No valid order dates were found.")
    st.stop()

orders_df["month"] = (
    orders_df["order_date"].dt.to_period("M").astype(str)
)

# ==================================================
# SIDEBAR: BRAND, NAVIGATION AND FILTERS
# ==================================================

with st.sidebar:

    st.markdown(
        '<div class="brand-title">🍃 MongoMirror</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="brand-caption">'
        'See your business as data sees it.'
        '</div>',
        unsafe_allow_html=True
    )

    st.divider()

    st.markdown("#### WORKSPACE")

    page = st.radio(
        "Navigation",
        [
            "Overview",
            "Sales Analytics",
            "Product Insights",
            "Customer Insights",
            "Order Status"
        ],
        label_visibility="collapsed"
    )

    st.divider()

    st.markdown("#### FILTERS")

    min_date = orders_df["order_date"].min().date()
    max_date = orders_df["order_date"].max().date()

    selected_dates = st.date_input(
        "Order date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    if isinstance(selected_dates, (tuple, list)):
        if len(selected_dates) == 2:
            start_date, end_date = selected_dates
        elif len(selected_dates) == 1:
            start_date = end_date = selected_dates[0]
        else:
            start_date, end_date = min_date, max_date
    else:
        start_date = end_date = selected_dates

    available_categories = sorted(
        orders_df["category"].dropna().unique().tolist()
    )

    selected_categories = st.multiselect(
        "Product categories",
        options=available_categories,
        default=available_categories
    )

    st.divider()

    st.caption("MongoDB · Python · Pandas · Plotly · Streamlit")
    st.caption("Demo dataset · Local database")


# ==================================================
# APPLY FILTERS
# ==================================================

date_mask = (
    (orders_df["order_date"].dt.date >= start_date)
    & (orders_df["order_date"].dt.date <= end_date)
)

date_orders = orders_df[date_mask].copy()

filtered_orders = date_orders[
    (date_orders["status"] == "Delivered")
    & (date_orders["category"].isin(selected_categories))
].copy()

# ==================================================
# SHARED PLOTLY STYLING
# ==================================================

GREEN = "#00684A"
SAGE = "#8BBF9F"
TEAL = "#159A83"
PURPLE = "#8B7CC8"
ORANGE = "#E5A04D"
PINK = "#D77FA1"
BLUE = "#6495CD"

PALETTE = [GREEN, SAGE, TEAL, PURPLE, ORANGE, PINK, BLUE]

def style_chart(fig, height=370):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family="Arial, sans-serif",
            color="#496354",
            size=12
        ),
        title_font=dict(
            size=16,
            color="#20382C"
        ),
        height=height,
        margin=dict(l=20, r=25, t=65, b=30),
        legend=dict(
            bgcolor="rgba(255,255,255,0)"
        ),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            font_color="#20382C"
        )
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="#EDF2ED",
        zeroline=False
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor="#EDF2ED",
        zeroline=False
    )

    return fig


def show_empty_message(message):
    st.info(message)


# ==================================================
# HEADER
# ==================================================

st.markdown(
    '<div class="section-caption">BUSINESS INTELLIGENCE WORKSPACE</div>',
    unsafe_allow_html=True
)

st.title(page)

st.caption(
    f"Reporting period: {start_date.strftime('%d %b %Y')} "
    f"– {end_date.strftime('%d %b %Y')}"
)

if not selected_categories:
    st.warning("Select at least one product category in the sidebar.")

# ==================================================
# PAGE 1: OVERVIEW
# ==================================================

if page == "Overview":

    revenue = filtered_orders["revenue"].sum()
    delivered_count = len(filtered_orders)
    units_sold = int(filtered_orders["quantity"].sum())

    customer_order_counts = filtered_orders.groupby(
        "customer_id"
    )["order_id"].count()

    repeat_customers = int(
        (customer_order_counts >= 2).sum()
    )

    total_customers = len(all_customers)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Delivered Revenue", f"₹{revenue:,.0f}")
    c2.metric("Delivered Orders", f"{delivered_count:,}")
    c3.metric("Units Sold", f"{units_sold:,}")
    c4.metric("Repeat Customers", f"{repeat_customers:,}")

    st.caption(
        f"{total_customers} customer records in the database. "
        "Repeat customers are counted within the selected filters."
    )

    st.divider()

    left, right = st.columns([1.5, 1])

    with left:
        st.subheader("Monthly Revenue Trends")

        if not filtered_orders.empty:
            monthly = (
                filtered_orders.groupby("month", as_index=False)
                .agg(revenue=("revenue", "sum"))
                .sort_values("month")
            )

            fig = px.line(
                monthly,
                x="month",
                y="revenue",
                markers=True,
                color_discrete_sequence=[GREEN],
                labels={
                    "month": "Month",
                    "revenue": "Revenue (₹)"
                }
            )

            fig.update_traces(
                line=dict(width=3),
                marker=dict(size=8)
            )

            fig.update_layout(
                title="Delivered Revenue by Month",
                hovermode="x unified",
                showlegend=False
            )

            style_chart(fig)
            st.plotly_chart(fig, use_container_width=True)
        else:
            show_empty_message("No delivered revenue for these filters.")

    with right:
        st.subheader("Revenue by Category")

        if not filtered_orders.empty:
            category_data = (
                filtered_orders.groupby("category", as_index=False)
                .agg(revenue=("revenue", "sum"))
                .sort_values("revenue", ascending=False)
            )

            fig = px.pie(
                category_data,
                names="category",
                values="revenue",
                hole=0.62,
                color_discrete_sequence=PALETTE
            )

            fig.update_traces(
                textposition="inside",
                textinfo="percent",
                hovertemplate=(
                    "%{label}<br>Revenue: ₹%{value:,.0f}"
                    "<br>Share: %{percent}<extra></extra>"
                )
            )

            fig.update_layout(title="Category Contribution")
            style_chart(fig)
            st.plotly_chart(fig, use_container_width=True)
        else:
            show_empty_message("No category revenue for these filters.")

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Top Products")

        if not filtered_orders.empty:
            top_products = (
                filtered_orders.groupby("product_name", as_index=False)
                .agg(
                    revenue=("revenue", "sum"),
                    units_sold=("quantity", "sum")
                )
                .nlargest(5, "revenue")
                .sort_values("revenue")
            )

            fig = px.bar(
                top_products,
                x="revenue",
                y="product_name",
                orientation="h",
                color="product_name",
                color_discrete_sequence=PALETTE,
                text="revenue",
                hover_data=["units_sold"]
            )

            fig.update_traces(
                texttemplate="₹%{x:,.0f}",
                textposition="outside",
                cliponaxis=False
            )

            fig.update_layout(
                title="Top 5 Products by Revenue",
                xaxis_title="Revenue (₹)",
                yaxis_title="",
                showlegend=False
            )

            style_chart(fig, 390)
            st.plotly_chart(fig, use_container_width=True)
        else:
            show_empty_message("No product sales for these filters.")

    with right:
        st.subheader("Top Customers")

        if not filtered_orders.empty:
            top_customers = (
                filtered_orders.groupby(
                    ["customer_id", "customer_name"],
                    as_index=False
                )
                .agg(
                    spending=("revenue", "sum"),
                    delivered_orders=("order_id", "count")
                )
                .nlargest(5, "spending")
                .sort_values("spending")
            )

            fig = px.bar(
                top_customers,
                x="spending",
                y="customer_name",
                orientation="h",
                color="customer_name",
                color_discrete_sequence=PALETTE,
                text="spending",
                hover_data=["delivered_orders"]
            )

            fig.update_traces(
                texttemplate="₹%{x:,.0f}",
                textposition="outside",
                cliponaxis=False
            )

            fig.update_layout(
                title="Top 5 Customers by Spending",
                xaxis_title="Delivered Spending (₹)",
                yaxis_title="",
                showlegend=False
            )

            style_chart(fig, 390)
            st.plotly_chart(fig, use_container_width=True)
        else:
            show_empty_message("No customer spending for these filters.")


# ==================================================
# PAGE 2: SALES ANALYTICS
# ==================================================

elif page == "Sales Analytics":

    st.subheader("Revenue Performance")

    if not filtered_orders.empty:

        revenue = filtered_orders["revenue"].sum()
        avg_order_value = filtered_orders["revenue"].mean()
        order_count = len(filtered_orders)

        c1, c2, c3 = st.columns(3)
        c1.metric("Revenue", f"₹{revenue:,.0f}")
        c2.metric("Average Order Value", f"₹{avg_order_value:,.0f}")
        c3.metric("Delivered Orders", f"{order_count:,}")

        monthly = (
            filtered_orders.groupby("month", as_index=False)
            .agg(
                revenue=("revenue", "sum"),
                orders=("order_id", "count")
            )
            .sort_values("month")
        )

        fig = px.bar(
            monthly,
            x="month",
            y="revenue",
            color="revenue",
            color_continuous_scale=["#CBE5D2", GREEN],
            text="revenue",
            hover_data=["orders"],
            labels={
                "month": "Month",
                "revenue": "Revenue (₹)",
                "orders": "Delivered Orders"
            }
        )

        fig.update_traces(
            texttemplate="₹%{y:,.0f}",
            textposition="outside",
            cliponaxis=False
        )

        fig.update_layout(
            title="Monthly Revenue Comparison",
            coloraxis_showscale=False,
            xaxis_title="Month",
            yaxis_title="Revenue (₹)"
        )

        style_chart(fig, 420)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Monthly Sales Data")

        st.dataframe(
            monthly.rename(columns={
                "month": "Month",
                "revenue": "Revenue (₹)",
                "orders": "Delivered Orders"
            }),
            use_container_width=True,
            hide_index=True
        )

    else:
        show_empty_message("No sales data matches your current filters.")


# ==================================================
# PAGE 3: PRODUCT INSIGHTS
# ==================================================

elif page == "Product Insights":

    st.subheader("Product Performance")

    if not filtered_orders.empty:

        product_data = (
            filtered_orders.groupby(
                ["product_name", "category"],
                as_index=False
            )
            .agg(
                revenue=("revenue", "sum"),
                units_sold=("quantity", "sum"),
                delivered_orders=("order_id", "count")
            )
            .sort_values("revenue", ascending=False)
        )

        c1, c2 = st.columns(2)

        c1.metric(
            "Unique Products Sold",
            f"{product_data['product_name'].nunique():,}"
        )

        c2.metric(
            "Total Units Sold",
            f"{int(product_data['units_sold'].sum()):,}"
        )

        fig = px.bar(
            product_data.head(10).sort_values("revenue"),
            x="revenue",
            y="product_name",
            orientation="h",
            color="category",
            color_discrete_sequence=PALETTE,
            text="revenue",
            hover_data=["units_sold", "delivered_orders"],
            labels={
                "revenue": "Revenue (₹)",
                "product_name": "Product",
                "category": "Category"
            }
        )

        fig.update_traces(
            texttemplate="₹%{x:,.0f}",
            textposition="outside",
            cliponaxis=False
        )

        fig.update_layout(
            title="Top Products by Delivered Revenue",
            xaxis_title="Revenue (₹)",
            yaxis_title=""
        )

        style_chart(fig, 460)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Product Performance Table")

        display_products = product_data.rename(columns={
            "product_name": "Product",
            "category": "Category",
            "revenue": "Revenue (₹)",
            "units_sold": "Units Sold",
            "delivered_orders": "Delivered Orders"
        })

        st.dataframe(
            display_products,
            use_container_width=True,
            hide_index=True
        )

    else:
        show_empty_message("No product sales match your filters.")


# ==================================================
# PAGE 4: CUSTOMER INSIGHTS
# ==================================================

elif page == "Customer Insights":

    st.subheader("Customer Spending Analysis")

    if not filtered_orders.empty:

        customer_data = (
            filtered_orders.groupby(
                ["customer_id", "customer_name"],
                as_index=False
            )
            .agg(
                spending=("revenue", "sum"),
                delivered_orders=("order_id", "count"),
                units_purchased=("quantity", "sum")
            )
            .sort_values("spending", ascending=False)
        )

        repeat_count = int(
            (customer_data["delivered_orders"] >= 2).sum()
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Customers with Delivered Orders",
            f"{len(customer_data):,}"
        )

        c2.metric(
            "Repeat Customers",
            f"{repeat_count:,}"
        )

        c3.metric(
            "Average Customer Spending",
            f"₹{customer_data['spending'].mean():,.0f}"
        )

        fig = px.bar(
            customer_data.head(10).sort_values("spending"),
            x="spending",
            y="customer_name",
            orientation="h",
            color="spending",
            color_continuous_scale=["#CBE5D2", GREEN],
            text="spending",
            hover_data=["delivered_orders", "units_purchased"],
            labels={
                "spending": "Spending (₹)",
                "customer_name": "Customer",
                "delivered_orders": "Delivered Orders",
                "units_purchased": "Units Purchased"
            }
        )

        fig.update_traces(
            texttemplate="₹%{x:,.0f}",
            textposition="outside",
            cliponaxis=False
        )

        fig.update_layout(
            title="Top Customers by Delivered Spending",
            coloraxis_showscale=False,
            xaxis_title="Spending (₹)",
            yaxis_title=""
        )

        style_chart(fig, 440)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Customer Details")

        display_customers = customer_data.rename(columns={
            "customer_id": "Customer ID",
            "customer_name": "Customer",
            "spending": "Delivered Spending (₹)",
            "delivered_orders": "Delivered Orders",
            "units_purchased": "Units Purchased"
        })

        st.dataframe(
            display_customers,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "Repeat customer means at least two delivered order records "
            "within the selected date and category filters. "
            "This is not a long-term retention metric."
        )

    else:
        show_empty_message("No customer activity matches your filters.")


# ==================================================
# PAGE 5: ORDER STATUS
# ==================================================

elif page == "Order Status":

    st.subheader("Order Status Overview")

    if not date_orders.empty:

        status_data = (
            date_orders.groupby("status", as_index=False)
            .agg(order_count=("order_id", "count"))
            .sort_values("order_count", ascending=False)
        )

        status_colors = {
            "Delivered": GREEN,
            "Pending": ORANGE,
            "Cancelled": "#D86B6B",
            "Returned": PURPLE
        }

        colors = [
            status_colors.get(status, SAGE)
            for status in status_data["status"]
        ]

        c1, c2 = st.columns(2)

        c1.metric("Total Orders", f"{len(date_orders):,}")

        delivered_pct = (
            (date_orders["status"] == "Delivered").mean() * 100
        )

        c2.metric("Delivered Order Share", f"{delivered_pct:.1f}%")

        fig = px.pie(
            status_data,
            names="status",
            values="order_count",
            hole=0.55,
            color="status",
            color_discrete_map=status_colors,
            labels={
                "status": "Order Status",
                "order_count": "Orders"
            }
        )

        fig.update_traces(
            textposition="inside",
            textinfo="label+percent"
        )

        fig.update_layout(title="Order Status Distribution")
        style_chart(fig)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Status Breakdown")

        st.dataframe(
            status_data.rename(columns={
                "status": "Status",
                "order_count": "Order Count"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "Revenue and product/customer spending analyses use delivered "
            "orders only. Order status counts include all order statuses."
        )

    else:
        show_empty_message("No orders found in this date range.")


# ==================================================
# FOOTER
# ==================================================

st.divider()

st.markdown(
    '<div class="footer-note">'
    'MongoMirror · Customer & Sales Insights · '
    'Powered by MongoDB, Python, Pandas, Plotly & Streamlit'
    '<br>Sample data for portfolio demonstration.'
    '</div>',
    unsafe_allow_html=True
)
