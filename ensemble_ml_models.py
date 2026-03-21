# Day 10: Ensemble ML Models
# Train Random Forest, XGBoost, and Neural Network
# Combine predictions (ensemble voting)

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

print("=== ENSEMBLE ML MODELS ===\n")

# Load advanced features
df = pd.read_csv('advanced_features.csv', index_col='Date')

# Prepare data
feature_cols = [col for col in df.columns if col not in ['Close', 'target_1d', 'target_5d']]
X = df[feature_cols].values
y = df['target_1d'].values  # Predict 1-day ahead

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Scale features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print(f"Training set: {len(X_train)} samples")
print(f"Test set: {len(X_test)} samples")
print(f"Features: {len(feature_cols)}\n")

# ========== MODEL 1: RANDOM FOREST ==========
print("Training Random Forest...")
rf_model = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
rf_model.fit(X_train_scaled, y_train)
rf_accuracy = rf_model.score(X_test_scaled, y_test)
rf_predictions = rf_model.predict_proba(X_test_scaled)[:, 1]
print(f"✓ Random Forest accuracy: {rf_accuracy:.1%}")

# ========== MODEL 2: XGBOOST ==========
print("Training XGBoost...")
xgb_model = xgb.XGBClassifier(n_estimators=100, max_depth=7, learning_rate=0.1, random_state=42, n_jobs=-1)
xgb_model.fit(X_train_scaled, y_train)
xgb_accuracy = xgb_model.score(X_test_scaled, y_test)
xgb_predictions = xgb_model.predict_proba(X_test_scaled)[:, 1]
print(f"✓ XGBoost accuracy: {xgb_accuracy:.1%}")

# ========== ENSEMBLE: VOTING CLASSIFIER ==========
print("\nCreating Ensemble...")

# Ensemble prediction = average of both models
ensemble_predictions = (rf_predictions + xgb_predictions) / 2
ensemble_predictions_binary = (ensemble_predictions > 0.5).astype(int)
ensemble_accuracy = (ensemble_predictions_binary == y_test).mean()

print(f"✓ Ensemble accuracy: {ensemble_accuracy:.1%}")

# ========== COMPARISON ==========
print("\n" + "="*60)
print("MODEL COMPARISON")
print("="*60)
print(f"Random Forest:    {rf_accuracy:.1%}")
print(f"XGBoost:          {xgb_accuracy:.1%}")
print(f"Ensemble (avg):   {ensemble_accuracy:.1%}")

best_accuracy = max(rf_accuracy, xgb_accuracy, ensemble_accuracy)
best_model = "Random Forest" if rf_accuracy == best_accuracy else "XGBoost" if xgb_accuracy == best_accuracy else "Ensemble"
print(f"\nBest: {best_model} with {best_accuracy:.1%}")

# ========== PREDICTION STATISTICS ==========
print("\n" + "="*60)
print("PREDICTION STATISTICS")
print("="*60)

print(f"\nEnsemble predictions on test set:")
print(f"  Bullish (>0.5): {(ensemble_predictions > 0.5).sum()} ({(ensemble_predictions > 0.5).sum()/len(ensemble_predictions)*100:.1f}%)")
print(f"  Bearish (<0.5): {(ensemble_predictions <= 0.5).sum()} ({(ensemble_predictions <= 0.5).sum()/len(ensemble_predictions)*100:.1f}%)")
print(f"  Average confidence: {ensemble_predictions.mean():.1%}")

# ========== FEATURE IMPORTANCE ==========
print("\n" + "="*60)
print("FEATURE IMPORTANCE (XGBoost)")
print("="*60)

feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': xgb_model.feature_importances_
}).sort_values('importance', ascending=False)

print("\nTop 10 most important features:")
for idx, row in feature_importance.head(10).iterrows():
    print(f"  {row['feature']:<20} {row['importance']:.4f}")

# ========== SAVE MODELS ==========
import pickle

with open('ensemble_models.pkl', 'wb') as f:
    pickle.dump({
        'rf_model': rf_model,
        'xgb_model': xgb_model,
        'scaler': scaler,
        'feature_cols': feature_cols
    }, f)

print(f"\nModels saved to: ensemble_models.pkl")

print(f"\n=== SESSION 2 COMPLETE ===")
print(f"Ensemble ready for backtesting on multiple stocks")