# Sistema de Gestión de Alertas — Kuepa

> Documento maestro del proyecto. **Léelo al inicio de cada sesión** para entender la
> filosofía, la arquitectura y el estado de avance, en vez de re-explorar el código.
> **Manténlo actualizado**: cada vez que se complete un paso, marca el checklist y
> anota decisiones nuevas en la sección correspondiente.

Última actualización: 2026-06-12

---

## 1. Filosofía del sistema

El objetivo es **anticipar la deserción estudiantil** detectando señales tempranas de
riesgo y poniéndolas frente al equipo que puede actuar (gestores, coordinación
académica). Principios:

- **Snapshot histórico, no foto en vivo.** Cada corrida semanal congela el estado de
  cada estudiante con una `fecha_informe`. El valor no está solo en "quién está en
  riesgo hoy", sino en **la evolución**: quién mejoró, quién empeoró, qué gestor movió
  la aguja. Por eso nunca consultamos BigQuery en vivo desde el dashboard.
- **El estudiante es la unidad de gestión.** Las alertas se consolidan a nivel
  estudiante aunque la data fuente sea más granular (por materia, por sesión).
- **Múltiples señales > una sola.** Un alumno con una alerta es ruido; un alumno con
  varias señales simultáneas (no se conecta + en mora + no asiste + reprueba) es una
  deserción casi segura. La vista de **riesgo combinado** es el corazón del sistema.
- **Cada alerta tiene un dueño.** Las alertas de estudiante son para gestores; las
  operativas (p. ej. profesores que no registran asistencia) van en panel aparte para
  el equipo correcto.
- **Identidad visual Kuepa siempre.** Naranja `#FD531E`, verde `#149852`, morado
  `#9725B9`, fondo oscuro, tipografía Barlow. Reusar componentes existentes
  (`section-title`, métricas, barras apiladas) en vez de inventar estilos nuevos.

---

## 2. Arquitectura

```
BigQuery (potent-poetry-284019)
        │   queries SQL (una por tipo de alerta)
        ▼
n8n  ── workflow SEMANAL, un nodo de query por alerta ──┐
        │                                                │ escribe
        ▼                                                ▼
Google Sheet (ID 1hPWt0oBdbJTuIEbkFh1G9V1NDXh_ADKUt3OqJPocxaU)
   ├─ Hoja 1     → alertas de conexión/login + estado financiero   [EN PROD]
   ├─ Asistencia → ausentismo (por estudiante × materia)           [POR CREAR]
   └─ Notas      → reprobación (por estudiante × materia)          [POR CREAR]
        │
        ▼
Streamlit  dashboard_alertas.py  (lee el Sheet con gspread, cache 5 min)
```

- **Pipeline:** un workflow **semanal de n8n** corre las queries y escribe cada
  resultado a una pestaña del Sheet. Para alertas nuevas → nodo de query nuevo + pestaña
  nueva. Los tres nodos deben correr en la **misma ejecución** para que las
  `fecha_informe` coincidan (es la llave del cruce 360).
- **Dashboard:** `dashboard_alertas.py` (Streamlit). Lee el Sheet, no BigQuery. Auth vía
  `st.secrets["gcp_service_account"]` en cloud o `credentials.json` local.

### Llave de cruce
`user_incremental` + `fecha_informe`. Es el único campo común a las tres fuentes.

### Config de los nodos n8n (no sobreescribir el histórico)
El trigger semanal hace fan-out a 3 ramas paralelas; cada query va a su **propio** nodo
Google Sheets (no comparten el code node `clasifica categoría`, que es solo para login).

- **Operation:** `Append or Update Row` · **Mapping:** `Map Automatically`.
- **Column to match on:** `clave_registro` — columna única que añade cada query nueva.
  Incluye la fecha del snapshot, así cada semana inserta filas nuevas (no sobreescribe) y
  re-correr el mismo día actualiza en vez de duplicar. Grano según la fuente:
  Asistencia = `estudiante|materia|fecha`; Notas = `estudiante|fecha` (resumen por alumno).
- Las pestañas `Asistencia` / `Notas` deben tener en la fila 1 los nombres de columna
  exactos del SELECT (ver §3 + `queries/*.sql`) para que el auto-mapping encaje.

