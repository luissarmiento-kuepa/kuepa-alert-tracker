-- ============================================================
-- ALERTA: REPROBACIÓN POR MATERIA (ranking de asignaturas)
-- Pestaña destino en Sheet: "Materias"
-- Grano: 1 fila por PROGRAMA × MATERIA (snapshot histórico).
--
-- Complementa a "Notas" (resumen por estudiante). Aquí la pregunta es
-- distinta: NO "cuántos módulos reprobó cada alumno", sino "QUÉ materias
-- son las que más se reprueban" → permite acción curricular/pedagógica,
-- no solo gestión 1-a-1. El dashboard suma estos conteos para el ranking.
--
-- Mantener el grano por programa (no solo por materia) permite que el
-- filtro de programas del dashboard siga funcionando: el front re-agrega.
-- ============================================================

WITH estudiantes_activos AS (
  -- Misma base y mismo abanico de "activo" que notas_reprobacion.sql (coherencia 360)
  SELECT
    user_id,
    user_incremental,
    program_id,
    program_name,
    academic_status_name
  FROM `potent-poetry-284019.DVKU_SIS.VKU10_student_info_current_program`
  WHERE program_id IN (
    "6810ff2fba8d1305eb777ef0", "678e56f347a9c4130b4e4ac7", "67bbbc326b1d000fb530abb5",
    "67bc7d70d15f4c0fb4a482c1", "686c3f4dd09df00ac3d14ae2", "686c479ad09df00ac3d1959a",
    "670e626ab638550218b827c0", "64b847111c6495204eb3e119", "6279265fdb9de50f6405ad9d",
    "627d48d06c7678122e01d1b6", "629e7a7b3289d80f7d3d575e", "65eb4271441c110f0a76db73",
    "65eb45c11592a80f09decf06", "65eb45e58372400f07c0691e", "66fecda90cc4330faddd4409",
    "60d2650e86a7940eab68ad7f", "60d2653f86a7940eab68ad80", "60d2657686a7940eab68ad81"
  )
  AND LOWER(academic_status_name) IN (
    'regular',
    'regular en verificación',
    'nuevo',
    'en riesgo de abandono',
    'solicitud de retiro'
  )
  QUALIFY ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY program_id) = 1
),

notas_historicas AS (
  -- Solo notas finales publicadas
  SELECT
    E100400.USER_ID AS user_id,
    E100415.name AS subject_name,
    SAFE_CAST(E100401.FINAL_NOTE_VALUE AS FLOAT64) AS value,
    E100401.FINAL_NOTE_APPROVE AS approved
  FROM `potent-poetry-284019.DSKU_SIS.EKU100401_subjects` AS E100401
  INNER JOIN `potent-poetry-284019.DSKU_SIS.EKU100400_centralize_final_note` AS E100400
    ON E100401.__CENTRALIZEFINALNOTES = E100400._ID
  LEFT JOIN `potent-poetry-284019.DSKU_SIS.EKU100415_subject` AS E100415
    ON E100415._ID = E100401.SUBJECT_ID
  WHERE E100401.FINAL_NOTE_VALUE IS NOT NULL
),

-- Estado actual por estudiante × materia (colapsa recuperaciones igual que en Notas:
-- si EXISTE alguna nota aprobatoria => la materia está aprobada/recuperada).
desempeno_materia AS (
  SELECT
    n.user_id,
    n.subject_name,
    MAX(CASE WHEN LOWER(TRIM(CAST(n.approved AS STRING))) IN
              ('true','1','yes','si','sí','aprobado','approved')
             THEN 1 ELSE 0 END) AS materia_aprobada,
    MAX(n.value) AS nota_materia
  FROM notas_historicas AS n
  GROUP BY n.user_id, n.subject_name
)

-- RESULTADO: una fila por programa × materia
SELECT
  CASE
    WHEN ea.program_name LIKE '%Bachillerato%' THEN 'Bachillerato'
    ELSE 'Técnico'
  END AS modalidad,
  ea.program_name,
  dm.subject_name AS materia,

  COUNT(DISTINCT ea.user_id)                                              AS estudiantes_cursaron,
  COUNT(DISTINCT IF(dm.materia_aprobada = 0, ea.user_id, NULL))           AS estudiantes_reprobaron,
  ROUND(SAFE_DIVIDE(
    COUNT(DISTINCT IF(dm.materia_aprobada = 0, ea.user_id, NULL)),
    COUNT(DISTINCT ea.user_id)) * 100, 1)                                 AS pct_reprobacion,
  ROUND(AVG(dm.nota_materia), 2)                                          AS nota_promedio,

  CURRENT_DATE() AS fecha_informe,
  CONCAT(ea.program_name, '|', dm.subject_name, '|', CAST(CURRENT_DATE() AS STRING)) AS clave_registro

FROM estudiantes_activos AS ea
INNER JOIN desempeno_materia AS dm
  ON ea.user_id = dm.user_id
WHERE dm.subject_name IS NOT NULL
GROUP BY
  modalidad,
  ea.program_name,
  dm.subject_name
HAVING estudiantes_reprobaron > 0   -- al ranking solo entran materias con al menos 1 reprobada
ORDER BY
  estudiantes_reprobaron DESC,
  pct_reprobacion DESC;
