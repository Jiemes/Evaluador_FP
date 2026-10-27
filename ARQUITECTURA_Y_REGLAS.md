# ARQUITECTURA Y REGLAS DE NEGOCIO
## Evaluador FP – Región 10 (Pcia. de Buenos Aires) – Listados 2027

> **Documento rector.** Los modelos que programen cada módulo deben leer **solo** este archivo
> (y el módulo que les toque). Si algo no está acá, **no inventar**: dejar un `# TODO(decisión)` y avisar.

---

## 0. Objetivo y alcance

App web **local** (Streamlit + OpenPyXL) que guía a un evaluador de la Comisión Evaluadora FP, pregunta por
pregunta, y vuelca el resultado en `PLANILLA DE DATOS DE ASPIRANTES.xlsx`:

- Aspirante que **cumple** requisitos → fila nueva en hoja `MERITUADOS` con puntajes calculados.
- Aspirante que **no cumple** → fila nueva en hoja `NO MERITUADOS` con motivo y observaciones.

Fuera de alcance: login, base de datos, multiusuario, internet.

---

## 1. Estructura de carpetas

```
evaluador_fp_reg10/
├── ARQUITECTURA_Y_REGLAS.md          (este archivo)
├── PLANILLA DE DATOS DE ASPIRANTES.xlsx   (ORIGINAL – nunca se modifica)
├── requirements.txt                  (streamlit, openpyxl)
├── extractor_datos.py                (MÓDULO 1 – I/O con Excel, sin Streamlit)
├── normativa_ayuda.py                (MÓDULO 2 – reglas/cálculos/textos, sin Streamlit ni Excel)
├── app.py                            (MÓDULO 3 – interfaz Streamlit, orquesta 1 y 2)
└── salida/
    └── PLANILLA_TRABAJO.xlsx         (copia de trabajo, la crea extractor_datos en el primer guardado)
```

Ejecución: `streamlit run app.py`

### Dependencias entre módulos (estrictamente en una dirección)

```
app.py ──► extractor_datos.py
   └─────► normativa_ayuda.py
(extractor_datos y normativa_ayuda NO se importan entre sí)
```

### Orden de programación sugerido (un modelo liviano, un turno por módulo)

1. `normativa_ayuda.py` (puro, testeable con `assert`, sin dependencias).
2. `extractor_datos.py` (probar contra el .xlsx real).
3. `app.py` (usa lo anterior; no recalcula nada por su cuenta).

---

## 2. Hallazgos de la planilla real (verificados leyendo el archivo)

Hojas: `MERITUADOS`, `Hoja 2`, `NO MERITUADOS`.

| Tema | Hecho verificado |
|---|---|
| Distrito evaluador | `D1` de ambas hojas, ej. `Reg 10 Distrito: 067-MARCOS PAZ`. |
| Código cobertura | `D2` (ej. `00PA - Pañol`) es informativo; **no tocar**. |
| Encabezados | Filas 4–8 (fusionadas). Datos desde **fila 9** (vacía hoy). |
| `MERITUADOS` columnas | A..AB (datos). A partir de AJ hay **tablas auxiliares con fórmulas** (`AL = CONCATENATE(...)`, `AO = INT(AP*60/40)`): **no tocar nada fuera de A..AB**. Dimensión hoy A1:AP542. |
| `NO MERITUADOS` columnas | **Distinta distribución**: `G`=Distrito 1, `H`=Distrito 2, `I`=Distrito 3 (**sin columnas de puntos**), `J`=Motivo, `K`=Observaciones. Auxiliares desde `R`. |
| `Hoja 2` | **Sin encabezados.** Col **A** desde `A1`: cursos con formato `CÓDIGO - Nombre` (ej. `AA01 - Operario Apícola`; incluye `00PA - Pañol`, `00PR - Preceptor`). Col **C** desde `C1`: distritos con formato `Reg N Distrito: NNN-NOMBRE` (de **todas** las regiones; **con repetidos**, ej. C1 y C2 iguales). Otras columnas (B, E, F, H, I) son auxiliares: ignorar. |
| Escala de ayuda en planilla | `M6`=25 pts, `N6`=3, `O6`=5, `P6`=7, `Q6`=8, `R6` tope 3, `S6` tope 5, `T/U` 3 años=5, 5 años=6, 10+=8, `V6`=7, `W6` tope 2,5, `X6` tope 5, `Y6/Z6` tope 1, `AA6`=10. Coincide con este documento. |
| Encabezado `AB4` | "PUNTAJE utilizar punto teclado" → **escribir números reales (float), nunca texto con coma**. |

> **Acción obligatoria para `extractor_datos.py`:** no asumir la cantidad de filas de `Hoja 2`; leer hasta que
> las celdas estén vacías, `strip()`, descartar vacíos, **eliminar duplicados conservando orden**.
> 335 cursos y 94 distritos son solo **valores esperados** para un `st.caption` informativo; **jamás** hardcodear listas.
> Nota: si tras deduplicar la col C trae más de un solo regional, el selector debe permitir **buscar por texto**
> (`st.selectbox` ya filtra al escribir) y ofrecer primero los de `Reg 10`.

---

## 3. Mapa de columnas (constantes en `extractor_datos.py`)

### 3.1 Hoja `MERITUADOS` (fila ≥ 9)

| Col | Campo (clave dict) | Origen | Tipo escrito |
|---|---|---|---|
| A | `orden` | automático: siguiente correlativo | int |
| B | `listado` | automático: `PRINCIPAL` si M==25, `COMPLEMENTARIO` si M==0 | str |
| C | `dni` | P1 | int (sin puntos) |
| D | `apellido` | P2 | str MAYÚS |
| E | `nombres` | P3 | str MAYÚS |
| F | `especialidad` | P4 | str (idéntico a Hoja 2 col A) |
| G / H | `dist1` / `pts_dist1` | P5 | str / 5 ó 0 |
| I / J | `dist2` / `pts_dist2` | P6 (opcional) | str o None / 5, 0 o None |
| K / L | `dist3` / `pts_dist3` | P7 (opcional) | str o None / 5, 0 o None |
| M | `fi` | P8 | 25 ó 0 |
| N | `fe_sec_orient` | P9 | 3 ó 0 |
| O | `fe_sec_tecnico` | P9 | 5 ó 0 |
| P | `fe_superior` | P9 | 7 ó 0 |
| Q | `fe_universitario` | P9 | 8 ó 0 |
| R | `cap_docente` | P10 | float (≤3.00) |
| S | `cap_especifica` | P11 | float (≤5.00) |
| T | `desemp_anios` | P12 | int o None |
| U | `desemp_pts` | P12 | 0/5/6/8 |
| V | `form_sup_fp` | P13 | 7 ó 0 |
| W | `antig_docencia` | P14 | float (≤2.50) |
| X | `antig_fp` | P15 | float (≤5.00) |
| Y | `calif1` | P16 | float (0/0.10/0.50/1) |
| Z | `calif2` | P16 | float (0/0.10/0.50/1) |
| AA | `art59` | P17 | 10 ó 0 |
| AB | `puntaje` | cálculo final | float (2 decimales) |

### 3.2 Hoja `NO MERITUADOS` (fila ≥ 9)

| Col | Campo | Valor |
|---|---|---|
| A | `orden` | correlativo propio de esta hoja |
| B | `listado` | **vacío** (no corresponde a no meritudos) |
| C, D, E, F | `dni`, `apellido`, `nombres`, `especialidad` | igual que arriba |
| G, H, I | `dist1`, `dist2`, `dist3` | solo nombre del distrito (sin puntos) |
| J | `motivo` | uno de los 7 motivos de §5.2 |
| K | `observaciones` | texto libre de la Comisión |

> Antes de codificar: `extractor_datos.py` debe **verificar por texto de encabezado** (fila 4/5 y D1) que las
> columnas coinciden con este mapa; si no, lanzar `ErrorEstructuraPlanilla` con mensaje claro.

---

## 4. Contratos de los 3 módulos

### 4.1 `extractor_datos.py` — I/O Excel (sin `import streamlit`)

Constantes: `RUTA_ORIGINAL`, `RUTA_TRABAJO`, `FILA_INICIAL = 9`, `HOJA_MER`, `HOJA_NO_MER`, `HOJA_LISTAS = "Hoja 2"`,
`COL_MER` (dict clave→letra), `COL_NO_MER`.

```python
class ErrorEstructuraPlanilla(Exception): ...
class PlanillaBloqueada(Exception): ...        # Excel abierto -> PermissionError

def asegurar_copia_trabajo() -> Path:
    """Si no existe salida/PLANILLA_TRABAJO.xlsx la crea copiando el original. Devuelve la ruta."""

def cargar_listas(ruta: Path) -> tuple[list[str], list[str]]:
    """(cursos, distritos) leídos de 'Hoja 2' col A y col C. Sin vacíos, sin duplicados, orden original.
    read_only=True, data_only=True. Lanza ErrorEstructuraPlanilla si alguna lista queda vacía."""

def leer_distrito_evaluador(ruta: Path) -> str:
    """Valor de MERITUADOS!D1."""

def siguiente_fila_libre(ws) -> int:
    """Primera fila >= 9 con columna C vacía."""

def siguiente_orden(ws) -> int:
    """max(col A numérica desde fila 9) + 1, o 1."""

def buscar_por_dni(ruta: Path, dni: int) -> list[dict]:
    """Registros ya cargados con ese DNI en ambas hojas: [{'hoja','fila','especialidad','motivo'|'puntaje'}]
    (para advertir duplicados DNI+curso y para 'evaluar otro curso')."""

def guardar_meritudo(registro: dict, ruta: Path = RUTA_TRABAJO) -> int:
    """Escribe en MERITUADOS. Devuelve nº de fila. Solo asigna .value (no cambia estilos, validaciones ni
    nada fuera de A..AB). Guarda con wb.save; si PermissionError -> PlanillaBloqueada."""

def guardar_no_meritudo(registro: dict, ruta: Path = RUTA_TRABAJO) -> int:
    """Ídem para NO MERITUADOS (mapa §3.2)."""

def resumen_cargados(ruta: Path) -> dict:
    """{'meritudos': n, 'no_meritudos': n} para mostrar en la barra lateral."""
```

Reglas de implementación:
- `load_workbook(ruta)` (sin `read_only`) **solo** al guardar; lecturas de listas con `read_only=True`.
- Hacer **backup** `salida/backup/PLANILLA_TRABAJO_AAAAMMDD_HHMMSS.xlsx` antes de cada guardado (conservar los últimos 20).
- No tocar el archivo original jamás.
- Si la fila destino no tiene formato y la anterior sí, copiar `_style` de la fila 9 (opcional, solo si se ve mal).

### 4.2 `normativa_ayuda.py` — reglas puras (sin Excel, sin Streamlit)

Todas las funciones son **puras** y deben poder probarse con `assert`. Usar `decimal.Decimal` internamente o
`round(x + 1e-9, 2)` para evitar errores de coma flotante.

```python
# ---- Constantes de topes y escalas (tablas de §6) ----
TOPE_CAP_DOCENTE = 3.00 ; TOPE_CAP_ESPECIFICA = 5.00
TOPE_ANTIG_DOCENCIA = 2.50 ; TOPE_ANTIG_FP = 5.00
MOTIVOS_NO_MERITUADO = [...]                 # los 7 literales de §5.2
OPCIONES_FORMACION_ESPECIFICA = {...}        # etiqueta UI -> clave (§6.3)

def convertir_hs_catedra_a_reloj(hs_catedra: float) -> int
def puntos_curso_docente(hs_reloj: float) -> float
def puntos_curso_especifico(hs_reloj: float) -> float
def total_capacitacion(horas_reloj: list[float], tipo: Literal["docente","especifica"]) -> float   # con tope
def puntos_desempeno(anios: int) -> int
def puntos_antiguedad_docencia(anios: float) -> float      # *0.25, tope 2.50
def puntos_antiguedad_fp(anios: float) -> float            # *0.50, tope 5.00
def puntos_calificacion(nota: float | None) -> float
def formacion_especifica(opcion: str) -> dict               # {'N':..,'O':..,'P':..,'Q':..}
def puntos_residencia(coincide: bool | None) -> int | None  # 5 / 0 / None si distrito no cargado
def calcular_listado(fi: int) -> str                        # PRINCIPAL / COMPLEMENTARIO
def calcular_puntaje(reg: dict) -> dict                     # {'base':..,'residencia':..,'con_residencia':..}
def evaluar_habilitacion(resp: dict) -> tuple[bool, list[str]]   # (cumple, motivos_sugeridos)
def sugerir_motivo(motivos_incumplidos: list[str]) -> str

AYUDAS: dict[str, dict]   # clave ('P1'...'P17','HABILITACION','HAB_INC6','HAB_6_1_1'...'HAB_6_2_3','PERFILES_NUEVOS') -> {titulo, columnas, normativa[list], texto}
def obtener_ayuda(clave: str, curso: str | None = None) -> str   # markdown listo; personaliza P9/P12 por cargo y agrega perfil de nuevo diseño
def opciones_formacion_especifica(curso: str | None) -> list[str]   # Pañol (00PA): solo títulos técnicos
def tipo_cargo(curso) -> 'instructor'|'preceptor'|'panolero'
def perfil_nuevo_diseno(curso) -> dict | None ; texto_perfil_nuevo_diseno(curso) -> str
def resumen_capacitacion(horas_reloj, tipo) -> {'bruto','total','tope','tope_aplicado'}
def promedio_calificaciones(notas: list[float]) -> float | None   # cargos simultáneos en un año
```

### 4.3 `app.py` — interfaz Streamlit (sin lógica de negocio)

> ⚠️ **SUPERSEDIDO por §11 (Rediseño de pantalla v2).** Lo que sigue describe la UI v1 (ya implementada).
> Para programar el nuevo `app.py` **seguir únicamente §11**; §5, §6, §7 y §9 (reglas de negocio) siguen vigentes.

- `st.set_page_config(page_title="Evaluador FP Reg 10 – 2027", layout="wide")`.
- Estado en `st.session_state`: `paso` (int), `reg` (dict de la respuesta en curso), `perfil_dni` (dict reutilizable, §7),
  `listas` (cursos, distritos; cargadas una vez con `@st.cache_data`).
- **Barra lateral**: Distrito Evaluador (D1), contadores cargados, botón "Nuevo aspirante", aviso de archivo bloqueado.
- **Cuerpo**: un `st.form` por paso, con barra de progreso `st.progress`, botones **Anterior / Siguiente**, y un
  `st.expander("Normativa")` con `obtener_ayuda(clave, curso)`.
- Validaciones en pantalla (DNI numérico 7–8 dígitos, apellido/nombres no vacíos, etc.); mostrar `st.error`, no avanzar.
- **Panel de resultado final** (antes de guardar): tabla con cada ítem y su puntaje, **Puntaje base** y
  **Puntaje con +5 por residencia** (ver §8), botones **Guardar** / **Volver a corregir**.
- Tras guardar: `st.success` con nº de fila y 2 botones: **"Evaluar otro curso para este DNI"** (conserva `perfil_dni`) y
  **"Nuevo aspirante"** (limpia todo).
- `app.py` solo llama a funciones de los otros dos módulos; **no** contiene tablas de puntos ni letras de columnas.

---

## 5. Flujo del asistente (estricto, columnas C → AB)

```
P1 DNI → P2 Apellido → P3 Nombres → P4 Curso → P5 Distrito 1 + residencia → P6 Distrito 2 (opc.) → P7 Distrito 3 (opc.)
        │
        ▼
   FILTRO DE HABILITACIÓN
        ├── NO CUMPLE → Motivo (J) + Observaciones (K) → GUARDAR en NO MERITUADOS → fin
        └── CUMPLE   → P8 … P17 → Resumen/Cálculo (AB) → GUARDAR en MERITUADOS → fin
```

### 5.1 Filtro de habilitación (después de P7, antes de P8)

Preguntas Sí/No (con ayuda normativa):

