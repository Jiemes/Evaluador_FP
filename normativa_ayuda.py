"""
normativa_ayuda.py  –  MÓDULO 2 (reglas de puntaje, habilitación y textos de ayuda [?]).

Funciones PURAS: no importa Streamlit ni openpyxl (ver ARQUITECTURA_Y_REGLAS.md §4.2 y §6).
Toda tabla de puntos y todo tope vive SOLO acá; `app.py` únicamente llama a estas funciones.

Fuentes citadas en los textos de ayuda (según el encargo del Arquitecto/usuario):
  * Disposición 13/2025 – Anexo I
  * Comunicación 07/2026 – Anexos 1 y 2
NOTA: los textos se redactaron a partir de los incisos y puntos indicados en el encargo.
Conviene que la Comisión los contraste con los documentos oficiales antes del uso en producción.
"""
from __future__ import annotations

import unicodedata
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

# =========================================================================== #
# 1. CONSTANTES DE PUNTAJE
# =========================================================================== #
TOPE_CAP_DOCENTE = 3.00
TOPE_CAP_ESPECIFICA = 5.00
TOPE_ANTIG_DOCENCIA = 2.50
TOPE_ANTIG_FP = 5.00
PTS_X_ANIO_DOCENCIA = Decimal("0.25")
PTS_X_ANIO_FP = Decimal("0.50")
PTS_RESIDENCIA = 5
PTS_FI = 25
PTS_FORM_SUP_FP = 7
PTS_ART59 = 10

# Decisión D1 (ARQUITECTURA §8): False -> la columna AB guarda el puntaje BASE (sin +5 de residencia).
AB_INCLUYE_RESIDENCIA = False

# Tablas (horas reloj desde, hasta, puntos). `hasta=None` significa "sin límite superior".
TABLA_CAP_DOCENTE = (
    (5, 10, "0.05"), (11, 30, "0.10"), (31, 50, "0.15"),
    (51, 70, "0.30"), (71, 100, "0.40"), (101, None, "0.60"),
)
TABLA_CAP_ESPECIFICA = (
    (5, 10, "0.05"), (11, 15, "0.10"), (16, 20, "0.15"),
    (21, 30, "0.20"), (31, None, "0.30"),
)
TABLA_DESEMPENO = ((0, 2, 0), (3, 4, 5), (5, 9, 6), (10, None, 8))   # años -> pts (col. U)
ANIOS_DESEMPENO_MAX = 35

# Escala de calificación (Ítem 10.9): (nota mínima, puntos)
ESCALA_CALIFICACION = (("9.51", 1.00), ("8.00", 0.50), ("6.00", 0.10))
OPCIONES_ESCALA_CALIFICACION = {
    "9.51 a 10": 1.00,
    "8 a 9.50": 0.50,
    "6 a 7.99": 0.10,
    "Sin calificación": 0.0,
}

# Motivos literales para NO MERITUADOS!J (ARQUITECTURA §5.2)
MOTIVO_DNI = "No presenta DNI"
MOTIVO_TITULO = "No presenta Titulo Secundario"
MOTIVO_ANEXO3 = "No presenta Anexo 3"
MOTIVO_NO_REUNE = "No Reune Requisitos"
MOTIVO_JUBILADO = "Aspirante Jubilado"
MOTIVO_ANTECEDENTES = "NO ACREDITA ANTECEDENTES PROFESIONALES ESPECÍFICOS"
MOTIVO_OTROS = "Otros"
MOTIVOS_NO_MERITUADO = [
    MOTIVO_DNI, MOTIVO_TITULO, MOTIVO_ANEXO3, MOTIVO_NO_REUNE,
    MOTIVO_JUBILADO, MOTIVO_ANTECEDENTES, MOTIVO_OTROS,
]

# Inscripción recurrente (Com. 07/2026 Punto 4.a/b): ítems que se conservan con
# "Mantiene Valoración Anterior" (col. entre paréntesis).
OPCION_MANTIENE_VALORACION = "Mantiene Valoración Anterior"
ITEMS_VALORACION_ANTERIOR = (
    "FI (M)", "Formación Específica (N–Q)", "Capacitación Específica (S)",
    "Capacitación Docente (R)", "Desempeño Profesional (T–U)", "Formación Superior en FP (V)",
)

# Códigos de curso con reglas propias
CODIGO_PRECEPTOR = "00PR"
CODIGO_PANOL = "00PA"

# Formación específica (Ítem 10.2): etiqueta UI -> columnas N, O, P, Q
OPCIONES_FORMACION_ESPECIFICA = {
    "Ninguno / Sin orientación afín": {"N": 0, "O": 0, "P": 0, "Q": 0},
    "Secundario orientado afín": {"N": 3, "O": 0, "P": 0, "Q": 0},
    "Secundario Técnico afín": {"N": 0, "O": 5, "P": 0, "Q": 0},
    "Superior afín": {"N": 0, "O": 0, "P": 7, "Q": 0},
    "Universitario de grado afín": {"N": 0, "O": 0, "P": 0, "Q": 8},
}
# Pañol (00PA): SOLO títulos técnicos; un secundario común suma 0.
OPCIONES_FORMACION_PANOL = {
    "Ninguno / Sin título técnico (secundario común suma 0)": {"N": 0, "O": 0, "P": 0, "Q": 0},
    "Secundario Técnico": {"N": 0, "O": 5, "P": 0, "Q": 0},
    "Superior Técnico": {"N": 0, "O": 0, "P": 7, "Q": 0},
    "Universitario Técnico": {"N": 0, "O": 0, "P": 0, "Q": 8},
}

# Claves del registro (ver ARQUITECTURA §3.1) que componen el puntaje BASE de la columna AB:
# M + N + O + P + Q + R + S + U + V + W + X + Y + Z + AA   (T son años, NO suma)
CLAVES_PUNTAJE_BASE = (
    "fi", "fe_sec_orient", "fe_sec_tecnico", "fe_superior", "fe_universitario",
    "cap_docente", "cap_especifica", "desemp_pts", "form_sup_fp",
    "antig_docencia", "antig_fp", "calif1", "calif2", "art59",
)


# =========================================================================== #
# 2. CÁLCULOS (puros)
# =========================================================================== #
def _d(valor) -> Decimal:
    return Decimal(str(valor))


