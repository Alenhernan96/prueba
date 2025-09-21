from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    flash,
    redirect,
    send_from_directory,
)
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
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
from unidecode import unidecode
import subprocess

sys.path.append(".")
from core.ai_extractor import (
    extract_all_data_from_image,
    extract_receta_data_from_image,
)
from core.harvester import DataHarvester
from core.validator import ValidadorReceta
from core.vademecum import VademecumChecker
from core.comparador import comparar_receta_ticket_inteligente

# Cargar variables del archivo .env
load_dotenv()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

app = Flask(__name__)
app.secret_key = "tu_clave_secreta_segura"
# Debajo de app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__name__))
validador = ValidadorReceta(os.path.join(BASE_DIR, "data", "normativas.xlsx"))
vademecum = VademecumChecker(os.path.join(BASE_DIR, "data", "vademecum.xlsx"))

# Crea la carpeta de subidas si no existe
UPLOADS_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_FOLDER, exist_ok=True)
app.config.update(UPLOAD_FOLDER=UPLOADS_FOLDER, MAX_CONTENT_LENGTH=16 * 1024 * 1024)

EMAIL_REMITENTE = os.getenv("EMAIL_REMITENTE")
EMAIL_RECEPTOR = os.getenv("EMAIL_RECEPTOR")
EMAIL_PASS = os.getenv("EMAIL_APP_PASS")

