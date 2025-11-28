import streamlit as st
import pandas as pd
import numpy as np
import warnings
import time
import io
import sys
import os

# --- GESTIÓN DE IMPORTACIÓN (NUEVA RUTA 'CORE') ---
# Añadimos la carpeta raíz del proyecto al sistema para poder encontrar 'core'
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

try:
    # Ahora buscamos la librería dentro de la carpeta 'core'
    from core.lib_estrategias import CATALOGO_ESTRATEGIAS
except ImportError as e:
    st.error(f"❌ Error Crítico: No se encuentra 'core/lib_estrategias.py'. Detalle: {e}")
    st.stop()

# 1. CONFIGURACIÓN
warnings.filterwarnings("ignore")

# --- ESTILOS CSS---
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

st.title("🧩 Consolidador Universal (Genérico)")
st.markdown("Modularidad total: Define tu **Clave** y tus reglas. **El registro Maestro siempre tiene prioridad.**")

# 2. CARGA BLINDADA
def cargar_blindado(archivo):
    archivo.seek(0)
    try:
        df = pd.read_csv(archivo, sep=';', dtype=str, encoding='utf-8-sig', on_bad_lines='skip', engine='python')
        if len(df.columns) < 2: raise ValueError()
    except:
        archivo.seek(0)
        try:
            df = pd.read_csv(archivo, sep=',', dtype=str, encoding='utf-8-sig', on_bad_lines='skip', engine='python')
        except:
            return None
    
    df.columns = df.columns.astype(str).str.lower().str.strip()
    for b in ['ï»¿', '\ufeff', '"', "'"]: df.columns = df.columns.str.replace(b, '', regex=False)
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    basura = ['', ' ', 'nan', 'NaN', 'null', 'NULL', 'None', 'none']
    df.replace(basura, np.nan, inplace=True)
    return df

# 3. INTERFAZ
col1, col2 = st.columns(2)
fm = col1.file_uploader("📂 Datos (Tabla Madre)", type=['csv'])
fc = col2.file_uploader("🛠️ Correcciones (Mapa)", type=['csv'])

# GESTIÓN DE ESTADO (LIMPIEZA AL CAMBIAR ARCHIVO)
if 'ultimo_archivo_06' not in st.session_state: st.session_state['ultimo_archivo_06'] = None