### Reto de granularidad (clave para entender el diseño)
- **Hoja 1**: grano = 1 fila por **estudiante** por fecha.
- **Asistencia / Notas**: grano = 1 fila por **estudiante × materia**.

Por eso se trabaja en dos niveles:
- **Detalle** (materia): tablas donde el alumno aparece una vez por materia problemática.
- **Rollup por estudiante**: derivar `nivel_ausentismo` (el peor de sus materias) y
  `materias_reprobadas` (conteo). Esto alimenta métricas y la matriz integral.

---

## 3. Fuentes de datos — columnas

### Hoja 1 (login + financiero) — EN PROD
`user_id`, `user_incremental`, `user_full_name`, `program_name`, `level_name`,
`alert_type` (SIN ALERTA / ALERTA TIPO 1..5 / SIN CONEXIÓN), `financial_status_name`,
`gestor_asignado`, `fecha_informe`.
Derivadas en el código: `gravedad` (rank 0–6), `fin_rank` (0–5), `etapa` (Lectiva/Productiva).

### Asistencia / Ausentismo — query lista (v2: por días de falta consecutivos)
Dataset `DVKU_SIS`. Pestaña destino del Sheet sigue siendo `Asistencia`.
Salida (1 fila por **estudiante**): `user_incremental`, `NOMBRE_ESTUDIANTE`,
`ESTADO_ACADEMICO`, `PROGRAMA`, `tipo_ausentismo` (Bachillerato/Técnico),
`dias_falta_consecutivos`, `NIVEL_ALERTA`, `gravedad_ausentismo` (0–5, mayor=peor),
`FECHA_REPORTE`, `clave_registro` (= `estudiante|fecha`).
- **Lógica = racha de faltas CONSECUTIVAS** hasta la fecha de corte (ya NO es % de asistencia).
  Escalas distintas por programa:
  - **Técnico:** Sin alerta 0–1 · Alerta 1: 2 · Alerta 3: 3–4 · Alerta 5: ≥5
  - **Bachillerato Plus:** Sin alerta 0–1 · Alerta 1: 2–4 · Alerta 2: 5–6 · Alerta 3: 7–10 · Alerta 4: >10
- **Bachillerato Flex EXCLUIDO** (asistencia no obligatoria; se sacó su `program_id`).
- **"Día"** = jornada de clase programada (no día calendario). Si asistió a ≥1 clase ese día →
  presente. Sesiones sin registrar (ATTENDANCE NULL) se **ignoran** (no rompen la racha).
- **"Activo":** mismo abanico de `academic_status_name` que Notas (coherencia Riesgo 360).
- **Cambio importante:** esta v2 ya **no trae** el panel de "sesiones sin registrar (docentes)"
  ni columnas de % / sesiones. Si se quiere ese panel operativo, sería un feed aparte.
  El **dashboard (`render_ausentismo`) debe reescribirse** a este nuevo esquema.

### Notas (reprobación / desempeño académico) — query lista
Datasets `DVKU_SIS` (estudiantes/estado) + `DSKU_SIS` (notas). Salida (1 fila por
**estudiante**): `user_incremental`, `user_full_name`, `modalidad` (Bachillerato/Técnico),
`program_name`, `modulos_cursados`, `modulos_aprobados`, `modulos_reprobados`,
`nota_promedio`, `fecha_informe`, `clave_registro` (= `estudiante|fecha`, llave única n8n).
- **Grano:** 1 fila por **estudiante** = resumen **histórico** de su desempeño (NO por materia).
  Se eligió resumen (no detalle por materia) para no inflar el Sheet con snapshots semanales.
- **🔑 Programa vigente (corregido 2026-06-12):** la nota se amarra al programa por
  `EKU100400.STRUCTURE_ID`, que **es el `program_id`** (validado con el alumno trasladado
  29649). El JOIN final exige `ea.program_id = STRUCTURE_ID`, así que **solo cuentan las
  materias del programa vigente** — antes el JOIN era solo por `user_id` e inflaba con módulos
  del programa del que fue trasladado. (El catálogo `EKU100415.INTEGRATION_PROGRAM_ID` viene NULL.)
