import requests
from bs4 import BeautifulSoup
import pycountry
import geopandas as gpd
import folium
from folium.features import GeoJsonTooltip, GeoJsonPopup
import pandas as pd
import matplotlib

# Constants
URL = 'http://registries.opencorporates.com/'
OUTPUT_MAP = 'interactive_corporate_openness_map_scraped_2024.html'
SHAPEFILE = 'world-administrative-boundaries'

# download the world administrative boundaries shapefile from https://public.opendatasoft.com/explore/dataset/world-administrative-boundaries/export/


def get_iso_code(country_name):
    """Retrieve the 3-letter ISO code for a given country name."""
    try:
        return pycountry.countries.lookup(country_name).alpha_3
    except LookupError:
        return None


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
        openness_score = int(row.find('td', class_='score').get_text(strip=True).split('/')[0])
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
    """Convert country data into a pandas DataFrame and display it."""
    df = pd.DataFrame(country_data)
    # print(df.to_string(index=False, justify='left', col_space=15))
    return df


def assign_colors(df):
    """Assign colors to countries based on their openness scores."""
    norm = matplotlib.colors.Normalize(vmin=0, vmax=100)
    cmap = matplotlib.cm.get_cmap('Blues')

    df['color'] = df['Openness Score'].apply(lambda score: matplotlib.colors.rgb2hex(cmap(norm(score))))
    return df


def prepare_geodataframe(df, shapefile_path):
    """Merge the country data with the world shapefile GeoDataFrame."""
    world = gpd.read_file(shapefile_path)
    
    # debug check keys
    # print(world.keys())
    # exit()
    
    
    # Ensure ISO codes are uppercase and stripped of whitespace
    world['iso3'] = world['iso3'].str.strip().str.upper()
    df['ISO Code'] = df['ISO Code'].str.strip().str.upper()
    
    # Debugging prints
    # print("Unique ISO Codes in Shapefile:", world['iso3'].unique())
    # print("Unique ISO Codes in DataFrame:", df['ISO Code'].unique())
    
    world = world.merge(df, left_on='iso3', right_on='ISO Code', how='left')
   
    world['color'] = world['color'].fillna('#ffffff')
    world['Country'] = world['Country'].fillna(world['name'])
    world['Openness Score'] = world['Openness Score'].fillna(0).astype(int)
    world['URL'] = world['URL'].apply(
        lambda x: f'<a href="{x}" target="_blank">Click through to details</a>' if pd.notna(x) else 'No link'
    )

    


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
        fields=['Country', 'Openness Score'],
        aliases=['Country:', 'Openness score:'],
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
        fields=['URL'],
        labels=False,
        localize=True,
        parse_html=True
    )

    folium.GeoJson(
        world_gdf,
        style_function=style_function,
        tooltip=tooltip,
        popup=popup
    ).add_to(m)

    # Add HTML elements
    m.get_root().html.add_child(folium.Element("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        html, body { width: 100%; height: 100%; margin: 0; padding: 0; }
        #map { position: absolute; top: 0; bottom: 0; right: 0; left: 0; }
        .folium-tooltip { font-family: Arial, Helvetica, sans-serif; font-size: 14px; }
    </style>
    <h3 align="center" style="font-size:30px"><b>Openness of company registries, by country</b></h3>
    <div style="position: fixed; bottom: 50px; left: 50px; width: 200px; height: 175px; 
                background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
                padding: 10px;">
        &nbsp; <b style="margin-bottom: 10px; display: inline-block;">Openness scores:</b> <br>
        &nbsp; <i style="background-color:#08306B;width:20px;height:20px;display:inline-block"></i>&nbsp; 100 <br>
        &nbsp; <i style="background-color:#2171B5;width:20px;height:20px;display:inline-block"></i>&nbsp; 75 <br>
        &nbsp; <i style="background-color:#6BAED6;width:20px;height:20px;display:inline-block"></i>&nbsp; 50 <br>
        &nbsp; <i style="background-color:#BDD7E7;width:20px;height:20px;display:inline-block"></i>&nbsp; 25 <br>
        &nbsp; <i style="background-color:#FFFFFF;width:20px;height:20px;display:inline-block;border:1px solid grey"></i>&nbsp; 0 <br>
    </div>
    """))

    return m


def main():
    # Fetch and process data
    country_data = fetch_country_data(URL)
    if not country_data:
        return

    df = create_dataframe(country_data)
    df = assign_colors(df)
    world_gdf = prepare_geodataframe(df, f'{SHAPEFILE}/{SHAPEFILE}.shp')

    # Create and save the map
    folium_map = create_map(world_gdf)
    folium_map.save(OUTPUT_MAP)
    print(f"Map has been saved to {OUTPUT_MAP}")


if __name__ == "__main__":
    main()
