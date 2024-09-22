import geopandas as gpd
import folium
from folium.features import GeoJsonTooltip, GeoJsonPopup
import pandas as pd
import pycountry
import numpy as np

# download the world administrative boundaries shapefile from https://public.opendatasoft.com/explore/dataset/world-administrative-boundaries/export/

# Constants
DATA_PATH = 'countries_with_open_registries_data.xlsx'
SHAPEFILE = 'world-administrative-boundaries'
OUTPUT_HTML = 'interactive_beneficial_ownership_map_2024.html'
DEFAULT_COLOR = '#dc3545'  # Red for missing countries
COLOR_MAP = {
    'public': '#28a745',    # Green
    'closed': '#ff7f0e'     # Bluegreen
}
MAP_CENTER = [20, 0]
ZOOM_START = 3
TILES = 'CartoDB positron'

def get_color(access):
    return COLOR_MAP.get('public' if 'public' in str(access).lower() else 'closed', DEFAULT_COLOR)

def convert_iso2_to_iso3(iso2_code):
    if pd.isna(iso2_code):  # Skip if value is NaN
        return np.nan
    
    try:
        country = pycountry.countries.get(alpha_2=iso2_code.upper())
        return country.alpha_3
    except AttributeError:
        raise Exception(f"Country with ISO2 code '{iso2_code}' not found.")

def load_data(data_path, shapefile_path):
    df = pd.read_excel(data_path)
    df['ISO3'] = df['ISO2'].apply(convert_iso2_to_iso3)
   
    world = gpd.read_file(shapefile_path)
    world['iso3'] = world['iso3'].str.strip()
    return df, world

def preprocess_data(df, world):
    df['color'] = df['Who can access'].apply(get_color)
    world = world.merge(df, left_on='iso3', right_on='ISO3', how='left')
    world['color'].fillna(DEFAULT_COLOR, inplace=True)
    world['Country'] = world.get('Country', world['name']).fillna(world['name'])
    world['Register launched'] = world['Register launched'].fillna('No register').apply(
        lambda x: str(int(x)) if isinstance(x, (float, int)) and not pd.isna(x) else x
    )
    world['Who can access'] = world['Who can access'].fillna('No register')
    world['Link'] = world['Link'].apply(
        lambda x: f'<a href="{x}" target="_blank">Open Register</a>' if pd.notna(x) else 'No link'
    )
    return world

def create_map(world):
    m = folium.Map(location=MAP_CENTER, zoom_start=ZOOM_START, tiles=TILES)

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

    popup = GeoJsonPopup(
        fields=['Link'],
        labels=False,
        localize=True,
        parse_html=True
    )

    folium.GeoJson(
        world,
        style_function=lambda feature: {
            'fillColor': feature['properties']['color'],
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.7,
        },
        tooltip=tooltip,
        popup=popup
    ).add_to(m)

    add_html_elements(m)
    return m

def add_html_elements(m):
    responsive_html = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
    additional_css = """
    <style>
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
    title_html = '''
        <h3 align="center" style="font-size:30px"><b>Beneficial ownership registers worldwide</b></h3>
    '''
    legend_html = '''
         <div style="position: fixed; 
         bottom: 50px; left: 50px; width: 200px; height: 120px; 
         background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
         ">&nbsp; <b>Legend</b> <br><br>
         &nbsp; <i class="fa fa-circle" style="color:#28a745"></i>&nbsp; Open registry (public) <br>
         &nbsp; <i class="fa fa-circle" style="color:#ff7f0e"></i>&nbsp; Closed registry <br>
         &nbsp; <i class="fa fa-circle" style="color:#dc3545"></i>&nbsp; No registry <br>
         </div>
    '''
    for element in [responsive_html, additional_css, title_html, legend_html]:
        m.get_root().html.add_child(folium.Element(element))

def main():
    df, world = load_data(DATA_PATH, f'{SHAPEFILE}/{SHAPEFILE}.shp')
    
    # print(df.to_string(index=False, justify='left', col_space=15))
    
    world = preprocess_data(df, world)
    m = create_map(world)
    m.save(OUTPUT_HTML)

if __name__ == "__main__":
    main()
