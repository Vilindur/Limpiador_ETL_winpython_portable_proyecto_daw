import streamlit as st

# Configuración de la página principal
st.set_page_config(
    page_title="Limpiador ETL Lite",
    page_icon="🧰",
    layout="wide"
)

# Título y Bienvenida
st.title("👋 Bienvenido al portal de ingeniería de datos")
st.caption("v2.0 | Entorno Portable WinPythonDot")

# Maquetación cuerpo principal
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
        ### Centro de Operaciones
    
        Bienvenido a tu suite de herramientas ETL (Extract, Transform, Load).
        Esta aplicación se ejecuta localmente y no requiere instalación.
    
        **👈 Selecciona una herramienta en el menú lateral para comenzar.**
        """
    )

    st.info(
        """
        🔐 Todos los procesos se realizan en la memoria de tu equipo. 
        Tus datos están seguros y no se envían a ninguna nube externa.
        """
    )

with col2:
    st.markdown("### 🛠️ Herramientas Disponibles")

    st.markdown("""
    
        1.-  **🧹 Limpieza genérica de caracteres (Quotes, BOM, Gremlins):**
            * Realiza una limpieza de caracteres problemáticos a un archivo dado.
            * Devuelve el archivo saneado en .csv o .xlsx.
        
        2.-  **🔍 Detección de posibles duplicados (Fuzzy Matching):**
            * Compara los registros por las columnas seleccionadas del archivo seleccionado.
            * Devuelve un informe en .csv o el archivo de correcciones con los ids válidos y erróneos. 
    
        3.-  **💾 Generador de script de carga de datos SQL:**
            * Genera un script en SQL a partir de un archivo .csv
            * Devuelve el script .sql con el código listo para importar o ejecutar en una base de datos.
        
        4.-  **🧩 Consolidador Universal (Genérico):**
            * La herramienta más flexible de la suite.
            * Tú defines manualmente la **Clave ID** y el **Criterio de Prioridad** (Fecha).
            * Sirve para cualquier tipo de datos (Productos, Vehículos, Inventario...).

        5.-  **🔗 Cruzador de Tablas (Vslookup):**
            * Une dos archivos CSV mediante una columna común (Join).
            * Ideal para enriquecer datos y rellenar columnas necesarias de otros archivos.
                
        7.-  ** Radiografía de Datos (Profiler):**
            * Auditoría inicial de control de calidad de datos.
            * Detecta % de nulos, duplicados exactos y duplicaciones de claves primarias.
            * Permite descargar los registros conflictivos aparte.
                
        """
    )

# Mensaje de estado en la barra lateral
st.sidebar.success("🟢 Sistema operativo. Selecciona una herramienta arriba.")