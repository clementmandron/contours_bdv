import streamlit as st
import geopandas as gpd
from io import BytesIO

# Load GeoParquet file 
@st.cache_data
def load_geoparquet_file(filepath):
    gdf = gpd.read_parquet(filepath)  # Load GeoParquet file
    return gdf

def download_button_for_gdf(get_gdf_callable, filename_prefix):
    gdf = get_gdf_callable()  # Call the function to get the filtered GeoDataFrame
    b = BytesIO()
    gdf.to_file(b, driver='GeoJSON')
    b.seek(0)
    st.download_button(
        label=f"Télécharger {filename_prefix}.geojson",
        data=b.getvalue(),
        file_name=f"{filename_prefix}.geojson",
        mime="application/geo+json",
    )

def main():
    st.title("Contours des bureaux de vote")

    st.markdown("""
                ## Sélectionnez le découpage
                """)
    
    # Path to the pre-existing GeoParquet file
    filepath = "contours-france-entiere-latest-v2.parquet"
    
    gdf = load_geoparquet_file(filepath)

    # Create formatted columns for department, circonscription, and commune
    gdf['nomCodeDepartement'] = gdf['codeDepartement'] + " - " + gdf['nomDepartement']
    gdf['nomCodeCirconscription'] = gdf['nomCirconscription'] + " (" + gdf['nomDepartement'] + ")" 
    gdf['nomCodeCommune'] = gdf['nomCommune'] + " (" + gdf['codeCommune'] + ")"

    # Step 1: Select NomDepartement
    nom_departement = st.selectbox("Sélectionnez un Département", options=[''] + sorted(gdf['nomCodeDepartement'].unique()))
    if nom_departement:
        code_departement = nom_departement.split(" - ")[0]  # Extract codeDepartement from selection
        def get_gdf_departement():
            return gdf[gdf['codeDepartement'] == code_departement]
        download_button_for_gdf(get_gdf_departement, f"departement_{nom_departement}")

        # Create two columns for the select boxes
        col1, col2 = st.columns(2)


        # Column 1: Selecting a specific NomCirconscription
        with col1:
            # Allow selecting and downloading a specific NomCirconscription
            nom_circonscription = st.selectbox("Sélectionnez une circonscription de " + nom_departement, options=[''] + sorted(gdf[gdf['codeDepartement'] == code_departement]['nomCodeCirconscription'].unique()))
            if nom_circonscription:
                def get_gdf_circonscription():
                    nom_seul_circonscription = nom_circonscription.split(" (")[0].rstrip(")")
                    return gdf[(gdf['codeDepartement'] == code_departement) & (gdf['nomCirconscription'] == nom_seul_circonscription)]

                download_button_for_gdf(get_gdf_circonscription, f"circonscription_{nom_circonscription}")

        # Column 2: Selecting a specific NomCommune directly after NomDepartement
        with col2:
            # Allow selecting and downloading a specific NomCommune directly after NomDepartement
            nom_commune = st.selectbox("Sélectionnez une commune de " + nom_departement + " (code INSEE)", options=[''] + sorted(gdf[gdf['codeDepartement'] == code_departement]['nomCodeCommune'].unique()))
            if nom_commune:
                code_commune = nom_commune.split(" (")[1].rstrip(")")  # Extract codeCommune from selection
                # Define a callable for filtering the commune data
                def get_gdf_commune():
                    return gdf[(gdf['codeDepartement'] == code_departement) & (gdf['codeCommune'] == code_commune)]
                download_button_for_gdf(get_gdf_commune, f"commune_{nom_commune}")
         # Using st.markdown for Markdown formatted text
    
    st.markdown("""
    ## Description
    Téléchargez les contours géographiques des bureaux de vote en France au format GeoJSON pour un département, une circonscription ou une commune.
                
    ## Les données
    Les données sont issues de [la proposition de contours des bureaux de vote de data.gouv.fr](https://www.data.gouv.fr/fr/datasets/proposition-de-contours-des-bureaux-de-vote/). 
    Veuillez vous référer à la description du jeu de données pour prendre connaissance des précautions d’usage. Les données ont été téléchargées le 14/06/2024 et ont été transformées au format GeoParquet.
        
    """)

if __name__ == "__main__":
    main()