import streamlit as st
import pandas as pd
import numpy as np
import io
import warnings
import re

# 1. CONFIGURACIÓN
warnings.filterwarnings("ignore")

# --- ESTILOS CSS UNIFICADOS---
st.markdown("""
    <style>
    div.stButton > button:first-child[kind="primary"] {
        background-color: #2E8B57;
        border-color: #2E8B57;
        color: white;
        border-radius: 6px;
    }
    div.stButton > button:first-child[kind="primary"]:hover {
        background-color: #236B45;
        border-color: #236B45;
        color: white;
    }
    div.stButton > button:first-child[kind="primary"]:focus,
    div.stButton > button:first-child[kind="primary"]:active {
        background-color: #2E8B57;
        border-color: #2E8B57;
        color: white;
        box-shadow: none;
    }
    </style>
""", unsafe_allow_html=True)

st.title("💾 Generador SQL Masivo")
st.markdown("Sube **múltiples archivos CSV**. Se generará un script SQL **idempotente** y compatible con MySQL.")

# 2. BARRA LATERAL
st.sidebar.header("⚙️ Configuración SQL")
st.sidebar.info("Los nombres de las tablas se tomarán del nombre del archivo CSV.")

# Configuraciones
incluir_drop = st.sidebar.checkbox("Incluir DROP TABLE IF EXISTS", value=True, help="Borra la tabla si ya existe. Evita errores al re-importar.")
incluir_create = st.sidebar.checkbox("Incluir CREATE TABLE", value=True)
batch_size = st.sidebar.number_input("Filas por INSERT (Batch):", 1, 5000, 100)

# 3. FUNCIONES AUXILIARES
def sanear_nombre_tabla(nombre_archivo):

    # Eliminar extensión y dejar solo caracteres seguros

    nombre = nombre_archivo.rsplit('.', 1)[0]
    nombre = re.sub(r'[^a-zA-Z0-9]', '_', nombre).lower()
    return nombre

def cargar_y_limpiar(archivo):
    archivo.seek(0)
    try:
        df = pd.read_csv(archivo, sep=';', dtype=str, encoding='utf-8-sig', on_bad_lines='skip', engine='python')
        if len(df.columns) < 2: raise ValueError()
    except:
        archivo.seek(0)
        try:
            df = pd.read_csv(archivo, sep=',', dtype=str, encoding='utf-8-sig', on_bad_lines='skip', engine='python')
        except:
            return None, None
            
    # --- SANEAMIENTO CABECERAS ---

    # 1. Todo a minúsculas y quitar espacios
    df.columns = df.columns.astype(str).str.lower().str.strip()
    
    # 2. Reemplazo regex: Mantener SOLO letras (a-z), números (0-9) y guion bajo (_)
    # Elimina -> ':', '.', '(', ')', '/', etc.
    # Ej: "Unnamed: 2" -> "unnamed2"
    df.columns = [re.sub(r'[^a-z0-9_]', '', col) for col in df.columns]
    
    # 3. Evita nombres vacíos "" 
    df.columns = [col if col else f"columna_{i}" for i, col in enumerate(df.columns)]
        
    # Saneamiento valores
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    basura = ['', ' ', 'nan', 'NaN', 'null', 'NULL', 'None', 'none']
    df.replace(basura, np.nan, inplace=True)
    
    return df, sanear_nombre_tabla(archivo.name)

def map_pandas_to_sql(df):
    tipos_sql = {}
    for col in df.columns:
        sample = df[col].dropna()
        if sample.empty:
            tipos_sql[col] = "VARCHAR(255)"
            continue
        try:
            pd.to_datetime(sample, dayfirst=True, errors='raise')
            tipos_sql[col] = "DATE"
            continue
        except: pass
        try:
            es_num = pd.to_numeric(sample, errors='raise')
            if (es_num % 1 == 0).all():
                if es_num.max() > 2147483647: tipos_sql[col] = "BIGINT"
                else: tipos_sql[col] = "INT"
                continue
        except: pass
        try:
            pd.to_numeric(sample, errors='raise')
            tipos_sql[col] = "DECIMAL(10,2)"
            continue
        except: pass

        max_len = sample.astype(str).str.len().max()
        if max_len > 255: tipos_sql[col] = "TEXT"
        else: tipos_sql[col] = f"VARCHAR({max(50, int(max_len * 1.5))})"
    return tipos_sql

