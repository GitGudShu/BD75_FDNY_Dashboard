
import os
import sys
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.pca.pca_analysis import PCAAnalyzer

def main():
    print("Starting Neighborhood PCA Analysis...")
    
    # Paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
    data_path = os.path.join(project_root, 'data', 'processed', 'pca_matrix_neighborhoods.csv')
    output_dir = os.path.join(project_root, 'output', 'pca_results', 'neighborhoods')
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    analyzer = PCAAnalyzer(data_path, output_dir)
    # Load with ZIPCODE as index
    analyzer.load_data(index_col='ZIPCODE')
    
    # Select columns (All numeric except index)
    cols_to_use = ['EMS_Incident_Count', 'EMS_Avg_Response_Time', 'Fire_Incident_Count', 'Fire_Avg_Response_Time']
    print(f"Using columns: {cols_to_use}")
    
    analyzer.preprocess(columns_to_use=cols_to_use)
    analyzer.run_pca()
    
    # Output Eigenvalues and Variance
    print("\n--- Eigenvalues & Variance ---")
    for i, (eig, var, cum) in enumerate(zip(analyzer.eigenvalues, analyzer.explained_variance_ratio, analyzer.cumulative_variance)):
        print(f"PC{i+1}: Eigenvalue={eig:.4f}, Variance={var*100:.2f}%, Cumulative={cum*100:.2f}%")

    # Output Loadings
    print("\n--- Factor Loadings (Correlations) ---")
    loadings = analyzer.pca.components_.T * np.sqrt(analyzer.pca.explained_variance_)
    loadings_df = pd.DataFrame(loadings, index=analyzer.feature_names, columns=[f'PC{i+1}' for i in range(len(analyzer.explained_variance_ratio))])
    print(loadings_df[[f'PC{i+1}' for i in range(min(5, len(analyzer.explained_variance_ratio)))]])
        
    # Plot Scree
    analyzer.plot_scree(title_prefix="Neighborhoods")
    
    # Plots
    print("\nGenerating Plots...")
    analyzer.plot_correlation_circle(0, 1, title_prefix="Neighborhoods")
    
    # For individuals, use the index (ZIPCODE) as labels
    labels = analyzer.raw_df.index.tolist()
    analyzer.plot_individuals(0, 1, title_prefix="Neighborhoods", labels=labels)
    
    # Check if we need more dimensions
    if analyzer.cumulative_variance[1] < 0.60:
        print("First two components explain less than 60%. Checking further...")
        analyzer.plot_correlation_circle(0, 2, title_prefix="Neighborhoods")
        analyzer.plot_individuals(0, 2, title_prefix="Neighborhoods", labels=labels)
        
    print("Neighborhood Analysis Complete. Results in:", output_dir)

if __name__ == "__main__":
    main()
