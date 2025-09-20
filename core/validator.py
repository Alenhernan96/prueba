# core/validator.py
import os
import pandas as pd
from datetime import datetime, timedelta


class ValidadorReceta:
    """
    Valida los datos extraídos de una receta contra un conjunto de reglas
    definidas en un archivo 'normativas.xlsx'.
    """

    def __init__(self, normativas_path: str):
        self.normativas = self._cargar_normativas(normativas_path)

    def _cargar_normativas(self, excel_path: str):
        print("-> Cargando normativas desde archivo XLSX...")
        try:
            df_os = pd.read_excel(excel_path, sheet_name="OBRAS SOCIALES")
            df_art = pd.read_excel(excel_path, sheet_name="ARTs")
            df_os.rename(columns={df_os.columns[0]: "FINANCIADOR"}, inplace=True)
            df_art.rename(columns={df_art.columns[0]: "FINANCIADOR"}, inplace=True)
            df_total = pd.concat([df_os, df_art], ignore_index=True)

            # Lista completa de columnas de requisitos a limpiar y verificar
            columnas_requisitos = [
                "REQUIERE_MEMBRETE",
                "REQUIERE_FIRMA",
                "REQUIERE_SELLO",
                "REQUIERE_DIAGNOSTICO",
                "REQUIERE_MONODROGA",
                "REQUIERE_AFILIADO",
            ]
            for col in columnas_requisitos:
                if col in df_total.columns:
                    df_total[col] = df_total[col].astype(str).str.strip()

            df_total.drop_duplicates(subset=["FINANCIADOR"], keep="first", inplace=True)
            normativas_dict = (
                df_total.set_index("FINANCIADOR").fillna("NO").to_dict("index")
            )
            print(f"✅ {len(normativas_dict)} normativas cargadas.")
            return normativas_dict
        except Exception as e:
            print(f"⚠️ Error al leer el archivo Excel: {e}.")
            return None

    def validar(self, datos_receta: dict):
        if self.normativas is None:
            return {
                "estado_general": "NO VERIFICADO",
                "observaciones": ["No se pudieron cargar las normativas."],
            }

        raw_financiador = datos_receta.get("Obra Social")
        financiador = raw_financiador.strip() if raw_financiador else ""
        if not financiador:
            return {
                "financiador": "",
                "estado_general": "NO VERIFICADO",
                "observaciones": [
                    "No se encontró el financiador en la receta para validar."
                ],
            }

        posibles_coincidencias = [
            key for key in self.normativas if key.lower() in financiador.lower()
        ]
        reglas_key = None
        if posibles_coincidencias:
            reglas_key = max(posibles_coincidencias, key=len)

        if reglas_key:
            print(
                f"\n[DEBUG] Coincidencia de financiador. Receta: '{financiador}' -> Mejor Clave en Excel: '{reglas_key}'"
            )

        if not reglas_key:
            return {
                "financiador": financiador,
                "estado_general": "NO VERIFICADO",
                "observaciones": [
                    f"No se encontraron normativas para el financiador: '{financiador}'."
                ],
            }

        reglas = self.normativas[reglas_key]
        observaciones, requisitos, encontrados = [], {}, {}

        # --- LÓGICA DE VALIDACIÓN ---

        # 1. Chequeo de Afiliado
        req_afiliado = str(reglas.get("REQUIERE_AFILIADO", "NO")).upper() == "SI"
        requisitos["afiliado"] = req_afiliado
        encontrados["afiliado_presente"] = bool(
            datos_receta.get("Numero de Afiliado")
        ) or bool(datos_receta.get("DNI del Paciente"))
        if req_afiliado and not encontrados["afiliado_presente"]:
            observaciones.append(
                "Normativa exige DNI o N° de Afiliado pero no fue encontrado."
            )

        # 2. Chequeo de Membrete
        req_membrete = str(reglas.get("REQUIERE_MEMBRETE", "NO")).upper() == "SI"
        requisitos["membrete"] = req_membrete
        encontrados["membrete_presente"] = bool(datos_receta.get("Obra Social"))
        if req_membrete and not encontrados["membrete_presente"]:
            observaciones.append("Normativa exige membrete pero no fue identificado.")

        # 3. Chequeo de Sello Médico
        req_sello = str(reglas.get("REQUIERE_SELLO", "NO")).upper() == "SI"
        requisitos["sello"] = req_sello
        encontrados["sello_presente"] = bool(
            datos_receta.get("Matricula del medico")
        ) and bool(datos_receta.get("Firma del medico"))
        if req_sello and not encontrados["sello_presente"]:
            observaciones.append(
                "Normativa exige sello (nombre y matrícula) pero falta información."
            )

        # 4. Chequeo de Monodroga
        req_monodroga = str(reglas.get("REQUIERE_MONODROGA", "NO")).upper() == "SI"
        requisitos["monodroga"] = req_monodroga
        encontrados["monodroga_presente"] = bool(
            datos_receta.get("vademecum_check_exitoso")
        )
        if req_monodroga and not encontrados["monodroga_presente"]:
            observaciones.append(
                "Normativa exige monodroga pero no se pudo verificar ningún producto con el Vademécum."
            )

        # 5. Chequeos Simples
        mapa = {
            "REQUIERE_DIAGNOSTICO": "Diagnostico",
            "REQUIERE_FIRMA": "Firma del medico",
        }
        for col, campo in mapa.items():
            requerido = str(reglas.get(col, "NO")).upper() == "SI"
            requisitos[col.lower().replace("requiere_", "")] = requerido
            presente = bool(datos_receta.get(campo))
            encontrados[f"{campo.lower().replace(' ', '_')}_presente"] = presente
            if requerido and not presente:
                observaciones.append(
                    f"Normativa exige '{campo}' pero no fue encontrado."
                )

        # 6. Chequeo de Validez
        dias_validez_str = str(reglas.get("REQUIERE_VALIDEZ", "0")).replace(".0", "")
        encontrados["fecha_receta"] = datos_receta.get("Fecha")
        if (
            dias_validez_str.isdigit()
            and int(dias_validez_str) > 0
            and encontrados["fecha_receta"]
        ):
            dias_validez = int(dias_validez_str)
            requisitos["validez_dias"] = dias_validez
            try:
                fecha_receta_obj = datetime.strptime(
                    encontrados["fecha_receta"], "%d/%m/%Y"
                )
                if datetime.now() > (fecha_receta_obj + timedelta(days=dias_validez)):
                    encontrados["estado_vencimiento"] = "VENCIDA"
                    observaciones.append(
                        f"La receta está vencida (validez de {dias_validez} días)."
                    )
                else:
                    encontrados["estado_vencimiento"] = "VIGENTE"
            except (ValueError, TypeError):
                encontrados["estado_vencimiento"] = "Error de Formato de Fecha"
        else:
            requisitos["validez_dias"] = dias_validez_str
            encontrados["estado_vencimiento"] = "No se pudo verificar."

        estado_general = "CUMPLE" if not observaciones else "NO CUMPLE"
        return {
            "financiador": financiador,
            "estado_general": estado_general,
            "requisitos_normativa": requisitos,
            "datos_encontrados": encontrados,
            "observaciones": observaciones or ["Sin observaciones."],
        }