- **🔑 "Cursado" vs "no cursado" (corregido 2026-06-12):** `FINAL_NOTE_VALUE` es STRING.
  `value > 0` = **cursado** (tiene nota real); `value ≤ 0` o NULL (en la data el placeholder de
  "no iniciado" es `"0"`, no NULL) = **no cursado → se excluye**. Antes se contaba todo lo que
  tuviera nota, así que los módulos en `"0"` (no iniciados) inflaban `modulos_reprobados`.
- **"Aprobado" por umbral:** `value ≥ 3.0` = aprobado; `0 < value < 3.0` = reprobado. Se usa el
  **umbral 3.0**, no `FINAL_NOTE_APPROVE`. Limitación aceptada: un 0 "real" (entregó y sacó 0)
  se trata como no cursado, porque en Kuepa el 0 es el placeholder de "no iniciado".
- **"Activo":** se define con `academic_status_name` de `VKU10_student_info_current_program`
  (misma fuente que Asistencia) — incluye 'regular', 'nuevo', 'en riesgo de abandono',
  'solicitud de retiro', etc. (decisión de negocio: esos cuentan como activos).
- **Estado actual por materia (recuperaciones):** la CTE `desempeno_materia` colapsa cada
  materia (× programa) a un solo estado: `materia_aprobada = MAX(value ≥ 3.0)` y
  `nota_materia = MAX(value)` (mejor nota alcanzada). En Kuepa la nota final se **recalcula**:
  una materia sale reprobada y, tras recuperar, su mejor nota llega a ≥3.0. Como cada snapshot
  lee el estado vigente, `modulos_reprobados` **baja** cuando el estudiante recupera → el
  comparativo semana vs. semana lo muestra como **mejora** (atribuible al gestor).
  Por eso `aprobados + reprobados = cursados` exacto (sin doble conteo).
- **Caso de validación (29649, trasladado):** programa vigente Contabilidad y Finanzas →
  4 cursados / 1 aprobado / 3 reprobados, nota prom. 1.3 (con la lógica vieja salían 17/1/16).
- **Limitación (resuelta por el feed `Materias`):** como `Notas` es resumen, muestra *cuántos*
  módulos reprobó cada alumno pero no *cuáles*. El detalle por materia vive ahora en `Materias`.

### Materias (ranking de reprobación por asignatura) — query lista
Datasets `DVKU_SIS` + `DSKU_SIS` (mismas CTEs que `Notas`, solo cambia el grano del SELECT).
SQL en `queries/materias_reprobadas.sql`, pestaña destino `Materias`. Salida (1 fila por
**programa × materia**): `modalidad`, `program_name`, `materia`, `estudiantes_cursaron`,
`estudiantes_reprobaron`, `pct_reprobacion`, `nota_promedio`, `fecha_informe`,
`clave_registro` (= `programa|materia|fecha`, llave única n8n).
- **Para qué:** responde "**qué materias se reprueban más**" (acción curricular/pedagógica),
  no solo gestión 1-a-1. El dashboard re-agrega por materia sumando los programas del filtro.
- **Grano por programa (no solo materia):** lo conserva para que el filtro de programas del
  sidebar siga funcionando; los % se re-derivan de los conteos en el front.
- `HAVING estudiantes_reprobaron > 0`: solo entran al ranking materias con ≥1 reprobada.
- **"Activo" / recuperaciones / "cursado":** idéntica definición que `Notas` (coherencia).

> Nota: la lista de `program_id` monitoreados coincide entre las cuatro queries, así que
> el alcance de programas es consistente.

---

## 4. Diseño de la interfaz

Pestañas superiores (`st.tabs`), sin romper lo existente:

| Pestaña            | Contenido |
|--------------------|-----------|
| 🔌 **Conexión**    | El dashboard actual, idéntico (login + financiero). |
| 📉 **Ausentismo**  | ⏸️ **FUERA DEL AIRE** (pestaña retirada de la navegación, 2026-06-12). El feed v2 cambió a "días de falta consecutivos" pero `render_ausentismo()` aún usa `PORCENTAJE_ASISTENCIA` → generaba confusión. La función y su loader siguen en el código (sin cablear) para reactivarla tras reescribir el render al nuevo esquema. La señal `sig_asis` de Riesgo 360 quedó en pausa (`False`). |
| 📕 **Reprobación** | Tres bloques con copy explicativo en cada gráfica: (1) **¿quiénes?** estudiantes con reprobaciones por programa + distribución de severidad (1/2/3/4+ módulos); (2) **¿qué materias?** ranking de asignaturas más reprobadas — por **volumen** (nº de estudiantes) y por **dificultad** (% reprobación, mín. 5 cursaron) + tabla detalle (feed `Materias`); (3) tabla accionable por estudiante. |
| 🎯 **Riesgo 360**  | **Pestaña principal (default).** Gráfico de **combinaciones de riesgo más frecuentes** + métricas de señales + tabla **"Riesgo Múltiple"** (estudiantes con 2+ alertas: login + mora + ausentismo + reprobación). Es el centro del sistema: ver quiénes combinan alertas, no alertas sueltas. |

