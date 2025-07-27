import os
import pandas as pd
import re
import openpyxl

def ajustar_columnas(path_archivo):
    wb = openpyxl.load_workbook(path_archivo)
    ws = wb.active
    for columna in ws.columns:
        max_length = 0
        columna_letra = columna[0].column_letter
        for celda in columna:
            if celda.value:
                max_length = max(max_length, len(str(celda.value)))
        ws.column_dimensions[columna_letra].width = max_length + 2
    wb.save(path_archivo)

def procesar_galeno(ruta_excel, carpeta_salida_base):
    nombre_archivo = os.path.basename(ruta_excel)
    match = re.search(r"(\d{2}-\d{2}-\d{4})", nombre_archivo)
    carpeta_base = f"Resultados {match.group(1)}" if match else "Resultados"
    carpeta_base_path = os.path.join(carpeta_salida_base, carpeta_base)
    carpeta_bajas_path = os.path.join(carpeta_base_path, "Bajas")
    os.makedirs(carpeta_base_path, exist_ok=True)
    os.makedirs(carpeta_bajas_path, exist_ok=True)

    columnas = ['AFILIADO', 'MONODROGA', 'DOSIS DIARIA', 'INICIO', 'FIN', 'DENOMINACION COMERCIAL', 'AUTORIZACION']
    df = pd.read_excel(ruta_excel)

    # Separar bajas y activos
    df_bajas = df[df['INICIO'].astype(str).str.lower().str.contains("baja", na=False)]
    df_activos = df[~df['INICIO'].astype(str).str.lower().str.contains("baja", na=False)].copy()

    df_activos['INICIO'] = pd.to_datetime(df_activos['INICIO'].astype(str), format="%Y%m%d", errors='coerce').dt.strftime('%d/%m/%Y')
    df_activos['FIN'] = pd.to_datetime(df_activos['FIN'].astype(str), format="%Y%m%d", errors='coerce').dt.strftime('%d/%m/%Y')

    for afiliado, grupo in df_activos.groupby('AFILIADO'):
        nombre = str(afiliado).replace('/', '_').replace('\\', '_')
        path_salida = os.path.join(carpeta_base_path, f"{nombre}.xlsx")
        grupo[columnas].to_excel(path_salida, index=False)
        ajustar_columnas(path_salida)

    for afiliado, grupo in df_bajas.groupby('AFILIADO'):
        nombre = str(afiliado).replace('/', '_').replace('\\', '_')
        path_salida = os.path.join(carpeta_bajas_path, f"{nombre}.xlsx")
        grupo[columnas].to_excel(path_salida, index=False)
        ajustar_columnas(path_salida)

    return carpeta_base_path