def _r2(valor: Decimal) -> float:
    return float(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _puntos_tabla(tabla, horas: float) -> Decimal:
    if horas < 0:
        raise ValueError("Las horas no pueden ser negativas.")
    h = int(horas)  # decisión D2: se trunca (igual que INT() de la planilla)
    for desde, hasta, pts in tabla:
        if h >= desde and (hasta is None or h <= hasta):
            return Decimal(pts)
    return Decimal("0")  # decisión D3: < 5 hs = 0 puntos


def convertir_hs_catedra_a_reloj(hs_catedra: float) -> int:
    """hs_reloj = INT(hs_catedra * 2 / 3). Ej.: 45 -> 30; 16 -> 10."""
    if hs_catedra < 0:
        raise ValueError("Las horas no pueden ser negativas.")
    return int(_d(hs_catedra) * 2 / 3)


def puntos_curso_docente(hs_reloj: float) -> float:
    """Ítem 10.5: puntos de UN curso pedagógico según horas reloj."""
    return float(_puntos_tabla(TABLA_CAP_DOCENTE, hs_reloj))


def puntos_curso_especifico(hs_reloj: float) -> float:
    """Ítem 10.3: puntos de UN curso específico del sector según horas reloj."""
    return float(_puntos_tabla(TABLA_CAP_ESPECIFICA, hs_reloj))


def resumen_capacitacion(horas_reloj: list[float],
                         tipo: Literal["docente", "especifica"]) -> dict:
    """{'bruto', 'total', 'tope', 'tope_aplicado'} para mostrar la calculadora en pantalla."""
    if tipo == "docente":
        tabla, tope = TABLA_CAP_DOCENTE, _d(TOPE_CAP_DOCENTE)
    elif tipo == "especifica":
        tabla, tope = TABLA_CAP_ESPECIFICA, _d(TOPE_CAP_ESPECIFICA)
    else:
        raise ValueError("tipo debe ser 'docente' o 'especifica'")
    bruto = sum((_puntos_tabla(tabla, h) for h in horas_reloj), Decimal("0"))
    total = min(bruto, tope)
    return {"bruto": _r2(bruto), "total": _r2(total), "tope": float(tope),
            "tope_aplicado": bruto > tope}


def total_capacitacion(horas_reloj: list[float],
                       tipo: Literal["docente", "especifica"]) -> float:
    """Suma de los cursos con el tope máximo automático (3.00 docente / 5.00 específica)."""
    return resumen_capacitacion(horas_reloj, tipo)["total"]


def puntos_desempeno(anios: int) -> int:
    """Ítem 10.6 (col. U): 0-2 -> 0; 3-4 -> 5; 5-9 -> 6; >=10 -> 8."""
    if not 0 <= anios <= ANIOS_DESEMPENO_MAX:
        raise ValueError(f"Los años deben estar entre 0 y {ANIOS_DESEMPENO_MAX}.")
    for desde, hasta, pts in TABLA_DESEMPENO:
        if anios >= desde and (hasta is None or anios <= hasta):
            return pts
    return 0



def puntos_antiguedad_docencia(anios: float) -> float:
    """Ítem 10.7 (col. W): años * 0.25, tope 2.50."""
    if anios < 0:
        raise ValueError("Los años no pueden ser negativos.")
    return _r2(min(_d(anios) * PTS_X_ANIO_DOCENCIA, _d(TOPE_ANTIG_DOCENCIA)))


def puntos_antiguedad_fp(anios: float) -> float:
    """Ítem 10.8 (col. X): años * 0.50, tope 5.00."""
    if anios < 0:
        raise ValueError("Los años no pueden ser negativos.")
    return _r2(min(_d(anios) * PTS_X_ANIO_FP, _d(TOPE_ANTIG_FP)))


def puntos_calificacion(nota: float | None) -> float:
    """Ítem 10.9: 9.51-10 -> 1; 8-9.50 -> 0.50; 6-7.99 -> 0.10; menos o sin nota -> 0."""
    if nota is None:
        return 0.0
    if not 0 <= nota <= 10:
        raise ValueError("La nota debe estar entre 0 y 10.")
    n = _d(nota)
    for minimo, pts in ESCALA_CALIFICACION:
        if n >= Decimal(minimo):
            return pts
    return 0.0


def promedio_calificaciones(notas: list[float]) -> float | None:
    """Cargos simultáneos en un mismo año: se promedian (Ítem 10.9). None si no hay notas."""
    if not notas:
        return None
    return float((sum((_d(n) for n in notas), Decimal("0")) / len(notas)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP))


def opciones_formacion_especifica(curso: str | None = None) -> list[str]:
    """Etiquetas del selector de la P9. Para Pañol (00PA) solo títulos técnicos."""
    if tipo_cargo(curso) == "panolero":
        return list(OPCIONES_FORMACION_PANOL)
    return list(OPCIONES_FORMACION_ESPECIFICA)


def formacion_especifica(opcion: str) -> dict:
    """Opción elegida -> {'N':..,'O':..,'P':..,'Q':..} (selección única excluyente)."""
    for tabla in (OPCIONES_FORMACION_ESPECIFICA, OPCIONES_FORMACION_PANOL):
        if opcion in tabla:
            return dict(tabla[opcion])
    raise ValueError(f"Opción de formación específica desconocida: {opcion!r}")


def puntos_residencia(coincide: bool | None) -> int | None:
    """Ítem 10.10: Sí -> 5, No -> 0, distrito no cargado (None) -> None (celda vacía)."""
    if coincide is None:
        return None
    return PTS_RESIDENCIA if coincide else 0


def calcular_listado(fi: int) -> str:
    """Inc. 3.3 y 7.1 Dispo 13/2025: FI=25 -> PRINCIPAL; FI=0 -> COMPLEMENTARIO."""
    if fi == PTS_FI:
        return "PRINCIPAL"
    if fi == 0:
        return "COMPLEMENTARIO"
    raise ValueError("FI debe ser 25 o 0.")


def calcular_puntaje(reg: dict, incluye_residencia: bool | None = None) -> dict:
    """Devuelve {'base', 'residencia', 'con_residencia', 'ab', 'desglose'}.
    base = suma de CLAVES_PUNTAJE_BASE; residencia = 5 si algún distrito coincide (máx. +5, D1);
    ab = valor a escribir en la columna AB (según incluye_residencia o AB_INCLUYE_RESIDENCIA)."""
    desglose = {k: _d(reg.get(k) or 0) for k in CLAVES_PUNTAJE_BASE}
    base = sum(desglose.values(), Decimal("0"))
    hay_residencia = any((reg.get(k) or 0) == PTS_RESIDENCIA
                         for k in ("pts_dist1", "pts_dist2", "pts_dist3"))
    residencia = Decimal(PTS_RESIDENCIA if hay_residencia else 0)
    con_res = base + residencia
    usar_residencia = AB_INCLUYE_RESIDENCIA if incluye_residencia is None else incluye_residencia
    return {
        "base": _r2(base),
        "residencia": float(residencia),
        "con_residencia": _r2(con_res),
        "ab": _r2(con_res if usar_residencia else base),
        "desglose": {k: _r2(v) for k, v in desglose.items()},
    }


# --------------------------------------------------------------------------- #
# Ayudas para la edición directa en la grilla (st.data_editor) y para AB
# --------------------------------------------------------------------------- #
def residencia_en_distrito_evaluador(datos: dict, distrito_eval: str | None) -> bool:
    """True si algún distrito del registro es el Distrito Evaluador (D1) y tiene 5 pts de residencia."""
    return bool(distrito_eval) and any(
        datos.get(f"dist{i}") == distrito_eval and datos.get(f"pts_dist{i}") == PTS_RESIDENCIA
        for i in (1, 2, 3))


def calcular_ab(datos: dict, distrito_eval: str | None, incluir_residencia: bool) -> dict:
    """Como `calcular_puntaje`, pero los +5 entran en 'ab' SOLO si `incluir_residencia` está activo
    Y el aspirante acredita residencia en el Distrito Evaluador."""
    usar = bool(incluir_residencia) and residencia_en_distrito_evaluador(datos, distrito_eval)
    return calcular_puntaje(datos, incluye_residencia=usar)


# =========================================================================== #
# Familias Profesionales (Catálogo 2027, §13.1)
# =========================================================================== #
FAMILIAS_PROFESIONALES: dict[str, str] = {
    "00": "00 - Cargos Docentes (Pañol / Preceptor)",
    "AA": "AA - Actividades Agropecuarias",
    "AC": "AC - Administración y Comercialización",
    "AE": "AE - Aeronáutica",
    "AP": "AP - Actividades Pesqueras",
    "CC": "CC - Cuero y Calzado",
    "CS": "CS - Comunicación Social",
    "EE": "EE - Energía Eléctrica",
    "EM": "EM - Electromecánica",
    "ET": "ET - Electrónica",
    "GH": "GH - Gastronomía / Hotelería y Turismo",
    "IA": "IA - Industria Alimentaria",
    "IC": "IC - Industrias Culturales y Creativas",
    "IG": "IG - Industria Gráfica",
    "IM": "IM - Informática",
    "LT": "LT - Logística y Transporte",
    "MA": "MA - Automotriz",
    "MC": "MC - Módulos Comunes",
    "MM": "MM - Madera y Mueble",
    "MT": "MT - Metalmecánica",
    "OA": "OA - Oficios Artesanales",
    "OC": "OC - Construcciones",
    "PA": "PA - Industria Papelera",
    "PL": "PL - Industria Plástica",
    "SC": "SC - Cuidados y Servicios Sociocomunitarios",
    "SM": "SM - Seguridad y Medio Ambiente",
    "SP": "SP - Estética Profesional",
    "SS": "SS - Salud",
    "TC": "TC - Telecomunicaciones",
    "TI": "TI - Textil e Indumentaria",
    "OT": "OT - Otros / Nuevos Cursos",
}


def obtener_prefijo_familia(curso: str | None) -> str:
    """Devuelve el prefijo de 2 letras del curso (ej: 'IM30 - ...' -> 'IM').
    Si no coincide con ninguna familia conocida, devuelve 'OT'."""
    if not curso or len(str(curso).strip()) < 2:
        return "OT"
    pref = str(curso).strip()[:2].upper()
    return pref if pref in FAMILIAS_PROFESIONALES else "OT"


def obtener_nombre_familia(curso: str | None) -> str:
    """Devuelve el nombre completo descriptivo de la familia."""
    pref = obtener_prefijo_familia(curso)
    return FAMILIAS_PROFESIONALES.get(pref, FAMILIAS_PROFESIONALES["OT"])


# =========================================================================== #
# Valores y Normalización Estricta de Antigüedad (§13.4)
# =========================================================================== #
VALORES_PERMITIDOS_ANTIG_DOCENCIA = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5)
VALORES_PERMITIDOS_ANTIG_FP = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0)


