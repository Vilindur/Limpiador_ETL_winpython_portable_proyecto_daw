import streamlit as st
import pandas as pd
import io
import warnings

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
    /* Estilo rojo para la tabla de duplicados */
    div[data-testid="stExpander"] div[data-testid="stDataFrame"] {
        border: 1px solid #ff4b4b;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🩻 Radiografía de Datos (Profiler)")
st.markdown("Auditoría de calidad: Detecta nulos, tipos de datos y **violaciones de clave primaria**.")

# 2. CARGA DE DATOS
def cargar_csv(archivo):
    archivo.seek(0)
    try:
        # Detectar separador automáticamente (sep=None)
        df = pd.read_csv(archivo, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip')
        return df
    except:
        return None

uploaded_file = st.file_uploader("📂 Sube tu archivo CSV para auditarlo", type=['csv'])

# Gestión de Estado
if 'res_profiler_09' not in st.session_state: st.session_state['res_profiler_09'] = None
if 'nombre_archivo_09' not in st.session_state: st.session_state['nombre_archivo_09'] = None

if uploaded_file:
    # Reset si cambia el archivo
    if st.session_state['nombre_archivo_09'] != uploaded_file.name:
        st.session_state['res_profiler_09'] = None
        st.session_state['nombre_archivo_09'] = uploaded_file.name

    if st.button("🔍 Analizar Calidad", type="primary"):
        df = cargar_csv(uploaded_file)
        if df is not None:
            st.session_state['res_profiler_09'] = df
        else:
            st.error("Error al leer el archivo.")

if st.session_state['res_profiler_09'] is not None:
    df = st.session_state['res_profiler_09']
    
    st.divider()
    st.success(f"✅ Análisis completado: {len(df)} filas, {len(df.columns)} columnas.")

    # 3. ANÁLISIS DE DUPLICADOS (INTELIGENTE)
    st.subheader("🔑 Análisis de Unicidad")
    
    col_sel, col_metrics = st.columns([1, 3])
    
    with col_sel:
        # Intentamos adivinar la columna ID
        posibles_ids = [c for c in df.columns if 'id' in c.lower() or 'cod' in c.lower() or 'sku' in c.lower()]
        idx_def = list(df.columns).index(posibles_ids[0]) if posibles_ids else 0
        
        col_id = st.selectbox("Selecciona tu Columna ID (PK):", df.columns, index=idx_def)

    with col_metrics:
        dup_exactos = df.duplicated().sum()
        dup_ids = df[col_id].duplicated().sum()
        
        m1, m2 = st.columns(2)
        m1.metric(
            "Filas Exactamente Iguales", 
            dup_exactos, 
            help="Filas idénticas (basura).",
            delta_color="inverse" if dup_exactos > 0 else "normal"
        )
        m2.metric(
            f"IDs Repetidos ({col_id})", 
            dup_ids, 
            help=f"Violaciones de Clave Primaria en '{col_id}'.",
            delta_color="inverse" if dup_ids > 0 else "normal"
        )

    # --- ZONA DE ALERTA Y DESCARGA DE DUPLICADOS ---
    if dup_ids > 0:
        st.write("###")
        st.error(f"⚠️ Se han encontrado **{dup_ids} duplicaciones de claves primarias**.")
        
        # Filtramos para obtener los datos problemáticos (keep=False muestra original y duplicado)
        df_dupes = df[df[col_id].duplicated(keep=False)].sort_values(by=col_id)

        with st.expander(f"Ver/Descargar registros conflictivos ({len(df_dupes)} filas)", expanded=True):
            st.dataframe(df_dupes, use_container_width=True, hide_index=True)
            
            st.write("---")
            st.markdown("##### 📥 Descargar solo esta tabla de errores")
            
            c_conf_err, c_btn_err = st.columns([1, 2])
            
            with c_conf_err:
                modo_sep_err = st.radio(
                    "Separador CSV:", 
                    ["Punto y coma (;)", "Coma (,)", "Pipe (|)", "Personalizado"], 
                    key="sep_err_09"
                )
                
                sep_final_err = ";"
                if "Coma" in modo_sep_err: sep_final_err = ","
                elif "Pipe" in modo_sep_err: sep_final_err = "|"
                elif "Personalizado" in modo_sep_err:
                    sep_final_err = st.text_input("Carácter:", value=";", max_chars=1, key="sep_custom_err_09")
            
            with c_btn_err:
                st.write("###")
                try:
                    # CSV de Errores
                    csv_err = df_dupes.to_csv(index=False, sep=sep_final_err, encoding='utf-8-sig')
                    st.download_button(
                        label=f"📥 Descargar CSV Errores ({sep_final_err})",
                        data=csv_err,
                        file_name="registros_duplicados_error.csv",
                        mime="text/csv",
                        type="secondary"
                    )
                except Exception as e:
                    st.error(f"Error separador: {e}")

                # Excel de Errores
                try:
                    buf_err = io.BytesIO()
                    with pd.ExcelWriter(buf_err, engine='xlsxwriter') as writer:
                        df_dupes.to_excel(writer, index=False, sheet_name="Duplicados")
                    
                    st.download_button(
                        label="📥 Descargar Excel Errores",
                        data=buf_err.getvalue(),
                        file_name="registros_duplicados_error.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
                except: pass

    # 4. DETALLE GENERAL POR COLUMNA
    st.divider()
    st.subheader("🔎 Detalle por Columna (General)")
    
    datos_col = []
    for col in df.columns:
        nulos = df[col].isna().sum()
        unicos = df[col].nunique()
        tipo = str(df[col].dtype)
        sample = df[col].dropna()
        ejemplo = str(sample.iloc[0])[:50] if not sample.empty else "-"
        
        datos_col.append({
            "Columna": col,
            "Tipo": tipo,
            "Nulos": nulos,
            "% Vacío": round((nulos / len(df)) * 100, 1),
            "Valores Únicos": unicos,
            "Ejemplo": ejemplo
        })
    
    df_info = pd.DataFrame(datos_col)
    
    st.dataframe(
        df_info,
        column_config={
            "% Vacío": st.column_config.ProgressColumn(
                "% Vacío",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
        },
        use_container_width=True,
        hide_index=True
    )

    # 5. DESCARGA INFORME COMPLETO
    st.divider()
    st.subheader("💾 Descargar Informe Completo")
    
    if st.button("Generar Excel de Calidad Global"):
        try:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_info.to_excel(writer, sheet_name="Calidad_Columnas", index=False)
                # Si hay duplicados, los metemos también en el informe global
                if dup_ids > 0:
                    df_dupes = df[df[col_id].duplicated(keep=False)].sort_values(by=col_id)
                    df_dupes.to_excel(writer, sheet_name="Errores_IDs_Duplicados", index=False)
                desc = df.describe().transpose().reset_index()
                desc.to_excel(writer, sheet_name="Estadisticas_Numericas", index=False)
                
            st.download_button(
                "📥 Descargar Auditoría .xlsx",
                data=buf.getvalue(),
                file_name=f"auditoria_completa_{st.session_state['nombre_archivo_09']}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
        except Exception as e:
            st.error(f"Error Excel: {e}")