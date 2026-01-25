
import pandas as pd
import os
import sys

def main():
    print("Generating Zip-Borough Mapping...")
    
    # Paths
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    data_raw_path = os.path.join(project_root, 'data', 'raw', 'EMS.csv')
    output_path = os.path.join(project_root, 'data', 'processed', 'zip_borough_mapping.csv')
    
    if not os.path.exists(data_raw_path):
        print(f"Error: {data_raw_path} not found.")
        return

    # Load only necessary columns to save memory
    print("Loading EMS data...")
    try:
        df = pd.read_csv(data_raw_path, usecols=['ZIPCODE', 'BOROUGH'])
    except ValueError:
        # Fallback if names are slightly different
        print("Standard columns not found, checking header...")
        df_head = pd.read_csv(data_raw_path, nrows=1)
        print("Columns:", df_head.columns.tolist())
        return

    # Normalize
    print("Normalizing...")
    df = df.dropna()
    df['ZIPCODE'] = pd.to_numeric(df['ZIPCODE'], errors='coerce').dropna().astype(int)
    df['BOROUGH'] = df['BOROUGH'].astype(str).str.strip().str.upper()
    
    # Mapping fix for Staten Island
    df['BOROUGH'] = df['BOROUGH'].replace({
        "RICHMOND / STATEN ISLAND": "STATEN ISLAND",
        "RICHMOND": "STATEN ISLAND", 
        "STATEN ISLAND": "STATEN ISLAND"
    })

    # Drop duplicates
    mapping = df.drop_duplicates().sort_values('ZIPCODE')
    
    # Handle conflicts: If a Zipcode maps to multiple boroughs, keep the one with most occurrences? 
    # For simplicity/speed here, we just drop duplicates. Realistically, some Zips span boroughs.
    # We will just take the first one or keep all and let the user decide?
    # Let's keep unique Zip-Borough pairs. 
    # If a zip is in multiple boroughs, it might be better to just pick the most frequent one to avoid one-to-many issues in PCA coloring.
    
    # Re-loading full dataset to count freq is expensive. 
    # Let's assume unique pairs are fine, but for coloring we need 1 color per zip.
    # We will drop duplicates keeping the first occurrence? No, that's random.
    # Let's clean it properly: Group by Zip, take mode of Borough
    
    print("Resolving one-to-many mappings...")
    # This might be slow on large data, but acceptable.
    distinct_counts = df.groupby(['ZIPCODE', 'BOROUGH']).size().reset_index(name='count')
    distinct_counts = distinct_counts.sort_values(['ZIPCODE', 'count'], ascending=[True, False])
    
    # Keep the borough with highest count for each zip
    final_mapping = distinct_counts.drop_duplicates(subset=['ZIPCODE'], keep='first')[['ZIPCODE', 'BOROUGH']]
    
    print(f"Found {len(final_mapping)} unique Zipcodes.")
    
    # Save
    final_mapping.to_csv(output_path, index=False)
    print(f"Saved mapping to {output_path}")

if __name__ == "__main__":
    main()
