import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt


st.set_page_config(page_title="Silver Price & Sales Dashboard", layout="wide")

price_df = pd.read_csv("historical_silver_price.csv")
sales_df = pd.read_csv("state_wise_silver_purchased_kg.csv")


# ================= SIDEBAR =================
st.sidebar.header("Silver Price Calculator")

weight = st.sidebar.number_input("Weight of Silver", min_value=0.0, step=1.0)
unit = st.sidebar.selectbox("Unit", ["grams", "kilograms"])
price_per_gram = st.sidebar.number_input("Price per gram (INR)", min_value=0.0)

currency = st.sidebar.selectbox("Currency", ["INR", "USD"])
usd_rate = 83.0  

weight_in_grams = weight if unit == "grams" else weight * 1000
total_cost_inr = weight_in_grams * price_per_gram
total_cost = total_cost_inr / usd_rate if currency == "USD" else total_cost_inr

st.sidebar.subheader("Total Cost")
st.sidebar.write(f"{currency} {total_cost:,.2f}")


# ================= PRICE ANALYSIS =================
st.header("Historical Silver Price Analysis")

price_filter = st.selectbox(
    "Filter price range (INR per kg)",
    ["≤ 20,000", "20,000 – 30,000", "≥ 30,000"]
)

if price_filter == "≤ 20,000":
    filtered_price = price_df[price_df["Silver_Price_INR_per_kg"] <= 20000]
elif price_filter == "20,000 – 30,000":
    filtered_price = price_df[
        (price_df["Silver_Price_INR_per_kg"] > 20000) &
        (price_df["Silver_Price_INR_per_kg"] < 30000)
    ]
else:
    filtered_price = price_df[price_df["Silver_Price_INR_per_kg"] >= 30000]

fig, ax = plt.subplots()
ax.plot(filtered_price["Year"], filtered_price["Silver_Price_INR_per_kg"])
ax.set_xlabel("Year")
ax.set_ylabel("Price (INR per kg)")
ax.set_title("Silver Price Trend")
plt.xticks(rotation=90)
st.pyplot(fig)


# ================= TOP 5 STATES =================
st.header("Top 5 States – Silver Purchases")

top5 = sales_df.sort_values(
    "Silver_Purchased_kg", ascending=False
).head(5)

fig, ax = plt.subplots()
ax.bar(top5["State"], top5["Silver_Purchased_kg"])
ax.set_xlabel("State")
ax.set_ylabel("Silver Purchased (kg)")
ax.set_title("Top 5 Silver Consuming States")
st.pyplot(fig)


# ================= JANUARY SALES =================
st.header("State-wise Silver Sales – January")

qty_col = None
for col in sales_df.columns:
    if "silver" in col.lower() and "kg" in col.lower():
        qty_col = col
        break

if qty_col is None:
    st.error("Silver quantity column not found in dataset.")
    st.stop()

total_january_sales = sales_df[qty_col].sum()

st.subheader("Overall Silver Sales in January")

st.metric(
    label="Total Silver Sold (kg)",
    value=f"{total_january_sales:,.2f}"
)

fig, ax = plt.subplots()
ax.bar(["January"], [total_january_sales])
ax.set_ylabel("Silver Purchased (kg)")
ax.set_title("Overall Silver Sales – January")
st.pyplot(fig)
