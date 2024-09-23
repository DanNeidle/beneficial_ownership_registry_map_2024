import requests
from bs4 import BeautifulSoup

import folium
from folium.features import GeoJsonTooltip, GeoJsonPopup
import pandas as pd
import matplotlib
import matplotlib.colors as colors

from map_plotting_functions import SHAPEFILE_ISO_KEY, SHAPEFILE_NAME_KEY, SHAPEFILE_SOVEREIGN_KEY, create_world, get_iso_code, verify_country_merge, add_html_elements

# We scrape the brilliant opencorporate data - please don't abuse this.
URL = 'http://registries.opencorporates.com/'
OUTPUT_MAP = 'interactive_corporate_openness_map_scraped_2024.html'

# download the map unit shapefile from https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-details/


def fetch_country_data(url):
    """Fetch and parse country data from the given URL."""
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to retrieve data. Status code: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    rows = soup.find_all('tr', {'data-href': True})

    country_data = []
    for row in rows:
        country_name = row.find('td', class_='name').get_text(strip=True)
        score_text = row.find('td', class_='score').get_text(strip=True)
        try:
            openness_score = int(score_text.split('/')[0])
        except (ValueError, IndexError):
            openness_score = 0  # Default to 0 if parsing fails
        country_url = f"http://registries.opencorporates.com/{row['data-href']}"
        iso_code = get_iso_code(country_name)

        country_data.append({
            'Country': country_name,
            'Openness Score': openness_score,
            'URL': country_url,
            'ISO Code': iso_code
        })
        
    return country_data



def create_dataframe(country_data):
    """Convert country data into a pandas DataFrame."""
    df = pd.DataFrame(country_data)
    return df



def assign_colors(df):
    # Using PowerNorm to adjust color intensity
    norm = colors.PowerNorm(gamma=0.5, vmin=0, vmax=100)  # Adjust gamma as needed
    
    # Retain the 'Blues' colormap
    cmap = matplotlib.colormaps.get_cmap('Blues')
    
    df['color'] = df['Openness Score'].apply(
        lambda score: matplotlib.colors.rgb2hex(cmap(norm(score)))
    )
    return df


def prepare_geodataframe(world, df):
    
    df['ISO Code'] = df['ISO Code'].str.strip().str.upper()

    # Merge dataframes on ISO code
    world = world.merge(df, left_on=SHAPEFILE_ISO_KEY, right_on='ISO Code', how='left')
    
    verify_country_merge(
        data_df=df, 
        world_gdf=world, 
        data_iso_column='ISO Code', 
        data_country_column='Country'
    )

    # Fill missing values
    world['color'] = world['color'].fillna('#ffffff')
    world['Country'] = world['Country'].fillna(world[SHAPEFILE_NAME_KEY])
    world['Openness Score'] = world['Openness Score'].fillna(0).astype(int)
    
    world['URL'] = world.apply(
        lambda row: f'<a href="{row["URL"]}" target="_blank">Click through to {row["Country"]} register</a>' 
        if pd.notna(row["URL"]) else 'No link',
        axis=1
    )

    # Handle Sovereign State and include in popup if key exists
    if SHAPEFILE_SOVEREIGN_KEY:
        world['Sovereign state'] = world[SHAPEFILE_SOVEREIGN_KEY]
    else:
        world['Sovereign state'] = None

    # Create popup_html field
    world['popup_html'] = world['URL']
    
    # Remove unnecessary columns to reduce size
    columns_to_keep = ['Country', 'Openness Score', 'popup_html', 'Sovereign state', 'color', 'geometry', 'tolerance']
    world = world[columns_to_keep]

    return world

def create_map(world_gdf):
    """Create and customize the interactive Folium map."""
    m = folium.Map(location=[20, 0], zoom_start=3, tiles='CartoDB positron')

    style_function = lambda feature: {
        'fillColor': feature['properties']['color'],
        'color': 'black',
        'weight': 0.5,
        'fillOpacity': 0.7,
    }

    tooltip = GeoJsonTooltip(
        fields=['Country', 'Openness Score', 'Sovereign state'] if SHAPEFILE_SOVEREIGN_KEY else ['Country', 'Openness Score'],
        aliases=['Country:', 'Openness score:', 'Sovereign state:']  if SHAPEFILE_SOVEREIGN_KEY else ['Country:', 'Openness score:'],
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

    # Define the popup using the precomputed 'popup_html' field
    popup = GeoJsonPopup(
        fields=['popup_html'],
        aliases=['Details:'],
        labels=False,
        localize=True,
        parse_html=True
    )

    # Add the GeoJson layer with style, tooltip, and popup
    folium.GeoJson(
        world_gdf,
        style_function=style_function,
        tooltip=tooltip,
        popup=popup,
        highlight_function=lambda x: {'weight': 3, 'color': 'yellow'},
        name="Corporate Openness"
    ).add_to(m)
    
    title = "Openness of Company Registries, by Country"
    legend = '''
    &nbsp; <b>Openness of register</b> <br><br>
    &nbsp; <i style="background-color:#08306B;width:20px;height:20px;display:inline-block;vertical-align:middle"></i>&nbsp; 100 <br>
    &nbsp; <i style="background-color:#2171B5;width:20px;height:20px;display:inline-block;vertical-align:middle"></i>&nbsp; 75 <br>
    &nbsp; <i style="background-color:#6BAED6;width:20px;height:20px;display:inline-block;vertical-align:middle"></i>&nbsp; 50 <br>
    &nbsp; <i style="background-color:#BDD7E7;width:20px;height:20px;display:inline-block;vertical-align:middle"></i>&nbsp; 25 <br>
    &nbsp; <i style="background-color:#FFFFFF;width:20px;height:20px;display:inline-block;border:1px solid grey;vertical-align:middle"></i>&nbsp; 0 <br>
    '''


    add_html_elements(m, title, legend, width=200, height=180)


    return m


def main():
    # Fetch and process data
    country_data = fetch_country_data(URL)
    if not country_data:
        print("No country data fetched. Exiting.")
        return

    df = create_dataframe(country_data)
    df = assign_colors(df)
    
    world = create_world() 
    world_gdf = prepare_geodataframe(world, df)

    if world_gdf is None:
        print("GeoDataFrame preparation failed. Exiting.")
        return

    # Create and save the map
    folium_map = create_map(world_gdf)
    folium_map.save(OUTPUT_MAP)
    print(f"Map has been saved to {OUTPUT_MAP}")


if __name__ == "__main__":
    main()



# now