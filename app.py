import pandas as pd
import streamlit as st
from PIL import Image
import numpy as np
from datetime import datetime

# Page configuration (custom icons, layout)
st.set_page_config(
    page_title="Análisis de Sensores - Mi Ciudad",
    page_icon="📍",
    layout="wide"
)

# Custom CSS (Updated styles for a fresh look)
st.markdown("""
    <style>
    /* Custom page layout */
    .main {
        padding: 2rem;
        background-color: #f4f6f9;
        font-family: 'Arial', sans-serif;
    }
    
    /* Custom title and subtitle styles */
    h1, h2, h3 {
        color: #1e2a47;
        font-weight: bold;
    }
    
    /* Tab bar background */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #2980b9;
    }
    
    /* Tab active state */
    .stTabs [data-baseweb="tab-list"] > div > div[aria-selected="true"] {
        background-color: #f39c12;
        color: white;
    }
    
    /* Tab content background */
    .stTabContent {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Chart styling */
    .streamlit-expanderHeader {
        color: #2980b9;
        font-size: 1.2rem;
    }
    
    .stButton > button {
        background-color: #e67e22;
        color: white;
        border-radius: 10px;
        font-weight: bold;
    }
    
    /* Map display styling */
    .stMap {
        border-radius: 15px;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Footer styling */
    footer {
        color: #777;
        font-size: 0.9rem;
        background-color: #f1f1f1;
        padding: 10px;
        text-align: center;
    }
    
    .stMarkdown, .stDataFrame {
        font-family: 'Arial', sans-serif;
    }
    </style>
""", unsafe_allow_html=True)

# Title and description
st.title('📊 Análisis de Datos de Sensores - Mi Ciudad')
st.markdown("""
    Bienvenido a la plataforma de análisis de datos de sensores urbanos. 
    Explora la información recolectada en diferentes puntos de la ciudad para un mejor entendimiento.
""")

# Custom map section with rounded corners and shadow
st.subheader("📍 Ubicación de los Sensores - Universidad EAFIT")
eafit_location = pd.DataFrame({
    'lat': [6.2006],
    'lon': [-75.5783],
    'location': ['Universidad EAFIT']
})

# Display map with custom style
st.map(eafit_location, zoom=15)

# File uploader with a custom button style
uploaded_file = st.file_uploader('Cargar archivo CSV', type=['csv'])

if uploaded_file is not None:
    try:
        # Load and process data from the CSV
        df1 = pd.read_csv(uploaded_file)
        
        # Renombrar la columna a 'variable'
        if 'Time' in df1.columns:
            other_columns = [col for col in df1.columns if col != 'Time']
            if len(other_columns) > 0:
                df1 = df1.rename(columns={other_columns[0]: 'variable'})
        else:
            df1 = df1.rename(columns={df1.columns[0]: 'variable'})
        
        # Procesar la columna de tiempo si existe
        if 'Time' in df1.columns:
            df1['Time'] = pd.to_datetime(df1['Time'])
            df1 = df1.set_index('Time')

        # Create tabs for different analyses
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Visualización", "📊 Estadísticas", "🔍 Filtros", "🗺 Información del Sitio"])

        with tab1:
            st.subheader('Visualización de Datos')
            
            # Chart type selector with custom colors and style
            chart_type = st.selectbox(
                "Seleccione el tipo de gráfico",
                ["Línea", "Área", "Barra"],
                help="Elija cómo desea visualizar los datos."
            )
            
            # Create plot based on selection
            if chart_type == "Línea":
                st.line_chart(df1["variable"])
            elif chart_type == "Área":
                st.area_chart(df1["variable"])
            else:
                st.bar_chart(df1["variable"])

            # Raw data display with toggle
            if st.checkbox('Mostrar datos crudos'):
                st.write(df1)

        with tab2:
            st.subheader('Análisis Estadístico')
            
            # Statistical summary with bold metrics
            stats_df = df1["variable"].describe()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.dataframe(stats_df)
            
            with col2:
                # Additional statistics
                st.metric("Valor Promedio", f"{stats_df['mean']:.2f}")
                st.metric("Valor Máximo", f"{stats_df['max']:.2f}")
                st.metric("Valor Mínimo", f"{stats_df['min']:.2f}")
                st.metric("Desviación Estándar", f"{stats_df['std']:.2f}")

        with tab3:
            st.subheader('Filtros de Datos')
            
            # Calcular rango de valores
            min_value = float(df1["variable"].min())
            max_value = float(df1["variable"].max())
            mean_value = float(df1["variable"].mean())
            
            # Verificar si hay variación en los datos
            if min_value == max_value:
                st.warning(f"⚠ Todos los valores en el dataset son iguales: {min_value:.2f}")
                st.info("No es posible aplicar filtros cuando no hay variación en los datos.")
                st.dataframe(df1)
            else:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Minimum value filter with custom slider style
                    min_val = st.slider(
                        'Valor mínimo',
                        min_value,
                        max_value,
                        mean_value,
                        key="min_val",
                        help="Ajuste el valor mínimo para filtrar los datos."
                    )
                    
                    filtrado_df_min = df1[df1["variable"] > min_val]
                    st.write(f"Registros con valor superior a {min_val:.2f}:")
                    st.dataframe(filtrado_df_min)
                    
                with col2:
                    # Maximum value filter with custom slider style
                    max_val = st.slider(
                        'Valor máximo',
                        min_value,
                        max_value,
                        mean_value,
                        key="max_val",
                        help="Ajuste el valor máximo para filtrar los datos."
                    )
                    
                    filtrado_df_max = df1[df1["variable"] < max_val]
                    st.write(f"Registros con valor inferior a {max_val:.2f}:")
                    st.dataframe(filtrado_df_max)

                # Download filtered data with custom button style
                if st.button('Descargar datos filtrados'):
                    csv = filtrado_df_min.to_csv().encode('utf-8')
                    st.download_button(
                        label="Descargar CSV",
                        data=csv,
                        file_name='datos_filtrados.csv',
                        mime='text/csv',
                    )

        with tab4:
            st.subheader("Información del Sitio de Medición")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("### Ubicación del Sensor")
                st.write("*Universidad EAFIT*")
                st.write("- Latitud: 6.2006")
                st.write("- Longitud: -75.5783")
                st.write("- Altitud: ~1,495 metros sobre el nivel del mar")
            
            with col2:
                st.write("### Detalles del Sensor")
                st.write("- Tipo: ESP32")
                st.write("- Variable medida: Según configuración del sensor")
                st.write("- Frecuencia de medición: Según configuración")
                st.write("- Ubicación: Campus universitario")

    except Exception as e:
        st.error(f'Error al procesar el archivo: {str(e)}')
        st.info('Asegúrese de que el archivo CSV tenga al menos una columna con datos.')
else:
    st.warning('Por favor, cargue un archivo CSV para comenzar el análisis.')

# Custom footer styling
st.markdown("""
    ---
    Desarrollado para el análisis de datos de sensores urbanos.
    Ubicación: Universidad EAFIT, Medellín, Colombia
""", unsafe_allow_html=True)
