"""
app.py  –  MÓDULO 3 (interfaz Streamlit v2). Ejecutar con: streamlit run app.py

Diseño v2 con cabecera superior centrada, asistente guiado paso a paso (Paso 1 a 18 + 8B),
panel de ayuda normativa fija sincronizada, fila en vivo A-AB y planilla st.data_editor.
Orquesta `extractor_datos.py` (I/O Excel) y `normativa_ayuda.py` (reglas y textos de ayuda).
"""
from __future__ import annotations

import copy
import inspect
import json
import re
import unicodedata

import pandas as pd
import streamlit as st

import extractor_datos as ed
import normativa_ayuda as na

# --------------------------------------------------------------------------- #
# Configuración y constantes de interfaz
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Evaluador FP Reg 10 – Listados 2027",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DISTRITO_DEFECTO = "Reg 10 Distrito: 067-MARCOS PAZ"
ARCHIVO_SESION = ed.DIR_SALIDA / "sesion_registros.json"
NINGUNO = "— Ninguno —"
SI, NO = "Sí", "No"
HOJA_MER, HOJA_NO = "MER", "NOMER"

NO_MERITUA = "NO MERITÚA (no cumple requisitos de habilitación)"
HAB_INSTRUCTOR = [
    "Vía General 6.1.1 + 6.1.2 (3 años de antecedentes laborales + título afín o 350 hs de FP)",
    "Idoneidad Profesional Estratégica – 6.2.1",
    "Dictado del curso 2 veces completo – 6.2.2",
    "Curso declarado en Certificado de FI – 6.2.3",
    "Inscripción Recurrente – 2.1",
    NO_MERITUA,
]
HAB_COMUN = [
    "Requisitos Comunes (Inc. 3) – Pañolero/a o Preceptor/a",
    "Inscripción Recurrente – 2.1",
    NO_MERITUA,
]

CAL_RELOJ, CAL_CATEDRA = "Horas reloj", "Horas cátedra"

CALIF_OPCIONES = {
    "1.00 (9.51 a 10 - Sobresaliente)": na.puntos_calificacion(10),
    "0.50 (8 a 9.50 - Distinguido)": na.puntos_calificacion(8),
    "0.10 (6 a 7.99 - Bueno)": na.puntos_calificacion(6),
    "0.00 (Sin calificación / No acredita SET 4)": na.puntos_calificacion(None),
}
CALIF_DEFECTO = "0.00 (Sin calificación / No acredita SET 4)"

_NOM_FORM_GENERAL = [
    "Ninguno/No afín",
    "Secundario Afín",
    "Secundario Técnico Afín",
    "Superior Afín",
    "Universitario Afín",
]
_NOM_FORM_PANOL = [
    "Ninguno / Secundario común (no suma en Pañol)",
    "Secundario Técnico",
    "Superior Técnico",
    "Universitario Técnico",
]
NOMBRES_FORMACION = {
    **dict(zip(na.OPCIONES_FORMACION_ESPECIFICA, _NOM_FORM_GENERAL)),
    **dict(zip(na.OPCIONES_FORMACION_PANOL, _NOM_FORM_PANOL)),
}

TAB_AYUDA = {
    "HAB_INC6": "Inc. 6 (general)",
    "HAB_6_1_1": "6.1.1",
    "HAB_6_1_2": "6.1.2",
    "HAB_6_2_1": "6.2.1",
    "HAB_6_2_2": "6.2.2",
    "HAB_6_2_3": "6.2.3",
}

CAMPOS_COMUNES = [
    "dni_txt", "apellido", "nombres",
    "d1", "d2", "d3",
    "r1", "r2", "r3",
    "fi", "form_sup", "antig_doc", "antig_fp",
    "calif1", "calif2", "art59",
]

PASOS_PRECARGADOS_SALTAR = {9, 14, 15, 16, 17}

# Columnas y etiquetas oficiales
COLS_OFICIALES_MER = [
    ("orden", "A", "ORDEN"),
    ("listado", "B", "LISTADO"),
    ("dni", "C", "DNI"),
    ("apellido", "D", "APELLIDO"),
    ("nombres", "E", "NOMBRES"),
    ("especialidad", "F", "ESPECIALIDAD (TRAYECTO, CURSO Y/O MÓDULO)"),
    ("dist1", "G", "Distrito 1"),
    ("pts_dist1", "H", "ptos."),
    ("dist2", "I", "Distrito 2"),
    ("pts_dist2", "J", "ptos."),
    ("dist3", "K", "Distrito 3"),
    ("pts_dist3", "L", "ptos."),
    ("fi", "M", "INSTRUCTOR DE FP – FI"),
    ("fe_sec_orient", "N", "FORMACIÓN ESPECÍFICA – Secundario"),
    ("fe_sec_tecnico", "O", "FORMACIÓN ESPECÍFICA – Sec. técnico"),
    ("fe_superior", "P", "FORMACIÓN ESPECÍFICA – Superior"),
    ("fe_universitario", "Q", "FORMACIÓN ESPECÍFICA – Universitario"),
    ("cap_docente", "R", "CAPACITACIÓN DOCENTE"),
    ("cap_especifica", "S", "CAPACITACIÓN ESPECÍFICA"),
    ("desemp_anios", "T", "DESEMPEÑO PROFESIONAL – años"),
    ("desemp_pts", "U", "DESEMPEÑO PROFESIONAL – pts"),
    ("form_sup_fp", "V", "FORMACIÓN SUPERIOR EN FP"),
    ("antig_docencia", "W", "ANTIGÜEDAD DOCENCIA OFICIAL"),
    ("antig_fp", "X", "ANTIGÜEDAD ÁMBITO FP OFICIAL"),
    ("calif1", "Y", "CALIFICACIÓN 1"),
    ("calif2", "Z", "CALIFICACIÓN 2"),
    ("art59", "AA", "ART 59 DEL ESTATUTO DOCENTE"),
    ("puntaje", "AB", "PUNTAJE"),
]

COLS_OFICIALES_NO_MER = [
    ("orden", "A", "ORDEN"),
    ("dni", "C", "DNI"),
    ("apellido", "D", "APELLIDO"),
    ("nombres", "E", "NOMBRES"),
    ("especialidad", "F", "ESPECIALIDAD"),
    ("dist1", "G", "Distrito 1"),
    ("dist2", "H", "Distrito 2"),
    ("dist3", "I", "Distrito 3"),
    ("motivo", "J", "NO MERITUA / MOTIVO"),
    ("observaciones", "K", "OBSERVACIONES DE LA COMISIÓN EVALUADORA"),
]


def _ancho(funcion) -> dict:
    if "width" in inspect.signature(funcion).parameters:
        return {"width": "stretch"}
    return {"use_container_width": True}


# --------------------------------------------------------------------------- #
# Manejo de respuestas y Estado
# --------------------------------------------------------------------------- #
def nueva_resp() -> dict:
    return {
        "dni_txt": "", "apellido": "", "nombres": "",
        "d1": None, "d2": None, "d3": None,
        "r1": False, "r2": False, "r3": False,
        "curso": None, "confirm_dup": False,
        "hab": None, "req_comunes": False, "mantiene": None,
        "motivo": na.MOTIVO_NO_REUNE, "obs": "",
        "fi": None,
        "fe_sel": None,
        "modo_doc": "Certificados", "cert_doc": [], "dir_doc": 0.0,
        "modo_esp": "Certificados", "cert_esp": [], "dir_esp": 0.0,
        "t_anios": 0, "u_prev": None,
        "form_sup": None,
        "antig_doc": 0.0, "antig_fp": 0.0,
        "calif1": CALIF_DEFECTO, "calif2": CALIF_DEFECTO,
        "art59": None,
    }


def wk(campo: str) -> str:
    return f"w{st.session_state.ver}_{campo}"


def _leer_disco() -> dict:
    try:
        return json.loads(ARCHIVO_SESION.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def guardar_disco() -> None:
    ss = st.session_state
    try:
        ed.DIR_SALIDA.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 2,
            "sig_id": ss.sig_id,
            "config": {
                "distrito_eval": ss.distrito_eval,
                "incluir_residencia_ab": ss.incluir_residencia_ab,
            },
            "registros": ss.registros,
        }
        ARCHIVO_SESION.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        st.toast(f"No se pudo respaldar la sesión en disco: {exc}", icon="⚠️")


def init_estado() -> None:
    ss = st.session_state
    if "registros" in ss:
        return
    disco = _leer_disco()
    raw_regs = disco.get("registros", [])
    # Sanitizar versión previa de registros si venían con 'inputs'
    regs_limpios = []
    for r in raw_regs:
        item = {"id": r.get("id"), "hoja": r.get("hoja"), "datos": r.get("datos", {})}
        regs_limpios.append(item)
    ss.registros = regs_limpios
    ss.sig_id = disco.get("sig_id", max([r["id"] for r in ss.registros], default=0) + 1)
    cfg = disco.get("config", {})
    ss.distrito_eval = cfg.get("distrito_eval", DISTRITO_DEFECTO)
    ss.incluir_residencia_ab = cfg.get("incluir_residencia_ab", False)

    ss.paso_actual = 1
    ss.resp = nueva_resp()
    ss.ver = 1
    ss.ver_tabla = 1
    ss.es_otro_curso = False
    ss.saltar_precargados = True
    ss.flash = None