---

## 5. Decisiones tomadas

- Pipeline: **n8n semanal**, un nodo de query + pestaña nueva por alerta (no consultar BQ en vivo).
- Sesiones sin registrar (docentes): **panel operativo separado**, no se mezcla con el riesgo del estudiante.
- Navegación: **pestañas superiores**, preservando la vista actual intacta.

---

## 6. Estado de avance

### Fase 1 — Datos (lado n8n)
- [x] Ajustar query de Notas: agregar `CURRENT_DATE() AS fecha_informe` → en `queries/notas_reprobacion.sql`.
- [ ] ⏸️ Nodo `Asistencia`: EN PAUSA (feed v2 listo, pero la pestaña está fuera del aire — ver §4).
- [ ] Nodo n8n + pestaña `Notas` poblándose semanalmente (SQL en `queries/notas_reprobacion.sql`).
- [ ] **Nodo n8n + pestaña `Materias`** poblándose semanalmente (SQL en `queries/materias_reprobadas.sql`).
- [ ] Confirmar que los nodos activos corren en la misma ejecución (fechas alineadas).

### Fase 2 — Dashboard (código)
- [x] Loaders `load_asistencia()` / `load_notas()` / `load_materias()` (leen pestañas, parsean fecha).
- [x] Envolver la página actual en `st.tabs` bajo `with tab0:` ("🔌 Conexión" intacta).
- [x] Pestaña 🎯 Riesgo 360 (`render_riesgo360`): señales login+mora+reprobación + tabla Riesgo Múltiple.
- [x] Probado en vivo (carga datos; usa snapshot más cercano con `_snapshot_fecha` si hay drift de fechas).
- [x] **Reprobación reforzada (2026-06-12):** 3 bloques con copy explicativo (`_chart_help`):
  (1) por programa + distribución de severidad (1/2/3/4+ módulos); (2) **ranking de materias**
  por volumen y por % de dificultad + tabla detalle (feed `Materias`, degrada con aviso si vacío);
  (3) tabla accionable por estudiante.
- [x] **Ausentismo retirado del aire (2026-06-12):** pestaña fuera de `st.tabs`, señal `sig_asis`
  de 360 en pausa. `render_ausentismo()` / `load_asistencia()` quedan en el código sin cablear.
- [ ] Reescribir `render_ausentismo()` al esquema v2 (días de falta) y reactivar pestaña + señal 360.
- [ ] Comparativos/eficacia week-over-week en las pestañas nuevas (v1 muestra fecha actual).

Notas de implementación: el bloque de contenido original quedó indentado +4 dentro de
`with tab0:` (sin reescribirlo). Las pestañas nuevas filtran por `fecha_principal` y por el
filtro de `programas` del sidebar. El gestor para Riesgo 360 sale de `df_principal` (Hoja 1).

---

## 7. Referencias rápidas de código

- App: `dashboard_alertas.py` (~981 líneas, líneas muy largas).
- Carga de datos: `load_historical_data()` (~L266).
- Paleta/ranks de alertas: `ALERT_RANK`, `ALERT_COLORS`, `ALERT_ORDER` (~L228–246).
- Estado financiero: `FIN_ORDER`, `FIN_COLORS`, `FIN_RANK` (~L250–259).
- Matriz de riesgo (login×financiero): ~L669.
- Tabla "Doble Riesgo" (a evolucionar → Riesgo Múltiple): ~L744.
- CSS / identidad visual: ~L16–225.
- Queries fuente de los nodos n8n: carpeta `queries/` (ver su `README.md`).
