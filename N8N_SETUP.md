# Setup de Nodos n8n para Alertas Kuepa

## Workflow semanal: estructura general

El workflow debe ejecutarse **semanalmente** (trigger: schedule, p. ej. lunes 00:05 UTC) con:
- **3 nodos de Query BigQuery en paralelo:** Notas, Materias, NotasDetalle.
- **3 nodos Google Sheets en paralelo:** población de pestañas.
- Mismo timestamp `CURRENT_DATE()` en las tres queries → feeds alineados por `fecha_informe`.

Estructura recomendada:
```
[Trigger semanal] → [Fan-out a 3 ramas]
    ├─ [BQ Query: Notas] → [Google Sheets: Notas]
    ├─ [BQ Query: Materias] → [Google Sheets: Materias]
    └─ [BQ Query: NotasDetalle] → [Google Sheets: NotasDetalle]
```

---

## Parámetros comunes (todos los nodos)

### Credenciales BigQuery
Todos los nodos BigQuery comparten la misma conexión:
- **Auth type:** Service Account Key JSON
- **Credencial n8n:** (la misma que ya usan los nodos existentes, p. ej. `GCP BigQuery Kuepa` o similar).

### Credenciales Google Sheets
Todos los nodos Sheets comparten la misma conexión:
- **Auth type:** Google OAuth 2.0
- **Credencial n8n:** (la misma que ya usan, p. ej. `Google Sheets Kuepa`).
- **Spreadsheet ID:** `1hPWt0oBdbJTuIEbkFh1G9V1NDXh_ADKUt3OqJPocxaU` (constante).

---

## Nodo 1: Query BigQuery → Notas

### BigQuery Query Node
```
Name: "BQ Query — Notas"
Operation: Execute Query
```

**SQL:**
```sql
-- Contenido íntegro de queries/notas_reprobacion.sql
-- (cópialo exactamente, incluyendo los comentarios y CTEs)
```

**Results:**
- Output Format: JSON
- Raw: OFF

### Google Sheets Node (Notas)
```
Name: "Sheets — Notas"
Operation: Append or Update Row
Spreadsheet: 1hPWt0oBdbJTuIEbkFh1G9V1NDXh_ADKUt3OqJPocxaU
Worksheet: Notas (o "NOTAS", depende del nombre exacto en el Sheet)
Column to match on: clave_registro
Mapping: Map Automatically
```

**Configuración importante:**
- El nombre de la pestaña debe coincidir exactamente (case-sensitive en el Sheet, pero n8n lo tolera con variantes menores).
- Headers esperados (fila 1 del Sheet): `user_incremental`, `user_full_name`, `modalidad`, `program_name`, `modulos_cursados`, `modulos_aprobados`, `modulos_reprobados`, `nota_promedio`, `fecha_informe`, `clave_registro`.
- `clave_registro` debe ser única: es la llave de "update or append".

---

## Nodo 2: Query BigQuery → Materias

### BigQuery Query Node
```
Name: "BQ Query — Materias"
Operation: Execute Query
```

**SQL:**
```sql
-- Contenido íntegro de queries/materias_reprobadas.sql
```

### Google Sheets Node (Materias)
```
Name: "Sheets — Materias"
Operation: Append or Update Row
Spreadsheet: 1hPWt0oBdbJTuIEbkFh1G9V1NDXh_ADKUt3OqJPocxaU
Worksheet: Materias
Column to match on: clave_registro
Mapping: Map Automatically
```

**Configuración importante:**
- Headers esperados: `modalidad`, `program_name`, `materia`, `estudiantes_cursaron`, `estudiantes_reprobaron`, `pct_reprobacion`, `nota_promedio`, `fecha_informe`, `clave_registro`.
- `clave_registro` = `programa|materia|fecha`.

---

## Nodo 3: Query BigQuery → NotasDetalle ⭐ NUEVO

### BigQuery Query Node
```
Name: "BQ Query — NotasDetalle"
Operation: Execute Query
```

**SQL:**
```sql
-- Contenido íntegro de queries/notas_detalle_materia.sql
```

### Google Sheets Node (NotasDetalle)
```
Name: "Sheets — NotasDetalle"
Operation: Append or Update Row
Spreadsheet: 1hPWt0oBdbJTuIEbkFh1G9V1NDXh_ADKUt3OqJPocxaU
Worksheet: NotasDetalle
Column to match on: clave_registro
Mapping: Map Automatically
```

**Configuración importante:**
- **Pestaña debe existir previamente** en el Sheet con headers exactos en fila 1 (ver Sección "Setup del Sheet" abajo).
- Headers esperados: `user_incremental`, `user_full_name`, `modalidad`, `program_name`, `materia`, `nota_materia`, `fecha_informe`, `clave_registro`.
- `clave_registro` = `estudiante|materia|fecha`.

