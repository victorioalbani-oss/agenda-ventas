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
                t1, t2, t3 = st.text_input("Teléfono 1"), st.text_input("Teléfono 2"), st.text_input("Teléfono 3")
                m1, m2, m3 = st.text_input("Mail 1"), st.text_input("Mail 2"), st.text_input("Mail 3")
                extra = st.text_area("Dato Extra")
            
            if st.form_submit_button("Guardar Contacto"):
                cid = f"C - {len(st.session_state.db_contactos) + 1}"
                st.session_state.db_contactos.append({
                    "N°": cid, "Empresa": empresa, "País": pais, "Ciudad": ciudad,
                    "Maps": maps, "Actividad": actividad, "Web": web,
                    "T1": t1, "T2": t2, "T3": t3, "M1": m1, "M2": m2, "M3": m3, "Extra": extra
                })
                st.success(f"Contacto {cid} guardado y campos limpios.")

    with t2:
        st.subheader("📋 Lista de Empresas Registradas")
        if st.session_state.db_contactos:
            df_contactos = pd.DataFrame(st.session_state.db_contactos)
            # Mostramos la tabla con las columnas principales
            st.dataframe(df_contactos[["N°", "Empresa", "Actividad", "País", "Ciudad", "T1"]], use_container_width=True)
        else:
            st.info("No hay contactos en la lista.")

    with t3:
        st.subheader("🔍 Buscador de Detalle")
        if st.session_state.db_contactos:
            nombres = [c['Empresa'] for c in st.session_state.db_contactos]
            busqueda = st.selectbox("Seleccioná una empresa para ver todo su detalle", nombres)
            # Buscamos los datos del seleccionado
            seleccionado = next(c for c in st.session_state.db_contactos if c['Empresa'] == busqueda)
            st.write(seleccionado)
        else:
            st.write("Cargá una empresa para habilitar la búsqueda.")
            
# --- MÓDULO ÓRDENES DE COMPRA (DINÁMICO) ---
elif opcion == "Órdenes de Compra":
    st.header("🛒 Nueva Orden de Compra")
    if not st.session_state.db_contactos:
        st.warning("Primero cargá un Contacto en el módulo correspondiente.")
    else:
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
            # Buscar precio original
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
                    "ID": oc_id, "Empresa": emp_oc, "Monto": total_usd, "Fecha": fecha_oc, "Estado": "Pendiente"
                })
                st.session_state.db_items_oc_actual = []
                st.success(f"Orden {oc_id} guardada.")

# --- MÓDULO BITÁCORA ---
elif opcion == "Bitácora":
    st.header("📝 Bitácora de Actividad")
    b1, b2 = st.tabs(["Agregar Bitácora", "Historial de Registros"])
    with b1:
        with st.form("form_bit", clear_on_submit=True):
            emp_b = st.selectbox("Empresa", [c['Empresa'] for c in st.session_state.db_contactos] if st.session_state.db_contactos else ["Sin contactos"])
            horas = st.number_input("Horas", min_value=0.1)
            cont = st.text_area("Contenido")
            if st.form_submit_button("Cargar Bitácora"):
                st.session_state.db_bitacora.append({
                    "Fecha": datetime.now().date(), "Empresa": emp_b, "Horas": horas, "Detalle": cont
                })
                st.success("Bitácora del día agregada.")