1. **Requisitos comunes (Inc. 3)** – deben ser todos Sí:
   - 1a. ¿Anexo III válido?
   - 1b. ¿DNI frente y reverso presentado?
   - 1c. ¿Título secundario / superior / universitario registrado?
2. **¿El cargo es de Instructor/a?** Si **No** → se omite el bloque 3.
3. **Inc. 6 (solo Instructor/a)** – se cumple si **(6.1 completo)** **O** **(algún reemplazo 6.2)**:
   - 6.1.1: ¿3 años de experiencia laboral **NO docente** en los últimos 5 años? **y**
   - 6.1.2: ¿Título afín **o** 350 hs de FP?
   - 6.2.1: ¿Idoneidad estratégica? **o** 6.2.2: ¿Dictó el curso 2 veces completo en los últimos 5 años? **o** 6.2.3: ¿Curso declarado en el Certificado de FI?

Lógica: `cumple = req_comunes_ok and (not es_instructor or (6_1_1 and 6_1_2) or 6_2_1 or 6_2_2 or 6_2_3)`.

Ayuda de `evaluar_habilitacion`: devuelve motivos sugeridos que el evaluador puede cambiar:

| Falla | Motivo sugerido |
|---|---|
| 1b | "No presenta DNI" |
| 1c | "No presenta Titulo Secundario" |
| 1a | "No presenta Anexo 3" |
| Inc. 6 no cumplido | "NO ACREDITA ANTECEDENTES PROFESIONALES ESPECÍFICOS" |
| otra causa | "No Reune Requisitos" |

### 5.2 Motivos permitidos en `NO MERITUADOS!J` (literales exactos)

`"No presenta DNI"`, `"No presenta Titulo Secundario"`, `"No presenta Anexo 3"`, `"No Reune Requisitos"`,
`"Aspirante Jubilado"`, `"NO ACREDITA ANTECEDENTES PROFESIONALES ESPECÍFICOS"`, `"Otros"`.

- "Aspirante Jubilado" **no** surge del filtro: es una opción manual del selector (también el evaluador puede marcarlo
  como motivo aunque los requisitos aparenten cumplirse → agregar casilla "El aspirante es jubilado" en el filtro).
- Si el motivo es `"Otros"` → observaciones **obligatorias**.
- Observaciones (K): texto libre, opcional salvo `"Otros"`.

---

## 6. Reglas de puntaje por pregunta (exactas)

### P1–P3 Datos personales (C, D, E)
- `dni`: solo dígitos, sin puntos ni espacios; `int`. Aceptar con puntos y normalizar. Rango razonable 1.000.000–99.999.999.
- `apellido`, `nombres`: `.strip().upper()`, colapsar espacios múltiples; no vacíos.

### P4 Especialidad (F)
- `st.selectbox` con lista dinámica `cursos` (Hoja 2 col A). Se escribe el texto **idéntico** al de la lista.
- Mismo DNI puede evaluarse en varios cursos (ver §7). Si ya existe DNI+curso en alguna de las dos hojas → `st.warning` y exigir confirmación.

### P5–P7 Residencia (G–L) – Ítem 10.10
- `Distrito 1` obligatorio, `Distrito 2` y `3` opcionales (opción "— Ninguno —" por defecto).
- Por cada distrito cargado: *"¿Coincide este Distrito N con el domicilio del DNI vigente (frente y reverso)?"* → Sí = **5**, No = **0**.
- Si el distrito no se carga: celdas de puntos **vacías** (None).
- No permitir el mismo distrito repetido en dos posiciones.

### P8 Instructor de FP – FI (M) – Ítem 10.1
- ¿Posee certificado de FI válido y registrado? Sí = **25**, No = **0**.
- Determina `B` (LISTADO): 25 → `PRINCIPAL`; 0 → `COMPLEMENTARIO` (Inc. 3.3 y 7.1, Dispo 13/2025).

### P9 Formación específica (N, O, P, Q) – Ítem 10.2 (selección única excluyente)

Solo se valora **el título de mayor nivel** vinculado a la especialidad. `st.radio`:

| Opción UI | N | O | P | Q |
|---|---|---|---|---|
| Ninguno / Sin orientación afín | 0 | 0 | 0 | 0 |
| Secundario orientado afín | **3** | 0 | 0 | 0 |
| Secundario Técnico afín | 0 | **5** | 0 | 0 |
| Superior afín | 0 | 0 | **7** | 0 |
| Universitario de grado afín | 0 | 0 | 0 | **8** |

Escribir `0` en las no elegidas (o vacío; **decisión fija: escribir 0** para que la suma sea clara).

### P10 Capacitación docente (R) – Ítem 10.5 — calculadora interactiva

Tabla por curso (horas **reloj**):

| Horas reloj | Puntos |
|---|---|
| < 5 | 0 (no válido) |
| 5 – 10 | 0.05 |
| 11 – 30 | 0.10 |
| 31 – 50 | 0.15 |
| 51 – 70 | 0.30 |
| 71 – 100 | 0.40 |
| > 100 | 0.60 |

- Interfaz: lista de cursos (`st.data_editor` con filas dinámicas: descripción opcional, horas, unidad `reloj`/`cátedra`) o
  campo "agregar curso" + tabla acumulada con botón de quitar.
- Conversor: `hs_reloj = INT(hs_catedra * 2 / 3)` (**truncar**, igual que la fórmula de la propia planilla `INT(AP*60/40)`).
- `R = min(suma, 3.00)`. Mostrar "Suma bruta" y "Aplicado con tope".
- Mostrar el puntaje de cada fila en vivo.

### P11 Capacitación específica (S) – Ítem 10.3 — calculadora interactiva

| Horas reloj | Puntos |
|---|---|
| < 5 | 0 |
| 5 – 10 | 0.05 |
| 11 – 15 | 0.10 |
| 16 – 20 | 0.15 |
| 21 – 30 | 0.20 |
| > 30 | 0.30 |

- Misma UI/conversor que P10. `S = min(suma, 5.00)`.

### P12 Desempeño profesional (T, U) – Ítem 10.6
- Entero 0–35 (`st.number_input(min_value=0, max_value=35, step=1)`).
- Si `anios >= 1`: `T = anios`; `U` según tabla. Si `anios == 0`: `T` y `U` quedan **vacíos** (None).

| Años | U |
|---|---|
| 0 – 2 | 0 |
| 3 – 4 | 5 |
| 5 – 9 | 6 |
| ≥ 10 | 8 |

### P13 Formación superior en el ámbito de la FP (V) – Ítem 10.4
- ¿Tecnicatura Universitaria/Superior en Educación Profesional o ETP específica para FP con **Validez Nacional**? Sí = **7**, No = **0**.

### P14 Antigüedad en la docencia oficial (W) – Ítem 10.7
- Años lectivos con Certificación de Servicios (acepta decimales, paso 0.5, ≥ 0). `W = min(años * 0.25, 2.50)`.

### P15 Antigüedad en el ámbito de FP oficial (X) – Ítem 10.8
- Años lectivos en FP con Certificación de Servicios. `X = min(años * 0.50, 5.00)`.

### P16 Calificaciones (Y, Z) – Ítem 10.9 (últimos 2 años calificados en FP, SET 4)
- Por cada una de las dos calificaciones: opción **"Ingresar nota"** (0.00–10.00, 2 decimales) u opción **"Elegir escala"**, u **"Sin calificación"**.

| Nota | Puntos |
|---|---|
| 9.51 – 10.00 | 1.00 |
| 8.00 – 9.50 | 0.50 |
| 6.00 – 7.99 | 0.10 |
| < 6.00 o sin calificación | 0 |

- Si se elige la escala se asigna directamente su valor (1 / 0.50 / 0.10 / 0).
- Se escribe el **puntaje** (no la nota) en Y y Z. Cada una máx. 1.

### P17 Art. 59 Estatuto Docente (AA)
- ¿Le corresponden los 10 puntos por no poseer cargos ni horas titulares? Sí = **10**, No = **0**.

### Cálculo final (AB) – Pantalla de resumen

```
BASE = M + N + O + P + Q + R + S + U + V + W + X + Y + Z + AA        # T (años) NO suma, solo U
RESIDENCIA = 5 si alguna de H, J, L == 5; si no, 0                   # tope 5 (ver decisión D1)
CON_RESIDENCIA = BASE + RESIDENCIA
```

- Redondear **solo al final** a 2 decimales; mostrar ambos valores en pantalla, claramente rotulados:
  **"Puntaje base (sin residencia)"** y **"Puntaje con +5 pts por residencia"**.
- Valor escrito en `AB`: **BASE** (suma literal de las columnas indicadas), salvo que la constante
  `AB_INCLUYE_RESIDENCIA = True` en `normativa_ayuda.py` (por defecto `False`; ver decisión D1).
- El máximo teórico del BASE no se hardcodea: se obtiene sumando los topes de cada ítem.

---

## 7. Evaluar varios cursos para el mismo DNI

Tras guardar, "Evaluar otro curso para este DNI" conserva `perfil_dni` (sesión) y salta a **P4** con valores precargados
(editables). Qué se **reutiliza** y qué se **vuelve a preguntar**:

| Reutilizado (precargado, editable) | Se vuelve a preguntar (depende del curso) |
|---|---|
| C, D, E (DNI y nombre) | F (nuevo curso) |
| G–L (distritos y puntos de residencia) | Filtro de habilitación completo (Inc. 6 depende del curso) |
| R (cap. docente), V (form. sup. FP) | M (FI: puede declarar otro curso, 6.2.3) |
| W, X (antigüedades), Y, Z (calificaciones) | N–Q (afinidad del título con el curso) |
| AA (Art. 59) | S (cap. específica), T–U (desempeño en la actividad) |

Si el DNI ya fue guardado en una sesión anterior, `buscar_por_dni` avisa; no hay precarga entre sesiones.

---

## 8. Decisiones abiertas (el Arquitecto las dejó **con un valor por defecto**; el usuario puede cambiarlas)

| ID | Tema | Valor por defecto asumido |
|---|---|---|
| D1 | +5 por residencia: ¿se suma una sola vez aunque varios distritos coincidan? ¿va dentro de AB? | Máximo +5 total; AB guarda el **BASE**; ambos se muestran en pantalla. Constante `AB_INCLUYE_RESIDENCIA`. |
| D2 | Horas con decimales tras convertir cátedra→reloj | Se **trunca** (`INT`). |
| D3 | Horas < 5 | 0 puntos, advertencia en pantalla. |
| D4 | `NO MERITUADOS!B` (LISTADO) | Queda vacío. |
| D5 | Archivo de salida | Copia de trabajo en `salida/`; el original no se toca. |
| D6 | Opción "Aspirante Jubilado" | Casilla manual en el filtro. |

---

## 9. Casos de prueba mínimos (para validar `normativa_ayuda.py` con `assert`)

| Función | Entrada | Esperado |
|---|---|---|
| `convertir_hs_catedra_a_reloj` | 45 | 30 |
| `convertir_hs_catedra_a_reloj` | 16 | 10 (10.67 → trunca) |
| `puntos_curso_docente` | 4 / 5 / 10 / 11 / 30 / 31 / 50 / 51 / 70 / 71 / 100 / 101 | 0 / .05 / .05 / .10 / .10 / .15 / .15 / .30 / .30 / .40 / .40 / .60 |
| `puntos_curso_especifico` | 5 / 10 / 11 / 15 / 16 / 20 / 21 / 30 / 31 | .05 / .05 / .10 / .10 / .15 / .15 / .20 / .20 / .30 |
| `total_capacitacion` | 6 cursos de 101 h, tipo docente | 3.00 (tope) |
| `total_capacitacion` | 20 cursos de 31 h, tipo específica | 5.00 (tope, 20×.30=6 → 5) |
| `puntos_desempeno` | 0, 2, 3, 4, 5, 9, 10, 35 | 0, 0, 5, 5, 6, 6, 8, 8 |
| `puntos_antiguedad_docencia` | 4 / 11 | 1.00 / 2.50 |
| `puntos_antiguedad_fp` | 4 / 11 | 2.00 / 5.00 |
| `puntos_calificacion` | 10 / 9.51 / 9.50 / 8 / 7.99 / 6 / 5.99 / None | 1 / 1 / .5 / .5 / .1 / .1 / 0 / 0 |
| `formacion_especifica("Superior afín")` | — | `{'N':0,'O':0,'P':7,'Q':0}` |
| `calcular_listado` | 25 / 0 | PRINCIPAL / COMPLEMENTARIO |
| `evaluar_habilitacion` | Instructor, 6.1.1 sí, 6.1.2 no, 6.2.* todos no | `(False, [...])` |
| `evaluar_habilitacion` | Instructor, 6.1 no, 6.2.2 sí | cumple |
| `calcular_puntaje` | Máximo posible de cada ítem + H=5 | `base`, `con_residencia = base + 5` |

Pruebas de `extractor_datos.py`: `cargar_listas` devuelve listas sin duplicados y sin vacíos;
`leer_distrito_evaluador` == `D1`; guardar un registro de prueba **en una copia temporal** y comprobar que
(a) cae en la fila 9, (b) el segundo cae en la 10, (c) no cambió nada en columnas AJ en adelante.

---

## 10. Criterios de aceptación globales

- [ ] Ninguna lista de cursos o distritos escrita a mano en ningún `.py`.
- [ ] El original `.xlsx` queda intacto.
- [ ] Los puntos se escriben como números (float/int), nunca como texto.
- [ ] Todas las reglas de §6 están en `normativa_ayuda.py` y solo ahí.
- [ ] `app.py` sigue el orden C → AB y el filtro de habilitación de §5.
- [ ] Se puede cargar un mismo DNI con 2+ cursos reutilizando datos (§7).
- [ ] Si el Excel está abierto, la app muestra un mensaje claro y no pierde las respuestas en curso.
- [ ] Se muestran **Puntaje base** y **Puntaje con +5 por residencia**.

---

# 11. REDISEÑO DE PANTALLA v2 (especificación para programar el nuevo `app.py`)

> **Instrucción para el modelo programador:** reescribir **solo** `app.py`. `extractor_datos.py` **no se toca**.
> `normativa_ayuda.py` ya incluye (implementados y probados) los helpers nuevos de §11.1: **no reimplementarlos**.
> Antes de borrar el `app.py` actual, copiar de él **sin cambios** las constantes y funciones listadas en §11.12.

## 11.0 Qué cambia respecto a la UI v1

| Tema | UI v1 (actual) | UI v2 (esta sección) |
|---|---|---|
| Distrito Evaluador / descarga / checkbox AB | Barra lateral | **Cabecera superior centrada** (sidebar colapsada y vacía) |
| Preguntas | 3 bloques apilados, todas visibles | **Asistente de UNA pregunta por vez** (`paso_actual` 1–18 + 8B), cuadro izquierdo |
| Ayuda | `st.expander` por campo | **Panel derecho fijo**, siempre visible, cambia con el paso |
| Vista previa | Tabla debajo del Bloque 3 | **Fila en vivo (A–AB)** del aspirante en curso, sección inferior |
| Tabla de sesión | `st.dataframe` + Editar/Eliminar vía formulario | **`st.data_editor`** editable celda a celda, AB se recalcula solo |
| Edición de un registro ya guardado | Recarga el formulario (`inputs`/`restaurar`) | **Solo en la grilla** (se elimina `snapshot()`/`restaurar()`/`inputs`) |
| Cálculo de AB | Se fija al guardar | **Derivado**: se recalcula al editar la grilla y al cambiar distrito evaluador o checkbox |
| Se conserva | Persistencia JSON, `generar_excel`, `listas`, duplicados, reglas de §5–§7 | — |

## 11.1 Helpers nuevos YA IMPLEMENTADOS en `normativa_ayuda.py` (usarlos, no duplicarlos)

