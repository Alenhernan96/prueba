# core/comparador.py
from .vademecum import clean_text_advanced  # Importamos la función de limpieza


def comparar_receta_ticket_inteligente(
    datos_receta: dict, datos_ticket: dict, vademecum
):
    """
    Compara de forma inteligente los datos de una receta y un ticket,
    utilizando el vademécum como puente para relacionar productos.
    """
    observaciones = []

    # 1. Comparación de Paciente (DNI o Nro. Afiliado de forma flexible)
    receta_afiliado = datos_receta.get("numero_afiliado")
    receta_dni = datos_receta.get("dni_paciente")
    ticket_afiliado = datos_ticket.get("numero_afiliado")
    ticket_dni = datos_ticket.get("dni_paciente")

    # Crear conjuntos con los identificadores encontrados en cada documento
    ids_receta = {str(id) for id in [receta_afiliado, receta_dni] if id}
    ids_ticket = {str(id) for id in [ticket_afiliado, ticket_dni] if id}

    if ids_receta:
        # Hay coincidencia si la intersección de los conjuntos no es vacía
        if ids_receta.intersection(ids_ticket):
            observaciones.append("OK: El DNI o Nro. de Afiliado coincide.")
        else:
            observaciones.append(
                "ERROR: El DNI / Nro. de Afiliado no coincide entre receta y ticket."
            )
    else:
        observaciones.append(
            "INFO: No se encontró DNI o Nro. Afiliado en la receta para comparar."
        )

    # 2. Comparación de Fechas
    if datos_receta.get("fecha_receta") and datos_ticket.get("fecha_ticket"):
        observaciones.append(
            f"OK: Fecha Receta: {datos_receta['fecha_receta']}, Fecha Ticket: {datos_ticket['fecha_ticket']}."
        )
    else:
        observaciones.append(
            "ERROR: Falta la fecha en la receta o en el ticket para comparar."
        )

    # 3. Comparación Inteligente de Productos
    productos_receta = datos_receta.get("productos", [])
    productos_ticket = datos_ticket.get("productos", [])

    # Obtener "identidades" para todos los productos usando el vademécum
    # Ejemplo: para "Alplax", las identidades serían {"alplax", "alprazolam"}
    identidades_receta = {
        p["descripcion"]: vademecum.get_product_identities(p["descripcion"])
        for p in productos_receta
    }
    identidades_ticket = {
        p["descripcion"]: vademecum.get_product_identities(p["descripcion"])
        for p in productos_ticket
    }

    matches = []
    ticket_matched_indices = (
        set()
    )  # Para no matchear el mismo producto del ticket dos veces

    for desc_receta_orig, ids_receta in identidades_receta.items():
        found_match = False
        for i, (desc_ticket_orig, ids_ticket) in enumerate(identidades_ticket.items()):
            if i in ticket_matched_indices:
                continue

            # ¡LA MAGIA OCURRE AQUÍ!
            # La coincidencia existe si los conjuntos de identidades tienen al menos un elemento en común.
            if ids_receta and ids_ticket and not ids_receta.isdisjoint(ids_ticket):
                matches.append(
                    {
                        "receta": desc_receta_orig,
                        "ticket": desc_ticket_orig,
                        "estado": "COINCIDE",
                    }
                )
                ticket_matched_indices.add(i)
                found_match = True
                break

        if not found_match:
            matches.append(
                {
                    "receta": desc_receta_orig,
                    "ticket": None,
                    "estado": "FALTANTE EN TICKET",
                }
            )

    # Añadir productos del ticket que no coincidieron con ninguna receta
    for i, (desc_ticket_orig, _) in enumerate(identidades_ticket.items()):
        if i not in ticket_matched_indices:
            matches.append(
                {"receta": None, "ticket": desc_ticket_orig, "estado": "NO PRESCRIPTO"}
            )

    # 4. Determinar estado general
    num_receta = len(productos_receta)
    num_ticket = len(productos_ticket)
    num_coincidencias = sum(1 for m in matches if m["estado"] == "COINCIDE")

    if num_coincidencias > 0 and num_coincidencias == num_receta == num_ticket:
        estado_general = "COINCIDENCIA_TOTAL"
    elif num_coincidencias > 0:
        estado_general = "COINCIDENCIA_PARCIAL"
    else:
        estado_general = "SIN_COINCIDENCIAS"

    return {
        "estado_general": estado_general,
        "observaciones": observaciones,
        "detalle_productos": matches,
    }
