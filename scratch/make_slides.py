import matplotlib.pyplot as plt

slides = {
    'Slide_01_Methane_Map.png': 'Slide 1: Punjab Methane Map\n(Insert GEE Screenshot Here)',
    'Slide_02_Machinery_Coverage.png': 'Slide 2: Verified Machinery Coverage\n(Insert GEE Screenshot Here)',
    'Slide_03_Scheme_Score.png': 'Slide 3: Scheme Penetration Score\n(Insert GEE Screenshot Here)',
    'Slide_04_Policy_Zones.png': 'Slide 4: Village Policy Zones\n(Insert GEE Screenshot Here)',
    'Slide_05_Priority_Villages.png': 'Slide 5: Top Priority Villages\n(Insert GEE Screenshot Here)',
    'Slide_06_Intervention_Index.png': 'Slide 6: Intervention Priority Index\n(Insert GEE Screenshot Here)',
}

for filename, text in slides.items():
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.text(0.5, 0.5, text, fontsize=24, ha='center', va='center', weight='bold', color='#1a365d')
    ax.set_facecolor('#f8f9fa')
    ax.axis('off')
    plt.savefig(f"presentation/{filename}", bbox_inches='tight', dpi=150)
    plt.close()

# Slide 7 is purely text limitations
fig, ax = plt.subplots(figsize=(10, 6))
text_7 = """
Study Limitations

• Machinery registry linkage available for 3,339 villages.
• Remaining villages shown as Data Not Available.
• Analysis is cross-sectional (2020 snapshot).
• Associations do not imply causation.
• Dashboard supports prioritization, not impact evaluation.
• Multi-year monitoring is recommended.
"""
ax.text(0.5, 0.5, text_7, fontsize=20, ha='center', va='center', color='#2d3748')
ax.set_facecolor('#ffffff')
ax.axis('off')
plt.savefig("presentation/Slide_07_Limitations.png", bbox_inches='tight', dpi=150)
plt.close()
