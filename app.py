import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración de página para Celular y PC
st.set_page_config(page_title="Mi Agenda de Ventas", layout="wide")

# --- INICIALIZACIÓN DE DATOS ---
for db in ['contactos', 'productos', 'bitacora', 'oc']:
    if f'db_{db}' not in st.session_state:
        st.session_state[f'db_{db}'] = []

# --- MENÚ LATERAL ---
st.sidebar.title("Menú Principal")
opcion = st.sidebar.radio("Ir a:", ["Bitácora", "Órdenes de Compra", "Cobros", "Contactos", "Productos"])

# --- MÓDULO CONTACTOS ---
if opcion == "Contactos":
    st.header("👥 Gestión de Contactos")
    t1, t2, t3 = st.tabs(["Agregar Contacto", "Lista de Contactos", "Buscar/Editar"])
    
    with t1:
        with st.form("form_contacto", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                empresa = st.text_input("Empresa")
                pais = st.text_input("País")
                prov = st.text_input("Provincia")
                maps = st.text_input("Dirección Google Maps")
            with col2:
                actividad = st.text_input("Actividad")
                web = st.text_input("Página Web")
                extra = st.text_area("Dato Extra")
            
            st.write("---")
            c1, c2 = st.columns(2)
            with c1:
                tel1 = st.text_input("Teléfono 1")
                mail1 = st.text_input("Mail 1")
            
            if st.form_submit_button("Guardar Contacto"):
                cid = f"C - {len(st.session_state.db_contactos) + 1}"
                st.session_state.db_contactos.append({"N°": cid, "Empresa": empresa, "País": pais, "M1": mail1, "T1": tel1})
                st.success(f"Contacto {cid} guardado.")

# --- MÓDULO PRODUCTOS ---
elif opcion == "Productos":
    st.header("📦 Catálogo de Artículos")
    with st.form("form_prod", clear_on_submit=True):
        nombre = st.text_input("Nombre Artículo")
        u$s = st.number_input("Precio U$S", min_value=0.0)
        if st.form_submit_button("Agregar Artículo"):
            aid = f"Art. - {len(st.session_state.db_productos) + 1}"
            st.session_state.db_productos.append({"N°": aid, "Nombre": nombre, "Precio": u$s})
            st.info(f"Artículo {aid} agregado.")

# --- MÓDULO ÓRDENES DE COMPRA (DINÁMICO) ---
elif opcion == "Órdenes de Compra":
    st.header("🛒 Nueva Orden de Compra")
    if not st.session_state.db_contactos:
        st.warning("Primero debés cargar un Contacto.")
    else:
        with st.container():
            col_a, col_b = st.columns(2)
            emp_sel = col_a.selectbox("Empresa", [c['Empresa'] for c in st.session_state.db_contactos])
            dolar = col_b.number_input("Dólar Pautado", value=1000.0)
            f_cobro = st.date_input("Fecha Posible Cobro")
        
        # Aquí podés seguir agregando la lógica de ítems múltiples...
        st.write("Módulo en construcción: Aquí podrás sumar los artículos del catálogo.")

# NOTA: El resto de los módulos (Bitácora y Cobros) se activan igual.
