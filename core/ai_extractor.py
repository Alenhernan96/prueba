# core/ai_extractor.py
import google.generativeai as genai
import json
from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold

# Configura tu API Key (idealmente desde una variable de entorno)
API_KEY = "AIzaSyBMd-vJMidDs5QPhUw_H1vS5NCvr9W9frM"
genai.configure(api_key=API_KEY)

# --- ESQUEMAS DE EXTRACCIÓN MODULARES ---
RECETA_SCHEMA = {
    "type": "object",
    "properties": {
        "obra_social": {"type": "string"},
        "numero_afiliado": {"type": "string"},
        "dni_paciente": {"type": "string"},
        "paciente": {"type": "string"},
        "fecha_receta": {"type": "string", "description": "Formato DD/MM/AAAA"},
        "medico_nombre": {"type": "string"},
        "medico_matricula": {"type": "string"},
        "diagnostico": {"type": "string"},
        "productos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "descripcion": {"type": "string"},
                    "cantidad": {"type": "number"},
                },
            },
        },
    },
    "required": ["paciente", "productos"],
}

TICKET_SCHEMA = {
    "type": "object",
    "properties": {
        "fecha_ticket": {
            "type": "string",
            "description": "Prioriza 'FecRec:'. Formato DD/MM/AAAA",
        },
        "numero_afiliado": {"type": "string"},
        "dni_paciente": {"type": "string"},
        "productos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "descripcion": {"type": "string"},
                    "cantidad": {"type": "number"},
                },
            },
        },
    },
}

# --- PROMPT UNIFICADO Y MEJORADO ---
BASE_PROMPT = """
Eres un experto farmacéutico analizando una imagen. Tu tarea es extraer información clave con máxima precisión.

Instrucciones de extracción detalladas:
- **Obra Social**: Es el nombre del financiador (ej: OSDE, IOMA, PAMI, DASMI). A menudo se encuentra cerca del número de afiliado o credencial. Puede ser un nombre propio o un acrónimo. Búscalo activamente en la zona de datos del paciente. Si no lo encuentras, deja el campo nulo.
- **Número de Afiliado/Credencial**: Extrae el número asociado al paciente o a la obra social.
- **Fechas**: Normaliza siempre a formato DD/MM/AAAA. Para el ticket, prioriza la fecha etiquetada como "FecRec:".
- **Productos**: Extrae la lista completa de productos. No omitas ninguno. La cantidad suele estar indicada como "Cantidad: x" o entre paréntesis. Si no se especifica, asume que es 1.
- **Médico**: El nombre y la matrícula (a veces abreviada como M.P. o M.N.) son datos cruciales.
- **Documentos Faltantes**: Si un documento (receta o ticket) no es visible en la imagen, devuelve su objeto correspondiente como `null`.
"""


def extract_all_data_from_image(file_path: str):
    print("-> Usando Extractor Maestro de Gemini AI (Proceso Completo)...")
    prompt = (
        "Analiza la imagen que contiene una RECETA y un TICKET.\n"
        + BASE_PROMPT
        + "Extrae los datos de AMBOS documentos en sus respectivos objetos (`receta`, `ticket`)."
    )
    output_schema = {
        "type": "object",
        "properties": {"receta": RECETA_SCHEMA, "ticket": TICKET_SCHEMA},
    }
    return _call_gemini_model(file_path, prompt, output_schema)


def extract_receta_data_from_image(file_path: str):
    print("-> Usando Extractor de Gemini AI (Solo Receta)...")
    prompt = (
        "Analiza la imagen, ignora por completo cualquier ticket o factura de compra.\n"
        + BASE_PROMPT
        + "Extrae ÚNICAMENTE los datos de la RECETA MÉDICA."
    )
    return _call_gemini_model(file_path, prompt, RECETA_SCHEMA)


# Función base para llamar al modelo
def _call_gemini_model(file_path, prompt, schema):
    if not API_KEY or "TU_API_KEY" in API_KEY:
        raise ValueError("API Key de Google no configurada.")

    sample_file = None
    try:
        sample_file = genai.upload_file(path=file_path, display_name="foto-proceso")
        print(f"✅ Archivo '{sample_file.display_name}' subido.")

        generation_config = genai.GenerationConfig(
            response_mime_type="application/json", response_schema=schema
        )
        model = genai.GenerativeModel(
            "gemini-1.5-flash-latest",
            generation_config=generation_config,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            },
        )
        response = model.generate_content([prompt, sample_file])

        print("✅ Datos extraídos con Gemini.")
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ Error durante la extracción con Gemini: {e}")
        return None
    finally:
        if sample_file:
            genai.delete_file(sample_file.name)
            print(f"-> Archivo temporal '{sample_file.display_name}' eliminado.")
