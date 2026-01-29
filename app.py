import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración de página para Celular y PC
st.set_page_config(page_title="CRM Agenda de Ventas", layout="wide")

# --- INICIALIZACIÓN DE BASES DE DATOS EN MEMORIA ---
for key in ['contactos', 'productos', 'bitacora', 'oc', 'items_oc_actual']:
    if f'db_{key}' not in st.session_state:
        st.session_state[f'db_{key}'] = []

# --- NAVEGACIÓN LATERAL ---
st.sidebar.title("Menú Principal")
opcion = st.sidebar.radio("Ir a:", ["Bitácora", "Órdenes de Compra", "Cobros", "Contactos", "Productos","Historial Empresas"])

# --- MÓDULO PRODUCTOS ---
if opcion == "Productos":
    st.header("📦 Gestión de Artículos")
    tab_p1, tab_p2 = st.tabs(["Agregar Artículos", "Listado de Artículos"])
    
    with tab_p1:
        with st.form("form_prod", clear_on_submit=True):
            n_art = st.text_input("Nombre Artículo")
            c1, c2 = st.columns(2)
            with c1:
                dims = st.text_input("Dimensiones")
                tej = st.text_input("Tejido")
                precio = st.number_input("Precio Unitario U$S", min_value=0.0)
            with c2:
                cant_pal = st.number_input("Cantidad por Pallet", min_value=0)
                peso_pal = st.number_input("Peso 1 Pallet", min_value=0.0)
            
            if st.form_submit_button("Registrar Artículo"):
                aid = f"Art. - {len(st.session_state.db_productos) + 1}"
                st.session_state.db_productos.append({
                    "N°": aid, "Nombre": n_art, "Dimensiones": dims, 
                    "Tejido": tej, "U$S": precio, "Cant/Pallet": cant_pal, "Peso/Pallet": peso_pal
                })
                st.success(f"Artículo {aid} guardado.")

    with tab_p2:
        if st.session_state.db_productos:
            st.dataframe(pd.DataFrame(st.session_state.db_productos))
            st.button("Descargar Listado PDF (Simulado)")

