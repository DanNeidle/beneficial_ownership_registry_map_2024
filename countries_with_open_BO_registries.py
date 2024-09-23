import geopandas as gpd
import folium
from folium.features import GeoJsonTooltip, GeoJsonPopup
import pandas as pd
import pycountry
import numpy as np

from map_plotting_functions import SHAPEFILE_ISO_KEY, SHAPEFILE_NAME_KEY, SHAPEFILE_SOVEREIGN_KEY, create_world, verify_country_merge, add_html_elements


# this data comes from https://www.openownership.org/en/map/
DATA_PATH = 'countries_with_open_registries_data.xlsx'

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

def load_data(data_path):
    df = pd.read_excel(data_path)
    df['ISO3'] = df['ISO2'].apply(convert_iso2_to_iso3)

    return df

def prepare_geodataframe(df, world):
    df['color'] = df['Who can access'].apply(get_color)
    world = world.merge(df, left_on=SHAPEFILE_ISO_KEY, right_on='ISO3', how='left')
    
    # Verify that all countries from the data are present in the shapefile
    verify_country_merge(
        data_df=df, 
        world_gdf=world, 
        data_iso_column='ISO3', 
        data_country_column='Country'
    )
    
    
    
    world['color'] = world['color'].fillna(DEFAULT_COLOR)
    world['Country'] = world.get('Country', world[SHAPEFILE_NAME_KEY]).fillna(world[SHAPEFILE_NAME_KEY])
    world['Register launched'] = world['Register launched'].fillna('No register').apply(
        lambda x: str(int(x)) if isinstance(x, (float, int)) and not pd.isna(x) else x
    )
    world['Who can access'] = world['Who can access'].fillna('No register')
    world['Link'] = world['Link'].apply(
        lambda x: f'<a href="{x}" target="_blank">Open Register</a>' if pd.notna(x) else 'No link'
    )
    
    # Handle Sovereign State and include in popup if key exists
    if SHAPEFILE_SOVEREIGN_KEY:
        world['Sovereign state'] = world[SHAPEFILE_SOVEREIGN_KEY]
    else:
        world['Sovereign state'] = None
        
    # Remove unnecessary columns to reduce size
    columns_to_keep = ['Country', 'Register launched', 'Link', 'Sovereign state', 'color', 'geometry', 'Who can access', 'tolerance']
    world = world[columns_to_keep]
        
    return world

def create_map(world):
    m = folium.Map(location=MAP_CENTER, zoom_start=ZOOM_START, tiles=TILES)

    tooltip = GeoJsonTooltip(
        fields=['Country', 'Register launched', 'Who can access', 'Sovereign state'] if SHAPEFILE_SOVEREIGN_KEY else ['Country:', 'Register launched:', 'Access:'],
        aliases=['Country:', 'Register launched:', 'Access:', 'Sovereign state:'] if SHAPEFILE_SOVEREIGN_KEY else ['Country:', 'Register launched:', 'Access:'],
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
        popup=popup,
        highlight_function=lambda x: {'weight': 3, 'color': 'yellow'},
    ).add_to(m)

    title = "Beneficial ownership registers worldwide"
    legend = '''
    &nbsp; <i class="fa fa-circle" style="color:#28a745"></i>&nbsp; Open BO registry (public) <br>
    &nbsp; <i class="fa fa-circle" style="color:#ff7f0e"></i>&nbsp; Closed BO registry <br>
    &nbsp; <i class="fa fa-circle" style="color:#dc3545"></i>&nbsp; No BO registry <br>
    '''

    add_html_elements(m, title, legend, width=220, height=90)
    return m




def main():
    df = load_data(DATA_PATH)
    world = create_world() 
    
    # print(df.to_string(index=False, justify='left', col_space=15))
    
    world_gdf = prepare_geodataframe(df, world)
    folium_map = create_map(world_gdf)
    folium_map.save(OUTPUT_HTML)

if __name__ == "__main__":
    main()



# about to refactor

