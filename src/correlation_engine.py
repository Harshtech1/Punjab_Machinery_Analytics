import pandas as pd
import scipy.stats as stats
from sklearn.linear_model import LinearRegression

def partial_corr(df, x, y, covars):
    data = df[[x, y] + covars].dropna()
    
    # regress x on covars
    mod_x = LinearRegression().fit(data[covars], data[x])
    res_x = data[x] - mod_x.predict(data[covars])
    
    # regress y on covars
    mod_y = LinearRegression().fit(data[covars], data[y])
    res_y = data[y] - mod_y.predict(data[covars])
    
    # pearson
    pearson_r, pearson_p = stats.pearsonr(res_x, res_y)
    # spearman
    spearman_rho, spearman_p = stats.spearmanr(res_x, res_y)
    
    return pearson_r, pearson_p, spearman_rho, spearman_p

def run_correlation(config):
    df = pd.read_csv(config['paths']['merged_output'], low_memory=False)
    
    print("\n========================================")
    print("  CORRELATION ENGINE")
    print("========================================")
    
    ch4_col = config['columns']['ch4_predicted']
    machinery_cols = config['columns']['machinery_cols']
    covars = config['columns'].get('control_variables', [])
    
    print(f"Target: {ch4_col}")
    print(f"Controls: {covars}")
    print("----------------------------------------")
    
    for m_col in machinery_cols:
        print(f"\nCorrelation:\n{ch4_col} vs {m_col}")
        try:
            if covars:
                pr, pp, sr, sp = partial_corr(df, ch4_col, m_col, covars)
                print(f"(Partial controlling for: {', '.join(covars)})")
            else:
                data = df[[ch4_col, m_col]].dropna()
                pr, pp = stats.pearsonr(data[ch4_col], data[m_col])
                sr, sp = stats.spearmanr(data[ch4_col], data[m_col])
                
            print(f"Pearson r = {pr:.4f}")
            print(f"Pearson p-value = {pp:.4e}")
            print(f"Spearman ρ = {sr:.4f}")
            print(f"Spearman p-value = {sp:.4e}")
        except Exception as e:
            print(f"Error calculating correlation: {e}")
