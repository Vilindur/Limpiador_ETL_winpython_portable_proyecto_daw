🧰 LimpiadorLite (Portal de Datos Portable)

Una suite ETL (Extract, Transform, Load) ligera y portable desarrollada en Python y Streamlit.
Diseñada para ejecutarse en entornos locales restringidos (como WinPython en un USB) sin necesidad de instalación ni permisos de administrador.

🛠️ Funcionalidades

1.- La aplicación cuenta con 6 herramientas especializadas:

2.- Limpieza Genérica: Saneamiento de caracteres extraños (BOM, Quotes, Gremlins).

3.- Detective Fuzzy: Detección de duplicados difusos por similitud.

4.- Generador SQL Masivo: Convierte múltiples CSVs en scripts .sql (MySQL).

5.- Consolidador Universal de datos: Flexible para cualquier tipo de archivo csv.

6.- Cruzador (VLOOKUP): Joins entre dos archivos CSV.

7.- Radiografía (Data Profiler): Auditoría de calidad y detección de PK duplicadas.

📦 Instalación y Uso

Requisitos

Python 3.8+

Librerías listadas en requirements.txt

Ejecución

Si tienes un entorno normal:

pip install -r requirements.txt

streamlit run Home.py


Si usas WinPython Portable:

Copia la carpeta del proyecto dentro de tu carpeta de WinPython.

Ejecuta el archivo EJECUTAR.bat.

🔐 Privacidad

Esta herramienta funciona 100% en local. Ningún dato abandona el equipo donde se ejecuta.

📂 Estructura

pages/: Scripts de las herramientas individuales.

core/: Lógica de negocio y librerías compartidas.

archive/: Versiones antiguas de scripts.