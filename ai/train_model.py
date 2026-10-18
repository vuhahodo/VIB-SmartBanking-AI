"""
VIB-SmartBanking AI — Production Recommendation Model Training Pipeline
=======================================================================
Problem: Next-Best-Action & Cross-Sell Recommendation
- Target 1: Credit Card (Thẻ tín dụng VIB Super Card, Online Plus,...)
- Target 2: Term Deposit (Tiết kiệm trực tuyến iDepo, Tiền gửi có kỳ hạn)
- Target 3: Consumer Loan (Vay tiêu dùng tín chấp, thấu chi)

Input: 6 datasets from VIB Hackathon 2021 Datarathon
Output:
  - 3 trained XGBoost models (.joblib)
  - Feature column dictionaries per target (.joblib)
  - Training metrics & summary (.json & .joblib)
  - Demo sample customer features (.json)
"""

import os
import gc
import json
import time
import warnings
import numpy as np
import pandas as pd
from datetime import datetime

import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ============================================================
# 0. CONFIG & ENVIRONMENT DETECTION
# ============================================================
def resolve_paths():
    # Detect Kaggle input
    if os.path.exists("/kaggle/input"):
        for root, dirs, files in os.walk("/kaggle/input"):
            if "1.Data_Customer.csv" in files:
                print(f"[ENV] Kaggle environment detected. Dataset at: {root}")
                return root, "/kaggle/working"
        print("[ENV] Kaggle detected but looking deeper in /kaggle/input:")
        for root, dirs, files in os.walk("/kaggle/input"):
            print(f"  {root}: {files}")

    # Local paths
    local_candidates = [
        os.path.join(os.getcwd(), "Track 1 Datarathon"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Track 1 Datarathon")),
        r"d:\HocTap\N4_K1\Cloud_Computing\Final_CloudComputing\Track 1 Datarathon"
    ]
    for p in local_candidates:
        if os.path.exists(os.path.join(p, "1.Data_Customer.csv")):
            models_dir = os.path.join(os.path.dirname(__file__), "models")
            os.makedirs(models_dir, exist_ok=True)
            print(f"[ENV] Local environment detected. Data at: {p}")
            return p, models_dir

    raise FileNotFoundError("Could not locate VIB Hackathon data directory!")

DATA_DIR, OUTPUT_DIR = resolve_paths()
os.makedirs(OUTPUT_DIR, exist_ok=True)

REFERENCE_DATE = pd.Timestamp("2019-12-31")
print("=" * 70)
print(" VIB-SMARTBANKING AI — NEXT-BEST-ACTION TRAINING PIPELINE")
print("=" * 70)
print(f"Data Source   : {DATA_DIR}")
print(f"Output Target : {OUTPUT_DIR}")

# ============================================================
# 1. LOAD DATA
# ============================================================
print("\n[1/7] Loading datasets...")
t0 = time.time()

# 1. Customer
df_customer = pd.read_csv(
    os.path.join(DATA_DIR, "1.Data_Customer.csv"),
    dtype=str,
    low_memory=False
)
df_customer['CUSTOMER_NUMBER'] = df_customer['CUSTOMER_NUMBER'].str.strip()
print(f"  - Customer demographics : {df_customer.shape[0]:,} records")

# 2. Transaction
df_transaction = pd.read_csv(
    os.path.join(DATA_DIR, "2.Data_MyVIB_Transaction.csv"),
    dtype={'CUSTOMER_NUMBER': str}
)
df_transaction['CUSTOMER_NUMBER'] = df_transaction['CUSTOMER_NUMBER'].str.strip()
print(f"  - MyVIB Transactions   : {df_transaction.shape[0]:,} records")

# 4. Deposit
df_deposit = pd.read_csv(
    os.path.join(DATA_DIR, "4.Data_Deposit.csv"),
    dtype={'CUSTOMER_NUMBER': str}
)
df_deposit['CUSTOMER_NUMBER'] = df_deposit['CUSTOMER_NUMBER'].str.strip()
print(f"  - Deposit records       : {df_deposit.shape[0]:,} records")

# 5. Lending
df_lending = pd.read_csv(
    os.path.join(DATA_DIR, "5.Data_Lending.csv"),
    dtype={'CUSTOMER_NUMBER': str}
)
df_lending['CUSTOMER_NUMBER'] = df_lending['CUSTOMER_NUMBER'].str.strip()
print(f"  - Lending records       : {df_lending.shape[0]:,} records")

# 6. Card
df_card = pd.read_csv(
    os.path.join(DATA_DIR, "6.Data_Card.csv"),
    dtype={'CUSTOMER_NUMBER': str}
)
df_card['CUSTOMER_NUMBER'] = df_card['CUSTOMER_NUMBER'].str.strip()
print(f"  - Card records          : {df_card.shape[0]:,} records")
print(f"  Datasets loaded in {time.time() - t0:.2f}s")

# ============================================================
# 2. FEATURE ENGINEERING
# ============================================================
print("\n[2/7] Feature Engineering...")

# --- 2A: Demographics (from Data_Customer) ---
print("  2A: Customer Demographics...")
df_demo = df_customer[['CUSTOMER_NUMBER']].copy()

# Gender
df_demo['is_male'] = (df_customer['CLIENT_SEX'] == 'M').astype(int)
df_demo['is_female'] = (df_customer['CLIENT_SEX'] == 'F').astype(int)

# Age calculation (from DATE_OF_BIRTH)
dob = pd.to_datetime(df_customer['DATE_OF_BIRTH'], errors='coerce')
df_demo['age'] = ((REFERENCE_DATE - dob).dt.days / 365.25).round(1)
df_demo.loc[(df_demo['age'] < 16) | (df_demo['age'] > 95), 'age'] = np.nan
median_age = df_demo['age'].median()
df_demo['age'] = df_demo['age'].fillna(median_age if not np.isnan(median_age) else 35.0)

# Tenure (days since CIF creation)
cif_date = pd.to_datetime(df_customer['CLIENT_CREATE_DATE'], errors='coerce')
df_demo['tenure_days'] = (REFERENCE_DATE - cif_date).dt.days
df_demo['tenure_days'] = df_demo['tenure_days'].fillna(0).clip(lower=0)

# Digital onboarding
ib_date = pd.to_datetime(df_customer['IB_REGISTER_DATE'], errors='coerce')
df_demo['has_ebank'] = ib_date.notna().astype(int)
df_demo['days_cif_to_ebank'] = (ib_date - cif_date).dt.days
df_demo['days_cif_to_ebank'] = df_demo['days_cif_to_ebank'].fillna(-1)

df_demo['is_staff_vib'] = (df_customer['STAFF_VIB'] == 'Y').astype(int)
df_demo['sms_registered'] = (df_customer['SMS'] == 'Y').astype(int)

# Register channel
for ch in ['BRANCH', 'MYVIB', 'AUTO-JOB', 'WEBSITE']:
    col_name = f'channel_{ch.lower().replace("-", "_")}'
    df_demo[col_name] = (df_customer['EB_REGISTER_CHANNEL'] == ch).astype(int)

# Verification method
for vm in ['SMART_OTP', 'SMS', 'HARD_TOKEN']:
    df_demo[f'verify_{vm.lower()}'] = (df_customer['VERIFY_METHOD'] == vm).astype(int)

print(f"    -> {df_demo.shape[1] - 1} demographic features created.")

# --- 2B: Transaction Behavior (from Data_MyVIB_Transaction) ---
print("  2B: Transaction behavioral aggregations...")
txn_agg = df_transaction.groupby('CUSTOMER_NUMBER').agg(
    total_transactions=('TRANS_NO', 'sum'),
    total_trans_amount=('TRANS_AMOUNT', 'sum'),
    avg_trans_amount=('TRANS_AMOUNT', 'mean'),
    max_trans_amount=('TRANS_AMOUNT', 'max'),
    median_trans_amount=('TRANS_AMOUNT', 'median'),
    std_trans_amount=('TRANS_AMOUNT', 'std'),
    num_trans_days=('TRANS_DATE', 'nunique'),
    avg_trans_hour=('TRANS_HOUR', 'mean'),
).reset_index()

# Transaction categories (LV1)
txn_lv1 = df_transaction.groupby(['CUSTOMER_NUMBER', 'TRANS_LV1'])['TRANS_NO'].sum().unstack(fill_value=0)
txn_lv1_sum = txn_lv1.sum(axis=1).replace(0, 1)
for col in ['Transfer', 'Topup', 'Payment']:
    if col in txn_lv1.columns:
        txn_lv1[f'pct_{col.lower()}'] = txn_lv1[col] / txn_lv1_sum
    else:
        txn_lv1[f'pct_{col.lower()}'] = 0.0
pct_cols = [c for c in txn_lv1.columns if c.startswith('pct_')]
txn_lv1_pct = txn_lv1[pct_cols].reset_index()

# Key LV2 spending categories (credit card repayment, eWallet, utilities, QR)
txn_lv2 = df_transaction.groupby(['CUSTOMER_NUMBER', 'TRANS_LV2'])['TRANS_AMOUNT'].sum().unstack(fill_value=0)
key_lv2_cats = ['Outside_VIB', 'Within_VIB', 'eWallet', 'Mobile', 'Credit_card_repayment', 'Utilities_payment', 'QR_payment']
for cat in key_lv2_cats:
    safe_name = f'amount_{cat.lower()}'
    if cat in txn_lv2.columns:
        txn_lv2[safe_name] = txn_lv2[cat]
    else:
        txn_lv2[safe_name] = 0.0
amount_cols = [c for c in txn_lv2.columns if c.startswith('amount_')]
txn_lv2_feats = txn_lv2[amount_cols].reset_index()

# Time patterns
df_transaction['is_night'] = df_transaction['TRANS_HOUR'].apply(lambda h: 1 if h >= 22 or h <= 6 else 0)
df_transaction['is_weekend'] = df_transaction['DAY_OF_WEEK'].isin(['Sat', 'Sun']).astype(int)
txn_time = df_transaction.groupby('CUSTOMER_NUMBER').agg(
    pct_night_trans=('is_night', 'mean'),
    pct_weekend_trans=('is_weekend', 'mean')
).reset_index()

txn_features = txn_agg \
    .merge(txn_lv1_pct, on='CUSTOMER_NUMBER', how='left') \
    .merge(txn_lv2_feats, on='CUSTOMER_NUMBER', how='left') \
    .merge(txn_time, on='CUSTOMER_NUMBER', how='left')
txn_features['std_trans_amount'] = txn_features['std_trans_amount'].fillna(0)
print(f"    -> {txn_features.shape[1] - 1} transaction features created.")

# Free memory from raw transactions
del df_transaction, txn_agg, txn_lv1, txn_lv2, txn_time
gc.collect()

# --- 2C: App Intent & Activity (from 3.Data_MyVIB_Activity - FAST VECTORIZED) ---
print("  2C: MyVIB Activity intent signals (16M+ rows)...")
t_act = time.time()
important_activities = {
    'LOGIN': 'count_login',
    'LOGIN_FACEID': 'count_login_faceid',
    'LOGIN_FINGER': 'count_login_finger',
    'MB_INTEREST_RATE_VIEW': 'count_interest_rate_view',
    'QUERY_LOAN_ACCOUNT': 'count_query_loan',
    'QUERY_ACCOUNT_INFORMATION': 'count_query_account_info',
    'QUERY_ACCOUNT_PORFOLIO': 'count_query_portfolio',
    'QUERY_CURRENT_ACCOUNT': 'count_query_current',
    'MB_EXCHANGE_RATE_VIEW': 'count_exchange_rate_view',
    'MB_ACCOUNT_QUICK_BALANCE': 'count_quick_balance',
    'EXPORT_ACCOUNT_STATEMENT_LOAN': 'count_export_loan_stmt',
    'CHANGE_PASSWORD': 'count_change_password',
    'MB_CHANGE_PIN': 'count_change_pin',
    'LOGOUT': 'count_logout',
}

activity_csv_path = os.path.join(DATA_DIR, "3.Data_MyVIB_Activity.csv")
chunk_aggregates = []
chunk_totals = []

for chunk in pd.read_csv(
    activity_csv_path,
    chunksize=2_000_000,
    usecols=['CUSTOMER_NUMBER', 'ACTIVITY_NAME', 'ACTIVITY_NO']
):
    chunk['CUSTOMER_NUMBER'] = chunk['CUSTOMER_NUMBER'].astype(str).str.strip()
    
    # 1. Total activities per customer in chunk
    c_tot = chunk.groupby('CUSTOMER_NUMBER')['ACTIVITY_NO'].sum().reset_index()
    chunk_totals.append(c_tot)
    
    # 2. Filter to key high-signal activities
    mask = chunk['ACTIVITY_NAME'].isin(important_activities.keys())
    if mask.any():
        c_agg = chunk[mask].groupby(['CUSTOMER_NUMBER', 'ACTIVITY_NAME'])['ACTIVITY_NO'].sum().reset_index()
        chunk_aggregates.append(c_agg)

# Combine totals
df_act_total = pd.concat(chunk_totals, ignore_index=True).groupby('CUSTOMER_NUMBER')['ACTIVITY_NO'].sum().reset_index()
df_act_total.rename(columns={'ACTIVITY_NO': 'total_activities'}, inplace=True)

# Combine key activities and pivot
df_act_combined = pd.concat(chunk_aggregates, ignore_index=True).groupby(['CUSTOMER_NUMBER', 'ACTIVITY_NAME'])['ACTIVITY_NO'].sum().reset_index()
df_act_pivot = df_act_combined.pivot_table(
    index='CUSTOMER_NUMBER',
    columns='ACTIVITY_NAME',
    values='ACTIVITY_NO',
    fill_value=0
).reset_index()

# Rename columns to standardized feature names
rename_map = {orig: feat for orig, feat in important_activities.items() if orig in df_act_pivot.columns}
df_act_pivot.rename(columns=rename_map, inplace=True)

# Ensure all target features exist
for feat_name in important_activities.values():
    if feat_name not in df_act_pivot.columns:
        df_act_pivot[feat_name] = 0

act_features = df_act_total.merge(df_act_pivot, on='CUSTOMER_NUMBER', how='left').fillna(0)

# Bio login ratios
tot_logins = act_features['count_login'] + act_features['count_login_faceid'] + act_features['count_login_finger']
act_features['total_logins'] = tot_logins
act_features['login_faceid_ratio'] = np.where(tot_logins > 0, act_features['count_login_faceid'] / tot_logins, 0.0)
act_features['login_finger_ratio'] = np.where(tot_logins > 0, act_features['count_login_finger'] / tot_logins, 0.0)

print(f"    -> {act_features.shape[1] - 1} activity features aggregated in {time.time() - t_act:.2f}s.")

del chunk_aggregates, chunk_totals, df_act_total, df_act_combined, df_act_pivot
gc.collect()

# --- 2D: Deposit & CASA (from Data_Deposit) ---
print("  2D: Deposit & Current Account (CASA) features...")
dep_agg = df_deposit.groupby('CUSTOMER_NUMBER').agg(
    avg_ca_balance_mean=('AVG_CA_BALANCE', 'mean'),
    avg_ca_balance_max=('AVG_CA_BALANCE', 'max'),
    avg_ca_balance_min=('AVG_CA_BALANCE', 'min'),
    avg_ca_balance_std=('AVG_CA_BALANCE', 'std'),
    avg_ca_balance_last=('AVG_CA_BALANCE', 'last'),
    max_ca_accounts=('COUNT_CA_ACCT', 'max'),
    max_td_accounts=('COUNT_TD_ACCT', 'max'),
    avg_td_balance_mean=('AVG_TD_BALANCE', 'mean'),
    avg_td_balance_max=('AVG_TD_BALANCE', 'max'),
    num_deposit_months=('MONTH', 'nunique'),
).reset_index()

dep_agg['has_term_deposit'] = (dep_agg['max_td_accounts'] > 0).astype(int)
dep_agg['avg_ca_balance_std'] = dep_agg['avg_ca_balance_std'].fillna(0)

# CASA balance growth trend
dep_first_last = df_deposit.sort_values('MONTH').groupby('CUSTOMER_NUMBER')['AVG_CA_BALANCE'].agg(['first', 'last'])
dep_first_last['ca_balance_growth'] = np.where(
    dep_first_last['first'] > 0,
    (dep_first_last['last'] - dep_first_last['first']) / dep_first_last['first'],
    0.0
)
dep_agg = dep_agg.merge(dep_first_last[['ca_balance_growth']].reset_index(), on='CUSTOMER_NUMBER', how='left').fillna(0)
print(f"    -> {dep_agg.shape[1] - 1} deposit/CASA features created.")

del df_deposit, dep_first_last
gc.collect()

# --- 2E: Lending Profile (from Data_Lending) ---
print("  2E: Lending profile features...")
lend_agg = df_lending.groupby('CUSTOMER_NUMBER').agg(
    max_loan_count=('COUNT_OF_LOAN', 'max'),
    avg_loan_amount_mean=('AVG_LOAN_AMOUNT', 'mean'),
    avg_loan_amount_max=('AVG_LOAN_AMOUNT', 'max'),
    avg_loan_amount_std=('AVG_LOAN_AMOUNT', 'std'),
    num_lending_months=('MONTH', 'nunique'),
).reset_index()

lend_agg['has_loan'] = (lend_agg['max_loan_count'] > 0).astype(int)
lend_agg['avg_loan_amount_std'] = lend_agg['avg_loan_amount_std'].fillna(0)

# Loan growth
lend_first_last = df_lending.sort_values('MONTH').groupby('CUSTOMER_NUMBER')['AVG_LOAN_AMOUNT'].agg(['first', 'last'])
lend_first_last['loan_amount_growth'] = np.where(
    lend_first_last['first'] > 0,
    (lend_first_last['last'] - lend_first_last['first']) / lend_first_last['first'],
    0.0
)
lend_agg = lend_agg.merge(lend_first_last[['loan_amount_growth']].reset_index(), on='CUSTOMER_NUMBER', how='left').fillna(0)
print(f"    -> {lend_agg.shape[1] - 1} lending features created.")

del df_lending, lend_first_last
gc.collect()

# --- 2F: Card Profile (from Data_Card) ---
print("  2F: Card usage features...")
card_agg = df_card.groupby('CUSTOMER_NUMBER').agg(
    max_creditcards=('COUNT_CREDITCARD', 'max'),
    max_debitcards=('COUNT_DEBITCARD', 'max'),
    num_card_months=('MONTH', 'nunique'),
).reset_index()

card_agg['has_creditcard'] = (card_agg['max_creditcards'] > 0).astype(int)
card_agg['has_debitcard'] = (card_agg['max_debitcards'] > 0).astype(int)
print(f"    -> {card_agg.shape[1] - 1} card features created.")

del df_card
gc.collect()

# ============================================================
# 3. MERGE MASTER DATASET
# ============================================================
print("\n[3/7] Merging master customer feature set...")
df_master = df_demo.copy()
df_master = df_master.merge(txn_features, on='CUSTOMER_NUMBER', how='left')
df_master = df_master.merge(act_features, on='CUSTOMER_NUMBER', how='left')
df_master = df_master.merge(dep_agg, on='CUSTOMER_NUMBER', how='left')
df_master = df_master.merge(lend_agg, on='CUSTOMER_NUMBER', how='left')
df_master = df_master.merge(card_agg, on='CUSTOMER_NUMBER', how='left')

fill_zero_cols = [c for c in df_master.columns if c != 'CUSTOMER_NUMBER']
df_master[fill_zero_cols] = df_master[fill_zero_cols].fillna(0)

print(f"  Master Dataset: {df_master.shape[0]:,} customers x {df_master.shape[1] - 1} total features.")

# ============================================================
# 4. DEFINE LABELS & STRICT LEAKAGE PREVENTION
# ============================================================
print("\n[4/7] Target definitions and leakage-safe feature partitioning...")

targets = {
    'target_creditcard': {
        'label_col': 'has_creditcard',
        'display_name': 'Credit Card (VIB Super Card)',
        'leak_cols': [
            'has_creditcard', 'max_creditcards', 'num_card_months'
        ]
    },
    'target_term_deposit': {
        'label_col': 'has_term_deposit',
        'display_name': 'Term Deposit (iDepo)',
        'leak_cols': [
            'has_term_deposit', 'max_td_accounts', 'avg_td_balance_mean', 'avg_td_balance_max'
        ]
    },
    'target_loan': {
        'label_col': 'has_loan',
        'display_name': 'Consumer Loan',
        'leak_cols': [
            'has_loan', 'max_loan_count', 'avg_loan_amount_mean', 'avg_loan_amount_max',
            'avg_loan_amount_std', 'loan_amount_growth', 'num_lending_months'
        ]
    }
}

# Create binary targets in df_master
for target_key, config in targets.items():
    df_master[target_key] = df_master[config['label_col']].astype(int)
    pos = df_master[target_key].sum()
    neg = len(df_master) - pos
    print(f"  [{target_key}] ({config['display_name']}):")
    print(f"    Positive = {pos:,} ({pos/len(df_master)*100:.1f}%) | Negative = {neg:,} ({neg/len(df_master)*100:.1f}%)")

# Base excluded columns for all models
common_exclude = {'CUSTOMER_NUMBER', 'target_creditcard', 'target_term_deposit', 'target_loan'}

# Build safe feature lists per target
features_by_target = {}
for target_key, config in targets.items():
    all_exclude = common_exclude.union(set(config['leak_cols']))
    safe_feats = [c for c in df_master.columns if c not in all_exclude]
    features_by_target[target_key] = safe_feats
    print(f"    -> Safe features for {target_key}: {len(safe_feats)} features (excluded {len(config['leak_cols'])} leak cols)")

# ============================================================
# 5. MODEL TRAINING & EVALUATION (XGBOOST)
# ============================================================
print("\n[5/7] Training XGBoost classifiers...")

from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, classification_report
import joblib

try:
    from xgboost import XGBClassifier
    USE_XGBOOST = True
    print("  Engine: XGBoost (Tree Method: hist)")
except ImportError:
    from sklearn.ensemble import HistGradientBoostingClassifier
    USE_XGBOOST = False
    print("  Engine: HistGradientBoostingClassifier (fallback)")

trained_models = {}
eval_results = {}
top_feature_importances = {}

for target_key, config in targets.items():
    print(f"\n" + "-" * 50)
    print(f"  Training Model: {target_key} ({config['display_name']})")
    print("-" * 50)
    
    feature_list = features_by_target[target_key]
    X = df_master[feature_list].values
    y = df_master[target_key].values
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42
    )
    
    pos_count = y_train.sum()
    neg_count = len(y_train) - pos_count
    scale_weight = float(neg_count / max(pos_count, 1))
    
    t_train = time.time()
    if USE_XGBOOST:
        model = XGBClassifier(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_weight,
            tree_method='hist',
            eval_metric='auc',
            random_state=42,
            n_jobs=-1
        )
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        importances = model.feature_importances_
    else:
        model = HistGradientBoostingClassifier(
            max_iter=150,
            max_depth=5,
            learning_rate=0.08,
            random_state=42
        )
        model.fit(X_train, y_train)
        importances = np.ones(len(feature_list)) / len(feature_list)
        
    train_duration = time.time() - t_train
    
    # Evaluation
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.50).astype(int)
    
    auc = float(roc_auc_score(y_test, y_prob))
    prec = float(precision_score(y_test, y_pred, zero_division=0))
    rec = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    
    print(f"  Trained in {train_duration:.2f}s")
    print(f"  ROC-AUC   : {auc:.4f}")
    print(f"  Precision : {prec:.4f}")
    print(f"  Recall    : {rec:.4f}")
    print(f"  F1-Score  : {f1:.4f}")
    
    trained_models[target_key] = model
    eval_results[target_key] = {
        'roc_auc': round(auc, 4),
        'precision': round(prec, 4),
        'recall': round(rec, 4),
        'f1': round(f1, 4),
        'positives_test': int(y_test.sum()),
        'total_test': len(y_test)
    }
    
    # Store top 10 feature importances
    feat_tuples = sorted(zip(feature_list, importances), key=lambda x: x[1], reverse=True)
    top_feature_importances[target_key] = [
        {'feature': f, 'importance': round(float(imp), 4)} for f, imp in feat_tuples[:10]
    ]