| Función | Uso en `app.py` |
|---|---|
| `residencia_en_distrito_evaluador(datos, distrito_eval) -> bool` | Informativo (tooltip de AB). |
| `calcular_ab(datos, distrito_eval, incluir_residencia) -> dict` | **Única** forma de obtener AB: devuelve `{'base','residencia','con_residencia','ab','desglose'}`. Suma +5 solo si `incluir_residencia` **y** el aspirante tiene 5 pts en el distrito == `distrito_eval`. |
| `normalizar_edicion_meritudo(anterior, nuevo) -> (datos, avisos)` | Aplicar a cada fila MERITUADOS editada en la grilla (valida, topa, recalcula LISTADO y U; **no** toca `puntaje`). |
| `normalizar_edicion_no_meritudo(anterior, nuevo) -> (datos, avisos)` | Ídem para NO MERITUADOS. |

Existentes que se siguen usando: `tipo_cargo`, `opciones_formacion_especifica`, `formacion_especifica`, `puntos_residencia`,
`calcular_listado`, `convertir_hs_catedra_a_reloj`, `puntos_curso_docente/especifico`, `resumen_capacitacion`, `puntos_desempeno`,
`puntos_antiguedad_docencia/fp`, `puntos_calificacion`, `texto_perfil_nuevo_diseno`, `obtener_ayuda`, `MOTIVOS_NO_MERITUADO`, `MOTIVO_*`, `PTS_*`, `TOPE_*`.

## 11.2 Layout global

```
st.set_page_config(page_title="Evaluador FP Reg 10 – Listados 2027", page_icon="📋", layout="wide",
                   initial_sidebar_state="collapsed")        # sidebar NO se usa

┌───────────────────────────── TOP BAR (centrada) ─────────────────────────────┐
│  título centrado                                                              │
│  [Distrito Evaluador ▼]  [📥 Descargar Planilla Oficial (.xlsx …)]  [☐ +5 AB] [⚙️] │
│  contadores centrados (caption)                                               │
├───────────────────────────────┬──────────────────────────────────────────────┤
│ col_izq: PREGUNTA ACTIVA       │ col_der: AYUDA, REGLAMENTACIÓN Y EJEMPLOS      │
│  (container height=470)        │  (container height=470, scroll interno)        │
│  [⬅️ Anterior][selector][Sig ➡️]│                                              │
├───────────────────────────────┴──────────────────────────────────────────────┤
│ 1. VISTA EN TIEMPO REAL DEL ASPIRANTE EN EVALUACIÓN (fila A–AB)               │
│ 2. PLANILLA GENERAL EDITABLE: tabs MERITUADOS | NO MERITUADOS (st.data_editor)│
└──────────────────────────────────────────────────────────────────────────────┘
```

Orden de ejecución en `main()` (**el orden importa**, ver §11.5): `init_estado()` → CSS → `top_bar()` → flash/`st.success` →
`col_izq, col_der = st.columns([1, 1])` → columna izquierda (render del paso + navegación) → columna derecha (ayuda) →
`preview_en_vivo()` → `grilla_general()`.

## 11.3 Cabecera superior (Top Bar)

- Título: `st.markdown` HTML centrado (`text-align:center`). Debajo, una fila:
  `_, c1, c2, c3, c4, _ = st.columns([0.4, 2.4, 2.6, 2.6, 0.5, 0.4], vertical_alignment="center")`
  - `c1`: `st.selectbox("Distrito Evaluador (celda D1)", distritos, key="distrito_eval", on_change=_al_cambiar_config)`.
    Valor inicial: el guardado en el JSON; si no hay, `"Reg 10 Distrito: 067-MARCOS PAZ"`; si no existe en la lista, `leer_distrito_evaluador()`.
  - `c2`: `st.download_button("📥 Descargar Planilla Oficial (.xlsx para Google Sheets)", type="primary", ...)`.
    **Siempre habilitado** (aunque no haya registros: entrega la planilla base con D1 actualizada).
    `data = generar_excel(json_mer, json_no, distrito_eval, mtime)` (cacheado, función ya existente) →
    `ed.exportar_excel_bytes(mer, no, distrito)`. Solo incluye registros **guardados** (no el borrador en curso).
    `file_name = f"PLANILLA DE DATOS DE ASPIRANTES - {slug_distrito(distrito)}.xlsx"`; `mime` de xlsx.
  - `c3`: `st.checkbox("Incluir +5 pts de residencia del Distrito Evaluador en Columna AB", key="incluir_residencia_ab", on_change=_al_cambiar_config)`
    (por defecto destildado).
  - `c4`: `st.popover("⚙️")` con: **"🧹 Limpiar asistente (sin guardar)"** (→ `resetear_aspirante()`) y **"🗑️ Vaciar toda la sesión"** (confirmación; vacía `registros`).
  - Debajo, `st.caption` centrado: `MERITUADOS: n cursos (m legajos) · NO MERITUADOS: n cursos (m legajos)`.
- `_al_cambiar_config()` (callback): `recalcular_ab_todos()` + `guardar_disco()`.
- `recalcular_ab_todos()`: para cada registro `hoja == MER`: `datos["puntaje"] = na.calcular_ab(datos, distrito_eval, incluir)["ab"]`.
- **Compatibilidad Google Sheets:** el archivo se genera con `exportar_excel_bytes` (openpyxl, parte de la planilla original: conserva hojas,
  formato, celdas combinadas, listas desplegables y fórmulas). Se abre con *Drive → Abrir con → Hojas de cálculo de Google*. No convertir ni
  quitar validaciones. Limitación conocida (no es un error): los puntajes con decimales (Y/Z = 0,5; W; R; S) caen fuera de las listas
  desplegables originales y Sheets puede marcarlos con un triángulo de advertencia; los valores se conservan.

## 11.4 Modelo de estado

### `st.session_state` (todas las claves se crean en `init_estado()`)

| Clave | Tipo | Significado |
|---|---|---|
| `registros` | `list[dict]` | Registros guardados: `{"id": int, "hoja": "MER"\|"NOMER", "datos": dict}` (sin `inputs`). |
| `sig_id` | int | Próximo id. |
| `paso_actual` | int | 1–18, o **19 = Paso 8B (Motivo/Observaciones)**. |
| `resp` | dict | **Única fuente de verdad** de las respuestas del aspirante/curso en curso (ver abajo). |
| `ver` | int | Versión de las keys de widgets; se incrementa en cada reseteo (§11.9). |
| `ver_tabla` | int | Versión de la key de cada `data_editor`; se incrementa al aplicar ediciones/eliminar. |
| `es_otro_curso` | bool | True tras “Evaluar otro curso del MISMO aspirante”. |
| `saltar_precargados` | bool | Checkbox de navegación (por defecto True; visible solo si `es_otro_curso`). |
| `flash` | str\|None | Mensaje `st.success` tras guardar/eliminar/editar. |
| `distrito_eval`, `incluir_residencia_ab` | str, bool | Widgets de la Top Bar. |

### `resp` (se crea con `nueva_resp()`; todos los campos siempre presentes)

```python
resp = {
  "dni_txt": "", "apellido": "", "nombres": "",
  "d1": None, "d2": None, "d3": None,          # str | None  (None = distrito no cargado)
  "r1": False, "r2": False, "r3": False,        # ¿coincide con el domicilio del DNI vigente?
  "curso": None, "confirm_dup": False,
  "hab": None, "req_comunes": False, "mantiene": None,   # filtro de habilitación (literales HAB_* / NO_MERITUA)
  "motivo": None, "obs": "",
  "fi": None,                                   # 25 | 0 | None
  "fe_sel": None,                               # clave de na.OPCIONES_FORMACION_* | None
  "modo_doc": "Certificados", "cert_doc": [], "dir_doc": 0.0,   # R
  "modo_esp": "Certificados", "cert_esp": [], "dir_esp": 0.0,   # S
  "t_anios": 0, "u_prev": None,                 # T y U (u_prev solo si mantiene valoración)
  "form_sup": None,                             # 7 | 0 | None   (V)
  "antig_doc": 0.0, "antig_fp": 0.0,            # años (W, X)
  "calif1": CALIF_DEFECTO, "calif2": CALIF_DEFECTO,   # etiquetas de CALIF_OPCIONES
  "art59": None,                                # 10 | 0 | None  (AA)
}
CAMPOS_COMUNES = ["dni_txt","apellido","nombres","d1","d2","d3","r1","r2","r3","fi","form_sup","antig_doc","antig_fp","calif1","calif2","art59"]
# CAMPOS_CURSO = todos los demás (curso, hab, req_comunes, mantiene, motivo, obs, fe_sel, cert_*, modo_*, dir_*, t_anios, u_prev, confirm_dup)
```

### Persistencia `salida/sesion_registros.json` (versión 2)

```json
{"version": 2, "sig_id": 5, "config": {"distrito_eval": "Reg 10 Distrito: 067-MARCOS PAZ", "incluir_residencia_ab": false},
 "registros": [{"id": 1, "hoja": "MER", "datos": { ... }}]}
```
- Se escribe después de **cada** cambio (guardar, editar en grilla, eliminar, cambiar config). `json.dumps(..., ensure_ascii=False)`.
- Al leer un archivo v1 (sin `version`): ignorar y **eliminar** la clave `inputs` de cada registro.
- Los valores de `datos` deben ser tipos nativos (`int/float/str/None`); convertir `numpy`/`NaN` antes de guardar.
- El borrador (`resp`) **no** se persiste (decisión D10).

## 11.5 REGLA CRÍTICA de Streamlit: widgets que existen de a uno

Streamlit **borra del `session_state` el valor de todo widget que no se renderiza en una corrida**. Como cada paso muestra un solo
widget, **es obligatorio** este patrón (sin excepciones):

1. `resp` es la única fuente de verdad. Los widgets **no** se leen de `session_state[key]` en otros pasos.
2. **Escritura inmediata:** en cada paso, el valor devuelto por el widget se asigna a `resp[campo]` **en la misma corrida**, antes de que
   se rendericen la navegación y la vista previa (que están más abajo en el script). Así la vista previa se actualiza celda por celda.
   ```python
   resp["apellido"] = st.text_input("APELLIDO (Col. D) *", value=resp["apellido"], key=wk("apellido"))
   ```
3. **Valor inicial desde `resp`** con `value=`/`index=` (nunca precargar con `st.session_state[key] = ...`, evita el aviso de Streamlit).
   Radios sin respuesta: `index=None if resp[x] is None else opciones.index(resp[x])`.
4. Keys con versión: `def wk(campo): return f"w{st.session_state.ver}_{campo}"`. Para listas dependientes del cargo, incluir el tipo en la key
   (`wk(f"fe_{tipo}")`, `wk(f"hab_{tipo}")`).
5. **Botones de navegación y de guardado: inline** (`if st.button(...):` + `st.rerun()`), colocados **después** del widget del paso en el script,
   para que lean el `resp` ya actualizado. Solo los botones que modifican listas (agregar/quitar certificado) usan `on_click`.
6. `sanear_resp()` al inicio de cada corrida (después de `init_estado`): si `resp["hab"]` no está en las opciones del `tipo_cargo(curso)`
   actual → `None`; si `resp["fe_sel"]` no está en `na.opciones_formacion_especifica(curso)` → `None` (el paso 10 usa la 1ª opción por defecto).
7. `st.rerun()` solo dentro de `if` de acción (nunca incondicional) para evitar bucles.

## 11.6 Asistente (columna izquierda): registro de pasos

`PASOS` = lista/dict de definiciones. Clave de ayuda = clave de `AYUDAS` de `normativa_ayuda.py` (sin cambios en ese módulo).
Título en pantalla: `Paso {n} de 18 · Col. {cols}` + barra `st.progress(n/18)`. Los textos de los widgets se toman de la UI v1
(`bloque1/2/3` de `app.py` actual).

| Paso | Col. | Campos `resp` | Widget (cuadro izquierdo) | **Bloquea “Siguiente” si…** | Ayuda (derecha) | Resalta en vista previa |
|---|---|---|---|---|---|---|
| 1 | C | `dni_txt` | `text_input` “DNI (Col. C) *” | tras quitar no-dígitos no es `\d{7,8}` | `P1` | C |
| 2 | D | `apellido` | `text_input` (se normaliza a MAYÚSCULAS sin espacios dobles) | vacío | `P2` | D |
| 3 | E | `nombres` | ídem | vacío | `P3` | E |
| 4 | G, H | `d1`, `r1` | `selectbox` Distrito 1 (`index=None`, buscable) + `checkbox` “Coincide con el domicilio del DNI vigente → 5 pts en Col. H” + caption “Col. H = 5/0” | `d1` vacío | `P5` | G, H |
| 5 | I, J | `d2`, `r2` | `selectbox([NINGUNO]+distritos)` opcional + checkbox (`disabled` si ninguno; si se elige NINGUNO → `r2=False`, `d2=None`) | `d2` igual a `d1`; o más de un `r*` en True | `P6` | I, J |
| 6 | K, L | `d3`, `r3` | ídem Distrito 3 | repetido; o más de un `r*` True | `P7` | K, L |
| 7 | F | `curso`, `confirm_dup` | `selectbox` buscable `index=None` (lista `cursos`) + `st.info` con `texto_perfil_nuevo_diseno(curso)` + aviso de duplicados (`duplicados()` v1) con checkbox “Confirmo cargarlo de todos modos” | `curso` vacío; hay duplicados y no `confirm_dup` | `P4` + `PERFILES_NUEVOS` | F |
| 8 | Filtro | `hab`, `req_comunes`, `mantiene` | `radio` `hab` (`HAB_INSTRUCTOR` si `tipo_cargo=="instructor"`, si no `HAB_COMUN`; incluye “Recurrente 2.1” y `NO_MERITUA`). Si `hab != NO_MERITUA`: `checkbox` `req_comunes` (Inc. 3). Si `hab` contiene “Recurrente”: `radio` `mantiene` “¿Mantiene la valoración anterior?” Sí/No | `hab` None; cumple y `not req_comunes`; recurrente y `mantiene is None` | `HABILITACION`; si instructor además `HAB_INC6`, `HAB_6_1_1`, `HAB_6_1_2`, `HAB_6_2_1`, `HAB_6_2_2`, `HAB_6_2_3` (en `st.tabs`) | — |
| 19 (8B) | J, K | `motivo`, `obs` | `selectbox` `MOTIVOS_NO_MERITUADO` (por defecto `MOTIVO_NO_REUNE`), `text_area` observaciones, panel de resumen y **2 botones de guardado** (§11.9) | `motivo` vacío; `motivo=="Otros"` sin observaciones | `HABILITACION` | J, K |
| 9 | B, M | `fi` | `radio` Sí (25 → PRINCIPAL) / No (0 → COMPLEMENTARIO), `index=None`; caption con Col. B | `fi` None | `P8` | B, M |
| 10 | N–Q | `fe_sel` | `radio` excluyente con `na.opciones_formacion_especifica(curso)` y `etiqueta_formacion()` v1 (Pañol: sin opción de 3 pts + `st.warning`) | — | `P9` (con `curso`) | N, O, P, Q |
| 11 | R | `modo_doc`, `cert_doc`, `dir_doc` | `calculadora_paso("doc")` (§11.6.1); si `mantiene` → solo `number_input` “Puntaje anterior” (0–3,00, paso 0,05) | — | `P10` | R |
| 12 | S | `modo_esp`, `cert_esp`, `dir_esp` | `calculadora_paso("esp")`; si `mantiene` → `number_input` 0–5,00 | — | `P11` | S |
| 13 | T, U | `t_anios`, `u_prev` | `number_input` 0–35 (`step=1`); `u = na.puntos_desempeno(años)`; si `mantiene` además `selectbox` U ∈ {0,5,6,8} (por defecto lo sugerido por los años) | — | `P12` (con `curso`) | T, U |
| 14 | V | `form_sup` | `radio` Sí (7) / No (0), `index=None` | `form_sup` None | `P13` | V |
| 15 | W | `antig_doc` | `number_input` float 0–60, `step=0.5`; caption `na.puntos_antiguedad_docencia` | — | `P14` | W |
| 16 | X | `antig_fp` | ídem; `na.puntos_antiguedad_fp` | — | `P15` | X |
| 17 | Y, Z | `calif1`, `calif2` | 2 `selectbox` con las 4 etiquetas exactas de `CALIF_OPCIONES` | — | `P16` | Y, Z |
| 18 | AA, AB | `art59` | `radio` Sí (10) / No (0), `index=None` + **panel de confirmación** (puntaje base, con +5, AB a guardar) + **2 botones de guardado** (§11.9) | `art59` None; `validar_todo()` con errores | `P17` | AA, AB |

