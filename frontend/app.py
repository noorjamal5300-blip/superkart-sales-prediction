
import streamlit as st
import pandas as pd
import requests

# Base URL of the Flask backend
BACKEND_URL = "http://backend:7860"

# Reference year used to compute Store_Age_Years when the model was trained
REFERENCE_YEAR = 2025

# SuperKart's existing outlets - selecting one fills in all store attributes consistently
STORES = {
    "OUT001 - Supermarket Type1, High, Tier 2 (est. 1987)": ("High", "Tier 2", "Supermarket Type1", 1987),
    "OUT002 - Food Mart, Small, Tier 3 (est. 1998)": ("Small", "Tier 3", "Food Mart", 1998),
    "OUT003 - Departmental Store, Medium, Tier 1 (est. 1999)": ("Medium", "Tier 1", "Departmental Store", 1999),
    "OUT004 - Supermarket Type2, Medium, Tier 2 (est. 2009)": ("Medium", "Tier 2", "Supermarket Type2", 2009),
    "Other store (enter the details manually)": None,
}

# Product type -> (Product_Id prefix, perishable category), exactly as engineered during training
PRODUCT_TYPES = {
    "Baking Goods": ("FD", "Non Perishables"),
    "Breads": ("FD", "Perishables"),
    "Breakfast": ("FD", "Perishables"),
    "Canned": ("FD", "Non Perishables"),
    "Dairy": ("FD", "Perishables"),
    "Frozen Foods": ("FD", "Non Perishables"),
    "Fruits and Vegetables": ("FD", "Perishables"),
    "Meat": ("FD", "Perishables"),
    "Seafood": ("FD", "Perishables"),
    "Snack Foods": ("FD", "Non Perishables"),
    "Starchy Foods": ("FD", "Non Perishables"),
    "Hard Drinks": ("DR", "Non Perishables"),
    "Soft Drinks": ("DR", "Non Perishables"),
    "Health and Hygiene": ("NC", "Non Perishables"),
    "Household": ("NC", "Non Perishables"),
    "Others": ("NC", "Non Perishables"),
}

REQUIRED_COLUMNS = [
    "Product_Weight", "Product_Sugar_Content", "Product_Allocated_Area", "Product_MRP",
    "Store_Size", "Store_Location_City_Type", "Store_Type", "Product_Id_char",
    "Store_Age_Years", "Product_Type_Category",
]

# Page title
st.title("SuperKart System")
st.write("Enter the product and store details below to predict the total sales.")

# ---------------------------------------------------------------- Product details
st.subheader("Product details")
Product_Type = st.selectbox("Product Type", list(PRODUCT_TYPES), index=list(PRODUCT_TYPES).index("Snack Foods"))
Product_Id_char, Product_Type_Category = PRODUCT_TYPES[Product_Type]
st.caption(f"Product ID prefix: **{Product_Id_char}** · Category: **{Product_Type_Category}**")
Product_Weight = st.number_input("Product Weight", min_value=0.0, value=12.66)
Product_Sugar_Content = st.selectbox("Product Sugar Content", ["Low Sugar", "Regular", "No Sugar"])
Product_Allocated_Area = st.number_input("Product Allocated Area (share of store display area)", min_value=0.0, max_value=1.0, value=0.027, format="%.3f")
Product_MRP = st.number_input("Product MRP", min_value=0.0, value=117.08)

# ---------------------------------------------------------------- Store details
st.subheader("Store details")
store_choice = st.selectbox("Store", list(STORES), index=3)
if STORES[store_choice] is not None:
    Store_Size, Store_Location_City_Type, Store_Type, est_year = STORES[store_choice]
    Store_Age_Years = REFERENCE_YEAR - est_year
    st.caption(f"Size: **{Store_Size}** · City: **{Store_Location_City_Type}** · Type: **{Store_Type}** · Age: **{Store_Age_Years} years**")
else:
    Store_Size = st.selectbox("Store Size", ["Small", "Medium", "High"])
    Store_Location_City_Type = st.selectbox("Store Location City Type", ["Tier 1", "Tier 2", "Tier 3"])
    Store_Type = st.selectbox("Store Type", ["Supermarket Type1", "Supermarket Type2", "Departmental Store", "Food Mart"])
    est_year = st.number_input("Store Establishment Year", min_value=1950, max_value=REFERENCE_YEAR, value=2009)
    Store_Age_Years = REFERENCE_YEAR - est_year

# Create JSON payload (same fields the Flask API expects)
product_data = {
    "Product_Weight": Product_Weight,
    "Product_Sugar_Content": Product_Sugar_Content,
    "Product_Allocated_Area": Product_Allocated_Area,
    "Product_MRP": Product_MRP,
    "Store_Size": Store_Size,
    "Store_Location_City_Type": Store_Location_City_Type,
    "Store_Type": Store_Type,
    "Product_Id_char": Product_Id_char,
    "Store_Age_Years": int(Store_Age_Years),
    "Product_Type_Category": Product_Type_Category,
}


def show_api_error(response):
    """Display the error message returned by the API (it always answers with JSON)."""
    try:
        message = response.json().get("error", response.text)
    except ValueError:
        message = response.text
    st.error(f"Prediction failed (HTTP {response.status_code}): {message}")


# ---------------------------------------------------------------- Single Prediction
if st.button("Predict", type='primary'):
    try:
        response = requests.post(f"{BACKEND_URL}/v1/predict", json=product_data, timeout=30)
    except requests.exceptions.RequestException as exc:
        st.error(f"Unable to connect to the prediction API: {exc}")
    else:
        if response.status_code == 200:
            result = response.json()
            st.success(f"Predicted Product Store Sales Total: ₹{result['Sales']:.2f}")
            for warning in result.get("warnings", []):
                st.warning(warning)
        else:
            show_api_error(response)

# ---------------------------------------------------------------- Batch Prediction
st.subheader("Batch Prediction")
st.caption("Upload a CSV with the columns: " + ", ".join(REQUIRED_COLUMNS) + " (extra columns are ignored).")

uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is not None:

    if st.button("Predict for Batch", type='primary'):
        try:
            response = requests.post(f"{BACKEND_URL}/v1/predictbatch", files={"file": uploaded_file}, timeout=120)
        except requests.exceptions.RequestException as exc:
            st.error(f"Unable to connect to the prediction API: {exc}")
        else:
            if response.status_code == 200:
                results = response.json()
                for warning in results.pop("warnings", []):
                    st.warning(warning)
                predictions = pd.Series({int(k): v for k, v in results.items()}).sort_index()

                # Show the predictions next to the uploaded rows
                uploaded_file.seek(0)
                batch_df = pd.read_csv(uploaded_file)
                if len(predictions) == len(batch_df):
                    batch_df["Predicted_Sales"] = predictions.values
                else:
                    batch_df = predictions.rename("Predicted_Sales").to_frame()

                st.success(f"Predictions completed successfully for {len(predictions)} rows!")
                st.dataframe(batch_df, use_container_width=True)
                st.download_button(
                    "Download predictions as CSV",
                    data=batch_df.to_csv(index=False).encode("utf-8"),
                    file_name="superkart_predictions.csv",
                    mime="text/csv",
                )
            else:
                show_api_error(response)