---

## Setup del Sheet: Crear pestañas y headers

### Pestaña "Notas"
```
user_incremental | user_full_name | modalidad | program_name | modulos_cursados | modulos_aprobados | modulos_reprobados | nota_promedio | fecha_informe | clave_registro
```
(pegado exacto, sin espacios extras, sin tildes adicionales)

### Pestaña "Materias"
```
modalidad | program_name | materia | estudiantes_cursaron | estudiantes_reprobaron | pct_reprobacion | nota_promedio | fecha_informe | clave_registro
```

### Pestaña "NotasDetalle" ⭐ NUEVO
```
user_incremental | user_full_name | modalidad | program_name | materia | nota_materia | fecha_informe | clave_registro
```

**Pasos en Google Sheets:**
1. Abre la hoja.
2. Para cada pestaña nueva (o si existe vacía):
   - Clic derecho → "Insertar 1 hoja" → nombre exacto (p. ej., "NotasDetalle").
   - En celda A1, pegado de los headers (usa Tab entre columnas).
   - **Guarda** (Ctrl+S).

---

## Testing y Validación

### Paso 1: Probar cada nodo por separado
1. En n8n, edita el workflow.
2. Selecciona el nodo BigQuery → "Test step" (botón de jugar).
3. Verifica que la query retorne datos (expandir JSON output).
4. Verifica que los nombres de columnas coincidan exactamente.

### Paso 2: Probar el nodo Sheets
1. Selecciona el nodo Google Sheets correspondiente.
2. "Test step" → debería escribir/actualizar 1-2 filas de prueba.
3. Ve al Sheet → refresca → verifica que los datos llegaron.

### Paso 3: Prueba de ejecución completa (dry run)
1. Guarda el workflow.
2. Clic en "Execute workflow" (botón play superior).
3. Espera a que complete (debería escribir en los 3 Sheets).
4. Verifica que las 3 pestañas tengan datos y `fecha_informe` sea coherente.

### Paso 4: Validación en el dashboard
1. En `dashboard_alertas.py`, ejecuta localmente:
   ```bash
   streamlit run dashboard_alertas.py
   ```
2. Ve a pestaña 📕 **Reprobación**.
3. Métricas y gráficas deben cargar datos de `df_notas_all` y `df_mat_all`.
4. Clic en una materia (en "Por volumen" o "Por dificultad") → debería desplegar lista de estudiantes (desde `df_det_all`).

### Paso 5: Agendar el workflow
1. En n8n, nodo "Trigger" → "Schedule".
2. **Frequency:** Weekly.
3. **Day of week:** Monday (o tu día preferido).
4. **Time:** 00:05 UTC (madrugada, antes que carguen tráfico).
5. Guarda y activa.

---

## Troubleshooting

### Error: "Column 'X' not found in the sheet"
- **Causa:** Header en el Sheet no coincide exactamente con el nombre en la query.
- **Solución:** Verifica el nombre en la query (SELECT), cópialo exacto (sin tildes extras, sin espacios), y pégalo en la fila 1 del Sheet.

### Error: "clave_registro is not unique" o duplicados en cada ejecución
- **Causa:** El nodo Sheets está usando "Append" en lugar de "Append or Update".
- **Solución:** Asegúrate de que "Operation" = "Append or Update Row" y "Column to match on" = "clave_registro".

### Datos no aparecen en el dashboard
- **Checklist:**
  1. ¿El Sheet tiene datos? (ve al Sheet, refresca, mira las pestañas).
  2. ¿Los headers en el Sheet coinciden exactamente con los nombres en la query?
  3. ¿La columna `fecha_informe` tiene valores (no vacíos)?
  4. ¿El formato de fecha es YYYY-MM-DD o DD/MM/YYYY? (el dashboard intenta detectarlo automáticamente).
  5. ¿El dashboard cache necesita refrescar? (Streamlit cachea 5 min; presiona `Ctrl+Shift+R` o espera).

### Workflow corre pero Sheets queda vacío
- **Causa:** BigQuery query retorna 0 filas (estudiantes activos = 0 en esa fecha).
- **Solución:** Verifica que la query SELECT pueda ejecutarse en BigQuery console (copia-pega directamente). Revisa que los `program_id` en la CTE `estudiantes_activos` sigan siendo válidos.

---

## Notas finales

- **Frecuencia:** semanal, todos los nodos en paralelo (misma timestamp → `fecha_informe` coherente).
- **Histórico:** cada ejecución escribe nuevas filas (no sobrescribe); el dashboard ve todos los snapshots.
- **Rollback:** si un nodo falla, los otros dos completarán solos (no es un problema, pero verás data parcial en el dashboard esa semana).
- **Optimización:** si el volumen crece y BQ queries lentean, consider índices o pre-cálculos en BQ (no en n8n).