def sanear_resp() -> None:
    ss = st.session_state
    resp = ss.resp
    tipo = na.tipo_cargo(resp.get("curso"))
    opciones_hab = HAB_INSTRUCTOR if tipo == "instructor" else HAB_COMUN
    if resp.get("hab") not in opciones_hab:
        resp["hab"] = None
    opciones_fe = na.opciones_formacion_especifica(resp.get("curso"))
    if resp.get("fe_sel") not in opciones_fe:
        resp["fe_sel"] = opciones_fe[0] if opciones_fe else None


def recalcular_ab_todos() -> None:
    ss = st.session_state
    for r in ss.registros:
        if r["hoja"] == HOJA_MER:
            res = na.calcular_ab(r["datos"], ss.distrito_eval, ss.incluir_residencia_ab)
            r["datos"]["puntaje"] = res["ab"]


def _al_cambiar_config() -> None:
    recalcular_ab_todos()
    guardar_disco()


# --------------------------------------------------------------------------- #
# Cache de Excel e información de base
# --------------------------------------------------------------------------- #
def _mtime() -> float:
    return ed.RUTA_ORIGINAL.stat().st_mtime


@st.cache_data(show_spinner="Leyendo cursos y distritos de 'Hoja 2'…")
def listas(mtime: float) -> tuple[list[str], list[str]]:
    return ed.cargar_listas(ed.RUTA_ORIGINAL)


@st.cache_data(show_spinner=False)
def resumen_base(mtime: float) -> dict:
    return ed.resumen_cargados(ed.RUTA_ORIGINAL)


@st.cache_data(show_spinner=False)
def buscar_dni_en_planilla(dni: int, mtime: float) -> list[dict]:
    return ed.buscar_por_dni(ed.RUTA_ORIGINAL, dni)


@st.cache_data(show_spinner="Generando el Excel oficial…")
def generar_excel(mer_json: str, no_json: str, distrito: str, mtime: float) -> bytes:
    return ed.exportar_excel_bytes(json.loads(mer_json), json.loads(no_json), distrito)


def slug_distrito(distrito: str) -> str:
    nombre = distrito.split("Distrito:")[-1].strip()
    nombre = "".join(c for c in unicodedata.normalize("NFD", nombre) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Za-z0-9-]+", "_", nombre).strip("_") or "REG10"


def fmt(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float):
        return f"{valor:.2f}"
    return str(valor)


def etiqueta_formacion(opcion: str) -> str:
    valores = na.formacion_especifica(opcion)
    pts = sum(valores.values())
    col = next((c for c, v in valores.items() if v), None)
    return f"{pts} pts - {NOMBRES_FORMACION.get(opcion, opcion)}" + (f" [Col {col}]" if col else "")


def _registros(hoja: str) -> list[dict]:
    return [r for r in st.session_state.registros if r["hoja"] == hoja]


def _orden_siguiente(hoja: str) -> int:
    base = resumen_base(_mtime())["meritudos" if hoja == HOJA_MER else "no_meritudos"]
    return base + len(_registros(hoja)) + 1


def duplicados(dni: int | None, curso: str | None) -> list[str]:
    if not dni or not curso:
        return []
    ss = st.session_state
    hallados = [
        f"sesión actual ({'MERITUADOS' if r['hoja'] == HOJA_MER else 'NO MERITUADOS'})"
        for r in ss.registros
        if r["datos"].get("dni") == dni and r["datos"].get("especialidad") == curso
    ]
    hallados += [
        f"planilla base, hoja {h['hoja']}, fila {h['fila']}"
        for h in buscar_dni_en_planilla(dni, _mtime())
        if h["especialidad"] == curso
    ]
    return hallados


# --------------------------------------------------------------------------- #
# Construcción unificada de datos para preview y guardado
# --------------------------------------------------------------------------- #
def construir_datos(resp: dict, distrito_eval: str, incluir: bool) -> tuple[str, dict]:
    limpio = re.sub(r"\D", "", resp.get("dni_txt") or "")
    dni = int(limpio) if limpio else None

    d1, d2, d3 = resp.get("d1"), resp.get("d2"), resp.get("d3")
    pts_d1 = na.puntos_residencia(resp.get("r1", False)) if d1 else None
    pts_d2 = na.puntos_residencia(resp.get("r2", False)) if d2 else None
    pts_d3 = na.puntos_residencia(resp.get("r3", False)) if d3 else None

    curso = resp.get("curso")
    hab = resp.get("hab")

    if hab == NO_MERITUA:
        hoja = HOJA_NO
        datos = {
            "dni": dni,
            "apellido": (resp.get("apellido") or "").strip(),
            "nombres": (resp.get("nombres") or "").strip(),
            "especialidad": curso,
            "dist1": d1,
            "dist2": d2,
            "dist3": d3,
            "motivo": resp.get("motivo"),
            "observaciones": (resp.get("obs") or "").strip() or None,
        }
        return hoja, datos

    hoja = HOJA_MER
    fi = resp.get("fi")
    fe_sel = resp.get("fe_sel") or (na.opciones_formacion_especifica(curso)[0] if curso else None)
    fe = na.formacion_especifica(fe_sel) if fe_sel else {"N": 0, "O": 0, "P": 0, "Q": 0}

    # Capacitaciones
    if resp.get("modo_doc") == "Puntaje directo":
        r_val = round(float(resp.get("dir_doc", 0.0) or 0.0), 2)
    else:
        hs_reloj_doc = [
            (na.convertir_hs_catedra_a_reloj(c["horas"]) if c["unidad"] == CAL_CATEDRA else c["horas"])
            for c in resp.get("cert_doc", [])
        ]
        r_val = na.resumen_capacitacion(hs_reloj_doc, "docente")["total"]

    if resp.get("modo_esp") == "Puntaje directo":
        s_val = round(float(resp.get("dir_esp", 0.0) or 0.0), 2)
    else:
        hs_reloj_esp = [
            (na.convertir_hs_catedra_a_reloj(c["horas"]) if c["unidad"] == CAL_CATEDRA else c["horas"])
            for c in resp.get("cert_esp", [])
        ]
        s_val = na.resumen_capacitacion(hs_reloj_esp, "especifica")["total"]

    t_anios = resp.get("t_anios", 0)
    if resp.get("mantiene") == "Sí" and resp.get("u_prev") is not None:
        u_pts = resp.get("u_prev")
    else:
        u_pts = na.puntos_desempeno(t_anios) if t_anios else 0

    t_val = t_anios if t_anios > 0 else None
    u_val = u_pts if t_anios > 0 else None

    v_val = resp.get("form_sup")
    w_val = na.puntos_antiguedad_docencia(resp.get("antig_doc", 0.0))
    x_val = na.puntos_antiguedad_fp(resp.get("antig_fp", 0.0))
    y_val = CALIF_OPCIONES.get(resp.get("calif1"), 0.0)
    z_val = CALIF_OPCIONES.get(resp.get("calif2"), 0.0)
    aa_val = resp.get("art59")

    datos = {
        "dni": dni,
        "apellido": (resp.get("apellido") or "").strip(),
        "nombres": (resp.get("nombres") or "").strip(),
        "especialidad": curso,
        "dist1": d1, "pts_dist1": pts_d1,
        "dist2": d2, "pts_dist2": pts_d2,
        "dist3": d3, "pts_dist3": pts_d3,
        "fi": fi,
        "fe_sec_orient": fe["N"], "fe_sec_tecnico": fe["O"],
        "fe_superior": fe["P"], "fe_universitario": fe["Q"],
        "cap_docente": r_val, "cap_especifica": s_val,
        "desemp_anios": t_val, "desemp_pts": u_val,
        "form_sup_fp": v_val,
        "antig_docencia": w_val, "antig_fp": x_val,
        "calif1": y_val, "calif2": z_val,
        "art59": aa_val,
    }
    datos["listado"] = na.calcular_listado(fi) if fi in (0, na.PTS_FI) else ""
    calc = na.calcular_ab(datos, distrito_eval, incluir)
    datos["puntaje"] = calc["ab"]
    return hoja, datos


