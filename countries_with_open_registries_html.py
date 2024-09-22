import geopandas as gpd
import folium
from folium.features import GeoJsonTooltip
import pandas as pd

# Load the data from the spreadsheet
# data is from https://www.openownership.org/en/map/
data_path = 'countries_with_open_registries_data.xlsx'
df = pd.read_excel(data_path)

# Define a function to check access and set color
def get_color(access):
    if 'public' in str(access).lower():
        return '#28a745'  # Green
    return '#ff7f0e'  # bluegreen

# Load the shapefile for world countries
local_shapefile_path = 'ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp'
world = gpd.read_file(local_shapefile_path)

# Ensure consistent naming
world['ISO_A2'] = world['ISO_A2'].str.strip()

# Create a color column based on access conditions in the spreadsheet
df['color'] = df['Who can access'].apply(get_color)

# Merge the data based on the ISO country codes
world = world.merge(df, left_on='ISO_A2', right_on='ISO2', how='left')

# Change the default color for countries not in the spreadsheet to black
world['color'] = world['color'].fillna('#dc3545')  # red for missing countries


# Fill missing fields with the text 'No register' for the tooltip
world['Country'] = world['Country'].fillna(world['NAME'])  # Use 'NAME' from shapefile if 'Country' is missing
world['Register launched'] = world['Register launched'].fillna('No register').apply(lambda x: str(int(x)) if isinstance(x, (float, int)) and not pd.isna(x) else x)

world['Who can access'] = world['Who can access'].fillna('No register')

# Modify the 'Link' field to contain the actual HTML link
world['Link'] = world['Link'].apply(lambda x: f'<a href="{x}" target="_blank">Open Register</a>' if pd.notna(x) else 'No link')



# Initialize Folium map centered around the equator and prime meridian
m = folium.Map(location=[20, 0], zoom_start=3, tiles='CartoDB positron')

# Function to style each country
def style_function(feature):
    return {
        'fillColor': feature['properties']['color'],
        'color': 'black',
        'weight': 0.5,
        'fillOpacity': 0.7,
    }

# Create tooltips with country name, register, and access info
tooltip = GeoJsonTooltip(
    fields=['Country', 'Register launched', 'Who can access'],
    aliases=['Country:', 'Register launched:', 'Access:'],
    localize=True,
    sticky=True,
    labels=True,
    style="""
        background-color: #F0EFEF;
        border: 1px solid black;
        border-radius: 3px;
        box-shadow: 3px;
    """,
    max_width=800,
)

# Add GeoJson to the map with hover text
geojson = folium.GeoJson(
    world,
    style_function=style_function,
    tooltip=tooltip,
    popup=folium.GeoJsonPopup(
        fields=['Link'],
        labels=False,
        localize=True,
        parse_html=True
    )
)


geojson.add_to(m)

# Add responsive meta tag
responsive_html = """
<meta name="viewport" content="width=device-width, initial-scale=1.0">
"""

m.get_root().html.add_child(folium.Element(responsive_html))

# Additional CSS to make the map responsive and pretty
additional_css = """
<style>
    /* Ensure the map fills the viewport */
    html, body {
        width: 100%;
        height: 100%;
        margin: 0;
        padding: 0;
    }
    #map {
        position: absolute;
        top: 0;
        bottom: 0;
        right: 0;
        left: 0;
    }
    .folium-tooltip {
        font-family: Arial, Helvetica, sans-serif;
        font-size: 14px;
    }
</style>
"""

m.get_root().html.add_child(folium.Element(additional_css))

# Add a title to the map
title_html = '''
    <h3 align="center" style="font-size:30px"><b>Beneficial ownership registers worldwide</b></h3>
    '''
m.get_root().html.add_child(folium.Element(title_html))


# Add a custom legend
legend_html = '''
     <div style="position: fixed; 
     bottom: 50px; left: 50px; width: 200px; height: 120px; 
     background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
     ">&nbsp; <b>Legend</b> <br>
     &nbsp; <i class="fa fa-circle" style="color:#28a745"></i>&nbsp; Open registry (public) <br>
     &nbsp; <i class="fa fa-circle" style="color:#ff7f0e"></i>&nbsp; Closed registry <br>
     &nbsp; <i class="fa fa-circle" style="color:#dc3545"></i>&nbsp; No registry <br>
     </div>
     '''
m.get_root().html.add_child(folium.Element(legend_html))

# Save the map to an HTML file
m.save('interactive_beneficial_ownership_map_2024.html')
