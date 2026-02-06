import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pathlib import Path


st.set_page_config(page_title="Silver Price & Sales Dashboard", layout="wide")

BASE_DIR = Path(__file__).resolve().parent


@st.cache_data
def load_price_data() -> pd.DataFrame:
    return pd.read_csv(BASE_DIR / "historical_silver_price.csv")


@st.cache_data
def load_sales_data() -> pd.DataFrame:
    return pd.read_csv(BASE_DIR / "state_wise_silver_purchased_kg.csv")


@st.cache_data
def load_india_boundary() -> gpd.GeoDataFrame:
    return gpd.read_file(BASE_DIR / "shapefile" / "india_India_Country_Boundary.geojson")


@st.cache_data
def load_state_capitals() -> gpd.GeoDataFrame:
    return gpd.read_file(BASE_DIR / "shapefile" / "State_Capitals.shp")


price_df = load_price_data()
sales_df = load_sales_data()
india_capitals = load_state_capitals()
india_boundary = load_india_boundary()

capitals_code_col = None
for col in india_capitals.columns:
    if col.lower() == "state":
        capitals_code_col = col
        break

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


# ================= INDIA MAP =================
st.header("India State-wise Silver Purchases")
if capitals_code_col is None:
    st.error("Could not find a 'state' code column in State_Capitals.shp")
    st.stop()


def normalize_state_name(value: str) -> str:
    value = str(value or "").strip()
    value = " ".join(value.split())
    return value


# Your State_Capitals.shp is a *points* layer (capitals), not state polygons.
# So instead of a choropleth fill, we plot the India boundary + capital points
# sized/colored by the 'Silver_Purchased_kg' value.
STATE_NAME_TO_CODE = {
    "Andhra Pradesh": "AP",
    "Arunachal Pradesh": "AR",
    "Assam": "AS",
    "Bihar": "BR",
    "Chhattisgarh": "CG",
    "Goa": "GA",
    "Gujarat": "GJ",
    "Haryana": "HR",
    "Himachal Pradesh": "HP",
    "Jharkhand": "JH",
    "Karnataka": "KA",
    "Kerala": "KL",
    "Madhya Pradesh": "MP",
    "Maharashtra": "MH",
    "Manipur": "MN",
    "Meghalaya": "ML",
    "Mizoram": "MZ",
    "Nagaland": "NL",
    "Odisha": "OR",
    "Punjab": "PB",
    "Rajasthan": "RJ",
    "Sikkim": "SK",
    "Tamil Nadu": "TN",
    "Telangana": "TG",
    "Tripura": "TR",
    "Uttar Pradesh": "UP",
    "Uttarakhand": "UK",
    "West Bengal": "WB",
    "Delhi": "DL",
    "Jammu & Kashmir": "JK",
    "Jammu and Kashmir": "JK",
    "Ladakh": "LA",
}

sales_df = sales_df.copy()
sales_df["State"] = sales_df["State"].map(normalize_state_name)
sales_df["state_code"] = sales_df["State"].map(STATE_NAME_TO_CODE)

missing_state_codes = sales_df[sales_df["state_code"].isna()]["State"].unique().tolist()
if missing_state_codes:
    st.warning(
        "Some state names couldn't be mapped to the shapefile state codes. "
        f"Missing: {', '.join(missing_state_codes)}"
    )

capitals = india_capitals[[capitals_code_col, "geometry"]].copy()
capitals = capitals.rename(columns={capitals_code_col: "state_code"})

merged_map = capitals.merge(
    sales_df[["State", "state_code", "Silver_Purchased_kg"]],
    on="state_code",
    how="left",
)

try:
    # Ensure consistent CRS for plotting
    if india_boundary.crs is None:
        india_boundary = india_boundary.set_crs("EPSG:4326")
    if merged_map.crs is None:
        merged_map = merged_map.set_crs(india_capitals.crs or "EPSG:4326")

    india_boundary = india_boundary.to_crs("EPSG:4326")
    merged_map = merged_map.to_crs("EPSG:4326")
except Exception as exc:
    st.error(f"Failed to reproject map layers: {exc}")
    st.stop()


fig, ax = plt.subplots(1, 1, figsize=(12, 10))
india_boundary.plot(ax=ax, color="#F5F5F5", edgecolor="#222222", linewidth=0.8)

plot_df = merged_map.dropna(subset=["Silver_Purchased_kg"]).copy()
if plot_df.empty:
    st.error("No sales data could be joined to the map (check state code mapping).")
else:
    # Bubble size scaling
    max_val = float(plot_df["Silver_Purchased_kg"].max())
    plot_df["_size"] = (plot_df["Silver_Purchased_kg"] / max_val).clip(0, 1) * 800 + 40

    plot_df.plot(
        ax=ax,
        column="Silver_Purchased_kg",
        cmap="Greys",
        legend=True,
        markersize=plot_df["_size"],
        alpha=0.85,
        edgecolor="black",
        linewidth=0.5,
    )

ax.set_title("State/UT-wise Silver Purchases (kg) — capital point map")
ax.axis("off")
st.pyplot(fig)

with st.expander("Show map join preview"):
    st.dataframe(merged_map[["state_code", "State", "Silver_Purchased_kg"]])


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