def normalizar_antiguedad_docencia(valor: float | int | None) -> float:
    """Redondea al múltiplo de 0.25 más cercano en el rango [0.0, 2.5]."""
    if valor is None:
        return 0.0
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return 0.0
    if v <= 0:
        return 0.0
    if v >= 2.5:
        return 2.5
    return min(VALORES_PERMITIDOS_ANTIG_DOCENCIA, key=lambda x: abs(x - v))


def normalizar_antiguedad_fp(valor: float | int | None) -> float:
    """Redondea al múltiplo de 0.50 más cercano en el rango [0.0, 5.0]."""
    if valor is None:
        return 0.0
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return 0.0
    if v <= 0:
        return 0.0
    if v >= 5.0:
        return 5.0
    return min(VALORES_PERMITIDOS_ANTIG_FP, key=lambda x: abs(x - v))


VALORES_DISCRETOS = {
    "fi": (0, 25), "fe_sec_orient": (0, 3), "fe_sec_tecnico": (0, 5), "fe_superior": (0, 7),
    "fe_universitario": (0, 8), "desemp_pts": (0, 5, 6, 8), "form_sup_fp": (0, 7), "art59": (0, 10),
    "pts_dist1": (0, 5), "pts_dist2": (0, 5), "pts_dist3": (0, 5),
    "calif1": (0.0, 0.1, 0.5, 1.0), "calif2": (0.0, 0.1, 0.5, 1.0),
}
TOPES_EDICION = {"cap_docente": TOPE_CAP_DOCENTE, "cap_especifica": TOPE_CAP_ESPECIFICA}
OBLIGATORIOS_MER = ("dni", "apellido", "nombres", "especialidad", "dist1", "fi")
OBLIGATORIOS_NO_MER = ("dni", "apellido", "nombres", "especialidad", "dist1", "motivo")
_CLAVES_FE = ("fe_sec_orient", "fe_sec_tecnico", "fe_superior", "fe_universitario")


def _es_vacio(v) -> bool:
    return v is None or (isinstance(v, float) and v != v) or v == ""


def _normalizar_comunes(anterior: dict, datos: dict, obligatorios: tuple, avisos: list[str]) -> None:
    """Reglas de edición comunes a ambas hojas (modifica `datos` in situ)."""
    cambiados = {k for k in datos if datos.get(k) != anterior.get(k)}
    for k in obligatorios:
        if _es_vacio(datos.get(k)):
            datos[k] = anterior.get(k)
            avisos.append(f"'{k}' es obligatorio: se restauró el valor anterior.")
    if "dni" in cambiados:
        digitos = "".join(c for c in str(datos["dni"]) if c.isdigit())
        if 7 <= len(digitos) <= 8:
            datos["dni"] = int(digitos)
        else:
            datos["dni"] = anterior.get("dni")
            avisos.append("DNI inválido (7 u 8 dígitos): se restauró el valor anterior.")
    for k in ("apellido", "nombres"):
        if k in cambiados and not _es_vacio(datos.get(k)):
            datos[k] = " ".join(str(datos[k]).upper().split())
    # Distritos: sin repetidos
    elegidos = [datos.get(f"dist{i}") for i in (1, 2, 3) if not _es_vacio(datos.get(f"dist{i}"))]
    if len(elegidos) != len(set(elegidos)):
        for i in (1, 2, 3):
            if f"dist{i}" in cambiados:
                datos[f"dist{i}"] = anterior.get(f"dist{i}")
        avisos.append("No se puede repetir el mismo distrito: se restauró el valor anterior.")
    for i in (1, 2, 3):
        if _es_vacio(datos.get(f"dist{i}")):
            datos[f"dist{i}"] = None