ALLOWED_EXT_TO_MIME = {
    "pdf": ("application", "pdf"),
    "xls": ("application", "vnd.ms-excel"),
    "xlsx": ("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    "doc": ("application", "msword"),
    "docx": (
        "application",
        "vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
}

MAX_ATTACHMENT_BYTES = 16 * 1024 * 1024  # 16 MB

# ========== RUTAS DE PÁGINAS ==========


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/servicios")
def servicios():
    return render_template("servicios.html")


@app.route("/contacto")
def contacto():
    return render_template("contacto.html")


@app.route("/faq")
def faq():
    return render_template("faq.html")


@app.route("/reseñas")
def reseñas():
    return render_template("reseñas.html")


@app.route("/herramientas")
def herramientas():
    return render_template("herramientas.html")


@app.route("/ioma")
def ioma():
    return render_template("ioma.html")


@app.route("/galeno")
def galeno():
    return render_template("galeno.html")


@app.route("/requisitos")
def requisitos():
    return render_template("requerimientos2.html")


@app.route("/prestadores")
def prestadores_page():
    return render_template("prestadores.html", obras=list(OBRAS_ARCHIVOS.keys()))


@app.route("/extractor")
@login_required
def extractor():
    """Muestra la página principal del extractor de recetas."""
    return render_template("extractor.html")


# ========== LÓGICA: CALCULADORA IOMA ==========


@app.route("/calcular-cupon", methods=["POST"])
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
            "CUPÓN 4 (80 a 120 días)",
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
            return jsonify(
                {
                    "fecha": fecha_str,
                    "dias_corridos": dias,
                    "cupon": "❌ No válido – supera los 120 días",
                    "no_validos": [],
                }
            )

        no_validos = [c for c in cupones_ordenados if c != cupon_valido]

        return jsonify(
            {
                "fecha": fecha_str,
                "dias_corridos": dias,
                "cupon": cupon_valido,
                "no_validos": no_validos,
            }
        )

    except ValueError:
        return jsonify({"error": "Fecha inválida. Verificá día, mes y año."}), 400


# ========== LÓGICA: REQUISITOS OBRAS SOCIALES ==========


def normalizar(texto):
    texto = str(texto) if not isinstance(texto, str) else texto
    return (
        unicodedata.normalize("NFKD", texto)
        .encode("ASCII", "ignore")
        .decode()
        .upper()
        .strip()
    )


@app.route("/api/requisitos", methods=["POST"])
def api_requisitos():
    data = request.get_json()
    obra = normalizar(data.get("obra", ""))

    try:
        # Ruta robusta al archivo dentro de webapp/data
        base_dir = os.path.dirname(os.path.abspath(__file__))
        excel_path = os.path.join(
            base_dir, "data", "NORMATIVAS OBRAS SOCIALES v1.01.xlsx"
        )

        df = pd.read_excel(excel_path, sheet_name="OBRAS SOCIALES")
        nombre_columna = [col for col in df.columns if "OBRA SOCIAL" in col.upper()][0]
        df["obra_normalizada"] = df[nombre_columna].apply(normalizar)
        filtro = df[df["obra_normalizada"] == obra]

        if not filtro.empty:
            fila = filtro.iloc[0]
            requisitos = [
                {"norma": col, "valor": fila[col]}
                for col in df.columns[1:]
                if pd.notna(fila[col]) and col != "obra_normalizada"
            ]
            return jsonify({"obra": fila[nombre_columna], "requisitos": requisitos})
        else:
            return jsonify({"error": "Obra social no encontrada"}), 404

    except Exception as e:
        return jsonify({"error": f"Error interno al leer el archivo: {str(e)}"}), 500


@app.route("/api/lista-obras")
def lista_obras():
    try:
        # Ruta absoluta segura al archivo Excel
        base_dir = os.path.dirname(os.path.abspath(__file__))
        excel_path = os.path.join(
            base_dir, "data", "NORMATIVAS OBRAS SOCIALES v1.01.xlsx"
        )

        df = pd.read_excel(excel_path, sheet_name="OBRAS SOCIALES")
        nombre_columna = [col for col in df.columns if "OBRA SOCIAL" in col.upper()][0]
        nombres = df[nombre_columna].dropna().unique().tolist()
        nombres_ordenados = sorted(nombres, key=lambda x: str(x).upper())

        return jsonify(nombres_ordenados)

    except Exception as e:
        return jsonify({"error": f"Error al obtener obras sociales: {str(e)}"}), 500


# ========== ENVÍO DE SUGERENCIAS ==========


@app.route("/enviar-sugerencia", methods=["POST"])
def enviar_sugerencia():
    tipo = request.form.get("tipo")  # "obra_social" o "prestador"
    nombre = request.form.get("nombre")
    email = request.form.get("email")
    obra = request.form.get("obra")
    archivos = request.files.getlist("archivo")  # 👈 varios archivos

    if not all([tipo, nombre, email, obra]):
        flash("Todos los campos obligatorios deben completarse", "danger")
        return redirect(request.referrer or "/")

    try:
        tipo_legible = (
            "Obra Social sugerida" if tipo == "obra_social" else "Prestador sugerido"
        )

        msg = EmailMessage()
        msg["Subject"] = f"Sugerencia nueva - {tipo_legible}: {obra}"
        msg["From"] = EMAIL_REMITENTE
        msg["To"] = EMAIL_RECEPTOR
        msg.set_content(
            f"Tipo: {tipo_legible}\nNombre: {nombre}\nEmail: {email}\nDetalle: {obra}"
        )

        for archivo in archivos:
            if archivo and archivo.filename:
                filename = secure_filename(archivo.filename)
                ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

                if ext in ALLOWED_EXT_TO_MIME:
                    contenido = archivo.read()
                    if len(contenido) > MAX_ATTACHMENT_BYTES:
                        flash(
                            f"El archivo {filename} es demasiado grande (máx. 16 MB).",
                            "warning",
                        )
                        continue
                    maintype, subtype = ALLOWED_EXT_TO_MIME[ext]
                    msg.add_attachment(
                        contenido, maintype=maintype, subtype=subtype, filename=filename
                    )
                else:
                    flash(f"Formato no permitido: {filename}", "warning")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_REMITENTE, EMAIL_PASS)
            smtp.send_message(msg)

        flash("✅ Sugerencia enviada con éxito. ¡Gracias por colaborar!", "success")

    except Exception as e:
        import traceback

        print("[ERROR DE ENVÍO]")
        traceback.print_exc()
        flash(
            "❌ Hubo un problema enviando la sugerencia. Probá de nuevo en unos minutos.",
            "danger",
        )

    return redirect(request.referrer or "/")


@app.route("/procesar", methods=["POST"])
def procesar():
    try:
        archivo = request.files.get("archivo")
        if not archivo:
            flash("❌ Debe subir un archivo .xlsx", "danger")
            return redirect("/galeno")

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
        with zipfile.ZipFile(zip_temp_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(carpeta_resultados):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, carpeta_resultados)
                    zipf.write(file_path, arcname)

        return render_template("galeno.html", archivo_zip=zip_filename)

    except Exception as e:
        print("[ERROR AL PROCESAR GALENO]", e)
        flash(
            "❌ Error procesando el archivo. Verificá que sea el formato correcto.",
            "danger",
        )
        return redirect("/galeno")


@app.route("/descarga-temporal/<path:filename>")
def descarga_temporal(filename):
    ruta = os.path.join("/tmp", filename)
    if not os.path.isfile(ruta):
        return "❌ Archivo temporal no encontrado", 404
    return send_from_directory("/tmp", filename, as_attachment=True)


@app.route("/descargas/<path:filename>")
def descargar_galeno(filename):
    carpeta_descargas = os.path.join("static", "descargas")

    # Asegurarse de que la carpeta exista
    if not os.path.exists(carpeta_descargas):
        os.makedirs(carpeta_descargas)

    # Verificar si el archivo realmente existe antes de enviarlo
    ruta_archivo = os.path.join(carpeta_descargas, filename)
    if not os.path.isfile(ruta_archivo):
        return "❌ Archivo no disponible para descarga", 404

    # Enviar el archivo como descarga
    return send_from_directory(carpeta_descargas, filename, as_attachment=True)


@app.post("/api/contacto")
def api_contacto():
    nombre = (request.form.get("nombre") or "").strip()
    email = (request.form.get("email") or "").strip()
    mensaje = (request.form.get("mensaje") or "").strip()

    if not (nombre and email and mensaje):
        return jsonify(ok=False, error="Completá todos los campos."), 400

    try:
        msg = EmailMessage()
        msg["Subject"] = f"Nuevo mensaje de contacto – {nombre}"
        msg["From"] = EMAIL_REMITENTE
        msg["To"] = EMAIL_RECEPTOR
        msg.set_content(f"Nombre: {nombre}\nEmail: {email}\n\nMensaje:\n{mensaje}")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_REMITENTE, EMAIL_PASS)
            smtp.send_message(msg)

        return jsonify(ok=True)
    except Exception as e:
        print("[ERROR CONTACTO]", e)
        return jsonify(ok=False, error="No se pudo enviar el mensaje."), 500


