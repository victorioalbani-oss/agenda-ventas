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

# --- MÓDULO CONTACTOS ---
elif opcion == "Contactos":
    st.header("👥 Gestión de Contactos")
    t1, t2, t3, t4 = st.tabs(["Agregar Contacto", "Lista de Contactos", "Buscar/Editar", "Cliente Activo"])
    
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
            
            # Buscamos los datos
            c = next(item for item in st.session_state.db_contactos if item['Empresa'] == busqueda)
            
            # --- DISEÑO MEJORADO DEL DETALLE ---
            st.markdown(f"### {c['Empresa']} ({c['N°']})")
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**📍 Ubicación**")
                st.write(f"🏠 {c['Ciudad']}, {c.get('Provincia', '')} ({c['País']})")
                if c['Maps']:
                    st.link_button("🌐 Ver en Google Maps", c['Maps'])
                
                st.markdown("**🛠 Actividad**")
                st.write(f"💼 {c['Actividad']}")
                
            with col_b:
                st.markdown("**📞 Contacto**")
                st.write(f"📱 {c['T1']} / {c['T2']} / {c['T3']}")
                st.write(f"📧 {c['M1']} / {c['M2']} / {c['M3']}")
                if c['Web']:
                    st.write(f"💻 [{c['Web']}]({c['Web']})")

            st.markdown("**📝 Datos Extra**")
            st.info(c['Extra'] if c['Extra'] else "Sin datos adicionales.")
        else:
            st.write("Cargá una empresa para habilitar la búsqueda.")

# --- MÓDULO ÓRDENES DE COMPRA (MULTI-ARTÍCULO, FILTROS Y DESCARGA) ---
elif opcion == "Órdenes de Compra":
    st.header("🛒 Gestión de Órdenes de Compra")
    tab_carga, tab_historial = st.tabs(["➕ Nueva Orden", "📋 Historial y Gestión"])

    if not st.session_state.db_contactos:
        st.warning("Primero cargá un Contacto en el módulo correspondiente.")
    else:
        with tab_carga:
            # 1. Datos Generales de la OC (Encabezado)
            with st.container():
                c_oc1, c_oc2 = st.columns(2)
                nombre_oc = c_oc1.text_input("Nombre OC / Referencia")
                fecha_oc = c_oc2.date_input("Fecha OC", datetime.now())
                emp_oc = c_oc1.selectbox("Empresa", [c['Empresa'] for c in st.session_state.db_contactos])
                dolar = c_oc2.number_input("Dólar Pautado", value=1000.0)
                f_cobro = st.date_input("Fecha Posible Cobro")
            
            st.write("---")
            
            # 2. Agregar Artículos (Lógica de uno por uno)
            st.subheader("📦 Agregar Artículos a esta Orden")
            if st.session_state.db_productos:
                col_p1, col_p2, col_p3 = st.columns([2, 1, 1])
                
                prod_sel = col_p1.selectbox("Elegir Artículo", [p['Nombre'] for p in st.session_state.db_productos])
                cant_it = col_p2.number_input("Cantidad", min_value=1, key="cant_temp")
                
                # Buscar precio base
                p_orig = next((p['U$S'] for p in st.session_state.db_productos if p['Nombre'] == prod_sel), 0.0)
                prec_it = col_p3.number_input("Precio U$S", value=float(p_orig), key="prec_temp")
                
                if st.button("➕ AÑADIR ARTÍCULO"):
                    st.session_state.db_items_oc_actual.append({
                        "Producto": prod_sel, 
                        "Cantidad": cant_it, 
                        "U$S Unit": prec_it, 
                        "Subtotal": round(cant_it * prec_it, 2)
                    })
                    st.toast(f"{prod_sel} añadido")

            # 3. Mostrar tabla temporal de la orden actual
            if st.session_state.db_items_oc_actual:
                st.write("### Vista Previa de la Orden")
                df_temp = pd.DataFrame(st.session_state.db_items_oc_actual)
                st.table(df_temp)
                
                total_usd = df_temp["Subtotal"].sum()
                st.metric("TOTAL DE LA ORDEN", f"U$S {total_usd:,.2f}")
                
                col_fin1, col_fin2 = st.columns(2)
                if col_fin1.button("💾 GUARDAR ORDEN COMPLETA", type="primary", use_container_width=True):
                    oc_id = f"OC - {len(st.session_state.db_oc) + 1}"
                    st.session_state.db_oc.append({
                        "ID": oc_id, 
                        "Empresa": emp_oc, 
                        "Monto": total_usd, 
                        "Fecha": fecha_oc, 
                        "Estado": "Pendiente", 
                        "Referencia": nombre_oc,
                        "Items": len(st.session_state.db_items_oc_actual)
                    })
                    st.session_state.db_items_oc_actual = [] # Limpiamos para la próxima
                    st.success(f"¡{oc_id} guardada exitosamente!")
                    st.rerun()

                if col_fin2.button("🗑️ Cancelar / Limpiar Items", use_container_width=True):
                    st.session_state.db_items_oc_actual = []
                    st.rerun()

        with tab_historial:
            st.subheader("🔎 Filtros y Descargas")
            if st.session_state.db_oc:
                df_hist = pd.DataFrame(st.session_state.db_oc)
                df_hist["Fecha"] = pd.to_datetime(df_hist["Fecha"]).dt.date
                
                c1, c2 = st.columns(2)
                with c1:
                    emp_busc = st.selectbox("Filtrar por Empresa", ["Todas"] + sorted(list(df_hist["Empresa"].unique())))
                with c2:
                    rango_oc = st.date_input("Filtrar por Rango de Fechas", value=[])

                df_f = df_hist.copy()
                if emp_busc != "Todas":
                    df_f = df_f[df_f['Empresa'] == emp_busc]
                if len(rango_oc) == 2:
                    df_f = df_f[(df_f["Fecha"] >= rango_oc[0]) & (df_f["Fecha"] <= rango_oc[1])]

                # --- BOTONES DE DESCARGA RÁPIDA ---
                if not df_f.empty:
                    st.write("### ⬇️ Exportar Reporte")
                    btn_col1, btn_col2 = st.columns(2)
                    csv = df_f.to_csv(index=False).encode('utf-8')
                    btn_col1.download_button("📥 DESCARGAR EXCEL", csv, f"OC_{emp_busc}.csv", "text/csv", use_container_width=True)
                    if btn_col2.button("📄 PREPARAR PDF", use_container_width=True):
                        st.table(df_f)
                
                st.write("---")
                st.dataframe(df_f, use_container_width=True)
                st.metric("Total Facturado en este filtro", f"U$S {df_f['Monto'].sum():,.2f}")

                # --- ELIMINACIÓN ---
                st.write("---")
                with st.expander("🗑️ Zona de eliminación"):
                    id_del = st.selectbox("ID a eliminar", df_f["ID"].tolist() if not df_f.empty else ["Ninguno"])
                    if st.button("Eliminar Orden Seleccionada"):
                        st.session_state.db_oc = [o for o in st.session_state.db_oc if o["ID"] != id_del]
                        st.rerun()
            else:
                st.info("No hay órdenes registradas.")
        
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
