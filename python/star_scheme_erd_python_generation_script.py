# =============================================================================
# AirLight Pro IoT Governance System
# ERD Generator — draws the star schema as a PNG using matplotlib
# Author: Alantz Innocent
# =============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.lines as mlines

fig, ax = plt.subplots(1, 1, figsize=(18, 12))
ax.set_xlim(0, 18)
ax.set_ylim(0, 12)
ax.axis('off')
fig.patch.set_facecolor('#0a0a0a')
ax.set_facecolor('#0a0a0a')

# Colors
FACT_HEADER  = '#C9A84C'  # gold
DIM_HEADER   = '#2c2c2c'  # dark gray
FACT_BODY    = '#1a1a1a'
DIM_BODY     = '#1a1a1a'
TEXT_GOLD    = '#C9A84C'
TEXT_WHITE   = '#FFFFFF'
TEXT_GRAY    = '#aaaaaa'
LINE_COLOR   = '#C9A84C'
PK_COLOR     = '#C9A84C'
FK_COLOR     = '#7a9fc4'

def draw_table(ax, x, y, width, title, fields, is_fact=False):
    row_h = 0.32
    header_h = 0.45
    total_h = header_h + len(fields) * row_h

    # Header
    header_color = FACT_HEADER if is_fact else '#3a3a3a'
    header_rect = FancyBboxPatch((x, y - header_h), width, header_h,
                                  boxstyle="square,pad=0", linewidth=1.5,
                                  edgecolor=FACT_HEADER if is_fact else '#555555',
                                  facecolor=header_color)
    ax.add_patch(header_rect)
    ax.text(x + width/2, y - header_h/2, title,
            ha='center', va='center', fontsize=9, fontweight='bold',
            color='#0a0a0a' if is_fact else TEXT_GOLD,
            fontfamily='monospace')

    # Body
    for i, (field_name, field_type, field_tag) in enumerate(fields):
        row_y = y - header_h - (i+1)*row_h
        row_color = '#111111' if i % 2 == 0 else '#161616'
        row_rect = FancyBboxPatch((x, row_y), width, row_h,
                                   boxstyle="square,pad=0", linewidth=0.5,
                                   edgecolor='#333333', facecolor=row_color)
        ax.add_patch(row_rect)

        # Tag (PK/FK)
        tag_color = PK_COLOR if field_tag == 'PK' else (FK_COLOR if field_tag == 'FK' else '#444444')
        if field_tag:
            ax.text(x + 0.12, row_y + row_h/2, field_tag,
                    ha='left', va='center', fontsize=5.5, fontweight='bold',
                    color=tag_color, fontfamily='monospace')

        ax.text(x + 0.55, row_y + row_h/2, field_name,
                ha='left', va='center', fontsize=7,
                color=TEXT_WHITE if field_tag in ('PK','FK') else TEXT_GRAY,
                fontfamily='monospace')

        ax.text(x + width - 0.1, row_y + row_h/2, field_type,
                ha='right', va='center', fontsize=6,
                color='#666666', fontfamily='monospace')

    # Outer border
    outer = FancyBboxPatch((x, y - total_h), width, total_h,
                            boxstyle="square,pad=0", linewidth=1.5,
                            edgecolor=FACT_HEADER if is_fact else '#555555',
                            facecolor='none')
    ax.add_patch(outer)

    return x, y, width, total_h


# =============================================================================
# TABLE DEFINITIONS
# =============================================================================

# FACT TABLE — center
draw_table(ax, 6.2, 9.5, 5.6, 'fact_device_telemetry', [
    ('telemetry_key',       'BIGSERIAL', 'PK'),
    ('date_key',            'INT',       'FK'),
    ('device_key',          'INT',       'FK'),
    ('store_key',           'INT',       'FK'),
    ('alert_type_key',      'INT',       'FK'),
    ('event_timestamp',     'TIMESTAMP', ''),
    ('temperature_celsius', 'NUMERIC',   ''),
    ('is_thermal_spike',    'BOOLEAN',   ''),
    ('session_duration_secs','INT',      ''),
    ('power_draw_watts',    'NUMERIC',   ''),
    ('data_quality_flag',   'VARCHAR',   ''),
    ('is_anomaly',          'BOOLEAN',   ''),
    ('gdpr_compliant',      'BOOLEAN',   ''),
], is_fact=True)

