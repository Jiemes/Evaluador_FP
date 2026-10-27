/**
 * app.js - LÓGICA DE LA APLICACIÓN WEB ESTÁTICA
 * Comisión Evaluadora Formación Profesional (Región 10 - Listados 2027)
 * 100% Client-Side para GitHub Pages (sin Streamlit, sin Backend)
 */

(function () {
  'use strict';

  // =========================================================================
  // 1. ESTADO GLOBAL DE LA APLICACIÓN
  // =========================================================================
  const estado = {
    distritoActivo: null,
    incluirResidencia: false,
    merituados: [],
    noMerituados: [],
    cursosPersonalizados: [],
    sigId: 1,
    pasoActual: 1,
    filtroBusqueda: '',
    filaBorrarInfo: null, // { tipo: 'mer'|'nomer', id: number }
    // Respuestas del aspirante en curso
    resp: crearRespVacia()
  };

  function crearRespVacia() {
    return {
      dni: '',
      apellido: '',
      nombres: '',
      dist1: '',
      pts_dist1: null,
      dist2: '',
      pts_dist2: null,
      dist3: '',
      pts_dist3: null,
      familia_prefijo: 'TODAS',
      cursos_seleccionados: [],
      // Habilitación
      anexo3_valido: true,
      dni_ok: true,
      titulo_ok: true,
      es_instructor: true,
      exp_laboral_3_de_5: false,
      titulo_afin_o_350hs: false,
      idoneidad_estrategica: false,
      dicto_2_veces: false,
      curso_en_certificado_fi: false,
      es_jubilado: false,
      cumple_hab: true,
      motivos_incumplidos: [],
      // No merituado
      motivo_no_meritudo: 'No Reune Requisitos',
      observaciones_no_meritudo: '',
      // Puntajes
      fi: 0,
      listado: 'COMPLEMENTARIO',
      formacion_opcion: 'Ninguno / Sin orientación afín',
      fe_sec_orient: 0,
      fe_sec_tecnico: 0,
      fe_superior: 0,
      fe_universitario: 0,
      cursos_docente: [],
      cap_docente: 0.0,
      cursos_especifica: [],
      cap_especifica: 0.0,
      desemp_anios: null,
      desemp_pts: 0,
      form_sup_fp: 0,
      antig_docencia_anios: 0,
      antig_docencia: 0.0,
      antig_fp_anios: 0,
      antig_fp: 0.0,
      calif1: 0.0,
      calif2: 0.0,
      art59: 10,
      puntaje: 10.0
    };
  }

  // =========================================================================
  // 2. INICIALIZACIÓN AL CARGAR LA PÁGINA
  // =========================================================================
  document.addEventListener('DOMContentLoaded', () => {
    if (!window.DATOS_APP) {
      alert('Error crítico: No se encontró window.DATOS_APP. Ejecute primero python generar_datos_web.py.');
      return;
    }

    // Inicializar cursos personalizados en memoria
    estado.cursosPersonalizados = [...(window.DATOS_APP.cursosIniciales2027 || [])];

    // Verificar si hay sesión activa en sessionStorage
    const sesionDistrito = sessionStorage.getItem('evaluador_distrito_actual');
    if (sesionDistrito) {
      cargarDistrito(sesionDistrito);
    } else {
      abrirModalInicio();
    }

    // Registrar escuchadores de eventos globales
    registrarEventos();
    actualizarVistaCompleta();
  });

  // =========================================================================
  // 3. PERSISTENCIA EN LOCALSTORAGE Y GESTIÓN DE DISTRITOS
  // =========================================================================
  function slugDistrito(nombre) {
    if (!nombre) return 'general';
    return nombre.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  }

  function claveLocalStorage(distrito) {
    return 'evaluador_distrito_' + slugDistrito(distrito);
  }

  function guardarEnLocalStorage() {
    if (!estado.distritoActivo) return;
    const datos = {
      distrito: estado.distritoActivo,
      incluirResidencia: estado.incluirResidencia,
      merituados: estado.merituados,
      noMerituados: estado.noMerituados,
      cursosPersonalizados: estado.cursosPersonalizados,
      sigId: estado.sigId,
      ultimaModificacion: new Date().toISOString()
    };
    try {
      localStorage.setItem(claveLocalStorage(estado.distritoActivo), JSON.stringify(datos));
    } catch (e) {
      console.warn('No se pudo guardar en localStorage:', e);
    }
  }

  function cargarDistrito(nombreDistrito) {
    estado.distritoActivo = nombreDistrito;
    sessionStorage.setItem('evaluador_distrito_actual', nombreDistrito);

    const clave = claveLocalStorage(nombreDistrito);
    const guardado = localStorage.getItem(clave);
    if (guardado) {
      try {
        const d = JSON.parse(guardado);
        estado.merituados = d.merituados || [];
        estado.noMerituados = d.noMerituados || [];
        estado.cursosPersonalizados = Array.from(new Set([...(d.cursosPersonalizados || []), ...(window.DATOS_APP.cursosIniciales2027 || [])]));
        estado.incluirResidencia = Boolean(d.incluirResidencia);
        estado.sigId = d.sigId || (estado.merituados.length + estado.noMerituados.length + 1);
      } catch (e) {
        console.error('Error al parsear datos guardados:', e);
      }
    } else {
      estado.merituados = [];
      estado.noMerituados = [];
      estado.sigId = 1;
    }

    // Si el aspirante actual no tiene dist1 seteado, sugerir el distrito activo
    if (!estado.resp.dist1) {
      estado.resp.dist1 = estado.distritoActivo;
    }

    document.getElementById('txt-distrito-activo').textContent = estado.distritoActivo;
    document.getElementById('chk-incluir-residencia').checked = estado.incluirResidencia;

    cerrarModalInicio();
    actualizarVistaCompleta();
  }

  function listarDistritosGuardados() {
    const lista = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith('evaluador_distrito_')) {
        try {
          const item = JSON.parse(localStorage.getItem(k));
          if (item && item.distrito) {
            lista.push(item);
          }
        } catch (e) {}
      }
    }
    return lista;
  }

  // =========================================================================
  // 4. MODAL DE INICIO / SELECCIÓN DE DISTRITO
  // =========================================================================
  let modalInicioObj = null;

  function abrirModalInicio() {
    const elModal = document.getElementById('modalInicioDistrito');
    if (!modalInicioObj) {
      modalInicioObj = new bootstrap.Modal(elModal, { backdrop: 'static', keyboard: false });
    }

    // Poblar Opción A: Select de distritos
    const selA = document.getElementById('sel-distrito-inicio');
    selA.innerHTML = '<option value="" disabled selected>-- Seleccione un Distrito Evaluador --</option>';

    // Separador Región 10 y Resto
    const optGroupR10 = document.createElement('optgroup');
    optGroupR10.label = '⭐ Distritos Región 10 (Prioritarios)';
    const optGroupOtros = document.createElement('optgroup');
    optGroupOtros.label = 'Distritos de la Provincia';

    window.DATOS_APP.distritos.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d;
      opt.textContent = d;
      const esR10 = window.DATOS_APP.distritosPrioritarios.some(cod => d.includes(cod));
      if (esR10) {
        optGroupR10.appendChild(opt);
      } else {
        optGroupOtros.appendChild(opt);
      }
    });

    selA.appendChild(optGroupR10);
    selA.appendChild(optGroupOtros);

    // Opción C: Listar distritos con guardado local
    const contC = document.getElementById('contenedor-distritos-guardados');
    contC.innerHTML = '';
    const guardados = listarDistritosGuardados();
    if (guardados.length === 0) {
      contC.innerHTML = '<span class="text-muted fst-italic fs-xs">No se detectaron tabulaciones guardadas previamente en este navegador.</span>';
    } else {
      guardados.forEach(item => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-sm btn-outline-secondary d-flex align-items-center gap-2 py-1 px-3';
        const total = (item.merituados?.length || 0) + (item.noMerituados?.length || 0);
        btn.innerHTML = `<i class="bi bi-folder-check text-success"></i> <strong>${item.distrito}</strong> <span class="badge bg-secondary">${total} reg.</span>`;
        btn.addEventListener('click', () => {
          cargarDistrito(item.distrito);
        });
        contC.appendChild(btn);
      });
    }

    modalInicioObj.show();
  }

  function cerrarModalInicio() {
    if (modalInicioObj) {
      modalInicioObj.hide();
    }
  }

  // =========================================================================
  // 5. CÁLCULO DE PUNTAJE REACTIVO (REGLA DISPO 13/2025)
  // =========================================================================
  function calcularPuntajeTotal(r, incluirRes = estado.incluirResidencia) {
    const fi = Number(r.fi || 0);
    const n = Number(r.fe_sec_orient || 0);
    const o = Number(r.fe_sec_tecnico || 0);
    const p = Number(r.fe_superior || 0);
    const q = Number(r.fe_universitario || 0);
    const capDoc = Number(r.cap_docente || 0);
    const capEsp = Number(r.cap_especifica || 0);
    const desemp = Number(r.desemp_pts || 0);
    const formSup = Number(r.form_sup_fp || 0);
    const antigDoc = Number(r.antig_docencia || 0);
    const antigFP = Number(r.antig_fp || 0);
    const c1 = Number(r.calif1 || 0);
    const c2 = Number(r.calif2 || 0);
    const art59 = Number(r.art59 || 0);

    const base = fi + n + o + p + q + capDoc + capEsp + desemp + formSup + antigDoc + antigFP + c1 + c2 + art59;
    
    // Residencia: 5 pts si algún distrito coincide con el domicilio
    const hayResidencia = [r.pts_dist1, r.pts_dist2, r.pts_dist3].some(v => Number(v) === 5);
    const ptsRes = (incluirRes && hayResidencia) ? 5 : 0;
    
    return Number((base + ptsRes).toFixed(2));
  }

  function obtenerCargoCurso(curso) {
    if (!curso) return 'instructor';
    const c = curso.toUpperCase();
    if (c.startsWith('00PR') || c.includes('PRECEPTOR')) return 'preceptor';
    if (c.startsWith('00PA') || c.includes('PAÑOL') || c.includes('PANOL')) return 'panolero';
    return 'instructor';
  }

  function evaluarHabilitacion(r) {
    const motivos = [];
    if (!r.anexo3_valido) motivos.push('No presenta Anexo 3');
    if (!r.dni_ok) motivos.push('No presenta DNI');
    if (!r.titulo_ok) motivos.push('No presenta Titulo Secundario');

    // Cargo instructor requiere inc 6
    const primerCurso = r.cursos_seleccionados[0] || '';
    const cargo = obtenerCargoCurso(primerCurso);
    if (cargo === 'instructor' && r.es_instructor) {
      const via61 = Boolean(r.exp_laboral_3_de_5 && r.titulo_afin_o_350hs);
      const via62 = Boolean(r.idoneidad_estrategica || r.dicto_2_veces || r.curso_en_certificado_fi);
      if (!via61 && !via62) {
        motivos.push('NO ACREDITA ANTECEDENTES PROFESIONALES ESPECÍFICOS');
      }
    }

    if (r.es_jubilado) {
      motivos.push('Aspirante Jubilado');
    }

    const cumple = motivos.length === 0;
    r.cumple_hab = cumple;
    r.motivos_incumplidos = motivos;
    if (!cumple) {
      r.motivo_no_meritudo = motivos.length === 1 ? motivos[0] : 'No Reune Requisitos';
    }
    return cumple;
  }

  // =========================================================================
  // 6. RENDERIZADO DEL WIZARD (PASOS 1 AL 18 Y 19)
  // =========================================================================
  const MAPA_PASOS = {
    1: { titulo: 'DNI del Aspirante', col: 'Columna C', ayuda: 'P1' },
    2: { titulo: 'Apellido del Aspirante', col: 'Columna D', ayuda: 'P2' },
    3: { titulo: 'Nombres del Aspirante', col: 'Columna E', ayuda: 'P3' },
    4: { titulo: 'Distrito 1 y Residencia', col: 'Columnas G y H', ayuda: 'P5' },
    5: { titulo: 'Distrito 2 y Residencia', col: 'Columnas I y J', ayuda: 'P6' },
    6: { titulo: 'Distrito 3 y Residencia', col: 'Columnas K y L', ayuda: 'P7' },
    7: { titulo: 'Especialidad / Cursos a Evaluar', col: 'Columna F', ayuda: 'P4' },
    8: { titulo: 'Filtro de Habilitación (Incisos 3 y 6)', col: 'Habilitación', ayuda: 'HABILITACION' },
    19: { titulo: 'NO MERITÚA – Motivo y Observaciones', col: 'Columnas J y K (No Merituados)', ayuda: 'HABILITACION' },
    9: { titulo: 'Certificado de Instructor (FI)', col: 'Columnas B y M', ayuda: 'P8' },
    10: { titulo: 'Formación Específica', col: 'Columnas N a Q', ayuda: 'P9' },
    11: { titulo: 'Capacitación Docente (Tope 3.00)', col: 'Columna R', ayuda: 'P10' },
    12: { titulo: 'Capacitación Específica (Tope 5.00)', col: 'Columna S', ayuda: 'P11' },
    13: { titulo: 'Desempeño Profesional en Actividad Laboral', col: 'Columnas T y U', ayuda: 'P12' },
    14: { titulo: 'Formación Superior en el Ámbito de FP', col: 'Columna V', ayuda: 'P13' },
    15: { titulo: 'Antigüedad en Docencia Oficial', col: 'Columna W', ayuda: 'P14' },
    16: { titulo: 'Antigüedad en Ámbito de FP Oficial', col: 'Columna X', ayuda: 'P15' },
    17: { titulo: 'Calificaciones Últimos 2 Años en FP', col: 'Columnas Y y Z', ayuda: 'P16' },
    18: { titulo: 'Art. 59 Estatuto Docente y Cierre', col: 'Columnas AA y AB', ayuda: 'P17' }
  };

  function renderizarPasoActual() {
    const paso = estado.pasoActual;
    const config = MAPA_PASOS[paso] || { titulo: 'Evaluación', col: '', ayuda: 'P1' };

    document.getElementById('badge-paso').textContent = paso === 19 ? 'No Meritúa' : `Paso ${paso} de 18`;
    document.getElementById('titulo-paso').textContent = config.titulo;
    document.getElementById('badge-columna').textContent = config.col;

    // Barra de progreso
    const pct = paso === 19 ? 100 : Math.min(100, Math.round((paso / 18) * 100));
    const barra = document.getElementById('barra-progreso-paso');
    barra.style.width = pct + '%';
    barra.className = paso === 19 ? 'progress-bar bg-danger' : 'progress-bar bg-warning progress-bar-striped progress-bar-animated';

    const cont = document.getElementById('contenedor-paso-dinamico');
    cont.innerHTML = '';

    const btnAnt = document.getElementById('btn-paso-anterior');
    const btnSig = document.getElementById('btn-paso-siguiente');
    const contAcciones = document.getElementById('contenedor-acciones-finales');

    btnAnt.disabled = (paso === 1);

    if (paso === 18 || paso === 19) {
      btnSig.classList.add('d-none');
      contAcciones.classList.remove('d-none');
    } else {
      btnSig.classList.remove('d-none');
      contAcciones.classList.add('d-none');
    }

    // Despacho de cada paso
    switch (paso) {
      case 1: renderPaso1(cont); break;
      case 2: renderPaso2(cont); break;
      case 3: renderPaso3(cont); break;
      case 4: renderPaso4(cont); break;
      case 5: renderPaso5(cont); break;
      case 6: renderPaso6(cont); break;
      case 7: renderPaso7(cont); break;
      case 8: renderPaso8(cont); break;
      case 19: renderPaso19(cont); break;
      case 9: renderPaso9(cont); break;
      case 10: renderPaso10(cont); break;
      case 11: renderPaso11(cont); break;
      case 12: renderPaso12(cont); break;
      case 13: renderPaso13(cont); break;
      case 14: renderPaso14(cont); break;
      case 15: renderPaso15(cont); break;
      case 16: renderPaso16(cont); break;
      case 17: renderPaso17(cont); break;
      case 18: renderPaso18(cont); break;
    }

    // Actualizar ayuda lateral
    actualizarAyudaLateral(config.ayuda);
    actualizarFilaEnVivo();
  }

  // --- RENDERS ESPECÍFICOS DE PASOS ---

  function renderPaso1(cont) {
    cont.innerHTML = `
      <div class="mb-3">
        <label class="form-label fw-bold">Número de DNI (sin puntos ni espacios) *</label>
        <input type="text" id="inp-dni" class="form-control form-control-lg font-monospace" placeholder="Ej: 28456789" value="${estado.resp.dni}">
        <div class="form-text">Debe presentarse DNI vigente frente y dorso. Ingrese solo los números.</div>
      </div>
    `;
    const inp = cont.querySelector('#inp-dni');
    inp.focus();
    inp.addEventListener('input', (e) => {
      estado.resp.dni = e.target.value.replace(/\D/g, '');
      e.target.value = estado.resp.dni;
      actualizarFilaEnVivo();
    });
  }

  function renderPaso2(cont) {
    cont.innerHTML = `
      <div class="mb-3">
        <label class="form-label fw-bold">Apellido del Aspirante (tal como figura en el DNI) *</label>
        <input type="text" id="inp-apellido" class="form-control form-control-lg text-uppercase" placeholder="Ej: GONZALEZ" value="${estado.resp.apellido}">
        <div class="form-text">Se normaliza automáticamente a MAYÚSCULAS sin abreviaturas.</div>
      </div>
    `;
    const inp = cont.querySelector('#inp-apellido');
    inp.focus();
    inp.addEventListener('input', (e) => {
      estado.resp.apellido = e.target.value.toUpperCase();
      actualizarFilaEnVivo();
    });
  }

  function renderPaso3(cont) {
    cont.innerHTML = `
      <div class="mb-3">
        <label class="form-label fw-bold">Nombres del Aspirante (completos según DNI) *</label>
        <input type="text" id="inp-nombres" class="form-control form-control-lg text-uppercase" placeholder="Ej: JUAN CARLOS" value="${estado.resp.nombres}">
        <div class="form-text">Cargue todos los nombres de pila completos.</div>
      </div>
    `;
    const inp = cont.querySelector('#inp-nombres');
    inp.focus();
    inp.addEventListener('input', (e) => {
      estado.resp.nombres = e.target.value.toUpperCase();
      actualizarFilaEnVivo();
    });
  }

  function renderPasoDistrito(cont, num) {
    const dKey = `dist${num}`;
    const pKey = `pts_dist${num}`;
    const valD = estado.resp[dKey] || '';
    const esRes = estado.resp[pKey] === 5;

    let options = `<option value="">-- Sin Distrito ${num} --</option>`;
    window.DATOS_APP.distritos.forEach(d => {
      options += `<option value="${d}" ${d === valD ? 'selected' : ''}>${d}</option>`;
    });

    cont.innerHTML = `
      <div class="mb-3">
        <label class="form-label fw-bold">Distrito Declarado ${num} ${num === 1 ? '*' : '(Opcional)'}</label>
        <select id="sel-dist" class="form-select mb-3">${options}</select>
        
        <div class="card p-3 bg-light border">
          <div class="form-check form-switch">
            <input class="form-check-input" type="checkbox" id="chk-res" ${esRes ? 'checked' : ''} ${!valD ? 'disabled' : ''}>
            <label class="form-check-label fw-bold" for="chk-res">
              ¿El domicilio del DNI vigente coincide con este Distrito ${num}? (+5 pts)
            </label>
          </div>
          <div class="form-text mt-1 text-muted">
            Solo un único distrito puede recibir los 5 puntos de residencia. Si marca este, se desmarcarán los demás.
          </div>
        </div>
      </div>
    `;

    const sel = cont.querySelector('#sel-dist');
    const chk = cont.querySelector('#chk-res');

    sel.addEventListener('change', (e) => {
      estado.resp[dKey] = e.target.value;
      chk.disabled = !e.target.value;
      if (!e.target.value) {
        estado.resp[pKey] = null;
        chk.checked = false;
      }
      actualizarFilaEnVivo();
    });

    chk.addEventListener('change', (e) => {
      if (e.target.checked) {
        estado.resp.pts_dist1 = (num === 1) ? 5 : 0;
        estado.resp.pts_dist2 = (num === 2) ? 5 : 0;
        estado.resp.pts_dist3 = (num === 3) ? 5 : 0;
      } else {
        estado.resp[pKey] = 0;
      }
      actualizarFilaEnVivo();
    });
  }

  function renderPaso4(cont) { renderPasoDistrito(cont, 1); }
  function renderPaso5(cont) { renderPasoDistrito(cont, 2); }
  function renderPaso6(cont) { renderPasoDistrito(cont, 3); }

  function renderPaso7(cont) {
    const familias = window.DATOS_APP.familias;
    const prefijoActual = estado.resp.familia_prefijo || 'TODAS';
    const seleccionados = new Set(estado.resp.cursos_seleccionados || []);

    // Opciones de familia
    let famOptions = `<option value="TODAS" ${prefijoActual === 'TODAS' ? 'selected' : ''}>-- TODAS LAS FAMILIAS PROFESIONALES --</option>`;
    for (const [k, v] of Object.entries(familias)) {
      famOptions += `<option value="${k}" ${prefijoActual === k ? 'selected' : ''}>${v}</option>`;
    }

    // Filtrar cursos según familia
    const todosCursos = Array.from(new Set([...window.DATOS_APP.cursos, ...estado.cursosPersonalizados])).sort();
    const cursosFiltrados = todosCursos.filter(c => {
      if (prefijoActual === 'TODAS') return true;
      return c.toUpperCase().startsWith(prefijoActual.toUpperCase());
    });

    let checkboxesHtml = '';
    cursosFiltrados.forEach((c, idx) => {
      const isChecked = seleccionados.has(c);
      checkboxesHtml += `
        <label class="especialidad-item">
          <input type="checkbox" class="chk-curso" data-curso="${c}" ${isChecked ? 'checked' : ''}>
          <span>${c}</span>
        </label>
      `;
    });

    cont.innerHTML = `
      <div class="mb-2">
        <label class="form-label fw-bold">1. Filtrar por Familia Profesional (Catálogo 2027)</label>
        <select id="sel-familia" class="form-select form-select-sm mb-2">${famOptions}</select>
      </div>

      <div class="d-flex align-items-center justify-content-between mb-1">
        <label class="form-label fw-bold mb-0">2. Especialidades a inscribir (seleccione una o varias) *</label>
        <button id="btn-abrir-nuevo-curso" type="button" class="btn btn-outline-primary btn-sm py-0 px-2 fs-xs">
          <i class="bi bi-plus-circle me-1"></i> Nueva Especialidad
        </button>
      </div>

      <div class="especialidades-grid mb-2">
        ${checkboxesHtml}
      </div>

      <div class="d-flex align-items-center justify-content-between alert alert-info py-1 px-2 mb-0 fs-xs">
        <span>Cursos seleccionados para este legajo: <strong id="lbl-cant-cursos">${seleccionados.size}</strong></span>
        <button id="btn-limpiar-cursos" class="btn btn-link btn-sm py-0 text-decoration-none">Deseleccionar todos</button>
      </div>
    `;

    const selFam = cont.querySelector('#sel-familia');
    selFam.addEventListener('change', (e) => {
      estado.resp.familia_prefijo = e.target.value;
      renderPaso7(cont);
    });

    cont.querySelectorAll('.chk-curso').forEach(chk => {
      chk.addEventListener('change', (e) => {
        const c = e.target.dataset.curso;
        if (e.target.checked) {
          if (!estado.resp.cursos_seleccionados.includes(c)) {
            estado.resp.cursos_seleccionados.push(c);
          }
        } else {
          estado.resp.cursos_seleccionados = estado.resp.cursos_seleccionados.filter(x => x !== c);
        }
        cont.querySelector('#lbl-cant-cursos').textContent = estado.resp.cursos_seleccionados.length;
        actualizarFilaEnVivo();
        // Chequear ayuda de perfil
        actualizarAyudaLateral('P4');
      });
    });

    cont.querySelector('#btn-limpiar-cursos').addEventListener('click', () => {
      estado.resp.cursos_seleccionados = [];
      renderPaso7(cont);
      actualizarFilaEnVivo();
    });

    cont.querySelector('#btn-abrir-nuevo-curso').addEventListener('click', () => {
      abrirModalNuevoCurso();
    });
  }

  function renderPaso8(cont) {
    const r = estado.resp;
    const primerCurso = r.cursos_seleccionados[0] || '';
    const cargo = obtenerCargoCurso(primerCurso);

    let inc6Html = '';
    if (cargo === 'instructor') {
      inc6Html = `
        <div class="card p-3 mb-3 border-info border-opacity-50 bg-light">
          <h6 class="fw-bold text-primary mb-2"><i class="bi bi-person-workspace me-1"></i> Requisitos Específicos de Instructor (Inciso 6)</h6>
          
          <div class="mb-2">
            <span class="fw-semibold text-dark fs-xs d-block mb-1">Vía 6.1 (Ambas condiciones obligatorias):</span>
            <div class="form-check fs-xs">
              <input class="form-check-input" type="checkbox" id="chk-exp" ${r.exp_laboral_3_de_5 ? 'checked' : ''}>
              <label class="form-check-label" for="chk-exp">6.1.1: Acredita mínimo 3 años de experiencia laboral no docente en la especialidad (últimos 5 años).</label>
            </div>
            <div class="form-check fs-xs">
              <input class="form-check-input" type="checkbox" id="chk-tit-esp" ${r.titulo_afin_o_350hs ? 'checked' : ''}>
              <label class="form-check-label" for="chk-tit-esp">6.1.2: Posee título afín o certificaciones de FP de 350 horas reloj o más.</label>
            </div>
          </div>

          <div class="mb-1">
            <span class="fw-semibold text-dark fs-xs d-block mb-1">Vía 6.2 (Reemplaza a la 6.1 con que cumpla una sola):</span>
            <div class="form-check fs-xs">
              <input class="form-check-input" type="checkbox" id="chk-idio" ${r.idoneidad_estrategica ? 'checked' : ''}>
              <label class="form-check-label" for="chk-idio">6.2.1: Posee Idoneidad Profesional Estratégica (Dispo 1/23 / Anexo III Orientación).</label>
            </div>
            <div class="form-check fs-xs">
              <input class="form-check-input" type="checkbox" id="chk-dicto" ${r.dicto_2_veces ? 'checked' : ''}>
              <label class="form-check-label" for="chk-dicto">6.2.2: Dictó el curso 2 veces completo en los últimos 5 años en FP oficial (con constancia y nota).</label>
            </div>
            <div class="form-check fs-xs">
              <input class="form-check-input" type="checkbox" id="chk-cfi" ${r.curso_en_certificado_fi ? 'checked' : ''}>
              <label class="form-check-label" for="chk-cfi">6.2.3: El curso está declarado en su Certificado de FI o es diseño reemplazado.</label>
            </div>
          </div>
        </div>
      `;
    }

    cont.innerHTML = `
      <div class="card p-3 mb-3 border-secondary border-opacity-50">
        <h6 class="fw-bold mb-2 text-dark"><i class="bi bi-shield-check text-success me-1"></i> Requisitos Comunes Obligatorios (Inciso 3)</h6>
        <div class="form-check mb-1 fs-xs">
          <input class="form-check-input" type="checkbox" id="chk-anexo3" ${r.anexo3_valido ? 'checked' : ''}>
          <label class="form-check-label" for="chk-anexo3">Presenta Anexo III oficial y válido (Inc. 2.1, 2.2, 11.1).</label>
        </div>
        <div class="form-check mb-1 fs-xs">
          <input class="form-check-input" type="checkbox" id="chk-dni" ${r.dni_ok ? 'checked' : ''}>
          <label class="form-check-label" for="chk-dni">Presenta DNI legible frente y reverso vigente (Inc. 3.2).</label>
        </div>
        <div class="form-check mb-1 fs-xs">
          <input class="form-check-input" type="checkbox" id="chk-tit" ${r.titulo_ok ? 'checked' : ''}>
          <label class="form-check-label" for="chk-tit">Presenta Título secundario, superior o universitario registrado.</label>
        </div>
      </div>

      ${inc6Html}

      <div class="card p-2 bg-light border-warning border-opacity-50">
        <div class="form-check fs-xs">
          <input class="form-check-input" type="checkbox" id="chk-jubilado" ${r.es_jubilado ? 'checked' : ''}>
          <label class="form-check-label text-danger fw-bold" for="chk-jubilado">El aspirante es JUBILADO (Inhabilita para merituar según Estatuto).</label>
        </div>
      </div>
    `;

    const vincular = (id, prop) => {
      const el = cont.querySelector('#' + id);
      if (el) {
        el.addEventListener('change', (e) => {
          r[prop] = e.target.checked;
          evaluarHabilitacion(r);
        });
      }
    };

    vincular('chk-anexo3', 'anexo3_valido');
    vincular('chk-dni', 'dni_ok');
    vincular('chk-tit', 'titulo_ok');
    vincular('chk-exp', 'exp_laboral_3_de_5');
    vincular('chk-tit-esp', 'titulo_afin_o_350hs');
    vincular('chk-idio', 'idoneidad_estrategica');
    vincular('chk-dicto', 'dicto_2_veces');
    vincular('chk-cfi', 'curso_en_certificado_fi');
    vincular('chk-jubilado', 'es_jubilado');
  }

  function renderPaso19(cont) {
    const motivos = window.DATOS_APP.motivosNoMerituado;
    let motOptions = '';
    motivos.forEach(m => {
      motOptions += `<option value="${m}" ${m === estado.resp.motivo_no_meritudo ? 'selected' : ''}>${m}</option>`;
    });

    cont.innerHTML = `
      <div class="alert alert-danger py-2 px-3 mb-3">
        <i class="bi bi-exclamation-triangle-fill me-1"></i> El aspirante <strong>NO CUMPLE</strong> con los requisitos reglamentarios y se registrará en la planilla de <strong>NO MERITUADOS</strong>.
      </div>

      <div class="mb-3">
        <label class="form-label fw-bold">Motivo Oficial de No Meritudo (Columna J) *</label>
        <select id="sel-motivo" class="form-select">${motOptions}</select>
      </div>

      <div class="mb-3">
        <label class="form-label fw-bold">Observaciones de la Comisión Evaluadora (Columna K) ${estado.resp.motivo_no_meritudo === 'Otros' ? '<span class="text-danger">* (Obligatorio en Otros)</span>' : ''}</label>
        <textarea id="txt-obs" class="form-control" rows="3" placeholder="Detalle las razones o probanzas faltantes...">${estado.resp.observaciones_no_meritudo || ''}</textarea>
      </div>
    `;

    cont.querySelector('#sel-motivo').addEventListener('change', (e) => {
      estado.resp.motivo_no_meritudo = e.target.value;
      renderPaso19(cont);
    });

    cont.querySelector('#txt-obs').addEventListener('input', (e) => {
      estado.resp.observaciones_no_meritudo = e.target.value;
    });
  }

  function renderPaso9(cont) {
    const esFI = estado.resp.fi === 25;
    cont.innerHTML = `
      <div class="card p-3 border-primary mb-3">
        <label class="form-label fw-bold mb-2">¿Posee Certificado de Instructor de Formación Profesional (FI) registrado? *</label>
        
        <div class="form-check mb-2">
          <input class="form-check-input" type="radio" name="rad-fi" id="rad-fi-si" value="25" ${esFI ? 'checked' : ''}>
          <label class="form-check-label fw-bold text-success" for="rad-fi-si">
            SÍ POSEE CERTIFICADO DE FI (25 pts) ➔ LISTADO PRINCIPAL
          </label>
        </div>

        <div class="form-check">
          <input class="form-check-input" type="radio" name="rad-fi" id="rad-fi-no" value="0" ${!esFI ? 'checked' : ''}>
          <label class="form-check-label text-muted" for="rad-fi-no">
            NO POSEE CERTIFICADO DE FI (0 pts) ➔ LISTADO COMPLEMENTARIO
          </label>
        </div>
      </div>
    `;

    cont.querySelectorAll('input[name="rad-fi"]').forEach(r => {
      r.addEventListener('change', (e) => {
        estado.resp.fi = Number(e.target.value);
        estado.resp.listado = estado.resp.fi === 25 ? 'PRINCIPAL' : 'COMPLEMENTARIO';
        actualizarFilaEnVivo();
      });
    });
  }

  function renderPaso10(cont) {
    const primerCurso = estado.resp.cursos_seleccionados[0] || '';
    const cargo = obtenerCargoCurso(primerCurso);
    const opciones = cargo === 'panolero' ? window.DATOS_APP.opcionesFormacionPanol : window.DATOS_APP.opcionesFormacion;
    const optActual = estado.resp.formacion_opcion || 'Ninguno / Sin orientación afín';

    let radiosHtml = '';
    for (const [nombre, pts] of Object.entries(opciones)) {
      const isChecked = nombre === optActual;
      const ptsTxt = `N=${pts.N}, O=${pts.O}, P=${pts.P}, Q=${pts.Q}`;
      radiosHtml += `
        <label class="list-group-item d-flex align-items-center justify-content-between py-2 cursor-pointer">
          <div class="form-check mb-0">
            <input class="form-check-input" type="radio" name="rad-form" id="rad-${ptsTxt}" value="${nombre}" ${isChecked ? 'checked' : ''}>
            <span class="form-check-label fw-semibold">${nombre}</span>
          </div>
          <span class="badge bg-primary rounded-pill">${Math.max(pts.N, pts.O, pts.P, pts.Q)} pts</span>
        </label>
      `;
    }

    cont.innerHTML = `
      <div class="mb-2">
        <label class="form-label fw-bold mb-1">Título de mayor nivel acreditado afín a la especialidad (Excluyente) *</label>
        <div class="list-group shadow-xs">
          ${radiosHtml}
        </div>
      </div>
    `;

    cont.querySelectorAll('input[name="rad-form"]').forEach(r => {
      r.addEventListener('change', (e) => {
        const nom = e.target.value;
        estado.resp.formacion_opcion = nom;
        const vals = opciones[nom] || { N: 0, O: 0, P: 0, Q: 0 };
        estado.resp.fe_sec_orient = vals.N;
        estado.resp.fe_sec_tecnico = vals.O;
        estado.resp.fe_superior = vals.P;
        estado.resp.fe_universitario = vals.Q;
        actualizarFilaEnVivo();
      });
    });
  }

  function renderCalculadoraHoras(cont, tipo) {
    const isDoc = tipo === 'docente';
    const lista = isDoc ? estado.resp.cursos_docente : estado.resp.cursos_especifica;
    const tope = isDoc ? window.DATOS_APP.topes.capDocente : window.DATOS_APP.topes.capEspecifica;
    const tabla = isDoc ? window.DATOS_APP.tablasPuntaje.capDocente : window.DATOS_APP.tablasPuntaje.capEspecifica;
    const propPuntos = isDoc ? 'cap_docente' : 'cap_especifica';

    function calcularPuntosCurso(hs) {
      if (hs < 5) return 0.0;
      for (const [desde, hasta, pts] of tabla) {
        if (hs >= desde && (hasta === null || hs <= hasta)) {
          return pts;
        }
      }
      return 0.0;
    }

    function recalcularTotal() {
      let bruto = 0.0;
      lista.forEach(c => bruto += c.puntos);
      const total = Math.min(bruto, tope);
      estado.resp[propPuntos] = Number(total.toFixed(2));
      actualizarFilaEnVivo();
      render();
    }

    function render() {
      let itemsHtml = '';
      if (lista.length === 0) {
        itemsHtml = '<div class="text-muted fst-italic fs-xs py-2 text-center">No se han ingresado cursos de capacitación.</div>';
      } else {
        lista.forEach((c, idx) => {
          itemsHtml += `
            <div class="calc-curso-item">
              <span><strong>Curso ${idx + 1}:</strong> ${c.horas} hs (${c.tipo}) ➔ <span class="badge bg-secondary">${c.puntos.toFixed(2)} pts</span></span>
              <button type="button" class="btn btn-outline-danger btn-sm py-0 px-2 fs-xs btn-borrar-curso" data-idx="${idx}">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          `;
        });
      }

      const totalActual = estado.resp[propPuntos];
      const topeAlcanzado = totalActual >= tope;

      cont.innerHTML = `
        <div class="card p-3 bg-light border mb-3">
          <label class="form-label fw-bold mb-2">Calculadora de Cursos de ${isDoc ? 'Capacitación Docente' : 'Capacitación Específica'}</label>
          
          <div class="row g-2 mb-2 align-items-end">
            <div class="col-4">
              <label class="form-label fs-xs mb-1">Carga Horaria</label>
              <input type="number" id="inp-hs" class="form-control form-control-sm" placeholder="Ej: 30" min="1">
            </div>
            <div class="col-5">
              <label class="form-label fs-xs mb-1">Tipo de Horas</label>
              <select id="sel-tipo-hs" class="form-select form-select-sm">
                <option value="reloj">Horas Reloj</option>
                <option value="catedra">Horas Cátedra (× 2/3)</option>
              </select>
            </div>
            <div class="col-3">
              <button type="button" id="btn-sumar-curso" class="btn btn-primary btn-sm w-100 fw-bold">
                <i class="bi bi-plus-lg"></i> Sumar
              </button>
            </div>
          </div>

          <div class="border rounded p-2 bg-white mb-2" style="max-height: 140px; overflow-y: auto;">
            ${itemsHtml}
          </div>

          <div class="d-flex align-items-center justify-content-between p-2 rounded ${topeAlcanzado ? 'bg-warning bg-opacity-25 border border-warning' : 'bg-primary bg-opacity-10'}">
            <span class="fw-bold fs-xs">Total ${isDoc ? 'Cap. Docente (Col. R)' : 'Cap. Específica (Col. S)'}:</span>
            <span class="fs-6 fw-bold ${topeAlcanzado ? 'text-warning-emphasis' : 'text-primary'}">
              ${totalActual.toFixed(2)} / ${tope.toFixed(2)} pts ${topeAlcanzado ? '(Tope máximo alcanzado)' : ''}
            </span>
          </div>
        </div>
      `;

      cont.querySelector('#btn-sumar-curso').addEventListener('click', () => {
        const inpHs = cont.querySelector('#inp-hs');
        const selTipo = cont.querySelector('#sel-tipo-hs');
        const hsRaw = Number(inpHs.value);
        if (!hsRaw || hsRaw <= 0) return;

        const tipo = selTipo.value;
        const hsReloj = tipo === 'catedra' ? Math.floor((hsRaw * 2) / 3) : Math.floor(hsRaw);
        const puntos = calcularPuntosCurso(hsReloj);

        lista.push({ horas: hsRaw, tipo: tipo === 'catedra' ? 'cátedra' : 'reloj', puntos: puntos });
        recalcularTotal();
      });

      cont.querySelectorAll('.btn-borrar-curso').forEach(b => {
        b.addEventListener('click', (e) => {
          const idx = Number(e.currentTarget.dataset.idx);
          lista.splice(idx, 1);
          recalcularTotal();
        });
      });
    }

    render();
  }

  function renderPaso11(cont) { renderCalculadoraHoras(cont, 'docente'); }
  function renderPaso12(cont) { renderCalculadoraHoras(cont, 'especifica'); }

  function renderPaso13(cont) {
    const aniosActual = estado.resp.desemp_anios !== null ? estado.resp.desemp_anios : '';
    const ptsActual = estado.resp.desemp_pts || 0;

    cont.innerHTML = `
      <div class="card p-3 border mb-3">
        <label class="form-label fw-bold mb-1">Años de Desempeño Profesional en la Actividad Laboral *</label>
        <p class="text-muted fs-xs mb-3">Se computan años de experiencia laboral comprobable (0 a 35 años). El puntaje se calcula automáticamente en la Columna U.</p>
        
        <div class="row g-2 align-items-center mb-3">
          <div class="col-6">
            <input type="number" id="inp-desemp" class="form-control form-control-lg font-monospace" min="0" max="35" placeholder="0" value="${aniosActual}">
          </div>
          <div class="col-6">
            <div class="badge bg-primary fs-6 p-2 w-100 text-center">
              Columna U: <strong id="lbl-pts-desemp">${ptsActual}</strong> pts
            </div>
          </div>
        </div>

        <div class="alert alert-light border fs-xs mb-0">
          <strong>Escala Disposición 13/2025:</strong> 0 a 2 años = 0 pts · 3 a 4 años = 5 pts · 5 a 9 años = 6 pts · 10 o más años = 8 pts.
        </div>
      </div>
    `;

    const inp = cont.querySelector('#inp-desemp');
    inp.addEventListener('input', (e) => {
      const v = e.target.value === '' ? null : Math.min(35, Math.max(0, parseInt(e.target.value, 10) || 0));
      estado.resp.desemp_anios = v;
      if (v === null || v <= 2) estado.resp.desemp_pts = 0;
      else if (v <= 4) estado.resp.desemp_pts = 5;
      else if (v <= 9) estado.resp.desemp_pts = 6;
      else estado.resp.desemp_pts = 8;

      cont.querySelector('#lbl-pts-desemp').textContent = estado.resp.desemp_pts;
      actualizarFilaEnVivo();
    });
  }

  function renderPaso14(cont) {
    const tiene = estado.resp.form_sup_fp === 7;
    cont.innerHTML = `
      <div class="card p-3 border mb-3">
        <label class="form-label fw-bold mb-2">¿Acredita Formación Superior en el Ámbito de la FP? *</label>
        <p class="text-muted fs-xs mb-3">Tecnicatura Universitaria o Superior en Educación Profesional / Formación Profesional con Validez Nacional (7 pts).</p>

        <div class="form-check mb-2">
          <input class="form-check-input" type="radio" name="rad-fs" id="rad-fs-si" value="7" ${tiene ? 'checked' : ''}>
          <label class="form-check-label fw-bold text-success" for="rad-fs-si">SÍ ACREDITA (7 pts en Columna V)</label>
        </div>

        <div class="form-check">
          <input class="form-check-input" type="radio" name="rad-fs" id="rad-fs-no" value="0" ${!tiene ? 'checked' : ''}>
          <label class="form-check-label text-muted" for="rad-fs-no">NO ACREDITA (0 pts en Columna V)</label>
        </div>
      </div>
    `;

    cont.querySelectorAll('input[name="rad-fs"]').forEach(r => {
      r.addEventListener('change', (e) => {
        estado.resp.form_sup_fp = Number(e.target.value);
        actualizarFilaEnVivo();
      });
    });
  }

  function renderPaso15(cont) {
    const anios = estado.resp.antig_docencia_anios || 0;
    let opts = '';
    for (let i = 0; i <= 10; i++) {
      const lbl = i === 10 ? '10 o más años (Tope 2.50 pts)' : `${i} año${i === 1 ? '' : 's'} (${(i * 0.25).toFixed(2)} pts)`;
      opts += `<option value="${i}" ${i === anios ? 'selected' : ''}>${lbl}</option>`;
    }

    cont.innerHTML = `
      <div class="card p-3 border mb-3">
        <label class="form-label fw-bold mb-1">Años Lectivos en Docencia Oficial (Ítem 10.7) *</label>
        <p class="text-muted fs-xs mb-3">0.25 puntos por cada año lectivo acreditado con Certificación de Servicios oficial. Tope máximo: 2.50 pts.</p>

        <select id="sel-ant-doc" class="form-select form-select-lg mb-3 font-monospace">${opts}</select>

        <div class="alert alert-info py-2 px-3 fs-xs mb-0">
          <i class="bi bi-info-circle me-1"></i> Se impiden decimales no estándar. Puntaje Columna W: <strong>${(Math.min(anios, 10) * 0.25).toFixed(2)} pts</strong>.
        </div>
      </div>
    `;

    cont.querySelector('#sel-ant-doc').addEventListener('change', (e) => {
      const a = parseInt(e.target.value, 10);
      estado.resp.antig_docencia_anios = a;
      estado.resp.antig_docencia = Number((Math.min(a, 10) * 0.25).toFixed(2));
      actualizarFilaEnVivo();
    });
  }

  function renderPaso16(cont) {
    const anios = estado.resp.antig_fp_anios || 0;
    let opts = '';
    for (let i = 0; i <= 10; i++) {
      const lbl = i === 10 ? '10 o más años (Tope 5.00 pts)' : `${i} año${i === 1 ? '' : 's'} (${(i * 0.50).toFixed(2)} pts)`;
      opts += `<option value="${i}" ${i === anios ? 'selected' : ''}>${lbl}</option>`;
    }

    cont.innerHTML = `
      <div class="card p-3 border mb-3">
        <label class="form-label fw-bold mb-1">Años Lectivos en Ámbito de FP Oficial (Ítem 10.8) *</label>
        <p class="text-muted fs-xs mb-3">0.50 puntos por cada año lectivo en Centros de Formación Profesional oficiales. Tope máximo: 5.00 pts.</p>

        <select id="sel-ant-fp" class="form-select form-select-lg mb-3 font-monospace">${opts}</select>

        <div class="alert alert-info py-2 px-3 fs-xs mb-0">
          <i class="bi bi-info-circle me-1"></i> Puntaje estricto en Columna X: <strong>${(Math.min(anios, 10) * 0.50).toFixed(2)} pts</strong>.
        </div>
      </div>
    `;

    cont.querySelector('#sel-ant-fp').addEventListener('change', (e) => {
      const a = parseInt(e.target.value, 10);
      estado.resp.antig_fp_anios = a;
      estado.resp.antig_fp = Number((Math.min(a, 10) * 0.50).toFixed(2));
      actualizarFilaEnVivo();
    });
  }

  function renderPaso17(cont) {
    const cOpts = window.DATOS_APP.opcionesCalificacion;
    const c1 = estado.resp.calif1 || 0.0;
    const c2 = estado.resp.calif2 || 0.0;

    let optHtml1 = '', optHtml2 = '';
    for (const [txt, val] of Object.entries(cOpts)) {
      optHtml1 += `<option value="${val}" ${val === c1 ? 'selected' : ''}>${txt} (${val.toFixed(2)} pts)</option>`;
      optHtml2 += `<option value="${val}" ${val === c2 ? 'selected' : ''}>${txt} (${val.toFixed(2)} pts)</option>`;
    }

    cont.innerHTML = `
      <div class="card p-3 border mb-3">
        <label class="form-label fw-bold mb-1">Calificaciones en FP de los Últimos 2 Años (Ítem 10.9) *</label>
        <p class="text-muted fs-xs mb-3">Acreditadas con SET 4 o constancia oficial. Se carga el puntaje correspondiente a cada año (máx. 1.00 pt por año).</p>

        <div class="row g-3 mb-2">
          <div class="col-md-6 col-12">
            <label class="form-label fs-xs fw-bold">Año 1 (Columna Y)</label>
            <select id="sel-calif1" class="form-select form-select-sm">${optHtml1}</select>
          </div>
          <div class="col-md-6 col-12">
            <label class="form-label fs-xs fw-bold">Año 2 (Columna Z)</label>
            <select id="sel-calif2" class="form-select form-select-sm">${optHtml2}</select>
          </div>
        </div>
      </div>
    `;

    cont.querySelector('#sel-calif1').addEventListener('change', (e) => {
      estado.resp.calif1 = parseFloat(e.target.value);
      actualizarFilaEnVivo();
    });

    cont.querySelector('#sel-calif2').addEventListener('change', (e) => {
      estado.resp.calif2 = parseFloat(e.target.value);
      actualizarFilaEnVivo();
    });
  }

  function renderPaso18(cont) {
    const noTieneTit = estado.resp.art59 === 10;
    const puntajeBase = calcularPuntajeTotal(estado.resp, false);
    const puntajeConRes = calcularPuntajeTotal(estado.resp, true);

    cont.innerHTML = `
      <div class="card p-3 border mb-3">
        <label class="form-label fw-bold mb-2">Art. 59 Estatuto Docente (Horas y Cargos Titulares) *</label>

        <div class="form-check mb-2">
          <input class="form-check-input" type="radio" name="rad-art59" id="rad-art-si" value="10" ${noTieneTit ? 'checked' : ''}>
          <label class="form-check-label fw-bold text-success" for="rad-art-si">
            NO POSEE CARGOS NI HORAS TITULARES (10 pts en Columna AA)
          </label>
        </div>

        <div class="form-check mb-3">
          <input class="form-check-input" type="radio" name="rad-art59" id="rad-art-no" value="0" ${!noTieneTit ? 'checked' : ''}>
          <label class="form-check-label text-muted" for="rad-art-no">
            SÍ POSEE CARGOS U HORAS TITULARES (0 pts en Columna AA)
          </label>
        </div>

        <div class="alert alert-success border-success p-3 rounded text-center">
          <h5 class="fw-bold text-success mb-1">¡Evaluación de Antecedentes Finalizada!</h5>
          <div class="fs-6 mb-2">
            Puntaje Base (Col. AB): <strong class="fs-5">${puntajeBase.toFixed(2)} pts</strong>
            ${estado.resp.pts_dist1 === 5 || estado.resp.pts_dist2 === 5 || estado.resp.pts_dist3 === 5 ? ` | Con Residencia (+5): <strong>${puntajeConRes.toFixed(2)} pts</strong>` : ''}
          </div>
          <p class="fs-xs text-muted mb-0">Seleccione a continuación si desea leer el veredicto en Zoom, evaluar otro curso para este aspirante o dar de alta uno nuevo.</p>
        </div>
      </div>
    `;

    cont.querySelectorAll('input[name="rad-art59"]').forEach(r => {
      r.addEventListener('change', (e) => {
        estado.resp.art59 = Number(e.target.value);
        actualizarFilaEnVivo();
      });
    });
  }

  // =========================================================================
  // 7. SINCRONIZACIÓN DE AYUDA NORMATIVA Y PERFILES ANEXO 2
  // =========================================================================
  function markdownToHtml(md) {
    if (!md) return '';
    let html = md
      .replace(/\r\n/g, '\n')
      .replace(/^### (.*$)/gim, '<h6 class="fw-bold text-primary mt-2 mb-1">$1</h6>')
      .replace(/^## (.*$)/gim, '<h6 class="fw-bold text-dark mt-2 mb-1">$1</h6>')
      .replace(/^# (.*$)/gim, '<h6 class="fw-bold text-dark mt-2 mb-1">$1</h6>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code class="bg-light text-dark px-1 py-0 rounded">$1</code>')
      .replace(/^\> (.*$)/gim, '<blockquote class="border-start border-3 border-warning ps-2 my-2 fst-italic text-muted fs-xs">$1</blockquote>')
      .replace(/^\- (.*$)/gim, '<li class="fs-xs">$1</li>')
      .replace(/\n\n/g, '<br>');

    // Limpieza de tablas markdown simples
    if (html.includes('|')) {
      const lineas = html.split('\n');
      let enTabla = false;
      let tablaHtml = '<table class="table table-sm table-bordered fs-xs my-2">';
      const out = [];
      lineas.forEach(l => {
        if (l.trim().startsWith('|')) {
          if (!enTabla) { enTabla = true; tablaHtml = '<table class="table table-sm table-bordered fs-xs my-2"><tbody>'; }
          if (!l.includes('---')) {
            const celdas = l.split('|').filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
            tablaHtml += '<tr>' + celdas.map(c => `<td>${c.trim()}</td>`).join('') + '</tr>';
          }
        } else {
          if (enTabla) { enTabla = false; tablaHtml += '</tbody></table>'; out.push(tablaHtml); }
          out.push(l);
        }
      });
      if (enTabla) { tablaHtml += '</tbody></table>'; out.push(tablaHtml); }
      html = out.join('\n');
    }

    return html;
  }

  function actualizarAyudaLateral(claveAyuda) {
    const cont = document.getElementById('contenedor-ayuda-dinamica');
    const badgeNorm = document.getElementById('badge-ayuda-normativa');
    const tarjetaAnexo2 = document.getElementById('tarjeta-anexo2');
    const detalleAnexo2 = document.getElementById('detalle-anexo2');

    const info = window.DATOS_APP.ayudas[claveAyuda];
    if (info) {
      badgeNorm.textContent = info.normativa ? info.normativa[0] : 'Disposición 13/2025';
      cont.innerHTML = `
        <h6 class="fw-bold mb-1">${info.titulo}</h6>
        <div class="mb-2 text-muted fs-xs">
          <strong>Normativa:</strong> ${(info.normativa || []).join(' · ')}
        </div>
        <div class="fs-xs lh-sm">${markdownToHtml(info.texto)}</div>
      `;
    } else {
      cont.innerHTML = '<div class="text-muted fs-xs">Seleccione una pregunta para ver su fundamentación legal.</div>';
    }

    // Verificar si algún curso seleccionado coincide con Anexo 2 Com. 07/2026
    const cursos = estado.resp.cursos_seleccionados || [];
    let perfilEncontrado = null;

    for (const curso of cursos) {
      const cNorm = curso.toLowerCase();
      for (const p of window.DATOS_APP.perfilesAnexo2) {
        const coincide = p.claves.some(alt => alt.every(palabra => cNorm.includes(palabra)));
        if (coincide) {
          perfilEncontrado = p;
          break;
        }
      }
      if (perfilEncontrado) break;
    }

    if (perfilEncontrado) {
      tarjetaAnexo2.classList.remove('d-none');
      const d = (perfilEncontrado.grupo === 'telecom') ? window.DATOS_APP.grupoTelecom : perfilEncontrado;
      detalleAnexo2.innerHTML = `
        <div><strong>Especialidad:</strong> ${perfilEncontrado.nombre} (${perfilEncontrado.resolucion})</div>
        <div><strong>Títulos / experiencia afín:</strong> ${d.titulos}</div>
        ${d.oficios ? `<div><strong>Oficios afines:</strong> ${d.oficios}</div>` : ''}
      `;
    } else {
      tarjetaAnexo2.classList.add('d-none');
    }
  }

  // =========================================================================
  // 8. FILA EN VIVO DEL ASPIRANTE EN EVALUACIÓN
  // =========================================================================
  function actualizarFilaEnVivo() {
    const tr = document.getElementById('fila-en-vivo-tr');
    if (!tr) return;

    const r = estado.resp;
    const pt = calcularPuntajeTotal(r);
    r.puntaje = pt;

    const cur = r.cursos_seleccionados.length > 0 
      ? (r.cursos_seleccionados.length === 1 ? r.cursos_seleccionados[0] : `[${r.cursos_seleccionados.length} cursos seleccionados]`)
      : '<span class="text-muted fst-italic">Sin curso</span>';

    tr.innerHTML = `
      <td>${estado.sigId}</td>
      <td><span class="badge ${r.fi === 25 ? 'bg-success' : 'bg-secondary'}">${r.listado || 'COMPL.'}</span></td>
      <td><strong>${r.dni || '-'}</strong></td>
      <td>${r.apellido || '-'}</td>
      <td>${r.nombres || '-'}</td>
      <td class="text-start">${cur}</td>
      <td>${r.dist1 ? r.dist1.substring(0, 15) : '-'}</td>
      <td>${r.pts_dist1 !== null ? r.pts_dist1 : '-'}</td>
      <td>${r.dist2 ? r.dist2.substring(0, 15) : '-'}</td>
      <td>${r.pts_dist2 !== null ? r.pts_dist2 : '-'}</td>
      <td>${r.dist3 ? r.dist3.substring(0, 15) : '-'}</td>
      <td>${r.pts_dist3 !== null ? r.pts_dist3 : '-'}</td>
      <td>${r.fi}</td>
      <td>${r.fe_sec_orient}</td>
      <td>${r.fe_sec_tecnico}</td>
      <td>${r.fe_superior}</td>
      <td>${r.fe_universitario}</td>
      <td>${r.cap_docente.toFixed(2)}</td>
      <td>${r.cap_especifica.toFixed(2)}</td>
      <td>${r.desemp_anios !== null ? r.desemp_anios : '-'}</td>
      <td>${r.desemp_pts}</td>
      <td>${r.form_sup_fp}</td>
      <td>${r.antig_docencia.toFixed(2)}</td>
      <td>${r.antig_fp.toFixed(2)}</td>
      <td>${r.calif1.toFixed(2)}</td>
      <td>${r.calif2.toFixed(2)}</td>
      <td>${r.art59}</td>
      <td class="table-primary fw-bold text-primary">${pt.toFixed(2)}</td>
    `;
  }

  // =========================================================================
  // 9. GUARDADO DE ASPIRANTE (PUNTUAL O MULTI-CURSO)
  // =========================================================================
  function guardarAspiranteEvaluado(esOtroCursoMismoAspirante = false) {
    const r = estado.resp;

    if (!r.dni || !r.apellido || !r.nombres) {
      alert('Complete DNI, Apellido y Nombres antes de guardar.');
      estado.pasoActual = 1;
      renderizarPasoActual();
      return false;
    }

    if (r.cursos_seleccionados.length === 0) {
      alert('Debe seleccionar al menos una especialidad en el Paso 7.');
      estado.pasoActual = 7;
      renderizarPasoActual();
      return false;
    }

    const esCumple = r.cumple_hab;
    const cursosAGuardar = [...r.cursos_seleccionados];

    cursosAGuardar.forEach(c => {
      if (esCumple) {
        const item = {
          id: estado.sigId++,
          orden: estado.merituados.length + 1,
          listado: r.fi === 25 ? 'PRINCIPAL' : 'COMPLEMENTARIO',
          dni: r.dni,
          apellido: r.apellido,
          nombres: r.nombres,
          especialidad: c,
          dist1: r.dist1,
          pts_dist1: r.pts_dist1,
          dist2: r.dist2,
          pts_dist2: r.pts_dist2,
          dist3: r.dist3,
          pts_dist3: r.pts_dist3,
          fi: r.fi,
          fe_sec_orient: r.fe_sec_orient,
          fe_sec_tecnico: r.fe_sec_tecnico,
          fe_superior: r.fe_superior,
          fe_universitario: r.fe_universitario,
          cap_docente: r.cap_docente,
          cap_especifica: r.cap_especifica,
          desemp_anios: r.desemp_anios,
          desemp_pts: r.desemp_pts,
          form_sup_fp: r.form_sup_fp,
          antig_docencia: r.antig_docencia,
          antig_fp: r.antig_fp,
          calif1: r.calif1,
          calif2: r.calif2,
          art59: r.art59,
          puntaje: calcularPuntajeTotal(r)
        };
        estado.merituados.push(item);
      } else {
        const item = {
          id: estado.sigId++,
          orden: estado.noMerituados.length + 1,
          dni: r.dni,
          apellido: r.apellido,
          nombres: r.nombres,
          especialidad: c,
          dist1: r.dist1,
          dist2: r.dist2,
          dist3: r.dist3,
          motivo: r.motivo_no_meritudo,
          observaciones: r.observaciones_no_meritudo
        };
        estado.noMerituados.push(item);
      }
    });

    guardarEnLocalStorage();
    actualizarVistaCompleta();

    if (esOtroCursoMismoAspirante) {
      // Conservar datos filiatorios, distritos y probanzas comunes
      const dniGuardado = r.dni;
      const apeGuardado = r.apellido;
      const nomGuardado = r.nombres;
      const d1 = r.dist1, p1 = r.pts_dist1;
      const d2 = r.dist2, p2 = r.pts_dist2;
      const d3 = r.dist3, p3 = r.pts_dist3;
      const antDocAnios = r.antig_docencia_anios, antDocPts = r.antig_docencia;
      const antFpAnios = r.antig_fp_anios, antFpPts = r.antig_fp;
      const c1 = r.calif1, c2 = r.calif2;
      const art = r.art59;

      estado.resp = crearRespVacia();
      estado.resp.dni = dniGuardado;
      estado.resp.apellido = apeGuardado;
      estado.resp.nombres = nomGuardado;
      estado.resp.dist1 = d1; estado.resp.pts_dist1 = p1;
      estado.resp.dist2 = d2; estado.resp.pts_dist2 = p2;
      estado.resp.dist3 = d3; estado.resp.pts_dist3 = p3;
      estado.resp.antig_docencia_anios = antDocAnios; estado.resp.antig_docencia = antDocPts;
      estado.resp.antig_fp_anios = antFpAnios; estado.resp.antig_fp = antFpPts;
      estado.resp.calif1 = c1; estado.resp.calif2 = c2;
      estado.resp.art59 = art;

      estado.pasoActual = 7; // Ir directo a elegir otra familia/curso
    } else {
      estado.resp = crearRespVacia();
      estado.resp.dist1 = estado.distritoActivo;
      estado.pasoActual = 1;
    }

    renderizarPasoActual();
    return true;
  }

  // =========================================================================
  // 10. RENDERIZADO DE TABLAS INFERIORES Y EDICIÓN INLINE AL CLIC
  // =========================================================================
  function renderizarTablasCompletas() {
    const q = estado.filtroBusqueda.toLowerCase().trim();

    // 1. MERITUADOS
    const tbodyMer = document.getElementById('cuerpo-tabla-merituados');
    const filtradosMer = estado.merituados.filter(item => {
      if (!q) return true;
      return (item.dni && String(item.dni).includes(q)) ||
             (item.apellido && item.apellido.toLowerCase().includes(q)) ||
             (item.nombres && item.nombres.toLowerCase().includes(q)) ||
             (item.especialidad && item.especialidad.toLowerCase().includes(q));
    });

    document.getElementById('cont-mer').textContent = estado.merituados.length;
    document.getElementById('lbl-total-merituados').textContent = estado.merituados.length;

    let trsMer = '';
    filtradosMer.forEach(item => {
      trsMer += `
        <tr data-id="${item.id}" data-tipo="mer">
          <td class="text-center">${item.orden}</td>
          <td class="editable-cell text-center" data-col="listado" title="Clic para editar">${item.listado}</td>
          <td class="editable-cell font-monospace" data-col="dni" title="Clic para editar">${item.dni}</td>
          <td class="editable-cell" data-col="apellido" title="Clic para editar">${item.apellido}</td>
          <td class="editable-cell" data-col="nombres" title="Clic para editar">${item.nombres}</td>
          <td class="editable-cell" data-col="especialidad" title="Clic para editar">${item.especialidad}</td>
          <td class="editable-cell" data-col="dist1" title="Clic para editar">${item.dist1 || '-'}</td>
          <td class="editable-cell text-center" data-col="pts_dist1" title="Clic para editar">${item.pts_dist1 !== null ? item.pts_dist1 : '-'}</td>
          <td class="editable-cell" data-col="dist2" title="Clic para editar">${item.dist2 || '-'}</td>
          <td class="editable-cell text-center" data-col="pts_dist2" title="Clic para editar">${item.pts_dist2 !== null ? item.pts_dist2 : '-'}</td>
          <td class="editable-cell" data-col="dist3" title="Clic para editar">${item.dist3 || '-'}</td>
          <td class="editable-cell text-center" data-col="pts_dist3" title="Clic para editar">${item.pts_dist3 !== null ? item.pts_dist3 : '-'}</td>
          <td class="editable-cell text-center" data-col="fi" title="Clic para editar">${item.fi}</td>
          <td class="editable-cell text-center" data-col="fe_sec_orient" title="Clic para editar">${item.fe_sec_orient}</td>
          <td class="editable-cell text-center" data-col="fe_sec_tecnico" title="Clic para editar">${item.fe_sec_tecnico}</td>
          <td class="editable-cell text-center" data-col="fe_superior" title="Clic para editar">${item.fe_superior}</td>
          <td class="editable-cell text-center" data-col="fe_universitario" title="Clic para editar">${item.fe_universitario}</td>
          <td class="editable-cell text-center font-monospace" data-col="cap_docente" title="Clic para editar">${Number(item.cap_docente || 0).toFixed(2)}</td>
          <td class="editable-cell text-center font-monospace" data-col="cap_especifica" title="Clic para editar">${Number(item.cap_especifica || 0).toFixed(2)}</td>
          <td class="editable-cell text-center" data-col="desemp_anios" title="Clic para editar">${item.desemp_anios !== null ? item.desemp_anios : '-'}</td>
          <td class="editable-cell text-center" data-col="desemp_pts" title="Clic para editar">${item.desemp_pts}</td>
          <td class="editable-cell text-center" data-col="form_sup_fp" title="Clic para editar">${item.form_sup_fp}</td>
          <td class="editable-cell text-center font-monospace" data-col="antig_docencia" title="Clic para editar">${Number(item.antig_docencia || 0).toFixed(2)}</td>
          <td class="editable-cell text-center font-monospace" data-col="antig_fp" title="Clic para editar">${Number(item.antig_fp || 0).toFixed(2)}</td>
          <td class="editable-cell text-center font-monospace" data-col="calif1" title="Clic para editar">${Number(item.calif1 || 0).toFixed(2)}</td>
          <td class="editable-cell text-center font-monospace" data-col="calif2" title="Clic para editar">${Number(item.calif2 || 0).toFixed(2)}</td>
          <td class="editable-cell text-center" data-col="art59" title="Clic para editar">${item.art59}</td>
          <td class="table-primary text-primary fw-bold text-center font-monospace">${Number(item.puntaje || 0).toFixed(2)}</td>
          <td class="text-center">
            <button class="btn btn-outline-danger btn-sm py-0 px-1 btn-eliminar-fila" data-tipo="mer" data-id="${item.id}" title="Eliminar fila">
              <i class="bi bi-trash"></i>
            </button>
          </td>
        </tr>
      `;
    });
    tbodyMer.innerHTML = trsMer || '<tr><td colspan="29" class="text-center text-muted py-3 fst-italic">No hay aspirantes merituados cargados para este distrito.</td></tr>';

    // 2. NO MERITUADOS
    const tbodyNoMer = document.getElementById('cuerpo-tabla-nomerituados');
    const filtradosNoMer = estado.noMerituados.filter(item => {
      if (!q) return true;
      return (item.dni && String(item.dni).includes(q)) ||
             (item.apellido && item.apellido.toLowerCase().includes(q)) ||
             (item.nombres && item.nombres.toLowerCase().includes(q)) ||
             (item.especialidad && item.especialidad.toLowerCase().includes(q));
    });

    document.getElementById('cont-nomer').textContent = estado.noMerituados.length;
    document.getElementById('lbl-total-nomerituados').textContent = estado.noMerituados.length;

    let trsNoMer = '';
    filtradosNoMer.forEach(item => {
      trsNoMer += `
        <tr data-id="${item.id}" data-tipo="nomer">
          <td class="text-center">${item.orden}</td>
          <td class="editable-cell font-monospace" data-col="dni" title="Clic para editar">${item.dni}</td>
          <td class="editable-cell" data-col="apellido" title="Clic para editar">${item.apellido}</td>
          <td class="editable-cell" data-col="nombres" title="Clic para editar">${item.nombres}</td>
          <td class="editable-cell" data-col="especialidad" title="Clic para editar">${item.especialidad}</td>
          <td class="editable-cell" data-col="dist1" title="Clic para editar">${item.dist1 || '-'}</td>
          <td class="editable-cell" data-col="dist2" title="Clic para editar">${item.dist2 || '-'}</td>
          <td class="editable-cell" data-col="dist3" title="Clic para editar">${item.dist3 || '-'}</td>
          <td class="editable-cell text-danger fw-bold" data-col="motivo" title="Clic para editar">${item.motivo}</td>
          <td class="editable-cell text-muted" data-col="observaciones" title="Clic para editar">${item.observaciones || '-'}</td>
          <td class="text-center">
            <button class="btn btn-outline-danger btn-sm py-0 px-1 btn-eliminar-fila" data-tipo="nomer" data-id="${item.id}" title="Eliminar fila">
              <i class="bi bi-trash"></i>
            </button>
          </td>
        </tr>
      `;
    });
    tbodyNoMer.innerHTML = trsNoMer || '<tr><td colspan="11" class="text-center text-muted py-3 fst-italic">No hay aspirantes no merituados en este distrito.</td></tr>';

    // Vincular clics de edición y eliminación
    vincularEventosTabla();
  }

  function vincularEventosTabla() {
    // 1. Eliminar
    document.querySelectorAll('.btn-eliminar-fila').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = Number(e.currentTarget.dataset.id);
        const tipo = e.currentTarget.dataset.tipo;
        const lista = tipo === 'mer' ? estado.merituados : estado.noMerituados;
        const reg = lista.find(x => x.id === id);
        if (!reg) return;

        estado.filaBorrarInfo = { tipo, id };
        document.getElementById('txt-confirmar-borrado').textContent =
          `¿Eliminar el registro de ${reg.apellido}, ${reg.nombres} (DNI ${reg.dni}) para el curso ${reg.especialidad}?`;

        const modalBorrar = new bootstrap.Modal(document.getElementById('modalConfirmarBorrado'));
        modalBorrar.show();
      });
    });

    // 2. Edición inline al clic
    document.querySelectorAll('.editable-cell').forEach(td => {
      td.addEventListener('click', manejarClicEdicionCelda);
    });
  }

  function manejarClicEdicionCelda(e) {
    const td = e.currentTarget;
    if (td.classList.contains('cell-editing')) return; // Ya se está editando

    const tr = td.closest('tr');
    const id = Number(tr.dataset.id);
    const tipo = tr.dataset.tipo;
    const col = td.dataset.col;
    const lista = tipo === 'mer' ? estado.merituados : estado.noMerituados;
    const reg = lista.find(x => x.id === id);
    if (!reg) return;

    td.classList.add('cell-editing');
    const valorActual = reg[col] !== undefined && reg[col] !== null ? reg[col] : '';

    // Decidir el tipo de control según la columna
    let inputControl;

    if (col === 'listado') {
      inputControl = document.createElement('select');
      inputControl.innerHTML = '<option value="PRINCIPAL">PRINCIPAL</option><option value="COMPLEMENTARIO">COMPLEMENTARIO</option>';
      inputControl.value = valorActual;
    } else if (['pts_dist1', 'pts_dist2', 'pts_dist3'].includes(col)) {
      inputControl = document.createElement('select');
      inputControl.innerHTML = '<option value="0">0</option><option value="5">5</option>';
      inputControl.value = String(valorActual || 0);
    } else if (col === 'fi') {
      inputControl = document.createElement('select');
      inputControl.innerHTML = '<option value="0">0</option><option value="25">25</option>';
      inputControl.value = String(valorActual || 0);
    } else if (col === 'form_sup_fp') {
      inputControl = document.createElement('select');
      inputControl.innerHTML = '<option value="0">0</option><option value="7">7</option>';
      inputControl.value = String(valorActual || 0);
    } else if (col === 'art59') {
      inputControl = document.createElement('select');
      inputControl.innerHTML = '<option value="0">0</option><option value="10">10</option>';
      inputControl.value = String(valorActual !== undefined ? valorActual : 10);
    } else if (col === 'desemp_pts') {
      inputControl = document.createElement('select');
      inputControl.innerHTML = '<option value="0">0</option><option value="5">5</option><option value="6">6</option><option value="8">8</option>';
      inputControl.value = String(valorActual || 0);
    } else if (col === 'antig_docencia') {
      inputControl = document.createElement('select');
      let o = '';
      [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5].forEach(v => {
        o += `<option value="${v}">${v.toFixed(2)}</option>`;
      });
      inputControl.innerHTML = o;
      inputControl.value = Number(valorActual).toFixed(2);
    } else if (col === 'antig_fp') {
      inputControl = document.createElement('select');
      let o = '';
      [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0].forEach(v => {
        o += `<option value="${v}">${v.toFixed(2)}</option>`;
      });
      inputControl.innerHTML = o;
      inputControl.value = Number(valorActual).toFixed(2);
    } else if (col === 'calif1' || col === 'calif2') {
      inputControl = document.createElement('select');
      let o = '';
      [0.0, 0.1, 0.5, 1.0].forEach(v => {
        o += `<option value="${v}">${v.toFixed(2)}</option>`;
      });
      inputControl.innerHTML = o;
      inputControl.value = Number(valorActual).toFixed(2);
    } else if (['fe_sec_orient', 'fe_sec_tecnico', 'fe_superior', 'fe_universitario'].includes(col)) {
      const maxPts = { fe_sec_orient: 3, fe_sec_tecnico: 5, fe_superior: 7, fe_universitario: 8 }[col];
      inputControl = document.createElement('select');
      inputControl.innerHTML = `<option value="0">0</option><option value="${maxPts}">${maxPts}</option>`;
      inputControl.value = String(valorActual || 0);
    } else if (col === 'motivo') {
      inputControl = document.createElement('select');
      let o = '';
      window.DATOS_APP.motivosNoMerituado.forEach(m => {
        o += `<option value="${m}">${m}</option>`;
      });
      inputControl.innerHTML = o;
      inputControl.value = valorActual;
    } else if (['dist1', 'dist2', 'dist3'].includes(col)) {
      inputControl = document.createElement('select');
      let o = '<option value="">-- Ninguno --</option>';
      window.DATOS_APP.distritos.forEach(d => {
        o += `<option value="${d}">${d}</option>`;
      });
      inputControl.innerHTML = o;
      inputControl.value = valorActual;
    } else {
      // Texto o número estándar
      inputControl = document.createElement('input');
      inputControl.type = ['cap_docente', 'cap_especifica', 'desemp_anios'].includes(col) ? 'number' : 'text';
      if (inputControl.type === 'number') inputControl.step = '0.01';
      inputControl.value = valorActual;
      if (['apellido', 'nombres'].includes(col)) {
        inputControl.style.textTransform = 'uppercase';
      }
    }

    td.innerHTML = '';
    td.appendChild(inputControl);
    inputControl.focus();

    const guardarEdicion = () => {
      let nuevoVal = inputControl.value;

      // Conversión de tipos
      if (['fi', 'form_sup_fp', 'art59', 'desemp_pts', 'fe_sec_orient', 'fe_sec_tecnico', 'fe_superior', 'fe_universitario'].includes(col)) {
        nuevoVal = Number(nuevoVal);
      } else if (['pts_dist1', 'pts_dist2', 'pts_dist3'].includes(col)) {
        nuevoVal = Number(nuevoVal);
        // Si es 5, apagar los otros dos
        if (nuevoVal === 5) {
          if (col === 'pts_dist1') { reg.pts_dist2 = 0; reg.pts_dist3 = 0; }
          if (col === 'pts_dist2') { reg.pts_dist1 = 0; reg.pts_dist3 = 0; }
          if (col === 'pts_dist3') { reg.pts_dist1 = 0; reg.pts_dist2 = 0; }
        }
      } else if (['antig_docencia', 'antig_fp', 'calif1', 'calif2', 'cap_docente', 'cap_especifica'].includes(col)) {
        nuevoVal = parseFloat(nuevoVal) || 0.0;
        if (col === 'cap_docente') nuevoVal = Math.min(nuevoVal, window.DATOS_APP.topes.capDocente);
        if (col === 'cap_especifica') nuevoVal = Math.min(nuevoVal, window.DATOS_APP.topes.capEspecifica);
      } else if (col === 'desemp_anios') {
        nuevoVal = nuevoVal === '' ? null : parseInt(nuevoVal, 10);
        if (nuevoVal !== null) {
          if (nuevoVal <= 2) reg.desemp_pts = 0;
          else if (nuevoVal <= 4) reg.desemp_pts = 5;
          else if (nuevoVal <= 9) reg.desemp_pts = 6;
          else reg.desemp_pts = 8;
        }
      } else if (['apellido', 'nombres'].includes(col)) {
        nuevoVal = nuevoVal.toUpperCase();
      }

      reg[col] = nuevoVal;

      // Si se editó FI, sincronizar el listado
      if (col === 'fi') {
        reg.listado = nuevoVal === 25 ? 'PRINCIPAL' : 'COMPLEMENTARIO';
      }

      // Recalcular puntaje total de la fila
      if (tipo === 'mer') {
        reg.puntaje = calcularPuntajeTotal(reg);
      }

      td.classList.remove('cell-editing');
      guardarEnLocalStorage();
      renderizarTablasCompletas();
    };

    inputControl.addEventListener('blur', guardarEdicion, { once: true });
    inputControl.addEventListener('keydown', (evt) => {
      if (evt.key === 'Enter') {
        inputControl.blur();
      } else if (evt.key === 'Escape') {
        td.classList.remove('cell-editing');
        renderizarTablasCompletas();
      }
    });
  }

  // =========================================================================
  // 11. EXPORTACIÓN OFICIAL CON EXCELJS
  // =========================================================================
  async function descargarPlanillaOficialExcel() {
    if (!estado.distritoActivo) {
      alert('Debe seleccionar un distrito primero.');
      return;
    }

    const btn = document.getElementById('btn-descargar-xlsx');
    const txtOriginal = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Generando Excel...';

    try {
      // 1. Fetch de plantilla.xlsx
      const resp = await fetch('plantilla.xlsx');
      if (!resp.ok) throw new Error('No se pudo cargar docs/plantilla.xlsx.');
      const arrayBuffer = await resp.arrayBuffer();

      // 2. Cargar workbook en ExcelJS
      const workbook = new ExcelJS.Workbook();
      await workbook.xlsx.load(arrayBuffer);

      // 3. Escribir celda D1 en ambas hojas
      const wsMer = workbook.getWorksheet('MERITUADOS');
      const wsNoMer = workbook.getWorksheet('NO MERITUADOS');
      const wsH2 = workbook.getWorksheet('Hoja 2');

      if (wsMer) wsMer.getCell('D1').value = estado.distritoActivo;
      if (wsNoMer) wsNoMer.getCell('D1').value = estado.distritoActivo;

      // 4. Volcar MERITUADOS desde fila 9
      if (wsMer) {
        let filaIdx = 9;
        estado.merituados.forEach(m => {
          const row = wsMer.getRow(filaIdx);
          row.getCell(1).value = m.orden;
          row.getCell(2).value = m.listado;
          row.getCell(3).value = Number(m.dni) || m.dni;
          row.getCell(4).value = m.apellido;
          row.getCell(5).value = m.nombres;
          row.getCell(6).value = m.especialidad;
          row.getCell(7).value = m.dist1 || null;
          row.getCell(8).value = m.pts_dist1 !== null ? Number(m.pts_dist1) : null;
          row.getCell(9).value = m.dist2 || null;
          row.getCell(10).value = m.pts_dist2 !== null ? Number(m.pts_dist2) : null;
          row.getCell(11).value = m.dist3 || null;
          row.getCell(12).value = m.pts_dist3 !== null ? Number(m.pts_dist3) : null;
          row.getCell(13).value = Number(m.fi || 0);
          row.getCell(14).value = Number(m.fe_sec_orient || 0);
          row.getCell(15).value = Number(m.fe_sec_tecnico || 0);
          row.getCell(16).value = Number(m.fe_superior || 0);
          row.getCell(17).value = Number(m.fe_universitario || 0);
          row.getCell(18).value = Number(m.cap_docente || 0);
          row.getCell(19).value = Number(m.cap_especifica || 0);
          row.getCell(20).value = m.desemp_anios !== null ? Number(m.desemp_anios) : null;
          row.getCell(21).value = Number(m.desemp_pts || 0);
          row.getCell(22).value = Number(m.form_sup_fp || 0);
          row.getCell(23).value = Number(m.antig_docencia || 0);
          row.getCell(24).value = Number(m.antig_fp || 0);
          row.getCell(25).value = Number(m.calif1 || 0);
          row.getCell(26).value = Number(m.calif2 || 0);
          row.getCell(27).value = Number(m.art59 || 0);
          row.getCell(28).value = Number(m.puntaje || 0);
          row.commit();
          filaIdx++;
        });
      }

      // 5. Volcar NO MERITUADOS desde fila 9
      if (wsNoMer) {
        let filaIdxNo = 9;
        estado.noMerituados.forEach(nm => {
          const row = wsNoMer.getRow(filaIdxNo);
          row.getCell(1).value = nm.orden;
          row.getCell(3).value = Number(nm.dni) || nm.dni;
          row.getCell(4).value = nm.apellido;
          row.getCell(5).value = nm.nombres;
          row.getCell(6).value = nm.especialidad;
          row.getCell(7).value = nm.dist1 || null;
          row.getCell(8).value = nm.dist2 || null;
          row.getCell(9).value = nm.dist3 || null;
          row.getCell(10).value = nm.motivo;
          row.getCell(11).value = nm.observaciones || null;
          row.commit();
          filaIdxNo++;
        });
      }

      // 6. Inyectar cursos nuevos en Hoja 2 columna A
      if (wsH2 && estado.cursosPersonalizados.length > 0) {
        const cursosBase = new Set(window.DATOS_APP.cursos);
        const nuevos = estado.cursosPersonalizados.filter(c => !cursosBase.has(c));
        if (nuevos.length > 0) {
          let ultimaFila = wsH2.rowCount;
          nuevos.forEach(c => {
            ultimaFila++;
            wsH2.getCell(`A${ultimaFila}`).value = c;
          });
        }
      }

      // 7. Generar buffer y descargar
      const bufferSalida = await workbook.xlsx.writeBuffer();
      const blob = new Blob([bufferSalida], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `PLANILLA DE DATOS DE ASPIRANTES - ${slugDistrito(estado.distritoActivo)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

    } catch (err) {
      console.error(err);
      alert('Error al generar la planilla oficial: ' + err.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = txtOriginal;
    }
  }

  // =========================================================================
  // 12. CARGA DE TABULACIÓN PREVIA (.XLSX O .JSON)
  // =========================================================================
  async function procesarArchivoAnterior(file) {
    const lblEstado = document.getElementById('lbl-estado-carga-archivo');
    lblEstado.innerHTML = '<span class="spinner-border spinner-border-sm text-success me-1"></span> Leyendo archivo...';

    const nombre = file.name.toLowerCase();

    if (nombre.endsWith('.json')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const d = JSON.parse(e.target.result);
          if (!d.distrito) throw new Error('El archivo JSON no contiene un distrito válido.');
          estado.distritoActivo = d.distrito;
          estado.merituados = d.merituados || [];
          estado.noMerituados = d.noMerituados || [];
          estado.cursosPersonalizados = Array.from(new Set([...(d.cursosPersonalizados || []), ...(window.DATOS_APP.cursosIniciales2027 || [])]));
          estado.incluirResidencia = Boolean(d.incluirResidencia);
          estado.sigId = (d.sigId || 0) || (estado.merituados.length + estado.noMerituados.length + 1);

          guardarEnLocalStorage();
          sessionStorage.setItem('evaluador_distrito_actual', estado.distritoActivo);
          document.getElementById('txt-distrito-activo').textContent = estado.distritoActivo;
          document.getElementById('chk-incluir-residencia').checked = estado.incluirResidencia;

          cerrarModalInicio();
          actualizarVistaCompleta();
          alert(`✅ Respaldo JSON cargado con éxito: ${estado.merituados.length} merituados y ${estado.noMerituados.length} no merituados.`);
        } catch (err) {
          lblEstado.innerHTML = `<span class="text-danger">Error: ${err.message}</span>`;
        }
      };
      reader.readAsText(file);

    } else if (nombre.endsWith('.xlsx')) {
      try {
        const arrayBuffer = await file.arrayBuffer();
        const workbook = new ExcelJS.Workbook();
        await workbook.xlsx.load(arrayBuffer);

        const wsMer = workbook.getWorksheet('MERITUADOS');
        const wsNoMer = workbook.getWorksheet('NO MERITUADOS');

        if (!wsMer && !wsNoMer) {
          throw new Error('El archivo Excel no contiene las hojas "MERITUADOS" o "NO MERITUADOS".');
        }

        // Obtener distrito de D1
        let distritoLeido = '';
        if (wsMer && wsMer.getCell('D1').value) {
          distritoLeido = String(wsMer.getCell('D1').value).trim();
        } else if (wsNoMer && wsNoMer.getCell('D1').value) {
          distritoLeido = String(wsNoMer.getCell('D1').value).trim();
        }

        // Buscar correspondencia en catálogo de distritos
        let distritoFinal = distritoLeido;
        const distCoincidente = window.DATOS_APP.distritos.find(d => 
          distritoLeido.toLowerCase().includes(d.toLowerCase()) || d.toLowerCase().includes(distritoLeido.toLowerCase())
        );
        if (distCoincidente) distritoFinal = distCoincidente;

        if (!distritoFinal) {
          distritoFinal = window.DATOS_APP.distritos[0];
        }

        const merList = [];
        const noMerList = [];
        let idCounter = 1;

        // Leer MERITUADOS desde fila 9
        if (wsMer) {
          wsMer.eachRow((row, rowNumber) => {
            if (rowNumber >= 9) {
              const dniVal = row.getCell(3).value;
              const apeVal = row.getCell(4).value;
              if (dniVal && apeVal) {
                const item = {
                  id: idCounter++,
                  orden: Number(row.getCell(1).value) || (merList.length + 1),
                  listado: String(row.getCell(2).value || 'COMPLEMENTARIO').toUpperCase(),
                  dni: String(dniVal).replace(/\D/g, ''),
                  apellido: String(apeVal).toUpperCase(),
                  nombres: String(row.getCell(5).value || '').toUpperCase(),
                  especialidad: String(row.getCell(6).value || ''),
                  dist1: row.getCell(7).value ? String(row.getCell(7).value) : '',
                  pts_dist1: row.getCell(8).value !== null ? Number(row.getCell(8).value) : null,
                  dist2: row.getCell(9).value ? String(row.getCell(9).value) : '',
                  pts_dist2: row.getCell(10).value !== null ? Number(row.getCell(10).value) : null,
                  dist3: row.getCell(11).value ? String(row.getCell(11).value) : '',
                  pts_dist3: row.getCell(12).value !== null ? Number(row.getCell(12).value) : null,
                  fi: Number(row.getCell(13).value || 0),
                  fe_sec_orient: Number(row.getCell(14).value || 0),
                  fe_sec_tecnico: Number(row.getCell(15).value || 0),
                  fe_superior: Number(row.getCell(16).value || 0),
                  fe_universitario: Number(row.getCell(17).value || 0),
                  cap_docente: parseFloat(row.getCell(18).value) || 0.0,
                  cap_especifica: parseFloat(row.getCell(19).value) || 0.0,
                  desemp_anios: row.getCell(20).value !== null ? Number(row.getCell(20).value) : null,
                  desemp_pts: Number(row.getCell(21).value || 0),
                  form_sup_fp: Number(row.getCell(22).value || 0),
                  antig_docencia: parseFloat(row.getCell(23).value) || 0.0,
                  antig_fp: parseFloat(row.getCell(24).value) || 0.0,
                  calif1: parseFloat(row.getCell(25).value) || 0.0,
                  calif2: parseFloat(row.getCell(26).value) || 0.0,
                  art59: row.getCell(27).value !== null ? Number(row.getCell(27).value) : 10,
                  puntaje: parseFloat(row.getCell(28).value) || 0.0
                };
                merList.push(item);
              }
            }
          });
        }

        // Leer NO MERITUADOS desde fila 9
        if (wsNoMer) {
          wsNoMer.eachRow((row, rowNumber) => {
            if (rowNumber >= 9) {
              const dniVal = row.getCell(3).value;
              const apeVal = row.getCell(4).value;
              if (dniVal && apeVal) {
                const item = {
                  id: idCounter++,
                  orden: Number(row.getCell(1).value) || (noMerList.length + 1),
                  dni: String(dniVal).replace(/\D/g, ''),
                  apellido: String(apeVal).toUpperCase(),
                  nombres: String(row.getCell(5).value || '').toUpperCase(),
                  especialidad: String(row.getCell(6).value || ''),
                  dist1: row.getCell(7).value ? String(row.getCell(7).value) : '',
                  dist2: row.getCell(8).value ? String(row.getCell(8).value) : '',
                  dist3: row.getCell(9).value ? String(row.getCell(9).value) : '',
                  motivo: String(row.getCell(10).value || 'No Reune Requisitos'),
                  observaciones: row.getCell(11).value ? String(row.getCell(11).value) : ''
                };
                noMerList.push(item);
              }
            }
          });
        }

        estado.distritoActivo = distritoFinal;
        estado.merituados = merList;
        estado.noMerituados = noMerList;
        estado.sigId = idCounter;

        guardarEnLocalStorage();
        sessionStorage.setItem('evaluador_distrito_actual', estado.distritoActivo);
        document.getElementById('txt-distrito-activo').textContent = estado.distritoActivo;

        cerrarModalInicio();
        actualizarVistaCompleta();
        alert(`✅ Planilla Excel cargada con éxito para ${estado.distritoActivo}:\n• ${merList.length} merituados\n• ${noMerList.length} no merituados.`);
      } catch (err) {
        lblEstado.innerHTML = `<span class="text-danger">Error al procesar Excel: ${err.message}</span>`;
      }
    }
  }

  // =========================================================================
  // 13. RESUMEN DE LECTURA ZOOM / MEET
  // =========================================================================
  function abrirModalResumenZoom() {
    const r = estado.resp;
    const ptBase = calcularPuntajeTotal(r, false);
    const ptConRes = calcularPuntajeTotal(r, true);
    const hayRes = [r.pts_dist1, r.pts_dist2, r.pts_dist3].some(v => Number(v) === 5);

    const txt = `COMISIÓN EVALUADORA REGIONAL FP - LISTADOS 2027
--------------------------------------------------------------
DISTRITO EVALUADOR: ${estado.distritoActivo || 'No especificado'}
ASPIRANTE: ${r.apellido || '---'}, ${r.nombres || '---'} (DNI: ${r.dni || '---'})
CURSO(S): ${r.cursos_seleccionados.join(' | ') || '---'}
CONDICIÓN: ${r.cumple_hab ? 'MERITUADO' : 'NO MERITUADO'}
LISTADO: ${r.listado || 'COMPLEMENTARIO'}

DESGLOSE DE ANTECEDENTES Y PUNTAJE:
• FI (Certificado de Instructor): ${r.fi} pts
• Formación Específica (N–Q): ${Math.max(r.fe_sec_orient, r.fe_sec_tecnico, r.fe_superior, r.fe_universitario)} pts (${r.formacion_opcion})
• Capacitación Docente (Col. R): ${r.cap_docente.toFixed(2)} pts
• Capacitación Específica (Col. S): ${r.cap_especifica.toFixed(2)} pts
• Desempeño Profesional (Col. U): ${r.desemp_pts} pts (${r.desemp_anios !== null ? r.desemp_anios : 0} años)
• Formación Superior en FP (Col. V): ${r.form_sup_fp} pts
• Antigüedad Docencia Oficial (Col. W): ${r.antig_docencia.toFixed(2)} pts (${r.antig_docencia_anios || 0} años)
• Antigüedad Ámbito FP (Col. X): ${r.antig_fp.toFixed(2)} pts (${r.antig_fp_anios || 0} años)
• Calificaciones FP (Cols. Y+Z): ${(r.calif1 + r.calif2).toFixed(2)} pts (Año 1: ${r.calif1.toFixed(2)}, Año 2: ${r.calif2.toFixed(2)})
• Art. 59 Estatuto Docente (Col. AA): ${r.art59} pts
--------------------------------------------------------------
PUNTAJE BASE (Columna AB): ${ptBase.toFixed(2)} pts
RESIDENCIA EN EL DISTRITO: ${hayRes ? '+5.00 pts' : '0.00 pts'}
PUNTAJE CON RESIDENCIA: ${ptConRes.toFixed(2)} pts
${!r.cumple_hab ? `\nMOTIVO DE NO MERITUDO: ${r.motivo_no_meritudo}\nOBSERVACIONES: ${r.observaciones_no_meritudo || 'Sin observaciones'}` : ''}`;

    document.getElementById('texto-resumen-zoom').textContent = txt;
    const modal = new bootstrap.Modal(document.getElementById('modalResumenZoom'));
    modal.show();
  }

  // =========================================================================
  // 14. MODAL NUEVA ESPECIALIDAD PERSONALIZADA
  // =========================================================================
  function abrirModalNuevoCurso() {
    const sel = document.getElementById('sel-nuevo-curso-familia');
    sel.innerHTML = '';
    for (const [k, v] of Object.entries(window.DATOS_APP.familias)) {
      sel.innerHTML += `<option value="${k}">${v}</option>`;
    }
    document.getElementById('input-nuevo-curso-codigo').value = '';
    document.getElementById('input-nuevo-curso-nombre').value = '';
    document.getElementById('lbl-error-nuevo-curso').textContent = '';

    const modal = new bootstrap.Modal(document.getElementById('modalNuevoCurso'));
    modal.show();
  }

  function guardarNuevoCursoModal() {
    const prefijo = document.getElementById('sel-nuevo-curso-familia').value;
    let codigo = document.getElementById('input-nuevo-curso-codigo').value.trim().toUpperCase();
    let nombre = document.getElementById('input-nuevo-curso-nombre').value.trim();
    const lblErr = document.getElementById('lbl-error-nuevo-curso');

    if (!codigo || !nombre) {
      lblErr.textContent = 'El código y la denominación son obligatorios.';
      return;
    }

    if (!codigo.startsWith(prefijo)) {
      codigo = `${prefijo}${codigo.replace(/^[A-Z0-9]+/, '')}`;
    }

    const formatoCurso = `${codigo} - ${nombre}`;
    if (!estado.cursosPersonalizados.includes(formatoCurso)) {
      estado.cursosPersonalizados.push(formatoCurso);
    }
    if (!estado.resp.cursos_seleccionados.includes(formatoCurso)) {
      estado.resp.cursos_seleccionados.push(formatoCurso);
    }

    guardarEnLocalStorage();
    bootstrap.Modal.getInstance(document.getElementById('modalNuevoCurso')).hide();
    renderPaso7(document.getElementById('contenedor-paso-dinamico'));
    actualizarFilaEnVivo();
  }

  // =========================================================================
  // 15. NAVEGACIÓN DEL WIZARD (ANTERIOR / SIGUIENTE)
  // =========================================================================
  function avanzarPaso() {
    const p = estado.pasoActual;
    const r = estado.resp;

    // Validaciones por paso
    if (p === 1) {
      if (!r.dni || r.dni.length < 6) {
        alert('Ingrese un número de DNI válido (mínimo 6 dígitos).');
        return;
      }
    } else if (p === 2) {
      if (!r.apellido.trim()) {
        alert('El apellido es obligatorio.');
        return;
      }
    } else if (p === 3) {
      if (!r.nombres.trim()) {
        alert('Los nombres son obligatorios.');
        return;
      }
    } else if (p === 4) {
      if (!r.dist1) {
        alert('Debe seleccionar al menos el Distrito 1.');
        return;
      }
    } else if (p === 7) {
      if (r.cursos_seleccionados.length === 0) {
        alert('Debe seleccionar al menos una especialidad antes de avanzar.');
        return;
      }
    } else if (p === 8) {
      const cumple = evaluarHabilitacion(r);
      if (!cumple) {
        estado.pasoActual = 19; // Ir a No Meritúa
        renderizarPasoActual();
        return;
      }
    }

    if (p === 18 || p === 19) return;

    estado.pasoActual = p + 1;
    renderizarPasoActual();
  }

  function retrocederPaso() {
    if (estado.pasoActual === 1) return;
    if (estado.pasoActual === 19) {
      estado.pasoActual = 8;
    } else {
      estado.pasoActual -= 1;
    }
    renderizarPasoActual();
  }

  // =========================================================================
  // 16. REGISTRO DE EVENTOS GLOBALES
  // =========================================================================
  function registrarEventos() {
    // Botón Cambiar Distrito
    document.getElementById('btn-cambiar-distrito').addEventListener('click', abrirModalInicio);

    // Modal Inicio Opción A
    const selA = document.getElementById('sel-distrito-inicio');
    const btnA = document.getElementById('btn-confirmar-distrito-nuevo');
    selA.addEventListener('change', () => {
      btnA.disabled = !selA.value;
    });
    btnA.addEventListener('click', () => {
      if (selA.value) cargarDistrito(selA.value);
    });

    // Modal Inicio Opción B (Archivo)
    const fileB = document.getElementById('file-cargar-anterior');
    const btnB = document.getElementById('btn-procesar-archivo-anterior');
    fileB.addEventListener('change', () => {
      btnB.disabled = !fileB.files.length;
    });
    btnB.addEventListener('click', () => {
      if (fileB.files.length) procesarArchivoAnterior(fileB.files[0]);
    });

    // Switch de Residencia (+5 pts)
    document.getElementById('chk-incluir-residencia').addEventListener('change', (e) => {
      estado.incluirResidencia = e.target.checked;
      guardarEnLocalStorage();
      // Recalcular puntajes de merituados
      estado.merituados.forEach(m => {
        m.puntaje = calcularPuntajeTotal(m, estado.incluirResidencia);
      });
      actualizarVistaCompleta();
    });

    // Descarga Excel
    document.getElementById('btn-descargar-xlsx').addEventListener('click', descargarPlanillaOficialExcel);

    // Descarga JSON
    document.getElementById('btn-descargar-json').addEventListener('click', () => {
      if (!estado.distritoActivo) return;
      const datos = {
        distrito: estado.distritoActivo,
        incluirResidencia: estado.incluirResidencia,
        merituados: estado.merituados,
        noMerituados: estado.noMerituados,
        cursosPersonalizados: estado.cursosPersonalizados,
        sigId: estado.sigId,
        fechaExportacion: new Date().toISOString()
      };
      const blob = new Blob([JSON.stringify(datos, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `respaldo_evaluador_${slugDistrito(estado.distritoActivo)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    });

    // Wizard Botonera
    document.getElementById('btn-paso-anterior').addEventListener('click', retrocederPaso);
    document.getElementById('btn-paso-siguiente').addEventListener('click', avanzarPaso);

    // Acciones Finales
    document.getElementById('btn-resumen-zoom').addEventListener('click', abrirModalResumenZoom);
    document.getElementById('btn-evaluar-otro-curso').addEventListener('click', () => {
      guardarAspiranteEvaluado(true);
    });
    document.getElementById('btn-guardar-nuevo-aspirante').addEventListener('click', () => {
      guardarAspiranteEvaluado(false);
    });

    // Copiar resumen Zoom
    document.getElementById('btn-copiar-resumen-zoom').addEventListener('click', () => {
      const txt = document.getElementById('texto-resumen-zoom').textContent;
      navigator.clipboard.writeText(txt).then(() => {
        alert('Texto copiado al portapapeles listo para pegar en Zoom/Meet.');
      });
    });

    // Guardar nuevo curso modal
    document.getElementById('btn-guardar-nuevo-curso').addEventListener('click', guardarNuevoCursoModal);

    // Confirmar eliminación de fila
    document.getElementById('btn-confirmar-eliminar-fila').addEventListener('click', () => {
      if (!estado.filaBorrarInfo) return;
      const { tipo, id } = estado.filaBorrarInfo;
      if (tipo === 'mer') {
        estado.merituados = estado.merituados.filter(x => x.id !== id);
        // Reordenar
        estado.merituados.forEach((m, idx) => m.orden = idx + 1);
      } else {
        estado.noMerituados = estado.noMerituados.filter(x => x.id !== id);
        estado.noMerituados.forEach((m, idx) => m.orden = idx + 1);
      }
      guardarEnLocalStorage();
      bootstrap.Modal.getInstance(document.getElementById('modalConfirmarBorrado')).hide();
      actualizarVistaCompleta();
    });

    // Buscador tabla
    const inpBuscar = document.getElementById('input-buscar-tabla');
    inpBuscar.addEventListener('input', (e) => {
      estado.filtroBusqueda = e.target.value;
      renderizarTablasCompletas();
    });
    document.getElementById('btn-limpiar-busqueda').addEventListener('click', () => {
      inpBuscar.value = '';
      estado.filtroBusqueda = '';
      renderizarTablasCompletas();
    });
  }

  function actualizarVistaCompleta() {
    renderizarPasoActual();
    renderizarTablasCompletas();
  }

})();