def normalizar_edicion_meritudo(anterior: dict, nuevo: dict) -> tuple[dict, list[str]]:
    """Valida y corrige un registro de MERITUADOS editado a mano.
    Devuelve (datos_corregidos, avisos). NO recalcula 'puntaje' (usar `calcular_ab` después).
    Reglas: obligatorios no vacíos; valores discretos permitidos; topes; FI -> LISTADO;
    T -> U automático; formación específica excluyente; 5 pts de residencia en un solo distrito."""
    datos = dict(nuevo)
    avisos: list[str] = []
    _normalizar_comunes(anterior, datos, OBLIGATORIOS_MER, avisos)
    cambiados = {k for k in datos if datos.get(k) != anterior.get(k)}

    for k, permitidos in VALORES_DISCRETOS.items():
        if k not in cambiados or k.startswith("pts_dist") or k == "desemp_pts":
            continue
        v = datos.get(k)
        try:
            ok = (not _es_vacio(v)) and any(abs(float(v) - p) < 1e-9 for p in permitidos)
        except (TypeError, ValueError):
            ok = False
        if ok:
            datos[k] = type(permitidos[0])(float(v)) if isinstance(permitidos[0], float) else int(float(v))
        else:
            datos[k] = anterior.get(k)
            avisos.append(f"'{k}' solo admite {list(permitidos)}: se restauró el valor anterior.")

    # Topes continuos para capacitaciones
    for k, tope in TOPES_EDICION.items():
        if k in cambiados:
            try:
                if _es_vacio(datos[k]):
                    raise ValueError
                v = float(datos[k])
            except (TypeError, ValueError):
                datos[k] = anterior.get(k)
                avisos.append(f"'{k}' debe ser numérico: se restauró el valor anterior.")
                continue
            topado = round(min(max(v, 0.0), tope), 2)
            if topado != round(v, 2):
                avisos.append(f"'{k}' se ajustó al rango 0–{tope:.2f}.")
            datos[k] = topado

    # Antigüedad Docencia Oficial (Col. W): múltiplos de 0.25 hasta 2.50
    if "antig_docencia" in cambiados:
        orig = datos.get("antig_docencia")
        norm_w = normalizar_antiguedad_docencia(orig)
        datos["antig_docencia"] = norm_w
        if orig is not None and abs(float(orig or 0) - norm_w) > 1e-6:
            avisos.append(f"'antig_docencia' se normalizó al valor válido más cercano ({norm_w:.2f} pts).")

    # Antigüedad FP Oficial (Col. X): múltiplos de 0.50 hasta 5.00
    if "antig_fp" in cambiados:
        orig = datos.get("antig_fp")
        norm_x = normalizar_antiguedad_fp(orig)
        datos["antig_fp"] = norm_x
        if orig is not None and abs(float(orig or 0) - norm_x) > 1e-6:
            avisos.append(f"'antig_fp' se normalizó al valor válido más cercano ({norm_x:.2f} pts).")

    # Residencia (H, J, L): sin distrito -> sin puntos; con distrito -> 0 ó 5; un solo 5
    for i in (1, 2, 3):
        d, p = datos.get(f"dist{i}"), datos.get(f"pts_dist{i}")
        if d is None:
            datos[f"pts_dist{i}"] = None
        else:
            try:
                p = 0 if _es_vacio(p) else int(float(p))
            except (TypeError, ValueError):
                p = anterior.get(f"pts_dist{i}") or 0
            if p not in (0, PTS_RESIDENCIA):
                p = anterior.get(f"pts_dist{i}") or 0
                avisos.append(f"Residencia solo admite 0 ó 5 (Distrito {i}).")
            datos[f"pts_dist{i}"] = p
    if sum(1 for i in (1, 2, 3) if datos.get(f"pts_dist{i}") == PTS_RESIDENCIA) > 1:
        for i in (1, 2, 3):
            if f"pts_dist{i}" in cambiados:
                datos[f"pts_dist{i}"] = (anterior.get(f"pts_dist{i}") or 0) if datos.get(f"dist{i}") else None
        avisos.append("Solo un distrito puede coincidir con el domicilio del DNI: se restauró el anterior.")

    # Formación específica excluyente (gana la columna recién editada)
    con_valor = [k for k in _CLAVES_FE if (datos.get(k) or 0) > 0]
    if len(con_valor) > 1:
        ganadora = next((k for k in con_valor if k in cambiados), con_valor[-1])
        for k in _CLAVES_FE:
            if k != ganadora:
                datos[k] = 0
        avisos.append("Formación específica es excluyente: solo se conserva el título editado.")

    # Desempeño: años -> puntos automáticos (salvo que se edite U a mano)
    if "desemp_anios" in cambiados:
        a = datos.get("desemp_anios")
        try:
            a = None if _es_vacio(a) or int(float(a)) == 0 else int(float(a))
            if a is not None and not 1 <= a <= ANIOS_DESEMPENO_MAX:
                raise ValueError
        except (TypeError, ValueError):
            a = anterior.get("desemp_anios")
            avisos.append(f"Los años de desempeño deben estar entre 0 y {ANIOS_DESEMPENO_MAX}.")
        datos["desemp_anios"] = a
        if "desemp_pts" not in cambiados:
            datos["desemp_pts"] = None if a is None else puntos_desempeno(a)
    if "desemp_pts" in cambiados and "desemp_anios" not in cambiados:
        v = datos.get("desemp_pts")
        try:
            ok = (not _es_vacio(v)) and int(float(v)) in VALORES_DISCRETOS["desemp_pts"] \
                 and datos.get("desemp_anios") is not None
        except (TypeError, ValueError):
            ok = False
        if ok:
            datos["desemp_pts"] = int(float(v))
        else:
            datos["desemp_pts"] = anterior.get("desemp_pts")
            avisos.append("Col. U solo admite 0, 5, 6 u 8 y requiere años cargados en Col. T.")

    # FI -> LISTADO
    datos["listado"] = calcular_listado(datos["fi"]) if datos.get("fi") in (0, PTS_FI) else ""
    return datos, avisos


def normalizar_edicion_no_meritudo(anterior: dict, nuevo: dict) -> tuple[dict, list[str]]:
    """Valida y corrige un registro de NO MERITUADOS editado a mano. Devuelve (datos, avisos)."""
    datos = dict(nuevo)
    avisos: list[str] = []
    _normalizar_comunes(anterior, datos, OBLIGATORIOS_NO_MER, avisos)
    if datos.get("motivo") not in MOTIVOS_NO_MERITUADO:
        datos["motivo"] = anterior.get("motivo")
        avisos.append("Motivo inválido: se restauró el valor anterior.")
    if _es_vacio(datos.get("observaciones")):
        datos["observaciones"] = None
    if datos.get("motivo") == MOTIVO_OTROS and not datos.get("observaciones"):
        datos["motivo"], datos["observaciones"] = anterior.get("motivo"), anterior.get("observaciones")
        avisos.append("Con el motivo “Otros” las observaciones son obligatorias.")
    return datos, avisos

# =========================================================================== #
# 3. HABILITACIÓN (Inc. 3 y Inc. 6)
# =========================================================================== #
def tipo_cargo(curso: str | None) -> Literal["instructor", "preceptor", "panolero"]:
    """Deduce el cargo desde el código del curso ('00PR - Preceptor', '00PA - Pañol'); resto: instructor."""
    codigo = (curso or "").split(" - ")[0].strip().upper()
    if codigo == CODIGO_PRECEPTOR:
        return "preceptor"
    if codigo == CODIGO_PANOL:
        return "panolero"
    return "instructor"


def evaluar_habilitacion(resp: dict) -> tuple[bool, list[str]]:
    """Claves de `resp` (bool; ausente = False, salvo es_instructor/es_jubilado):
      anexo3_valido, dni_ok, titulo_ok          -> Inc. 3
      es_instructor                              -> activa el Inc. 6
      exp_laboral_3_de_5 (6.1.1), titulo_afin_o_350hs (6.1.2)
      idoneidad_estrategica (6.2.1), dicto_2_veces (6.2.2), curso_en_certificado_fi (6.2.3)
      es_jubilado                                -> casilla manual (decisión D6)
    Devuelve (cumple, motivos_sugeridos)."""
    motivos: list[str] = []
    if not resp.get("dni_ok"):
        motivos.append(MOTIVO_DNI)
    if not resp.get("titulo_ok"):
        motivos.append(MOTIVO_TITULO)
    if not resp.get("anexo3_valido"):
        motivos.append(MOTIVO_ANEXO3)
    if resp.get("es_instructor"):
        via_61 = bool(resp.get("exp_laboral_3_de_5")) and bool(resp.get("titulo_afin_o_350hs"))
        via_62 = any(resp.get(k) for k in
                     ("idoneidad_estrategica", "dicto_2_veces", "curso_en_certificado_fi"))
        if not (via_61 or via_62):
            motivos.append(MOTIVO_ANTECEDENTES)
    if resp.get("es_jubilado"):
        motivos.append(MOTIVO_JUBILADO)
    return (not motivos, motivos)


