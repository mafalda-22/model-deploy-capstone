import os
BASE_DIR = os.path.dirname(__file__)
import joblib
import json
import pandas as pd
from flask import Flask, jsonify, request
from peewee import (
    SqliteDatabase, Model, CharField, IntegerField, FloatField,
    IntegrityError, CompositeKey
)
from playhouse.db_url import connect

# -----------------------------------------
# 3. (No CSV ingestion) Features DB must already be pre-populated externally
# -----------------------------------------
# At this point, features.db should already contain all engineered features.


# -----------------------------------------
# 4. Load pipelines and metadata
# -----------------------------------------
pipeline_A = joblib.load(os.path.join(BASE_DIR, 'pipeline_A_1.pickle'))
pipeline_B = joblib.load(os.path.join(BASE_DIR, 'pipeline_B_1.pickle'))
with open(os.path.join(BASE_DIR, 'columns_A_1.json'), 'r') as fh:
    FEATURE_COLUMNS_A = json.load(fh)
with open(os.path.join(BASE_DIR, 'dtypes_A_1.pickle'), 'rb') as fh:
    FEATURE_DTYPES_A = joblib.load(fh)
with open(os.path.join(BASE_DIR, 'columns_B_1.json'), 'r') as fh:
    FEATURE_COLUMNS_B = json.load(fh)
with open(os.path.join(BASE_DIR, 'dtypes_B_1.pickle'), 'rb') as fh:
    FEATURE_DTYPES_B = joblib.load(fh)

# -----------------------------------------
# 5. Helper: fetch features from the DB
# -----------------------------------------
def build_features(sku: str, time_key: int):
    try:
        rec = FeatureRow.get((FeatureRow.sku == sku) & (FeatureRow.time_key == time_key))
    except FeatureRow.DoesNotExist:
        return None, None, {'error': 'SKU or date not found'}
    row = rec.__data__
    df_A = pd.DataFrame([{col: row[col] for col in FEATURE_COLUMNS_A}])
    df_B = pd.DataFrame([{col: row[col] for col in FEATURE_COLUMNS_B}])
    try:
        df_A = df_A.astype(FEATURE_DTYPES_A)
        df_B = df_B.astype(FEATURE_DTYPES_B)
    except Exception as e:
        return None, None, {'error': f'Dtype casting error: {e}'}
    return df_A, df_B, None

# -----------------------------------------
# 6. Flask app and endpoints
# -----------------------------------------
app = Flask(__name__)

@app.route('/forecast_prices/', methods=['POST'])
def forecast_prices():
    data = request.get_json() or {}
    sku = data.get('sku'); tk = data.get('time_key')
    if not isinstance(sku, str) or not isinstance(tk, int):
        return jsonify({'error':'Invalid input'}), 200
    df_A, df_B, err = build_features(sku, tk)
    if err:
        return jsonify(err), 200
    try:
        pred_A = float(pipeline_A.predict(df_A)[0])
        proba_A = float(pipeline_A.predict_proba(df_A)[0].max())
        pred_B = float(pipeline_B.predict(df_B)[0])
        proba_B = float(pipeline_B.predict_proba(df_B)[0].max())
    except Exception as e:
        return jsonify({'error': f'Prediction error: {e}'}), 200
    try:
        Forecast.create(sku=sku, time_key=tk, pvp_pred_A=pred_A, pvp_pred_B=pred_B)
    except IntegrityError:
        return jsonify({'error':'Forecast exists'}), 200
    return jsonify({
        'sku':sku,'time_key':tk,
        'pred_A':pred_A,'proba_A':proba_A,
        'pred_B':pred_B,'proba_B':proba_B
    }), 200

@app.route('/actual_prices/', methods=['POST'])
def actual_prices():
    data = request.get_json() or {}
    sku = data.get('sku'); tk = data.get('time_key')
    aA = data.get('pvp_actual_A'); aB = data.get('pvp_actual_B')
    if not (isinstance(sku,str) and isinstance(tk,int)
            and isinstance(aA,(int,float)) and isinstance(aB,(int,float))):
        return jsonify({'error':'Invalid actuals input'}), 200
    try:
        rec = Forecast.get((Forecast.sku==sku)&(Forecast.time_key==tk))
    except Forecast.DoesNotExist:
        return jsonify({'error':'No matching forecast'}), 200
    rec.pvp_actual_A=aA; rec.pvp_actual_B=aB; rec.save()
    return jsonify({
        'sku':sku,'time_key':tk,
        'actual_A':aA,'actual_B':aB
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
