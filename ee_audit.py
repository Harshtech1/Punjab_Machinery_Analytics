import ee
import os

ee.Initialize(project='agrivision-38cc2')

print("Fetching fc_villages...")
fc_villages = ee.FeatureCollection('projects/agrivision-38cc2/assets/punjab_machinery_ch4_shapefile')

# Add Intervention_Priority
def compute_priority(f):
    def get_num(key):
        val = f.get(key)
        return ee.Number(ee.Algorithms.If(val, val, 0))

    ch4 = get_num('Pred_CH4')
    ch4_score = ee.Algorithms.If(ch4.gt(1915), 3, ee.Algorithms.If(ch4.gt(1900), 2, ee.Algorithms.If(ch4.gt(1885), 1, 0)))

    in_situ = get_num('In_Situ')
    ex_situ = get_num('Ex_Situ')
    prime = get_num('Prime_Move')
    gen = get_num('General')
    total_mach = in_situ.add(ex_situ).add(prime).add(gen)
    
    is_matched = ee.Algorithms.If(total_mach.gt(0), 1, 0)

    mach_score = ee.Algorithms.If(ee.Number(is_matched).eq(0), 0, 
                    ee.Algorithms.If(total_mach.lt(5), 2, 
                    ee.Algorithms.If(total_mach.lt(15), 1, 0)))

    pol_score = ee.Algorithms.If(ee.Filter.eq('Policy_Zon', 'Policy Failure Zone'), 3, 0)
    
    priority = ee.Number(ch4_score).add(ee.Number(mach_score)).add(ee.Number(pol_score))
    
    final_priority = ee.Algorithms.If(priority.gt(6), 4,
                        ee.Algorithms.If(priority.gt(4), 3,
                        ee.Algorithms.If(priority.gt(2), 2, 1)))
                        
    return f.set('Intervention_Priority', final_priority)

merged_villages = fc_villages.map(compute_priority)

# Diagnostics
print("Calculating histogram for Policy_Zon...")
policy_hist = merged_villages.aggregate_histogram('Policy_Zon').getInfo()
print("Policy_Zon Histogram:", policy_hist)

print("Calculating stats for Intervention_Priority...")
priority_stats = merged_villages.aggregate_stats('Intervention_Priority').getInfo()
print("Intervention_Priority Stats:", priority_stats)

os.makedirs('outputs/audit', exist_ok=True)
with open('outputs/audit/gee_dashboard_bug_audit.txt', 'w') as f:
    f.write("GEE DASHBOARD BUG AUDIT\n")
    f.write("=======================\n\n")
    f.write("1. Policy_Zon Histogram:\n")
    for k, v in policy_hist.items():
        f.write(f"  {k}: {v}\n")
    
    f.write("\n2. Intervention_Priority Stats:\n")
    for k, v in priority_stats.items():
        f.write(f"  {k}: {v}\n")

print("Done. Saved to outputs/audit/gee_dashboard_bug_audit.txt")