Si en el Paso 8 se elige `NO_MERITUA`, los pasos 9–18 **no existen** en la ruta; y viceversa el 19 solo existe con `NO_MERITUA`.

### 11.6.1 `calculadora_paso(p)` (p = `"doc"` o `"esp"`, pasos 11 y 12)

Reusar la lógica de `calculadora()` v1 con estos cambios: el estado vive en `resp` (`modo_{p}`, `cert_{p}`, `dir_{p}`), no en widgets.
- `radio` “Certificados / Puntaje directo” (valor inicial desde `resp`; si `mantiene` se fuerza “Puntaje directo”).
- Modo certificados: `text_input` descripción, `number_input` horas (entero ≥ 0), `radio` unidad (“Horas reloj” / “Horas cátedra”), botón **➕ Agregar**
  con `on_click=_agregar_cert(p)` que lee `st.session_state[wk(f"h_{p}")]`, `...u_{p}`, `...desc_{p}`, agrega a `resp[f"cert_{p}"]` y limpia esos widgets.
  Lista de certificados con **❌** por fila (`on_click=_quitar_cert(p, i)`), cada fila muestra horas, horas reloj equivalentes
  (`na.convertir_hs_catedra_a_reloj` si es cátedra) y puntos; métricas “Suma bruta” y “Aplicado (tope)” con `na.resumen_capacitacion`.
- Resultado: `R` / `S` = `resumen["total"]` (certificados) o `round(dir_{p}, 2)` (directo, `max_value` = tope).

### 11.6.2 Pasos precargados (“Evaluar otro curso del MISMO aspirante”)

Tras ese botón: `es_otro_curso=True`, `resp` conserva `CAMPOS_COMUNES` y reinicia el resto, `paso_actual=7`. Pasos con datos precargados:
**9, 14, 15, 16, 17** (y 1–6, que quedan antes del 7). Cada uno muestra `st.caption("✔ Precargado del curso anterior: confirme o modifique")`.
Si `saltar_precargados` es True, “Siguiente”/“Anterior” **saltan** los pasos {9, 14, 15, 16, 17}. El Paso 18 **no se salta** (confirmación final).

## 11.7 Navegación (debajo del cuadro izquierdo, siempre visible)

```python
ruta = ruta_activa(resp)   # [1..8] si hab es None; [1..8,19] si NO_MERITUA; [1..18] si cumple
n1, n2, n3 = st.columns([1.3, 2, 1.3])
```
- **“⬅️ Pregunta Anterior”**: nunca bloquea; va al paso previo de `ruta` (respeta saltos de precargados); **conserva** lo respondido (está en `resp`). Deshabilitado en el Paso 1.
- **“Siguiente Pregunta ➡️”**: ejecuta `validar_paso(paso_actual)`; si hay errores los muestra con `st.error` y **no** avanza. Siguiente de 8: `19` si `hab == NO_MERITUA`, si no `9`.
  No existe en los pasos 18 y 19 (allí están los botones de guardado).
- **Selector compacto de pasos** (`st.selectbox`, `label_visibility="collapsed"`): opciones `"1 · DNI (C)"`, …, `"8 · Habilitación"`, `"8B · Motivo (J,K)"`, …,
  solo las de `ruta`. `key=f"sel_paso_{paso_actual}"` y `index` = posición actual (la key por paso evita valores viejos). Si el elegido ≠ actual → `paso_actual = elegido; st.rerun()`.
  **Restricción:** solo se puede saltar a pasos anteriores al primer paso inválido (`primer_paso_invalido(resp)`) o a ese mismo paso, para no llegar al guardado con datos incompletos.
- `validar_paso(p) -> list[str]` y `primer_paso_invalido(resp) -> int` usan **las mismas reglas** de la columna “Bloquea” (reutilizar `validar_comun()` v1 donde aplique).

## 11.8 Panel de ayuda (columna derecha)

- `with col_der: with st.container(height=470, border=True):` (scroll interno si el texto es largo). **Sin `st.expander`**: texto visible siempre.
- Contenido: `st.markdown(na.obtener_ayuda(clave, curso))` con la clave de la tabla §11.6 (si hay varias, `st.tabs` con `TAB_AYUDA` v1).
- Si `resp["curso"]` es un diseño del Anexo 2 (`na.texto_perfil_nuevo_diseno(curso)` no vacío) y `paso_actual >= 7`: mostrar arriba un `st.info` con ese texto
  (títulos y perfiles admitidos), además de lo que `obtener_ayuda` agregue en P4/P9/HAB_*.
- Encabezado fijo: `### Ayuda, Reglamentación y Ejemplos de esta Pregunta` + `Paso n · Col. …`.
- El panel se renderiza **después** de la columna izquierda (usa `paso_actual` ya actualizado en esa misma corrida).

## 11.9 Guardado y reinicios

`construir_datos(resp, distrito_eval, incluir) -> (hoja, datos)` (función única; la usan preview y guardado):
- `datos` con las claves de §3 (`dni` int o None, `apellido`, `nombres`, `especialidad`, `dist1..3`, `pts_dist1..3` vía `na.puntos_residencia(marca) if distrito else None`,
  `fi`, `fe_*` desde `na.formacion_especifica(fe_sel or primera opción)`, `cap_docente`, `cap_especifica`, `desemp_anios`/`desemp_pts` (None si años == 0),
  `form_sup_fp`, `antig_docencia`, `antig_fp`, `calif1/2` (valores de `CALIF_OPCIONES`), `art59`).
- Sin responder → `None` (la vista previa muestra celda vacía). `listado = na.calcular_listado(fi)` solo si `fi in (0, 25)`, si no `""`.
- `puntaje = na.calcular_ab(datos, distrito_eval, incluir)["ab"]`.
- Si `hab == NO_MERITUA` → hoja `NOMER` con `{dni, apellido, nombres, especialidad, dist1..3, motivo, observaciones}`; si no, hoja `MER`.

`validar_todo(resp) -> list[str]`: junta los errores de todos los pasos de `ruta`. Los botones de guardado **solo actúan** si la lista es vacía (si no, `st.error` por cada ítem indicando el paso).

**Dos botones** (pasos 18 y 19; etiquetas exactas):
| Botón | Acción |
|---|---|
| `💾 Guardar y evaluar OTRO curso del MISMO aspirante` | `guardar()` + `resetear_curso()` → `paso_actual=7`, `es_otro_curso=True` |
| `✅ Guardar y cargar NUEVO aspirante` | `guardar()` + `resetear_aspirante()` → `paso_actual=1`, `es_otro_curso=False` |

(En el Paso 19 las etiquetas empiezan con “Guardar en NO MERITUADOS y …”.)

- `guardar(hoja, datos)`: agrega `{"id": sig_id, "hoja", "datos"}`, `sig_id += 1`, `ver_tabla += 1`, `flash = "✅ Curso guardado en MERITUADOS/NO MERITUADOS: …"`, `guardar_disco()`.
- `resetear_curso()`: `resp` = `nueva_resp()` con los `CAMPOS_COMUNES` copiados del `resp` anterior; `ver += 1`.
- `resetear_aspirante()`: `resp = nueva_resp()`; `ver += 1`; `paso_actual = 1`.
- Después de resetear: `st.rerun()`.

## 11.10 Sección inferior (ancho completo)

### 11.10.1 Vista en tiempo real (`preview_en_vivo()`)

- Título “**1. Vista en tiempo real del aspirante en evaluación**”.
- Construye `construir_datos(resp, …)` en cada corrida. Si `hab == NO_MERITUA` muestra columnas de NO MERITUADOS (A, C–K); si no, A–AB de MERITUADOS.
- Valor de A = `orden_siguiente(hoja)` (base de la planilla + registros de la sesión + 1).
- Se muestra con `st.dataframe(df.style.set_properties(subset=cols_resaltadas, **{"background-color": "#fff3bf", "font-weight": "700"}), hide_index=True)`,
  donde `cols_resaltadas` = columnas de la última columna de la tabla §11.6 para el `paso_actual`. Valores como `str` formateados con `fmt()` v1 (2 decimales en floats).
- Debajo, 3 `st.metric`: Puntaje base · Puntaje con +5 por residencia · **PUNTAJE (Col. AB) a guardar** (con tooltip explicando si los +5 entran o no).

### 11.10.2 Planilla general editable (`grilla_general()`)

- Título “**2. Planilla general**”. `st.tabs([f"MERITUADOS ({n})", f"NO MERITUADOS ({m})"])`. Si no hay filas: `st.info`.
- DataFrame **tipado** (no strings): columnas numéricas como `float`/`Int64`, vacíos como `None`. Nombre de columna = `f"{letra} · {ETIQUETA_OFICIAL}"` y primera columna **`🗑`** (bool, `False`).
  `col_a_clave`: dict nombre de columna → clave de `datos` (para volver de la grilla al registro).
- `st.data_editor(df, hide_index=True, num_rows="fixed", height=420, disabled=[...], column_config={...}, key=f"editor_{hoja}_{ver_tabla}")`
  (ancho completo; scroll horizontal/vertical nativo).

**Etiquetas oficiales** (`ETIQUETA_OFICIAL`, tomadas de las filas 4–8 de la planilla) y `column_config`:

| Col | Clave | Etiqueta | Editable | `column_config` |
|---|---|---|---|---|
| A | orden | ORDEN | no | `NumberColumn` |
| B | listado | LISTADO | no | `TextColumn` |
| C | dni | DNI | sí | `NumberColumn(format="%d", step=1)` |
| D | apellido | APELLIDO | sí | `TextColumn` |
| E | nombres | NOMBRES | sí | `TextColumn` |
| F | especialidad | ESPECIALIDAD (TRAYECTO, CURSO Y/O MÓDULO) | sí | `SelectboxColumn(options=cursos)` |
| G / I / K | dist1 / dist2 / dist3 | Distrito 1 / 2 / 3 | sí | `SelectboxColumn(options=distritos)` (2 y 3 admiten vacío) |
| H / J / L | pts_dist1..3 | ptos. | sí | `NumberColumn(min_value=0, max_value=5, step=5)` |
| M | fi | INSTRUCTOR DE FP – FI | sí | `NumberColumn(min 0, max 25, step 25)` |
| N / O / P / Q | fe_sec_orient / fe_sec_tecnico / fe_superior / fe_universitario | FORMACIÓN ESPECÍFICA – Secundario / Sec. técnico / Superior / Universitario | sí | `NumberColumn(min 0, max 3/5/7/8, step 3/5/7/8)` |
| R | cap_docente | CAPACITACIÓN DOCENTE | sí | `NumberColumn(0–3, step 0.05, format="%.2f")` |
| S | cap_especifica | CAPACITACIÓN ESPECÍFICA | sí | `NumberColumn(0–5, step 0.05, format="%.2f")` |
| T | desemp_anios | DESEMPEÑO PROFESIONAL – años | sí | `NumberColumn(0–35, step=1, format="%d")` |
| U | desemp_pts | DESEMPEÑO PROFESIONAL – pts | sí | `NumberColumn(0–8, step=1)` |
| V | form_sup_fp | FORMACIÓN SUPERIOR EN FP | sí | `NumberColumn(0–7, step=7)` |
| W | antig_docencia | ANTIGÜEDAD DOCENCIA OFICIAL | sí | `NumberColumn(0–2.5, step 0.25, "%.2f")` |
| X | antig_fp | ANTIGÜEDAD ÁMBITO FP OFICIAL | sí | `NumberColumn(0–5, step 0.5, "%.2f")` |
| Y / Z | calif1 / calif2 | CALIFICACIÓN 1 / 2 | sí | `NumberColumn(0–1, step 0.1, "%.2f")` |
| AA | art59 | ART 59 DEL ESTATUTO DOCENTE | sí | `NumberColumn(0–10, step 10)` |
| AB | puntaje | PUNTAJE | **no (se recalcula)** | `NumberColumn(format="%.2f")` |

NO MERITUADOS: A (no editable), C, D, E, F, G, H, I (distritos, `SelectboxColumn`), J motivo (`SelectboxColumn(options=MOTIVOS_NO_MERITUADO)`), K observaciones (`TextColumn`).
Etiquetas: A ORDEN · C DNI · D APELLIDO · E NOMBRES · F ESPECIALIDAD · G Distrito 1 · H Distrito 2 · I Distrito 3 · J NO MERITUA / MOTIVO · K OBSERVACIONES DE LA COMISIÓN EVALUADORA.

**Cómo se aplican las ediciones (algoritmo obligatorio, por hoja):**
1. `estado = st.session_state.get(key)`; `edited = (estado or {}).get("edited_rows", {})` → `{posición_fila: {nombre_columna: nuevo_valor}}`.
2. Separar los cambios de la columna `🗑` (solo marcan filas) de los demás. **Si solo hay cambios en `🗑`, no hacer nada más** (no `rerun`, no tocar `ver_tabla`).
3. Para cada fila con cambios de datos: `anterior = item["datos"]`; `nuevo = {**anterior, **{col_a_clave[c]: v}}` con `NaN`→`None` y numpy→nativo;
   `datos, avisos = na.normalizar_edicion_meritudo(anterior, nuevo)` (o `..._no_meritudo`).
4. Solo MERITUADOS: `datos["puntaje"] = na.calcular_ab(datos, distrito_eval, incluir)["ab"]`.
5. Reemplazar `item["datos"]`; acumular `avisos` y mostrarlos con `st.toast`/`st.warning` (“Edición corregida: …”).
6. `ver_tabla += 1`; `guardar_disco()`; `flash = "✏️ Fila actualizada"`; `st.rerun()` (la key nueva descarta `edited_rows` y evita aplicar dos veces).

**Eliminar:** botón `🗑️ Eliminar filas marcadas (k)` bajo cada grilla (`disabled` si k = 0), dentro de un `st.popover` de confirmación. Las filas marcadas = las que tienen `🗑 = True`
en `edited_rows`. Al confirmar: quitar de `registros` por `id`, `ver_tabla += 1`, `guardar_disco()`, `flash`, `st.rerun()`.

## 11.11 Reglas de edición por celda (ya implementadas en `normativa_ayuda.normalizar_edicion_*`)

| Edición | Regla aplicada |
|---|---|
| Cualquier obligatorio vacío (DNI, apellido, nombres, curso, distrito 1, FI / motivo) | Se restaura el valor anterior + aviso. |
| DNI | 7–8 dígitos, se guarda como `int`. Apellido/nombres → MAYÚSCULAS. |
| Distritos | No se permite repetir; sin distrito ⇒ puntos de residencia `None`; con distrito ⇒ 0 ó 5. Un único `5` entre H, J, L. |
| M (FI) | Solo 0 ó 25; **recalcula LISTADO (B)**. |
| N–Q | Valores permitidos 0/3, 0/5, 0/7, 0/8; **excluyentes** (gana la columna editada). |
| R, S, W, X | Se topan a 3,00 / 5,00 / 2,50 / 5,00 y a ≥ 0. |
| T (años) | 1–35 (0/vacío ⇒ T y U vacíos); **recalcula U** salvo que U se edite en la misma operación. |
| U | Solo 0/5/6/8 y requiere T cargado. |
| V, AA, Y, Z | Solo valores permitidos (7; 10; 0/0,1/0,5/1). |
| **AB** | No editable: siempre `calcular_ab(...)`. Cambia también al alternar la checkbox o el Distrito Evaluador (`recalcular_ab_todos`). |
| Motivo (NO MERITUADOS) | Debe pertenecer a `MOTIVOS_NO_MERITUADO`; “Otros” exige observaciones. |

## 11.12 Estructura de `app.py` v2 y qué reutilizar

