"""
generar_datos_web.py - SCRIPT PUENTE GENERADOR
Extrae los datos de extractor_datos.py y normativa_ayuda.py,
copia PLANILLA DE DATOS DE ASPIRANTES.xlsx a docs/plantilla.xlsx,
y genera docs/datos.js (window.DATOS_APP = { ... }) para la aplicación web estática.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import extractor_datos
import normativa_ayuda

BASE_DIR = Path(__file__).resolve().parent
DIR_DOCS = BASE_DIR / "docs"
RUTA_PLANTILLA_ORIGINAL = BASE_DIR / "PLANILLA DE DATOS DE ASPIRANTES.xlsx"
RUTA_PLANTILLA_DESTINO = DIR_DOCS / "plantilla.xlsx"
RUTA_DATOS_JS = DIR_DOCS / "datos.js"


def serializar_perfil(p: dict) -> dict:
    """Convierte tuplas en listas para JSON."""
    d = dict(p)
    if "claves" in d:
        d["claves"] = [list(c) for c in d["claves"]]
    return d


def main() -> None:
    print("[1/3] Creando directorio docs/ si no existe...")
    DIR_DOCS.mkdir(parents=True, exist_ok=True)

    print("[2/3] Copiando planilla Excel oficial a docs/plantilla.xlsx...")
    if not RUTA_PLANTILLA_ORIGINAL.exists():
        raise FileNotFoundError(f"No se encontró la plantilla original en {RUTA_PLANTILLA_ORIGINAL}")
    shutil.copy2(RUTA_PLANTILLA_ORIGINAL, RUTA_PLANTILLA_DESTINO)
    print(f"      Copiado exitosamente ({RUTA_PLANTILLA_DESTINO.stat().st_size:,} bytes).")

    print("[3/3] Extrayendo datos de la aplicación y generando docs/datos.js...")
    cursos, distritos = extractor_datos.cargar_listas()
    familias = extractor_datos.FAMILIAS_PROFESIONALES
    distritos_prioritarios = list(extractor_datos.CODIGOS_PRIORITARIOS_REG10)
    cursos_2027 = extractor_datos.CURSOS_CATALOGO_2027_INICIALES

    # Formatear tablas de capacitación
    def conv_tabla(t):
        res = []
        for d, h, pts in t:
            res.append([d, h, float(pts)])
        return res

    tabla_cap_doc = conv_tabla(normativa_ayuda.TABLA_CAP_DOCENTE)
    tabla_cap_esp = conv_tabla(normativa_ayuda.TABLA_CAP_ESPECIFICA)
    tabla_desemp = [[d, h, pts] for d, h, pts in normativa_ayuda.TABLA_DESEMPENO]

    # Formatear perfiles
    perfiles = [serializar_perfil(p) for p in normativa_ayuda.PERFILES_NUEVOS_DISENOS]

    datos_app = {
        "version": 1,
        "generado": datetime.now().isoformat(),
        "distritos": distritos,
        "distritosPrioritarios": distritos_prioritarios,
        "cursos": cursos,
        "familias": familias,
        "cursosIniciales2027": cursos_2027,
        "ayudas": normativa_ayuda.AYUDAS,
        "perfilesAnexo2": perfiles,
        "grupoTelecom": normativa_ayuda._GRUPO_TELECOM,
        "tablasPuntaje": {
            "capDocente": tabla_cap_doc,
            "capEspecifica": tabla_cap_esp,
            "desempeno": tabla_desemp,
        },
        "topes": {
            "capDocente": float(normativa_ayuda.TOPE_CAP_DOCENTE),
            "capEspecifica": float(normativa_ayuda.TOPE_CAP_ESPECIFICA),
            "antigDocencia": float(normativa_ayuda.TOPE_ANTIG_DOCENCIA),
            "antigFp": float(normativa_ayuda.TOPE_ANTIG_FP),
        },
        "puntosFijos": {
            "fi": int(normativa_ayuda.PTS_FI),
            "residencia": int(normativa_ayuda.PTS_RESIDENCIA),
            "formSupFp": int(normativa_ayuda.PTS_FORM_SUP_FP),
            "art59": int(normativa_ayuda.PTS_ART59),
            "ptsXAnioDocencia": float(normativa_ayuda.PTS_X_ANIO_DOCENCIA),
            "ptsXAnioFp": float(normativa_ayuda.PTS_X_ANIO_FP),
        },
        "opcionesFormacion": normativa_ayuda.OPCIONES_FORMACION_ESPECIFICA,
        "opcionesFormacionPanol": normativa_ayuda.OPCIONES_FORMACION_PANOL,
        "opcionesCalificacion": normativa_ayuda.OPCIONES_ESCALA_CALIFICACION,
        "motivosNoMerituado": normativa_ayuda.MOTIVOS_NO_MERITUADO,
        "columnasMer": extractor_datos.COL_MER,
        "columnasNoMer": extractor_datos.COL_NO_MER,
    }

    contenido_js = (
        "// Archivo generado automáticamente por generar_datos_web.py - NO EDITAR A MANO\n"
        "// Contiene los catálogos oficiales, reglas y ayudas de la Comisión Evaluadora FP (Listados 2027)\n"
        f"window.DATOS_APP = {json.dumps(datos_app, ensure_ascii=False, indent=2)};\n"
    )

    RUTA_DATOS_JS.write_text(contenido_js, encoding="utf-8")
    print("\n[OK] Proceso completado con exito. Los datos estan listos en docs/.")


if __name__ == "__main__":
    main()