def sugerir_motivo(motivos_incumplidos: list[str]) -> str:
    """Un solo incumplimiento -> ese motivo; varios o ninguno identificado -> 'No Reune Requisitos'."""
    if len(motivos_incumplidos) == 1:
        return motivos_incumplidos[0]
    return MOTIVO_NO_REUNE


# =========================================================================== #
# 4. PERFILES DE NUEVOS DISEÑOS 2026/2027 (Com. 07/2026 – Anexo 2)
# =========================================================================== #
# `claves`: lista de alternativas; una alternativa coincide si TODAS sus palabras están en el
# nombre del curso (sin tildes y en minúsculas).
PERFILES_NUEVOS_DISENOS = (
    {"nombre": "Usuaria/o de IA Generativa", "resolucion": "RESOC-2026-3756 / IM30",
     "claves": (("ia generativa",),),
     "titulos": "Lic./Prof. en Informática; Ing. en Sistemas/Computación; Téc. Sup. en Análisis de "
                "Sistemas/Programación; Analista Univ. de Sistemas.",
     "oficios": "Desarrollador/a de software, analista de datos, consultor informático."},
    {"nombre": "Podadora/or Frutícola", "resolucion": "RESOC-2026-3757",
     "claves": (("podador", "fruticola"),),
     "titulos": "Ing. Agrónomo; Téc. Sup. en Producción Agropecuaria/Frutihortícola; "
                "Téc. Agrario/Arbolista.",
     "oficios": None},
    {"nombre": "Empalmadora/or de Fibra Óptica", "resolucion": "RESOC-2026-3749",
     "claves": (("empalmador", "fibra optica"),), "grupo": "telecom"},
    {"nombre": "Instaladora/or FTTH", "resolucion": "RESOC-2026-3758",
     "claves": (("ftth",),), "grupo": "telecom"},
    {"nombre": "Operadora/or de Redes de Fibra Óptica", "resolucion": "RESOC-2026-3759",
     "claves": (("operador", "redes", "fibra optica"),), "grupo": "telecom"},
    {"nombre": "Analista en Redes de Telecomunicaciones", "resolucion": "RESOC-2026-3748",
     "claves": (("analista", "redes", "telecomunicaciones"),), "grupo": "telecom"},
    {"nombre": "Promotora/or de cooperativas y mutuales", "resolucion": "RESOC-2026-3746",
     "claves": (("promotor", "cooperativ"),),
     "titulos": "Lic./Téc. en Economía Social; Trabajo Social; Sociología; Contador; "
                "Lic. en Administración.",
     "oficios": None},
    {"nombre": "Operadora/or de Cuidados de Personas con Discapacidad",
     "resolucion": "RESOC-2026-23943",
     "claves": (("operador", "cuidados", "discapacidad"),),
     "titulos": "Trabajo Social; Psicología; Psicología Social; Cs. de la Educación; "
                "Psicopedagogía; Medicina; Enfermería; Terapia Ocupacional; "
                "Acompañamiento Terapéutico.",
     "oficios": None},
)
_GRUPO_TELECOM = {
    "titulos": "Títulos y experiencia en Telecomunicaciones, Electrónica, Redes, ISP/NOC.",
    "oficios": None,
}


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto)
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").lower()


def perfil_nuevo_diseno(curso: str | None) -> dict | None:
    """Perfil (dict) si el curso es uno de los nuevos diseños 2026/2027; si no, None."""
    if not curso:
        return None
    nombre = _normalizar(curso)
    for perfil in PERFILES_NUEVOS_DISENOS:
        if any(all(p in nombre for p in alt) for alt in perfil["claves"]):
            return perfil
    return None


def texto_perfil_nuevo_diseno(curso: str | None) -> str:
    """Markdown con la equivalencia de títulos/oficios si el curso es un nuevo diseño; si no, ''."""
    perfil = perfil_nuevo_diseno(curso)
    if not perfil:
        return ""
    datos = _GRUPO_TELECOM if perfil.get("grupo") == "telecom" else perfil
    lineas = [f"**Nuevo diseño 2026/2027: {perfil['nombre']}** ({perfil['resolucion']}) "
              f"– Com. 07/2026, Anexo 2",
              f"- **Títulos / experiencia afín:** {datos['titulos']}"]
    if datos.get("oficios"):
        lineas.append(f"- **Oficios afines:** {datos['oficios']}")
    return "\n".join(lineas)


def texto_perfiles_nuevos_completo() -> str:
    """Diccionario rápido con TODOS los perfiles (para la ayuda general)."""
    bloques = []
    for p in PERFILES_NUEVOS_DISENOS:
        d = _GRUPO_TELECOM if p.get("grupo") == "telecom" else p
        linea = f"- **{p['nombre']}** ({p['resolucion']}): {d['titulos']}"
        if d.get("oficios"):
            linea += f" Oficios: {d['oficios']}"
        bloques.append(linea)
    return "\n".join(bloques)


# =========================================================================== #
# 5. TEXTOS DE AYUDA [?]
# =========================================================================== #
DISPO = "Disposición 13/2025 (Anexo I)"
COM = "Comunicación 07/2026"


def _tabla_md(tabla, unidad: str = "hs reloj") -> str:
    filas = ["| Carga horaria | Puntos |", "|---|---|"]
    for desde, hasta, pts in tabla:
        rango = f"más de {desde - 1}" if hasta is None else (
            f"{desde} a {hasta}")
        filas.append(f"| {rango} {unidad} | {pts} |")
    return "\n".join(filas)


_TEXTO_DNI_RESIDENCIA = """\
**DNI (Inc. 3.2):** debe presentarse el **DNI frente y reverso**. Si falta alguna cara el DNI no se \
considera presentado → motivo *"No presenta DNI"* (hoja NO MERITUADOS). Cargar el número sin puntos \
(ej.: `26943922`).

**Residencia (Ítem 10.10 y Com. 07/2026 Punto 4.d):** se pueden declarar hasta 3 distritos. Los \
**5 puntos solo se asignan al distrito que coincide con el domicilio del DNI vigente** (frente y \
reverso); los demás distritos suman 0.

> **Ejemplo:** el aspirante declara Marcos Paz, Gral. Las Heras y Luján. Su DNI dice \
*"Juan Aguer 741, Marcos Paz"* → **5 pts en Marcos Paz** y **0 pts en Gral. Las Heras y Luján**.

Si el DNI vigente no muestra domicilio en ninguno de los distritos declarados, los tres puntajes son 0. \
El puntaje de residencia se informa aparte: en pantalla se muestran el *puntaje base* y el *puntaje con \
+5 por residencia*."""