**Copiar sin cambios del `app.py` actual:** `_ancho`, `CSS` (ajustar), `DISTRITO_DEFECTO`, `LBL_AYUDA` (ya no se usa), `NINGUNO`, `SI/NO`, `HOJA_MER/HOJA_NO`, `NO_MERITUA`,
`HAB_INSTRUCTOR`, `HAB_COMUN`, `CAL_RELOJ/CAL_CATEDRA`, `CALIF_OPCIONES`, `CALIF_DEFECTO`, `NOMBRES_FORMACION`, `TAB_AYUDA`, `listas`, `resumen_base`,
`buscar_dni_en_planilla`, `generar_excel`, `slug_distrito`, `fmt`, `etiqueta_formacion`, `duplicados`, `validar_comun`, `_mtime`, `_registros`, `_orden_siguiente`.

**Eliminar:** `k12`, `k3`, `defecto`, `snapshot`, `restaurar`, `limpiar`, `bloque1`, `bloque2`, `bloque3`, `botones_guardar`, `_editar`, `_eliminar`, `tabla_resumen`, `sidebar`, `ETIQ_MER/ETIQ_NO` (reemplazadas por `ETIQUETA_OFICIAL`).

**Nuevo (esqueleto):**
```python
def init_estado(); def nueva_resp() -> dict; def sanear_resp(); def wk(campo) -> str
def leer_disco(); def guardar_disco(); def recalcular_ab_todos(); def _al_cambiar_config()
def top_bar(distritos) -> tuple[str, bool]                  # (distrito_eval, incluir_residencia_ab)
PASOS: dict[int, dict]  # titulo, cols, ayuda(list[str]), resalta(list[str]), render(fn), validar(fn)
def ruta_activa(resp) -> list[int]; def siguiente_paso(p, ruta); def anterior_paso(p, ruta)
def validar_paso(p, resp) -> list[str]; def primer_paso_invalido(resp) -> int; def validar_todo(resp) -> list[str]
def render_paso_1() ... render_paso_19()                    # uno por paso; escriben en resp (§11.5)
def calculadora_paso(p); def _agregar_cert(p); def _quitar_cert(p, i)
def nav_izquierda(); def panel_ayuda()
def construir_datos(resp, distrito_eval, incluir) -> tuple[str, dict]
def guardar(hoja, datos); def resetear_curso(); def resetear_aspirante()
def preview_en_vivo(); def df_hoja(hoja) -> tuple[DataFrame, dict]; def grilla_general(); def aplicar_ediciones(hoja, ...); def eliminar_marcadas(hoja, ...)
def main()
```

## 11.13 Criterios de aceptación y pruebas (usar `streamlit.testing.v1.AppTest`; las keys de widgets son `w{ver}_{campo}`)

- [ ] Al abrir: la Top Bar está arriba y centrada; no hay contenido en la sidebar; se ve **solo** el Paso 1 en `col_izq` y su ayuda (`P1`) en `col_der` sin expanders.
- [ ] “Siguiente” no avanza con DNI inválido y muestra el error; con DNI válido pasa al Paso 2. “Anterior” vuelve **conservando** el DNI escrito.
- [ ] La vista previa (fila A–AB) muestra el DNI apenas se escribe y resalta la columna del paso actual; cada respuesta nueva completa su celda.
- [ ] Pasos 4–6: tildar “Coincide” pone 5 en H/J/L; no permite dos distritos con 5 ni distritos repetidos.
- [ ] Paso 7 con curso del Anexo 2 (p. ej. `IM30 - Usuario de IA Generativa`): aparece el `st.info` de perfiles y la ayuda lo incluye.
- [ ] Paso 8 con `NO_MERITUA` → siguiente es el 19 (8B); guardar crea fila en NO MERITUADOS con motivo/observaciones; “Otros” exige observaciones.
- [ ] Paso 8 cumple → recorre 9…18; Pañol (00PA) no ofrece la opción de 3 pts en el Paso 10; la calculadora topa en 3,00 y 5,00.
- [ ] Selector de pasos permite saltar solo a pasos válidos; no se puede llegar al guardado con datos incompletos.
- [ ] “Guardar y evaluar OTRO curso…” vuelve al Paso 7 con datos personales y comunes precargados y salta 9, 14–17 si `saltar_precargados`.
- [ ] “Guardar y cargar NUEVO aspirante” vuelve al Paso 1 con todo vacío.
- [ ] Grilla: editar un puntaje (p. ej. R = 9) lo topa a 3,00, recalcula AB, persiste en `sesion_registros.json`; editar FI actualiza LISTADO; editar T actualiza U.
- [ ] Marcar `🗑` y confirmar elimina la fila; con solo marcar no hay `rerun` ni pérdida de marcas.
- [ ] Checkbox AB tildado + distrito evaluador = distrito de residencia del aspirante ⇒ AB = base + 5; con otro distrito evaluador ⇒ AB = base; cambia en todas las filas guardadas.
- [ ] Botón “📥 Descargar Planilla Oficial (.xlsx para Google Sheets)” siempre activo; el archivo abre en Hojas de Cálculo de Google con hojas, formato, validaciones y fórmulas; D1 = distrito evaluador elegido.
- [ ] Recargar el navegador conserva `registros` y la configuración (distrito, checkbox) desde el JSON.

## 11.14 Decisiones nuevas (con valor por defecto; el usuario puede cambiarlas)

| ID | Tema | Valor por defecto asumido |
|---|---|---|
| D7 | Nombre del archivo descargado | `PLANILLA DE DATOS DE ASPIRANTES - <distrito>.xlsx` (mismo nombre oficial + sufijo para no pisar versiones). |
| D8 | AB en registros ya guardados | Derivado: se recalcula al cambiar checkbox, distrito evaluador o editar la grilla. |
| D9 | Eliminar filas | Casilla `🗑` + botón con confirmación (en vez de `num_rows="dynamic"`, que permitiría crear filas incompletas). |
| D10 | Borrador del asistente | No se persiste: al recargar el navegador se pierde solo el aspirante en curso, no los registros guardados. |
| D11 | Datos “comunes” precargados al evaluar otro curso | `CAMPOS_COMUNES` (C–L, M, V, W, X, Y, Z, AA); R, S, T/U, N–Q y habilitación se vuelven a preguntar. |
| D12 | Edición de registros guardados | Solo desde la grilla (se elimina “cargar de nuevo en el asistente”). |
| D13 | `PLANILLA_TRABAJO.xlsx` y backups | El `app.py` v2 no los usa (la descarga parte siempre del original); las funciones siguen en `extractor_datos.py`. |

---

# 12. SEGURIDAD, PERMISOS POR DISTRITO Y AISLAMIENTO MULTI-DISTRITO

> **Instrucción para el modelo programador:**
> 1. Crear el nuevo módulo `auth_usuarios.py` usando **exclusivamente la librería estándar** (`hashlib`, `json`, `os`, `datetime`, `pathlib`).
> 2. No modificar `extractor_datos.py` ni `normativa_ayuda.py`.
> 3. Integrar la autenticación, permisos, aislamiento y modo Zoom/Meet en `app.py` respetando las firmas y reglas definidas a continuación.

---

## 12.0 Visión General y Objetivos
Para permitir el trabajo simultáneo de comisiones evaluadoras que operan en paralelo en distintas mesas o videollamadas (Zoom/Google Meet):
1. **Seguridad y Auditoría:** Autenticación obligatoria con roles (`admin` y `evaluador`) y contraseñas hasheadas en SHA-256.
2. **Permisos Granulares:** Cada usuario evaluador tiene asignada una lista de distritos habilitados (`distritos_permitidos`). El administrador tiene acceso a `"TODOS"`.
3. **Aislamiento Multi-Distrito:** Cada distrito cuenta con su propio archivo de base de datos JSON en `salida/registros_<slug_distrito>.json`. Distintas comisiones pueden trabajar al mismo tiempo en distritos diferentes sin riesgo de colisión ni sobreescritura de datos.
4. **Control de Operador Único (Anti-Colisión en Zoom/Meet):** En un mismo distrito solo puede haber **un operador activo** escribiendo. Si otro evaluador del mismo distrito ingresa, entra en *"Modo Observador (Solo Lectura)"* viendo en vivo lo que se carga, con posibilidad de solicitar/tomar el relevo acordado en la videollamada.
5. **Modo Lectura para Videollamada:** Cuadro de texto limpio y ordenado para que el operador lea en voz alta a la Comisión en Zoom/Meet los datos y puntajes asignados antes de confirmar la carga.

---

## 12.1 Módulo `auth_usuarios.py`

### 12.1.1 Archivos de Persistencia y Estructura JSON

- Directorio base: `salida/` (respetando `extractor_datos.DIR_SALIDA`).
- Archivo de usuarios: `salida/usuarios.json`.
- Archivo de bloqueos activos: `salida/bloqueos_distrito.json`.

#### Estructura de `salida/usuarios.json`:
```json
{
  "version": 1,
  "usuarios": {
    "admin": {
      "username": "admin",
      "password_hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220ac73a56647537149f54ace3b",
      "nombre": "Administrador General",
      "rol": "admin",
      "distritos_permitidos": ["TODOS"],
      "creado": "2026-10-23T12:00:00"
    },
    "comision_mercedes": {
      "username": "comision_mercedes",
      "password_hash": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
      "nombre": "Comisión Mercedes",
      "rol": "evaluador",
      "distritos_permitidos": ["Reg 10 Distrito: 070-MERCEDES"],
      "creado": "2026-10-23T12:10:00"
    }
  }
}
```

*Nota sobre inicialización:* Si `salida/usuarios.json` no existe, se crea automáticamente con el usuario `admin` por defecto:
- `username`: `"admin"`
- `password` en texto plano inicial: `"admin2027"`
- `password_hash`: SHA-256 de `"admin2027"`
- `nombre`: `"Administrador General"`
- `rol`: `"admin"`
- `distritos_permitidos`: `["TODOS"]`

#### Estructura de `salida/bloqueos_distrito.json`:
```json
{
  "Reg 10 Distrito: 070-MERCEDES": {
    "username": "comision_mercedes",
    "nombre": "Comisión Mercedes",
    "timestamp": "2026-10-23T12:35:10"
  }
}
```

### 12.1.2 Especificación de Firmas de Funciones en `auth_usuarios.py`

```python
from __future__ import annotations
import datetime
import hashlib
import json
from pathlib import Path

DIR_SALIDA = Path(__file__).resolve().parent / "salida"
RUTA_USUARIOS = DIR_SALIDA / "usuarios.json"
RUTA_BLOQUEOS = DIR_SALIDA / "bloqueos_distrito.json"

def hashear_password(password: str) -> str:
    """Devuelve el hash SHA-256 en hexadecimal."""
    ...

def inicializar_almacen() -> None:
    """Crea los archivos JSON si no existen y asegura el usuario admin por defecto."""
    ...

def verificar_credenciales(username: str, password: str) -> dict | None:
    """Verifica usuario y contraseña.
    Devuelve dict del usuario (sin password_hash) si es correcto; si falla, devuelve None."""
    ...

def listar_usuarios() -> dict[str, dict]:
    """Devuelve diccionario de todos los usuarios registrados (con campos públicos, sin hash)."""
    ...

def crear_o_actualizar_usuario(
    username: str,
    password: str | None,
    nombre: str,
    rol: str,
    distritos_permitidos: list[str]
) -> tuple[bool, str]:
    """Crea un nuevo usuario o actualiza uno existente.
    Si password es None o vacío al actualizar, conserva el hash anterior.
    Valida que username no sea vacío y que rol sea 'admin' o 'evaluador'.
    Devuelve (True, 'Mensaje de éxito') o (False, 'Motivo del error')."""
    ...

def eliminar_usuario(username: str) -> tuple[bool, str]:
    """Elimina el usuario indicado.
    PROHIBIDO eliminar al usuario 'admin' (devuelve False)."""
    ...

# --- Control de Operador Único ---

def obtener_operador_distrito(distrito: str) -> dict | None:
    """Devuelve dict con {'username', 'nombre', 'timestamp'} del operador activo del distrito,
    o None si el distrito no tiene operador asignado."""
    ...

def tomar_control_distrito(distrito: str, username: str, nombre: str) -> dict:
    """Asigna al usuario como Operador Activo del distrito con timestamp actual.
    Persiste en salida/bloqueos_distrito.json y devuelve el registro creado."""
    ...

def liberar_control_distrito(distrito: str, username: str) -> bool:
    """Si el distrito está operado por username, lo libera y guarda en disco.
    Devuelve True si liberó el bloqueo, False en caso contrario."""
    ...

def listar_bloqueos() -> dict[str, dict]:
    """Devuelve el mapa completo de distritos y sus operadores activos."""
    ...
```

---

## 12.2 Aislamiento de Archivos de Datos por Distrito

### 12.2.1 Nomenclatura y Persistencia
1. Ya no se utiliza un único archivo global `sesion_registros.json` para todos los distritos.
2. Cada distrito evaluador guarda y lee sus registros en:
   ```
   salida/registros_<slug_distrito>.json
   ```
   Ejemplo:
   - Para `"Reg 10 Distrito: 070-MERCEDES"` → `salida/registros_070-MERCEDES.json` (usando `slug_distrito()`).
3. Estructura interna del archivo por distrito:
   ```json
   {
     "version": 2,
     "distrito": "Reg 10 Distrito: 070-MERCEDES",
     "sig_id": 14,
     "config": {
       "incluir_residencia_ab": false
     },
     "registros": [
       {"id": 1, "hoja": "MER", "datos": { ... }},
       {"id": 2, "hoja": "NOMER", "datos": { ... }}
     ]
   }
   ```
4. **Retrocompatibilidad / Migración:**
   Si al abrir un distrito no existe su archivo `registros_<slug>.json`, pero existe el archivo legado `salida/sesion_registros.json`, se leen los registros que coincidan con dicho distrito evaluador; en caso contrario, se inicializa con lista vacía.

### 12.2.2 Ciclo de Cambio de Distrito
Al cambiar el selector de distrito evaluador en la barra superior:
1. Si el usuario actual tenía tomado el control del distrito anterior, se ejecuta `auth.liberar_control_distrito(distrito_anterior, usuario)`.
2. Se cargan los registros desde `salida/registros_<slug_nuevo_distrito>.json`.
3. Se verifica si el nuevo distrito tiene operador activo:
   - Si no tiene operador: el usuario toma automáticamente el control (`auth.tomar_control_distrito`).
   - Si ya está ocupado por otro usuario: entra en **Modo Observador (Solo Lectura)**.

---

## 12.3 Reglas de Concurrencia y Permisos

### 12.3.1 Roles y Filtro de Distritos
| Rol | Distritos accesibles en el selector | Permisos de Administración |
|---|---|---|
| `admin` | **TODOS** los distritos (priorizando Región 10). | Alta/baja de usuarios, reasignar contraseñas, ver bloqueos globales. |
| `evaluador` | Únicamente los definidos en `distritos_permitidos` del usuario. | Sin acceso al panel de administración. |

*Regla:* Si un evaluador tiene asignado `["Reg 10 Distrito: 067-MARCOS PAZ", "Reg 10 Distrito: 057-GENERAL LAS HERAS"]`, el `selectbox` superior solo le mostrará esas dos opciones.

### 12.3.2 Modo Operador Activo vs Modo Observador
- **Operador Activo (`es_operador = True`):**
  - Muestra insignia verde: `🟢 Operador Activo (Edición habilitada)`.
  - El asistente permite escribir, avanzar pasos y presionar los botones de guardado.
  - La grilla inferior `st.data_editor` está habilitada para edición directa celda por celda y borrado de filas.
- **Modo Observador (`es_operador = False`):**
  - Muestra cartel amarillo o azul destacado:
    `👁️ Modo Observador (Operando actualmente: {nombre_operador} desde las {hora})`.
  - **Bloqueo de edición:** Los campos del asistente se muestran deshabilitados (`disabled=True`), los botones de guardado están deshabilitados.
  - La grilla `st.data_editor` se muestra con `disabled=True`.
  - **Botón de Relevo:** Se incluye el botón `🤝 Tomar el control de carga`. Al presionarlo (previo acuerdo en la reunión de Zoom/Meet), se transfiere el rol de operador al usuario actual y se notifica con `st.toast`.

