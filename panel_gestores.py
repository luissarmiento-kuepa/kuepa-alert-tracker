"""Pestaña «Gestores»: desempeño diario de los gestores académicos de Bachillerato y Técnicos.

Fuente: `alertas_academicas.cola_gestores` (US), que el flujo n8n «cola_gestores_diaria» carga cada día a las
6:30 desde `potent-poetry-284019.DSKU_SIS.EKU101042_management_queue` (us-east1; la cola guarda solo el estado
actual de cada caso, por eso se fotografía a diario). Misma lógica que el panel HTML de SEGUIMIENTO 2026
(OTROS-INFORMES/bq/panel_gestores.py):
  · «esperando respuesta» = caso en cola cuyo último mensaje es del estudiante: lo pendiente de verdad hoy;
  · un gestor «trabaja» si cerró o transfirió algún caso en 7 días (CONFIG_IS_ACTIVE del SIS no lo refleja);
  · «sin atender por nadie» = en cola sin gestor, o con un gestor que no trabaja.
Las cifras se miden contra la hora de la carga, no contra la hora en que se abre el dashboard.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

TABLA = "kuepa-alertadashboard.alertas_academicas.cola_gestores"
PROGS = ["Bachillerato", "Técnicos"]
PRIO = {"critical": "Crítica", "high": "Alta", "medium": "Media", "low": "Baja"}
SIN = "(sin gestor)"


@st.cache_data(ttl=600)
def _cargar(_bq_df):
    casos = _bq_df(f"""
        SELECT * FROM `{TABLA}`
        WHERE fecha_foto = (SELECT MAX(fecha_foto) FROM `{TABLA}`)
        QUALIFY cargado = MAX(cargado) OVER ()""")
    serie = _bq_df(f"""
        SELECT fecha_foto, prog, gestor,
               COUNTIF(estado_caso = 'queued') cola,
               COUNTIF(estado_caso = 'queued' AND ult_tipo = 'message_inbound') esperando
        FROM (SELECT * FROM `{TABLA}` WHERE TRUE
              QUALIFY cargado = MAX(cargado) OVER (PARTITION BY fecha_foto))
        GROUP BY 1, 2, 3 ORDER BY 1""")
    # TIEMPO DE RESPUESTA (aproximado): la cola guarda solo el último mensaje de cada caso, y el log de mensajes
    # (EKU101015_log_message) dejó de replicarse el 2026-10-05. Se mide comparando fotos consecutivas: un caso que
    # a las 6:30 de un día esperaba respuesta (último mensaje del estudiante, en t_in) y en la foto siguiente tiene
    # como último mensaje uno del gestor (t_out) → respondió en t_out - t_in. Si el gestor escribió varias veces
    # entre fotos, t_out es la última → tiende a sobrestimar. No ve lo que se abre y responde entre dos fotos.
    resp = _bq_df(f"""
        WITH f AS (SELECT * FROM `{TABLA}` WHERE TRUE
                   QUALIFY cargado = MAX(cargado) OVER (PARTITION BY fecha_foto))
        SELECT a.gestor, a.prog, b.fecha_foto, TIMESTAMP_DIFF(b.ult_inter, a.ult_inter, MINUTE) / 60 horas
        FROM f a JOIN f b ON a.caso = b.caso AND b.fecha_foto = DATE_ADD(a.fecha_foto, INTERVAL 1 DAY)
        WHERE a.estado_caso = 'queued' AND a.ult_tipo = 'message_inbound'
          AND b.ult_tipo = 'message_outbound' AND b.ult_inter > a.ult_inter""")
    return casos, serie, resp


def _preparar(c):
    c = c.copy()
    ahora = c["cargado"].max()
    c["cola"] = c["estado_caso"] == "queued"
    c["esperando"] = c["cola"] & (c["ult_tipo"] == "message_inbound")
    c["dias_cola"] = ((ahora - c["creado"]).dt.total_seconds() / 86400).where(c["cola"])
    c["dias_espera"] = ((ahora - c["ult_inter"]).dt.total_seconds() / 86400).where(c["esperando"])
    c["h_cierre"] = ((c["actualizado"] - c["creado"]).dt.total_seconds() / 3600).where(c["estado_caso"] == "finished")
    c["sin_leer"] = c["sin_leer"].fillna(0).astype(int)
    hace7 = ahora - pd.Timedelta(days=7)
    trabajan = set(c.loc[(c["actualizado"] >= hace7) & ~c["cola"], "gestor"])
    c["trabaja"] = c["gestor"].isin(trabajan) & (c["gestor"] != SIN)

    # CALIDAD DEL CIERRE: señales de que un caso se cerró sin resolverse. Se evalúan los cerrados entre hace
    # 28 y hace 7 días (a los de la última semana aún no les da tiempo de "volver").
    #  · sin responder: se cerró con el último mensaje del estudiante y no era cortesía ("gracias", "ok"…);
    #  · volvió a escribir: el mismo estudiante abrió otro caso (de chat) en los 7 días siguientes al cierre.
    # cierre_cortesia / origen existen desde la carga del 2026-10-17; en fotos anteriores vienen vacías.
    c["cierre_cortesia"] = c.get("cierre_cortesia", pd.Series(index=c.index, dtype=object))
    c["origen"] = c.get("origen", pd.Series(index=c.index, dtype=object))
    c["cerr_eval"] = ((c["estado_caso"] == "finished") & (c["actualizado"] >= ahora - pd.Timedelta(days=28))
                      & (c["actualizado"] <= hace7))
    cort = c["cierre_cortesia"].fillna(False).astype(bool)
    c["sin_resp"] = c["cerr_eval"] & (c["ult_tipo"] == "message_inbound") & ~cort
    nuevos = c[c["origen"].isna() | (c["origen"] == "inbound_chat")][["id", "caso", "creado"]]
    par = c.loc[c["cerr_eval"], ["id", "caso", "actualizado"]].merge(nuevos, on="id", suffixes=("", "_n"))
    par = par[(par["caso_n"] != par["caso"]) & (par["creado"] > par["actualizado"])
              & (par["creado"] <= par["actualizado"] + pd.Timedelta(days=7))]
    vuelta = par.groupby("caso")["creado"].min()
    c["volvio_en"] = c["caso"].map(vuelta)
    c["volvio"] = c["volvio_en"].notna()
    return c, ahora


def _metricas(cs, ahora):
    hace7, hace28 = ahora - pd.Timedelta(days=7), ahora - pd.Timedelta(days=28)
    cola = cs[cs["cola"]]
    esp = cola[cola["esperando"]]
    fin = cs["estado_caso"] == "finished"
    cerr28 = cs[fin & (cs["actualizado"] >= hace28)]
    est = cerr28.drop_duplicates("id")
    return {
        "En cola": len(cola),
        "Esperando respuesta": len(esp),
        "Mensajes sin leer": int(cola["sin_leer"].sum()),
        "Críticos en cola": int((cola["prioridad"] == "critical").sum()),
        "En cola +7 días": int((cola["dias_cola"] > 7).sum()),
        "Días en cola (mediana)": cola["dias_cola"].median(),
        "Días esperando (mediana)": esp["dias_espera"].median(),
        "Nuevos 7 días": int((cs["creado"] >= hace7).sum()),
        "Cerrados 7 días": int((fin & (cs["actualizado"] >= hace7)).sum()),
        "Transferidos 7 días": int(((cs["estado_caso"] == "transferred") & (cs["actualizado"] >= hace7)).sum()),
        "Horas para cerrar (mediana, 28 días)": cerr28["h_cierre"].median(),
        "Siguen activos (%)": (est["estado_hoy"].notna().mean() * 100) if len(est) else None,
        "Cierres evaluados": int(cs["cerr_eval"].sum()),
        "Cerrados sin responder (%)": cs.loc[cs["cerr_eval"], "sin_resp"].mean() * 100 if cs["cerr_eval"].any() else None,
        "Volvió a escribir 7 días (%)": cs.loc[cs["cerr_eval"], "volvio"].mean() * 100 if cs["cerr_eval"].any() else None,
    }


def _resp_stats(r):
    """Mediana / promedio de horas de respuesta y cuántas se midieron (ver nota en _cargar)."""
    return {"Respuesta (h, mediana)": r["horas"].median() if len(r) else None,
            "Respuesta (h, promedio)": r["horas"].mean() if len(r) else None,
            "Respuestas medidas": len(r)}


def _tabla_gestores(c, ahora, prog, resp):
    cp = c[c["prog"] == prog]
    rp = resp[resp["prog"] == prog]
    filas = []
    for (g, trabaja), x in cp.groupby(["gestor", "trabaja"]):
        m = _metricas(x, ahora)
        nota = ("" if trabaja or g == SIN else "⚠️ sin movimiento en 7 días")
        if trabaja and not x["gestor_activo"].any():
            nota = "inactivo en el SIS, pero trabajando"
        filas.append({"Gestor": g, "Nota": nota, **_resp_stats(rp[rp["gestor"] == g]), **m})
    t = pd.DataFrame(filas).sort_values(["Esperando respuesta", "En cola"], ascending=False)
    total = {"Gestor": f"Total {prog}", "Nota": "", **_resp_stats(rp), **_metricas(cp, ahora)}
    return pd.concat([t, pd.DataFrame([total])], ignore_index=True), total


def _rojo(col, umbral):
    return lambda s: ["color:#E74C3C; font-weight:700" if (pd.notna(v) and v >= umbral) else "" for v in s] \
        if s.name == col else [""] * len(s)


def _mostrar(t):
    fmt = {k: "{:.1f}" for k in ["Días en cola (mediana)", "Días esperando (mediana)"]}
    fmt.update({"Horas para cerrar (mediana, 28 días)": "{:.0f}", "Siguen activos (%)": "{:.0f} %",
                "Respuesta (h, mediana)": "{:.1f}", "Respuesta (h, promedio)": "{:.1f}",
                "Cerrados sin responder (%)": "{:.0f} %", "Volvió a escribir 7 días (%)": "{:.0f} %"})
    sty = t.style.format(fmt, na_rep="—")
    for col, u in [("Esperando respuesta", 10), ("Críticos en cola", 5), ("En cola +7 días", 10),
                   ("Respuesta (h, mediana)", 24), ("Cerrados sin responder (%)", 25),
                   ("Volvió a escribir 7 días (%)", 30)]:
        sty = sty.apply(_rojo(col, u), axis=0)
    st.dataframe(sty, hide_index=True, use_container_width=True)


def render_gestores(_bq_df, chart_help):
    try:
        casos, serie, resp = _cargar(_bq_df)
    except Exception as e:
        st.error(f"No se pudo leer la cola de gestores: {e}")
        return
    if casos.empty:
        st.info("La cola de gestores todavía no tiene datos.")
        return
    c, ahora = _preparar(casos)
    hora = ahora.tz_convert("America/Bogota").strftime("%d/%m/%Y %H:%M")

    gest_disp = sorted(g for g in c.loc[c["gestor"] != SIN, "gestor"].unique())
    ver = st.selectbox("Ver", ["Todos los gestores"] + gest_disp, key="gest_panel")
    uno = ver != "Todos los gestores"
    cs = c[c["gestor"] == ver] if uno else c
    rs = resp[resp["gestor"] == ver] if uno else resp

    st.markdown(f"<div class='section-title'>{'👤 ' + ver if uno else '📋 Lo pendiente hoy'} — cola al {hora}</div>",
                unsafe_allow_html=True)
    m = _metricas(cs, ahora)
    huerf = c[c["cola"] & ~c["trabaja"]]
    k = st.columns(6)
    k[0].metric("⏳ Esperando respuesta", m["Esperando respuesta"],
                " · ".join(f"{p} {int(cs[cs['prog'] == p]['esperando'].sum())}" for p in PROGS), delta_color="off")
    k[1].metric("📥 En cola", m["En cola"], f"{m['Mensajes sin leer']:,} mensajes sin leer", delta_color="off")
    k[2].metric("🔴 Críticos en cola", m["Críticos en cola"])
    if uno:
        k[3].metric("🕰️ En cola +7 días", m["En cola +7 días"])
    else:
        k[3].metric("🚫 Sin atender por nadie", len(huerf), "sin gestor o gestor sin movimiento", delta_color="off")
    k[4].metric("✅ Cerrados 7 días", m["Cerrados 7 días"], f"{m['Nuevos 7 días']} nuevos", delta_color="off")
    r = _resp_stats(rs)
    k[5].metric("⏱️ Tiempo de respuesta", "—" if r["Respuesta (h, mediana)"] is None
                else f"{r['Respuesta (h, mediana)']:.1f} h",
                f"mediana · {r['Respuestas medidas']} respuestas medidas", delta_color="off")
    chart_help("<b>Esperando respuesta</b> = el caso sigue en cola y el último mensaje es del estudiante: es lo que "
               "está pendiente de verdad. Datos del Área académica, estudiantes de Bachillerato y Técnicos; se "
               "actualizan cada mañana a las 6:30.")

    if not uno and len(huerf):
        pres = huerf.groupby(["gestor", "prog"]).size().sort_values(ascending=False).head(8)
        st.warning(f"**{len(huerf)} casos en cola no los atiende nadie**: "
                   + "; ".join(f"{g} ({p}) {n}" for (g, p), n in pres.items()) + ". Hay que reasignarlos.")

    # ---- por programa
    for p in PROGS:
        if not (cs["prog"] == p).any():
            continue
        t, tot = _tabla_gestores(cs, ahora, p, rs)
        st.markdown(f"<div class='section-title'>Gestores de {p}</div>", unsafe_allow_html=True)
        st.caption(f"{tot['En cola']} en cola · {tot['Esperando respuesta']} esperando respuesta · "
                   f"{tot['Cerrados 7 días']} cerrados en 7 días")
        _mostrar(t)
    chart_help("En rojo: 10 o más esperando, 5 o más críticos, 10 o más con más de 7 días en cola. "
               "<b>Horas para cerrar</b>: de la creación a la última actualización de los casos cerrados en 28 días "
               "(aproximado). <b>Siguen activos</b>: de los estudiantes con un caso cerrado en 28 días, qué parte "
               "tiene hoy estado académico activo. <b>Respuesta (h)</b>: horas entre el último mensaje del "
               "estudiante y la respuesta del gestor, medido entre dos fotos diarias seguidas (aproximado, en rojo "
               "si la mediana pasa de 24 h). Con pocas <i>respuestas medidas</i> la cifra aún no es confiable: "
               "gana precisión con cada foto diaria. <b>Calidad del cierre</b> (casos cerrados hace 7 a 28 días): "
               "<b>sin responder</b> = se cerró con el último mensaje del estudiante y no era un «gracias/ok» "
               "(rojo desde 25 %); <b>volvió a escribir</b> = el estudiante abrió otro caso en los 7 días "
               "siguientes (rojo desde 30 %). Ojo: si se resolvió por llamada, el chat se ve sin responder.")

    # ---- evolución
    # Una línea por gestor (o, viendo a uno solo, sus dos curvas), con el número en cada punto y el eje
    # por día: la foto es diaria, un eje con horas inventaba tramos que no existen.
    s = serie[serie["gestor"] == ver] if uno else serie[serie["gestor"] != SIN]
    dias = sorted(s["fecha_foto"].unique())
    st.markdown("<div class='section-title'>Cómo evoluciona la cola — estudiantes esperando respuesta, día a día</div>",
                unsafe_allow_html=True)
    if len(dias) < 2:
        st.info(f"La serie arrancó el {dias[0] if dias else '—'}: con un día todavía no hay tendencia. Cada mañana suma uno.")
    else:
        s = s.assign(dia=pd.to_datetime(s["fecha_foto"]).dt.strftime("%d %b"))
        orden = [pd.Timestamp(d).strftime("%d %b") for d in dias]
        fig = go.Figure()
        if uno:
            a = s.groupby("dia")[["cola", "esperando"]].sum().reindex(orden, fill_value=0)
            fig.add_trace(go.Scatter(x=a.index, y=a["esperando"], name="Esperando respuesta",
                                     mode="lines+markers+text", text=a["esperando"], textposition="top center",
                                     line=dict(color="#FD531E", width=3)))
            fig.add_trace(go.Scatter(x=a.index, y=a["cola"], name="Total en cola",
                                     mode="lines+markers+text", text=a["cola"], textposition="bottom center",
                                     line=dict(color="#656A71", width=2, dash="dot")))
        else:
            paleta = ["#FD531E", "#149852", "#9725B9", "#3498DB", "#F5A623", "#E74C3C", "#1ABC9C", "#C0C0C0"]
            a = s.groupby(["gestor", "dia"])["esperando"].sum().unstack(fill_value=0).reindex(columns=orden, fill_value=0)
            a = a.loc[a.iloc[:, -1].sort_values(ascending=False).index]   # leyenda: el que más debe, primero
            resto = len(a) - 8
            a = a.head(8)   # más de 8 líneas no se leen; el resto se ve eligiendo al gestor arriba
            for k, (g, fila) in enumerate(a.iterrows()):
                fig.add_trace(go.Scatter(x=orden, y=fila.values, name=f"{g} ({int(fila.iloc[-1])})",
                                         mode="lines+markers+text", text=fila.values, textposition="top center",
                                         line=dict(color=paleta[k % len(paleta)], width=3)))
        eje = dict(gridcolor="#2A2A2A", color="#C0C0C0", tickfont=dict(color="#C0C0C0", size=12))
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0),
                          font=dict(color="#C0C0C0", family="Barlow", size=13),
                          legend=dict(orientation="h", y=-0.15, font=dict(color="#E0E0E0", size=12)),
                          xaxis=dict(type="category", **eje),
                          yaxis=dict(title=dict(text="estudiantes esperando", font=dict(color="#656A71")),
                                     rangemode="tozero", **eje),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        chart_help("Cada punto = estudiantes cuyo último mensaje es suyo y siguen esperando respuesta, en la foto de "
                   "las 6:30 de ese día. <b>Si la línea de un gestor baja, va al día; si sube, se le está "
                   "acumulando.</b> Entre paréntesis, cuántos tiene esperando hoy."
                   + (" La punteada es todo lo que tiene en cola." if uno else
                      (f" Se muestran los 8 con más pendientes hoy; los otros {resto} se ven eligiéndolos en "
                       "<i>Ver</i>." if resto > 0 else "")))

    # ---- cierres para revisar (calidad del cierre)
    rev = cs[cs["sin_resp"] | cs["volvio"]].sort_values("actualizado", ascending=False)
    st.markdown(f"<div class='section-title' style='border-color:#9725B9'>🔍 {len(rev)} cierres para revisar "
                "— ¿se solucionó de verdad?</div>", unsafe_allow_html=True)
    if c["cierre_cortesia"].isna().all():
        st.caption("⚠️ La foto de hoy aún no distingue los cierres de cortesía («gracias», «ok»): se cuentan "
                   "como sin responder. Desde la carga de mañana a las 6:30 ya se descuentan.")
    if len(rev):
        señal = (rev["sin_resp"].map({True: "Cerrado sin responder", False: ""}) + " · "
                 + rev["volvio"].map({True: "Volvió a escribir", False: ""})).str.strip(" ·")
        tabla_rev = pd.DataFrame({
            "ID": rev["id"], "Estudiante": rev["estudiante"], "Programa": rev["prog"], "Gestor": rev["gestor"],
            "Cerrado": rev["actualizado"].dt.tz_convert("America/Bogota").dt.strftime("%Y-%m-%d"),
            "Señal": señal,
            "Volvió a los (días)": ((rev["volvio_en"] - rev["actualizado"]).dt.total_seconds() / 86400).round(1),
            "Motivo (resumen automático)": rev["motivo"].fillna(""),
        })
        st.dataframe(tabla_rev, hide_index=True, use_container_width=True, height=360)
        st.download_button(f"⬇️ Descargar {len(tabla_rev):,} cierres para revisar (CSV)",
                           tabla_rev.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"cierres_revisar_{ver.lower().replace(' ', '_') if uno else 'todos'}"
                                     f"_{ahora:%Y-%m-%d}.csv",
                           mime="text/csv", key="dl_cierres")
    chart_help("Casos cerrados hace 7 a 28 días con alguna señal de que no quedaron resueltos. Revisar unos "
               "cuantos por semana en la plataforma (y que el equipo lo sepa) es lo que más previene los cierres "
               "por cumplir. Si se resolvió por llamada, es normal que salga como «sin responder».")

    # ---- lista de pendientes
    pend = cs[cs["esperando"]].sort_values("dias_espera", ascending=False)
    st.markdown(f"<div class='section-title' style='border-color:#FD531E'>📥 {len(pend)} estudiantes esperando "
                "respuesta</div>", unsafe_allow_html=True)
    lista = pd.DataFrame({
        "ID": pend["id"], "Estudiante": pend["estudiante"], "Programa": pend["prog"], "Gestor": pend["gestor"],
        "Días esperando": pend["dias_espera"].round(1), "Días en cola": pend["dias_cola"].round(1),
        "Prioridad": pend["prioridad"].map(PRIO).fillna("—"), "Sin leer": pend["sin_leer"],
        "Cartera": pend["cartera"].fillna("—"), "Motivo (resumen automático)": pend["motivo"].fillna(""),
    })
    st.dataframe(lista, hide_index=True, use_container_width=True, height=420)
    slug = ver.lower().replace(" ", "_") if uno else "todos"
    st.download_button(f"⬇️ Descargar {len(lista):,} pendientes (CSV)", lista.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"pendientes_gestores_{slug}_{ahora:%Y-%m-%d}.csv", mime="text/csv",
                       key="dl_gestores")
    chart_help("Ordenados por cuánto llevan esperando: arriba, a quien hay que contestar primero.")
