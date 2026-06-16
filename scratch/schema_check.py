import ee
try:
    ee.Initialize()
    villages = ee.FeatureCollection('projects/agrivision-38cc2/assets/punjab_machinery_ch4_shapefile')
    print("=== ASSET SCHEMA CHECK ===")
    print("Feature Count:", villages.size().getInfo())
    print("\nFirst Feature Properties:")
    properties = villages.first().getInfo()['properties']
    for k, v in properties.items():
        print(f"  {k}: {v}")
except Exception as e:
    print("Error:", e)