# --- MÓDULO CONTACTOS (RESTAURADO + ESTADOS INDEPENDIENTES) ---
elif opcion == "Contactos":
    st.header("👥 Gestión de Contactos")
    
    # Inicializamos las listas de seguimiento si no existen para que no den error
    if "list_activos" not in st.session_state: st.session_state.list_activos = []
    if "list_interesados" not in st.session_state: st.session_state.list_interesados = []
    if "list_visitar" not in st.session_state: st.session_state.list_visitar = []
    if "list_otros" not in st.session_state: st.session_state.list_otros = []

    t1, t2, t3, t_act, t_int, t_vis, t_otr = st.tabs([
        "Agregar Contacto", "Lista de Contactos", "Buscar/Editar", 
        "✅ Clientes Activos", "⭐ Interesados", "📍 Por Visitar", "👤 Clientes de Otro"
    ])
    
    with t1:
        with st.form("form_contacto", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                empresa = st.text_input("Empresa")
                actividad = st.text_input("Actividad")
                pais = st.text_input("País")
                prov = st.text_input("Provincia")
                ciudad = st.text_input("Ciudad")
                maps = st.text_input("Dirección Google Maps")
            with col2:
                web = st.text_input("Página Web")
                tel1, tel2, tel3 = st.text_input("Teléfono 1"), st.text_input("Teléfono 2"), st.text_input("Teléfono 3")
                mail1, mail2, mail3 = st.text_input("Mail 1"), st.text_input("Mail 2"), st.text_input("Mail 3")
                extra = st.text_area("Dato Extra")
            
            if st.form_submit_button("Guardar Contacto"):
                cid = f"C - {len(st.session_state.db_contactos) + 1}"
                st.session_state.db_contactos.append({
                    "N°": cid, "Empresa": empresa, "País": pais, "Ciudad": ciudad,
                    "Provincia": prov, "Maps": maps, "Actividad": actividad, "Web": web,
                    "T1": tel1, "T2": tel2, "T3": tel3, "M1": mail1, "M2": mail2, "M3": mail3, "Extra": extra
                })
                st.success(f"Contacto {cid} guardado y campos limpios.")

    with t2:
        st.subheader("📋 Lista de Empresas Registradas")
        if st.session_state.db_contactos:
            df_contactos = pd.DataFrame(st.session_state.db_contactos)
            st.dataframe(df_contactos[["N°", "Empresa", "Actividad", "País", "Ciudad", "T1"]], use_container_width=True)
        else:
            st.info("No hay contactos en la lista.")

    with t3:
        st.subheader("🔍 Buscador de Detalle")
        if st.session_state.db_contactos:
            nombres = [c['Empresa'] for c in st.session_state.db_contactos]
            busqueda = st.selectbox("Seleccioná una empresa", nombres)
            
            # Buscamos los datos del seleccionado
            c = next(item for item in st.session_state.db_contactos if item['Empresa'] == busqueda)
            
            # --- DISEÑO MEJORADO DEL DETALLE ---
            st.markdown(f"### {c['Empresa']} ({c['N°']})")
            
            # BOTONES PARA ASIGNAR ESTADOS (Independientes)
            st.write("**Asignar a lista de seguimiento:**")
            btn1, btn2, btn3, btn4 = st.columns(4)
            if btn1.button("✅ Activo", key="btn_act"):
                if c['Empresa'] not in st.session_state.list_activos: st.session_state.list_activos.append(c['Empresa'])
                st.toast("Agregado a Activos")
            if btn2.button("⭐ Interesado", key="btn_int"):
                if c['Empresa'] not in st.session_state.list_interesados: st.session_state.list_interesados.append(c['Empresa'])
                st.toast("Agregado a Interesados")
            if btn3.button("📍 Por Visitar", key="btn_vis"):
                if c['Empresa'] not in st.session_state.list_visitar: st.session_state.list_visitar.append(c['Empresa'])
                st.toast("Agregado a Por Visitar")
            if btn4.button("👤 De Otro", key="btn_otr"):
                if c['Empresa'] not in st.session_state.list_otros: st.session_state.list_otros.append(c['Empresa'])
                st.toast("Agregado a De Otros")

            st.write("---")
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**📍 Ubicación**")
                st.write(f"🏠 {c['Ciudad']}, {c.get('Provincia', '')} ({c['País']})")
                if c['Maps']: st.link_button("🌐 Ver en Google Maps", c['Maps'])
                st.markdown("**🛠 Actividad**")
                st.write(f"💼 {c['Actividad']}")
            with col_b:
                st.markdown("**📞 Contacto**")
                st.write(f"📱 {c['T1']} / {c['T2']} / {c['T3']}")
                st.write(f"📧 {c['M1']} / {c['M2']} / {c['M3']}")
                if c['Web']: st.write(f"💻 [{c['Web']}]({c['Web']})")

            st.markdown("**📝 Datos Extra**")
            st.info(c['Extra'] if c['Extra'] else "Sin datos adicionales.")
        else:
            st.write("Cargá una empresa para habilitar la búsqueda.")

    # --- LÓGICA DE PESTAÑAS DE SEGUIMIENTO ---
    def render_lista(titulo, lista_key):
        st.subheader(titulo)
        lista_actual = st.session_state[lista_key]
        if lista_actual:
            for emp_nombre in lista_actual:
                with st.expander(f"🏢 {emp_nombre}"):
                    datos = next((item for item in st.session_state.db_contactos if item['Empresa'] == emp_nombre), None)
                    if datos:
                        st.write(f"**Actividad:** {datos['Actividad']} | **Tel:** {datos['T1']}")
                    if st.button(f"❌ Quitar de la lista", key=f"del_{lista_key}_{emp_nombre}"):
                        st.session_state[lista_key].remove(emp_nombre)
                        st.rerun()
        else:
            st.info(f"No hay empresas en {titulo}.")

    with t_act: render_lista("Clientes Activos", "list_activos")
    with t_int: render_lista("Clientes Interesados", "list_interesados")
    with t_vis: render_lista("Clientes por Visitar", "list_visitar")
    with t_otr: render_lista("Clientes de Otro", "list_otros")

# --- MÓDULO ÓRDENES DE COMPRA (DÓLAR A LA IZQUIERDA DEL MONTO) ---
elif opcion == "Órdenes de Compra":
    st.header("🛒 Gestión de Órdenes de Compra")
    tab_carga, tab_historial = st.tabs(["➕ Nueva Orden", "📋 Historial y Gestión"])

    if not st.session_state.db_contactos:
        st.warning("Primero cargá un Contacto en el módulo correspondiente.")
    else:
        with tab_carga:
            with st.container():
                c_oc1, c_oc2 = st.columns(2)
                nombre_oc = c_oc1.text_input("Nombre OC / Referencia")
                fecha_oc = c_oc2.date_input("Fecha OC", datetime.now())
                emp_oc = c_oc1.selectbox("Empresa", [c['Empresa'] for c in st.session_state.db_contactos])
                # Mantenemos el input del dólar
                dolar = c_oc2.number_input("Dólar Pautado", value=1000.0) 
                
                tipo_fact = st.radio("Tipo de Facturación", ["En Blanco", "En Negro"], horizontal=True)
                detalle_extra_oc = st.text_area("Detalle Extra de la Orden")
            
            st.write("---")
            st.subheader("📦 Cargar Artículos")
            if st.session_state.db_productos:
                col_p1, col_p2, col_p3 = st.columns([2, 1, 1])
                prod_sel = col_p1.selectbox("Elegir Artículo", [p['Nombre'] for p in st.session_state.db_productos])
                cant_it = col_p2.number_input("Cantidad", min_value=1, key="oc_cant")
                p_orig = next((p['U$S'] for p in st.session_state.db_productos if p['Nombre'] == prod_sel), 0.0)
                prec_it = col_p3.number_input("Precio U$S", value=float(p_orig), key="oc_prec")
                
                if st.button("➕ Añadir a la lista"):
                    st.session_state.db_items_oc_actual.append({
                        "Producto": prod_sel, "Cantidad": cant_it, "Precio": prec_it, "Subtotal": round(cant_it * prec_it, 2)
                    })

            if st.session_state.db_items_oc_actual:
                df_temp = pd.DataFrame(st.session_state.db_items_oc_actual)
                st.table(df_temp)
                total_usd = df_temp["Subtotal"].sum()
                st.metric("TOTAL ACUMULADO", f"U$S {total_usd:,.2f}")
                
                c_fin1, c_fin2 = st.columns(2)
                if c_fin1.button("💾 GUARDAR ORDEN COMPLETA", type="primary", use_container_width=True):
                    oc_id = f"OC - {len(st.session_state.db_oc) + 1}"
                    st.session_state.db_oc.append({
                        "ID": oc_id, 
                        "Empresa": emp_oc, 
                        "Dólar": dolar,    # <--- Guardado
                        "Monto": total_usd, 
                        "Fecha": fecha_oc, 
                        "Referencia": nombre_oc,
                        "Facturación": tipo_fact,
                        "Detalle Extra": detalle_extra_oc
                    })
                    st.session_state.db_items_oc_actual = []
                    st.success(f"¡{oc_id} guardada exitosamente!")
                    st.rerun()
                if c_fin2.button("🗑️ Vaciar lista items", use_container_width=True):
                    st.session_state.db_items_oc_actual = []
                    st.rerun()

        with tab_historial:
            st.subheader("🔎 Filtros y Reportes")
            if st.session_state.db_oc:
                df_hist = pd.DataFrame(st.session_state.db_oc)
                df_hist["Fecha"] = pd.to_datetime(df_hist["Fecha"]).dt.date
                
                f_col1, f_col2 = st.columns(2)
                with f_col1:
                    emp_busc = st.selectbox("Filtrar por Empresa", ["Todas"] + sorted(list(df_hist["Empresa"].unique())))
                with f_col2:
                    rango = st.date_input("Rango de fechas", value=[])

                df_f = df_hist.copy()
                if emp_busc != "Todas": df_f = df_f[df_f['Empresa'] == emp_busc]
                if len(rango) == 2: df_f = df_f[(df_f["Fecha"] >= rango[0]) & (df_f["Fecha"] <= rango[1])]

                # --- BOTONES DE DESCARGA ---
                if not df_f.empty:
                    st.write("### ⬇️ Descargar")
                    d_col1, d_col2 = st.columns(2)
                    csv = df_f.to_csv(index=False).encode('utf-8')
                    d_col1.download_button("📥 EXCEL", csv, f"OC_{emp_busc}.csv", use_container_width=True)
                    
                    html = f"""
                    <div style='font-family: Arial;'>
                        <h2>Reporte OC: {emp_busc}</h2>
                        {df_f.to_html(index=False)}
                        <br>
                        <h3>Monto Total Filtrado: U$S {df_f['Monto'].sum():,.2f}</h3>
                    </div>
                    """
                    d_col2.download_button("📄 PDF", html, f"OC_{emp_busc}.html", "text/html", use_container_width=True)

                st.write("---")
                # Reordenamos las columnas aquí para que aparezca: ID, Empresa, Dólar, Monto...
                columnas_ordenadas = ["ID", "Fecha", "Empresa", "Dólar", "Monto", "Referencia", "Facturación", "Detalle Extra"]
                # Solo mostramos las columnas que existen para evitar errores
                cols_finales = [col for col in columnas_ordenadas if col in df_f.columns]
                st.dataframe(df_f[cols_finales], use_container_width=True)

                with st.expander("🗑️ Eliminar una Orden"):
                    id_a_borrar = st.selectbox("Elegí el ID para borrar", df_f["ID"].tolist() if not df_f.empty else ["Ninguno"])
                    if st.button("Confirmar Borrado"):
                        if id_a_borrar != "Ninguno":
                            st.session_state.db_oc = [o for o in st.session_state.db_oc if o["ID"] != id_a_borrar]
                            st.rerun()
            else:
                st.info("No hay órdenes.")

# --- MÓDULO BITÁCORA (CON ELIMINACIÓN Y DESCARGA FILTRADA) ---
elif opcion == "Bitácora":
    st.header("📝 Bitácora de Actividad")
    b1, b2 = st.tabs(["➕ Agregar Registro", "📋 Historial y Gestión"])
    
    with b1:
        with st.form("form_bit", clear_on_submit=True):
            emp_b = st.selectbox("Asociar a Empresa", [c['Empresa'] for c in st.session_state.db_contactos] if st.session_state.db_contactos else ["Sin contactos"])
            fecha_realizada = st.date_input("Fecha Realizada", datetime.now())
            cont = st.text_area("Detalle de la actividad")
            
            if st.form_submit_button("Cargar Bitácora"):
                st.session_state.db_bitacora.append({
                    "Fecha Realizada": fecha_realizada,
                    "Empresa": emp_b,
                    "Detalle": cont
                })
                st.success("Registro guardado exitosamente.")

    with b2:
        st.subheader("🔎 Historial de Gestiones")
        if st.session_state.db_bitacora:
            df_bit = pd.DataFrame(st.session_state.db_bitacora)
            df_bit["Fecha Realizada"] = pd.to_datetime(df_bit["Fecha Realizada"]).dt.date
            
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                empresas_bit = ["Todas"] + sorted(list(df_bit["Empresa"].unique()))
                f_emp = st.selectbox("Filtrar por Empresa", empresas_bit)
            with c_f2:
                rango_fechas = st.date_input("Seleccionar Rango de Fechas", value=[])

            # --- Lógica de Filtros ---
            df_filtrado = df_bit.copy()
            if f_emp != "Todas":
                df_filtrado = df_filtrado[df_filtrado["Empresa"] == f_emp]
            if len(rango_fechas) == 2:
                f_inicio, f_fin = rango_fechas
                df_filtrado = df_filtrado[(df_filtrado["Fecha Realizada"] >= f_inicio) & (df_filtrado["Fecha Realizada"] <= f_fin)]

            # Mostramos la tabla filtrada
            st.dataframe(df_filtrado, use_container_width=True)
            
            # --- SECCIÓN DE DESCARGA Y ELIMINACIÓN ---
            st.write("---")
            col_acc1, col_acc2 = st.columns(2)

            with col_acc1:
                st.write("📂 **Exportar Datos Filtrados**")
                if not df_filtrado.empty:
                    # El nombre del archivo cambia según la empresa elegida
                    nombre_archivo = f"bitacora_{f_emp.replace(' ', '_')}.csv"
                    csv = df_filtrado.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label=f"📥 Descargar Bitácora de {f_emp}",
                        data=csv,
                        file_name=nombre_archivo,
                        mime="text/csv",
                    )
                
            with col_acc2:
                st.write("⚠️ **Zona de Peligro**")
                # Opción para eliminar el último registro o limpiar todo
                if st.button("🗑️ Eliminar último registro cargado"):
                    if len(st.session_state.db_bitacora) > 0:
                        st.session_state.db_bitacora.pop()
                        st.rerun() # Reinicia la app para mostrar los cambios
            
        else:
            st.info("No hay registros todavía.")

