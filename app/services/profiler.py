import os
import json
import pandas as pd

# Configurable constants
PLACEHOLDERS = {
    "-- Unbranded --", "-- No Unilog Brand --", "-- No DIB Brand --",
    "-", "N/A", "NA", "NULL", "null", "None", "", " "
}

HIGH_MISSING_THRESHOLD = 0.90
HIGH_CARDINALITY_THRESHOLD = 0.95

def profile_csv(file_path: str) -> tuple[dict, str]:
  
    try:
        # Pandas reads the CSV into a DataFrame
        df = pd.read_csv(file_path)
    except Exception as e:
        raise ValueError(f"Failed to read CSV. Ensure it is properly formatted. Error: {str(e)}")

    if df.empty:
        raise ValueError("The uploaded CSV is completely empty.")

    rows, cols = df.shape
    columns = df.columns.tolist()

    # 13. Final Profile Structure
    profile = {
        "profile_version": "1.0",
        "dataset": {
            "rows": int(rows),
            "column_count": int(cols),
            "columns": columns,
            "duplicate_rows": int(df.duplicated().sum())
        },
        "columns": {},
        "missing": {},
        "unique": {},
        "placeholders": {},
        "text_statistics": {},
        "top_values": {},
        "suspicious_columns": []
    }

    # Iterate dynamically - no hardcoded column names!
    for col in columns:
        col_data = df[col]
        
        # 5. Missing Value Analysis
        missing_count = int(col_data.isna().sum())
        non_missing = int(col_data.notna().sum())
        missing_pct = float(missing_count / rows) if rows > 0 else 0.0
        
        profile["missing"][col] = {
            "count": missing_count,
            "percentage": missing_pct,
            "non_missing": non_missing
        }
        
        # 6. Unique Value Analysis
        unique_count = int(col_data.nunique(dropna=True))
        unique_ratio = float(unique_count / non_missing) if non_missing > 0 else 0.0
        
        profile["unique"][col] = {
            "count": unique_count,
            "ratio": unique_ratio
        }

        # 12. Column Summary
        profile["columns"][col] = {
            "dtype": str(col_data.dtype),
            "non_null": non_missing,
            "missing": missing_count,
            "unique": unique_count,
            "uniqueness_ratio": unique_ratio
        }

        # 8. Placeholder Detection
        # Drop NaNs, convert to string, strip whitespace
        str_data = col_data.dropna().astype(str).str.strip()
        placeholder_counts = str_data[str_data.isin(PLACEHOLDERS)].value_counts().to_dict()
        if placeholder_counts:
            profile["placeholders"][col] = {k: int(v) for k, v in placeholder_counts.items()}

        # 10. Top Value Distribution
        # Only calculate if there's data, and it's not a primary key (high cardinality)
        if unique_count > 0 and unique_ratio < HIGH_CARDINALITY_THRESHOLD:
            top = col_data.value_counts().head(10)
            profile["top_values"][col] = [{"value": str(k), "count": int(v)} for k, v in top.items()]

        # 9. Text Statistics
        # Only calculate for string/object columns
        if pd.api.types.is_object_dtype(col_data) or pd.api.types.is_string_dtype(col_data):
            lengths = str_data.str.len()
            if not lengths.empty:
                profile["text_statistics"][col] = {
                    "min_length": int(lengths.min()),
                    "max_length": int(lengths.max()),
                    "average_length": float(lengths.mean()),
                    "median_length": float(lengths.median())
                }

        # 11. Suspicious Column Detection
        reasons = []
        if missing_pct == 1.0:
            reasons.append("100% of values are missing (completely empty)")
        elif missing_pct > HIGH_MISSING_THRESHOLD:
            reasons.append(f"{missing_pct*100:.1f}% of values are missing")
        
        if unique_count == 1 and non_missing > 0:
            reasons.append("Only one unique non-null value")
            
        if unique_ratio > HIGH_CARDINALITY_THRESHOLD and non_missing > 10:
            reasons.append(f"Extremely high cardinality ({unique_ratio*100:.1f}% unique)")
            
        if placeholder_counts:
            total_placeholders = sum(placeholder_counts.values())
            if (total_placeholders / non_missing) > 0.5:
                reasons.append("Over 50% of non-null values are placeholders")

        if reasons:
            profile["suspicious_columns"].append({
                "column": col,
                "reasons": reasons
            })

    reports_dir = os.path.join("data", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    report_path = os.path.join(reports_dir, f"{base_name}_profile.json")
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)

    return profile, report_path