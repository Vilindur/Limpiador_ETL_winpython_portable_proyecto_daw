import streamlit as st
import pandas as pd
import numpy as np
import io
import warnings
from difflib import SequenceMatcher
import time

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

st.title("🔍 Detective de Duplicados (Fuzzy Match)")
st.markdown("Detecta registros que **se parecen** pero no son idénticos.")

# 2. BARRA LATERAL
st.sidebar.header("⚙️ Configuración")

st.sidebar.subheader("Sensibilidad")
umbral = st.sidebar.slider("Similitud mínima (%)", 50, 99, 85)

st.sidebar.subheader("Rendimiento")
limite_filas = st.sidebar.number_input(
    "Filas a analizar (Tope):", 
    min_value=100, 
    max_value=1000000, 
    value=10000, 
    step=1000,
    help="Límite de seguridad para no bloquear el equipo con archivos gigantes."
)

# 3. MOTOR DE CARGA
def cargar_dataset(archivo):
    archivo.seek(0)
    try:
        df = pd.read_csv(archivo, sep=';', dtype=str, encoding='utf-8-sig', on_bad_lines='skip', engine='python')
        if len(df.columns) < 2: raise ValueError()
    except:
        archivo.seek(0)
        try:
            df = pd.read_csv(archivo, sep=',', dtype=str, encoding='utf-8-sig', on_bad_lines='skip', engine='python')
        except:
            return None, "Error crítico: Formato no detectado."

    df.columns = df.columns.astype(str).str.lower().str.strip()
    for b in ['ï»¿', '\ufeff', '"', "'"]: df.columns = df.columns.str.replace(b, '', regex=False)
    
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    basura = ['', ' ', 'nan', 'NaN', 'null', 'NULL', 'None', 'none']
    df.replace(basura, np.nan, inplace=True)
    
    return df, None

# 4. LÓGICA DIFUSA
def similitud_texto(a, b):
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio() * 100

def buscar_parecidos(df, columnas_clave, umbral, limite):
    df_proc = df.copy()
    cols_id = [c for c in df.columns if 'id' in c or 'nif' in c or 'dni' in c]
    col_id_ref = cols_id[0] if cols_id else None
    
    for col in columnas_clave:
        df_proc[col] = df_proc[col].fillna('')
        
    df_proc['__huella__'] = df_proc[columnas_clave].apply(lambda row: ' '.join(row.values.astype(str)).strip(), axis=1)
    df_proc = df_proc[df_proc['__huella__'] != '']
    
    indices = df_proc.index.tolist()
    huellas = df_proc['__huella__'].tolist()
    ids_reales = df_proc[col_id_ref].tolist() if col_id_ref else [str(x) for x in indices]

    n = len(huellas)
    parejas = []
    rango = min(n, limite)
    
    barra = st.progress(0)
    texto = st.empty()
    start_time = time.time()
    
    for i in range(rango):
        if i % 50 == 0: 
            progreso = i / rango
            barra.progress(progreso)
            
            elapsed = time.time() - start_time
            if elapsed > 0:
                velocidad = (i + 1) / elapsed
                segundos_restantes = (rango - i) / velocidad
                mins, segs = divmod(int(segundos_restantes), 60)
                msg_tiempo = f"{mins}m {segs}s" if mins > 0 else f"{segs}s"
            else:
                msg_tiempo = "Calculando..."

            texto.text(f"Analizando fila {i}/{rango}... (~{msg_tiempo} restantes)")

        for j in range(i + 1, rango):
            if abs(len(huellas[i]) - len(huellas[j])) > 5 and umbral > 90: continue 

            score = similitud_texto(huellas[i], huellas[j])
            
            if score >= umbral and score < 100:
                parejas.append({
                    'ID_Real_A': ids_reales[i],
                    'Valor_A': huellas[i],
                    'ID_Real_B': ids_reales[j],
                    'Valor_B': huellas[j],
                    'Similitud': round(score, 2)
                })
    
    barra.empty()
    texto.empty()
    return pd.DataFrame(parejas)

# 5. INTERFAZ
uploaded_file = st.file_uploader("📂 Sube archivo a investigar (CSV)", type=['csv'])

if 'ultimo_archivo_03' not in st.session_state: st.session_state['ultimo_archivo_03'] = None

