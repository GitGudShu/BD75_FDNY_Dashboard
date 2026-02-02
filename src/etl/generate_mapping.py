
import pandas as pd
import os
import sys

def main():
    """
    Generate a Zipcode to Borough mapping CSV.
    
    Reads EMS.csv, normalizes borough names, and resolves one-to-many mappings
    by assigning each Zipcode to its most frequent Borough.
    Saves the result to data/processed/zip_borough_mapping.csv.
    """
    print("Generating Zip-Borough Mapping...")
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    data_raw_path = os.path.join(project_root, 'data', 'raw', 'EMS.csv')
    output_path = os.path.join(project_root, 'data', 'processed', 'zip_borough_mapping.csv')
    
    if not os.path.exists(data_raw_path):
        print(f"Error: {data_raw_path} not found.")
        return

    print("Loading EMS data...")
    try:
        df = pd.read_csv(data_raw_path, usecols=['ZIPCODE', 'BOROUGH'])
    except ValueError:
        print("Standard columns not found, checking header...")
        df_head = pd.read_csv(data_raw_path, nrows=1)
        print("Columns:", df_head.columns.tolist())
        return

    print("Normalizing...")
    df = df.dropna()
    df['ZIPCODE'] = pd.to_numeric(df['ZIPCODE'], errors='coerce').dropna().astype(int)
    df['BOROUGH'] = df['BOROUGH'].astype(str).str.strip().str.upper()
    
    df['BOROUGH'] = df['BOROUGH'].replace({
        "RICHMOND / STATEN ISLAND": "STATEN ISLAND",
        "RICHMOND": "STATEN ISLAND", 
        "STATEN ISLAND": "STATEN ISLAND"
    })

    mapping = df.drop_duplicates().sort_values('ZIPCODE')
    
    print("Resolving one-to-many mappings...")
    distinct_counts = df.groupby(['ZIPCODE', 'BOROUGH']).size().reset_index(name='count')
    distinct_counts = distinct_counts.sort_values(['ZIPCODE', 'count'], ascending=[True, False])
    
    final_mapping = distinct_counts.drop_duplicates(subset=['ZIPCODE'], keep='first')[['ZIPCODE', 'BOROUGH']]
    
    print(f"Found {len(final_mapping)} unique Zipcodes.")
    
    final_mapping.to_csv(output_path, index=False)
    print(f"Saved mapping to {output_path}")

if __name__ == "__main__":
    main()
