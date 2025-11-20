import pandas as pd
import streamlit as st
from PIL import Image
import numpy as np
from datetime import datetime

# Configuración de la página con icono, layout y título personalizados
st.set_page_config(
    page_title="Análisis de Sensores - Mi Ciudad",
    page_icon="📍",  # Icono personalizado
    layout="wide"    # Layout de página ancha
)

# Personalización CSS para modificar la apariencia general
st.markdown("""
    <style>
    /* Background and overall style */
    .main {
        background-color: #eef2f7;
        padding: 2rem;
        font-family: 'Arial', sans-serif;
    }

    /* Title and Subtitle Styling */
    h1 {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2c3e50;
    }
    h2, h3 {
        color: #34495e;
    }

    /* Tab Background Color */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #3498db;
        border-radius: 10px;
    }
    
    /* Active Tab Style */
    .stTabs [data-baseweb="tab-list"] > div > div[aria-selected="true"] {
        background-color: #f39c12;
        color: white;
    }

    /* General layout of tabs */
    .stTabContent {
        background-color: white;
        padding: 1rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    /* Button Style */
    .stButton > button {
        background-color: #e67e22;
        color: white;
        border-radius: 12px;
        padding: 10px 20px;
        font-weight: bold;
        border: none;
        transition: background-color 0.3s;
    }
    .stButton > button:hover {
        background-color: #d35400;
    }

    /* Map Style */
    .stMap {
        border-radius: 20px;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.15);
    }

    /* Footer Style */
    footer {
        color: #777;
        font-size: 0.9rem;
        background-color: #f1f1f1;
        padding: 10px;
        text-align: center;
    }

    /* Custom Grid Style */
    .stColumns > div {
        padding: 20px;
        border-radius: 10px;
    }

    /* Custom Dataframe Styling */
    .stDataFrame {
        font-family: 'Arial', sans-serif;
        border-radius: 8px;
        background-color: #f9f9f9;
        padding: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Título principal
st.title('📊 Análisis de Datos de Sensores - Mi Ciudad')
st.markdown("""
    Bienvenido al análisis de datos de sensores urbanos. 
    Explore los datos recogidos en diferentes puntos de la ciudad para comprender mejor el entorno.
""")

# Ubicación del Sensor con un mapa estilizado (ahora El Tesoro)
st.subheader("📍 Ubicación del Sensor - Centro Comercial El Tesoro")
el_tesoro_location = pd.DataFrame({
    'lat': [6.1861],  # Coordenada actualizada para El Tesoro
    'lon': [-75.5776],  # Coordenada actualizada para El Tesoro
    'location': ['Centro Comercial El Tesoro']
})

# Muestra el mapa con borde redondeado y sombra
st.map(el_tesoro_location, zoom=15)

# Carga de archivo CSV
uploaded_file = st.file_uploader('Cargar archivo CSV', type=['csv'])

if uploaded_file is not None:
    try:
        # Cargar y procesar los datos del archivo CSV
        df1 = pd.read_csv(uploaded_file)
        
        # Renombrar la columna de la variable de interés
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

        # Crear pestañas para análisis diferentes
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Visualización", "📊 Estadísticas", "🔍 Filtros", "🗺️ Información del Sitio"])

        with tab1:
            st.subheader('Visualización de Datos')
            
            # Selector de tipo de gráfico con colores personalizados
            chart_type = st.selectbox(
                "Seleccione el tipo de gráfico",
                ["Línea", "Área", "Barra"]
            )
            
            # Generar el gráfico según la selección
            if chart_type == "Línea":
                st.line_chart(df1["variable"])
            elif chart_type == "Área":
                st.area_chart(df1["variable"])
            else:
                st.bar_chart(df1["variable"])

            # Opción para mostrar los datos crudos
            if st.checkbox('Mostrar datos crudos'):
                st.write(df1)

        with tab2:
            st.subheader('Análisis Estadístico')
            
            # Resumen estadístico
            stats_df = df1["variable"].describe()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.dataframe(stats_df)
            
            with col2:
                # Estadísticas adicionales con estilo
                st.metric("Valor Promedio", f"{stats_df['mean']:.2f}")
                st.metric("Valor Máximo", f"{stats_df['max']:.2f}")
                st.metric("Valor Mínimo", f"{stats_df['min']:.2f}")
                st.metric("Desviación Estándar", f"{stats_df['std']:.2f}")

        with tab3:
            st.subheader('Filtros de Datos')
            
            # Calcular el rango de los datos
            min_value = float(df1["variable"].min())
            max_value = float(df1["variable"].max())
            mean_value = float(df1["variable"].mean())
            
            # Verificar variación en los datos
            if min_value == max_value:
                st.warning(f"⚠️ Todos los valores en el dataset son iguales: {min_value:.2f}")
                st.info("No es posible aplicar filtros cuando no hay variación en los datos.")
                st.dataframe(df1)
            else:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Filtro de valor mínimo con slider estilizado
                    min_val = st.slider(
                        'Valor mínimo',
                        min_value,
                        max_value,
                        mean_value,
                        key="min_val"
                    )
                    
                    filtrado_df_min = df1[df1["variable"] > min_val]
                    st.write(f"Registros con valor superior a {min_val:.2f}:")
                    st.dataframe(filtrado_df_min)
                    
                with col2:
                    # Filtro de valor máximo con slider estilizado
                    max_val = st.slider(
                        'Valor máximo',
                        min_value,
                        max_value,
                        mean_value,
                        key="max_val"
                    )
                    
                    filtrado_df_max = df1[df1["variable"] < max_val]
                    st.write(f"Registros con valor inferior a {max_val:.2f}:")
                    st.dataframe(filtrado_df_max)

                # Botón para descargar los datos filtrados con estilo personalizado
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
                st.write("**Centro Comercial El Tesoro**")
                st.write("- Latitud: 6.1861")
                st.write("- Longitud: -75.5776")
                st.write("- Altitud: ~1,545 metros sobre el nivel del mar")
            
            with col2:
                st.write("### Detalles del Sensor")
                st.write("- Tipo: ESP32")
                st.write("- Variable medida: Según configuración del sensor")
                st.write("- Frecuencia de medición: Según configuración")
                st.write("- Ubicación: Centro comercial")

    except Exception as e:
        st.error(f'Error al procesar el archivo: {str(e)}')
        st.info('Asegúrese de que el archivo CSV tenga al menos una columna con datos.')
else:
    st.warning('Por favor, cargue un archivo CSV para comenzar el análisis.')

# Estilo personalizado para el pie de página
st.markdown("""
    ---
    Desarrollado para el análisis de datos de sensores urbanos.
    Ubicación: Centro Comercial El Tesoro, Medellín, Colombia
""", unsafe_allow_html=True)
