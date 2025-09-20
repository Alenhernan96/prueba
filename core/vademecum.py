# core/vademecum.py
import os
import pandas as pd
import re


def clean_text_advanced(text):
    """Limpia texto para comparación: minúsculas, sin acentos, sin puntuación, etc."""
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    # Reemplazar acentos
    accents = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u"}
    for accent, char in accents.items():
        text = text.replace(accent, char)
    # Eliminar puntuación y caracteres no alfanuméricos (excepto +)
    text = re.sub(r"[^\w\s+]", "", text)
    # Eliminar palabras comunes sin valor (unidades, etc.)
    common_words = ["mg", "gr", "comp", "comprimidos", "cap", "capsulas", "ml", "x"]
    words = text.split()
    words = [word for word in words if not word.isdigit() and word not in common_words]
    return " ".join(words)


class VademecumChecker:
    def __init__(self, file_path: str):
        self.df = self._load_vademecum(file_path)

    def _load_vademecum(self, file_path: str):
        if not (file_path and os.path.exists(file_path)):
            print("⚠️ Archivo de Vademécum no encontrado o no proporcionado.")
            return None
        try:
            print("-> Cargando y pre-procesando Vademécum...")
            df = pd.read_excel(file_path, dtype={"CODIGO": str})
            # Pre-procesamiento para búsquedas eficientes
            df.dropna(subset=["DESCRIPCION", "MONODROGA"], inplace=True)
            df["DESCRIPCION_LIMPIA"] = df["DESCRIPCION"].apply(clean_text_advanced)
            df["MONODROGA_LIMPIA"] = df["MONODROGA"].apply(clean_text_advanced)
            df["MARCA_LIMPIA"] = df["DESCRIPCION_LIMPIA"].apply(
                lambda x: x.split()[0] if x else None
            )
            print("✅ Vademécum cargado y procesado.")
            return df
        except Exception as e:
            print(f"⚠️ Error al cargar Vademécum: {e}")
            return None

    def check_code(self, barcode: str) -> dict | None:
        if self.df is None or barcode is None:
            return None
        match = self.df[self.df["CODIGO"] == barcode]
        return match.iloc[0].to_dict() if not match.empty else None

    def get_product_identities(self, product_name: str) -> set:
        """Devuelve un conjunto de identidades (marca, monodrogas) para un producto."""
        if self.df is None or not product_name:
            return set()

        cleaned_name = clean_text_advanced(product_name)
        cleaned_brand = cleaned_name.split()[0] if cleaned_name else ""

        identities = {cleaned_brand}

        # Buscar por coincidencia de marca
        matches = self.df[self.df["MARCA_LIMPIA"] == cleaned_brand]

        if not matches.empty:
            for _, row in matches.iterrows():
                monodrogas = row["MONODROGA_LIMPIA"].split("+")
                for md in monodrogas:
                    identities.add(md.strip())
        else:
            # Si no hay match por marca, buscar por monodroga
            for _, row in self.df.iterrows():
                if cleaned_name in row["MONODROGA_LIMPIA"]:
                    identities.add(row["MARCA_LIMPIA"])
                    monodrogas = row["MONODROGA_LIMPIA"].split("+")
                    for md in monodrogas:
                        identities.add(md.strip())

        return {id for id in identities if id}  # Eliminar posibles vacíos
