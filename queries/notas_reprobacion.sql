-- ============================================================
-- ALERTA: REPROBACIÓN / DESEMPEÑO ACADÉMICO (OPTIMIZADA)
-- Pestaña destino en Sheet: "Notas"
-- Grano: 1 fila por ESTUDIANTE (resumen histórico).
-- ============================================================

WITH estudiantes_activos AS (
  -- 1. BASE LIMPIA: Estudiantes deduplicados y con su estado real ampliado
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
  -- 🚨 CORRECCIÓN CLAVE: El abanico completo de estados que equivalen a "Activo"
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
  -- 2. NOTAS: Traemos solo las notas publicadas
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

-- 2b. ESTADO ACTUAL POR MATERIA: colapsa todos los registros de una materia a un solo
-- estado. Si EXISTE alguna nota aprobatoria => materia aprobada (recuperada). Así, cuando
-- un estudiante recupera una materia, deja de contar como reprobada (la cuenta BAJA).
desempeno_materia AS (
  SELECT
    n.user_id,
    n.subject_name,
    MAX(CASE WHEN LOWER(TRIM(CAST(n.approved AS STRING))) IN
              ('true','1','yes','si','sí','aprobado','approved')
             THEN 1 ELSE 0 END) AS materia_aprobada,
    MAX(n.value) AS nota_materia   -- mejor nota alcanzada en la materia (refleja recuperación)
  FROM notas_historicas AS n
  GROUP BY n.user_id, n.subject_name
)

-- 3. RESULTADO FINAL: una fila por estudiante (estado actual de cada materia)
SELECT
  ea.user_incremental,
  ea.user_full_name,
  CASE
    WHEN ea.program_name LIKE '%Bachillerato%' THEN 'Bachillerato'
    ELSE 'Técnico'
  END AS modalidad,
  ea.program_name,

  COUNT(*)                          AS modulos_cursados,
  SUM(dm.materia_aprobada)          AS modulos_aprobados,
  SUM(1 - dm.materia_aprobada)      AS modulos_reprobados,
  ROUND(AVG(dm.nota_materia), 2)    AS nota_promedio,

  CURRENT_DATE() AS fecha_informe,
  CONCAT(CAST(ea.user_incremental AS STRING), '|', CAST(CURRENT_DATE() AS STRING)) AS clave_registro

FROM estudiantes_activos AS ea
INNER JOIN desempeno_materia AS dm
  ON ea.user_id = dm.user_id
GROUP BY
  ea.user_incremental,
  ea.user_full_name,
  modalidad,
  ea.program_name
ORDER BY
  modulos_reprobados DESC,
  ea.user_incremental;