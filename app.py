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

# --- MÓDULO ÓRDENES DE COMPRA (DINÁMICO) ---
elif opcion == "Órdenes de Compra":
    st.header("🛒 Gestión de Órdenes de Compra")
    
    # Creamos dos pestañas: una para cargar y otra para ver el historial
    tab_carga, tab_historial = st.tabs(["➕ Nueva Orden", "📋 Historial y Búsqueda"])

    if not st.session_state.db_contactos:
        st.warning("Primero cargá un Contacto en el módulo correspondiente.")
    else:
        with tab_carga:
            with st.container():
                c_oc1, c_oc2 = st.columns(2)
                nombre_oc = c_oc1.text_input("Nombre OC")
                fecha_oc = c_oc2.date_input("Fecha OC", datetime.now())
                emp_oc = c_oc1.selectbox("Empresa", [c['Empresa'] for c in st.session_state.db_contactos])
                dolar = c_oc2.number_input("Dólar Pautado", value=1000.0)
                f_cobro = st.date_input("Fecha Posible Cobro")

            st.write("---")
            st.subheader("Agregar Artículos")
            if st.session_state.db_productos:
                prod_sel = st.selectbox("Elegir Artículo", [p['Nombre'] for p in st.session_state.db_productos])
                col_it1, col_it2 = st.columns(2)
                cant_it = col_it1.number_input("Cantidad", min_value=1)
                p_orig = next(p['U$S'] for p in st.session_state.db_productos if p['Nombre'] == prod_sel)
                prec_it = col_it2.number_input("Precio Unitario U$S", value=float(p_orig))
                
                if st.button("➕ Añadir a esta OC"):
                    st.session_state.db_items_oc_actual.append({
                        "Producto": prod_sel, "Cantidad": cant_it, "U$S Unit": prec_it, "Subtotal": cant_it * prec_it
                    })
            
            if st.session_state.db_items_oc_actual:
                df_items = pd.DataFrame(st.session_state.db_items_oc_actual)
                st.table(df_items)
                total_usd = df_items["Subtotal"].sum()
                st.metric("Total OC", f"U$S {total_usd}")
                
                if st.button("💾 GUARDAR ORDEN COMPLETA"):
                    oc_id = f"OC - {len(st.session_state.db_oc) + 1}"
                    st.session_state.db_oc.append({
                        "ID": oc_id, "Empresa": emp_oc, "Monto": total_usd, 
                        "Fecha": str(fecha_oc), "Estado": "Pendiente", "Referencia": nombre_oc
                    })
                    st.session_state.db_items_oc_actual = []
                    st.success(f"Orden {oc_id} guardada.")

        with tab_historial:
            st.subheader("🔎 Buscar por Empresa")
            if st.session_state.db_oc:
                # Sacamos la lista de empresas que tienen OCs
                empresas_con_oc = sorted(list(set([o['Empresa'] for o in st.session_state.db_oc])))
                empresa_buscada = st.selectbox("Seleccionar Empresa para filtrar historial", ["Todas"] + empresas_con_oc)
                
                df_historial = pd.DataFrame(st.session_state.db_oc)
                
                if empresa_buscada != "Todas":
                    df_historial = df_historial[df_historial['Empresa'] == empresa_buscada]
                
                st.dataframe(df_historial, use_container_width=True)
            else:
                st.info("No hay órdenes de compra registradas todavía.")

# --- MÓDULO BITÁCORA ---
elif opcion == "Bitácora":
    st.header("📝 Bitácora de Actividad")
    b1, b2 = st.tabs(["➕ Agregar Registro", "📋 Historial y Filtros"])
    
    with b1:
        with st.form("form_bit", clear_on_submit=True):
            emp_b = st.selectbox("Asociar a Empresa", [c['Empresa'] for c in st.session_state.db_contactos] if st.session_state.db_contactos else ["Sin contactos"])
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                fecha_realizada = st.date_input("Fecha Realizada", datetime.now())
            with col_b2:
                fecha_recordar = st.date_input("Fecha a Recordar", datetime.now())
            
            horas = st.number_input("Horas dedicadas", min_value=0.0, step=0.5)
            cont = st.text_area("Detalle de la actividad")
            
            if st.form_submit_button("Cargar Bitácora"):
                st.session_state.db_bitacora.append({
                    "Fecha Realizada": fecha_realizada,
                    "Fecha Recordar": fecha_recordar,
                    "Empresa": emp_b,
                    "Horas": horas,
                    "Detalle": cont
                })
                st.success("Registro guardado.")

    with b2:
        st.subheader("🔎 Historial de Gestiones")
        if st.session_state.db_bitacora:
            df_bit = pd.DataFrame(st.session_state.db_bitacora)
            
            # Aseguramos que las columnas de fecha sean tipo datetime para comparar
            df_bit["Fecha Realizada"] = pd.to_datetime(df_bit["Fecha Realizada"]).dt.date
            
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                empresas_bit = ["Todas"] + sorted(list(df_bit["Empresa"].unique()))
                f_emp = st.selectbox("Filtrar por Empresa", empresas_bit)
            with c_f2:
                # FILTRO DE RANGO: Al pasar una tupla vacía [] permitimos seleccionar dos fechas
                rango_fechas = st.date_input("Seleccionar Rango de Fechas", value=[])

            # Aplicamos Filtros
            df_filtrado = df_bit.copy()
            
            if f_emp != "Todas":
                df_filtrado = df_filtrado[df_filtrado["Empresa"] == f_emp]
            
            # Lógica para el Rango de Fechas
            if len(rango_fechas) == 2:
                fecha_inicio, fecha_fin = rango_fechas
                df_filtrado = df_filtrado[(df_filtrado["Fecha Realizada"] >= fecha_inicio) & 
                                          (df_filtrado["Fecha Realizada"] <= fecha_fin)]

            st.dataframe(df_filtrado, use_container_width=True)
            
            # Extra: Sumatoria de horas en el rango seleccionado
            if "Horas" in df_filtrado.columns:
                total_horas = df_filtrado["Horas"].sum()
                st.info(f"⏱️ Total de horas en este filtro: {total_horas}")
        else:
            st.info("No hay registros todavía.")
