
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import os

class PCAAnalyzer:
    def __init__(self, data_path, output_dir):
        self.data_path = data_path
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        self.raw_df = None
        self.df_normalized = None
        self.pca = None
        self.pca_data = None
        self.feature_names = None
        
    def load_data(self, index_col=None):
        """Loads data from CSV."""
        self.raw_df = pd.read_csv(self.data_path)
        if index_col and index_col in self.raw_df.columns:
            self.raw_df.set_index(index_col, inplace=True)
            
    def preprocess(self, columns_to_use=None):
        """Selects columns and normalizes data."""
        if columns_to_use:
            # Check if columns exist
            missing_cols = [c for c in columns_to_use if c not in self.raw_df.columns]
            if missing_cols:
                raise ValueError(f"Columns not found: {missing_cols}")
            df_selected = self.raw_df[columns_to_use].copy()
        else:
            df_selected = self.raw_df.select_dtypes(include=[np.number]).copy()
            
        # Handle NaNs
        if df_selected.isnull().values.any():
            print(f"Warning: Missing values found in {self.data_path}. Imputing with mean.")
            df_selected = df_selected.fillna(df_selected.mean())
            
        self.feature_names = df_selected.columns
        
        # Normalize (Centering and Scaling)
        scaler = StandardScaler()
        self.df_normalized = scaler.fit_transform(df_selected)
        return self.df_normalized

    def run_pca(self, n_components=None):
        """Runs PCA."""
        self.pca = PCA(n_components=n_components)
        self.pca_data = self.pca.fit_transform(self.df_normalized)
        
        # Variance explanations
        self.eigenvalues = self.pca.explained_variance_
        self.explained_variance_ratio = self.pca.explained_variance_ratio_
        self.cumulative_variance = np.cumsum(self.explained_variance_ratio)
        
        return self.pca_data

    def plot_scree(self, title_prefix=""):
        """Plots Scree plot with cumulative variance."""
        plt.figure(figsize=(10, 6))
        
        x_range = range(1, len(self.explained_variance_ratio) + 1)
        
        # Bar plot for individual explained variance
        bar = plt.bar(x_range, self.explained_variance_ratio * 100, alpha=0.6, label='Individual Variance')
        
        # Line plot for cumulative variance
        plt.plot(x_range, self.cumulative_variance * 100, marker='o', color='red', linewidth=2, label='Cumulative Variance')
        
        # Annotations
        for i, val in enumerate(self.cumulative_variance):
            plt.text(i + 1, val * 100 + 1, f'{val*100:.1f}%', ha='center', va='bottom', fontsize=9)
            
        plt.xlabel('Principal Components')
        plt.ylabel('Percentage of Variance Explained')
        plt.title(f'{title_prefix} PCA Scree Plot')
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        save_path = os.path.join(self.output_dir, f'{title_prefix.lower().replace(" ", "_")}_scree_plot.png')
        plt.savefig(save_path)
        plt.close()
        return save_path

    def plot_correlation_circle(self, x_comp=0, y_comp=1, title_prefix="", threshold=0.6):
        """Plots Correlation Circle for the specified components.
        
        only plots if cumulative variance of the two components is significant or as requested.
        """
        plt.figure(figsize=(8, 8))
        ax = plt.gca()
        
        # Circle
        circle = plt.Circle((0, 0), 1, color='black', fill=False, linestyle='--')
        ax.add_artist(circle)
        
        # Loadings (Correlation between original variables and PCs)
        # Loadings = Eigenvectors * sqrt(Eigenvalues)
        loadings = self.pca.components_.T * np.sqrt(self.pca.explained_variance_)
        
        x_loading = loadings[:, x_comp]
        y_loading = loadings[:, y_comp]
        
        for i, feature in enumerate(self.feature_names):
            plt.arrow(0, 0, x_loading[i], y_loading[i], head_width=0.03, head_length=0.05, fc='blue', ec='blue', alpha=0.8)
            plt.text(x_loading[i]*1.1, y_loading[i]*1.1, feature, color='black', ha='center', va='center')
            
        plt.axhline(0, color='grey', linestyle='--', linewidth=0.8)
        plt.axvline(0, color='grey', linestyle='--', linewidth=0.8)
        
        plt.xlim(-1.2, 1.2)
        plt.ylim(-1.2, 1.2)
        plt.xlabel(f'PC{x_comp+1} ({self.explained_variance_ratio[x_comp]*100:.1f}%)')
        plt.ylabel(f'PC{y_comp+1} ({self.explained_variance_ratio[y_comp]*100:.1f}%)')
        plt.title(f'{title_prefix} Correlation Circle (PC{x_comp+1} & PC{y_comp+1})')
        plt.grid()
        
        save_path = os.path.join(self.output_dir, f'{title_prefix.lower().replace(" ", "_")}_corr_circle_pc{x_comp+1}_pc{y_comp+1}.png')
        plt.savefig(save_path)
        plt.close()
        return save_path

    def plot_individuals(self, x_comp=0, y_comp=1, title_prefix="", labels=None, groups=None):
        """Plots projection of individuals using distinct colors for groups if provided."""
        plt.figure(figsize=(12, 10))
        
        x_vals = self.pca_data[:, x_comp]
        y_vals = self.pca_data[:, y_comp]
        
        if groups is not None:
            # Create a dataframe for easy plotting with seaborn
            temp_df = pd.DataFrame({
                'x': x_vals,
                'y': y_vals,
                'Group': groups
            })
            sns.scatterplot(data=temp_df, x='x', y='y', hue='Group', alpha=0.7, palette='tab10', s=100)
        else:
            plt.scatter(x_vals, y_vals, alpha=0.6, c='blue')
        
        if labels is not None:
             # Limit labels if too many
             # Logic to label outliers or just a subset could be added here
             # For now, just simplistic labeling if count is low, or avoid if high
             if len(labels) < 100:
                 for i, label in enumerate(labels):
                     plt.text(x_vals[i], y_vals[i], str(label), fontsize=8, alpha=0.7)
             else:
                 # Label extremes (top 5 furthest from origin)
                 # Distances
                 dists = np.sqrt(x_vals**2 + y_vals**2)
                 # Get indices of top 10
                 top_indices = np.argsort(dists)[-10:]
                 for i in top_indices:
                     plt.text(x_vals[i], y_vals[i], str(labels[i]), fontsize=9, fontweight='bold')

        plt.xlabel(f'PC{x_comp+1} ({self.explained_variance_ratio[x_comp]*100:.1f}%)')
        plt.ylabel(f'PC{y_comp+1} ({self.explained_variance_ratio[y_comp]*100:.1f}%)')
        plt.title(f'{title_prefix} Individuals Projection (PC{x_comp+1} & PC{y_comp+1})')
        plt.axhline(0, color='grey', linestyle='--', linewidth=0.8)
        plt.axvline(0, color='grey', linestyle='--', linewidth=0.8)
        plt.grid(True, linestyle='--', alpha=0.6)
        
        # Move legend if exists
        if groups is not None:
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.tight_layout()
        
        save_path = os.path.join(self.output_dir, f'{title_prefix.lower().replace(" ", "_")}_individuals_pc{x_comp+1}_pc{y_comp+1}.png')
        plt.savefig(save_path)
        plt.close()
        return save_path
