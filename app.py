import streamlit as st
import pandas as pd

# Configuración para que se vea bien en celular y PC
st.set_page_config(page_title="Agenda de Ventas", layout="wide")

# Inicialización de las bases de datos en la memoria del navegador
if 'db_contactos' not in st.session_state: st.session_state.db_contactos = []
if 'db_productos' not in st.session_state: st.session_state.db_productos = []

st.sidebar.title("Menú Principal")
opcion = st.sidebar.radio("Ir a:", ["Contactos", "Productos", "Bitácora", "OC", "Cobros"])

if opcion == "Contactos":
    st.header("👥 Gestión de Contactos")
    with st.form("form_contacto", clear_on_submit=True):
        empresa = st.text_input("Nombre de la Empresa")
        if st.form_submit_button("Guardar Contacto"):
            st.session_state.db_contactos.append({"Empresa": empresa})
            st.success("¡Contacto Guardado!")
    
    if st.session_state.db_contactos:
        st.write("### Lista de Contactos")
        st.table(pd.DataFrame(st.session_state.db_contactos))

elif opcion == "Productos":
    st.header("📦 Catálogo de Productos")
    with st.form("form_producto", clear_on_submit=True):
        nombre = st.text_input("Nombre del Artículo")
        # CORRECCIÓN: Usamos precio_uss en lugar de u$s
        precio_uss = st.number_input("Precio Unitario U$S", min_value=0.0)
        if st.form_submit_button("Agregar Artículo"):
            st.session_state.db_productos.append({"Artículo": nombre, "Precio U$S": precio_uss})
            st.info("Artículo agregado correctamente")
            
    if st.session_state.db_productos:
        st.write("### Listado de Artículos")
        st.dataframe(pd.DataFrame(st.session_state.db_productos))

else:
    st.warning("Módulo en desarrollo (Bitácora, OC y Cobros)")
