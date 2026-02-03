import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. Configuración de página
st.set_page_config(page_title="Vico S.A.", page_icon="🌎", layout="wide")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- INICIO DEL BLOQUE DE LOGIN (PONELO ACÁ) ---
def login_nube():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.markdown("<h1 style='text-align: center;'>🔐 Acceso al CRM</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                user_input = st.text_input("Usuario")
                pass_input = st.text_input("Contraseña", type="password")
                submit = st.form_submit_button("Entrar", use_container_width=True)
                
                if submit:
                    try:
                        # Buscamos en la pestaña 'credenciales' del Sheets
                        df_creds = conn.read(worksheet="credenciales", ttl=0)
                        valido = df_creds[(df_creds['usuario'] == user_input) & 
                                          (df_creds['clave'].astype(str) == str(pass_input))]
                        
                        if not valido.empty:
                            st.session_state.autenticado = True
                            st.rerun()
                        else:
                            st.error("Usuario o contraseña incorrectos")
                    except Exception as e:
                        st.error("Error: No se pudo verificar la pestaña 'credenciales' en Google Sheets.")
        return False
    return True

# Verificamos login antes de seguir con el resto del código
if not login_nube():
    st.stop() 
# --- FIN DEL BLOQUE DE LOGIN ---

# 3. Función para cargar TODO desde Google Sheets
def cargar_datos_nube():
    mapeo = {
        "contactos": "db_contactos",
        "productos": "db_productos",
        "bitacora": "db_bitacora",
        "oc": "db_oc",
        "cobros": "db_cobros",
        "Empresa": "db_historial_empresa",
        # AGREGAMOS ESTO:
        "list_activos": "list_activos",
        "list_interesados": "list_interesados",
        "list_visitar": "list_visitar",
        "list_otros": "list_otros"
    }
    
    for hoja, sesion in mapeo.items():
        try:
            df = conn.read(worksheet=hoja, ttl=0)
            datos = df.dropna(how="all").to_dict('records')
            
            if hoja == "cobros":
                st.session_state[sesion] = {str(item['OC_ID']): item for item in datos if 'OC_ID' in item}
            # NUEVO ARREGLO PARA LAS 4 LISTAS:
            elif hoja in ["list_activos", "list_interesados", "list_visitar", "list_otros"]:
                st.session_state[sesion] = [item['Empresa'] for item in datos if 'Empresa' in item]
            else:
                st.session_state[sesion] = datos
        except Exception:
            # Si falla cobros, iniciamos diccionario vacío, sino lista vacía
            st.session_state[sesion] = {} if hoja == "cobros" else []

# 4. Función para subir datos
def sincronizar(pestaña, datos):
    # Solo salimos si es None. Si es una lista vacía [], queremos que siga para limpiar el Sheets.
    if datos is None:
        return
    try:
        # Si la lista está vacía, creamos un DataFrame vacío con la columna correspondiente
        if isinstance(datos, list) and len(datos) == 0:
            # Si es de las listas de seguimiento, mantenemos el encabezado "Empresa"
            if pestaña in ["list_activos", "list_interesados", "list_visitar", "list_otros"]:
                df = pd.DataFrame(columns=["Empresa"])
            else:
                df = pd.DataFrame() # Para otras tablas
        else:
            df = pd.DataFrame(datos)
            
        conn.update(worksheet=pestaña, data=df)
        st.toast(f"✅ Sincronizado en Nube: {pestaña}")
    except Exception as e:
        st.error(f"⚠️ Error al guardar en {pestaña}: {e}")

# 5. Inicialización de Estados
variables_necesarias = [
    'db_contactos', 'db_productos', 'db_bitacora', 'db_oc', 'db_cobros', 'db_historial_empresa',
    'list_activos', 'list_interesados', 'list_visitar', 'list_otros' # <--- Agregadas
]
if not all(var in st.session_state for var in variables_necesarias):
    cargar_datos_nube()

if 'db_items_oc_actual' not in st.session_state:
    st.session_state.db_items_oc_actual = []

# 6. Menú Lateral
st.sidebar.title("Menú Principal")
if st.sidebar.button("🔄 Recargar desde Nube"):
    cargar_datos_nube()
    st.success("¡Datos sincronizados!")
    st.rerun()

opcion = st.sidebar.radio("Ir a:", ["Bitácora", "Órdenes de Compra", "Cobros", "Contactos", "Productos", "Historial Empresas"])

# --- MÓDULO PRODUCTOS (CON ADVERTENCIAS DE GESTIÓN) ---
if opcion == "Productos":
    st.header("📦 Gestión de Artículos")
    tab_p1, tab_p2, tab_p3 = st.tabs(["Agregar Artículos", "Listado de Artículos", "🔍 Editar / Eliminar"])
    
    with tab_p1:
        # Mensaje de consejo para la creación de nuevos artículos
        st.info("""💡 **Consejo de carga:** Aconsejo agregar el Artículo como **'AÑO/MES - Articulo X'**. 
        Por ejemplo: **'2026/1 - Artículo 54'** (incluso si querés ponerle día también podés, queda en vos). 
        Esto asegura que el precio quede asociado a un periodo específico.""")
        
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
                nuevo_prod = {
                    "N°": aid, "Nombre": n_art, "Dimensiones": dims, 
                    "Tejido": tej, "U$S": precio, "Cant/Pallet": cant_pal, "Peso/Pallet": peso_pal
                }
                st.session_state.db_productos.append(nuevo_prod)
                sincronizar("productos", st.session_state.db_productos)
                st.success(f"Artículo {aid} guardado.")
                st.rerun()
                
    with tab_p2:
        if st.session_state.db_productos:
            df_prods = pd.DataFrame(st.session_state.db_productos)
            if "U$S" in df_prods.columns:
                df_prods["U$S"] = df_prods["U$S"].map("{:,.2f}".format)
            st.dataframe(df_prods, use_container_width=True)
            st.button("Descargar Listado PDF (Simulado)")
        else:
            st.info("No hay productos cargados.")

    with tab_p3:
        if not st.session_state.db_productos:
            st.info("No hay productos para editar.")
        else:
            # Mensaje de advertencia crítico para la edición
            st.warning("""⚠️ **Atención:** No aconsejo editar porque se modifican todas las OC relacionadas y capaz hay viejas. 
            Por eso es mejor agregar Artículos nuevos como **'AÑO/MES - Articulo X'** para asociar el producto y precio a una fecha 
            y no tener el problema de viejas OC modificadas.""")
            
            nombres_prod = [p['Nombre'] for p in st.session_state.db_productos]
            prod_sel = st.selectbox("Elegí el artículo a MODIFICAR o ELIMINAR:", nombres_prod)
            
            idx_p = next(i for i, p in enumerate(st.session_state.db_productos) if p['Nombre'] == prod_sel)
            p_actual = st.session_state.db_productos[idx_p]

            with st.form("form_edit_prod"):
                st.write(f"### Editando: {p_actual['N°']}")
                edit_nom = st.text_input("Nombre Artículo", value=p_actual['Nombre'])
                ce1, ce2 = st.columns(2)
                with ce1:
                    edit_dims = st.text_input("Dimensiones", value=p_actual.get('Dimensiones', ''))
                    edit_tej = st.text_input("Tejido", value=p_actual.get('Tejido', ''))
                    edit_precio = st.number_input("Precio Unitario U$S", value=float(p_actual.get('U$S', 0.0)))
                with ce2:
                    edit_cant = st.number_input("Cantidad por Pallet", value=int(p_actual.get('Cant/Pallet', 0)))
                    edit_peso = st.number_input("Peso 1 Pallet", value=float(p_actual.get('Peso/Pallet', 0.0)))
                
                col_eb1, col_eb2 = st.columns(2)
                if col_eb1.form_submit_button("💾 GUARDAR CAMBIOS"):
                    st.session_state.db_productos[idx_p] = {
                        "N°": p_actual['N°'], "Nombre": edit_nom, "Dimensiones": edit_dims, 
                        "Tejido": edit_tej, "U$S": edit_precio, "Cant/Pallet": edit_cant, "Peso/Pallet": edit_peso
                    }
                    sincronizar("productos", st.session_state.db_productos)
                    st.success("✅ Artículo actualizado en la nube")
                    st.rerun()

            st.write("---")
            if st.button("🗑️ ELIMINAR ESTE ARTÍCULO DEFINITIVAMENTE"):
                st.session_state.db_productos.pop(idx_p)
                sincronizar("productos", st.session_state.db_productos)
                st.warning(f"Artículo '{prod_sel}' eliminado de la nube.")
                st.rerun()

# --- MÓDULO CONTACTOS (CON FILTROS BLINDADOS) ---
elif opcion == "Contactos":
    st.header("👥 Gestión de Contactos")
    
    if "list_activos" not in st.session_state: st.session_state.list_activos = []
    if "list_interesados" not in st.session_state: st.session_state.list_interesados = []
    if "list_visitar" not in st.session_state: st.session_state.list_visitar = []
    if "list_otros" not in st.session_state: st.session_state.list_otros = []

    t1, t2, t3, t_act, t_int, t_vis, t_otr = st.tabs([
        "Agregar Contacto", "Lista", "🔍 Editar Datos", "✅ Activos", "⭐ Interesados", "📍 Visitar", "👤 Otros"
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
                tel1 = st.text_input("Teléfono 1")
                tel2 = st.text_input("Teléfono 2")
                mail1 = st.text_input("Mail 1")
                mail2 = st.text_input("Mail 2")
                extra = st.text_area("Dato Extra")
            
            if st.form_submit_button("Guardar Contacto"):
                if empresa:
                    cid = f"C - {len(st.session_state.db_contactos) + 1}"
                    nuevo = {
                        "N°": cid, "Empresa": empresa, "País": pais, "Ciudad": ciudad,
                        "Provincia": prov, "Maps": maps, "Actividad": actividad, "Web": web,
                        "T1": tel1, "T2": tel2, "M1": mail1, "M2": mail2, "Extra": extra
                    }
                    st.session_state.db_contactos.append(nuevo)
                    sincronizar("contactos", st.session_state.db_contactos)
                    st.success(f"Contacto {cid} guardado.")
                    st.rerun()
                else:
                    st.warning("Por favor, ingresa el nombre de la empresa.")

    with t2:
        if st.session_state.db_contactos:
            st.subheader("🔍 Buscador de Contactos")
            # Convertimos a DataFrame y limpiamos nulos para que el filtro no rompa
            df_contactos = pd.DataFrame(st.session_state.db_contactos).fillna("")

            # --- FILTROS EN COLUMNAS CON VALIDACIÓN ---
            c_f1, c_f2, c_f3 = st.columns(3)
            with c_f1:
                f_empresa = st.text_input("🏢 Empresa", placeholder="Buscar nombre...")
                # VALIDACIÓN ANTI-ERROR: Filtramos nulos antes de ordenar
                u_act = df_contactos["Actividad"].unique() if "Actividad" in df_contactos.columns else []
                lista_act = ["Todas"] + sorted([str(x) for x in u_act if x])
                f_actividad = st.selectbox("🛠️ Actividad", lista_act)
            
            with c_f2:
                u_pais = df_contactos["País"].unique() if "País" in df_contactos.columns else []
                lista_pais = ["Todos"] + sorted([str(x) for x in u_pais if x])
                f_pais = st.selectbox("🌎 País", lista_pais)
                
                u_prov = df_contactos["Provincia"].unique() if "Provincia" in df_contactos.columns else []
                lista_prov = ["Todas"] + sorted([str(x) for x in u_prov if x])
                f_prov = st.selectbox("📍 Provincia", lista_prov)
            
            with c_f3:
                f_ciudad = st.text_input("🏙️ Ciudad", placeholder="Buscar ciudad...")

            # --- LÓGICA DE FILTRADO ---
            df_filtrado = df_contactos.copy()
            if f_empresa:
                df_filtrado = df_filtrado[df_filtrado["Empresa"].str.contains(f_empresa, case=False, na=False)]
            if f_actividad != "Todas":
                df_filtrado = df_filtrado[df_filtrado["Actividad"] == f_actividad]
            if f_pais != "Todos":
                df_filtrado = df_filtrado[df_filtrado["País"] == f_pais]
            if f_prov != "Todas":
                df_filtrado = df_filtrado[df_filtrado["Provincia"] == f_prov]
            if f_ciudad:
                df_filtrado = df_filtrado[df_filtrado["Ciudad"].str.contains(f_ciudad, case=False, na=False)]

            st.write("---")
            num_res = len(df_filtrado)
            if num_res > 0:
                st.write(f"📊 Mostrando **{num_res}** contactos encontrados:")
                st.dataframe(df_filtrado, use_container_width=True)
            else:
                st.warning("❌ No se encontraron contactos.")
        else:
            st.info("No hay contactos en la lista.")

    with t3:
        if st.session_state.db_contactos:
            nombres = [c['Empresa'] for c in st.session_state.db_contactos]
            busc = st.selectbox("Seleccioná la empresa que querés MODIFICAR:", nombres)
            idx = next(i for i, item in enumerate(st.session_state.db_contactos) if item['Empresa'] == busc)
            c = st.session_state.db_contactos[idx]

            st.markdown(f"### Edición de: {c['Empresa']}")
            with st.form("edit_contacto_form"):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    new_nom = st.text_input("Nombre Empresa", value=c.get('Empresa', ''))
                    new_act = st.text_input("Actividad", value=c.get('Actividad', ''))
                    new_pais = st.text_input("País", value=c.get('País', ''))
                    new_prov = st.text_input("Provincia", value=c.get('Provincia', '')) # Agregado
                    new_ciudad = st.text_input("Ciudad", value=c.get('Ciudad', ''))
                    new_maps = st.text_input("Maps", value=c.get('Maps',''))
                with col_e2:
                    # Aplicamos el seguro de la comilla "'" para evitar errores en Excel
                    new_tel1 = st.text_input("Teléfono 1", value=str(c.get('T1', '')).replace("'", ""))
                    new_tel2 = st.text_input("Teléfono 2", value=str(c.get('T2', '')).replace("'", ""))
                    new_mail1 = st.text_input("Mail 1", value=c.get('M1', ''))
                    new_mail2 = st.text_input("Mail 2", value=c.get('M2',''))
                    new_web = st.text_input("Web", value=c.get('Web',''))
                    new_extra = st.text_area("Notas / Extra", value=str(c.get('Extra','')).replace("'", ""))
                
                if st.form_submit_button("Guardar Cambios"):
                    st.session_state.db_contactos[idx] = {
                        "N°": c['N°'], 
                        "Empresa": new_nom, 
                        "País": new_pais, 
                        "Ciudad": new_ciudad,
                        "Provincia": new_prov, # Guardado correctamente
                        "Maps": new_maps, 
                        "Actividad": new_act, 
                        "Web": new_web, 
                        "T1": f"'{new_tel1}", # Seguro de Excel
                        "T2": f"'{new_tel2}", # Seguro de Excel
                        "M1": new_mail1, 
                        "M2": new_mail2, 
                        "Extra": f"'{new_extra}" # Seguro de Excel
                    }
                    sincronizar("contactos", st.session_state.db_contactos)
                    st.success("✅ ¡Vico S.A. actualizado correctamente!")
                    st.rerun()

    # --- LISTAS DE SEGUIMIENTO (Sin cambios, pero asegurando renderizado) ---
    def render_lista_seguimiento(titulo, lista_key):
        st.subheader(titulo)
        if st.session_state.db_contactos:
            nombres_totales = sorted([c['Empresa'] for c in st.session_state.db_contactos])
            col_add, col_btn = st.columns([3, 1])
            with col_add:
                emp_a_agregar = st.selectbox(f"Añadir a {titulo}:", [""] + nombres_totales, key=f"sel_{lista_key}")
            with col_btn:
                st.write("##")
                if st.button("➕", key=f"btn_add_{lista_key}"):
                    if emp_a_agregar and emp_a_agregar not in st.session_state[lista_key]:
                        st.session_state[lista_key].append(emp_a_agregar)
                        df_p = pd.DataFrame(st.session_state[lista_key], columns=["Empresa"])
                        sincronizar(lista_key, df_p.to_dict('records'))
                        st.rerun()

        lista = st.session_state[lista_key]
        if lista:
            for emp_nombre in lista:
                with st.expander(f"🏢 {emp_nombre}"):
                    if st.button(f"Quitar", key=f"del_{lista_key}_{emp_nombre}"):
                        st.session_state[lista_key].remove(emp_nombre)
                        df_p = pd.DataFrame(st.session_state[lista_key], columns=["Empresa"])
                        sincronizar(lista_key, df_p.to_dict('records'))
                        st.rerun()

    with t_act: render_lista_seguimiento("Clientes Activos", "list_activos")
    with t_int: render_lista_seguimiento("Clientes Interesados", "list_interesados")
    with t_vis: render_lista_seguimiento("Clientes por Visitar", "list_visitar")
    with t_otr: render_lista_seguimiento("Clientes de Otro", "list_otros")

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
                    sincronizar("oc", st.session_state.db_oc)
                    
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
                            sincronizar("oc", st.session_state.db_oc)
                            st.rerun()
            else:
                st.info("No hay órdenes.")

# --- MÓDULO BITÁCORA (TU VERSIÓN REPARADA) ---
elif opcion == "Bitácora":
    st.header("📝 Bitácora de Actividad")
    
    # Asegurar que la base existe
    if "db_bitacora" not in st.session_state:
        st.session_state.db_bitacora = []

    b1, b2 = st.tabs(["➕ Agregar Registro", "📋 Historial y Gestión"])
    
    with b1:
        if not st.session_state.db_contactos:
            st.warning("⚠️ Primero cargá un contacto en el módulo 'Contactos'.")
        else:
            with st.form("form_bit", clear_on_submit=True):
                # Usamos los nombres actuales de la DB de contactos para que siempre estén vinculados
                lista_empresas = sorted([c['Empresa'] for c in st.session_state.db_contactos])
                emp_b = st.selectbox("Asociar a Empresa", lista_empresas)
                fecha_realizada = st.date_input("Fecha Realizada", datetime.now())
                cont = st.text_area("Detalle de la gestión") # Esto se guardará en la columna 'Gestion'
                
                if st.form_submit_button("Cargar Bitácora"):
                    # 1. Creamos el nuevo registro (convertimos la fecha a texto para que Google no se queje)
                    nuevo_registro = {
                        "Fecha": str(fecha_realizada), 
                        "Empresa": emp_b, 
                        "Gestion": cont 
                    }
                    
                    # 2. Agregamos a la memoria de la App
                    st.session_state.db_bitacora.append(nuevo_registro)
                    
                    # 3. LA LÍNEA CLAVE: Mandamos toda la lista a Google Sheets
                    sincronizar("bitacora", st.session_state.db_bitacora)
                    
                    st.success(f"✅ Registro guardado para {emp_b}")
                    st.rerun() # Esto limpia el formulario para el próximo registro

    with b2:
        st.subheader("🔎 Historial de Gestiones")
        if st.session_state.db_bitacora:
            df_bit = pd.DataFrame(st.session_state.db_bitacora)
            
            # Limpieza de fechas para que el filtro no falle
            df_bit["Fecha"] = pd.to_datetime(df_bit["Fecha"]).dt.date
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                empresas_en_uso = ["Todas"] + sorted(list(df_bit["Empresa"].unique()))
                f_emp = st.selectbox("Filtrar por Empresa", empresas_en_uso)
            with col_f2:
                rango = st.date_input("Rango de fechas", value=[])

            # Lógica de filtrado
            df_filtrado = df_bit.copy()
            if f_emp != "Todas":
                df_filtrado = df_filtrado[df_filtrado["Empresa"] == f_emp]
            
            if len(rango) == 2:
                df_filtrado = df_filtrado[(df_filtrado["Fecha"] >= rango[0]) & (df_filtrado["Fecha"] <= rango[1])]

            # Muestra de tabla con las columnas correctas
            st.dataframe(df_filtrado, use_container_width=True)
            
            st.write("---")
            # Exportación simple en CSV (como tenías originalmente)
            if not df_filtrado.empty:
                csv = df_filtrado.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"📥 Descargar Bitácora de {f_emp} (.CSV)",
                    data=csv,
                    file_name=f"bitacora_{f_emp}.csv",
                    mime="text/csv",
                )

            if st.button("🗑️ Eliminar último registro cargado"):
                if len(st.session_state.db_bitacora) > 0:
                    st.session_state.db_bitacora.pop()
                    sincronizar("bitacora", st.session_state.db_bitacora)
                    st.rerun()
        else:
            st.info("La bitácora está vacía.")

# --- MÓDULO COBROS (CON ID Y REFERENCIA EN PESTAÑAS DE ESTADO) ---
elif opcion == "Cobros":
    st.header("💰 Gestión de Cobros")
    
    if "db_cobros" not in st.session_state:
        st.session_state.db_cobros = {}

    # Definimos las 5 pestañas
    tab_gestion, tab_mensual, tab_cobrado, tab_tiempo, tab_deuda = st.tabs([
        "🔄 Actualizar Estado", 
        "📅 Proyección Mensual",
        "✅ Cobrado",
        "⏳ En Tiempo",
        "❌ En Deuda"
    ])

    if not st.session_state.db_oc:
        st.warning("Primero creá una Orden de Compra en el módulo correspondiente.")
    else:
        # PESTAÑA 1: GESTIÓN
        with tab_gestion:
            mapeo_oc = {f"{o['ID']} | {o['Empresa']}": o for o in st.session_state.db_oc}
            oc_seleccionada_key = st.selectbox("Seleccioná OC para modificar o eliminar:", list(mapeo_oc.keys()))
            
            datos_oc = mapeo_oc[oc_seleccionada_key]
            oc_id = datos_oc['ID']
            oc_ref = datos_oc.get('Referencia', 'S/R') # Tomamos la referencia o nombre de la OC

            info_actual = st.session_state.db_cobros.get(oc_id, {
                "Estado": "En Tiempo", 
                "Fecha": datetime.now().date(), 
                "Notas": ""
            })

            st.markdown(f"### Gestión: {oc_id} - {oc_ref}")
            st.write(f"**Empresa:** {datos_oc['Empresa']} | **Dólar Pautado:** {datos_oc.get('Dólar', 0)} | **Monto:** U$S {datos_oc['Monto']:,.2f}")

            with st.form(f"form_cobro_{oc_id}"):
                c1, c2 = st.columns(2)
                nuevo_estado = c1.selectbox("Estado", ["En Tiempo", "Cobrado", "En Deuda"], 
                                          index=["En Tiempo", "Cobrado", "En Deuda"].index(info_actual.get("Estado", "En Tiempo")))
                
                fecha_val = info_actual["Fecha"]
                if isinstance(fecha_val, str): fecha_val = datetime.strptime(fecha_val, '%Y-%m-%d').date()
                
                nueva_fecha = c2.date_input("Fecha de Cobro (Real o Estimada)", fecha_val)
                nuevas_notas = st.text_input("Notas adicionales", info_actual.get("Notas", ""))
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.form_submit_button("💾 ACTUALIZAR / COBRAR"):
                    st.session_state.db_cobros[oc_id] = {
                        "OC_ID": oc_id,
                        "Referencia": oc_ref,
                        "Estado": nuevo_estado,
                        "Fecha": str(nueva_fecha),
                        "Notas": nuevas_notas,
                        "Dólar": datos_oc.get('Dólar', 0),
                        "Monto": datos_oc['Monto'],
                        "Empresa": datos_oc['Empresa']
                    }
                    
                    # MANDAR A LA NUBE (Convertimos de vuelta a lista para el Sheets)
                    sincronizar("cobros", list(st.session_state.db_cobros.values()))
                    
                    st.success("✅ Cobro actualizado")
                    st.rerun()
                
                if col_btn2.form_submit_button("🗑️ ELIMINAR COBRO"):
                    if oc_id in st.session_state.db_cobros:
                        del st.session_state.db_cobros[oc_id]
                        sincronizar("cobros", list(st.session_state.db_cobros.values()))
                        st.rerun()

            st.write("---")
            st.subheader("📋 Planilla General de Cobranzas")
            if st.session_state.db_cobros:
                df_resumen = pd.DataFrame(list(st.session_state.db_cobros.values()))
                cols_resumen = ["OC_ID", "Referencia", "Empresa", "Dólar", "Monto", "Estado", "Fecha"]
                st.dataframe(df_resumen[[c for c in cols_resumen if c in df_resumen.columns]], use_container_width=True)

        # PESTAÑA 2: MENSUAL (Corregida)
        with tab_mensual:
            st.subheader("📅 Cobros por Mes")
            if st.session_state.db_cobros:
                meses_es = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
                data_m = []
                for k, v in st.session_state.db_cobros.items():
                    f = v['Fecha']
                    
                    # --- EL ARREGLO ESTÁ ACÁ: Convertimos texto a fecha si es necesario ---
                    if isinstance(f, str):
                        try:
                            # Intentamos convertir el texto "AAAA-MM-DD" a fecha real
                            f = datetime.strptime(f, '%Y-%m-%d').date()
                        except:
                            # Si el formato es distinto, usamos la fecha de hoy para no romper la app
                            f = datetime.now().date()
                    # ---------------------------------------------------------------------

                    data_m.append({
                        "Fecha_Sort": f,
                        "Mes_Anio": f"{meses_es[f.month]} {f.year}",
                        "OC": k, 
                        "Referencia": v.get('Referencia', ''), 
                        "Empresa": v['Empresa'], 
                        "Dólar": v.get('Dólar', 0), 
                        "Monto": v['Monto'], 
                        "Estado": v['Estado']
                    })
                
                if data_m:
                    df_m = pd.DataFrame(data_m).sort_values("Fecha_Sort")
                    for etiqueta in df_m["Mes_Anio"].unique():
                        df_mes = df_m[df_m["Mes_Anio"] == etiqueta]
                        
                        # --- EL ARREGLO PARA LOS DECIMALES ESTÁ ACÁ ---
                        # Forzamos a que Dólar y Monto solo muestren 2 decimales
                        df_mostrar = df_mes[["OC", "Referencia", "Empresa", "Dólar", "Monto", "Estado"]].copy()
                        df_mostrar["Dólar"] = df_mostrar["Dólar"].map("{:,.2f}".format)
                        df_mostrar["Monto"] = df_mostrar["Monto"].map("{:,.2f}".format)
                        # ----------------------------------------------

                        with st.expander(f"🗓️ {etiqueta}  —  Total: U$S {df_mes['Monto'].sum():,.2f}"):
                            st.table(df_mostrar)
       # --- LÓGICA PARA LAS 3 PESTAÑAS (Corregida para decimales) ---
        def mostrar_tabla_por_estado(estado_nombre):
            if st.session_state.db_cobros:
                df_all = pd.DataFrame(list(st.session_state.db_cobros.values()))
                df_filt = df_all[df_all["Estado"] == estado_nombre].copy()
                
                if not df_filt.empty:
                    st.metric(f"Total en {estado_nombre}", f"U$S {df_filt['Monto'].sum():,.2f}")
                    
                    # --- FORMATEO DE DECIMALES AQUÍ ---
                    cols_vista = ["OC_ID", "Referencia", "Empresa", "Dólar", "Monto", "Fecha"]
                    # Filtramos solo las columnas que existen
                    df_final = df_filt[[c for c in cols_vista if c in df_filt.columns]].copy()
                    
                    # Aplicamos los 2 decimales y formato de miles
                    if "Dólar" in df_final.columns:
                        df_final["Dólar"] = df_final["Dólar"].map("{:,.2f}".format)
                    if "Monto" in df_final.columns:
                        df_final["Monto"] = df_final["Monto"].map("{:,.2f}".format)
                    # ----------------------------------

                    st.table(df_final)
                else:
                    st.info(f"No hay registros con estado '{estado_nombre}'.")

        with tab_cobrado:
            mostrar_tabla_por_estado("Cobrado")
        with tab_tiempo:
            mostrar_tabla_por_estado("En Tiempo")
        with tab_deuda:
            mostrar_tabla_por_estado("En Deuda")

# --- MÓDULO HISTORIAL INTEGRAL (UNIFICADO Y COMPLETO) ---
elif opcion == "Historial Empresas":
    st.header("🏢 Historial Integral por Empresa")
    
    if not st.session_state.db_contactos:
        st.warning("No hay contactos registrados.")
    else:
        lista_nombres = sorted(list(set([c['Empresa'] for c in st.session_state.db_contactos])))
        empresa_f = st.selectbox("🔍 Seleccioná la empresa para ver TODO su historial:", lista_nombres)
        c = next((item for item in st.session_state.db_contactos if item['Empresa'] == empresa_f), None)
        
        if c:
            # --- 1. LÓGICA DE FILTRADO ---
            # Estado de Cliente (Listas de seguimiento)
            estados_cliente = []
            if empresa_f in st.session_state.get('list_activos', []): estados_cliente.append("✅ Activo")
            if empresa_f in st.session_state.get('list_interesados', []): estados_cliente.append("⭐ Interesado")
            if empresa_f in st.session_state.get('list_visitar', []): estados_cliente.append("📍 Visitar")
            if empresa_f in st.session_state.get('list_otros', []): estados_cliente.append("👤 Otros")
            txt_estado = " | ".join(estados_cliente) if estados_cliente else "Sin Clasificar"

            # Bitácora
            df_bit_all = pd.DataFrame(st.session_state.db_bitacora)
            df_bit_f = df_bit_all[df_bit_all['Empresa'] == empresa_f] if not df_bit_all.empty and 'Empresa' in df_bit_all.columns else pd.DataFrame()

            # Órdenes de Compra
            df_oc_all = pd.DataFrame(st.session_state.db_oc)
            df_oc_f = df_oc_all[df_oc_all['Empresa'] == empresa_f] if not df_oc_all.empty and 'Empresa' in df_oc_all.columns else pd.DataFrame()

            # Estado de Cobros (Diccionario a DataFrame)
            df_cobros_all = pd.DataFrame(list(st.session_state.db_cobros.values()))
            df_cob_f = df_cobros_all[df_cobros_all['Empresa'] == empresa_f] if not df_cobros_all.empty and 'Empresa' in df_cobros_all.columns else pd.DataFrame()

            # --- 2. MOSTRAR INFORMACIÓN (ESTÉTICA ORIGINAL) ---
            st.write("---")
            st.subheader(f"🚩 Estado del Cliente: {txt_estado}")
            
            st.subheader("📞 Información de Contacto Completa")
            col_inf1, col_inf2 = st.columns(2)
            with col_inf1:
                st.write(f"**N° Registro:** {c.get('N°', 'S/N')}")
                st.write(f"**Empresa:** {c['Empresa']}")
                st.write(f"**Actividad:** {c['Actividad']}")
                st.write(f"**Ubicación:** {c['Ciudad']}, {c.get('Provincia','')}, {c['País']}")
                st.write(f"**Google Maps:** {c.get('Maps', 'N/A')}")
            with col_inf2:
                st.write(f"**Web:** {c.get('Web', 'N/A')}")
                st.write(f"**Teléfonos:** {c['T1']} / {c.get('T2','')}")
                st.write(f"**Mails:** {c['M1']} / {c.get('M2','')}")
                st.write(f"**Dato Extra:** {c.get('Extra', 'N/A')}")

           # --- SECCIÓN BITÁCORA: TABLA ESTILIZADA ---
            if not df_bit_f.empty:
                # 1. Aseguramos que la fecha se vea bien y ordenamos (la más reciente primero)
                df_bit_f['Fecha_DT'] = pd.to_datetime(df_bit_f['Fecha'], errors='coerce')
                df_bit_f = df_bit_f.sort_values(by='Fecha_DT', ascending=False)

                for _, fila in df_bit_f.iterrows():
                    # Formato de tarjeta limpia
                    with st.container():
                        # Usamos Markdown con un poco de estilo para que se vea como una ficha técnica
                        fecha_str = fila['Fecha']
                        usuario = fila.get('Usuario', 'S/U')
                        detalle = fila.get('Detalle', 'Sin detalle')
                        resultado = fila.get('Resultado', '')

                        st.markdown(f"""
                        <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; margin-bottom: 10px;">
                            <span style="color: #1f77b4; font-weight: bold;">📅 {fecha_str}</span> | 
                            <span style="color: #555;">👤 {usuario}</span>
                            <p style="margin-top: 10px; font-size: 16px;">{detalle}</p>
                            {f'<p style="color: #2e7d32; font-style: italic;"><b>🎯 Resultado:</b> {resultado}</p>' if resultado else ''}
                        </div>
                        """, unsafe_allow_html=True)
            else: 
                st.info("No hay gestiones en la bitácora para esta empresa.")
                
            st.write("---")
            st.subheader("🛒 Historial de Órdenes de Compra")
            if not df_oc_f.empty:
                # Mantenemos tu orden de columnas preferido
                c_oc = ["ID", "Fecha", "Referencia", "Dólar", "Monto", "Facturación"]
                cols_validas = [col for col in c_oc if col in df_oc_f.columns]
                st.dataframe(df_oc_f[cols_validas], use_container_width=True)
                st.metric("Total Facturado", f"U$S {df_oc_f['Monto'].sum():,.2f}")
            else: 
                st.info("No hay órdenes registradas.")

            st.write("---")
            st.subheader("💰 Estado de Cobros")
            if not df_cob_f.empty:
                # Mostramos ID, Referencia, Estado y Fecha de cobro
                df_cob_view = df_cob_f[["OC_ID", "Referencia", "Monto", "Estado", "Fecha"]].copy()
                st.table(df_cob_view)
            else:
                st.info("No hay registros de cobros para esta empresa.")

            # --- 3. REPORTE GLOBAL ACTUALIZADO ---
            st.write("---")
            html_final = f"""
            <html>
            <body style="font-family: Arial; padding: 20px;">
                <div style="border: 2px solid #1f77b4; padding: 15px; border-radius: 10px;">
                    <h1 style="color: #1f77b4; text-align: center;">INFORME GLOBAL: {empresa_f}</h1>
                    <h3 style="text-align: center;">Estado: {txt_estado}</h3>
                    <hr>
                    <h3>1. DATOS DE CONTACTO</h3>
                    <p><b>Registro:</b> {c.get('N°','')} | <b>Empresa:</b> {c['Empresa']}</p>
                    <p><b>Ubicación:</b> {c['Ciudad']}, {c.get('Provincia','')}, {c['País']}</p>
                    <p><b>Contacto:</b> {c['T1']} / {c['M1']}</p>
                    <p><b>Extra:</b> {c.get('Extra', 'N/A')}</p>
                    <hr>
                    <h3>2. BITÁCORA</h3>
                    {df_bit_f.to_html(index=False) if not df_bit_f.empty else '<p>Sin registros.</p>'}
                    <hr>
                    <h3>3. ÓRDENES Y COBROS</h3>
                    {df_oc_f.to_html(index=False) if not df_oc_f.empty else '<p>Sin órdenes.</p>'}
                    <h3 style="text-align: right;">TOTAL FACTURADO: U$S {df_oc_f['Monto'].sum() if not df_oc_f.empty else 0:,.2f}</h3>
                </div>
            </body>
            </html>
            """
            st.download_button("📥 DESCARGAR REPORTE GLOBAL (.HTML)", data=html_final, file_name=f"Reporte_{empresa_f}.html", mime="text/html", use_container_width=True, type="primary")