# --- MÓDULO COBROS (ACTUALIZADO CON DÓLAR A LA IZQUIERDA) ---
elif opcion == "Cobros":
    st.header("💰 Gestión de Cobros")
    
    if "db_cobros" not in st.session_state:
        st.session_state.db_cobros = {}

    tab_gestion, tab_mensual = st.tabs(["🔄 Actualizar Estado", "📅 Proyección Mensual"])

    if not st.session_state.db_oc:
        st.warning("Primero creá una Orden de Compra en el módulo correspondiente.")
    else:
        with tab_gestion:
            # Diccionario para seleccionar la OC
            mapeo_oc = {f"{o['ID']} | {o['Empresa']}": o for o in st.session_state.db_oc}
            oc_seleccionada_key = st.selectbox("Seleccioná OC para modificar o eliminar:", list(mapeo_oc.keys()))
            
            datos_oc = mapeo_oc[oc_seleccionada_key]
            oc_id = datos_oc['ID']

            # Cargar datos actuales si existen
            info_actual = st.session_state.db_cobros.get(oc_id, {
                "Estado": "En Tiempo", 
                "Fecha": datetime.now().date(), 
                "Notas": ""
            })

            st.markdown(f"### Gestión: {oc_id}")
            # Mostramos el dólar pautado también en el resumen de arriba
            st.write(f"**Empresa:** {datos_oc['Empresa']} | **Dólar Pautado:** {datos_oc.get('Dólar', 0)} | **Monto:** U$S {datos_oc['Monto']:,.2f}")

            with st.form(f"form_cobro_{oc_id}"):
                c1, c2 = st.columns(2)
                nuevo_estado = c1.selectbox("Estado", ["En Tiempo", "Cobrado", "En Deuda"], 
                                          index=["En Tiempo", "Cobrado", "En Deuda"].index(info_actual["Estado"]))
                nueva_fecha = c2.date_input("Fecha de Cobro (Real o Estimada)", info_actual["Fecha"])
                nuevas_notas = st.text_input("Notas adicionales", info_actual["Notas"])
                
                col_btn1, col_btn2 = st.columns(2)
                guardar = col_btn1.form_submit_button("💾 ACTUALIZAR / COBRAR")
                eliminar = col_btn2.form_submit_button("🗑️ ELIMINAR COBRO")

                if guardar:
                    st.session_state.db_cobros[oc_id] = {
                        "Estado": nuevo_estado,
                        "Fecha": nueva_fecha,
                        "Notas": nuevas_notas,
                        "Dólar": datos_oc.get('Dólar', 0), # Guardamos el dólar en el registro de cobro
                        "Monto": datos_oc['Monto'],
                        "Empresa": datos_oc['Empresa']
                    }
                    st.success(f"¡Orden {oc_id} actualizada!")
                    st.rerun()
                
                if eliminar:
                    if oc_id in st.session_state.db_cobros:
                        del st.session_state.db_cobros[oc_id]
                        st.warning(f"Se eliminó el registro de cobro de {oc_id}.")
                        st.rerun()

            st.write("---")
            st.subheader("📋 Planilla General de Cobranzas")
            if st.session_state.db_cobros:
                df_resumen = pd.DataFrame(list(st.session_state.db_cobros.values()))
                # Reordenamos para que Dólar esté a la izquierda de Monto
                cols_resumen = ["Empresa", "Dólar", "Monto", "Estado", "Fecha"]
                # Solo mostramos las columnas que existen para evitar errores
                st.dataframe(df_resumen[[c for c in cols_resumen if c in df_resumen.columns]], use_container_width=True)

        with tab_mensual:
            st.subheader("📅 Cobros por Mes")
            if st.session_state.db_cobros:
                meses_es = {
                    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
                    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
                }
                
                data_m = []
                for k, v in st.session_state.db_cobros.items():
                    f = v['Fecha']
                    data_m.append({
                        "Fecha_Sort": f,
                        "Mes_Anio": f"{meses_es[f.month]} {f.year}",
                        "OC": k,
                        "Empresa": v['Empresa'],
                        "Dólar": v.get('Dólar', 0), # Traemos el dólar
                        "Monto": v['Monto'],
                        "Estado": v['Estado']
                    })
                
                df_m = pd.DataFrame(data_m).sort_values("Fecha_Sort")
                
                for etiqueta in df_m["Mes_Anio"].unique():
                    df_mes = df_m[df_m["Mes_Anio"] == etiqueta]
                    total_mes = df_mes["Monto"].sum()
                    with st.expander(f"🗓️ {etiqueta}  —  Total: U$S {total_mes:,.2f}"):
                        # En la tabla del expander también ponemos el Dólar a la izquierda de Monto
                        st.table(df_mes[["OC", "Empresa", "Dólar", "Monto", "Estado"]])
            else:
                st.info("No hay datos de cobros.")

