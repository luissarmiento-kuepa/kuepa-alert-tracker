-- ============================================================
-- ALERTA: AUSENTISMO (asistencia de módulo vigente)
-- Pestaña destino en Sheet: "Asistencia"
-- Grano: 1 fila por estudiante x materia (módulo vigente)
-- Propósito: detectar estudiantes con baja asistencia E identificar
--            sesiones sin registrar por profesores.
-- Snapshot: usa FECHA_REPORTE = CURRENT_DATE().
-- Dataset: DVKU_SIS
-- ============================================================

WITH
estudiantes_activos AS (
  -- Trae solo estudiantes en los programas monitorizados e incluye el ESTADO
  SELECT
    user_id,
    user_incremental,
    user_full_name AS PROFILE_FULL_NAME,
    program_id,
    program_name,
    academic_status_name AS ESTADO_ACADEMICO
  FROM `potent-poetry-284019.DVKU_SIS.VKU10_student_info_current_program`
  WHERE
    program_id IN (
      "6810ff2fba8d1305eb777ef0",  -- T.L en Auxiliar de Mercadeo y Ventas
      "678e56f347a9c4130b4e4ac7",  -- T.L. en Contabilidad y Finanzas
      "67bbbc326b1d000fb530abb5",  -- Técnico Laboral en Recursos Humanos y Riesgo Laboral
      "67bc7d70d15f4c0fb4a482c1",  -- Técnico Laboral en Programación de Sistemas de Información
      "686c3f4dd09df00ac3d14ae2",  -- T.L en Servicios Turisticos y Hoteleros
      "686c479ad09df00ac3d1959a",  -- T.L en Procesamiento y Digitación de Datos
      "670e626ab638550218b827c0",  -- T.L. en Auxiliar Administrativo
      "64b847111c6495204eb3e119",  -- Técnico laboral en servicios turísticos y hoteleros
      "6279265fdb9de50f6405ad9d",  -- Técnico Laboral en Auxiliar de Mercadeo y Ventas
      "627d48d06c7678122e01d1b6",  -- Técnico Laboral en Auxiliar Administrativo
      "629e7a7b3289d80f7d3d575e",  -- Técnico laboral en procesamiento de datos
      "65eb4271441c110f0a76db73",  -- Técnico Laboral en Desarrollo de Software
      "65eb45c11592a80f09decf06",  -- Técnico Laboral Auxiliar en Recursos Humanos y Riesgo Laboral
      "65eb45e58372400f07c0691e",  -- Técnico Laboral Auxiliar en Recursos Humanos
      "66fecda90cc4330faddd4409",  -- Inactivo T.L. en Auxiliar de Mercadeo y Venta
      "60d2650e86a7940eab68ad7f",  -- Bachillerato Flex
      "60d2653f86a7940eab68ad80",  -- Bachillerato Plus Online
      "60d2657686a7940eab68ad81"   -- Bachillerato Plus Onsite
    )
    -- Solo estudiantes ACTIVOS (mismo abanico de estados que la query de Notas)
    AND LOWER(academic_status_name) IN (
      'regular',
      'regular en verificación',
      'nuevo',
      'en riesgo de abandono',
      'solicitud de retiro'
    )
  QUALIFY ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY program_id) = 1
),
grupo_vigente AS (
  -- Identifica el grupo académico vigente e incluye el ESTADO
  SELECT DISTINCT
    ea.user_id,
    ea.user_incremental,
    ea.PROFILE_FULL_NAME,
    ea.program_name,
    ea.ESTADO_ACADEMICO,
    as_ses.GROUP,
    as_ses.SUBJECT,
    as_ses.LEVEL,
    as_ses.PROGRAM_STRING,
    as_ses.LEVEL_STRING,
    as_ses.GROUP_STRING,
    as_ses.SUBJECT_STRING,
    CAST(TIMESTAMP(as_ses.START_DATE_GROUP) AS DATE) AS START_DATE,
    CAST(TIMESTAMP(as_ses.END_DATE_GROUP) AS DATE) AS END_DATE
  FROM estudiantes_activos AS ea
  LEFT JOIN `potent-poetry-284019.DVKU_SIS.VKU10_attendance_users` AS au
    ON ea.user_incremental = au.INCREMENTAL
  LEFT JOIN
    `potent-poetry-284019.DVKU_SIS.VKU10_attendance_sessions` AS as_ses
    ON
      au.ALLIANCE = as_ses.ALLIANCE
      AND au.`GROUP` = as_ses.`GROUP`
      AND au.SECTION = as_ses.SECTION
      AND au.PERIOD = as_ses.PERIOD
      AND au.PROGRAM = as_ses.PROGRAM
      AND au.SUBJECT = as_ses.SUBJECT
      AND au.LEVEL = as_ses.LEVEL
  WHERE
    CAST(TIMESTAMP(as_ses.START_DATE_GROUP) AS DATE) <= CURRENT_DATE()
    AND CAST(TIMESTAMP(as_ses.END_DATE_GROUP) AS DATE) >= CURRENT_DATE()
)
SELECT
  gv.user_incremental,
  gv.PROFILE_FULL_NAME AS NOMBRE_ESTUDIANTE,
  gv.ESTADO_ACADEMICO,
  gv.program_name AS PROGRAMA,
  gv.LEVEL_STRING AS NIVEL,
  gv.GROUP_STRING AS GRUPO,
  gv.SUBJECT_STRING AS ASIGNATURA,
  gv.START_DATE,
  gv.END_DATE,

  -- SESIONES PROGRAMADAS
  COUNT(DISTINCT CAST(TIMESTAMP(as_ses.SESSION) AS DATE))
    AS TOTAL_SESIONES_PROGRAMADAS,

  -- SESIONES CON REGISTRO DE ASISTENCIA
  COUNT(DISTINCT CASE WHEN au.INCREMENTAL IS NOT NULL THEN CAST(TIMESTAMP(au.SESSION) AS DATE) END)
    AS TOTAL_SESIONES_REGISTRADAS,

  -- SESIONES SIN REGISTRAR POR PROFESORES
  COUNT(DISTINCT CAST(TIMESTAMP(as_ses.SESSION) AS DATE))
    - COUNT(DISTINCT CASE WHEN au.INCREMENTAL IS NOT NULL THEN CAST(TIMESTAMP(au.SESSION) AS DATE) END)
    AS SESIONES_SIN_REGISTRAR,

  -- DESGLOSE DE ASISTENCIA
  COUNT(DISTINCT CASE WHEN au.ATTENDANCE = 1 THEN CAST(TIMESTAMP(au.SESSION) AS DATE) END)
    AS SESIONES_ASISTIO,
  COUNT(DISTINCT CASE WHEN au.ATTENDANCE = -1 THEN CAST(TIMESTAMP(au.SESSION) AS DATE) END)
    AS SESIONES_NO_ASISTIO,
  COUNT(DISTINCT CASE WHEN au.ATTENDANCE = 0 THEN CAST(TIMESTAMP(au.SESSION) AS DATE) END)
    AS SESIONES_TARDE,
  COUNT(DISTINCT CASE WHEN au.ATTENDANCE IS NULL THEN CAST(TIMESTAMP(au.SESSION) AS DATE) END)
    AS SESIONES_PENDIENTE,

  -- PORCENTAJE DE ASISTENCIA
  ROUND(
    100.0
    * COUNT(DISTINCT CASE WHEN au.ATTENDANCE = 1 THEN CAST(TIMESTAMP(au.SESSION) AS DATE) END)
    / NULLIF(COUNT(DISTINCT CASE WHEN au.INCREMENTAL IS NOT NULL THEN CAST(TIMESTAMP(au.SESSION) AS DATE) END), 0),
    2
  ) AS PORCENTAJE_ASISTENCIA,

  -- NIVEL DE ALERTA
  CASE
    WHEN
      ROUND(100.0 * COUNT(DISTINCT CASE WHEN au.ATTENDANCE = 1 THEN CAST(TIMESTAMP(au.SESSION) AS DATE) END) / NULLIF(COUNT(DISTINCT CASE WHEN au.INCREMENTAL IS NOT NULL THEN CAST(TIMESTAMP(au.SESSION) AS DATE) END), 0), 2) < 50
      THEN '🔴 CRÍTICO'
    WHEN
      ROUND(100.0 * COUNT(DISTINCT CASE WHEN au.ATTENDANCE = 1 THEN CAST(TIMESTAMP(au.SESSION) AS DATE) END) / NULLIF(COUNT(DISTINCT CASE WHEN au.INCREMENTAL IS NOT NULL THEN CAST(TIMESTAMP(au.SESSION) AS DATE) END), 0), 2) < 70
      THEN '🟡 ALERTA'
    WHEN
      ROUND(100.0 * COUNT(DISTINCT CASE WHEN au.ATTENDANCE = 1 THEN CAST(TIMESTAMP(au.SESSION) AS DATE) END) / NULLIF(COUNT(DISTINCT CASE WHEN au.INCREMENTAL IS NOT NULL THEN CAST(TIMESTAMP(au.SESSION) AS DATE) END), 0), 2) < 85
      THEN '🟠 BAJO'
    ELSE '🟢 NORMAL'
  END AS NIVEL_ALERTA,

  -- ALERTA SOBRE SESIONES SIN REGISTRAR (operativa, equipo docente)
  CASE
    WHEN COUNT(DISTINCT CAST(TIMESTAMP(as_ses.SESSION) AS DATE))
      - COUNT(DISTINCT CASE WHEN au.INCREMENTAL IS NOT NULL THEN CAST(TIMESTAMP(au.SESSION) AS DATE) END) > 0
      THEN '⚠️ PENDIENTE REGISTRO'
    ELSE '✅ TODO REGISTRADO'
  END AS ESTADO_REGISTRO_PROFESORES,

  CURRENT_DATE() AS FECHA_REPORTE,

  -- LLAVE ÚNICA para "Append or Update" en n8n (estudiante | materia | fecha snapshot)
  -- Incluye la fecha => cada semana inserta fila nueva (no sobreescribe el histórico).
  CONCAT(CAST(gv.user_incremental AS STRING), '|', gv.SUBJECT_STRING, '|', CAST(CURRENT_DATE() AS STRING))
    AS clave_registro