---

## 12.4 Pantalla de Login en `app.py`

1. Si `st.session_state.get("usuario_actual") is None`:
   - Se renderiza un contenedor centrado con ancho restringido (usando columnas `[1, 1.2, 1]`).
   - Título: `🔐 Acceso a la Comisión Evaluadora de FP`.
   - Campos: `Usuario` y `Contraseña` (`type="password"`).
   - Botón: `Iniciar Sesión` (valida contra `auth_usuarios.verificar_credenciales`).
   - Si las credenciales son inválidas: `st.error("Usuario o contraseña incorrectos")`.
   - Si son válidas: se guarda en `st.session_state.usuario_actual = dict_usuario`, se inicializa el distrito y se ejecuta `st.rerun()`.
   - Se detiene la ejecución del resto de `app.py` mediante `st.stop()`.
2. **Cierre de sesión:**
   - Botón permanente `"🚪 Cerrar Sesión"` en la barra superior.
   - Acción: llama a `auth_usuarios.liberar_control_distrito`, borra `usuario_actual` de `session_state` y ejecuta `st.rerun()`.

---

## 12.5 Panel de Administración (Exclusivo `rol == "admin"`)

Visible únicamente cuando `usuario_actual["rol"] == "admin"`.
Se ubica en un contenedor colapsable o pestaña superior (`st.expander("⚙️ Panel de Administración de Usuarios y Comisiones")`):
1. **Pestaña 1: Gestión de Usuarios:**
   - Formulario para Crear / Modificar usuario:
     * Nombre de usuario (`username`).
     * Nombre visible / Comisión (ej. `"Comisión Luján - Mesa 1"`).
     * Contraseña (opcional al editar: si se deja vacía mantiene la actual).
     * Rol (`evaluador` o `admin`).
     * `st.multiselect` de Distritos Permitidos (con opción rápida de seleccionar toda la Región 10).
   - Botón `Guardar Usuario`.
2. **Pestaña 2: Monitoreo en Vivo de Comisiones y Bloqueos:**
   - Tabla con todos los usuarios registrados.
   - Lista en tiempo real de qué distritos están bloqueados y quién es el operador activo en ese instante.
   - Botón para **forzar liberación de bloqueo** de un distrito (por si un usuario cerró la pestaña sin cerrar sesión).
   - Botón para eliminar usuarios (con confirmación; protegido contra borrado de `admin`).
3. **Pestaña 3: Mi Contraseña de Administrador:**
   - Campo para cambiar la clave del usuario `admin` actual.

---

## 12.6 Modo Lectura de Verificación para Zoom/Meet

Para agilizar la dinámica de trabajo en videollamada, el operador no debe perder tiempo leyendo celda por celda ni dictando números sueltos. Se implementa un generador de **Lectura Limpia y Fluida**.

### 12.6.1 Función Generadora de Resumen Textual
En `app.py` (o helper de presentación):
```python
def texto_lectura_comision(hoja: str, datos: dict) -> str:
    """Devuelve un texto formateado en prosa estructurada, listo para ser leído en voz alta
    por el operador a los demás integrantes de la comisión en Zoom/Meet."""
```

### 12.6.2 Formato del Texto de Lectura
```markdown
🗣️ RESUMEN DE LECTURA PARA LA COMISIÓN (Dictamen en voz alta):
--------------------------------------------------------------------------------
• Aspirante: {APELLIDO}, {NOMBRES}  |  DNI: {DNI}
• Especialidad / Curso: {CURSO}
• Dictamen: {MERITÚA en Hoja MERITUADOS | NO MERITÚA en Hoja NO MERITUADOS}

[Si NO MERITÚA]:
• Motivo de exclusión (Col. J): {MOTIVO}
• Observaciones de la Comisión (Col. K): {OBSERVACIONES}

[Si MERITÚA]:
• Distritos Solicitados y Residencia:
  - Distrito 1: {D1} ({5 pts por residencia | 0 pts})
  - Distrito 2: {D2 o 'No solicita'} ({5 o 0 pts})
  - Distrito 3: {D3 o 'No solicita'} ({5 o 0 pts})
• Listado y Formación:
  - Certificado FI (Col. M): {Posee 25 pts -> Listado PRINCIPAL | No posee 0 pts -> Listado COMPLEMENTARIO}
  - Formación Específica (Cols. N-Q): {Nombre del título} ({PTS} pts en Col. {LETRA})
  - Formación Superior en FP (Col. V): {Acredita 7 pts | 0 pts}
• Capacitaciones:
  - Capacitación Docente (Col. R): {PUNTOS} pts (tope 3.00)
  - Capacitación Específica (Col. S): {PUNTOS} pts (tope 5.00)
• Trayectoria y Calificaciones:
  - Desempeño Profesional (Cols. T y U): {AÑOS} años acreditados -> {PUNTOS} pts
  - Antigüedad Docencia Oficial (Col. W): {AÑOS} años -> {PUNTOS} pts
  - Antigüedad FP Oficial (Col. X): {AÑOS} años -> {PUNTOS} pts
  - Calificaciones SET 4 (Cols. Y y Z): Año 1 = {Y} pts | Año 2 = {Z} pts
  - Art. 59 Estatuto (Col. AA): {10 pts sin cargos titulares | 0 pts}
--------------------------------------------------------------------------------
>>> PUNTAJE BASE: {BASE} pts
>>> PUNTAJE CON RESIDENCIA (+5): {CON_RESIDENCIA} pts
>>> PUNTAJE FINAL COLUMNA AB A GUARDAR: {AB} pts
```

### 12.6.3 Ubicación en la Interfaz
1. **En el Paso 18 (Confirmación Final):** Dentro de un contenedor destacado `st.info` con botón `"📋 Copiar resumen para el chat de Zoom/Meet"`.
2. **En la Planilla General Editable:** Botón `"🗣️ Leer fila seleccionada"` que abre un diálogo/popover con el dictamen listo para repasar con la Comisión.

---

## 12.7 Criterios de Aceptación y Pruebas del §12
- [ ] Si no hay sesión iniciada, solo se visualiza la pantalla de login; ninguna planilla ni dato es accesible.
- [ ] Las credenciales por defecto `admin` / `admin2027` ingresan correctamente con rol `admin`.
- [ ] El administrador puede crear usuarios evaluadores con distritos asignados; las contraseñas quedan almacenadas en hash SHA-256 en `salida/usuarios.json`.
- [ ] Un usuario `evaluador` solo ve en el selector de la cabecera los distritos que tiene permitidos.
- [ ] Cada distrito guarda sus registros en `salida/registros_<slug>.json`; cargar registros en Luján no modifica los de Mercedes ni Marcos Paz.
- [ ] Si el Usuario A está operando el Distrito Mercedes, el Usuario B ve el cartel de `Modo Observador` y no puede modificar ni guardar hasta presionar `Tomar el control de carga`.
- [ ] El resumen de lectura para Zoom/Meet genera el texto claro y completo con todos los ítems de las columnas A a AB.

---

# 13. FAMILIAS PROFESIONALES (CATÁLOGO 2027), MULTISELECCIÓN DE CURSOS, ALTA DE CURSOS NUEVOS Y CORRECCIÓN DE ANTIGÜEDADES

> **Instrucción para el modelo programador:**
> 1. Modificar `extractor_datos.py` agregando la persistencia de cursos personalizados y su integración con `'Hoja 2'`.
> 2. Modificar `normativa_ayuda.py` incorporando el diccionario de familias profesionales, la extracción de familias y las listas de valores permitidos y normalizadores de antigüedad.
> 3. Modificar `app.py` rediseñando el Paso 7 (familia + multiselección de especialidades), el guardado múltiple en Pasos 18 y 19, los selectores de años enteros en Pasos 15 y 16, y las `SelectboxColumn` de Cols. W y X en `st.data_editor`.

---

## 13.1 Diccionario de Familias Profesionales según Catálogo 2027

Cada curso de Formación Profesional tiene un código alfanumérico cuyo prefijo de 2 caracteres define su **Familia Profesional** según el Catálogo de Títulos y Certificaciones de la Provincia de Buenos Aires (Listados 2027).

### 13.1.1 Mapeo Oficial de Familias
En `normativa_ayuda.py`:
```python
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
```

### 13.1.2 Funciones de Utilidad en `normativa_ayuda.py`
```python
def obtener_prefijo_familia(curso: str | None) -> str:
    """Devuelve el prefijo de 2 letras del curso (ej: 'IM30 - ...' -> 'IM').
    Si no coincide con ninguna familia conocida, devuelve 'OT'."""
    if not curso or len(curso) < 2:
        return "OT"
    prefijo = curso[:2].upper()
    return prefijo if prefijo in FAMILIAS_PROFESIONALES else "OT"

def obtener_nombre_familia(curso: str | None) -> str:
    """Devuelve el nombre completo descriptivo de la familia."""
    pref = obtener_prefijo_familia(curso)
    return FAMILIAS_PROFESIONALES.get(pref, FAMILIAS_PROFESIONALES["OT"])
```

---

## 13.2 Base de Datos Persistente de Cursos Nuevos (`salida/cursos_personalizados.json`)

### 13.2.1 Inicialización Automática con los 14 Cursos del Catálogo 2027
La planilla base original (`Hoja 2`, Columna A) omitía 14 cursos aprobados en la Resolución del Catálogo Oficial 2027 (IF-2026-29133749-GDEBA-DFPDGCYE).
Al iniciar la aplicación, si el archivo `salida/cursos_personalizados.json` no existe, se crea automáticamente con la siguiente lista precargada:

```json
{
  "version": 1,
  "cursos": [
    "AA54 - Armadora/or de Invernáculos",
    "AA55 - Podadora/or Frutícola",
    "AC36 - Promotora/or de cooperativas y mutuales",
    "IA19 - Elaboradora/or de productos lácteos diversificados",
    "OC49 - Operaria/o Ladrillera/o",
    "IG10 - Operadora/or en Diseño para la Industria Gráfica",
    "MM12 - Desarrolladora/or de Mobiliario y Productos de Carpintería",
    "MT44 - Montadora/or Cañista Industrial",
    "SC03 - Operadora/or de Cuidados de Personas con Discapacidad",
    "TC01 - Empalmadora/or de Fibra Óptica",
    "TC02 - Instaladora/or Reparadora/or de redes de acceso FTTH y redes internas del cliente",
    "TC03 - Analista en Redes de Telecomunicaciones",
    "TC04 - Operadora/or de Redes de Fibra Óptica",
    "MC01 - Orientación Profesional"
  ]
}
```

### 13.2.2 Firmas y Funciones en `extractor_datos.py`

```python
RUTA_CURSOS_PERSONALIZADOS = DIR_SALIDA / "cursos_personalizados.json"

CURSOS_CATALOGO_2027_INICIALES = [
    "AA54 - Armadora/or de Invernáculos",
    "AA55 - Podadora/or Frutícola",
    "AC36 - Promotora/or de cooperativas y mutuales",
    "IA19 - Elaboradora/or de productos lácteos diversificados",
    "OC49 - Operaria/o Ladrillera/o",
    "IG10 - Operadora/or en Diseño para la Industria Gráfica",
    "MM12 - Desarrolladora/or de Mobiliario y Productos de Carpintería",
    "MT44 - Montadora/or Cañista Industrial",
    "SC03 - Operadora/or de Cuidados de Personas con Discapacidad",
    "TC01 - Empalmadora/or de Fibra Óptica",
    "TC02 - Instaladora/or Reparadora/or de redes de acceso FTTH y redes internas del cliente",
    "TC03 - Analista en Redes de Telecomunicaciones",
    "TC04 - Operadora/or de Redes de Fibra Óptica",
    "MC01 - Orientación Profesional",
]

def inicializar_cursos_personalizados() -> None:
    """Crea salida/cursos_personalizados.json con los 14 cursos si no existe."""
    ...

def obtener_cursos_personalizados() -> list[str]:
    """Devuelve la lista limpia de cursos guardados en salida/cursos_personalizados.json."""
    ...

def agregar_o_editar_curso_personalizado(
    codigo_nombre_nuevo: str,
    codigo_nombre_anterior: str | None = None
) -> tuple[bool, str]:
    """Agrega un curso nuevo o reemplaza uno anterior si se editó.
    Guarda en salida/cursos_personalizados.json y retorna (True, mensaje) o (False, error)."""
    ...

def obtener_todos_los_cursos(ruta_base: Path = RUTA_ORIGINAL) -> list[str]:
    """Une los cursos de 'Hoja 2' (columna A) con los de cursos_personalizados.json,
    sin duplicados y ordenados alfabéticamente."""
    ...
```

### 13.2.3 Inyección de Cursos Personalizados en `exportar_excel_bytes()`
Para que el archivo `.xlsx` oficial descargado sea 100% válido y compatible con Google Sheets y Excel:
1. Al momento de generar el libro en memoria, se compara la lista de cursos utilizados en las hojas `MERITUADOS` y `NO MERITUADOS` contra la Columna A de `'Hoja 2'`.
2. Si hay cursos que no están en la Columna A de `'Hoja 2'` (por ser cursos nuevos o personalizados), **se insertan a continuación al final de la Columna A de `'Hoja 2'`**.
3. Se actualizan las referencias de las validaciones de datos de lista en las hojas de datos para que el rango cubra hasta la última fila poblada de `'Hoja 2'`, garantizando que las listas desplegables de Excel reconozcan todos los cursos oficiales y nuevos sin arrojar advertencias.
4. Si el evaluador edita la celda de la Columna F en la planilla `st.data_editor` escribiendo un nombre nuevo, el sistema lo incorpora automáticamente a `salida/cursos_personalizados.json`.

---

## 13.3 Rediseño del Paso 7: Selección de Familia + Multiselección de Especialidades

Muchos aspirantes se inscriben a varios cursos de la misma familia profesional (por ejemplo, en Informática a `IM30 - Usuario de IA Generativa`, `IM01 - Operador de PC` e `IM05 - Programador`). El sistema debe permitir cargar todos los cursos del legajo en un solo flujo.

### 13.3.1 Componentes de la Interfaz en el Paso 7
En `col_izq` (Paso 7 - Columna F):
1. **Selector de Familia Profesional (`st.selectbox`):**
   - Opciones: `["TODAS LAS FAMILIAS"] + list(FAMILIAS_PROFESIONALES.values())`.
   - Por defecto: `"TODAS LAS FAMILIAS"`.
2. **Selector Múltiple de Especialidades (`st.multiselect`):**
   - Etiqueta: `"Especialidades a las que se inscribe el aspirante (seleccione una o varias) *"`
   - Opciones filtradas dinámicamente según la familia seleccionada (pero conservando en la selección las especialidades ya marcadas aunque se cambie de familia en el dropdown).
   - `resp["cursos_seleccionados"]: list[str]` almacena todos los cursos elegidos para este aspirante.
   - Si no hay cursos seleccionados, bloquea el avance al Paso 8.
3. **Bloque Desplegable `"➕ Agregar / Editar Especialidad que no está en el listado"`:**
   - Un `st.expander` con:
     * Selector del prefijo de familia (ej: `IM`, `MT`, `AC`).
     * Campo de texto para el código específico (ej: `IM31`).
     * Campo de texto para el nombre oficial del curso (ej: `Especialista en Ciberseguridad Aplicada`).
     * Botón `"💾 Guardar Curso en Base de Datos"`: ejecuta `extractor_datos.agregar_o_editar_curso_personalizado(...)`, lo agrega a `salida/cursos_personalizados.json`, lo incorpora a las opciones y lo añade automáticamente a `resp["cursos_seleccionados"]`.