if uploaded_file:
    if st.session_state['ultimo_archivo_03'] != uploaded_file.name:
        keys_clear = ['res_fuzzy_03', 'excel_bytes_03']
        for k in keys_clear:
            if k in st.session_state: del st.session_state[k]
        st.session_state['ultimo_archivo_03'] = uploaded_file.name

    df, error = cargar_dataset(uploaded_file)
    
    if error:
        st.error(error)
    else:
        st.info(f"Filas: {len(df)}")
        st.divider()
        
        c_conf, c_par = st.columns([2, 1])
        cols = list(df.columns)
        
        with c_conf:
            c_nom = [c for c in cols if 'nombre' in c]
            c_ape = [c for c in cols if 'apellido' in c]
            c_ids = [c for c in cols if 'id' in c or 'nif' in c]
            sel = st.multiselect("Huella Digital:", cols, default=c_nom + c_ape if (c_nom and c_ape) else c_ids[:1])

        with c_par:
            st.markdown(f"**Umbral:** {umbral}%")

        if st.button("Buscar Parecidos", type="primary"):
            if not sel:
                st.error("Selecciona columnas.")
            else:
                res = buscar_parecidos(df, sel, umbral, limite_filas)
                st.session_state['res_fuzzy_03'] = res
                st.session_state['excel_bytes_03'] = None 

    # RESULTADOS
    if 'res_fuzzy_03' in st.session_state:
        res_df = st.session_state['res_fuzzy_03']
        
        st.divider()
        
        if res_df.empty:
            st.success("✅ No se encontraron parecidos.")
        else:
            st.subheader(f"⚠️ {len(res_df)} Parejas Detectadas")
            
            df_editor = pd.DataFrame({
                'nif_valido': res_df['ID_Real_A'],
                'nif_erroneo1': res_df['ID_Real_B'],
                'Similitud (%)': res_df['Similitud'],
                'Ref_Valido': res_df['Valor_A'],
                'Ref_Erroneo': res_df['Valor_B']
            })
            
            # --- CORRECCIÓN CLAVE: Se captura el dataframe editado---
            edited_df = st.data_editor(
                df_editor,
                use_container_width=True,
                column_config={
                    "nif_valido": st.column_config.TextColumn("ID Válido", required=True),
                    "nif_erroneo1": st.column_config.TextColumn("ID Erróneo", required=True),
                    "Similitud (%)": st.column_config.ProgressColumn("Similitud", format="%d%%", min_value=0, max_value=100),
                },
                hide_index=True,
                key="editor_duplicados" # Clave para persistencia interna del widget
            )

            # --- ZONA DE DESCARGA (Usamos 'edited_df' en lugar de 'df_editor') ---
            st.divider()
            st.subheader("💾 Descargas (Incluye tus ediciones)")
            
            c_conf_dl, c_btn_dl = st.columns([1, 2])
            
            with c_conf_dl:
                modo_sep = st.radio(
                    "Separador CSV:", 
                    ["Punto y coma (;)", "Coma (,)", "Pipe (|)", "Personalizado"], 
                    horizontal=False,
                    key="sep_radio_03"
                )
                
                sep_final = ";"
                if "Coma" in modo_sep: sep_final = ","
                elif "Pipe" in modo_sep: sep_final = "|"
                elif "Personalizado" in modo_sep:
                    sep_final = st.text_input("Carácter:", value=";", max_chars=1, key="sep_custom_03")

            with c_btn_dl:
                st.write("###")
                
                # Uso de edited_df
                df_correcciones = edited_df[['nif_valido', 'nif_erroneo1']]
                df_informe = edited_df
                
                try:
                    csv_corr = df_correcciones.to_csv(index=False, sep=sep_final, encoding='utf-8-sig')
                    st.download_button(
                        label=f"📥 CSV Correcciones ({sep_final})",
                        data=csv_corr,
                        file_name="correcciones_duplicados.csv",
                        mime="text/csv",
                        type="secondary"
                    )
                    
                    csv_info = df_informe.to_csv(index=False, sep=sep_final, encoding='utf-8-sig')
                    st.download_button(
                        label=f"📥 CSV Informe Completo ({sep_final})",
                        data=csv_info,
                        file_name="informe_duplicados.csv",
                        mime="text/csv",
                        type="secondary"
                    )
                except Exception as e:
                    st.error(f"Separador inválido: {e}")

                # Excel
                try:
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                        df_informe.to_excel(writer, sheet_name="Informe Completo", index=False)
                        df_correcciones.to_excel(writer, sheet_name="Solo Correcciones", index=False)
                    excel_data = buf.getvalue()
                    
                    st.download_button(
                        label="📥 Descargar Excel (Multisheet)",
                        data=excel_data,
                        file_name="analisis_duplicados.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
                except:
                    st.error("Error generando Excel.")