if fm and fc:
    nombres_actuales = f"{fm.name}_{fc.name}"
    if st.session_state['ultimo_archivo_06'] != nombres_actuales:
        # Borramos caché anterior
        keys_borrar = ['res_consol_06', 'excel_bytes_06']
        for k in keys_borrar:
            if k in st.session_state: del st.session_state[k]
        st.session_state['ultimo_archivo_06'] = nombres_actuales

    df_p = cargar_blindado(fm)
    df_c = cargar_blindado(fc)
    
    if df_p is not None and df_c is not None:
        st.success(f"✅ Datos cargados: {len(df_p)} filas.")
        st.divider()

        # A. CONFIG CLAVES
        st.subheader("🔑 Configuración de Claves")
        c_key, c_sort = st.columns(2)

        col_id_usuario = c_key.selectbox(
            "1. Columna ID (Clave Única):", df_p.columns, index=0
        )

        cols_fecha = [c for c in df_p.columns if 'fecha' in c.lower() or 'date' in c.lower() or 'update' in c.lower()]
        idx_def = list(df_p.columns).index(cols_fecha[0]) + 1 if cols_fecha else 0

        col_sort_usuario = c_sort.selectbox(
            "2. Criterio de 'frescura' (Desempate):", 
            ["-- Ninguna (El Maestro manda siempre) --"] + list(df_p.columns),
            index=idx_def
        )

        # MAPEO INTERNO
        df_p['pid_clean'] = df_p[col_id_usuario].astype(str).str.replace(r'[- ]', '', regex=True).str.upper().str.strip()
        def clean_key(s): return s.astype(str).str.replace(r'[- ]', '', regex=True).str.upper().str.strip()
        mapa_dict = {}

        cols_err = [c for c in df_c.columns if 'erroneo' in c or 'bad' in c]
        if not cols_err and len(df_c.columns) > 1: cols_err = [df_c.columns[1]]
        cols_val = [c for c in df_c.columns if 'valido' in c or 'good' in c]
        col_val_corr = cols_val[0] if cols_val else df_c.columns[0]

        if cols_err:
            for c_err in cols_err:
                temp = df_c.dropna(subset=[c_err]).copy()
                k_bad = clean_key(temp[c_err])
                k_good = clean_key(temp[col_val_corr])
                mapa_dict.update(zip(k_bad, k_good))
            st.info(f"Mapeo: {col_val_corr} <- {cols_err}")
        else:
            st.warning("⚠️ Usando columnas 0 y 1 por defecto.")

        df_p['id_maestro'] = df_p['pid_clean'].map(mapa_dict).fillna(df_p['pid_clean'])
        
        # B. REGLAS
        st.divider()
        st.subheader("🛠️ Reglas de Fusión")
        
        c_fmt, c_info = st.columns([1, 2])
        user_date_fmt = c_fmt.text_input("Formato Fechas:", value="%d/%m/%Y")
        
        with st.expander("Desplegar Reglas", expanded=True):
            cols_datos = [c for c in df_p.columns if c not in ['pid_clean', 'id_maestro', 'es_original']]
            reglas_seleccionadas = {}
            cols_ui = st.columns(3)
            cols_tipo_fecha = [] 
            
            opciones_reglas = list(CATALOGO_ESTRATEGIAS.keys())

            def buscar_indice_regla(col_actual):
                texto_col = col_actual.lower()
                for idx, nombre_regla in enumerate(opciones_reglas):
                    if 'nif' in texto_col and 'nif' in nombre_regla.lower(): return idx
                    if 'genero' in texto_col and 'género' in nombre_regla.lower(): return idx
                    if 'fecha' in texto_col and 'inicio' in texto_col and 'inicio' in nombre_regla.lower(): return idx
                    if 'fecha' in texto_col and 'fin' in texto_col and 'fin' in nombre_regla.lower(): return idx
                return 0 

            for i, col_name in enumerate(cols_datos):
                idx_def = buscar_indice_regla(col_name)
                with cols_ui[i % 3]:
                    estrategia = st.selectbox(
                        f"**{col_name}**", opciones_reglas, index=idx_def, key=f"s_{col_name}"
                    )
                    reglas_seleccionadas[col_name] = CATALOGO_ESTRATEGIAS[estrategia]
                    if "Fecha" in estrategia or "date" in col_name.lower():
                        cols_tipo_fecha.append(col_name)

        # C. EJECUCIÓN (Genera y Guarda en Session State)
        st.divider()
        if st.button("Consolidar registros", type="primary"):
            p_bar = st.progress(0, text="Procesando...")
            
            try:
                # 1. ORDENACIÓN
                df_p['es_original'] = df_p['pid_clean'] == df_p['id_maestro']
                sort_cols = ['es_original']
                asc = [False]

                if col_sort_usuario != "-- Ninguna (El Maestro manda siempre) --":
                    sort_cols.append(col_sort_usuario)
                    asc.append(False)

                df_sorted = df_p.sort_values(by=sort_cols, ascending=asc)
                
                # 2. AGREGACIÓN
                df_final = df_sorted.groupby('id_maestro', as_index=False).agg(reglas_seleccionadas)
                
                # 3. RESTAURACIÓN
                if col_id_usuario in df_final.columns: 
                    df_final[col_id_usuario] = df_final['id_maestro']
                if 'id_maestro' in df_final.columns: del df_final['id_maestro']

                # 4. NIF CHECK
                if 'nif' in df_final.columns:
                    patron_dni = r'^[0-9]{8}[A-Z]$'
                    pid_norm = df_final[col_id_usuario].astype(str).str.upper().str.strip().str.replace(r'[- .]', '', regex=True)
                    nif_vacio = df_final['nif'].isna() | (df_final['nif'] == "")
                    id_es_bueno = pid_norm.str.match(patron_dni)
                    df_final.loc[nif_vacio & id_es_bueno, 'nif'] = pid_norm.loc[nif_vacio & id_es_bueno]

                # 5. FORMATO FECHAS
                for col_fecha in cols_tipo_fecha:
                    if col_fecha in df_final.columns:
                        fechas_obj = pd.to_datetime(df_final[col_fecha], dayfirst=True, errors='coerce')
                        df_final[col_fecha] = fechas_obj.dt.strftime(user_date_fmt).replace('NaT', np.nan)

                # --- GUARDADO EN SESIÓN ---
                st.session_state['res_consol_06'] = df_final
                
                # Generación Excel
                try:
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                        df_final.to_excel(writer, index=False, sheet_name="Consolidado")
                    st.session_state['excel_bytes_06'] = buf.getvalue()
                except Exception as e:
                    st.warning(f"No se pudo generar Excel: {e}")
                    st.session_state['excel_bytes_06'] = None

                p_bar.empty()
                st.success(f"✅ Consolidación finalizada: {len(df_final)} registros únicos.")

            except Exception as e:
                p_bar.empty()
                st.error(f"Error: {e}")

    # D. VISUALIZACIÓN Y DESCARGA (PERSISTENTE)
    if 'res_consol_06' in st.session_state:
        df_res = st.session_state['res_consol_06']
        
        st.divider()
        st.subheader(f"📊 Resultados ({len(df_res)} registros)")
        st.dataframe(df_res.head(50))
        
        # ZONA DE DESCARGAS
        st.divider()
        st.subheader("💾 Descargar Resultados")
        
        # Selector de separador
        c_conf_dl, c_btn_dl = st.columns([1, 2])
        
        with c_conf_dl:
            modo_sep = st.radio(
                "Separador CSV:", 
                ["Punto y coma (;)", "Coma (,)", "Pipe (|)", "Personalizado"], 
                horizontal=False
            )
            
            sep_final = ";"
            if "Coma" in modo_sep: sep_final = ","
            elif "Pipe" in modo_sep: sep_final = "|"
            elif "Personalizado" in modo_sep:
                sep_final = st.text_input("Escribe tu carácter:", value=";", max_chars=1)

        with c_btn_dl:
            st.write("###") # Espaciador visual
            
            # 1. Generación dinámica del CSV según selección
            try:
                csv_data = df_res.to_csv(index=False, sep=sep_final, encoding='utf-8-sig')
                
                st.download_button(
                    label=f"📥 Descargar CSV ({sep_final})",
                    data=csv_data,
                    file_name="consolidado_universal.csv",
                    mime="text/csv",
                    type="secondary" # Botón secundario para diferenciar
                )
            except Exception as e:
                st.error(f"Separador inválido: {e}")

            # 2. Descarga Excel (Desde Caché)
            if st.session_state.get('excel_bytes_06'):
                st.download_button(
                    label="📥 Descargar Excel (.xlsx)",
                    data=st.session_state['excel_bytes_06'],
                    file_name="consolidado_universal.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary" # Botón principal
                )