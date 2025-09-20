# core/harvester.py
from pdf2image import convert_from_path
from PIL import Image
from pyzbar import pyzbar


class DataHarvester:
    """
    Encapsula la lógica para extraer únicamente códigos de barras de los archivos.
    """

    def get_barcode_data(self, file_path: str) -> list[str]:
        """
        Detecta y decodifica códigos de barras de un archivo de imagen o PDF.
        """
        print("-> Buscando códigos de barras en el archivo...")
        try:
            image = (
                convert_from_path(file_path, first_page=1, last_page=1)[0]
                if file_path.lower().endswith(".pdf")
                else Image.open(file_path)
            )
            barcodes = pyzbar.decode(image)
            found_codes = []
            types = ["EAN13", "EAN8", "UPCA", "UPCE", "CODE128"]
            for barcode in barcodes:
                if barcode.type in types:
                    data = barcode.data.decode("utf-8")
                    print(
                        f"✅ Código de barras de producto encontrado ({barcode.type}): {data}"
                    )
                    found_codes.append(data)
            if not found_codes:
                print("⚠️ No se encontraron códigos de barras de PRODUCTO.")
            return found_codes
        except Exception as e:
            print(f"⚠️  Error al leer códigos de barras: {e}")
            return []
