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
    return casos, serie


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
    }


def _tabla_gestores(c, ahora, prog):
    cp = c[c["prog"] == prog]
    filas = []
    for (g, trabaja), x in cp.groupby(["gestor", "trabaja"]):
        m = _metricas(x, ahora)
        nota = ("" if trabaja or g == SIN else "⚠️ sin movimiento en 7 días")
        if trabaja and not x["gestor_activo"].any():
            nota = "inactivo en el SIS, pero trabajando"
        filas.append({"Gestor": g, "Nota": nota, **m})
    t = pd.DataFrame(filas).sort_values(["Esperando respuesta", "En cola"], ascending=False)
    total = {"Gestor": f"Total {prog}", "Nota": "", **_metricas(cp, ahora)}
    return pd.concat([t, pd.DataFrame([total])], ignore_index=True), total


def _rojo(col, umbral):
    return lambda s: ["color:#E74C3C; font-weight:700" if (pd.notna(v) and v >= umbral) else "" for v in s] \
        if s.name == col else [""] * len(s)


def _mostrar(t):
    fmt = {k: "{:.1f}" for k in ["Días en cola (mediana)", "Días esperando (mediana)"]}
    fmt.update({"Horas para cerrar (mediana, 28 días)": "{:.0f}", "Siguen activos (%)": "{:.0f} %"})
    sty = t.style.format(fmt, na_rep="—")
    for col, u in [("Esperando respuesta", 10), ("Críticos en cola", 5), ("En cola +7 días", 10)]:
        sty = sty.apply(_rojo(col, u), axis=0)
    st.dataframe(sty, hide_index=True, use_container_width=True)


def render_gestores(_bq_df, chart_help):
    try:
        casos, serie = _cargar(_bq_df)
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

    st.markdown(f"<div class='section-title'>{'👤 ' + ver if uno else '📋 Lo pendiente hoy'} — cola al {hora}</div>",
                unsafe_allow_html=True)
    m = _metricas(cs, ahora)
    huerf = c[c["cola"] & ~c["trabaja"]]
    k = st.columns(5)
    k[0].metric("⏳ Esperando respuesta", m["Esperando respuesta"],
                " · ".join(f"{p} {int(cs[cs['prog'] == p]['esperando'].sum())}" for p in PROGS), delta_color="off")
    k[1].metric("📥 En cola", m["En cola"], f"{m['Mensajes sin leer']:,} mensajes sin leer", delta_color="off")
    k[2].metric("🔴 Críticos en cola", m["Críticos en cola"])
    if uno:
        k[3].metric("🕰️ En cola +7 días", m["En cola +7 días"])
    else:
        k[3].metric("🚫 Sin atender por nadie", len(huerf), "sin gestor o gestor sin movimiento", delta_color="off")
    k[4].metric("✅ Cerrados 7 días", m["Cerrados 7 días"], f"{m['Nuevos 7 días']} nuevos", delta_color="off")
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
        t, tot = _tabla_gestores(cs, ahora, p)
        st.markdown(f"<div class='section-title'>Gestores de {p}</div>", unsafe_allow_html=True)
        st.caption(f"{tot['En cola']} en cola · {tot['Esperando respuesta']} esperando respuesta · "
                   f"{tot['Cerrados 7 días']} cerrados en 7 días")
        _mostrar(t)
    chart_help("En rojo: 10 o más esperando, 5 o más críticos, 10 o más con más de 7 días en cola. "
               "<b>Horas para cerrar</b>: de la creación a la última actualización de los casos cerrados en 28 días "
               "(aproximado). <b>Siguen activos</b>: de los estudiantes con un caso cerrado en 28 días, qué parte "
               "tiene hoy estado académico activo. La fuente no guarda la primera respuesta, solo el último visto.")

    # ---- evolución
    s = serie[serie["gestor"] == ver] if uno else serie
    dias = sorted(s["fecha_foto"].unique())
    st.markdown("<div class='section-title'>Cómo evoluciona la cola</div>", unsafe_allow_html=True)
    if len(dias) < 2:
        st.info(f"La serie arrancó el {dias[0] if dias else '—'}: con un día todavía no hay tendencia. Cada mañana suma uno.")
    else:
        agg = s.groupby(["fecha_foto", "prog"])[["cola", "esperando"]].sum().reset_index()
        fig = go.Figure()
        for p, color in zip(PROGS, ["#FD531E", "#3498DB"]):
            a = agg[agg["prog"] == p]
            fig.add_trace(go.Scatter(x=a["fecha_foto"], y=a["esperando"], name=f"{p} · esperando",
                                     mode="lines+markers", line=dict(color=color, width=3)))
            fig.add_trace(go.Scatter(x=a["fecha_foto"], y=a["cola"], name=f"{p} · en cola",
                                     mode="lines", line=dict(color=color, width=1, dash="dot")))
        fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h"),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        chart_help("Línea gruesa: estudiantes esperando respuesta. Punteada: todo lo que está en cola. "
                   "Si la gruesa baja día a día, el equipo va al día.")

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
