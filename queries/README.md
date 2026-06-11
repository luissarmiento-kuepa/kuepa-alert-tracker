# Queries BigQuery — nodos n8n

SQL fuente de cada tipo de alerta. Cada archivo corresponde a **un nodo de query** en el
workflow semanal de n8n, que escribe el resultado a una pestaña del Google Sheet.

| Archivo | Pestaña destino | Estado | Dataset |
|---------|-----------------|--------|---------|
| `login_conexion.sql` | `Hoja 1` | EN PROD (no incluida aquí; vive en n8n) | — |
| `asistencia_ausentismo.sql` | `Asistencia` | Lista para nodo nuevo | `DVKU_SIS` |
| `notas_reprobacion.sql` | `Notas` | Lista para nodo nuevo | `DVKU_SIS` + `DSKU_SIS` |

**Reglas:**
- Los 3 nodos deben correr en la **misma ejecución semanal** para que las
  `fecha_informe` coincidan (es la llave del cruce 360 en el dashboard).
- Si editas una query aquí, actualiza también el nodo en n8n y, si cambian columnas,
  `SISTEMA_ALERTAS.md` §3 y el `load_historical_data()` del dashboard.
- Lista de `program_id` monitoreados: mantener idéntica entre las tres queries.

Ver contexto completo en `../SISTEMA_ALERTAS.md`.
