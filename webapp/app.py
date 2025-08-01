from flask import Flask, render_template, request, jsonify, flash, redirect, send_from_directory
from datetime import datetime, date
import pandas as pd
import unicodedata
import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv
import zipfile
import shutil
from werkzeug.utils import secure_filename
import re
import sys
sys.path.append(".")

# Cargar variables del archivo .env
load_dotenv()

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_segura'

EMAIL_REMITENTE = os.getenv("EMAIL_REMITENTE")
EMAIL_RECEPTOR = os.getenv("EMAIL_RECEPTOR")
EMAIL_PASS = os.getenv("EMAIL_APP_PASS")

# ========== RUTAS DE PÁGINAS ==========

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/servicios')
def servicios():
    return render_template('servicios.html')

@app.route('/contacto')
def contacto():
    return render_template('contacto.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/reseñas')
def reseñas():
    return render_template('reseñas.html')

@app.route('/herramientas')
def herramientas():
    return render_template("herramientas.html")

@app.route('/ioma')
def ioma():
    return render_template("ioma.html")

@app.route('/requisitos')
def requisitos():
    return render_template("requerimientos.html")

@app.route('/galeno')
def galeno():
    return render_template("galeno.html")

# ========== LÓGICA: CALCULADORA IOMA ==========

@app.route('/calcular-cupon', methods=['POST'])
def calcular():
    data = request.get_json()
    dia = data.get("dia", "").zfill(2)
    mes = data.get("mes", "").zfill(2)
    anio = data.get("anio", "").strip()

    if not anio.isdigit() or len(anio) != 4:
        return jsonify({"error": "Ingresá un año válido de 4 dígitos."}), 400

    try:
        fecha = datetime.strptime(f"{dia}/{mes}/{anio}", "%d/%m/%Y").date()
        hoy = date.today()
        dias = (hoy - fecha).days + 1

        if dias <= 0:
            return jsonify({"error": "La fecha es posterior a hoy."}), 400

        fecha_str = fecha.strftime("%d/%m/%Y")
        cupones_ordenados = [
            "CUPÓN 1 (0 a 30 días)",
            "CUPÓN 2 (20 a 60 días)",
            "CUPÓN 3 (50 a 90 días)",
            "CUPÓN 4 (80 a 120 días)"
        ]

        if dias <= 30:
            cupon_valido = cupones_ordenados[0]
        elif dias > 20 and dias <= 60:
            cupon_valido = cupones_ordenados[1]
        elif dias > 50 and dias <= 90:
            cupon_valido = cupones_ordenados[2]
        elif dias > 80 and dias <= 120:
            cupon_valido = cupones_ordenados[3]
        else:
            return jsonify({
                "fecha": fecha_str,
                "dias_corridos": dias,
                "cupon": "❌ No válido – supera los 120 días",
                "no_validos": []
            })

        no_validos = [c for c in cupones_ordenados if c != cupon_valido]

        return jsonify({
            "fecha": fecha_str,
            "dias_corridos": dias,
            "cupon": cupon_valido,
            "no_validos": no_validos
        })

    except ValueError:
        return jsonify({"error": "Fecha inválida. Verificá día, mes y año."}), 400

# ========== LÓGICA: REQUISITOS OBRAS SOCIALES ==========

def normalizar(texto):
    texto = str(texto) if not isinstance(texto, str) else texto
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode().upper().strip()

@app.route('/api/requisitos', methods=['POST'])
def api_requisitos():
    data = request.get_json()
    obra = normalizar(data.get("obra", ""))

    try:
        # Ruta robusta al archivo dentro de webapp/data
        base_dir = os.path.dirname(os.path.abspath(__file__))
        excel_path = os.path.join(base_dir, 'data', 'NORMATIVAS OBRAS SOCIALES v1.01.xlsx')

        df = pd.read_excel(excel_path, sheet_name="OBRAS SOCIALES")
        nombre_columna = [col for col in df.columns if "OBRA SOCIAL" in col.upper()][0]
        df['obra_normalizada'] = df[nombre_columna].apply(normalizar)
        filtro = df[df['obra_normalizada'] == obra]

        if not filtro.empty:
            fila = filtro.iloc[0]
            requisitos = [
                {"norma": col, "valor": fila[col]}
                for col in df.columns[1:] if pd.notna(fila[col]) and col != 'obra_normalizada'
            ]
            return jsonify({"obra": fila[nombre_columna], "requisitos": requisitos})
        else:
            return jsonify({"error": "Obra social no encontrada"}), 404

    except Exception as e:
        return jsonify({"error": f"Error interno al leer el archivo: {str(e)}"}), 500

