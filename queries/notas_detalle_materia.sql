-- ============================================================
-- ALERTA: REPROBACIÓN — DETALLE ESTUDIANTE × MATERIA
-- Pestaña destino en Sheet: "NotasDetalle"
-- Grano: 1 fila por ESTUDIANTE × MATERIA REPROBADA (de su programa vigente).
--
-- Habilita el drill-down del dashboard: "¿QUIÉNES reprobaron esta materia?".
-- Mismas CTEs y misma lógica corregida que notas_reprobacion.sql / materias_reprobadas.sql:
--   1) PROGRAMA VIGENTE: nota ↔ programa por EKU100400.STRUCTURE_ID = program_id.
--   2) CURSADO: FINAL_NOTE_VALUE (STRING) > 0 ; aprobado = value >= 3.0.
-- Aquí SOLO salen las materias REPROBADAS (materia_aprobada = 0), así el volumen
-- queda acotado (no es 1 fila por cada materia cursada, solo las reprobadas).
-- ============================================================

WITH estudiantes_activos AS (
  SELECT
    user_id,
    user_incremental,
    user_full_name,
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

notas_cursadas AS (
  SELECT
    cn.USER_ID                                   AS user_id,
    cn.STRUCTURE_ID                              AS program_id_nota,
    cat.NAME                                     AS subject_name,
    SAFE_CAST(s.FINAL_NOTE_VALUE AS FLOAT64)     AS value
  FROM `potent-poetry-284019.DSKU_SIS.EKU100401_subjects` AS s
  INNER JOIN `potent-poetry-284019.DSKU_SIS.EKU100400_centralize_final_note` AS cn
    ON s.__CENTRALIZEFINALNOTES = cn._ID
  LEFT JOIN `potent-poetry-284019.DSKU_SIS.EKU100415_subject` AS cat
    ON cat._ID = s.SUBJECT_ID
  WHERE SAFE_CAST(s.FINAL_NOTE_VALUE AS FLOAT64) > 0
),

desempeno_materia AS (
  SELECT
    user_id,
    program_id_nota,
    subject_name,
    MAX(CASE WHEN value >= 3.0 THEN 1 ELSE 0 END) AS materia_aprobada,
    MAX(value)                                    AS nota_materia
  FROM notas_cursadas
  GROUP BY user_id, program_id_nota, subject_name
)

-- RESULTADO: 1 fila por estudiante × materia REPROBADA (programa vigente)
SELECT
  ea.user_incremental,
  ea.user_full_name,
  CASE
    WHEN ea.program_name LIKE '%Bachillerato%' THEN 'Bachillerato'
    ELSE 'Técnico'
  END AS modalidad,
  ea.program_name,
  dm.subject_name              AS materia,
  ROUND(dm.nota_materia, 2)    AS nota_materia,

  CURRENT_DATE() AS fecha_informe,
  CONCAT(CAST(ea.user_incremental AS STRING), '|', dm.subject_name, '|', CAST(CURRENT_DATE() AS STRING)) AS clave_registro

FROM estudiantes_activos AS ea
INNER JOIN desempeno_materia AS dm
  ON ea.user_id = dm.user_id
  AND ea.program_id = dm.program_id_nota   -- 🔑 solo materias del programa vigente
WHERE dm.materia_aprobada = 0              -- 🔑 solo materias REPROBADAS
  AND dm.subject_name IS NOT NULL
ORDER BY
  ea.program_name,
  dm.subject_name,
  dm.nota_materia,
  ea.user_incremental;