# ========== BUSCADOR DE PRESTADORES (3 TXT + 1 XLS) ==========

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

OBRAS_ARCHIVOS = {
    "Assistencial Salud": os.path.join(
        DATA_DIR, "ASSISTENCIAL SALUD - PRESTADORES.txt"
    ),
    "OSMEDICA": os.path.join(DATA_DIR, "OSMEDICA -PRESTADORES.txt"),
    "OSPIT (Tabaco)": os.path.join(DATA_DIR, "TABACO -PRESTADORES.txt"),
    "Unión Personal": os.path.join(DATA_DIR, "UNION PERSONAL - PRESTADORES.xls"),
}


def _doc_to_text(path_txt):
    # Acá leemos directamente el .txt ya convertido (UTF-8)
    with open(path_txt, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _clean_lines(txt):
    # Limpieza básica de líneas
    return [re.sub(r"\s+", " ", l).strip() for l in txt.splitlines() if l and l.strip()]


# ---- Parsers mínimos por obra ----
def parse_assistencial(path_txt):
    txt = _doc_to_text(path_txt)
    lines = _clean_lines(txt)
    zona = ""
    rows = []
    for l in lines:
        up = l.upper()
        if re.fullmatch(
            r"(CAPITAL(\s+FEDERAL)?|ZONA\s+SUR|ZONA\s+OESTE|ZONA\s+NORTE)", up
        ):
            zona = up.replace("CAPITAL FEDERAL", "CAPITAL").strip()
            continue
        if any(
            k in up
            for k in [
                "CARTILLA DE PRESTADORES",
                "VIGENCIA",
                "ASSISTENCIAL",
                "OBRA SOCIAL",
            ]
        ):
            continue
        if len(l) >= 3:
            rows.append({"prestador": l, "zona": zona})
    return pd.DataFrame(rows)


def parse_osmedica(path_txt):
    txt = _doc_to_text(path_txt)
    lines = _clean_lines(txt)
    zona = ""
    rows = []
    for l in lines:
        up = l.upper()
        if re.fullmatch(
            r"(PRESTADORES?\s+CABA|CABA|ZONA\s+NORTE|ZONA\s+SUR|ZONA\s+OESTE|ZONA\s+NOROESTE|PRESTADORES?\s+ZONA\s+\w+)",
            up,
        ):
            zona = re.sub(r"PRESTADORES?\s+", "", up).strip()
            continue
        if any(
            k in up
            for k in ["CARTILLA DE PRESTADORES", "VIGENCIA", "FEDERACION MEDICA"]
        ):
            continue
        m = re.search(r"\b(MN|MP)\s*[\-–:]?\s*(\d{4,6})\b", l, flags=re.I)
        matricula = m.group(2) if m else ""
        rows.append({"prestador": l, "zona": zona, "matricula": matricula})
    return pd.DataFrame(rows)


def parse_tabaco(path_txt):
    txt = _doc_to_text(path_txt)
    lines = _clean_lines(txt)
    tipo = ""
    rows = []
    for l in lines:
        up = l.upper()
        if up == "ENTIDADES":
            tipo = "Entidad"
            continue
        if up == "PROFESIONALES":
            tipo = "Profesional"
            continue
        if any(
            k in up
            for k in [
                "CARTILLA DE PRESTADORES",
                "VIGENCIA",
                "O.S.P.I.T",
                "OSPIT",
                "OBRA SOCIAL",
            ]
        ):
            continue
        if len(l) >= 3:
            rows.append({"prestador": l, "especialidad": tipo})
    return pd.DataFrame(rows)


def _norm_col(col):
    s = unidecode(str(col or ""))
    s = re.sub(r"\s+", " ", s)  # colapsa espacios (incluye NBSP)
    s = s.strip().lower()
    s = re.sub(r"[^\w]+", "", s)  # deja solo [a-z0-9_]
    return s


def read_union_personal_xls(path_xls):
    df = pd.read_excel(path_xls)

    # 1) normalizo nombres → k
    norm_map = {c: _norm_col(c) for c in df.columns}

    # 2) candidatos
    cand_prest = [c for c, k in norm_map.items() if ("prest" in k or "nombre" in k)]
    cand_matric = [
        c for c, k in norm_map.items() if ("matric" in k and "tipo" not in k)
    ]
    col_tipo_matric = next(
        (c for c, k in norm_map.items() if "tipo" in k and "matric" in k), None
    )

    # 3) elegir mejor columna de matrícula (la que tenga más dígitos)
    def score_digits(series):
        s = series.astype(str).str.findall(r"\d").str.len().fillna(0)
        return int(s.sum())

    if cand_matric:
        scores = {c: score_digits(df[c]) for c in cand_matric}
        col_matric = max(scores, key=scores.get)
    else:
        col_matric = None  # no encontrada; la dejaremos vacía

    # 4) construir dataframe con nombres amigables
    out = pd.DataFrame()

    # prestador
    if cand_prest:
        out["prestador"] = df[cand_prest[0]]
    else:
        # si no hay, intenta una genérica
        out["prestador"] = df.iloc[:, 0].astype(str)

    # matrícula numérica (si existe)
    if col_matric:
        out["matricula"] = df[col_matric]
    else:
        out["matricula"] = ""

    # extras comunes
    # (estos mapeos son best-effort; si no están, quedan vacíos)
    def pick_one(substrs):
        for c, k in norm_map.items():
            if any(s in k for s in substrs):
                return c
        return None

    col_espec = pick_one(["espec"])
    col_dir = pick_one(["direc", "domic"])
    col_loc = pick_one(["local", "ciud", "partido"])
    col_zona = pick_one(["zona", "regi"])
    col_obs = pick_one(["observ", "nota"])

    out["especialidad"] = df[col_espec] if col_espec else ""
    out["direccion"] = df[col_dir] if col_dir else ""
    out["localidad"] = df[col_loc] if col_loc else ""
    out["zona"] = df[col_zona] if col_zona else ""
    out["observaciones"] = df[col_obs] if col_obs else ""

    # opcional: conservar el "tipo matricula" por si lo querés mostrar luego
    if col_tipo_matric:
        out["observaciones"] = out["observaciones"].astype(str) + out[
            "observaciones"
        ].mask(out["observaciones"].astype(str).str.strip() == "", "").astype(str).radd(
            ""
        )  # no duplica, pero lo podés unir distinto
        # o guardar en otra columna si querés:
        # out["tipo_matricula"] = df[col_tipo_matric]

    # limpiar filas totalmente vacías
    out = out.dropna(how="all")

    return out


def _norm_text(x):
    from unidecode import unidecode

    return unidecode(str(x or "")).upper()


def _first_series(df, col):
    """Devuelve una Series para 'col'. Si hay varias columnas con ese nombre, usa la primera."""
    obj = df[col]
    if isinstance(obj, pd.DataFrame):
        # tomá la 1ra columna; si querés, podés combinar, pero con la 1ra alcanza
        return obj.iloc[:, 0]
    return obj


def _to_index(df, obra):
    # columnas estándar
    cols = [
        "prestador",
        "matricula",
        "especialidad",
        "direccion",
        "localidad",
        "zona",
        "observaciones",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = ""

    # Si hay duplicadas, uso la primera
    def _first_series(obj):
        return obj.iloc[:, 0] if isinstance(obj, pd.DataFrame) else obj

    base = pd.DataFrame({c: _first_series(df[c]) for c in cols}).fillna("")

    base["obra_social"] = obra

    from unidecode import unidecode

    def norm_text(x):
        return unidecode(str(x or "")).upper()

    # Blob normalizado para texto
    base["__blob__"] = (
        base["prestador"].map(norm_text)
        + " | "
        + base["matricula"].map(norm_text)
        + " | "
        + base["especialidad"].map(norm_text)
        + " | "
        + base["direccion"].map(norm_text)
        + " | "
        + base["localidad"].map(norm_text)
        + " | "
        + base["zona"].map(norm_text)
        + " | "
        + base["observaciones"].map(norm_text)
    )

    # __mat_num__: matrícula limpia (quita .0 y no dígitos)
    mat_str = base["matricula"].astype(str).str.replace(r"\.0$", "", regex=True)
    base["__mat_num__"] = mat_str.str.replace(r"\D", "", regex=True)

    # __nums_all__: TODAS las secuencias de dígitos presentes en el registro (cualquier columna)
    # 1) concateno todas las columnas originales a texto (sin normalizar)
    df_txt = df.fillna("").astype(str)
    concat_all = df_txt.apply(lambda r: " | ".join(r.values), axis=1)

    # 2) extraigo todas las secuencias numéricas y las uno con espacios (ej: "12345 6789")
    base["__nums_all__"] = concat_all.str.findall(r"\d+").str.join(" ")

    return base


def _load_all():
    data = {}
    for obra, path in OBRAS_ARCHIVOS.items():
        if not os.path.exists(path):
            print(f"⚠️ No se encontró {path}")
            continue
        if obra == "Assistencial Salud":
            df = parse_assistencial(path)
        elif obra == "OSMEDICA":
            df = parse_osmedica(path)
        elif obra == "OSPIT (Tabaco)":
            df = parse_tabaco(path)
        else:  # Unión Personal (.xls)
            df = read_union_personal_xls(path)
        data[obra] = _to_index(df, obra)
    return data


DATA_PRESTADORES = _load_all()


def _tokens(q):
    return [t for t in _norm_text(q).split() if t]


@app.get("/api/prestadores")
def api_prestadores():
    obra = request.args.get("obra", "")
    q = (request.args.get("q") or "").strip()
    if obra not in DATA_PRESTADORES:
        return jsonify({"total": 0, "items": []})
    df = DATA_PRESTADORES[obra]

    qd = re.sub(r"\D", "", q)
    if qd and len(qd) >= 3:  # desde 3 dígitos
        # Busca en matrícula limpia y en todas las secuencias numéricas del registro
        mask = df["__mat_num__"].str.contains(qd, na=False) | df[
            "__nums_all__"
        ].str.contains(qd, na=False)
        res = df[mask]
        if res.empty:
            # fallback textual (por si el número está pegado a letras raras)
            res = df[df["__blob__"].str.contains(re.escape(qd), na=False)]
    else:
        toks = [t for t in _norm_text(q).split() if t]
        mask = pd.Series([True] * len(df))
        for t in toks:
            mask &= df["__blob__"].str.contains(re.escape(t), na=False)
        res = df[mask] if toks else df.iloc[0:0]

    cols_out = [
        "obra_social",
        "prestador",
        "matricula",
        "especialidad",
        "direccion",
        "localidad",
        "zona",
        "observaciones",
    ]
    items = res[cols_out].head(500).fillna("").to_dict(orient="records")
    return jsonify({"total": int(res.shape[0]), "items": items})


@app.route("/extract", methods=["POST"])
def handle_extraction():
    """Maneja la lógica de extracción de la imagen subida."""
    proceso = request.form.get("proceso", "normativa")
    if "documento_completo" not in request.files:
        return jsonify({"error": "No se encontró el archivo"}), 400

    file = request.files["documento_completo"]
    if not file.filename:
        return jsonify({"error": "No se seleccionó archivo"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        datos_receta = None
        datos_ticket = None
        barcodes = []
        validacion_normativa = None
        verificacion_vademecum = []
        comparacion_ticket = None

        print(f"\n🚀 Iniciando proceso: '{proceso.upper()}'")

        if proceso == "full":
            all_data = extract_all_data_from_image(filepath)
            if not all_data:
                raise Exception("Gemini no pudo procesar la imagen.")
            datos_receta = all_data.get("receta")
            datos_ticket = all_data.get("ticket")
        else:
            datos_receta = extract_receta_data_from_image(filepath)
            if not datos_receta:
                raise Exception("Gemini no pudo procesar la receta.")

        if proceso in ["vademecum", "full"]:
            barcodes = DataHarvester().get_barcode_data(filepath)
            medicament_barcodes = [code for code in barcodes if code.startswith("77")]
            print(
                f"-> [Server] Se filtraron {len(medicament_barcodes)} códigos de medicamentos (inician con '77')."
            )
            if vademecum.df is not None and medicament_barcodes:
                for code in medicament_barcodes:
                    check = vademecum.check_code(code)
                    verificacion_vademecum.append(
                        {
                            "codigo": code,
                            "estado": "ENCONTRADO" if check else "NO ENCONTRADO",
                            "datos": check,
                        }
                    )

        if datos_receta:
            vademecum_check_exitoso = any(
                v.get("estado") == "ENCONTRADO" for v in verificacion_vademecum
            )
            if (
                not vademecum_check_exitoso
                and vademecum.df is not None
                and datos_receta.get("productos")
            ):
                print(
                    "-> Chequeo por troqueles fallido o no realizado. Usando fallback de texto para monodroga..."
                )
                monodrogas_conocidas = (
                    vademecum.df["MONODROGA"].dropna().str.lower().unique()
                )
                for producto_recetado in datos_receta["productos"]:
                    descripcion = producto_recetado.get("descripcion", "").lower()
                    if any(m in descripcion for m in monodrogas_conocidas if m):
                        print(f"✅ Monodroga encontrada por texto en: '{descripcion}'")
                        vademecum_check_exitoso = True
                        break

            datos_para_validar = {
                "Obra Social": datos_receta.get("obra_social"),
                "Fecha": datos_receta.get("fecha_receta"),
                "Diagnostico": datos_receta.get("diagnostico"),
                "Firma del medico": datos_receta.get("medico_nombre"),
                "Matricula del medico": datos_receta.get("medico_matricula"),
                "Numero de Afiliado": datos_receta.get("numero_afiliado"),
                "DNI del Paciente": datos_receta.get("dni_paciente"),
                "vademecum_check_exitoso": vademecum_check_exitoso,
            }
            validacion_normativa = validador.validar(datos_para_validar)

        if proceso == "full" and datos_receta and datos_ticket:
            comparacion_ticket = comparar_receta_ticket_inteligente(
                datos_receta, datos_ticket, vademecum
            )

        return jsonify(
            {
                "datos_extraidos_ia": datos_receta,
                "datos_extraidos_ticket": datos_ticket,
                "codigos_barra_detectados": barcodes,
                "validacion_normativa": validacion_normativa,
                "verificacion_vademecum": verificacion_vademecum,
                "comparacion_con_ticket": comparacion_ticket,
            }
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"Error en el servidor: {str(e)}"}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


# --- RUTAS DE LOGIN Y LOGOUT (MODIFICADAS) ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Comparamos directamente con las variables de entorno
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            user = User(id="1")  # Creamos nuestro usuario genérico
            login_user(user)
            return redirect(url_for("herramientas"))
        else:
            flash("Usuario o contraseña incorrectos.", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


# Creamos una clase de Usuario simple, solo para la sesión
class User(UserMixin):
    def __init__(self, id):
        self.id = id


# Función para cargar el usuario. Como solo hay uno, es muy simple.
@login_manager.user_loader
def load_user(user_id):
    if user_id == "1":
        return User(user_id)
    return None


# ========== EJECUCIÓN ==========

if __name__ == "__main__":
    app.run(debug=True)