### 13.3.2 Guardado Múltiple Automático (Pasos 18 y 19)
- En el Paso 18 (y Paso 19 si no meritúa), al hacer clic en cualquiera de los dos botones de guardado (`💾 Guardar y evaluar OTRO curso...` o `✅ Guardar y cargar NUEVO aspirante`):
  1. El sistema toma la lista `resp["cursos_seleccionados"]`.
  2. Para cada curso `c` de la lista:
     * Construye los datos con `especialidad = c`.
     * Asigna un nuevo `id` único consecutivo y calcula el `PUNTAJE (Col. AB)` correspondiente.
     * Inserta la fila en `MERITUADOS` o `NO MERITUADOS`.
  3. Muestra mensaje de éxito: `f"✅ Se guardaron {len(cursos_seleccionados)} cursos para {apellido}, {nombres}."`
  4. Si alguna de las especialidades requiere un ajuste puntual de puntaje, el evaluador puede modificar la celda directamente en la grilla inferior `st.data_editor`.

---

## 13.4 Corrección Estricta de Antigüedad Docente (Col. W) y Antigüedad en FP (Col. X)

### 13.4.1 Marco Normativo y Regla de Cálculo
- **Prohibición de Decimales Arbitrarios:** El Estatuto Docente y los Ítems 10.7 y 10.8 de la Disposición 13/2025 establecen que la antigüedad se acredita exclusivamente en **años lectivos completos** mediante Certificación de Servicios oficial. Valores arbitrarios (como `0.63` o `1.15`) son **inválidos**.
- **Paso 15 - Columna W (Antigüedad en Docencia Oficial - Ítem 10.7):**
  * Puntos por año lectivo: **0.25 pts**.
  * Tope máximo: **2.50 pts** (se alcanza a los 10 años).
  * Entrada de usuario: Selector de años lectivos enteros: `0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 o más`.
  * Cálculo: `round(min(anios, 10) * 0.25, 2)`.
  * Valores admitidos estrictos: `[0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5]`.
- **Paso 16 - Columna X (Antigüedad en el Ámbito de FP Oficial - Ítem 10.8):**
  * Puntos por año lectivo: **0.50 pts**.
  * Tope máximo: **5.00 pts** (se alcanza a los 10 años).
  * Entrada de usuario: Selector de años lectivos enteros: `0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 o más`.
  * Cálculo: `round(min(anios, 10) * 0.50, 2)`.
  * Valores admitidos estrictos: `[0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]`.

### 13.4.2 Saneamiento y Normalización en `normativa_ayuda.py`
Se agregan funciones puras para validar y sanear valores en memoria o cargados desde JSON:

```python
VALORES_PERMITIDOS_ANTIG_DOCENCIA = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5)
VALORES_PERMITIDOS_ANTIG_FP = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0)

def normalizar_antiguedad_docencia(valor: float | int | None) -> float:
    """Redondea al múltiplo de 0.25 más cercano en el rango [0.0, 2.5]."""
    if valor is None:
        return 0.0
    v = float(valor)
    if v <= 0:
        return 0.0
    if v >= 2.5:
        return 2.5
    return min(VALORES_PERMITIDOS_ANTIG_DOCENCIA, key=lambda x: abs(x - v))

def normalizar_antiguedad_fp(valor: float | int | None) -> float:
    """Redondea al múltiplo de 0.50 más cercano en el rango [0.0, 5.0]."""
    if valor is None:
        return 0.0
    v = float(valor)
    if v <= 0:
        return 0.0
    if v >= 5.0:
        return 5.0
    return min(VALORES_PERMITIDOS_ANTIG_FP, key=lambda x: abs(x - v))
```

- Al leer cualquier archivo `salida/registros_<slug>.json`, la función `cargar_distrito()` pasa automáticamente cada fila por `normalizar_antiguedad_docencia` y `normalizar_antiguedad_fp`, asegurando que registros antiguos con decimales no estándar queden regularizados y con la Columna AB recalculada.

### 13.4.3 Grilla `st.data_editor`
En la configuración de columnas de la grilla editable:
- **Columna W:** Reemplazar `NumberColumn` por `SelectboxColumn(options=[0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5])`.
- **Columna X:** Reemplazar `NumberColumn` por `SelectboxColumn(options=[0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0])`.
- De este modo se imposibilita que el usuario tipee decimales erróneos en la tabla.

---

## 13.5 Criterios de Aceptación y Pruebas del §13
- [ ] Al iniciar la app por primera vez, se genera `salida/cursos_personalizados.json` con los 14 cursos faltantes del Catálogo 2027.
- [ ] La lista de cursos en pantalla unifica los de `'Hoja 2'` con los de `salida/cursos_personalizados.json` sin duplicados.
- [ ] En el Paso 7, el usuario puede filtrar por Familia Profesional y seleccionar múltiples cursos a la vez.
- [ ] Al guardar un aspirante con N cursos seleccionados en el Paso 7, se generan automáticamente N filas en la planilla con los puntajes y datos correspondientes.
- [ ] Es posible dar de alta un curso nuevo en el Paso 7 y que quede inmediatamente disponible y seleccionado.
- [ ] En el Paso 15, el usuario selecciona años enteros (0 a 10) y Columna W solo adopta múltiplos de 0.25 (máx 2.50).
- [ ] En el Paso 16, el usuario selecciona años enteros (0 a 10) y Columna X solo adopta múltiplos de 0.50 (máx 5.00).
- [ ] En `st.data_editor`, las Columnas W y X son desplegables con valores oficiales estrictos.
- [ ] La descarga del archivo `.xlsx` inyecta los cursos nuevos en la Columna A de `'Hoja 2'`, manteniendo la validez del libro en Excel y Google Sheets.

---

## 14. Migración a Aplicación Web Estática (HTML/CSS/JS para GitHub Pages)

### 14.1 Propósito y Fundamentos de Arquitectura
La versión actual de la aplicación basada en Streamlit requiere un entorno de ejecución Python con servidor local o en la nube, reconexiones WebSocket y recargas de página (`st.rerun`). Para garantizar portabilidad absoluta, máxima velocidad de respuesta (60 FPS sin latencia de red), despliegue gratuito e inmediato en **GitHub Pages** (o cualquier servidor estático / apertura directa `file://` en navegador), se define la migración a una **Aplicación Web Estática Pura** alojada en la carpeta `web/`.

#### Principios Clave:
1. **Zero-Backend (100% Client-Side):** Toda la lógica de cálculo, validación, evaluación de normativa, persistencia y generación de archivos Excel `.xlsx` corre exclusivamente en el motor JavaScript del navegador del usuario.
2. **Cero Transcripción Manual (Regla de Oro):** Queda terminantemente prohibido duplicar o transcribir a mano en JavaScript los textos normativos de `normativa_ayuda.py`, las listas de cursos o los distritos. Se implementa un script puente en Python (`generar_datos_web.py`) que lee los módulos existentes y compila automáticamente `web/datos.js` y copia `web/plantilla.xlsx`.
3. **Persistencia Local Segura:** Almacenamiento en `localStorage` por distrito (`evaluador_distrito_<slug>`) y de usuarios (`evaluador_usuarios`), complementado con descarga y carga de archivos `.json` de progreso.
4. **Exportación Oficial con ExcelJS:** Generación binaria en el navegador del archivo `.xlsx` oficial a partir de `web/plantilla.xlsx`, respetando celdas combinadas, estilos, fórmulas y validaciones.

---

### 14.2 Estructura del Proyecto Web (`web/`)

```
evaluador_fp_reg10/
├── ... (código Python existente: extractor_datos.py, normativa_ayuda.py, auth_usuarios.py)
├── generar_datos_web.py          # Script puente generador (ejecuta en Python)
└── web/                          # Carpeta lista para GitHub Pages
    ├── index.html                # Estructura semántica, Bootstrap 5, ExcelJS CDN, modales
    ├── estilos.css               # Diseño profesional en 3 secciones (100% ancho, sticky headers, inline-edit)
    ├── plantilla.xlsx            # Copia exacta de PLANILLA DE DATOS DE ASPIRANTES.xlsx
    ├── datos.js                  # Compilado automático generado por generar_datos_web.py
    └── app.js                    # Lógica interactiva Vanilla JS (Auth, Wizard 1-18, Tabla en Vivo, ExcelJS)
```

---

### 14.3 Especificación del Script Puente (`generar_datos_web.py`)

#### 14.3.1 Responsabilidades del Script
1. **Lectura y Unificación de Datos:**
   - **Cursos:** Lee los cursos de `'Hoja 2'` de la planilla original más los 14 cursos del Catálogo 2027 (`extractor_datos.obtener_todos_los_cursos()`).
   - **Familias Profesionales:** Exporta el diccionario `FAMILIAS_PROFESIONALES` (códigos de 2 letras y nombres descriptivos).
   - **Distritos:** Lee los distritos oficiales de `'Hoja 2'` ordenados con los códigos de la Región 10 primero (`extractor_datos.obtener_distritos()`).
   - **Ayudas Normativas:** Exporta el diccionario completo `AYUDAS` de `normativa_ayuda.py` con sus títulos, columnas asociadas, normativas citadas y textos completos formateados.
   - **Perfiles Anexo 2 (Com. 07/2026):** Exporta `PERFILES_NUEVOS_DISENOS` y `_GRUPO_TELECOM`.
   - **Tablas y Topes de Puntaje:** Exporta `TABLA_CAP_DOCENTE`, `TABLA_CAP_ESPECIFICA`, `TABLA_DESEMPENO`, topes máximos y constantes de puntos.
   - **Opciones y Motivos:** Exporta `OPCIONES_FORMACION_ESPECIFICA`, `OPCIONES_FORMACION_PANOL`, `OPCIONES_ESCALA_CALIFICACION` y `MOTIVOS_NO_MERITUADO`.
   - **Usuarios Iniciales:** Exporta los usuarios definidos en `salida/usuarios.json` (o crea por defecto el usuario `admin` con clave inicial `admin2027` y hash SHA-256).
2. **Copia de la Plantilla Binaria:**
   - Copia de manera segura `PLANILLA DE DATOS DE ASPIRANTES.xlsx` hacia `web/plantilla.xlsx`.
3. **Generación de `web/datos.js`:**
   - Escribe el archivo en formato JavaScript definiendo el objeto global `window.DATOS_APP = { ... };`.

#### 14.3.2 Estructura de `window.DATOS_APP` en `web/datos.js`
```javascript
// Archivo generado automáticamente por generar_datos_web.py - NO EDITAR A MANO
window.DATOS_APP = {
  version: 1,
  generado: "2026-10-27T...",
  distritos: ["067-MARCOS PAZ", "057-GENERAL LAS HERAS", ...],
  distritosPrioritarios: ["067", "057", "063", "070", "044", "093", "101"],
  familias: {
    "00": "00 - Cargos Docentes (Pañol / Preceptor)",
    "AA": "AA - Actividades Agropecuarias",
    // ...
  },
  cursos: [
    "00PA - Pañol",
    "00PR - Preceptor",
    "AA54 - Armadora/or de Invernáculos",
    // ...
  ],
  cursosIniciales2027: [...],
  ayudas: {
    "P1": { "titulo": "DNI y Residencia", "columnas": "C", "normativa": [...], "texto": "..." },
    // ... todas las ayudas normativas de los pasos 1 a 18 y de habilitación
  },
  perfilesAnexo2: [
    { "nombre": "Usuaria/o de IA Generativa", "resolucion": "RESOC-2026-3756 / IM30", "claves": [["ia generativa"]], "titulos": "...", "oficios": "..." },
    // ...
  ],
  grupoTelecom: { "titulos": "...", "oficios": null },
  tablasPuntaje: {
    capDocente: [[5, 10, 0.05], [11, 30, 0.10], [31, 50, 0.15], [51, 70, 0.30], [71, 100, 0.40], [101, null, 0.60]],
    capEspecifica: [[5, 10, 0.05], [11, 15, 0.10], [16, 20, 0.15], [21, 30, 0.20], [31, null, 0.30]],
    desempeno: [[0, 2, 0], [3, 4, 5], [5, 9, 6], [10, null, 8]]
  },
  topes: {
    capDocente: 3.00,
    capEspecifica: 5.00,
    antigDocencia: 2.50,
    antigFp: 5.00
  },
  puntosFijos: {
    fi: 25,
    residencia: 5,
    formSupFp: 7,
    art59: 10,
    ptsXAnioDocencia: 0.25,
    ptsXAnioFp: 0.50
  },
  opcionesFormacion: {
    "Ninguno / Sin orientación afín": { N: 0, O: 0, P: 0, Q: 0 },
    "Secundario orientado afín": { N: 3, O: 0, P: 0, Q: 0 },
    "Secundario Técnico afín": { N: 0, O: 5, P: 0, Q: 0 },
    "Superior afín": { N: 0, O: 0, P: 7, Q: 0 },
    "Universitario de grado afín": { N: 0, O: 0, P: 0, Q: 8 }
  },
  opcionesFormacionPanol: {
    "Ninguno / Sin título técnico (secundario común suma 0)": { N: 0, O: 0, P: 0, Q: 0 },
    "Secundario Técnico": { N: 0, O: 5, P: 0, Q: 0 },
    "Superior Técnico": { N: 0, O: 0, P: 7, Q: 0 },
    "Universitario Técnico": { N: 0, O: 0, P: 0, Q: 8 }
  },
  opcionesCalificacion: {
    "9.51 a 10": 1.00,
    "8 a 9.50": 0.50,
    "6 a 7.99": 0.10,
    "Sin calificación": 0.0
  },
  motivosNoMerituado: [
    "No presenta DNI",
    "No presenta Titulo Secundario",
    "No presenta Anexo 3",
    "No Reune Requisitos",
    "Aspirante Jubilado",
    "NO ACREDITA ANTECEDENTES PROFESIONALES ESPECÍFICOS",
    "Otros"
  ],
  usuariosIniciales: {
    "admin": {
      "username": "admin",
      "password_hash": "...", // Hash SHA-256 de "admin2027"
      "nombre": "Administrador General",
      "rol": "admin",
      "distritos_permitidos": ["TODOS"]
    }
  }
};
```

---

### 14.4 Módulo de Autenticación, Roles y Administración de Usuarios en `web/app.js`

#### 14.4.1 Modelo de Autenticación en Cliente
1. **Almacenamiento de Usuarios:**
   - La base de datos de usuarios reside en `localStorage.getItem("evaluador_usuarios")`.
   - Si no existe en el primer inicio, se inicializa automáticamente con `window.DATOS_APP.usuariosIniciales`.
2. **Cálculo de Hash SHA-256:**
   - Se utiliza la API nativa del navegador: `crypto.subtle.digest("SHA-256", new TextEncoder().encode(password))`.
   - Para entornos con protocolo `file://` o navegadores donde `crypto.subtle` esté restringido a contextos seguros (`isSecureContext === false`), se provee una función de hashing SHA-256 en JavaScript puro como salvaguarda infalible.
3. **Sesión Activa:**
   - Se guarda en `sessionStorage.getItem("evaluador_sesion_activa")`: `{ username, nombre, rol, distritos_permitidos }`.
   - Si no hay sesión activa, la app muestra exclusivamente la pantalla de **Login**.
   - Al loguearse exitosamente, se oculta el login y se revela el dashboard principal con la barra superior de usuario y botón de cerrar sesión.

#### 14.4.2 Modal "⚙️ Administrar Usuarios" (Exclusivo Rol `admin`)
- Accesible únicamente si el usuario autenticado tiene rol `admin` (`admin2027`).
- **Listado y Edición:** Permite ver la lista de usuarios, crear un nuevo usuario, editar nombre, cambiar contraseña y asignar distritos permitidos (checklist con los distritos disponibles o selector de `"TODOS"`).
- **Exportar `usuarios.json`:** Descarga en el navegador un archivo `.json` con la nómina de usuarios y sus hashes.
- **Importar `usuarios.json`:** Permite subir un archivo JSON para actualizar los usuarios en `localStorage` (útil para sincronizar usuarios creados en otras máquinas).

---

### 14.5 Cabecera Superior Centrada y Persistencia por Distrito

#### 14.5.1 Controles de la Cabecera
1. **Selector de Distrito Evaluador:**
   - Filtrado según los permisos del usuario logueado (`distritos_permitidos`). Si tiene `"TODOS"`, muestra toda la lista priorizada de la Región 10.
   - Al cambiar de distrito, el sistema conmuta automáticamente los registros activos cargando desde `localStorage` la clave `evaluador_distrito_<slug>`.