def generar_bloque_sql(df, nombre_tabla):
    script_bloque = []
    
    # Separador visual con formato de comentario SQL (-- )
    script_bloque.append(f"\n-- ----------------------------------------") 
    script_bloque.append(f"-- TABLA: {nombre_tabla}")
    script_bloque.append(f"-- ----------------------------------------")
    
    # A. DROP
    if incluir_drop: 
        script_bloque.append(f"DROP TABLE IF EXISTS {nombre_tabla};")

    # B. CREATE
    if incluir_create:
        tipos = map_pandas_to_sql(df)
        cols_def = [f"    {col} {tipo}" for col, tipo in tipos.items()]
        create_stmt = f"CREATE TABLE {nombre_tabla} (\n" + ",\n".join(cols_def) + "\n);"
        script_bloque.append(create_stmt)
        script_bloque.append("")

    # C. INSERTS
    def sql_val(val):
        if pd.isna(val) or str(val).upper() == 'NAN': return "NULL"
        # Escapado robusto de caracteres especiales
        clean_val = str(val).replace("\\", "\\\\").replace("'", "''")
        return f"'{clean_val}'"

    columnas = ", ".join(df.columns)
    total = len(df)
    
    if total > 0:
        for i in range(0, total, batch_size):
            chunk = df.iloc[i : i + batch_size]
            values_list = []
            for _, row in chunk.iterrows():
                v = [sql_val(val) for val in row]
                values_list.append(f"({', '.join(v)})")
            
            if values_list:
                bloque = ",\n".join(values_list)
                script_bloque.append(f"INSERT INTO {nombre_tabla} ({columnas}) VALUES\n{bloque};")
    else:
         script_bloque.append(f"-- Tabla {nombre_tabla} vacía, omitiendo inserts.")
    
    return "\n".join(script_bloque)

# 4. INTERFAZ
uploaded_files = st.file_uploader("📂 Arrastra tus archivos CSV aquí", type=['csv'], accept_multiple_files=True)

if 'sql_completo_04' not in st.session_state: st.session_state['sql_completo_04'] = None

if uploaded_files:
    if st.button(f"Generar Script para {len(uploaded_files)} archivos", type="primary"):
        sql_total = []
        sql_total.append(f"-- Script Generado Automáticamente: {len(uploaded_files)} tablas")
        sql_total.append(f"-- Fecha: {pd.Timestamp.now()}\n")
        
        barra = st.progress(0)
        
        for i, archivo in enumerate(uploaded_files):
            df, nombre_tabla = cargar_y_limpiar(archivo)
            
            if df is not None:
                bloque = generar_bloque_sql(df, nombre_tabla)
                sql_total.append(bloque)
            else:
                st.warning(f"⚠️ No se pudo leer {archivo.name}")
            
            barra.progress((i + 1) / len(uploaded_files))
            
        st.session_state['sql_completo_04'] = "\n".join(sql_total)
        st.success("✅ Generación Masiva Completada.")

    # ZONA DE DESCARGA
    if st.session_state.get('sql_completo_04'):
        st.divider()
        st.subheader("💾 Descargar Script Unificado")
        
        st.download_button(
            label="📥 Descargar dump_completo.sql",
            data=st.session_state['sql_completo_04'],
            file_name="dump_carga_masiva.sql",
            mime="text/plain",
            type="primary"
        )
        
        with st.expander("🔍 Previsualizar inicio del script"):
            st.code("\n".join(st.session_state['sql_completo_04'].splitlines()[:50]), language="sql")

else:
    st.info("Esperando archivos...")