_TEXTO_ANEXO3 = f"""\
**Instrumento válido:** el **único** instrumento válido de inscripción es el **Anexo III oficial** \
(Inc. 2.1, 2.2 y 11.1; {COM} Punto 4.a/b). Sin Anexo III válido → motivo *"No presenta Anexo 3"*.

**Inscripción recurrente – opción "{OPCION_MANTIENE_VALORACION}":** el aspirante conserva los \
**puntajes firmes del listado anterior** en: FI, Formación Específica, Capacitación Específica, \
Capacitación Docente, Desempeño Profesional y Formación Superior en FP. En ese caso **solo debe \
presentar probanzas de antigüedad y de calificación de los últimos 2 años**.

**Si agrega cursos nuevos o probanzas nuevas** en alguno de esos ítems, **se valora el inciso completo** \
(lo anterior más lo nuevo, con su tope).

> **Ejemplo 1:** marca *Mantiene Valoración Anterior* y presenta solo Certificación de Servicios \
actualizada y SET 4 de los últimos 2 años → conserva FI, formación y capacitaciones del listado anterior.
>
> **Ejemplo 2:** marca *Mantiene Valoración Anterior* pero adjunta un curso nuevo de capacitación \
específica → se valora **todo** el Ítem 10.3 (cursos anteriores + el nuevo, con tope de 5 pts)."""

_TEXTO_HAB_COMUNES = f"""\
**Requisitos comunes (Inc. 3)** – deben cumplirse **todos**:
1. **Anexo III** oficial y válido (Inc. 2.1, 2.2, 11.1).
2. **DNI frente y reverso** (Inc. 3.2).
3. **Título secundario / superior / universitario registrado.**

Si falla alguno, el aspirante **no se meritúa**: se elige el motivo (*No presenta DNI*, *No presenta \
Titulo Secundario*, *No presenta Anexo 3*, *No Reune Requisitos*, *Aspirante Jubilado*, *NO ACREDITA \
ANTECEDENTES PROFESIONALES ESPECÍFICOS* u *Otros*) y se cargan las observaciones de la Comisión.

Los cargos de **Instructor/a** además deben cumplir el **Inc. 6**. Los de Preceptor/a (00PR) y \
Pañolero/a (00PA) se habilitan por requisitos comunes."""

_TEXTO_INC6 = f"""\
**Inc. 6 – Requisitos específicos del Instructor/a.** Se cumple por una de dos vías:

- **Vía 6.1:** **6.1.1** (antecedentes laborales) **y** **6.1.2** (formación específica) juntas.
- **Vía 6.2 (reemplazos):** basta **uno** de: **6.2.1** Idoneidad Profesional Estratégica, \
**6.2.2** haber dictado el curso 2 veces completo en los últimos 5 años en FP, o **6.2.3** curso \
declarado en el Certificado de FI.

Si no se cumple ninguna vía → motivo *"NO ACREDITA ANTECEDENTES PROFESIONALES ESPECÍFICOS"*.

> **Ejemplo:** un/a aspirante tiene 4 años de experiencia como soldador, pero no tiene título afín ni \
350 hs de FP (falla 6.1.2). Si además dictó el curso 2 veces completas en los últimos 5 años en un CFP \
(6.2.2) y lo prueba con la constancia, **cumple por la vía 6.2**."""

_TEXTO_611 = f"""\
**Inc. 6.1.1 – Antecedentes laborales:** mínimo **3 años dentro de los últimos 5 años** de experiencia \
laboral **NO docente** en la especialidad.

- Según {COM} **Punto 4.e**, **NO se computa el ejercicio de la docencia en ningún nivel o modalidad** \
como antecedente profesional (para cargos de Instructor).
- **En relación de dependencia:** constancia con **fecha de inicio, continuidad y baja**, más **nota del \
empleador que detalle las tareas realizadas**. **No se exigen recibos de sueldo** si la nota detalla \
fehacientemente fechas y funciones.

> **Ejemplo válido:** 4 años (2021–2025) como electricista en una empresa, con constancia de inicio/baja \
y nota del empleador describiendo las instalaciones realizadas → **cumple**.
>
> **Ejemplo NO válido:** 5 años como docente de taller de electricidad en una escuela técnica → \
**no suma** como antecedente profesional."""

_TEXTO_612 = """\
**Inc. 6.1.2 – Formación específica:** alguna de estas opciones:
- **Título secundario orientado o técnico**, **superior** o **universitario**, afín a la especialidad; **o**
- **Certificaciones de FP de 350 hs reloj o más**.

> **Ejemplo:** Técnico en Electrónica (secundario técnico) que aspira al curso de Reparación de \
Electrodomésticos → **cumple 6.1.2**. Alternativa: dos certificados de FP de 200 y 160 hs reloj en la \
especialidad (360 hs) → **cumple**."""

_TEXTO_621 = """\
**Inc. 6.2.1 – Idoneidad Profesional Estratégica** (reemplaza a la vía 6.1): se acredita conforme a la \
**Disposición 1/23**.

> **Ejemplo:** el aspirante presenta el **Anexo III de Orientación Profesional** que acredita su idoneidad \
estratégica para la especialidad."""

_TEXTO_622 = f"""\
**Inc. 6.2.2 – Dictado del curso 2 veces completo en los últimos 5 años en FP** ({COM} **Punto 4.f**).

La constancia debe ser emitida por **CFP / CFL / CFPI / DIEGEP** e incluir: **código del curso**, **curso \
completo**, **calificación**, **período**, **firma y sello**.

> **Ejemplo válido:** constancia del CFP 403 que indica código del curso, que se dictó completo en 2023 y \
2024, con calificación, período, firma y sello.
>
> **Ejemplo NO válido:** constancia sin sello, o que informa un solo dictado → no alcanza."""

_TEXTO_623 = f"""\
**Inc. 6.2.3 – Curso declarado en el Certificado de FI** (Formador/Instructor de FP).

Verificar el curso en la tabla de **"Diseños reemplazados" del Catálogo Jurisdiccional** ({COM} \
**Punto 1.a**): el curso del certificado debe estar declarado en el FI o ser el diseño que reemplaza al \
curso al que se inscribe.

> **Ejemplo:** el FI declara el curso *Operario Apícola* y la tabla de "Diseños reemplazados" lo vincula \
con el nuevo diseño al que se inscribe → **cumple 6.2.3**."""

_TEXTO_FI = f"""\
**Ítem 10.1 – Instructor de Formación Profesional (FI):** ¿posee **certificado de FI válido y \
registrado**? **Sí = 25 pts**, **No = 0 pts**.

Este puntaje define el **LISTADO** (Inc. 3.3 y 7.1, {DISPO}): **25 pts → PRINCIPAL**; **0 pts → \
COMPLEMENTARIO**. Con *{OPCION_MANTIENE_VALORACION}* se conserva el valor firme del listado anterior.

> **Ejemplo:** certificado de FI registrado → 25 pts y listado **PRINCIPAL**. Sin certificado → 0 pts y \
listado **COMPLEMENTARIO**."""

_TEXTO_FORM_ESP = f"""\
**Ítem 10.2 y {COM} Punto 4.c – Formación específica.** Selección **única y excluyente**: solo se \
valora el **título de mayor nivel** vinculado a la especialidad (las demás columnas quedan en 0).

| Título afín | Col. | Puntos |
|---|---|---|
| Secundario orientado | N | 3 |
| Secundario Técnico | O | 5 |
| Superior | P | 7 |
| Universitario de grado | Q | 8 |

**Solo cuentan títulos con reconocimiento oficial y validez nacional.** **No valen** constancias \
provisorias, diplomaturas universitarias de extensión ni postítulos.

> **Ejemplo:** posee Técnico Superior en Electromecánica (7) y Secundario Técnico (5) para un curso de \
Electricista → se valora **solo el Superior: 7 pts** (P=7; N, O, Q=0).

{{FORMACION_CURSO}}"""

