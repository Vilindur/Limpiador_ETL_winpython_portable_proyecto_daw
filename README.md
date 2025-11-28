🧰 LimpiadorLite (Portal de Datos Portable)

Una suite ETL (Extract, Transform, Load) ligera y portable desarrollada en Python y Streamlit.
Diseñada para ejecutarse en entornos locales restringidos (como WinPython en un USB) sin necesidad de instalación ni permisos de administrador.

IMPORTANTE: Esto es un proyecto simple y dedicado a ser un TFGS. Cabe destacar que me he apoyado en la IA y que no es una aplicación perfecta y tiene mucho margen de mejora. Simplemente es un proyecto escalable que tengo intención de implementar via web también. Gracias por usarlo. ¡Saludos!

Todo feedback es bienvenido :D

------------------------------------------------------------------------------------------------------

🛠️ Funcionalidades

La aplicación cuenta con 6 herramientas especializadas:

1.- Limpieza Genérica: Saneamiento de caracteres extraños (BOM, Quotes, Gremlins).

2.- Detective Fuzzy: Detección de duplicados difusos por similitud.

3.- Generador SQL Masivo: Convierte múltiples CSVs en scripts .sql (MySQL).

4.- Consolidador Universal de datos: Flexible para cualquier tipo de archivo csv.

5.- Cruzador (VLOOKUP): Joins entre dos archivos CSV.

6.- Radiografía (Data Profiler): Auditoría de calidad y detección de PK duplicadas.

------------------------------------------------------------------------------------------------------

📦 Instalación y Uso

Requisitos

Python 3.8+

Librerías listadas en requirements.txt

Ejecución

Si tienes un entorno normal:

pip install -r requirements.txt

streamlit run Home.py

------------------------------------------------------------------------------------------------------

Cómo ejecutar si usas WinPython Portable o en mi caso WinPythonDot:

------------------------------------------------------------------------------------------------------

Copia la carpeta del proyecto dentro de tu carpeta de WinPython/Dot.

Ejecuta el archivo EJECUTAR.bat en comando o doble clic.

Esperas a que aparezca la URL local, la copias en el navegador, ENTER y listo para usar.

------------------------------------------------------------------------------------------------------

🔐 Privacidad

Esta herramienta funciona 100% en local. Ningún dato abandona el equipo donde se ejecuta.

------------------------------------------------------------------------------------------------------

📂 Estructura

pages/: Scripts de las herramientas individuales.

core/: Lógica de negocio y librerías compartidas.

archive/: Versiones antiguas de scripts.

------------------------------------------------------------------------------------------------------