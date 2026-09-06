
# Import necessary libraries
import numpy as np
import joblib  # For loading the serialized model
import pandas as pd  # For data manipulation
from flask import Flask, request, jsonify  # For creating the Flask API
from werkzeug.exceptions import HTTPException

# Initialize Flask app with a name
superkart_api = Flask("SuperKart")

# Load the trained model (pre-processing + model pipeline)
model = joblib.load("superkart_model.joblib")

# Columns the model was trained on - all must be present (any order, extra columns are ignored)
REQUIRED_COLUMNS = [
    "Product_Weight", "Product_Sugar_Content", "Product_Allocated_Area", "Product_MRP",
    "Store_Size", "Store_Location_City_Type", "Store_Type", "Product_Id_char",
    "Store_Age_Years", "Product_Type_Category",
]
NUMERIC_COLUMNS = ["Product_Weight", "Product_Allocated_Area", "Product_MRP", "Store_Age_Years"]

# Category values seen during training. Other values are still scored (OneHotEncoder(handle_unknown='ignore')
# encodes them as "none of the known categories"), but the response flags them because such predictions are
# less reliable - e.g. the batch file contains "Supermarket Type3", a store type that does not exist in the data.
KNOWN_CATEGORIES = {
    "Product_Sugar_Content": ["Low Sugar", "Regular", "No Sugar"],
    "Store_Size": ["Small", "Medium", "High"],
    "Store_Location_City_Type": ["Tier 1", "Tier 2", "Tier 3"],
    "Store_Type": ["Supermarket Type1", "Supermarket Type2", "Departmental Store", "Food Mart"],
    "Product_Id_char": ["FD", "DR", "NC"],
    "Product_Type_Category": ["Perishables", "Non Perishables"],
}


def validate(df):
    """Check that a DataFrame can be scored.

    Returns (error, warnings): `error` is a message if the data cannot be scored (missing / non-numeric
    fields), otherwise None; `warnings` lists category values the model has never seen during training.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return f"Missing required field(s): {missing}", []
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if df[col].isna().any():
            return f"Field '{col}' must be numeric", []
    warnings = []
    for col, allowed in KNOWN_CATEGORIES.items():
        unexpected = sorted(set(df[col].astype(str)) - set(allowed))
        if unexpected:
            n_rows = int(df[col].astype(str).isin(unexpected).sum())
            warnings.append(f"{n_rows} row(s) have value(s) {unexpected} for '{col}' that were not seen during "
                            f"training (known values: {allowed}); their predictions are less reliable")
    return None, warnings


# Define a route for the home page
@superkart_api.get('/')
def home():
    return "Welcome to the SuperKart System"


# Health-check endpoint (useful for Docker / monitoring)
@superkart_api.get('/health')
def health():
    return jsonify({"status": "ok", "model": type(model.steps[-1][1]).__name__})


# Define an endpoint to predict sales for a single product
@superkart_api.post('/v1/predict')
def predict_sales():
    # Get JSON data from the request
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object with the product and store fields"}), 400

    # Convert the input into a DataFrame and validate it
    input_data = pd.DataFrame([data])
    error, warnings = validate(input_data)
    if error:
        return jsonify({"error": error}), 400

    # Make a prediction using the trained model
    prediction = model.predict(input_data[REQUIRED_COLUMNS]).tolist()[0]

    # Return the prediction as a JSON response (plus warnings about unseen category values, if any)
    response = {'Sales': round(prediction, 2)}
    if warnings:
        response['warnings'] = warnings
    return jsonify(response)


# Define an endpoint to predict sales for a batch of products
@superkart_api.post('/v1/predictbatch')
def predict_sales_batch():
    # Get the uploaded CSV file from the request
    if 'file' not in request.files:
        return jsonify({"error": "Upload a CSV file in the 'file' field of the multipart form-data"}), 400
    try:
        input_data = pd.read_csv(request.files['file'])
    except Exception as exc:
        return jsonify({"error": f"Could not read the CSV file: {exc}"}), 400
    if input_data.empty:
        return jsonify({"error": "The CSV file contains no rows"}), 400

    error, warnings = validate(input_data)
    if error:
        return jsonify({"error": error}), 400

    # Make predictions for the batch data
    predictions = model.predict(input_data[REQUIRED_COLUMNS]).tolist()

    # Create an output dictionary mapping row index to predicted sales
    output_dict = {str(i): round(pred, 2) for i, pred in enumerate(predictions)}
    if warnings:
        output_dict['warnings'] = warnings

    return jsonify(output_dict)


# Always answer with JSON (never an HTML error page), so clients can show a meaningful message
@superkart_api.errorhandler(Exception)
def handle_error(exc):
    if isinstance(exc, HTTPException):
        return jsonify({"error": exc.description}), exc.code
    return jsonify({"error": f"{type(exc).__name__}: {exc}"}), 500


# Run the Flask app in debug mode
if __name__ == '__main__':
    superkart_api.run(debug=True)