_FORMACION_POR_CURSO = {
    "preceptor": """\
**Preceptor/a (00PR):** solo se valoran títulos vinculados con **Administración, Docencia \
(Profesorados), Organización, Recursos Humanos e Informática**. Secundario = 3, Sec. Técnico = 5, \
Superior = 7, Universitario = 8.

> **Ejemplo:** Técnico Superior en Administración de Empresas → **7 pts** (Superior). Técnico Superior en \
Electromecánica → **0 pts** (no vinculado).""",
    "panolero": """\
**Pañolero/a (00PA):** se valoran **SOLO títulos Técnicos**, sin importar su orientación: Secundario \
Técnico = 5, Superior Técnico = 7, Universitario Técnico = 8. Un **secundario común** permite \
inscribirse a Pañol pero **suma 0 pts** en este ítem.

> **Ejemplo:** Técnico Mecánico (secundario técnico) → **5 pts**. Bachiller en Ciencias Sociales \
(secundario común) → se inscribe, pero **0 pts**.""",
    "instructor": """\
**Instructor/a:** el título debe estar **vinculado a la especialidad** del curso. Para los cursos de \
Preceptor/a (00PR) y Pañolero/a (00PA) rigen reglas propias que se muestran al seleccionar esos cursos.""",
}

_TEXTO_FORM_SUP_FP = """\
**Ítem 10.4 – Formación Superior en el ámbito de la FP:** **7 pts** *exclusivamente* por **Tecnicatura \
Universitaria/Superior en Educación Profesional** o **ETP específica para FP**, con **Validez Nacional**.

**No confundir** con Profesorado en Docencia Superior ni con postítulos docentes: esos **no** otorgan \
este puntaje.

> **Ejemplo:** Tecnicatura Superior en Educación Profesional con validez nacional → **7 pts**. \
Profesorado en Docencia Superior → **0 pts** en este ítem."""

_TEXTO_CAP_DOCENTE = f"""\
**Ítem 10.5 – Capacitación Docente** (cursos pedagógicos). Tope máximo: **3,00 pts**.

{_tabla_md(TABLA_CAP_DOCENTE)}

Menos de 5 hs reloj = 0 pts. **Horas cátedra → reloj:** `hs_catedra × 2 / 3` (se trunca). \
**Postítulos, tramos pedagógicos, actualizaciones académicas y cursos de CIIE / CFAP / INET** se \
valoran en estos ítems **según su carga horaria**.

> **Ejemplo:** cursos de 20 hs (0,10), 45 hs (0,15) y 120 hs (0,60) → **0,85 pts**. Un curso de 45 hs \
cátedra = 30 hs reloj → 0,10."""

_TEXTO_CAP_ESPECIFICA = f"""\
**Ítem 10.3 – Capacitación Específica** (cursos del sector/especialidad). Tope máximo: **5,00 pts**.

{_tabla_md(TABLA_CAP_ESPECIFICA)}

Menos de 5 hs reloj = 0 pts. **Postítulos, tramos pedagógicos, actualizaciones académicas y cursos de \
CIIE / CFAP / INET** se valoran en estos ítems **según su carga horaria**.

> **Ejemplo:** cursos de 12 hs (0,10), 25 hs (0,20) y 40 hs (0,30) → **0,60 pts**."""

_TEXTO_DESEMPENO = """\
**Ítem 10.6 – Desempeño profesional en la actividad laboral.** Años acreditados (0 a 35):

| Años | Puntos (col. U) |
|---|---|
| 0 a 2 | 0 |
| 3 a 4 | 5 |
| 5 a 9 | 6 |
| 10 o más | 8 |

**Qué actividad se valora según el cargo:**

{DESEMPENO}

> **Ejemplo:** Instructor/a con 6 años como técnico en una empresa → T = 6 y **U = 6 pts**."""

_DESEMPENO_POR_CARGO = {
    "instructor": "- **Instructor/a:** **NO incluye actividades docentes**; solo actividad laboral "
                  "en la especialidad.",
    "preceptor": "- **Preceptor/a:** valora **manejo de grupos (incluida la docencia)**, "
                 "Administración, Organización, RRHH e Informática.",
    "panolero": "- **Pañolero/a:** valora tareas de **pañol, encargado de depósito o logística**.",
}

_TEXTO_ANTIG_COMUN = """\
La antigüedad **requiere obligatoriamente Certificación de Servicios**: **sin probanza = 0 pts**."""

_TEXTO_ANTIG_DOCENCIA = f"""\
**Ítem 10.7 – Antigüedad en la docencia oficial:** años lectivos × **0,25**, tope **2,50 pts**.

{_TEXTO_ANTIG_COMUN}

> **Ejemplo:** 7 años lectivos con Certificación de Servicios → 7 × 0,25 = **1,75 pts**. \
Más de 10 años → tope **2,50**. Sin certificación → **0**."""

_TEXTO_ANTIG_FP = f"""\
**Ítem 10.8 – Antigüedad en el ámbito de FP oficial:** años lectivos en FP × **0,50**, tope **5,00 pts**.

{_TEXTO_ANTIG_COMUN}

> **Ejemplo:** 4 años en FP con Certificación de Servicios → **2,00 pts**. 12 años → 6,00 → \
tope **5,00**."""

_TEXTO_CALIF = """\
**Ítem 10.9 – Calificaciones (col. Y y Z):** corresponden a los **últimos 2 años calificados en FP**. \
Se acreditan con **SET 4** o **constancia oficial**.

| Nota | Puntos (cada año, máx. 1) |
|---|---|
| 9,51 a 10 | 1,00 |
| 8 a 9,50 | 0,50 |
| 6 a 7,99 | 0,10 |
| Menos de 6 o sin calificación | 0 |

Si tuvo **cargos simultáneos en un mismo año**, las notas **se promedian**. Se carga el **puntaje** (no la nota).

> **Ejemplo:** Año 1: 9,60 → **1,00**. Año 2: dos cargos con 9 y 7 → promedio 8 → **0,50**. \
Total Y + Z = **1,50 pts**."""

_TEXTO_ART59 = """\
**Art. 59 del Estatuto Docente – horas y cargos titulares:** **10 pts** si el aspirante **no posee cargos \
ni horas titulares**; **0 pts** si los posee.

> **Ejemplo:** no tiene cargos ni horas titulares → **10 pts**. Es docente titular de 12 horas cátedra → \
**0 pts**."""

_TEXTO_APELLIDO = f"""\
Cargar **apellido** y **nombres** completos **tal como figuran en el DNI** ({DISPO}, Inc. 3.2), en \
MAYÚSCULAS y sin abreviaturas.

> **Ejemplo:** Apellido `SABORIDO` – Nombres `LORENA LILIANA`."""

# Estructura: clave -> {titulo, columnas, normativa[list], texto}
_DNI = {"titulo": "DNI y Residencia", "columnas": "C, G–L",
        "normativa": [f"{DISPO}, Inc. 3.2", f"{DISPO}, Inc. 10.10", f"{COM}, Punto 4.d"],
        "texto": _TEXTO_DNI_RESIDENCIA}