# ============================================================
# 6. FEATURE IMPORTANCE DISPLAY
# ============================================================
print("\n[6/7] Key Predictive Drivers (Top 8 per product)...")
for target_key, feat_list in top_feature_importances.items():
    print(f"\n  === {target_key} ({targets[target_key]['display_name']}) ===")
    for rank, item in enumerate(feat_list[:8], 1):
        bar = "#" * int(item['importance'] * 50)
        print(f"    {rank:2d}. {item['feature']:30s} {item['importance']:.4f}  {bar}")

# ============================================================
# 7. EXPORT MODELS, METADATA & SAMPLE FOR FASTAPI
# ============================================================
print("\n[7/7] Saving models and production inference assets...")

# 1. Save individual model files
for target_key, model in trained_models.items():
    model_filename = f"model_{target_key}.joblib"
    model_path = os.path.join(OUTPUT_DIR, model_filename)
    joblib.dump(model, model_path, compress=3)
    file_size_kb = os.path.getsize(model_path) / 1024
    print(f"  - Saved: {model_filename} ({file_size_kb:.1f} KB)")

# 2. Save feature column maps
joblib.dump(features_by_target, os.path.join(OUTPUT_DIR, "features_by_target.joblib"))
print(f"  - Saved: features_by_target.joblib")

