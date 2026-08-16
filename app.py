import streamlit as st
import pandas as pd
import numpy as np
import re

st.set_page_config(page_title="Data Cleaning Pipeline", page_icon="🧹", layout="wide")

def load_data(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            return pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xls', '.xlsx')):
            return pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

def clean_data(df):
    cleaned_df = df.copy()

    str_cols = cleaned_df.select_dtypes(include=['object', 'string']).columns
    for col in str_cols:
        cleaned_df[col] = cleaned_df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

    # FIXED REGEX: Moved (?i) to the very start of the string
    patterns = [
        r"^--.*--$", 
        r"(?i)^(n/a|null|none|-|--|\?\?\?|nan)$"
    ]
    
    for col in str_cols:
        for pattern in patterns:
            cleaned_df[col] = cleaned_df[col].replace(to_replace=pattern, value=np.nan, regex=True)

    cols_to_drop = [col for col in cleaned_df.columns if cleaned_df[col].nunique(dropna=False) <= 1]
    cleaned_df = cleaned_df.drop(columns=cols_to_drop)

    cleaned_df = cleaned_df.drop_duplicates()

    return cleaned_df

def main():
    st.title("🧹 Data Cleaning Pipeline")
    st.markdown("Upload your dirty dataset and run our smart cleaning engine to instantly sanitize, standardize, and optimize your data.")

    uploaded_file = st.file_uploader("Upload a .csv, .xls, or .xlsx file", type=['csv', 'xls', 'xlsx'])

    if uploaded_file is not None:
        st.subheader("Raw Data Summary")
        df_raw = load_data(uploaded_file)
        
        if df_raw is not None:
            st.write(f"**Shape:** {df_raw.shape[0]} rows and {df_raw.shape[1]} columns")
            st.dataframe(df_raw.head())

            if st.button("Run Smart Clean", type="primary"):
                with st.spinner("Cleaning data..."):
                    df_cleaned = clean_data(df_raw)
                
                st.success("✅ Data successfully cleaned!")
                st.subheader("Cleaned Data Summary")
                st.write(f"**New Shape:** {df_cleaned.shape[0]} rows and {df_cleaned.shape[1]} columns")
                st.dataframe(df_cleaned.head())
                
                csv = df_cleaned.to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label="Download Cleaned Data",
                    data=csv,
                    file_name="cleaned_data.csv",
                    mime="text/csv",
                )

if __name__ == "__main__":
    main()