_NOMBRE = {"titulo": "Apellido y nombres", "columnas": "D–E",
           "normativa": [f"{DISPO}, Inc. 3.2"], "texto": _TEXTO_APELLIDO}

AYUDAS: dict[str, dict] = {
    "P1": {**_DNI, "titulo": "DNI y Residencia", "columnas": "C"},
    "P2": {**_NOMBRE, "columnas": "D"},
    "P3": {**_NOMBRE, "columnas": "E"},
    "P4": {"titulo": "Especialidad, Inscripción Recurrente y Anexo III", "columnas": "F",
           "normativa": [f"{DISPO}, Inc. 2.1, 2.2 y 11.1", f"{COM}, Punto 4.a/b"],
           "texto": _TEXTO_ANEXO3},
    "P5": {**_DNI, "columnas": "G–H"},
    "P6": {**_DNI, "columnas": "I–J"},
    "P7": {**_DNI, "columnas": "K–L"},
    "HABILITACION": {"titulo": "Filtro de habilitación – Requisitos comunes", "columnas": "(filtro)",
                     "normativa": [f"{DISPO}, Inc. 3", f"{DISPO}, Inc. 2.1, 2.2 y 11.1",
                                   f"{DISPO}, Inc. 3.2"],
                     "texto": _TEXTO_HAB_COMUNES},
    "HAB_INC6": {"titulo": "Requisitos específicos Instructor/a (Inc. 6)", "columnas": "(filtro)",
                 "normativa": [f"{DISPO}, Inc. 6", f"{COM}, Punto 4.e", f"{COM}, Punto 4.f",
                               f"{COM}, Punto 1.a"],
                 "texto": _TEXTO_INC6},
    "HAB_6_1_1": {"titulo": "Vía 6.1.1 – Antecedentes laborales", "columnas": "(filtro)",
                  "normativa": [f"{DISPO}, Inc. 6.1.1", f"{COM}, Punto 4.e"],
                  "texto": _TEXTO_611},
    "HAB_6_1_2": {"titulo": "Vía 6.1.2 – Formación específica", "columnas": "(filtro)",
                  "normativa": [f"{DISPO}, Inc. 6.1.2"], "texto": _TEXTO_612},
    "HAB_6_2_1": {"titulo": "Reemplazo 6.2.1 – Idoneidad Profesional Estratégica",
                  "columnas": "(filtro)",
                  "normativa": [f"{DISPO}, Inc. 6.2.1", "Disposición 1/23"], "texto": _TEXTO_621},
    "HAB_6_2_2": {"titulo": "Reemplazo 6.2.2 – Dictado 2 veces completo", "columnas": "(filtro)",
                  "normativa": [f"{DISPO}, Inc. 6.2.2", f"{COM}, Punto 4.f"],
                  "texto": _TEXTO_622},
    "HAB_6_2_3": {"titulo": "Reemplazo 6.2.3 – Curso declarado en Certificado de FI",
                  "columnas": "(filtro)",
                  "normativa": [f"{DISPO}, Inc. 6.2.3", f"{COM}, Punto 1.a"],
                  "texto": _TEXTO_623},
    "P8": {"titulo": "Instructor de Formación Profesional (FI)", "columnas": "M",
           "normativa": [f"{DISPO}, Ítem 10.1", f"{DISPO}, Inc. 3.3 y 7.1"], "texto": _TEXTO_FI},
    "P9": {"titulo": "Formación Específica", "columnas": "N, O, P, Q",
           "normativa": [f"{DISPO}, Ítem 10.2", f"{COM}, Punto 4.c"], "texto": _TEXTO_FORM_ESP},
    "P10": {"titulo": "Capacitación Docente", "columnas": "R",
            "normativa": [f"{DISPO}, Ítem 10.5"], "texto": _TEXTO_CAP_DOCENTE},
    "P11": {"titulo": "Capacitación Específica", "columnas": "S",
            "normativa": [f"{DISPO}, Ítem 10.3"], "texto": _TEXTO_CAP_ESPECIFICA},
    "P12": {"titulo": "Desempeño Profesional en la actividad laboral", "columnas": "T, U",
            "normativa": [f"{DISPO}, Ítem 10.6"], "texto": _TEXTO_DESEMPENO},
    "P13": {"titulo": "Formación Superior en el ámbito de la FP", "columnas": "V",
            "normativa": [f"{DISPO}, Ítem 10.4"], "texto": _TEXTO_FORM_SUP_FP},
    "P14": {"titulo": "Antigüedad en la docencia oficial", "columnas": "W",
            "normativa": [f"{DISPO}, Ítem 10.7"], "texto": _TEXTO_ANTIG_DOCENCIA},
    "P15": {"titulo": "Antigüedad en el ámbito de FP oficial", "columnas": "X",
            "normativa": [f"{DISPO}, Ítem 10.8"], "texto": _TEXTO_ANTIG_FP},
    "P16": {"titulo": "Calificaciones (últimos 2 años en FP)", "columnas": "Y, Z",
            "normativa": [f"{DISPO}, Ítem 10.9"], "texto": _TEXTO_CALIF},
    "P17": {"titulo": "Art. 59 del Estatuto Docente", "columnas": "AA",
            "normativa": ["Art. 59 del Estatuto Docente (horas y cargos titulares)"],
            "texto": _TEXTO_ART59},
    "PERFILES_NUEVOS": {"titulo": "Perfiles de Nuevos Diseños 2026/2027", "columnas": "F",
                        "normativa": [f"{COM}, Anexo 2"],
                        "texto": "Títulos y oficios afines de los nuevos diseños:\n\n"
                                 + texto_perfiles_nuevos_completo()},
}

# Claves donde se agrega automáticamente el perfil de "nuevo diseño" si el curso lo es.
_CLAVES_CON_PERFIL = {"P4", "P9", "HAB_INC6", "HAB_6_1_2"}


def obtener_ayuda(clave: str, curso: str | None = None) -> str:
    """Markdown listo para `st.expander`/`st.popover` del botón [?].
    `curso` (texto de 'Hoja 2' col. A) personaliza P9 (Preceptor/Pañol), P12 (cargo) y agrega
    la equivalencia de títulos cuando es un nuevo diseño 2026/2027."""
    if clave not in AYUDAS:
        raise KeyError(f"No hay ayuda para la clave {clave!r}")
    a = AYUDAS[clave]
    texto = a["texto"]
    cargos = (tipo_cargo(curso),) if curso else tuple(_DESEMPENO_POR_CARGO)
    if clave == "P9":
        texto = texto.replace("{FORMACION_CURSO}", "\n\n".join(
            _FORMACION_POR_CURSO[c] for c in ((tipo_cargo(curso),) if curso else
                                               ("preceptor", "panolero"))))
    elif clave == "P12":
        texto = texto.replace("{DESEMPENO}", "\n".join(_DESEMPENO_POR_CARGO[c] for c in cargos))
    partes = [f"### {a['titulo']}  \n*(Col. {a['columnas']})*",
              "**Normativa:** " + " · ".join(a["normativa"]), "", texto]
    if clave in _CLAVES_CON_PERFIL:
        extra = texto_perfil_nuevo_diseno(curso)
        if extra:
            partes += ["", "---", extra]
    return "\n".join(partes)