# --- MÓDULO HISTORIAL INTEGRAL (VERSIÓN FINAL ANTI-ERRORES) ---
elif opcion == "Historial Empresas":
    st.header("🏢 Informe Integral de Empresa")
    
    if not st.session_state.db_contactos:
        st.warning("No hay contactos registrados.")
    else:
        # 1. Buscador de Empresa
        lista_nombres = sorted(list(set([c['Empresa'] for c in st.session_state.db_contactos])))
        empresa_f = st.selectbox("🔍 Seleccioná la empresa para el reporte:", lista_nombres)
        c = next((item for item in st.session_state.db_contactos if item['Empresa'] == empresa_f), None)
        
        if c:
            # 2. Filtrar Bitácora (SOLUCIÓN AL KEYERROR)
            df_bit_all = pd.DataFrame(st.session_state.db_bitacora)
            filtro_bit = pd.DataFrame()
            if not df_bit_all.empty and 'Empresa' in df_bit_all.columns:
                filtro_bit = df_bit_all[df_bit_all['Empresa'] == empresa_f]
                # Solo seleccionamos las columnas si existen en el DataFrame
                cols_bit_deseadas = ['Fecha', 'Gestion', 'Observaciones']
                cols_bit_reales = [col for col in cols_bit_deseadas if col in filtro_bit.columns]
                filtro_bit = filtro_bit[cols_bit_reales]

            # 3. Filtrar Órdenes de Compra (Dólar a la izquierda de Monto)
            df_oc_all = pd.DataFrame(st.session_state.db_oc)
            filtro_oc = pd.DataFrame()
            if not df_oc_all.empty and 'Empresa' in df_oc_all.columns:
                df_oc_f = df_oc_all[df_oc_all['Empresa'] == empresa_f]
                # Reordenamos: Dólar antes que Monto
                cols_oc_deseadas = ["ID", "Fecha", "Referencia", "Dólar", "Monto", "Facturación", "Detalle Extra"]
                cols_oc_reales = [col for col in cols_oc_deseadas if col in df_oc_f.columns]
                filtro_oc = df_oc_f[cols_oc_reales]

            st.write("---")
            
            # 4. Construcción del HTML para Descarga Directa
            # Usamos .to_html() sin especificar columnas para que use las que ya filtramos arriba
            html_bitacora = filtro_bit.to_html(index=False) if not filtro_bit.empty else "<p>Sin registros en bitácora.</p>"
            html_oc = filtro_oc.to_html(index=False) if not filtro_oc.empty else "<p>Sin órdenes de compra.</p>"

            html_descarga = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 20px; color: #333; }}
                    .header {{ border: 2px solid #1f77b4; padding: 20px; border-radius: 10px; text-align: center; background-color: #f0f8ff; }}
                    h1 {{ color: #1f77b4; margin: 0; }}
                    h3 {{ border-bottom: 2px solid #1f77b4; padding-bottom: 5px; margin-top: 20px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; font-size: 12px; }}
                    th {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>INFORME INTEGRAL</h1>
                    <p><b>Empresa:</b> {empresa_f} | <b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y')}</p>
                </div>
                <h3>1. Datos de Contacto</h3>
                <p><b>ID:</b> {c['N°']} | <b>Actividad:</b> {c['Actividad']}</p>
                <p><b>Ubicación:</b> {c['Ciudad']}, {c.get('Provincia','')}, {c['País']}</p>
                <p><b>Teléfonos:</b> {c['T1']} / {c.get('T2','')} | <b>Mails:</b> {c['M1']} / {c.get('M2','')}</p>
                <p><b>Web:</b> {c.get('Web','N/A')} | <b>Maps:</b> {c.get('Maps','N/A')}</p>
                <p><b>Observaciones:</b> {c.get('Extra','N/A')}</p>

                <h3>2. Historial de Bitácora</h3>
                {html_bitacora}

                <h3>3. Historial de Órdenes de Compra</h3>
                {html_oc}
                
                <h3 style="text-align: right;">Total Facturado: U$S {filtro_oc['Monto'].sum() if not filtro_oc.empty else 0:,.2f}</h3>
            </body>
            </html>
            """

            # 5. Botón de Descarga
            st.download_button(
                label="📥 DESCARGAR INFORME COMPLETO (.HTML)",
                data=html_descarga,
                file_name=f"Informe_{empresa_f}.html",
                mime="text/html",
                use_container_width=True,
                type="primary"
            )

            # 6. Vista rápida en pantalla
            st.write("---")
            st.subheader(f"Vista previa: {empresa_f}")
            if not filtro_oc.empty:
                st.dataframe(filtro_oc, use_container_width=True)
            else:
                st.info("Esta empresa no tiene Órdenes de Compra.")
