"""Pestaña «Envíos»: qué correos salieron a estudiantes, a quiénes, cuántos y quiénes faltan.

Pedido de Luis (20-oct-2026): «posterior a todos los envíos, a quiénes se les envió, qué se le ha enviado,
cuántos correos se enviaron… quiénes faltan, para estar alineados, al día».

Fuente: la vista `alertas_academicas.vw_envios` (US), que une
  · log_informes          → el informe académico modular (Bachillerato y Técnicos), uno por estudiante × cierre;
  · informe_foto_corte    → los ELEGIBLES de cada corrida nocturna: lo que no está en el log, falta;
  · log_promocion_panel   → el correo de promoción de grado (copia sin HTML del registro de us-east1);
  · promocion_foto        → los candidatos de cada lunes;
  · log_avisos_institucional → los avisos al correo personal y alternativo.
Cada flujo de n8n escribe su parte al correr, así que la pestaña está al día sin que nadie la actualice.
SQL y código de los nodos: SEGUIMIENTO 2026 › COMUNICACION/correos/panel-envios/ESPECIFICACION.md.
"""
import pandas as pd
import streamlit as st

VISTA = "kuepa-alertadashboard.alertas_academicas.vw_envios"
FLUJOS = ["Informe académico", "Promoción de grado", "Aviso a correo personal"]
ICONO = {"Informe académico": "📘", "Promoción de grado": "🎓", "Aviso a correo personal": "🔔"}


@st.cache_data(ttl=600)
def _cargar(_bq_df):
    return _bq_df(f"SELECT * FROM `{VISTA}`")


def _preparar(d):
    d = d.copy()
    d["fecha"] = pd.to_datetime(d["fecha"], utc=True).dt.tz_convert("America/Bogota")
    d["dia"] = d["fecha"].dt.date
    d["modulo"] = d["modulo"].fillna("(sin módulo: envíos antes del 2-oct)")
    for c in ("cierre", "previsto"):
        d[c] = pd.to_datetime(d[c]).dt.date if c in d else None
    # Los avisos no traen el nombre: se toma de cualquier otro envío del mismo estudiante.
    nombres = d.dropna(subset=["estudiante"]).drop_duplicates("id").set_index("id")["estudiante"]
    d["estudiante"] = d["estudiante"].fillna(d["id"].map(nombres))
    return d


TOPE = 750   # informes por noche (MAX_CORREOS_NOCHE del flujo)


