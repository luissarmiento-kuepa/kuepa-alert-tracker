# Queries BigQuery — nodos n8n

SQL fuente de cada tipo de alerta. Cada archivo corresponde a **un nodo de query** en el
workflow semanal de n8n, que escribe el resultado a una pestaña del Google Sheet.

| Archivo | Pestaña destino | Estado | Dataset |
|---------|-----------------|--------|---------|
| `login_conexion.sql` | `Hoja 1` | EN PROD (no incluida aquí; vive en n8n) | — |
| `asistencia_ausentismo.sql` | `Asistencia` | ⏸️ En revisión — pestaña FUERA DEL AIRE en el dashboard | `DVKU_SIS` |
| `notas_reprobacion.sql` | `Notas` | Lista para nodo nuevo (resumen por estudiante) | `DVKU_SIS` + `DSKU_SIS` |
| `materias_reprobadas.sql` | `Materias` | Lista para nodo nuevo (ranking por materia) | `DVKU_SIS` + `DSKU_SIS` |

`Notas` y `Materias` salen de las **mismas CTEs** (estudiantes activos + estado por materia),
solo cambia el grano del SELECT final: `Notas` = 1 fila por estudiante; `Materias` = 1 fila
por programa × materia (para "qué materias se reprueban más"). En n8n: `clave_registro` como
columna de match (`Append or Update Row`) — en `Materias` es `programa|materia|fecha`.

**Reglas:**
- Los nodos deben correr en la **misma ejecución semanal** para que las
  `fecha_informe` coincidan (es la llave del cruce 360 en el dashboard).
- Si editas una query aquí, actualiza también el nodo en n8n y, si cambian columnas,
  `SISTEMA_ALERTAS.md` §3 y el `load_historical_data()` del dashboard.
- Lista de `program_id` monitoreados: mantener idéntica entre las tres queries.

Ver contexto completo en `../SISTEMA_ALERTAS.md`.
