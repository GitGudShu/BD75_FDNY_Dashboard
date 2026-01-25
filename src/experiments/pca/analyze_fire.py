
import os
import sys
import pandas as pd
import numpy as np

# Add project root to path to allow importing src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.pca.pca_analysis import PCAAnalyzer

def main():
    print("Starting Fire Data PCA Analysis...")
    
    # Paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
    data_path = os.path.join(project_root, 'data', 'processed', 'pca_matrix_fire_efficiency.csv')
    output_dir = os.path.join(project_root, 'output', 'pca_results', 'fire')
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    analyzer = PCAAnalyzer(data_path, output_dir)
    analyzer.load_data()
    
    # Select columns
    cols_to_use = ['Dispatch_Time_Sec', 'Travel_Time_Sec', 'Engines', 'Ladders', 'Other_Units']
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
    analyzer.plot_scree(title_prefix="Fire Efficiency")
    
    # Determine relevant planes (cumulative variance >= 60%)
    # We will loop through pairs (0,1), (0,2)... until we find interesting ones? 
    # Usually PC1-PC2 is the main one.
    # User said: "combination of axes that have a cumulative eigen of at least 60%ish or more explainability"
    # Actually, PC1+PC2 usually sums to X%. If X < 60%, maybe PC1+PC3? 
    # Usually we plot PC1 vs PC2, and maybe PC1 vs PC3 if PC2 is weak?
    
    # Let's plot PC1 vs PC2 always.
    print("\nGenerating Plots...")
    analyzer.plot_correlation_circle(0, 1, title_prefix="Fire Efficiency")
    analyzer.plot_individuals(0, 1, title_prefix="Fire Efficiency")
    
    # Check if we need more dimensions to hit 60%
    if analyzer.cumulative_variance[1] < 0.60:
        print("First two components explain less than 60%. Checking further...")
        # Maybe PC1 vs PC3?
        analyzer.plot_correlation_circle(0, 2, title_prefix="Fire Efficiency")
        analyzer.plot_individuals(0, 2, title_prefix="Fire Efficiency")
        
    print("Fire Analysis Complete. Results in:", output_dir)

if __name__ == "__main__":
    main()