# 3. Save training summary JSON
summary_payload = {
    'created_at': datetime.now().isoformat(),
    'num_customers': len(df_master),
    'results': eval_results,
    'top_drivers': top_feature_importances,
    'features_count': {k: len(v) for k, v in features_by_target.items()}
}
summary_path = os.path.join(OUTPUT_DIR, "training_metrics.json")
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary_payload, f, indent=2, ensure_ascii=False)
print(f"  - Saved: training_metrics.json")

# 4. Generate 5 realistic customer sample feature dictionaries for FastAPI testing
sample_customers = df_master.sample(n=5, random_state=42)
sample_records = []
for _, row in sample_customers.iterrows():
    rec = {}
    for col in df_master.columns:
        val = row[col]
        if pd.isna(val):
            rec[col] = 0
        elif isinstance(val, (np.integer, int)):
            rec[col] = int(val)
        elif isinstance(val, (np.floating, float)):
            rec[col] = round(float(val), 2)
        else:
            rec[col] = str(val)
    sample_records.append(rec)

sample_path = os.path.join(OUTPUT_DIR, "sample_customers.json")
with open(sample_path, "w", encoding="utf-8") as f:
    json.dump(sample_records, f, indent=2, ensure_ascii=False)
print(f"  - Saved: sample_customers.json (5 demo customers)")

print("\n" + "=" * 70)
print(" PIPELINE FINISHED SUCCESSFULLY!")
print("=" * 70)
for k, v in eval_results.items():
    print(f"  {k:22s} -> ROC-AUC: {v['roc_auc']:.4f} | F1: {v['f1']:.4f}")
print(f"\nAssets written to: {OUTPUT_DIR}")