# dim_date — top left
draw_table(ax, 0.4, 11.5, 4.2, 'dim_date', [
    ('date_key',    'INT',      'PK'),
    ('full_date',   'DATE',     ''),
    ('month_name',  'VARCHAR',  ''),
    ('quarter',     'SMALLINT', ''),
    ('year',        'SMALLINT', ''),
    ('fiscal_period','VARCHAR', ''),
    ('is_weekend',  'BOOLEAN',  ''),
], is_fact=False)

# dim_store — top right
draw_table(ax, 13.4, 11.5, 4.2, 'dim_store', [
    ('store_key',   'SERIAL',  'PK'),
    ('store_id',    'VARCHAR', ''),
    ('store_name',  'VARCHAR', ''),
    ('city',        'VARCHAR', ''),
    ('country',     'VARCHAR', ''),
    ('region',      'VARCHAR', ''),
    ('store_tier',  'VARCHAR', ''),
    ('is_active',   'BOOLEAN', ''),
], is_fact=False)

# dim_device — bottom left
draw_table(ax, 0.4, 5.8, 4.2, 'dim_device', [
    ('device_key',       'SERIAL',  'PK'),
    ('device_id',        'VARCHAR', ''),
    ('store_key',        'INT',     'FK'),
    ('model_version',    'VARCHAR', ''),
    ('firmware_version', 'VARCHAR', ''),
    ('install_date',     'DATE',    ''),
    ('gdpr_masked',      'BOOLEAN', ''),
], is_fact=False)

# dim_alert_type — bottom right
draw_table(ax, 13.4, 5.8, 4.2, 'dim_alert_type', [
    ('alert_type_key',   'SERIAL',   'PK'),
    ('alert_code',       'VARCHAR',  ''),
    ('alert_category',   'VARCHAR',  ''),
    ('severity',         'VARCHAR',  ''),
    ('auto_shutoff',     'BOOLEAN',  ''),
    ('notifies_regional','BOOLEAN',  ''),
    ('sla_response_mins','SMALLINT', ''),
], is_fact=False)

# =============================================================================
# RELATIONSHIP LINES
# =============================================================================

line_props = dict(color=LINE_COLOR, linewidth=1.2, linestyle='--', alpha=0.7,
                  transform=ax.transData)

# dim_date → fact (date_key)
ax.annotate('', xy=(6.2, 8.22), xytext=(4.6, 9.1),
            arrowprops=dict(arrowstyle='->', color=LINE_COLOR, lw=1.2))

# dim_store → fact (store_key)
ax.annotate('', xy=(11.8, 8.22), xytext=(13.4, 9.1),
            arrowprops=dict(arrowstyle='->', color=LINE_COLOR, lw=1.2))

# dim_device → fact (device_key)
ax.annotate('', xy=(6.2, 7.58), xytext=(4.6, 4.64),
            arrowprops=dict(arrowstyle='->', color=LINE_COLOR, lw=1.2))

# dim_alert_type → fact (alert_type_key)
ax.annotate('', xy=(11.8, 7.9), xytext=(13.4, 4.64),
            arrowprops=dict(arrowstyle='->', color=LINE_COLOR, lw=1.2))

# =============================================================================
# TITLE & LEGEND
# =============================================================================

ax.text(9, 11.75, 'AirLight Pro IoT Governance System — Star Schema ERD',
        ha='center', va='center', fontsize=13, fontweight='bold',
        color=TEXT_GOLD, fontfamily='monospace')

ax.text(9, 11.4, 'L\'Oréal AirLight Pro  |  PostgreSQL 16  |  Schema: airlight',
        ha='center', va='center', fontsize=8,
        color=TEXT_GRAY, fontfamily='monospace')

# Legend
pk_patch = mpatches.Patch(color=PK_COLOR, label='PK — Primary Key')
fk_patch = mpatches.Patch(color=FK_COLOR, label='FK — Foreign Key')
fact_patch = mpatches.Patch(color=FACT_HEADER, label='Fact Table')
dim_patch = mpatches.Patch(color='#3a3a3a', label='Dimension Table')
ax.legend(handles=[pk_patch, fk_patch, fact_patch, dim_patch],
          loc='lower center', ncol=4, fontsize=7,
          facecolor='#1a1a1a', edgecolor='#555555',
          labelcolor=TEXT_WHITE, bbox_to_anchor=(0.5, 0.01))

plt.tight_layout()
output_path = 'C:/Users/ainno/airlight-pro-iot-governance/docs/ERD.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight',
            facecolor='#0a0a0a', edgecolor='none')
print(f"ERD saved to {output_path}")
plt.show()