2. **Checkbox de Residencia (+5 pts):**
   - Checkbox: `"Incluir +5 pts de residencia del Distrito Evaluador en Columna AB"`.
   - Estado guardado por distrito. Si está tildado, la Columna AB suma los 5 puntos al aspirante si su domicilio coincide con el distrito evaluador activo. Si no está tildado, Columna AB refleja el puntaje base.
3. **Persistencia Automática Local:**
   - Cada alta, edición o baja de registro se sincroniza instantáneamente en `localStorage` con la estructura:
     ```json
     {
       "distrito": "067-MARCOS PAZ",
       "merituados": [ ... ],
       "no_merituados": [ ... ],
       "cursos_personalizados": [ ... ],
       "incluir_residencia": false,
       "ultima_modificacion": "2026-10-27T..."
     }
     ```
4. **Botones de Respaldo Offline:**
   - **"💾 Guardar Progreso (.json)":** Descarga directa de `progreso_<slug_distrito>.json`.
   - **"📂 Cargar Progreso (.json)":** Selector de archivo con lectura `FileReader` que restaura los aspirantes evaluados para ese distrito.

#### 14.5.2 Generación y Descarga de Planilla Oficial (`ExcelJS`)
- **Botón "📥 Descargar Planilla Oficial (.xlsx para Google Sheets)":**
  1. Descarga en memoria `web/plantilla.xlsx` como `ArrayBuffer` mediante `fetch()`.
  2. Carga el libro con `new ExcelJS.Workbook()` y `workbook.xlsx.load(buffer)`.
  3. Escribe en ambas hojas (`MERITUADOS` y `NO MERITUADOS`) la celda `D1` con el formato exacto del distrito evaluador: `Reg 10 Distrito: <distrito>`.
  4. Inserta las filas de `MERITUADOS` a partir de la fila 9, escribiendo cada valor en su columna correspondiente (A a AB) conservando estilos originales, bordes y fuentes.
  5. Inserta las filas de `NO MERITUADOS` a partir de la fila 9 (columnas A a K).
  6. Si existen cursos nuevos o personalizados dados de alta por el usuario, los agrega al final de la Columna A en `'Hoja 2'`, actualizando el rango de opciones válidas para listas desplegables.
  7. Exporta el libro con `workbook.xlsx.writeBuffer()` y genera la descarga con nombre `PLANILLA_EVALUADA_<slug_distrito>_<timestamp>.xlsx`.
  8. El archivo resultante es 100% nativo, con formato intacto, compatible de inmediato con Google Sheets y Microsoft Excel.

---

### 14.6 Interfaz de Usuario Dividida en Tres Secciones (Layout & UX)

El contenedor principal ocupa el 100% del ancho de pantalla (`container-fluid`) con una distribución balanceada:

```
+----------------------------------------------------------------------------------------------------+
|                                    CABECERA SUPERIOR CENTRADA                                      |
|  Distrito: [ 067-MARCOS PAZ v ]   [x] Incluir +5 pts   [📥 Descargar .xlsx] [💾 Guardar] [📂 Cargar] |
+--------------------------------------------------+-------------------------------------------------+
|      SECCIÓN SUPERIOR IZQUIERDA (50% ancho)      |      SECCIÓN SUPERIOR DERECHA (50% ancho)       |
|            Asistente Guiado (Pasos 1 al 18)      |           Ayuda Normativa y Perfiles Anexo 2    |
|  - Barra de Progreso y Paso Actual               |  - Marco Legal (Dispo 13/25, Com 07/26)        |
|  - Pregunta Activa y Controles Validados        |  - Texto Explicativo y Ejemplos Oficiales       |
|  - Calculadoras de Horas (Col. R y S)            |  - Equivalencias de Títulos Nuevos Diseños 2027 |
|  - Años de Antigüedad Estrictos (Col. W y X)     |                                                 |
|  - [⬅️ Anterior]  [Siguiente ➡️]                  |                                                 |
+--------------------------------------------------+-------------------------------------------------+
|                                SECCIÓN INFERIOR (100% ancho)                                       |
|                                    PLANILLA EN VIVO                                                |
|  [Fila en vivo del aspirante que se está evaluando actualmente: Col A ... Col AB]                  |
|  ------------------------------------------------------------------------------------------------  |
|  Pestañas: [ 📋 MERITUADOS (N) ]  [ ⚠️ NO MERITUADOS (M) ]          [ 🔍 Buscar por DNI/Apellido ] |
|  Tabla completa con Cabeceras Fijas (Sticky Header) y Edición Directa al Clic en Celdas            |
+----------------------------------------------------------------------------------------------------+
```

#### 14.6.1 Sección Superior Izquierda: Asistente Guiado Paso a Paso (Pasos 1 al 18)
- Flujo secuencial reactivo con validación instantánea antes de avanzar:
  * **Paso 1 (DNI - Col. C):** Entrada numérica limpia, sin puntos ni comas.
  * **Paso 2 (Apellido - Col. D):** Entrada de texto, mayúsculas automáticas.
  * **Paso 3 (Nombres - Col. E):** Entrada de texto, mayúsculas automáticas.
  * **Pasos 4, 5 y 6 (Distritos 1, 2 y 3 - Cols. G a L):**
    - Selectores de los 3 distritos declarados por el aspirante.
    - Checkbox o selector automático para asignar los 5 puntos de residencia únicamente al distrito que coincide con el DNI vigente (los demás quedan en 0 automáticamente).
  * **Paso 7 (Especialidad / Cursos - Col. F):**
    - Selector de **Familia Profesional** (filtra la lista con los prefijos del Catálogo 2027: IM, AA, MT, etc.).
    - Selector múltiple con checkboxes: permite seleccionar **varias especialidades a la vez** para el mismo aspirante, repitiendo la valoración de antecedentes sin reescribir todo el legajo.
    - Modal/formulario **"➕ Agregar / Editar Especialidad"**: permite cargar código y denominación de un curso no catalogado, incorporándolo a la lista y seleccionándolo inmediatamente.
  * **Paso 8 (Filtro de Habilitación):**
    - Preguntas de requisitos comunes (Inciso 3: Anexo 3, DNI ambas caras, Título secundario/superior).
    - Para instructores, preguntas del Inciso 6 (Vía 6.1: experiencia laboral + título/350hs; o Vía 6.2: idoneidad estratégica / 2 dictados completos / curso en certificado FI).
    - Si no cumple los requisitos, deriva al **Paso 19 ("NO MERITÚA")** con selección de motivo y observaciones obligatorias si es "Otros".
  * **Paso 9 (Certificado FI - Cols. B y M):**
    - ¿Posee certificado de FI registrado? Sí (25 pts -> **LISTADO PRINCIPAL**) o No (0 pts -> **LISTADO COMPLEMENTARIO**).
  * **Paso 10 (Formación Específica - Cols. N a Q):**
    - Radio buttons excluyentes: Ninguno (0), Secundario orientado (3), Secundario Técnico (5), Superior (7), Universitario (8).
    - Si el curso seleccionado es Pañolero (`00PA`), solo otorga puntos a títulos técnicos (secundario común suma 0).
  * **Paso 11 (Capacitación Docente - Col. R):**
    - Calculadora integrada: el evaluador ingresa cursos en horas reloj u horas cátedra (`hs_reloj = trunc(hs_catedra * 2 / 3)`).
    - Aplica la escala oficial de la Disposición 13/2025 y aplica el tope estricto de **3.00 pts**.
  * **Paso 12 (Capacitación Específica - Col. S):**
    - Calculadora integrada por tramos de horas reloj/cátedra con tope estricto de **5.00 pts**.
  * **Paso 13 (Desempeño Profesional - Cols. T y U):**
    - Entrada de años laborales acreditados (0 a 35).
    - Asigna automáticamente los puntos en Col. U: 0-2 años = 0; 3-4 años = 5; 5-9 años = 6; 10+ años = 8.
  * **Paso 14 (Formación Superior en FP - Col. V):**
    - ¿Posee Tecnicatura Superior/Universitaria en FP con validez nacional? Sí (7 pts) o No (0 pts).
  * **Paso 15 (Antigüedad en Docencia Oficial - Col. W):**
    - Selector cerrado de años lectivos enteros: `0, 1, 2, ..., 10 o más`.
    - Cálculo estricto: `años * 0.25` (tope **2.50 pts**). Prohibidos decimales no estándar.
  * **Paso 16 (Antigüedad en Ámbito de FP - Col. X):**
    - Selector cerrado de años lectivos enteros: `0, 1, 2, ..., 10 o más`.
    - Cálculo estricto: `años * 0.50` (tope **5.00 pts**). Prohibidos decimales no estándar.
  * **Paso 17 (Calificaciones de los Últimos 2 Años en FP - Cols. Y y Z):**
    - Selectores para Año 1 y Año 2 con opciones oficiales: `9.51 a 10 (1.00 pt)`, `8 a 9.50 (0.50 pt)`, `6 a 7.99 (0.10 pt)`, `Menos de 6 / Sin calificación (0.00 pt)`.
  * **Paso 18 (Art. 59 Estatuto Docente - Col. AA) y Cierre:**
    - ¿Posee cargos u horas titulares? No posee titulares = **10 pts**; Posee titulares = **0 pts**.
    - Cálculo en tiempo real del puntaje de la Columna AB.
    - Botones de acción final:
      * **"🗣️ Resumen para leer en Zoom/Meet":** Abre modal con texto estructurado para lectura rápida en la comisión evaluadora (DNI, Nombre, Cursos, Listado, Desglose de puntajes y Total).
      * **"➕ Evaluar otra Familia/Curso del MISMO Aspirante":** Guarda las filas evaluadas y resetea el wizard al Paso 7, conservando datos filiatorios, distritos y probanzas comunes.
      * **"👤 Nuevo Aspirante":** Guarda todas las filas evaluadas y limpia el formulario completo para iniciar un legajo nuevo.

#### 14.6.2 Sección Superior Derecha: Panel de Ayuda, Reglamentación y Perfiles
- Sincronización bidireccional inmediata con el paso visible en la sección izquierda.
- Muestra:
  * Encabezado con título del paso y columnas de la planilla impactadas.
  * Artículos y normativas aplicables (Disposición 13/2025, Comunicación 07/2026, Estatuto Docente).
  * Texto explicativo con ejemplos prácticos de casos válidos y no válidos.
  * **Tarjeta de Nuevos Diseños (Anexo 2 Com. 07/2026):** Si el curso seleccionado coincide con alguno de los diseños aprobados (ej. `IA Generativa`, `Fibra Óptica`, `Podador Frutícola`, `Promotor de Cooperativas`, etc.), despliega automáticamente la lista de títulos y oficios habilitados para que el evaluador no tenga que consultar archivos externos.

#### 14.6.3 Sección Inferior: Planilla en Vivo y Grilla Interactiva Editable
1. **Fila en Vivo del Aspirante Actual:**
   - Barra superior que refleja en tiempo real cómo se compondrá la fila en la planilla oficial (Columnas A a AB) a medida que el evaluador selecciona opciones o tipea valores.
2. **Tabla Completa del Distrito:**
   - Pestañas independientes: **`MERITUADOS (<total>)`** y **`NO MERITUADOS (<total>)`**.
   - Buscador instantáneo con filtrado reactivo por DNI, Apellido o Especialidad.
   - Cabeceras fijas (`sticky header`) para navegación fluida con decenas de registros.
3. **Edición Directa en Celda (Inline Editing):**
   - El evaluador puede hacer clic sobre cualquier celda de la tabla para editarla sin volver al asistente:
     * Celdas de texto (DNI, Apellido, Nombre, Observaciones): se convierten en input editable.
     * Celdas de puntaje con valores discretos (Formación, FI, Antigüedad Docente 0.25, Antigüedad FP 0.50, Calificaciones, Art. 59, Residencia): se convierten en selector desplegable con las únicas opciones válidas según normativa.
     * Al confirmar la edición (Enter o blur), se valida el dato y **se recalcula inmediatamente la Columna AB** de esa fila, guardando el cambio en `localStorage`.
   - Botón de eliminación por fila con modal de confirmación rápida.

---

### 14.7 Plan de Implementación para el Próximo Turno

En el siguiente turno, el modelo liviano generará los 4 archivos de la solución:
1. `generar_datos_web.py`
   - Script ejecutable en consola Python.
   - Importa `extractor_datos`, `normativa_ayuda` y `auth_usuarios`.
   - Crea el directorio `web/` si no existe.
   - Copia `PLANILLA DE DATOS DE ASPIRANTES.xlsx` hacia `web/plantilla.xlsx`.
   - Genera `web/datos.js` con el objeto global `window.DATOS_APP`.
2. `web/index.html`
   - Estructura HTML5 moderna con enlaces a Bootstrap 5 CSS/JS y `ExcelJS` (CDN jsDelivr).
   - Estructura semántica de las 3 secciones (superior izq, superior der, inferior).
   - Modales: Login, Administrar Usuarios, Agregar Curso Nuevo, Resumen Zoom/Meet.
3. `web/estilos.css`
   - Variables CSS para paleta institucional, tipografía moderna legible, 100% de ancho de pantalla.
   - Cabecera fija, tarjetas con sombras suaves, scrollbars estilizadas.
   - Estilos para celdas editables (`.editable-cell`), estados hover y alertas visuales.
4. `web/app.js`
   - Módulo JS autocontenido:
     * Inicialización de datos y autenticación (SHA-256 + sesión).
     * Gestión de usuarios y distritos.
     * Máquina de estados del asistente (Pasos 1 al 18 y Paso 19).
     * Calculadoras de carga horaria e inferencia de perfiles del Anexo 2.
     * Renderizador y buscador de la planilla en vivo.
     * Controlador de edición inline con validaciones y recálculo instantáneo.
     * Exportador binario con `ExcelJS` sobre `plantilla.xlsx`.

---

### 14.8 Criterios de Aceptación y Pruebas del §14
- [ ] El script `python generar_datos_web.py` se ejecuta sin errores, genera `web/datos.js` y copia `web/plantilla.xlsx`.
- [ ] `web/datos.js` contiene todos los cursos oficiales, familias profesionales, distritos, ayudas de los 18 pasos, perfiles de nuevos diseños y usuarios iniciales.
- [ ] La aplicación web carga correctamente en cualquier navegador sin dependencias de servidor Python (100% cliente).
- [ ] El sistema de login valida credenciales con hash SHA-256; el usuario `admin` (`admin2027`) puede gestionar usuarios, contraseñas y permisos de distrito.
- [ ] El evaluador puede seleccionar su distrito y la selección de distritos se ajusta a sus permisos.
- [ ] El asistente de los 18 pasos guía la carga pregunta a pregunta; en el Paso 7 permite filtrar por familia profesional y marcar múltiples especialidades a la vez.
- [ ] Las calculadoras de capacitación docente y específica computan horas reloj/cátedra respetando los topes oficiales (3.00 y 5.00).
- [ ] Los selectores de antigüedad docente (Col. W) y FP (Col. X) solo admiten años enteros y aplican múltiplos estrictos (0.25 y 0.50).
- [ ] El panel superior derecho muestra la ayuda y perfiles del Anexo 2 sincronizados en tiempo real con el paso actual.
- [ ] La fila en vivo y la tabla inferior reflejan instantáneamente los datos cargados.
- [ ] Cualquier celda de la tabla inferior es editable al hacer clic, con opciones validadas y recálculo automático de la Columna AB.
- [ ] El progreso se guarda automáticamente en `localStorage` y se puede exportar/importar en formato `.json`.
- [ ] El botón de descarga oficial utiliza `ExcelJS` para inyectar los datos en `web/plantilla.xlsx`, actualizando `D1`, las hojas `MERITUADOS` / `NO MERITUADOS` desde la fila 9 y `'Hoja 2'`, generando un archivo `.xlsx` válido para Excel y Google Sheets.



