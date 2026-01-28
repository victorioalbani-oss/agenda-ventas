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
opcion = st.sidebar.radio("Ir a:", ["Bitácora", "Órdenes de Compra", "Cobros", "Contactos", "Productos"])

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

# --- MÓDULO CONTACTOS (LISTAS INDEPENDIENTES) ---
elif opcion == "Contactos":
    st.header("👥 Gestión de Contactos y Seguimiento")
    
    # Inicializamos las listas en el session_state si no existen
    if "list_activos" not in st.session_state: st.session_state.list_activos = []
    if "list_interesados" not in st.session_state: st.session_state.list_interesados = []
    if "list_visitar" not in st.session_state: st.session_state.list_visitar = []
    if "list_otros" not in st.session_state: st.session_state.list_otros = []

    tabs = st.tabs(["➕ Agregar", "📋 Lista Total", "🔍 Detalle", "✅ Clientes Activos", "⭐ Interesados", "📍 Por Visitar", "👤 De Otro"])
    
    # 1. AGREGAR CONTACTO
    with tabs[0]:
        with st.form("form_contacto", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                empresa = st.text_input("Empresa")
                actividad = st.text_input("Actividad")
                ciudad = st.text_input("Ciudad")
            with col2:
                tel1 = st.text_input("Teléfono 1")
                mail1 = st.text_input("Mail 1")
                extra = st.text_area("Dato Extra")
            
            if st.form_submit_button("Guardar Contacto"):
                cid = f"C - {len(st.session_state.db_contactos) + 1}"
                st.session_state.db_contactos.append({
                    "N°": cid, "Empresa": empresa, "Actividad": actividad,
                    "Ciudad": ciudad, "T1": tel1, "M1": mail1, "Extra": extra
                })
                st.success(f"Empresa {empresa} guardada.")

    # 2. LISTA TOTAL
    with tabs[1]:
        if st.session_state.db_contactos:
            st.dataframe(pd.DataFrame(st.session_state.db_contactos), use_container_width=True)
        else:
            st.info("No hay contactos.")

    # 3. BUSCADOR Y ASIGNADOR DE ESTADOS
    with tabs[2]:
        if st.session_state.db_contactos:
            nombres = [c['Empresa'] for c in st.session_state.db_contactos]
            sel_emp = st.selectbox("Seleccioná una empresa para asignar a una lista:", nombres)
            
            st.write(f"### Gestionar: {sel_emp}")
            c1, c2, c3, c4 = st.columns(4)
            
            if c1.button("✅ Activo"):
                if sel_emp not in st.session_state.list_activos:
                    st.session_state.list_activos.append(sel_emp)
                    st.toast(f"{sel_emp} movido a Activos")
            
            if c2.button("⭐ Interesado"):
                if sel_emp not in st.session_state.list_interesados:
                    st.session_state.list_interesados.append(sel_emp)
                    st.toast(f"{sel_emp} movido a Interesados")

            if c3.button("📍 Por Visitar"):
                if sel_emp not in st.session_state.list_visitar:
                    st.session_state.list_visitar.append(sel_emp)
                    st.toast(f"{sel_emp} movido a Por Visitar")

            if c4.button("👤 De Otro"):
                if sel_emp not in st.session_state.list_otros:
                    st.session_state.list_otros.append(sel_emp)
                    st.toast(f"{sel_emp} movido a De Otro")
        else:
            st.warning("Cargá un contacto primero.")

    # --- LÓGICA DE LAS PESTAÑAS DE ESTADO ---
    def render_lista_seguimiento(titulo, lista_key):
        st.subheader(titulo)
        lista_actual = st.session_state[lista_key]
        if lista_actual:
            for emp_nombre in lista_actual:
                with st.expander(f"🏢 {emp_nombre}"):
                    # Buscamos los datos completos de la empresa para mostrar algo de info
                    datos = next((item for item in st.session_state.db_contactos if item['Empresa'] == emp_nombre), None)
                    if datos:
                        st.write(f"**Actividad:** {datos['Actividad']} | **Tel:** {datos['T1']}")
                    
                    if st.button(f"❌ Quitar de {titulo}", key=f"btn_{lista_key}_{emp_nombre}"):
                        st.session_state[lista_key].remove(emp_nombre)
                        st.rerun()
        else:
            st.info("Esta lista está vacía.")

    with tabs[3]: render_lista_seguimiento("Clientes Activos", "list_activos")
    with tabs[4]: render_lista_seguimiento("Clientes Interesados", "list_interesados")
    with tabs[5]: render_lista_seguimiento("Clientes por Visitar", "list_visitar")
    with tabs[6]: render_lista_seguimiento("Clientes de Otro", "list_otros")
# --- MÓDULO ÓRDENES DE COMPRA (FINAL: MULTI-ARTÍCULO + PDF + ELIMINAR) ---
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
                dolar = c_oc2.number_input("Dólar Pautado", value=1000.0)
            
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
                if c_fin1.button("💾 GUARDAR ORDEN COMPLETA", type="primary"):
                    oc_id = f"OC - {len(st.session_state.db_oc) + 1}"
                    st.session_state.db_oc.append({
                        "ID": oc_id, "Empresa": emp_oc, "Monto": total_usd, 
                        "Fecha": fecha_oc, "Referencia": nombre_oc
                    })
                    st.session_state.db_items_oc_actual = []
                    st.success("Orden guardada!")
                    st.rerun()
                if c_fin2.button("🗑️ Vaciar lista"):
                    st.session_state.db_items_oc_actual = []
                    st.rerun()

        with tab_historial:
            st.subheader("🔎 Filtros y Reportes")
            if st.session_state.db_oc:
                df_hist = pd.DataFrame(st.session_state.db_oc)
                df_hist["Fecha"] = pd.to_datetime(df_hist["Fecha"]).dt.date
                
                f_col1, f_col2 = st.columns(2)
                with f_col1:
                    emp_busc = st.selectbox("Empresa", ["Todas"] + sorted(list(df_hist["Empresa"].unique())))
                with f_col2:
                    rango = st.date_input("Rango de fechas", value=[])

                df_f = df_hist.copy()
                if emp_busc != "Todas": df_f = df_f[df_f['Empresa'] == emp_busc]
                if len(rango) == 2: df_f = df_f[(df_f["Fecha"] >= rango[0]) & (df_f["Fecha"] <= rango[1])]

                # --- BOTONES DE DESCARGA ---
                if not df_f.empty:
                    st.write("### ⬇️ Descargar")
                    d_col1, d_col2 = st.columns(2)
                    
                    # Excel
                    csv = df_f.to_csv(index=False).encode('utf-8')
                    d_col1.download_button("📥 EXCEL", csv, f"OC_{emp_busc}.csv", use_container_width=True)
                    
                    # PDF (HTML prolijo para guardar como PDF)
                    html = f"<h2>Reporte OC: {emp_busc}</h2>{df_f.to_html()}<br><h3>Total: U$S {df_f['Monto'].sum():,.2f}</h3>"
                    d_col2.download_button("📄 PDF", html, f"OC_{emp_busc}.html", "text/html", use_container_width=True)

                st.write("---")
                st.dataframe(df_f, use_container_width=True)

                # --- ELIMINAR ORDEN ---
                with st.expander("🗑️ Eliminar una Orden"):
                    id_a_borrar = st.selectbox("Elegí el ID para borrar", df_f["ID"].tolist())
                    if st.button("Confirmar Borrado"):
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
