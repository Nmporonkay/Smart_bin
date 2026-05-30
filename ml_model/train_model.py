"""
train_model.py

Generates synthetic motion event training data with realistic
university lab patterns, trains a Random Forest classifier to
predict busy/quiet periods, evaluates it, and saves the model.
"""

import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
import joblib


# ---------------------------------------------------------------------------
# Training data generation
# ---------------------------------------------------------------------------

def generate_training_data(days: int = 30, seed: int = 42) -> pd.DataFrame:
    """
    Generate synthetic hourly motion event data mimicking a university
    lab room (Kypes Lab, University of Patras).

    Patterns
    --------
    Weekdays
        08:00–10:00  morning rush          base_rate=15
        11:00–14:00  lunch / peak activity base_rate=25
        15:00–17:00  afternoon lectures    base_rate=12
        18:00–20:00  evening activity      base_rate=8
        other hours  low / night           base_rate=1

    Weekends
        all hours                          base_rate=2

    A label of "busy" is assigned when event_count > 10.
    """
    rng  = np.random.default_rng(seed)
    rows = []

    for day in range(days):
        day_of_week = day % 7          # 0=Monday … 6=Sunday
        is_weekend  = 1 if day_of_week >= 5 else 0

        for hour in range(24):

            if is_weekend:
                base_rate = 2

            elif 8 <= hour <= 10:
                base_rate = 15         # morning rush

            elif 11 <= hour <= 14:
                base_rate = 25         # lunch / peak

            elif 15 <= hour <= 17:
                base_rate = 12         # afternoon lectures

            elif 18 <= hour <= 20:
                base_rate = 8          # evening activity

            else:
                base_rate = 1          # night / early morning

            # Add Gaussian noise — std = 30 % of base rate
            noise       = rng.normal(loc=0, scale=base_rate * 0.3)
            event_count = max(0, int(base_rate + noise))

            label = "busy" if event_count > 10 else "quiet"

            rows.append({
                "day_of_week": day_of_week,
                "hour":        hour,
                "is_weekend":  is_weekend,
                "event_count": event_count,
                "label":       label,
            })

    df = pd.DataFrame(rows)
    print(f"[DATA] Generated {len(df)} samples over {days} days")
    print(f"[DATA] Class distribution:\n{df['label'].value_counts().to_string()}\n")
    return df


# ---------------------------------------------------------------------------
# Training and evaluation
# ---------------------------------------------------------------------------

def train_and_save(output_dir: str = "models") -> RandomForestClassifier:
    """
    Train a Random Forest classifier on the synthetic data,
    evaluate it, and save the model to disk.

    Returns
    -------
    The trained classifier.
    """
    os.makedirs(output_dir, exist_ok=True)

    # -----------------------------------------------------------------------
    # 1. Generate data
    # -----------------------------------------------------------------------
    df = generate_training_data(days=30, seed=42)

    X = df[["day_of_week", "hour", "is_weekend"]].values
    y = df["label"].values

    # -----------------------------------------------------------------------
    # 2. Train / test split
    # -----------------------------------------------------------------------
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y           # preserve class balance in both splits
    )
    print(f"[SPLIT] Train: {len(X_train)} samples  |  Test: {len(X_test)} samples\n")

    # -----------------------------------------------------------------------
    # 3. Train Random Forest
    # -----------------------------------------------------------------------
    model = RandomForestClassifier(
        n_estimators=100,      # more trees → more stable predictions
        max_depth=None,        # let trees grow fully
        min_samples_split=2,
        min_samples_leaf=1,
        class_weight="balanced",  # handles any class imbalance automatically
        random_state=42,
        n_jobs=-1              # use all CPU cores
    )

    model.fit(X_train, y_train)
    print("[MODEL] Training complete\n")

    # -----------------------------------------------------------------------
    # 4. Evaluation
    # -----------------------------------------------------------------------
    y_pred = model.predict(X_test)

    print("=" * 55)
    print("CLASSIFICATION REPORT")
    print("=" * 55)
    print(classification_report(y_test, y_pred, target_names=["busy", "quiet"]))

    print("CONFUSION MATRIX")
    print("=" * 55)
    cm     = confusion_matrix(y_test, y_pred, labels=["busy", "quiet"])
    cm_df  = pd.DataFrame(
        cm,
        index=["Actual: busy", "Actual: quiet"],
        columns=["Predicted: busy", "Predicted: quiet"]
    )
    print(cm_df.to_string())
    print()

    # 5-fold cross-validation on the full dataset for a more robust estimate
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
    print(f"CROSS-VALIDATION (5-fold)")
    print("=" * 55)
    print(f"Accuracy per fold : {[round(s, 3) for s in cv_scores]}")
    print(f"Mean accuracy     : {cv_scores.mean():.3f}")
    print(f"Std deviation     : {cv_scores.std():.3f}\n")

    # -----------------------------------------------------------------------
    # 5. Feature importance
    # -----------------------------------------------------------------------
    feature_names      = ["day_of_week", "hour", "is_weekend"]
    importances        = model.feature_importances_
    sorted_idx         = np.argsort(importances)[::-1]

    print("FEATURE IMPORTANCE")
    print("=" * 55)
    for i in sorted_idx:
        bar = "█" * int(importances[i] * 40)
        print(f"  {feature_names[i]:<15} {importances[i]:.3f}  {bar}")
    print()

    # -----------------------------------------------------------------------
    # 6. Save model
    # -----------------------------------------------------------------------
    model_path = os.path.join(output_dir, "busy_predictor.joblib")
    joblib.dump(model, model_path)
    print(f"[SAVE] Model saved to '{model_path}'")

    # -----------------------------------------------------------------------
    # 7. Quick sanity check — predict a few known cases
    # -----------------------------------------------------------------------
    print("\nSANITY CHECK — known cases")
    print("=" * 55)
    test_cases = [
        ([1, 12, 0], "Tuesday 12:00 → expect busy"),
        ([1, 23, 0], "Tuesday 23:00 → expect quiet"),
        ([5,  9, 1], "Saturday 09:00 → expect quiet"),
        ([0,  9, 0], "Monday 09:00 → expect busy"),
        ([4, 13, 0], "Friday 13:00 → expect busy"),
    ]

    for features, description in test_cases:
        arr        = np.array([features])
        pred       = model.predict(arr)[0]
        proba      = model.predict_proba(arr)[0]
        classes    = list(model.classes_)
        confidence = proba[classes.index(pred)]
        print(f"  {description}")
        print(f"    → {pred.upper()} (confidence: {confidence*100:.1f}%)\n")

    return model


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    train_and_save()