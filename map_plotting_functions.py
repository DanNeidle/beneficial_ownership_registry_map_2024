import pycountry
import os
import geopandas as gpd
import folium

SHAPEFILE = 'ne_10m_admin_0_map_units'
SHAPEFILE_ISO_KEY = "ADM0_A3"
SHAPEFILE_NAME_KEY = "NAME"
SHAPEFILE_SOVEREIGN_KEY = "SOVEREIGNT"  # set as None if there isn't one

SHAPEFILE_RESOLUTION_BY_COUNTRY_SIZE = {
    1000: 0.001,  # Minimal simplification for very small countries/islands
    10000: 0.005, # Slight simplification for small countries
    100000: 0.05, # Moderate simplification for medium-sized countries
    float('inf'): 0.1  # Higher simplification for large countries (default)
}


# Path to the shapefile (ensure all associated files are present)
SHAPEFILE_PATH = f'{SHAPEFILE}/{SHAPEFILE}.shp'




def get_iso_code(country_name):
    try:
        country = pycountry.countries.lookup(country_name)
        return country.alpha_3
    except LookupError:
        # Attempt to handle common discrepancies manually
        manual_mappings = {
            "Russia": "RUS",
            "Bolivia": "BOL",
            "Vietnam": "VNM",
            "Tanzania": "TZA",
            "Moldova": "MDA",
            "Syria": "SYR",
            "Laos": "LAO",
            "Venezuela": "VEN",
            "Iran": "IRN",
            "Egypt": "EGY",
            "Bahamas, The": "BHS",
            "Congo, Dem. Rep.": "COD",
            "Congo, Rep.": "COG",
            "Egypt, Arab Rep.": "EGY",
            "French Guiana": "FRA",            # Mapped to France
            "Gambia, The": "GMB",
            "Guadeloupe": "FRA",               # Mapped to France
            "Hong Kong Sar": "HKG",
            "Iran, Islamic Rep.": "IRN",
            "Korea, Rep.": "KOR",
            "Kosovo": "XKX",                    # Not in standard shapefiles
            "Lao Pdr": "LAO",
            "Macedonia, Fyr": "MKD",
            "Martinique": "FRA",                # Mapped to France
            "Mayotte": "FRA",                   # Mapped to France
            "Micronesia, Fed. Sts.": "FSM",
            "Réunion": "FRA",                   # Mapped to France
            "South Sudan": "SSD",
            "St. Kitts and Nevis": "KNA",
            "St. Lucia": "LCA",
            "St. Vincent and the Grenadines": "VCT",
            "Swaziland": "SWZ",
            "São Tomé and Príncipe": "STP",
            "Turkey": "TUR",
            "Venezuela, Rb": "VEN",
            "West Bank and Gaza": "PSE",
            "Yemen, Rep.": "YEM",
            # Add more mappings as needed
        }
        iso_code = manual_mappings.get(country_name, None)
        if iso_code:
            pass
            # print(f"Manual mapping applied for '{country_name}': {iso_code}")
        else:
            pass
            # print(f"Warning: No ISO code found for '{country_name}'. It will be reported as missing.")
        return iso_code



def assign_tolerance(area_km2):
    """
    Assign simplification tolerance based on the country's area.
    
    Parameters:
    - area_km2 (float): Area of the country in square kilometers.
    
    Returns:
    - float: Tolerance value for simplification.
    """
    for threshold, tolerance in SHAPEFILE_RESOLUTION_BY_COUNTRY_SIZE.items():
        if area_km2 < threshold:
            return tolerance
        
        
def create_world():
    
    if not os.path.exists(SHAPEFILE_PATH):
        raise Exception(f"Shapefile not found at {SHAPEFILE_PATH}. Please check the path.")

    world = gpd.read_file(SHAPEFILE_PATH)
    
    # Debugging: Print available columns
    # print(f"Available shapefile columns: {world.columns.tolist()}")

    # Ensure ISO codes are uppercase and stripped of whitespace
    world[SHAPEFILE_ISO_KEY] = world[SHAPEFILE_ISO_KEY].str.strip().str.upper()
    
    
    # Simplify geometries to reduce file size
    # The tolerance value might need adjustment based on desired simplification level
    # world['geometry'] = world['geometry'].simplify(tolerance=SHAPEFILE_TOLERANCE, preserve_topology=True)
    
    # Reproject a copy of the GeoDataFrame to Equal Earth for accurate area calculations
    world_proj = world.to_crs(epsg=8857)

    # Calculate area in square kilometers
    world_proj['area_km2'] = world_proj['geometry'].area / 1e6  # from m² to km²

    # Assign tolerance based on area
    world_proj['tolerance'] = world_proj['area_km2'].apply(assign_tolerance)

    # Merge tolerance back to the main GeoDataFrame
    world['tolerance'] = world_proj['tolerance']

    # Simplify geometries with variable tolerance
    world['geometry'] = world.apply(
        lambda row: row['geometry'].simplify(tolerance=row['tolerance'], preserve_topology=True),
        axis=1
    )
    
    return world