# --------------------------------------------------------------------------- #
# Top Bar (Cabecera Superior Centrada)
# --------------------------------------------------------------------------- #
def top_bar(distritos: list[str]) -> None:
    ss = st.session_state
    st.markdown(
        "<div style='text-align: center; margin-bottom: 0.5rem;'>"
        "<h2 style='margin-bottom:0;'>📋 Evaluador de Formación Profesional · Región 10</h2>"
        "<p style='color:gray; font-size: 0.95rem; margin-top:0;'>Comisión Evaluadora · Listados Oficiales 2027</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    _, c1, c2, c3, c4, _ = st.columns([0.2, 2.5, 2.7, 2.6, 0.6, 0.2], vertical_alignment="center")

    with c1:
        idx_dist = distritos.index(ss.distrito_eval) if ss.distrito_eval in distritos else 0
        st.selectbox(
            "Distrito Evaluador (celda D1)",
            distritos,
            index=idx_dist,
            key="distrito_eval",
            on_change=_al_cambiar_config,
        )

    with c2:
        mer = [r["datos"] for r in _registros(HOJA_MER)]
        no = [r["datos"] for r in _registros(HOJA_NO)]
        mer_json = json.dumps(mer, ensure_ascii=False, sort_keys=True)
        no_json = json.dumps(no, ensure_ascii=False, sort_keys=True)
        nombre_archivo = f"PLANILLA DE DATOS DE ASPIRANTES - {slug_distrito(ss.distrito_eval)}.xlsx"
        st.download_button(
            "📥 Descargar Planilla Oficial (.xlsx)",
            data=generar_excel(mer_json, no_json, ss.distrito_eval, _mtime()),
            file_name=nombre_archivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            help="Genera y descarga la planilla compatible al 100% con Hojas de Cálculo de Google.",
            **_ancho(st.download_button),
        )

    with c3:
        st.checkbox(
            "Incluir +5 pts de residencia del Distrito Evaluador en Columna AB",
            key="incluir_residencia_ab",
            on_change=_al_cambiar_config,
            help="Si está activo, suma 5 pts en Col. AB solo si el aspirante acredita residencia en el Distrito Evaluador actual.",
        )

    with c4:
        with st.popover("⚙️", **_ancho(st.popover)):
            st.markdown("##### Acciones de sesión")
            if st.button("🧹 Limpiar asistente (sin guardar)", **_ancho(st.button)):
                resetear_aspirante()
                st.rerun()
            st.divider()
            st.markdown("⚠️ **Zona de riesgo:**")
            if st.button("🗑️ Vaciar toda la sesión", type="primary", **_ancho(st.button)):
                ss.registros = []
                ss.sig_id = 1
                ss.ver_tabla += 1
                guardar_disco()
                resetear_aspirante()
                st.rerun()

    # Contadores centrados
    n_mer, n_no = len(_registros(HOJA_MER)), len(_registros(HOJA_NO))
    legajos_mer = len({r["datos"]["dni"] for r in _registros(HOJA_MER) if r["datos"].get("dni")})
    legajos_no = len({r["datos"]["dni"] for r in _registros(HOJA_NO) if r["datos"].get("dni")})
    st.markdown(
        f"<div style='text-align: center; color: #666; font-size: 0.88rem; margin-bottom: 0.8rem;'>"
        f"<b>MERITUADOS:</b> {n_mer} cursos ({legajos_mer} legajos) &nbsp;·&nbsp; "
        f"<b>NO MERITUADOS:</b> {n_no} cursos ({legajos_no} legajos)"
        f"</div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Lógica de Navegación, Rutas y Validaciones
# --------------------------------------------------------------------------- #
def ruta_activa(resp: dict) -> list[int]:
    hab = resp.get("hab")
    if hab is None:
        return list(range(1, 9))
    if hab == NO_MERITUA:
        return list(range(1, 9)) + [19]
    return list(range(1, 19))


def validar_paso(p: int, resp: dict) -> list[str]:
    errores = []
    if p == 1:
        dni_limpio = re.sub(r"\D", "", resp.get("dni_txt") or "")
        if not re.fullmatch(r"\d{7,8}", dni_limpio):
            errores.append("DNI inválido: ingrese 7 u 8 dígitos sin puntos.")
    elif p == 2:
        if not (resp.get("apellido") or "").strip():
            errores.append("El APELLIDO es obligatorio.")
    elif p == 3:
        if not (resp.get("nombres") or "").strip():
            errores.append("Los NOMBRES son obligatorios.")
    elif p == 4:
        if not resp.get("d1"):
            errores.append("Debe seleccionar el Distrito 1.")
    elif p == 5:
        d1, d2 = resp.get("d1"), resp.get("d2")
        if d2 and d2 == d1:
            errores.append("El Distrito 2 no puede ser igual al Distrito 1.")
        r_sum = sum([resp.get("r1", False), resp.get("r2", False), resp.get("r3", False)])
        if r_sum > 1:
            errores.append("Solo un distrito puede coincidir con el domicilio del DNI vigente (máx. 5 pts).")
    elif p == 6:
        d1, d2, d3 = resp.get("d1"), resp.get("d2"), resp.get("d3")
        elegidos = [d for d in [d1, d2, d3] if d]
        if len(elegidos) != len(set(elegidos)):
            errores.append("No puede repetir un mismo distrito en dos opciones.")
        r_sum = sum([resp.get("r1", False), resp.get("r2", False), resp.get("r3", False)])
        if r_sum > 1:
            errores.append("Solo un distrito puede coincidir con el domicilio del DNI vigente.")
    elif p == 7:
        curso = resp.get("curso")
        if not curso:
            errores.append("Debe seleccionar un Curso o Especialidad.")
        else:
            dni_limpio = re.sub(r"\D", "", resp.get("dni_txt") or "")
            dni = int(dni_limpio) if dni_limpio else None
            dups = duplicados(dni, curso)
            if dups and not resp.get("confirm_dup"):
                errores.append("Ya existe una carga de este aspirante para este curso. Marque la confirmación.")
    elif p == 8:
        hab = resp.get("hab")
        if not hab:
            errores.append("Debe indicar una opción de Habilitación (o 'NO MERITÚA').")
        elif hab != NO_MERITUA:
            if not resp.get("req_comunes"):
                errores.append("Debe confirmar los Requisitos Comunes (Inc. 3) para merituar.")
            if "Recurrente" in hab and resp.get("mantiene") is None:
                errores.append("Indique si Mantiene o No la valoración anterior.")
    elif p == 19:
        motivo = resp.get("motivo")
        if not motivo:
            errores.append("Seleccione un Motivo.")
        elif motivo == na.MOTIVO_OTROS and not (resp.get("obs") or "").strip():
            errores.append("Con el motivo 'Otros' las observaciones son obligatorias.")
    elif p == 9:
        if resp.get("fi") is None:
            errores.append("Debe responder si posee Certificado de Instructor de FP (FI).")
    elif p == 14:
        if resp.get("form_sup") is None:
            errores.append("Debe responder sobre Formación Superior en FP.")
    elif p == 18:
        if resp.get("art59") is None:
            errores.append("Debe responder sobre el Art. 59 del Estatuto Docente.")
    return errores


def primer_paso_invalido(resp: dict) -> int:
    ruta = ruta_activa(resp)
    for p in ruta:
        if validar_paso(p, resp):
            return p
    return ruta[-1]


def validar_todo(resp: dict) -> list[str]:
    ruta = ruta_activa(resp)
    todos = []
    for p in ruta:
        errs = validar_paso(p, resp)
        for e in errs:
            nom_p = "8B" if p == 19 else str(p)
            todos.append(f"Paso {nom_p}: {e}")
    return todos


PASOS_PRECARGADOS_SALTAR = {9, 14, 15, 16, 17}


def siguiente_paso_idx(p_actual: int, ruta: list[int], saltar_precargados: bool, es_otro_curso: bool) -> int:
    idx = ruta.index(p_actual)
    for sig in ruta[idx + 1:]:
        if es_otro_curso and saltar_precargados and sig in PASOS_PRECARGADOS_SALTAR:
            continue
        return sig
    return p_actual


def anterior_paso_idx(p_actual: int, ruta: list[int], saltar_precargados: bool, es_otro_curso: bool) -> int:
    idx = ruta.index(p_actual)
    sub = list(reversed(ruta[:idx]))
    for ant in sub:
        if es_otro_curso and saltar_precargados and ant in PASOS_PRECARGADOS_SALTAR:
            continue
        return ant
    return p_actual


# --------------------------------------------------------------------------- #
# Calculadoras de Capacitación R y S
# --------------------------------------------------------------------------- #
def _agregar_cert(p: str) -> None:
    ss = st.session_state
    resp = ss.resp
    h_key = wk(f"h_{p}")
    u_key = wk(f"u_{p}")
    desc_key = wk(f"desc_{p}")
    horas = ss.get(h_key, 0)
    if not horas or horas <= 0:
        st.toast("Ingrese una cantidad de horas mayor a 0.", icon="⚠️")
        return
    unidad = ss.get(u_key, CAL_RELOJ)
    desc = (ss.get(desc_key) or "").strip()
    resp[f"cert_{p}"].append({"desc": desc, "horas": int(horas), "unidad": unidad})
    # Reset widget state
    ss[h_key] = 0
    ss[desc_key] = ""


def _quitar_cert(p: str, i: int) -> None:
    lista = st.session_state.resp.get(f"cert_{p}", [])
    if 0 <= i < len(lista):
        lista.pop(i)


def calculadora_paso(p: str, titulo: str, tipo: str, tope: float, puntos_fn) -> float:
    ss = st.session_state
    resp = ss.resp

    # Si mantiene valoración anterior, se fuerza "Puntaje directo"
    es_recurrente = resp.get("mantiene") == "Sí"
    if es_recurrente:
        resp[f"modo_{p}"] = "Puntaje directo"
        st.caption("ℹ️ Mantiene valoración anterior: tipee directamente el puntaje firme anterior.")

    modo = st.radio(
        f"{titulo}: forma de carga",
        ["Certificados", "Puntaje directo"],
        index=0 if resp[f"modo_{p}"] == "Certificados" else 1,
        horizontal=True,
        key=wk(f"modo_radio_{p}"),
        disabled=es_recurrente,
    )
    resp[f"modo_{p}"] = modo

    if modo == "Puntaje directo":
        val = st.number_input(
            f"Puntaje total (máx. {tope:.2f})",
            min_value=0.0,
            max_value=tope,
            step=0.05,
            value=float(resp.get(f"dir_{p}", 0.0) or 0.0),
            key=wk(f"dir_input_{p}"),
        )
        resp[f"dir_{p}"] = round(float(val), 2)
        return resp[f"dir_{p}"]

    # Modo Certificados
    ca, cb, cc, cd = st.columns([3, 1.2, 2.2, 1.4], vertical_alignment="bottom")
    ca.text_input("Descripción del certificado (opcional)", key=wk(f"desc_{p}"))
    cb.number_input("Horas", min_value=0, max_value=3000, step=1, key=wk(f"h_{p}"))
    cc.radio("Unidad", [CAL_RELOJ, CAL_CATEDRA], horizontal=True, key=wk(f"u_{p}"))
    cd.button("➕ Agregar", key=wk(f"btn_add_{p}"), on_click=_agregar_cert, args=(p,), **_ancho(st.button))

    certs = resp.get(f"cert_{p}", [])
    hs_reloj = []
    for i, c in enumerate(certs):
        reloj = na.convertir_hs_catedra_a_reloj(c["horas"]) if c["unidad"] == CAL_CATEDRA else c["horas"]
        hs_reloj.append(reloj)
        pts = puntos_fn(reloj)
        r1, r2 = st.columns([11, 1])
        aviso = " ⚠️ (< 5 hs = 0)" if reloj < 5 else ""
        r1.markdown(
            f"{i + 1}. {c['desc'] or 'Certificado'} — {c['horas']} {c['unidad'].lower()} "
            f"→ **{reloj} hs reloj** → **{pts:.2f} pts**{aviso}"
        )
        r2.button(
            "❌",
            key=wk(f"del_{p}_{i}"),
            on_click=_quitar_cert,
            args=(p, i),
            help="Quitar certificado",
        )

    res = na.resumen_capacitacion(hs_reloj, tipo)
    m1, m2 = st.columns(2)
    m1.metric("Suma bruta", f"{res['bruto']:.2f}")
    m2.metric(f"Aplicado (tope {res['tope']:.2f})", f"{res['total']:.2f}")
    if res["tope_aplicado"]:
        st.caption("Se alcanzó el tope máximo del ítem.")
    return res["total"]


# --------------------------------------------------------------------------- #
# Renders de cada paso individual
# --------------------------------------------------------------------------- #
def render_paso_1(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### Columna C: DNI del Aspirante")
    dni_val = st.text_input(
        "DNI (Col. C) *",
        value=resp["dni_txt"],
        key=wk("dni_txt"),
        placeholder="Ej: 26943922",
        help="Número sin puntos ni espacios.",
    )
    resp["dni_txt"] = dni_val


def render_paso_2(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### Columna D: Apellido del Aspirante")
    ap_val = st.text_input(
        "APELLIDO (Col. D) *",
        value=resp["apellido"],
        key=wk("apellido"),
        placeholder="Ej: SABORIDO",
    )
    resp["apellido"] = " ".join(ap_val.upper().split())


def render_paso_3(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### Columna E: Nombres del Aspirante")
    nom_val = st.text_input(
        "NOMBRES (Col. E) *",
        value=resp["nombres"],
        key=wk("nombres"),
        placeholder="Ej: LORENA LILIANA",
    )
    resp["nombres"] = " ".join(nom_val.upper().split())


def render_paso_4(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### Columnas G y H: Distrito 1 y Residencia")
    idx = distritos.index(resp["d1"]) if resp["d1"] in distritos else None
    d1 = st.selectbox(
        "Distrito 1 (Col. G) *",
        distritos,
        index=idx,
        placeholder="Escriba o elija el Distrito 1...",
        key=wk("d1"),
    )
    resp["d1"] = d1
    r1 = st.checkbox(
        "Coincide con el domicilio del DNI vigente → 5 pts en Col. H",
        value=resp["r1"],
        key=wk("r1"),
    )
    resp["r1"] = r1
    pts = na.puntos_residencia(r1) if d1 else None
    st.caption(f"Col. H (Puntaje de Residencia) = **{'—' if pts is None else pts}** pts")


def render_paso_5(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### Columnas I y J: Distrito 2 (Opcional) y Residencia")
    lista_d2 = [NINGUNO] + distritos
    idx = lista_d2.index(resp["d2"]) if resp["d2"] in lista_d2 else 0
    d2_sel = st.selectbox("Distrito 2 (Col. I) – opcional", lista_d2, index=idx, key=wk("d2"))
    if d2_sel == NINGUNO:
        resp["d2"] = None
        resp["r2"] = False
        st.caption("Distrito 2 deshabilitado.")
    else:
        resp["d2"] = d2_sel
        r2 = st.checkbox(
            "Coincide con el domicilio del DNI vigente → 5 pts en Col. J",
            value=resp["r2"],
            key=wk("r2"),
        )
        resp["r2"] = r2
        pts = na.puntos_residencia(r2)
        st.caption(f"Col. J (Puntaje de Residencia) = **{pts}** pts")


def render_paso_6(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### Columnas K y L: Distrito 3 (Opcional) y Residencia")
    lista_d3 = [NINGUNO] + distritos
    idx = lista_d3.index(resp["d3"]) if resp["d3"] in lista_d3 else 0
    d3_sel = st.selectbox("Distrito 3 (Col. K) – opcional", lista_d3, index=idx, key=wk("d3"))
    if d3_sel == NINGUNO:
        resp["d3"] = None
        resp["r3"] = False
        st.caption("Distrito 3 deshabilitado.")
    else:
        resp["d3"] = d3_sel
        r3 = st.checkbox(
            "Coincide con el domicilio del DNI vigente → 5 pts en Col. L",
            value=resp["r3"],
            key=wk("r3"),
        )
        resp["r3"] = r3
        pts = na.puntos_residencia(r3)
        st.caption(f"Col. L (Puntaje de Residencia) = **{pts}** pts")


def render_paso_7(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### Columna F: Especialidad (Trayecto, Curso y/o Módulo)")
    idx = cursos.index(resp["curso"]) if resp["curso"] in cursos else None
    curso = st.selectbox(
        "Especialidad (Col. F) *",
        cursos,
        index=idx,
        placeholder="Escriba el nombre o código del curso...",
        key=wk("curso"),
    )
    resp["curso"] = curso
    if curso:
        perfil = na.texto_perfil_nuevo_diseno(curso)
        if perfil:
            st.info("🔷 " + perfil)
        tipo = na.tipo_cargo(curso)
        if tipo == "panolero":
            st.warning("**Pañol (00PA):** solo valen títulos TÉCNICOS. El secundario común no otorga puntaje.")
        elif tipo == "preceptor":
            st.info("**Preceptor (00PR):** solo títulos afines a Administración, Docencia, Organización, RRHH o Informática.")

        limpio = re.sub(r"\D", "", resp.get("dni_txt") or "")
        dni = int(limpio) if limpio else None
        dups = duplicados(dni, curso)
        if dups:
            st.warning("⚠️ Ya existe una carga de este aspirante para este curso:\n- " + "\n- ".join(dups))
            resp["confirm_dup"] = st.checkbox(
                "Confirmo que deseo cargarlo de todos modos",
                value=resp["confirm_dup"],
                key=wk("confirm_dup"),
            )


def render_paso_8(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    tipo = na.tipo_cargo(resp.get("curso"))
    st.markdown(f"#### Filtro de Habilitación para el Cargo ({tipo.capitalize()})")
    opciones_hab = HAB_INSTRUCTOR if tipo == "instructor" else HAB_COMUN
    idx = opciones_hab.index(resp["hab"]) if resp["hab"] in opciones_hab else None

    hab = st.radio(
        "Indique el cumplimiento de requisitos específicos o generales:",
        opciones_hab,
        index=idx,
        key=wk(f"hab_{tipo}"),
    )
    resp["hab"] = hab

    if hab and hab != NO_MERITUA:
        resp["req_comunes"] = st.checkbox(
            "Confirmo Requisitos Comunes (Inc. 3): Anexo III oficial, DNI frente/reverso y Título registrado.",
            value=resp["req_comunes"],
            key=wk("req_comunes"),
        )
        if "Recurrente" in hab:
            st.markdown("**Inscripción Recurrente:**")
            idx_m = [SI, NO].index(resp["mantiene"]) if resp["mantiene"] in [SI, NO] else None
            mantiene = st.radio(
                "¿Mantiene la valoración anterior firme del listado previo?",
                [SI, NO],
                index=idx_m,
                horizontal=True,
                key=wk("mantiene_rad"),
            )
            resp["mantiene"] = mantiene


def render_paso_19(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### NO MERITÚA – Motivo y Observaciones (Cols. J y K)")
    idx = na.MOTIVOS_NO_MERITUADO.index(resp["motivo"]) if resp["motivo"] in na.MOTIVOS_NO_MERITUADO else 0
    resp["motivo"] = st.selectbox("Motivo (Col. J) *", na.MOTIVOS_NO_MERITUADO, index=idx, key=wk("motivo"))
    resp["obs"] = st.text_area(
        "Observaciones de la Comisión Evaluadora (Col. K)",
        value=resp["obs"],
        key=wk("obs"),
        height=100,
    )
    st.info("Al guardar, este aspirante pasará a la planilla de **NO MERITUADOS**.")

    errs = validar_todo(resp)
    for e in errs:
        st.error(e)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Guardar en NO MERITUADOS y evaluar OTRO curso del MISMO aspirante", **_ancho(st.button)):
            if errs:
                st.warning("Corrija los errores antes de guardar.")
            else:
                hoja, datos = construir_datos(resp, ss.distrito_eval, ss.incluir_residencia_ab)
                guardar(hoja, datos)
                resetear_curso()
                st.rerun()
    with c2:
        if st.button("✅ Guardar en NO MERITUADOS y cargar NUEVO aspirante", type="primary", **_ancho(st.button)):
            if errs:
                st.warning("Corrija los errores antes de guardar.")
            else:
                hoja, datos = construir_datos(resp, ss.distrito_eval, ss.incluir_residencia_ab)
                guardar(hoja, datos)
                resetear_aspirante()
                st.rerun()


def render_paso_9(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### Columna M: Certificado de Instructor de FP (FI)")
    if ss.es_otro_curso and resp["fi"] is not None:
        st.caption("✔ Precargado del curso anterior: confirme o modifique")
    opciones = [SI, NO]
    idx = 0 if resp["fi"] == na.PTS_FI else (1 if resp["fi"] == 0 else None)
    fi_sel = st.radio(
        "¿Posee Certificado de Formador/Instructor de FP (FI) registrado?",
        opciones,
        index=idx,
        horizontal=True,
        key=wk("fi"),
        format_func=lambda x: "Sí (25 pts → Listado PRINCIPAL)" if x == SI else "No (0 pts → Listado COMPLEMENTARIO)",
    )
    if fi_sel is not None:
        resp["fi"] = na.PTS_FI if fi_sel == SI else 0
        st.caption(f"Col. M = **{resp['fi']}** pts · Col. B (LISTADO) = **{na.calcular_listado(resp['fi'])}**")


def render_paso_10(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    curso = resp.get("curso")
    st.markdown("#### Columnas N a Q: Formación Específica")
    opciones_fe = na.opciones_formacion_especifica(curso)
    idx = opciones_fe.index(resp["fe_sel"]) if resp["fe_sel"] in opciones_fe else 0
    fe_sel = st.radio(
        "Título de mayor nivel vinculado al curso (selección única y excluyente):",
        opciones_fe,
        index=idx,
        key=wk("fe_sel"),
        format_func=etiqueta_formacion,
    )
    resp["fe_sel"] = fe_sel


def render_paso_11(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### Columna R: Capacitación Docente (Tope 3.00 pts)")
    r_val = calculadora_paso("doc", "Capacitación Docente", "docente", na.TOPE_CAP_DOCENTE, na.puntos_curso_docente)
    st.caption(f"Col. R = **{r_val:.2f}** pts")


def render_paso_12(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### Columna S: Capacitación Específica (Tope 5.00 pts)")
    s_val = calculadora_paso("esp", "Capacitación Específica", "especifica", na.TOPE_CAP_ESPECIFICA, na.puntos_curso_especifico)
    st.caption(f"Col. S = **{s_val:.2f}** pts")


def render_paso_13(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### Columnas T y U: Desempeño Profesional")
    t_val = st.number_input(
        "Años de desempeño laboral acreditados (Col. T)",
        min_value=0,
        max_value=na.ANIOS_DESEMPENO_MAX,
        step=1,
        value=int(resp.get("t_anios", 0)),
        key=wk("t_anios"),
    )
    resp["t_anios"] = int(t_val)
    sugerido = na.puntos_desempeno(resp["t_anios"])

    if resp.get("mantiene") == "Sí":
        idx_u = [0, 5, 6, 8].index(resp["u_prev"]) if resp["u_prev"] in [0, 5, 6, 8] else [0, 5, 6, 8].index(sugerido)
        u_sel = st.selectbox("Puntaje anterior firme (Col. U)", [0, 5, 6, 8], index=idx_u, key=wk("u_prev"))
        resp["u_prev"] = int(u_sel)
        st.caption(f"Sugerido por años: {sugerido} pts · Registrado: **{resp['u_prev']}** pts")
    else:
        st.caption(f"Col. T = **{resp['t_anios'] or '—'}** años · Col. U = **{sugerido if resp['t_anios'] else '—'}** pts")


def render_paso_14(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### Columna V: Formación Superior en el Ámbito de la FP")
    if ss.es_otro_curso and resp["form_sup"] is not None:
        st.caption("✔ Precargado del curso anterior: confirme o modifique")
    opciones = [SI, NO]
    idx = 0 if resp["form_sup"] == na.PTS_FORM_SUP_FP else (1 if resp["form_sup"] == 0 else None)
    v_sel = st.radio(
        "¿Posee Tecnicatura Universitaria/Superior en Educación Profesional o ETP para FP (con Validez Nacional)?",
        opciones,
        index=idx,
        horizontal=True,
        key=wk("form_sup"),
        format_func=lambda x: "Sí (7 pts)" if x == SI else "No (0 pts)",
    )
    if v_sel is not None:
        resp["form_sup"] = na.PTS_FORM_SUP_FP if v_sel == SI else 0
        st.caption(f"Col. V = **{resp['form_sup']}** pts")


def render_paso_15(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### Columna W: Antigüedad en Docencia Oficial")
    if ss.es_otro_curso and resp["antig_doc"] > 0:
        st.caption("✔ Precargado del curso anterior: confirme o modifique")
    w_val = st.number_input(
        "Años lectivos con Certificación de Servicios (Col. W)",
        min_value=0.0,
        max_value=60.0,
        step=0.5,
        value=float(resp.get("antig_doc", 0.0)),
        key=wk("antig_doc"),
    )
    resp["antig_doc"] = float(w_val)
    pts = na.puntos_antiguedad_docencia(resp["antig_doc"])
    st.caption(f"Col. W = **{pts:.2f}** pts ({resp['antig_doc']} años × 0.25, tope {na.TOPE_ANTIG_DOCENCIA:.2f})")


def render_paso_16(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### Columna X: Antigüedad en Ámbito de FP Oficial")
    if ss.es_otro_curso and resp["antig_fp"] > 0:
        st.caption("✔ Precargado del curso anterior: confirme o modifique")
    x_val = st.number_input(
        "Años lectivos en FP con Certificación de Servicios (Col. X)",
        min_value=0.0,
        max_value=60.0,
        step=0.5,
        value=float(resp.get("antig_fp", 0.0)),
        key=wk("antig_fp"),
    )
    resp["antig_fp"] = float(x_val)
    pts = na.puntos_antiguedad_fp(resp["antig_fp"])
    st.caption(f"Col. X = **{pts:.2f}** pts ({resp['antig_fp']} años × 0.50, tope {na.TOPE_ANTIG_FP:.2f})")


def render_paso_17(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### Columnas Y y Z: Calificaciones de los Últimos 2 Años en FP (SET 4)")
    if ss.es_otro_curso:
        st.caption("✔ Precargado del curso anterior: confirme o modifique")
    c1, c2 = st.columns(2)
    lista_c = list(CALIF_OPCIONES.keys())
    idx1 = lista_c.index(resp["calif1"]) if resp["calif1"] in lista_c else lista_c.index(CALIF_DEFECTO)
    idx2 = lista_c.index(resp["calif2"]) if resp["calif2"] in lista_c else lista_c.index(CALIF_DEFECTO)
    resp["calif1"] = c1.selectbox("Calificación 1 (Col. Y)", lista_c, index=idx1, key=wk("calif1"))
    resp["calif2"] = c2.selectbox("Calificación 2 (Col. Z)", lista_c, index=idx2, key=wk("calif2"))
    st.caption(f"Col. Y = **{CALIF_OPCIONES[resp['calif1']]:.2f}** · Col. Z = **{CALIF_OPCIONES[resp['calif2']]:.2f}**")


def render_paso_18(distritos, cursos):
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### Columna AA: Art. 59 del Estatuto Docente")
    if ss.es_otro_curso and resp["art59"] is not None:
        st.caption("✔ Precargado del curso anterior: confirme o modifique")
    opciones = [SI, NO]
    idx = 0 if resp["art59"] == na.PTS_ART59 else (1 if resp["art59"] == 0 else None)
    aa_sel = st.radio(
        "¿Le corresponden 10 pts por NO poseer cargos ni horas titulares en la docencia oficial?",
        opciones,
        index=idx,
        horizontal=True,
        key=wk("art59"),
        format_func=lambda x: "Sí – Sin cargos titulares (10 pts)" if x == SI else "No – Con cargos titulares (0 pts)",
    )
    if aa_sel is not None:
        resp["art59"] = na.PTS_ART59 if aa_sel == SI else 0

    st.divider()
    if ss.es_otro_curso:
        st.markdown("##### 📋 Resumen de Datos Comunes Precargados del Aspirante")
        st.caption("Verifique los datos comunes vigentes para este legajo o salte a su paso si desea corregirlos:")
        rc1, rc2, rc3 = st.columns(3)
        rc1.markdown(f"- **DNI:** `{resp.get('dni_txt')}`\n- **Apellido y Nombres:** {resp.get('apellido')}, {resp.get('nombres')}\n- **Distrito 1:** {resp.get('d1') or '—'} (Col. H: {na.puntos_residencia(resp.get('r1')) if resp.get('d1') else '—'} pts)")
        rc2.markdown(f"- **Certificado FI (Col. M):** {resp.get('fi')} pts ({na.calcular_listado(resp.get('fi')) if resp.get('fi') in (0, na.PTS_FI) else '—'})\n- **Form. Superior FP (Col. V):** {resp.get('form_sup') or 0} pts\n- **Art. 59 (Col. AA):** {resp.get('art59') or 0} pts")
        pts_w = na.puntos_antiguedad_docencia(resp.get('antig_doc', 0.0))
        pts_x = na.puntos_antiguedad_fp(resp.get('antig_fp', 0.0))
        rc3.markdown(f"- **Antigüedad Doc. (Col. W):** {pts_w:.2f} pts\n- **Antigüedad FP (Col. X):** {pts_x:.2f} pts\n- **Calificaciones (Y, Z):** {CALIF_OPCIONES.get(resp.get('calif1'), 0.0):.2f} / {CALIF_OPCIONES.get(resp.get('calif2'), 0.0):.2f} pts")
        st.divider()

    st.markdown("##### Resumen y Guardado de la Evaluación")
    hoja, datos = construir_datos(resp, ss.distrito_eval, ss.incluir_residencia_ab)
    calc = na.calcular_ab(datos, ss.distrito_eval, ss.incluir_residencia_ab)

    r1, r2, r3 = st.columns(3)
    r1.metric("Puntaje Base", f"{calc['base']:.2f}")
    r2.metric("Puntaje con +5 de Residencia", f"{calc['con_residencia']:.2f}")
    r3.metric("PUNTAJE (Col. AB) a guardar", f"{calc['ab']:.2f}")

    errs = validar_todo(resp)
    for e in errs:
        st.error(e)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Guardar y evaluar OTRO curso del MISMO aspirante", **_ancho(st.button)):
            if errs:
                st.warning("Corrija los pasos incompletos antes de guardar.")
            else:
                guardar(hoja, datos)
                resetear_curso()
                st.rerun()
    with c2:
        if st.button("✅ Guardar y cargar NUEVO aspirante", type="primary", **_ancho(st.button)):
            if errs:
                st.warning("Corrija los pasos incompletos antes de guardar.")
            else:
                guardar(hoja, datos)
                resetear_aspirante()
                st.rerun()


PASOS = {
    1: {"titulo": "DNI", "cols": "C", "ayuda": ["P1"], "resalta": ["C"], "render": render_paso_1},
    2: {"titulo": "APELLIDO", "cols": "D", "ayuda": ["P2"], "resalta": ["D"], "render": render_paso_2},
    3: {"titulo": "NOMBRES", "cols": "E", "ayuda": ["P3"], "resalta": ["E"], "render": render_paso_3},
    4: {"titulo": "Distrito 1 y Residencia", "cols": "G, H", "ayuda": ["P5"], "resalta": ["G", "H"], "render": render_paso_4},
    5: {"titulo": "Distrito 2 y Residencia", "cols": "I, J", "ayuda": ["P6"], "resalta": ["I", "J"], "render": render_paso_5},
    6: {"titulo": "Distrito 3 y Residencia", "cols": "K, L", "ayuda": ["P7"], "resalta": ["K", "L"], "render": render_paso_6},
    7: {"titulo": "Especialidad / Curso", "cols": "F", "ayuda": ["P4", "PERFILES_NUEVOS"], "resalta": ["F"], "render": render_paso_7},
    8: {"titulo": "Habilitación", "cols": "Filtro", "ayuda": ["HABILITACION", "HAB_INC6", "HAB_6_1_1", "HAB_6_1_2", "HAB_6_2_1", "HAB_6_2_2", "HAB_6_2_3"], "resalta": [], "render": render_paso_8},
    19: {"titulo": "NO MERITÚA – Motivo y Obs.", "cols": "J, K", "ayuda": ["HABILITACION"], "resalta": ["J", "K"], "render": render_paso_19},
    9: {"titulo": "Certificado FI", "cols": "B, M", "ayuda": ["P8"], "resalta": ["B", "M"], "render": render_paso_9},
    10: {"titulo": "Formación Específica", "cols": "N, O, P, Q", "ayuda": ["P9"], "resalta": ["N", "O", "P", "Q"], "render": render_paso_10},
    11: {"titulo": "Capacitación Docente", "cols": "R", "ayuda": ["P10"], "resalta": ["R"], "render": render_paso_11},
    12: {"titulo": "Capacitación Específica", "cols": "S", "ayuda": ["P11"], "resalta": ["S"], "render": render_paso_12},
    13: {"titulo": "Desempeño Profesional", "cols": "T, U", "ayuda": ["P12"], "resalta": ["T", "U"], "render": render_paso_13},
    14: {"titulo": "Formación Superior en FP", "cols": "V", "ayuda": ["P13"], "resalta": ["V"], "render": render_paso_14},
    15: {"titulo": "Antigüedad Docencia Oficial", "cols": "W", "ayuda": ["P14"], "resalta": ["W"], "render": render_paso_15},
    16: {"titulo": "Antigüedad Ámbito FP", "cols": "X", "ayuda": ["P15"], "resalta": ["X"], "render": render_paso_16},
    17: {"titulo": "Calificaciones", "cols": "Y, Z", "ayuda": ["P16"], "resalta": ["Y", "Z"], "render": render_paso_17},
    18: {"titulo": "Art. 59 del Estatuto Docente", "cols": "AA, AB", "ayuda": ["P17"], "resalta": ["AA", "AB"], "render": render_paso_18},
}


# --------------------------------------------------------------------------- #
# Guardado y Reinicio
# --------------------------------------------------------------------------- #
def guardar(hoja: str, datos: dict) -> None:
    ss = st.session_state
    item = {"id": ss.sig_id, "hoja": hoja, "datos": datos}
    ss.sig_id += 1
    ss.registros.append(item)
    ss.ver_tabla += 1
    dest = "MERITUADOS" if hoja == HOJA_MER else "NO MERITUADOS"
    ss.flash = f"✅ Curso guardado en {dest}: {datos['apellido']}, {datos['nombres']} – {datos['especialidad']}."
    guardar_disco()


def resetear_curso() -> None:
    ss = st.session_state
    ant = ss.resp
    nuevo = nueva_resp()
    for k in CAMPOS_COMUNES:
        nuevo[k] = copy.deepcopy(ant[k])
    ss.resp = nuevo
    ss.ver += 1
    ss.es_otro_curso = True
    ss.paso_actual = 7


def resetear_aspirante() -> None:
    ss = st.session_state
    ss.resp = nueva_resp()
    ss.ver += 1
    ss.es_otro_curso = False
    ss.paso_actual = 1


# --------------------------------------------------------------------------- #
# Columna Izquierda: Asistente y Navegación
# --------------------------------------------------------------------------- #
def panel_asistente_izq(distritos: list[str], cursos: list[str]) -> None:
    ss = st.session_state
    resp = ss.resp
    ruta = ruta_activa(resp)

    if ss.paso_actual not in ruta:
        ss.paso_actual = ruta[0]

    p = ss.paso_actual
    paso_def = PASOS[p]

    progreso = (ruta.index(p) + 1) / len(ruta)
    p_num_lbl = "8B" if p == 19 else str(p)
    st.markdown(f"### Paso {p_num_lbl} de {len(ruta)} · Col. {paso_def['cols']}")
    st.progress(progreso)

    # Render del widget del paso activo
    paso_def["render"](distritos, cursos)

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    st.divider()

    # Barra de navegación
    c_ant, c_sel, c_sig = st.columns([1.3, 2.2, 1.3], vertical_alignment="center")

    with c_ant:
        ant_p = anterior_paso_idx(p, ruta, ss.saltar_precargados, ss.es_otro_curso)
        deshab_ant = p == ruta[0]
        if st.button("⬅️ Anterior", disabled=deshab_ant, key=wk("btn_ant"), **_ancho(st.button)):
            ss.paso_actual = ant_p
            st.rerun()

    with c_sel:
        # Selector compacto de pasos
        opciones_sel = [p_i for p_i in ruta]
        limite_invalido = primer_paso_invalido(resp)
        idx_limite = ruta.index(limite_invalido) if limite_invalido in ruta else len(ruta) - 1

        def _formato_sel(item_p):
            lbl = "8B" if item_p == 19 else str(item_p)
            return f"Paso {lbl}: {PASOS[item_p]['titulo']}"

        idx_curr = opciones_sel.index(p)
        sel_p = st.selectbox(
            "Ir al paso:",
            opciones_sel,
            index=idx_curr,
            format_func=_formato_sel,
            key=f"sel_nav_{p}",
            label_visibility="collapsed",
        )
        if sel_p != p:
            idx_elegido = ruta.index(sel_p)
            if idx_elegido > idx_limite:
                st.toast("Complete los pasos anteriores antes de saltar hacia adelante.", icon="⚠️")
            else:
                ss.paso_actual = sel_p
                st.rerun()

    with c_sig:
        if p in (18, 19):
            st.write("")
        else:
            sig_p = siguiente_paso_idx(p, ruta, ss.saltar_precargados, ss.es_otro_curso)
            if st.button("Siguiente ➡️", type="primary", key=wk("btn_sig"), **_ancho(st.button)):
                errs = validar_paso(p, resp)
                if errs:
                    for e in errs:
                        st.error(e)
                else:
                    ss.paso_actual = sig_p
                    st.rerun()

    if ss.es_otro_curso:
        st.checkbox(
            "Saltar automáticamente preguntas comunes ya precargadas (Cols. M, V, W, X, Y, Z)",
            value=ss.saltar_precargados,
            key="saltar_precargados",
            help="Si está tildado, la navegación avanza directo a las preguntas exclusivas de este curso.",
        )


# --------------------------------------------------------------------------- #
# Columna Derecha: Panel de Ayuda Normativa Dinámica
# --------------------------------------------------------------------------- #
def panel_ayuda_der() -> None:
    ss = st.session_state
    resp = ss.resp
    p = ss.paso_actual
    paso_def = PASOS.get(p, PASOS[1])
    curso = resp.get("curso")

    st.markdown(f"#### 📖 Ayuda Normativa y Ejemplos\n*Paso {'8B' if p == 19 else p} · Columna(s) {paso_def['cols']}*")

    # Si hay perfil de nuevo diseño del Anexo 2 Com 07/2026 y p >= 7
    if p >= 7 and curso:
        perfil_txt = na.texto_perfil_nuevo_diseno(curso)
        if perfil_txt:
            st.info("🔷 " + perfil_txt)

    claves = paso_def["ayuda"]
    if len(claves) == 1:
        st.markdown(na.obtener_ayuda(claves[0], curso))
    else:
        etiquetas_tab = [TAB_AYUDA.get(c, c) for c in claves]
        tabs = st.tabs(etiquetas_tab)
        for t, c in zip(tabs, claves):
            with t:
                st.markdown(na.obtener_ayuda(c, curso))


# --------------------------------------------------------------------------- #
# Sección Inferior 1: Vista en Tiempo Real del Aspirante Activo (A-AB)
# --------------------------------------------------------------------------- #
def preview_en_vivo() -> None:
    ss = st.session_state
    resp = ss.resp
    st.markdown("#### 1. Vista en tiempo real del aspirante en evaluación")
    hoja, datos = construir_datos(resp, ss.distrito_eval, ss.incluir_residencia_ab)

    cols_resaltar_letras = PASOS.get(ss.paso_actual, {}).get("resalta", [])

    if hoja == HOJA_NO:
        cols_cfg = COLS_OFICIALES_NO_MER
    else:
        cols_cfg = COLS_OFICIALES_MER

    fila = {}
    cols_nombres = []
    cols_a_estilar = []
    orden_act = _orden_siguiente(hoja)

    for clave, letra, etiqueta in cols_cfg:
        col_nom = f"{letra} · {etiqueta}"
        cols_nombres.append(col_nom)
        val = orden_act if clave == "orden" else datos.get(clave)
        fila[col_nom] = fmt(val)
        if letra in cols_resaltar_letras:
            cols_a_estilar.append(col_nom)

    df_p = pd.DataFrame([fila], columns=cols_nombres)

    if cols_a_estilar:
        styled = df_p.style.set_properties(
            subset=cols_a_estilar,
            **{"background-color": "#fff3bf", "color": "#000000", "font-weight": "bold"},
        )
        st.dataframe(styled, hide_index=True, **_ancho(st.dataframe))
    else:
        st.dataframe(df_p, hide_index=True, **_ancho(st.dataframe))

    if hoja == HOJA_MER:
        calc = na.calcular_ab(datos, ss.distrito_eval, ss.incluir_residencia_ab)
        c1, c2, c3 = st.columns(3)
        c1.metric("Puntaje base (sin residencia)", f"{calc['base']:.2f}")
        c2.metric(
            "Puntaje con +5 pts por residencia",
            f"{calc['con_residencia']:.2f}",
            help="Suma 5 pts si algún distrito coincide con el domicilio del DNI vigente.",
        )
        tiene_res = na.residencia_en_distrito_evaluador(datos, ss.distrito_eval)
        ayuda_ab = (
            "Col. AB guarda el puntaje base (sin residencia)."
            if not ss.incluir_residencia_ab
            else (
                "Col. AB incluye +5 pts por residencia acreditada en el Distrito Evaluador."
                if tiene_res
                else f"Col. AB guarda puntaje base: el aspirante no acredita residencia en {ss.distrito_eval}."
            )
        )
        c3.metric("PUNTAJE (Col. AB) a guardar", f"{calc['ab']:.2f}", help=ayuda_ab)


# --------------------------------------------------------------------------- #
# Sección Inferior 2: Planilla General Editable (st.data_editor)
# --------------------------------------------------------------------------- #
def grilla_general(cursos: list[str], distritos: list[str]) -> None:
    ss = st.session_state
    st.markdown("#### 2. Planilla general")

    tabs = st.tabs([
        f"MERITUADOS ({len(_registros(HOJA_MER))})",
        f"NO MERITUADOS ({len(_registros(HOJA_NO))})",
    ])

    for pestana, hoja in zip(tabs, (HOJA_MER, HOJA_NO)):
        with pestana:
            items = _registros(hoja)
            if not items:
                st.info("No hay aspirantes cargados en esta planilla todavía.")
                continue

            base_orden = resumen_base(_mtime())["meritudos" if hoja == HOJA_MER else "no_meritudos"]

            cols_def = COLS_OFICIALES_MER if hoja == HOJA_MER else COLS_OFICIALES_NO_MER
            col_a_clave = {f"{letra} · {etiq}": clave for clave, letra, etiq in cols_def}

            filas = []
            for i, it in enumerate(items):
                d = it["datos"]
                f_dict = {"🗑": False}
                for clave, letra, etiq in cols_def:
                    col_nom = f"{letra} · {etiq}"
                    if clave == "orden":
                        f_dict[col_nom] = base_orden + i + 1
                    else:
                        f_dict[col_nom] = d.get(clave)
                filas.append(f_dict)

            df = pd.DataFrame(filas)

            # Configuraciones de columna
            cfg = {"🗑": st.column_config.CheckboxColumn("🗑", default=False, help="Marcar para eliminar")}
            cfg["A · ORDEN"] = st.column_config.NumberColumn("A · ORDEN", disabled=True)
            if hoja == HOJA_MER:
                cfg["B · LISTADO"] = st.column_config.TextColumn("B · LISTADO", disabled=True)
                cfg["C · DNI"] = st.column_config.NumberColumn("C · DNI", format="%d", step=1)
                cfg["D · APELLIDO"] = st.column_config.TextColumn("D · APELLIDO")
                cfg["E · NOMBRES"] = st.column_config.TextColumn("E · NOMBRES")
                cfg["F · ESPECIALIDAD (TRAYECTO, CURSO Y/O MÓDULO)"] = st.column_config.SelectboxColumn(
                    "F · ESPECIALIDAD (TRAYECTO, CURSO Y/O MÓDULO)", options=cursos
                )
                cfg["G · Distrito 1"] = st.column_config.SelectboxColumn("G · Distrito 1", options=distritos)
                cfg["H · ptos."] = st.column_config.NumberColumn("H · ptos.", min_value=0, max_value=5, step=5)
                cfg["I · Distrito 2"] = st.column_config.SelectboxColumn("I · Distrito 2", options=[None] + distritos)
                cfg["J · ptos."] = st.column_config.NumberColumn("J · ptos.", min_value=0, max_value=5, step=5)
                cfg["K · Distrito 3"] = st.column_config.SelectboxColumn("K · Distrito 3", options=[None] + distritos)
                cfg["L · ptos."] = st.column_config.NumberColumn("L · ptos.", min_value=0, max_value=5, step=5)
                cfg["M · INSTRUCTOR DE FP – FI"] = st.column_config.NumberColumn("M · INSTRUCTOR DE FP – FI", min_value=0, max_value=25, step=25)
                cfg["N · FORMACIÓN ESPECÍFICA – Secundario"] = st.column_config.NumberColumn("N · Secundario", min_value=0, max_value=3, step=3)
                cfg["O · FORMACIÓN ESPECÍFICA – Sec. técnico"] = st.column_config.NumberColumn("O · Sec. técnico", min_value=0, max_value=5, step=5)
                cfg["P · FORMACIÓN ESPECÍFICA – Superior"] = st.column_config.NumberColumn("P · Superior", min_value=0, max_value=7, step=7)
                cfg["Q · FORMACIÓN ESPECÍFICA – Universitario"] = st.column_config.NumberColumn("Q · Universitario", min_value=0, max_value=8, step=8)
                cfg["R · CAPACITACIÓN DOCENTE"] = st.column_config.NumberColumn("R · CAPACITACIÓN DOCENTE", min_value=0.0, max_value=3.0, step=0.05, format="%.2f")
                cfg["S · CAPACITACIÓN ESPECÍFICA"] = st.column_config.NumberColumn("S · CAPACITACIÓN ESPECÍFICA", min_value=0.0, max_value=5.0, step=0.05, format="%.2f")
                cfg["T · DESEMPEÑO PROFESIONAL – años"] = st.column_config.NumberColumn("T · AÑOS", min_value=0, max_value=35, step=1, format="%d")
                cfg["U · DESEMPEÑO PROFESIONAL – pts"] = st.column_config.NumberColumn("U · DESEMP. PTS", min_value=0, max_value=8, step=1)
                cfg["V · FORMACIÓN SUPERIOR EN FP"] = st.column_config.NumberColumn("V · FORMACIÓN SUPERIOR EN FP", min_value=0, max_value=7, step=7)
                cfg["W · ANTIGÜEDAD DOCENCIA OFICIAL"] = st.column_config.NumberColumn("W · ANTIGÜEDAD DOCENCIA", min_value=0.0, max_value=2.5, step=0.25, format="%.2f")
                cfg["X · ANTIGÜEDAD ÁMBITO FP OFICIAL"] = st.column_config.NumberColumn("X · ANTIGÜEDAD FP", min_value=0.0, max_value=5.0, step=0.5, format="%.2f")
                cfg["Y · CALIFICACIÓN 1"] = st.column_config.NumberColumn("Y · CALIF 1", min_value=0.0, max_value=1.0, step=0.1, format="%.2f")
                cfg["Z · CALIFICACIÓN 2"] = st.column_config.NumberColumn("Z · CALIF 2", min_value=0.0, max_value=1.0, step=0.1, format="%.2f")
                cfg["AA · ART 59 DEL ESTATUTO DOCENTE"] = st.column_config.NumberColumn("AA · ART 59", min_value=0, max_value=10, step=10)
                cfg["AB · PUNTAJE"] = st.column_config.NumberColumn("AB · PUNTAJE", disabled=True, format="%.2f")
            else:
                cfg["C · DNI"] = st.column_config.NumberColumn("C · DNI", format="%d", step=1)
                cfg["D · APELLIDO"] = st.column_config.TextColumn("D · APELLIDO")
                cfg["E · NOMBRES"] = st.column_config.TextColumn("E · NOMBRES")
                cfg["F · ESPECIALIDAD"] = st.column_config.SelectboxColumn("F · ESPECIALIDAD", options=cursos)
                cfg["G · Distrito 1"] = st.column_config.SelectboxColumn("G · Distrito 1", options=distritos)
                cfg["H · Distrito 2"] = st.column_config.SelectboxColumn("H · Distrito 2", options=[None] + distritos)
                cfg["I · Distrito 3"] = st.column_config.SelectboxColumn("I · Distrito 3", options=[None] + distritos)
                cfg["J · NO MERITUA / MOTIVO"] = st.column_config.SelectboxColumn("J · MOTIVO", options=na.MOTIVOS_NO_MERITUADO)
                cfg["K · OBSERVACIONES DE LA COMISIÓN EVALUADORA"] = st.column_config.TextColumn("K · OBSERVACIONES")

            editor_key = f"editor_{hoja}_{ss.ver_tabla}"
            st.data_editor(
                df,
                hide_index=True,
                num_rows="fixed",
                height=350,
                column_config=cfg,
                key=editor_key,
                **_ancho(st.data_editor),
            )

            # Procesamiento de ediciones
            estado_editor = ss.get(editor_key)
            edited_rows = (estado_editor or {}).get("edited_rows", {})

            # Detección de filas marcadas para eliminar
            marcadas_indices = []
            filas_con_datos_editados = {}

            for idx_fila_str, cambios in edited_rows.items():
                idx_f = int(idx_fila_str)
                solo_tacho = True
                for col_name, val_nuevo in cambios.items():
                    if col_name == "🗑":
                        if val_nuevo:
                            marcadas_indices.append(idx_f)
                    else:
                        solo_tacho = False
                if not solo_tacho:
                    filas_con_datos_editados[idx_f] = cambios

            # Botón de eliminación en popover
            c_del, _ = st.columns([2, 5])
            with c_del.popover(
                f"🗑️ Eliminar filas seleccionadas ({len(marcadas_indices)})",
                disabled=len(marcadas_indices) == 0,
                **_ancho(st.popover),
            ):
                st.warning(f"¿Confirma eliminar las {len(marcadas_indices)} fila(s) seleccionadas?")
                if st.button("Sí, confirmar eliminación", type="primary", key=f"conf_del_{hoja}"):
                    ids_a_borrar = [items[i]["id"] for i in marcadas_indices if i < len(items)]
                    ss.registros = [r for r in ss.registros if r["id"] not in ids_a_borrar]
                    ss.ver_tabla += 1
                    guardar_disco()
                    ss.flash = f"🗑️ Se eliminaron {len(ids_a_borrar)} registro(s)."
                    st.rerun()

            # Aplicar modificaciones de celdas si las hubiera
            if filas_con_datos_editados:
                todos_avisos = []
                for idx_f, cambios in filas_con_datos_editados.items():
                    if idx_f >= len(items):
                        continue
                    item = items[idx_f]
                    anterior = item["datos"]
                    nuevo = dict(anterior)
                    for col_name, val_nuevo in cambios.items():
                        if col_name in col_a_clave:
                            clave = col_a_clave[col_name]
                            nuevo[clave] = val_nuevo

                    if hoja == HOJA_MER:
                        norm_datos, avisos = na.normalizar_edicion_meritudo(anterior, nuevo)
                        calc = na.calcular_ab(norm_datos, ss.distrito_eval, ss.incluir_residencia_ab)
                        norm_datos["puntaje"] = calc["ab"]
                    else:
                        norm_datos, avisos = na.normalizar_edicion_no_meritudo(anterior, nuevo)

                    item["datos"] = norm_datos
                    todos_avisos.extend(avisos)

                ss.ver_tabla += 1
                guardar_disco()
                ss.flash = "✏️ Fila(s) actualizada(s) correctamente."
                if todos_avisos:
                    for av in todos_avisos:
                        st.toast(av, icon="ℹ️")
                st.rerun()


# --------------------------------------------------------------------------- #
# Función Principal (main)
# --------------------------------------------------------------------------- #
def main() -> None:
    init_estado()
    sanear_resp()

    try:
        cursos, distritos = listas(_mtime())
    except Exception as exc:  # noqa: BLE001
        st.error(f"No se pudo leer la planilla base: {exc}")
        st.stop()

    top_bar(distritos)

    if st.session_state.flash:
        st.success(st.session_state.flash)
        st.session_state.flash = None

    # Mitad superior dividida en dos contenedores con borde
    col_izq, col_der = st.columns([1, 1])

    with col_izq:
        with st.container(border=True, height=520):
            panel_asistente_izq(distritos, cursos)

    with col_der:
        with st.container(border=True, height=520):
            panel_ayuda_der()

    # Rectángulo inferior de ancho completo
    with st.container(border=True):
        preview_en_vivo()
        st.divider()
        grilla_general(cursos, distritos)


if __name__ == "__main__":
    main()
