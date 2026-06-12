-- ============================================================
-- ALERTA: AUSENTISMO (por DÍAS DE FALTA CONSECUTIVOS hasta la fecha de corte)
-- Pestaña destino en Sheet: "Asistencia"
-- Grano: 1 fila por ESTUDIANTE (su racha de faltas consecutivas más reciente).
--
-- Lógica (dos escalas según programa):
--   TÉCNICO:        Sin alerta 0-1 · Alerta 1: 2 · Alerta 3: 3-4 · Alerta 5: >=5
--   BACHILLERATO+:  Sin alerta 0-1 · Alerta 1: 2-4 · Alerta 2: 5-6 · Alerta 3: 7-10 · Alerta 4: >10
--   Bachillerato FLEX: EXCLUIDO (asistencia no obligatoria).
--
-- "Día" = jornada de clase (agrupa todas las materias del día). Si asistió a AL MENOS
--   una clase ese día => presente (no rompe nada; "presente gana").
-- La racha NO se acota al módulo vigente: cuenta los días de clase consecutivos más
--   recientes con falta, hasta la fecha de corte (así Bachillerato puede llegar a >10).
-- Sesiones sin marcar (ATTENDANCE NULL / sin fila) se IGNORAN: no rompen la racha.
-- ATTENDANCE: 1=asistió, 0=tarde (ambos = presente), -1=no asistió (falta).
-- Snapshot: FECHA_REPORTE = CURRENT_DATE(). Llave n8n: clave_registro (estudiante|fecha).
-- Dataset: DVKU_SIS
-- ============================================================

WITH
estudiantes_activos AS (
  SELECT
    user_id,
    user_incremental,
    user_full_name AS NOMBRE_ESTUDIANTE,
    program_id,
    program_name,
    academic_status_name AS ESTADO_ACADEMICO,
    CASE
      WHEN program_id IN ("60d2653f86a7940eab68ad80",   -- Bachillerato Plus Online
                          "60d2657686a7940eab68ad81")   -- Bachillerato Plus Onsite
      THEN 'Bachillerato'
      ELSE 'Técnico'
    END AS tipo_ausentismo
  FROM `potent-poetry-284019.DVKU_SIS.VKU10_student_info_current_program`
  WHERE program_id IN (
      -- TÉCNICOS
      "6810ff2fba8d1305eb777ef0", "678e56f347a9c4130b4e4ac7", "67bbbc326b1d000fb530abb5",
      "67bc7d70d15f4c0fb4a482c1", "686c3f4dd09df00ac3d14ae2", "686c479ad09df00ac3d1959a",
      "670e626ab638550218b827c0", "64b847111c6495204eb3e119", "6279265fdb9de50f6405ad9d",
      "627d48d06c7678122e01d1b6", "629e7a7b3289d80f7d3d575e", "65eb4271441c110f0a76db73",
      "65eb45c11592a80f09decf06", "65eb45e58372400f07c0691e", "66fecda90cc4330faddd4409",
      -- BACHILLERATO PLUS (Flex EXCLUIDO a propósito)
      "60d2653f86a7940eab68ad80", "60d2657686a7940eab68ad81"
    )
    AND LOWER(academic_status_name) IN (
      'regular', 'regular en verificación', 'nuevo', 'en riesgo de abandono', 'solicitud de retiro'
    )
  QUALIFY ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY program_id) = 1
),

dias AS (
  -- Un registro por estudiante x día de clase. "Presente gana": si asistió a alguna
  -- clase ese día, el día es presente. Solo días con marca real (1/0/-1).
  SELECT
    ea.user_incremental,
    CAST(TIMESTAMP(au.SESSION) AS DATE) AS dia,
    MAX(CASE WHEN au.ATTENDANCE IN (1, 0) THEN 1 ELSE 0 END) AS hubo_presente
  FROM estudiantes_activos AS ea
  JOIN `potent-poetry-284019.DVKU_SIS.VKU10_attendance_users` AS au
    ON ea.user_incremental = au.INCREMENTAL
  WHERE au.ATTENDANCE IN (1, 0, -1)   -- ignora sesiones sin marcar (NULL / sin fila)
    AND CAST(TIMESTAMP(au.SESSION) AS DATE) <= CURRENT_DATE()
  GROUP BY ea.user_incremental, dia
),

ordenados AS (
  SELECT
    user_incremental,
    hubo_presente,
    ROW_NUMBER() OVER (PARTITION BY user_incremental ORDER BY dia DESC) AS rn
  FROM dias
),

racha AS (
  -- Días consecutivos de falta más recientes = hasta el primer día presente (rn más bajo).
  -- Si nunca hubo día presente => todos sus días son falta (COUNT(*)).
  SELECT
    user_incremental,
    COALESCE(MIN(CASE WHEN hubo_presente = 1 THEN rn END) - 1, COUNT(*)) AS dias_falta_consecutivos
  FROM ordenados
  GROUP BY user_incremental
)

SELECT
  ea.user_incremental,
  ea.NOMBRE_ESTUDIANTE,
  ea.ESTADO_ACADEMICO,
  ea.program_name AS PROGRAMA,
  ea.tipo_ausentismo,
  r.dias_falta_consecutivos,
  -- NIVEL según escala por tipo de programa
  CASE
    WHEN ea.tipo_ausentismo = 'Bachillerato' THEN
      CASE
        WHEN r.dias_falta_consecutivos <= 1 THEN 'SIN ALERTA'
        WHEN r.dias_falta_consecutivos BETWEEN 2 AND 4 THEN 'ALERTA 1'
        WHEN r.dias_falta_consecutivos BETWEEN 5 AND 6 THEN 'ALERTA 2'
        WHEN r.dias_falta_consecutivos BETWEEN 7 AND 10 THEN 'ALERTA 3'
        ELSE 'ALERTA 4'
      END
    ELSE  -- Técnico
      CASE
        WHEN r.dias_falta_consecutivos <= 1 THEN 'SIN ALERTA'
        WHEN r.dias_falta_consecutivos = 2 THEN 'ALERTA 1'
        WHEN r.dias_falta_consecutivos BETWEEN 3 AND 4 THEN 'ALERTA 3'
        ELSE 'ALERTA 5'
      END
  END AS NIVEL_ALERTA,
  -- gravedad numérica 0..5 (color/orden en el dashboard; mayor = peor)
  CASE
    WHEN ea.tipo_ausentismo = 'Bachillerato' THEN
      CASE
        WHEN r.dias_falta_consecutivos <= 1 THEN 0
        WHEN r.dias_falta_consecutivos BETWEEN 2 AND 4 THEN 1
        WHEN r.dias_falta_consecutivos BETWEEN 5 AND 6 THEN 2
        WHEN r.dias_falta_consecutivos BETWEEN 7 AND 10 THEN 3
        ELSE 4
      END
    ELSE
      CASE
        WHEN r.dias_falta_consecutivos <= 1 THEN 0
        WHEN r.dias_falta_consecutivos = 2 THEN 1
        WHEN r.dias_falta_consecutivos BETWEEN 3 AND 4 THEN 3
        ELSE 5
      END
  END AS gravedad_ausentismo,
  CURRENT_DATE() AS FECHA_REPORTE,
  CONCAT(CAST(ea.user_incremental AS STRING), '|', CAST(CURRENT_DATE() AS STRING)) AS clave_registro
FROM racha AS r
JOIN estudiantes_activos AS ea
  ON ea.user_incremental = r.user_incremental
ORDER BY gravedad_ausentismo DESC, r.dias_falta_consecutivos DESC;