def _estado(flujo, previsto, enviados, faltan, hoy):
    """Estado de un grupo (un cierre del informe, una semana de promoción). Lo que falta solo es alarma si ya
    debía haber salido: el informe sale 5 días después del cierre, a las 21:00, con tope de 750 por noche."""
    if faltan == 0:
        return "✅ Completo", False
    if previsto is None or pd.isna(previsto):
        return "⏳ Pendiente", False
    if hoy < previsto:
        return f"🗓️ Programado: sale el {previsto:%d/%m}", False
    noches = 1 if flujo != "Informe académico" else -(-(enviados + faltan) // TOPE)
    fin = previsto + pd.Timedelta(days=noches - 1)
    if hoy == previsto and enviados == 0:
        return "🕘 Sale hoy a las 21:00" + (f" (termina el {fin:%d/%m})" if noches > 1 else ""), False
    if hoy <= fin:
        return f"📤 Enviando por tandas de {TOPE}: termina el {fin:%d/%m}", False
    return f"🔴 Atrasado {(hoy - fin).days} día(s): debía terminar el {fin:%d/%m}", True


def _grupos(base, hoy):
    """Una fila por cierre (informe) o semana (promoción), con su estado."""
    g = (base.assign(e=base["estado"] == "Enviado", f=base["estado"] == "Falta", s=base["estado"] == "Sin correo")
         .groupby(["flujo", "familia", "modulo", "cierre", "previsto"], dropna=False)
         .agg(Enviados=("e", "sum"), Faltan=("f", "sum"), **{"Sin correo": ("s", "sum")}, Último=("fecha", "max"))
         .reset_index())
    est = [_estado(r.flujo, r.previsto, r.Enviados, r.Faltan, hoy) for r in g.itertuples()]
    g["Estado"] = [e for e, _ in est]
    g["atrasado"] = [a for _, a in est]
    return g


def _csv(df, nombre, key, etiqueta):
    st.download_button(f"⬇️ {etiqueta} ({len(df):,}) · CSV", df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=nombre, mime="text/csv", key=key)


def render_envios(_bq_df, chart_help):
    try:
        d = _cargar(_bq_df)
    except Exception as e:
        st.error(f"No se pudo leer el registro de envíos: {e}")
        return
    if d.empty:
        st.info("Todavía no hay envíos registrados.")
        return
    d = _preparar(d)

    c = st.columns([2, 2, 2])
    flujo = c[0].selectbox("Correo", ["Todos"] + FLUJOS, key="env_flujo")
    fam = c[1].selectbox("Programa", ["Todos", "Bachillerato", "Técnicos"], key="env_fam")
    dias = c[2].selectbox("Periodo", [7, 14, 30, 60, 3650], index=1, key="env_dias",
                          format_func=lambda x: "Todo el registro" if x > 365 else f"Últimos {x} días")
    x = d
    if flujo != "Todos":
        x = x[x["flujo"] == flujo]
    if fam != "Todos":
        x = x[x["familia"] == fam]
    env = x[x["estado"].isin(["Enviado", "Falló"])]
    hoy = pd.Timestamp.now(tz="America/Bogota").date()
    env_p = env[env["dia"] >= hoy - pd.Timedelta(days=dias)]
    falta = x[x["estado"] == "Falta"]
    sinc = x[x["estado"] == "Sin correo"]

    # ---- cifras de arriba
    ok = env_p[env_p["estado"] == "Enviado"]
    ult = ok["fecha"].max() if len(ok) else None
    ult_dia = ok[ok["dia"] == ult.date()] if ult is not None else ok
    k = st.columns(5)
    k[0].metric("📤 Último envío", ult.strftime("%d/%m/%Y") if ult is not None else "—",
                " · ".join(f"{ICONO[f]} {n}" for f, n in ult_dia.groupby("flujo").size().items()) or None,
                delta_color="off")
    k[1].metric("✉️ Correos enviados", f"{len(ok):,}", f"{ok['id'].nunique():,} estudiantes", delta_color="off")
    base = x[x["flujo"] != "Aviso a correo personal"]
    grupos = _grupos(base, hoy)
    atr = grupos[grupos["atrasado"]]
    prog = grupos[(grupos["Faltan"] > 0) & ~grupos["atrasado"]]
    k[2].metric("🔴 Atrasados", f"{int(atr['Faltan'].sum()):,}",
                f"{int(prog['Faltan'].sum()):,} programados para las próximas noches", delta_color="off")
    k[3].metric("🚫 Sin correo institucional", f"{len(sinc):,}", "no pueden recibir nada", delta_color="off")
    fallos = env_p[env_p["estado"] == "Falló"]
    k[4].metric("⚠️ Fallaron en Gmail", f"{len(fallos):,}")
    chart_help("<b>Enviados</b>: correos que Gmail aceptó en el periodo elegido. <b>Faltan</b>: estudiantes que "
               "debían recibir en la última corrida de cada flujo y aún no tienen envío; el informe académico sale "
               "cada noche a las 21:00 con un tope de 750, así que lo pendiente se va enviando en las noches "
               "siguientes. <b>Sin correo</b>: no tienen correo institucional en el SIS. Se actualiza solo: cada "
               "flujo escribe aquí al enviar.")

    if len(atr):
        st.error("**Hay envíos atrasados** (ya debían haber salido): "
                 + "; ".join(f"{r.flujo} · {r.modulo}"
                             + (f" (cierre {r.cierre:%d/%m})" if pd.notna(r.cierre) else "") + f": {int(r.Faltan):,}"
                             for r in atr.itertuples()) + ".")
    elif len(prog):
        st.info("**Nada atrasado.** Programado: "
                + "; ".join(f"{r.modulo}" + (f" (cierre {r.cierre:%d/%m})" if pd.notna(r.cierre) else "")
                            + f" · {int(r.Faltan):,} · {r.Estado.split(' ', 1)[1]}" for r in prog.itertuples()) + ".")

    # ---- envíos por día
    st.markdown("<div class='section-title'>📅 Envíos por día — qué salió y cuántos</div>", unsafe_allow_html=True)
    if len(env_p):
        t = (env_p.assign(ok=env_p["estado"] == "Enviado", mal=env_p["estado"] == "Falló")
             .groupby(["dia", "flujo", "familia", "modulo"], dropna=False)
             .agg(Enviados=("ok", "sum"), Fallaron=("mal", "sum"), Estudiantes=("id", "nunique"))
             .reset_index().sort_values(["dia", "flujo"], ascending=[False, True]))
        t = t.rename(columns={"dia": "Fecha", "flujo": "Correo", "familia": "Programa", "modulo": "Módulo / cierre"})
        st.dataframe(t, hide_index=True, use_container_width=True, height=min(420, 38 + 35 * len(t)))
    else:
        st.info("No hubo envíos en el periodo elegido.")

    # ---- estado por módulo (avance)
    st.markdown("<div class='section-title'>📊 Estado de cada cierre — ¿salió, está programado o está atrasado?</div>",
                unsafe_allow_html=True)
    av = grupos[(grupos["Faltan"] > 0) | (grupos["Último"].dt.date >= hoy - pd.Timedelta(days=dias))].copy()
    if len(av):
        tot = av["Enviados"] + av["Faltan"] + av["Sin correo"]
        av["Avance"] = (av["Enviados"] / tot * 100).round(0)
        av["Cierre"] = av["cierre"].map(lambda v: f"{v:%d/%m/%Y}" if pd.notna(v) else "—")
        av["Le toca salir"] = av["previsto"].map(lambda v: f"{v:%d/%m/%Y}" if pd.notna(v) else "—")
        av["Último envío"] = av["Último"].dt.strftime("%d/%m/%Y").fillna("—")
        av = av.sort_values(["atrasado", "Faltan", "previsto"], ascending=[False, False, False])
        av = av.rename(columns={"flujo": "Correo", "familia": "Programa", "modulo": "Módulo / cierre"})
        cols = ["Correo", "Programa", "Módulo / cierre", "Cierre", "Le toca salir", "Estado",
                "Enviados", "Faltan", "Sin correo", "Avance", "Último envío"]
        sty = av[cols].style.format({"Avance": "{:.0f} %"}).apply(
            lambda r: ["color:#E74C3C;font-weight:700" if "Atrasado" in str(r["Estado"]) else "" for _ in r], axis=1)
        st.dataframe(sty, hide_index=True, use_container_width=True)
        chart_help("Una fila por <b>cierre</b>: un mismo módulo de Técnicos cierra por grupos en días distintos, y "
                   "cada grupo tiene su fecha. El informe <b>le toca salir</b> 5 días después del cierre, a las "
                   "21:00, en tandas de 750 por noche. Solo es alarma lo que sale en rojo como <b>atrasado</b>: "
                   "lo programado todavía no debía haber salido.")

    # ---- quiénes faltan
    st.markdown(f"<div class='section-title' style='border-color:#FD531E'>⏳ {len(falta) + len(sinc):,} estudiantes "
                "que faltan</div>", unsafe_allow_html=True)
    fl = pd.concat([falta, sinc]).sort_values(["estado", "flujo", "modulo", "estudiante"])
    if len(fl):
        lista = pd.DataFrame({"ID": fl["id"], "Estudiante": fl["estudiante"], "Programa": fl["programa"].fillna(fl["familia"]),
                              "Correo": fl["flujo"], "Módulo / cierre": fl["modulo"], "Estado": fl["estado"],
                              "Cuándo / por qué": fl["que"], "Correo institucional": fl["destinatario"].fillna("—")})
        st.dataframe(lista, hide_index=True, use_container_width=True, height=360)
        _csv(lista, f"envios_faltan_{hoy}.csv", "dl_env_faltan", "Descargar los que faltan")
    else:
        st.success("No falta nadie: todo lo que debía salir ya salió.")

    # ---- a quiénes se les envió
    st.markdown("<div class='section-title'>✅ A quiénes se les envió</div>", unsafe_allow_html=True)
    buscar = st.text_input("Buscar por nombre o ID", key="env_buscar")
    ev = env_p.sort_values("fecha", ascending=False)
    if buscar:
        b = buscar.strip().lower()
        ev = ev[ev["estudiante"].fillna("").str.lower().str.contains(b, regex=False) | (ev["id"].astype(str) == b)]
    detalle = pd.DataFrame({"Fecha": ev["dia"], "ID": ev["id"], "Estudiante": ev["estudiante"],
                            "Programa": ev["programa"].fillna(ev["familia"]), "Correo": ev["flujo"],
                            "Módulo / cierre": ev["modulo"], "Qué se le envió": ev["que"],
                            "Enviado a": ev["destinatario"], "Estado": ev["estado"]})
    st.dataframe(detalle, hide_index=True, use_container_width=True, height=420)
    _csv(detalle, f"envios_enviados_{hoy}.csv", "dl_env_enviados", "Descargar los enviados")
    chart_help("Una fila por correo. <b>Qué se le envió</b>: en el informe, si llevaba las notas visibles u ocultas "
               "por cartera; en promoción y avisos, el asunto exacto. Los avisos van al correo personal y al "
               "alternativo (nunca llevan notas ni montos).")