FROM grupo_vigente AS gv
LEFT JOIN `potent-poetry-284019.DVKU_SIS.VKU10_attendance_users` AS au
  ON
    gv.user_incremental = au.INCREMENTAL
    AND gv.GROUP = au.`GROUP`
    AND gv.SUBJECT = au.SUBJECT
    AND gv.LEVEL = au.LEVEL
    AND CAST(TIMESTAMP(au.SESSION) AS DATE) BETWEEN gv.START_DATE AND CURRENT_DATE()
LEFT JOIN `potent-poetry-284019.DVKU_SIS.VKU10_attendance_sessions` AS as_ses
  ON
    gv.GROUP = as_ses.`GROUP`
    AND gv.SUBJECT = as_ses.SUBJECT
    AND gv.LEVEL = as_ses.LEVEL
    AND CAST(TIMESTAMP(as_ses.SESSION) AS DATE) BETWEEN gv.START_DATE AND CURRENT_DATE()
GROUP BY
  gv.user_incremental,
  gv.PROFILE_FULL_NAME,
  gv.ESTADO_ACADEMICO,
  gv.program_name,
  gv.LEVEL_STRING,
  gv.GROUP_STRING,
  gv.SUBJECT_STRING,
  gv.START_DATE,
  gv.END_DATE
HAVING
  PORCENTAJE_ASISTENCIA < 85
  OR SESIONES_SIN_REGISTRAR > 0
ORDER BY
  ESTADO_REGISTRO_PROFESORES DESC,
  PORCENTAJE_ASISTENCIA ASC,
  gv.program_name,
  gv.ESTADO_ACADEMICO;