def verify_country_merge(data_df, world_gdf, data_iso_column, shapefile_iso_column=SHAPEFILE_ISO_KEY, data_country_column='Country'):
    """
    Verify that all countries in the data have been successfully merged into the shapefile data.
    If any countries are missing, print an error listing them.
    
    Parameters:
    - data_df (pd.DataFrame): The data frame containing country data.
    - world_gdf (gpd.GeoDataFrame): The GeoDataFrame containing shapefile data.
    - data_iso_column (str): The column name in data_df that contains ISO codes.
    - shapefile_iso_column (str): The column name in world_gdf that contains ISO codes. Defaults to SHAPEFILE_ISO_KEY.
    - data_country_column (str): The column name in data_df that contains country names. Defaults to 'Country'.
    """
    # Countries with missing ISO codes
    missing_iso = data_df[data_iso_column].isnull()
    missing_iso_countries = data_df.loc[missing_iso, data_country_column].unique()

    # Countries with ISO codes not present in shapefile
    data_iso_codes = set(data_df[data_iso_column].dropna().str.upper())
    shapefile_iso_codes = set(world_gdf[shapefile_iso_column].dropna().str.upper())

    missing_iso_codes = data_iso_codes - shapefile_iso_codes
    if not missing_iso_codes:
        missing_iso_codes_countries = []
    else:
        missing_iso_codes_countries = data_df[data_iso_column].str.upper().isin(missing_iso_codes)
        missing_iso_countries_from_codes = data_df.loc[missing_iso_codes_countries, data_country_column].unique()
        missing_iso_codes_countries = missing_iso_countries_from_codes.tolist()

    # Combine both missing lists
    total_missing = list(missing_iso_countries) + missing_iso_codes_countries

    if total_missing:
        missing_sorted = sorted(total_missing)
        error_message = (
            "The following countries could not be merged into the shapefile:\n" +
            "\n".join(missing_sorted)
        )
        print(error_message)


def add_html_elements(m, title, legend, width=200, height=120):
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
    title_html = f'''
        <h3 align="center" style="font-size:30px"><b>{title}</b></h3>
    '''
    legend_html = f'''
         <div style="position: fixed; 
         bottom: 50px; left: 50px; width: {width}px; height: {height}px; 
         background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
         padding: 10px;">
         {legend}
         </div>
    '''
    
    
    logo_html = """
<style>
    
    #custom-logo {
        position: fixed;
        bottom: 10px;
        right: 10px; /* Changed from left to right */
        width: 7.5%; /* Increased size by 50% from 5% to 7.5% */
        z-index: 9999;
    }
    #custom-logo img {
        width: 100%;    /* Ensures the image fills the div's width */
        height: auto;   /* Maintains the image's aspect ratio */
    }
</style>
<!-- Conditional Logo: Visible only when not in an iframe -->
    <div id="custom-logo" style="display: none;">
    <a href="https://taxpolicy.org.uk/" target="_blank">
        <img src="https://taxpolicy.org.uk/wp-content/uploads/2022/04/logo_standard.jpg.webp" alt="Tax Policy Associates Ltd logo">
    </a>
</div>
<script>
    // Function to check if the page is in an iframe
    function isInIframe() {
        try {
            return window.self !== window.top;
        } catch (e) {
            return true;
        }
    }

    // If not in an iframe, display the logo
    if (!isInIframe()) {
        document.getElementById('custom-logo').style.display = 'block';
    }
</script>


"""
    
    for element in [responsive_html, additional_css, title_html, legend_html, logo_html]:
        m.get_root().html.add_child(folium.Element(element))
    return m