@app.route('/api/lista-obras')
def lista_obras():
    try:
        # Ruta absoluta segura al archivo Excel
        base_dir = os.path.dirname(os.path.abspath(__file__))
        excel_path = os.path.join(base_dir, 'data', 'NORMATIVAS OBRAS SOCIALES v1.01.xlsx')

        df = pd.read_excel(excel_path, sheet_name="OBRAS SOCIALES")
        nombre_columna = [col for col in df.columns if "OBRA SOCIAL" in col.upper()][0]
        nombres = df[nombre_columna].dropna().unique().tolist()
        nombres_ordenados = sorted(nombres, key=lambda x: str(x).upper())

        return jsonify(nombres_ordenados)

    except Exception as e:
        return jsonify({"error": f"Error al obtener obras sociales: {str(e)}"}), 500

# ========== ENVÍO DE SUGERENCIAS ==========

@app.route('/enviar-sugerencia', methods=['POST'])
def enviar_sugerencia():
    nombre = request.form.get("nombre")
    email = request.form.get("email")
    obra = request.form.get("obra")
    archivo = request.files.get("archivo")

    if not all([nombre, email, obra]):
        flash("Todos los campos obligatorios deben completarse", "danger")
        return redirect("/requisitos")

    try:
        msg = EmailMessage()
        msg['Subject'] = f"Sugerencia nueva - {obra}"
        msg['From'] = EMAIL_REMITENTE
        msg['To'] = EMAIL_RECEPTOR
        msg.set_content(f"Nombre: {nombre}\nEmail: {email}\nObra sugerida: {obra}")

        if archivo and archivo.filename.endswith(".pdf"):
            contenido = archivo.read()
            msg.add_attachment(contenido, maintype='application', subtype='pdf', filename=archivo.filename)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_REMITENTE, EMAIL_PASS)
            smtp.send_message(msg)

        flash("✅ Sugerencia enviada con éxito. ¡Gracias por colaborar!", "success")
    except Exception as e:
        import traceback
        print("[ERROR DE ENVÍO]")
        traceback.print_exc()

    return redirect("/requisitos")

@app.route('/procesar', methods=['POST'])
def procesar():
    try:
        archivo = request.files.get('archivo')
        if not archivo:
            flash("❌ Debe subir un archivo .xlsx", "danger")
            return redirect('/galeno')

        nombre_archivo = secure_filename(archivo.filename)
        ruta_input = os.path.join("/tmp", nombre_archivo)
        archivo.save(ruta_input)

        from galeno import procesar_galeno
        carpeta_resultados = procesar_galeno(ruta_input)

        # Extraer fecha para nombrar el ZIP
        match = re.search(r"(\d{2}-\d{2}-\d{4})", nombre_archivo)
        fecha = match.group(1) if match else datetime.now().strftime("%Y-%m-%d")
        zip_filename = f"{fecha}.zip"
        zip_temp_path = os.path.join("/tmp", zip_filename)

        # Comprimir resultados en /tmp
        with zipfile.ZipFile(zip_temp_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(carpeta_resultados):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, carpeta_resultados)
                    zipf.write(file_path, arcname)

        return render_template("galeno.html", archivo_zip=zip_filename)

    except Exception as e:
        print("[ERROR AL PROCESAR GALENO]", e)
        flash("❌ Error procesando el archivo. Verificá que sea el formato correcto.", "danger")
        return redirect('/galeno')

@app.route('/descarga-temporal/<path:filename>')
def descarga_temporal(filename):
    ruta = os.path.join('/tmp', filename)
    if not os.path.isfile(ruta):
        return "❌ Archivo temporal no encontrado", 404
    return send_from_directory('/tmp', filename, as_attachment=True)

@app.route('/descargas/<path:filename>')
def descargar_galeno(filename):
    carpeta_descargas = os.path.join('static', 'descargas')

    # Asegurarse de que la carpeta exista
    if not os.path.exists(carpeta_descargas):
        os.makedirs(carpeta_descargas)

    # Verificar si el archivo realmente existe antes de enviarlo
    ruta_archivo = os.path.join(carpeta_descargas, filename)
    if not os.path.isfile(ruta_archivo):
        return "❌ Archivo no disponible para descarga", 404

    # Enviar el archivo como descarga
    return send_from_directory(carpeta_descargas, filename, as_attachment=True)

# ========== EJECUCIÓN ==========

if __name__ == '__main__':
    app.run(debug=True)