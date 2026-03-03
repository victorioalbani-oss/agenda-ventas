import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import json
import gspread

# 1. Configuración de página
st.set_page_config(page_title="Vico S.A.", page_icon="🌎", layout="wide")

# --- 2. CONEXIÓN MANUAL Y ROBUSTA ---
try:
    s = st.secrets["connections"]["gsheets"]
    creds_dict = dict(s)
    
    # Procesamos la llave correctamente (buscando los \n que pusimos arriba)
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
    
    service_drive = build('drive', 'v3', credentials=credentials)
    client_sheets = gspread.authorize(credentials)
    sheet = client_sheets.open_by_url(s["spreadsheet"])
    
    class MockConn:
        def read(self, worksheet, **kwargs):
            hojas = {h.title.strip().lower(): h for h in sheet.worksheets()}
            target = worksheet.strip().lower()
            if target in hojas:
                return pd.DataFrame(hojas[target].get_all_records())
            return pd.DataFrame()

        def update(self, worksheet, data):
            if data is None or not isinstance(data, pd.DataFrame) or data.empty:
                return 
            try:
                wks = sheet.worksheet(worksheet)
                wks.clear()
                # Encabezados + Valores
                cuerpo = [data.columns.values.tolist()] + data.values.tolist()
                wks.update(cuerpo)
            except Exception as e:
                st.error(f"Error escribiendo en {worksheet}: {e}")

    conn = MockConn()

except Exception as e:
    st.error(f"Error de conexión crítica: {e}")
    st.stop()
# --------------------------------

# --- BLOQUE DE LOGIN REPARADO ---
def login_nube():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.markdown("<h1 style='text-align: center;'>🔐 Acceso a la AGENDA ALBANI</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                user_input = st.text_input("Usuario")
                pass_input = st.text_input("Contraseña", type="password")
                submit = st.form_submit_button("Entrar", use_container_width=True)
                
                if submit:
                    try:
                        # Leemos la pestaña
                        df_creds = conn.read(worksheet="credenciales")
                        
                        # Normalizamos nombres de columnas
                        df_creds.columns = [c.strip().lower() for c in df_creds.columns]

                        # --- LA COMPARACIÓN QUE NO FALLA ---
                        # Primero limpiamos lo que VOS escribís
                        u_ingresado = str(user_input).strip()
                        p_ingresado = str(pass_input).strip()

                        # Ahora comparamos contra el Excel (sin usar .strip() en la columna)
                        valido = df_creds[
                            (df_creds['usuario'].astype(str) == u_ingresado) & 
                            (df_creds['clave'].astype(str) == p_ingresado)
                        ]
                        
                        if not valido.empty:
                            st.session_state.autenticado = True
                            st.rerun()
                        else:
                            st.error("Usuario o contraseña incorrectos")
                    except Exception as e:
                        st.error(f"Error al verificar credenciales: {e}")
        return False
    return True

if not login_nube():
    st.stop()

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

# 4. Función para subir datos (VERSIÓN BLINDADA)
def sincronizar(pestaña, datos):
    if datos is None:
        return
        
    try:
        df = pd.DataFrame(datos)
        
        # Bloqueo preventivo para contactos vacíos
        if pestaña == "contactos" and df.empty:
            st.error("🛑 BLOQUEO DE SEGURIDAD: Se detectó un intento de borrar TODOS los contactos.")
            return 

        # Si son listas chicas y están vacías, les ponemos el encabezado para que no den error
        if df.empty and pestaña in ["list_activos", "list_interesados", "list_visitar", "list_otros"]:
            df = pd.DataFrame(columns=["Empresa"])
        
        # Llamamos al motor que arreglamos en el Paso 1
        conn.update(worksheet=pestaña, data=df)
        st.toast(f"✅ Sincronizado: {pestaña}")
        
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

opcion = st.sidebar.radio("Ir a:", ["Bitácora", "Diseño", "Órdenes de Compra", "Cobros", "Contactos", "Productos", "Historial Empresas", "Google Maps"])

# --- MÓDULO PRODUCTOS ---
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

# --- MÓDULO CONTACTOS ---
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

    # --- FUNCION DE LISTAS CON FILTROS AVANZADOS Y BITÁCORA ---
    # --- FUNCION DE LISTAS CON FILTROS AVANZADOS Y BITÁCORA ---
    def render_lista_seguimiento(titulo, lista_key):
        st.subheader(titulo)
        
        # 1. BLOQUE DE AÑADIR (Se mantiene igual)
        if st.session_state.db_contactos:
            nombres_totales = sorted([c['Empresa'] for c in st.session_state.db_contactos])
            with st.container():
                col_add, col_btn = st.columns([3, 1])
                with col_add:
                    emp_a_agregar = st.selectbox(
                        f"Seleccionar para añadir a {titulo}", 
                        [""] + nombres_totales, 
                        key=f"search_{lista_key}"
                    )
                with col_btn:
                    st.write("##")
                    if st.button("➕", key=f"add_btn_{lista_key}"):
                        if emp_a_agregar and emp_a_agregar not in st.session_state[lista_key]:
                            st.session_state[lista_key].append(emp_a_agregar)
                            df_p = pd.DataFrame(st.session_state[lista_key], columns=["Empresa"])
                            sincronizar(lista_key, df_p.to_dict('records'))
                            st.rerun()

        st.write("---")

        # 2. LÓGICA DE FILTRADO PARA LA LISTA
        lista_nombres = st.session_state.get(lista_key, [])
        if lista_nombres:
            df_contactos = pd.DataFrame(st.session_state.db_contactos).fillna("")
            df_bit_all = pd.DataFrame(st.session_state.db_bitacora)
            
            df_en_lista = df_contactos[df_contactos['Empresa'].isin(lista_nombres)].copy()

            # --- BUSCADOR INTERNO DE LA LISTA (Ajustado con Empresa) ---
            st.caption(f"🔍 Filtrar dentro de {titulo}:")
            
            # Agregamos el buscador de Empresa arriba o en una fila nueva
            f_emp_search = st.selectbox("🏢 Buscar Empresa específica", ["Todas"] + sorted(df_en_lista["Empresa"].unique().tolist()), key=f"f_emp_{lista_key}")
            
            c_f1, c_f2, c_f3, c_f4 = st.columns(4)
            with c_f1:
                f_act = st.selectbox("🛠️ Actividad", ["Todas"] + sorted(df_en_lista["Actividad"].unique().tolist()), key=f"f_act_{lista_key}")
            with c_f2:
                f_pais = st.selectbox("🌎 País", ["Todos"] + sorted(df_en_lista["País"].unique().tolist()), key=f"f_pais_{lista_key}")
            with c_f3:
                f_prov = st.selectbox("📍 Prov.", ["Todas"] + sorted(df_en_lista["Provincia"].unique().tolist()), key=f"f_prov_{lista_key}")
            with c_f4:
                f_ciu = st.text_input("🏙️ Ciudad", key=f"f_ciu_{lista_key}", placeholder="Buscar...")

            # Aplicamos los filtros
            df_final = df_en_lista.copy()
            if f_emp_search != "Todas": df_final = df_final[df_final["Empresa"] == f_emp_search] # <-- El nuevo filtro
            if f_act != "Todas": df_final = df_final[df_final["Actividad"] == f_act]
            if f_pais != "Todos": df_final = df_final[df_final["País"] == f_pais]
            if f_prov != "Todas": df_final = df_final[df_final["Provincia"] == f_prov]
            if f_ciu: df_final = df_final[df_final["Ciudad"].str.contains(f_ciu, case=False, na=False)]

            st.write(f"📊 **{len(df_final)}** empresas encontradas")

            # 3. RENDERIZADO DE LOS EXPANDERS (Se mantiene igual)
            df_final = df_final.sort_values(by=['País', 'Provincia', 'Ciudad'])

            for i, row in df_final.iterrows():
                emp_nombre = row['Empresa']
                ubicacion = f"{row['País']} - {row['Provincia']} - {row['Ciudad']}"
                llave_unica = f"item_{lista_key}_{emp_nombre}_{i}"
                
                with st.expander(f"🏢 {emp_nombre} | 🌎 {ubicacion}", expanded=False):
                    st.write(f"**Actividad:** {row.get('Actividad', 'S/D')}")
                    
                    if not df_bit_all.empty and 'Empresa' in df_bit_all.columns:
                        df_bit_emp = df_bit_all[df_bit_all['Empresa'] == emp_nombre].copy()
                        if not df_bit_emp.empty:
                            st.markdown("---")
                            st.caption("📝 Últimas gestiones:")
                            col_g = "Gestion" if "Gestion" in df_bit_emp.columns else "Detalle"
                            df_view_bit = df_bit_emp[["Fecha", col_g]].sort_index(ascending=False).head(3)
                            st.dataframe(df_view_bit, use_container_width=True, hide_index=True)
                    
                    if st.button(f"Quitar de {titulo}", key=f"del_{llave_unica}"):
                        st.session_state[lista_key].remove(emp_nombre)
                        df_p = pd.DataFrame(st.session_state[lista_key], columns=["Empresa"])
                        sincronizar(lista_key, df_p.to_dict('records'))
                        st.rerun()
        else:
            st.info(f"No hay empresas en la lista de {titulo}.")
            
    # Llamadas a las pestañas
    with t_act: render_lista_seguimiento("Clientes Activos", "list_activos")
    with t_int: render_lista_seguimiento("Clientes Interesados", "list_interesados")
    with t_vis: render_lista_seguimiento("Clientes por Visitar", "list_visitar")
    with t_otr: render_lista_seguimiento("Clientes de Otro", "list_otros")

# --- MÓDULO ÓRDENES DE COMPRA ---
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
                        "Dólar": dolar,   
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

# --- Modulo Bitacora  ----
elif opcion == "Bitácora":
    st.header("📝 Bitácora de Actividad y Recordatorios")
    
    dic_meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 
                 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}

    if "db_bitacora" not in st.session_state:
        st.session_state.db_bitacora = []

    tab_carga, tab_historial, tab_alertas = st.tabs(["➕ Nuevo Registro", "📋 Historial", "📅 Recordatorios"])
    
    with tab_carga:
        if not st.session_state.db_contactos:
            st.warning("⚠️ Primero cargá un contacto.")
        else:
            with st.form("form_gestion_vico_estable", clear_on_submit=True):
                lista_empresas = sorted([c['Empresa'] for c in st.session_state.db_contactos])
                emp_b = st.selectbox("Empresa", lista_empresas)
                f_hoy = st.date_input("Fecha de hoy", datetime.now())
                detalle = st.text_area("¿Qué se hizo?")
                
                st.write("---")
                col1, col2 = st.columns(2)
                with col1:
                    tiene_rec = st.checkbox("📌 Programar Aviso Futuro")
                with col2:
                    fecha_futura = st.date_input("¿Cuándo avisar?", datetime.now() + timedelta(days=7))
                
                if st.form_submit_button("🚀 Guardar Gestión"):
                    valor_rec = str(fecha_futura) if tiene_rec else "Sin aviso"
                    nuevo = {
                        "Fecha": str(f_hoy), 
                        "Empresa": emp_b, 
                        "Gestion": detalle, 
                        "Recordatorio": valor_rec
                    }
                    st.session_state.db_bitacora.append(nuevo)
                    sincronizar("bitacora", st.session_state.db_bitacora)
                    st.success("✅ Guardado correctamente.")
                    st.rerun()

    
    with tab_historial:
        st.subheader("📋 Historial de Gestiones")
        if st.session_state.db_bitacora:
            # 1. Convertimos la base a DataFrame para operar
            df_historial = pd.DataFrame(st.session_state.db_bitacora)
            
            # Aseguramos que la columna Fecha sea de tipo datetime para poder filtrar
            df_historial['Fecha_DT'] = pd.to_datetime(df_historial['Fecha'], errors='coerce')
            df_historial = df_historial.sort_values(by='Fecha_DT', ascending=False)


             # --- SECCIÓN DE EDICIÓN ---
            st.write("---")
            with st.expander("📝 Editar una gestión existente"):
                # Creamos la lista de opciones para elegir qué editar
                opciones_edit = [
                    f"{idx} | {g['Fecha']} | {g['Empresa']} | {g['Gestion'][:30]}..." 
                    for idx, g in enumerate(st.session_state.db_bitacora)
                ]
                seleccion_edit = st.selectbox("Seleccionar gestión para MODIFICAR:", ["Seleccionar..."] + opciones_edit, key="edit_bit_sel")
                
                if seleccion_edit != "Seleccionar...":
                    idx_edit = int(seleccion_edit.split(" | ")[0])
                    gestion_previa = st.session_state.db_bitacora[idx_edit]
                    
                    # Formulario de edición
                    with st.form("form_edit_bitacora"):
                        st.write(f"### Editando Registro N° {idx_edit}")
                        
                        # Empresa (puedes cambiarla si te equivocaste de cliente)
                        lista_emp_edit = sorted([c['Empresa'] for c in st.session_state.db_contactos])
                        new_emp = st.selectbox("Empresa", lista_emp_edit, index=lista_emp_edit.index(gestion_previa['Empresa']))
                        
                        # Fecha
                        fecha_previa = datetime.strptime(gestion_previa['Fecha'], '%Y-%m-%d')
                        new_fecha = st.date_input("Fecha", fecha_previa)
                        
                        # Detalle
                        new_gestion = st.text_area("Gestión realizada", value=gestion_previa['Gestion'])
                        
                        # Recordatorio
                        rec_previo = gestion_previa['Recordatorio']
                        tiene_rec_prev = "-" in rec_previo
                        
                        c_ed1, c_ed2 = st.columns(2)
                        with c_ed1:
                            new_tiene_rec = st.checkbox("📌 Programar Aviso Futuro", value=tiene_rec_prev)
                        with c_ed2:
                            # Si no tenía fecha, ponemos hoy + 7 por defecto
                            val_fecha_rec = datetime.strptime(rec_previo, '%Y-%m-%d') if tiene_rec_prev else (datetime.now() + timedelta(days=7))
                            new_fecha_futura = st.date_input("Nueva fecha de aviso", val_fecha_rec)
                        
                        if st.form_submit_button("💾 Guardar Cambios en Nube"):
                            new_val_rec = str(new_fecha_futura) if new_tiene_rec else "Sin aviso"
                            
                            # Actualizamos el registro en la lista
                            st.session_state.db_bitacora[idx_edit] = {
                                "Fecha": str(new_fecha),
                                "Empresa": new_emp,
                                "Gestion": new_gestion,
                                "Recordatorio": new_val_rec
                            }
                            
                            sincronizar("bitacora", st.session_state.db_bitacora)
                            st.success("✅ Gestión actualizada correctamente.")
                            st.rerun()

            # --- SECCIÓN DE BORRADO (Se mantiene igual bajo la edición) ---
            st.write("---")
            with st.expander("🗑️ Eliminar una gestión"):
                opciones_borrar = [
                    f"{idx} | {g['Fecha']} | {g['Empresa']} | {g['Gestion'][:30]}..." 
                    for idx, g in enumerate(st.session_state.db_bitacora)
                ]
                seleccion_borrar = st.selectbox("Seleccionar para borrar:", ["Seleccionar..."] + opciones_borrar, key="del_bit_hist")
                if st.button("❌ Confirmar Borrado"):
                    if seleccion_borrar != "Seleccionar...":
                        idx_borrar = int(seleccion_borrar.split(" | ")[0])
                        st.session_state.db_bitacora.pop(idx_borrar)
                        sincronizar("bitacora", st.session_state.db_bitacora)
                        st.rerun()
                        
            # --- SECCIÓN DE FILTROS ---
            st.write("---")
            
            col_f1, col_f2 = st.columns(2)
            
            with col_f1:
                empresas_en_bitacora = ["Todas"] + sorted(list(df_historial["Empresa"].unique()))
                filtro_emp = st.selectbox("Filtrar por empresa:", empresas_en_bitacora)
            
            with col_f2:
                # Selector de rango de fechas
                fecha_min = df_historial['Fecha_DT'].min().date()
                fecha_max = df_historial['Fecha_DT'].max().date()
                
                rango_fechas = st.date_input(
                    "Filtrar por rango de fechas:",
                    value=(fecha_min, fecha_max),
                    min_value=fecha_min,
                    max_value=fecha_max
                )

            st.write("---")
            # --- APLICACIÓN DE FILTROS ---
            df_mostrar = df_historial.copy()
            
            # Filtro de Empresa
            if filtro_emp != "Todas":
                df_mostrar = df_mostrar[df_mostrar["Empresa"] == filtro_emp]
            
            # Filtro de Rango (verificamos que se hayan seleccionado las dos fechas)
            if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
                f_inicio, f_fin = rango_fechas
                df_mostrar = df_mostrar[
                    (df_mostrar["Fecha_DT"].dt.date >= f_inicio) & 
                    (df_mostrar["Fecha_DT"].dt.date <= f_fin)
                ]
            
            # --- VISUALIZACIÓN ---
            
            if not df_mostrar.empty:
                for i, fila in df_mostrar.iterrows():
                    fecha_str = fila['Fecha']
                    empresa_str = fila['Empresa']
                    gestion_resumen = fila['Gestion'][:60] + "..." if len(fila['Gestion']) > 60 else fila['Gestion']
                    
                    with st.expander(f"📅 {fecha_str} | 🏢 **{empresa_str}** | 📝 {gestion_resumen}"):
                        st.markdown(f"**Empresa:** {empresa_str}")
                        st.markdown(f"**Fecha:** {fecha_str}")
                        st.info(fila['Gestion'])
                        if fila['Recordatorio'] not in ["Sin aviso", "Realizado"]:
                            st.write(f"🔔 **Próximo aviso:** {fila['Recordatorio']}")
            else:
                st.warning("No hay registros para los filtros seleccionados.")
                        
        else:
            st.info("Todavía no hay nada cargado en la bitácora.")
                
    with tab_alertas:
        st.subheader("🔔 Pendientes de Seguimiento")
        if st.session_state.db_bitacora:
            # Convertimos a DF para filtrar pero operamos sobre la lista original para no romper nada
            df_b = pd.DataFrame(st.session_state.db_bitacora)
            
            if "Recordatorio" in df_b.columns:
                # Filtrar solo los que tienen una fecha (contienen '-') y NO son 'Realizado'
                df_alertas = df_b[df_b["Recordatorio"].astype(str).str.contains("-", na=False)].copy()
                
                if not df_alertas.empty:
                    df_alertas["F_REC"] = pd.to_datetime(df_alertas["Recordatorio"], errors='coerce')
                    df_alertas = df_alertas.sort_values("F_REC")

                    for idx_filtrado, fila in df_alertas.iterrows():
                        f = fila["F_REC"]
                        vencido = f.date() <= datetime.now().date()
                        color = "🔴 VENCIDO" if vencido else "⏳ Pendiente"
                        
                        with st.container(border=True):
                            c1, c2 = st.columns([0.8, 0.2])
                            with c1:
                                st.markdown(f"**{color} | {f.day} de {dic_meses.get(f.month)} - {fila['Empresa']}**")
                                st.info(f"👉 **Tarea previa:** {fila['Gestion']}")
                            with c2:
                                # Aquí usamos el ID original de la lista para que no falle al guardar
                                if st.button("Quitar 🔔", key=f"q_{idx_filtrado}"):
                                    # Modificamos el registro original en el session_state
                                    st.session_state.db_bitacora[idx_filtrado]["Recordatorio"] = "Realizado"
                                    sincronizar("bitacora", st.session_state.db_bitacora)
                                    st.success("Aviso marcado como Realizado")
                                    st.rerun()
                else:
                    st.info("No hay avisos pendientes.")
        else:
            st.info("La bitácora está vacía.")
                    
# --- MÓDULO COBROS ---
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

        # PESTAÑA 2: MENSUAL 
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

# --- MÓDULO HISTORIAL INTEGRAL ---
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

            # Estado de Cobros
            df_cobros_all = pd.DataFrame(list(st.session_state.db_cobros.values()))
            df_cob_f = df_cobros_all[df_cobros_all['Empresa'] == empresa_f] if not df_cobros_all.empty and 'Empresa' in df_cobros_all.columns else pd.DataFrame()

            # --- 2. MOSTRAR INFORMACIÓN ---
            st.write("---")
            st.subheader(f"🚩 Estado del Cliente: {txt_estado}")
            
            # --- SECCIÓN 1: CONTACTO ---
            st.subheader("📞 Información de Contacto Completa")
            col_inf1, col_inf2 = st.columns(2)
            with col_inf1:
                st.write(f"**N° Registro:** {c.get('N°', 'S/N')}")
                st.write(f"**Empresa:** {c['Empresa']}")
                st.write(f"**Actividad:** {c['Actividad']}")
                st.write(f"**Ubicación:** {c['Ciudad']}, {c.get('Provincia','')}, {c['País']}")
            with col_inf2:
                st.write(f"**Web:** {c.get('Web', 'N/A')}")
                st.write(f"**Teléfonos:** {c['T1']} / {c.get('T2','')}")
                st.write(f"**Mails:** {c['M1']} / {c.get('M2','')}")
                st.write(f"**Dato Extra:** {c.get('Extra', 'N/A')}")

            # --- SECCIÓN 2: BITÁCORA ---
            st.write("---")
            st.subheader("📝 Bitácora de Gestiones")
            if not df_bit_f.empty:
                df_temp = df_bit_f.copy()
                if 'Fecha' in df_temp.columns:
                    df_temp['Fecha'] = pd.to_datetime(df_temp['Fecha'], errors='coerce').dt.strftime('%d/%m/%Y')
                col_gestion = "Gestion" if "Gestion" in df_temp.columns else "Detalle"
                df_view = df_temp[["Fecha", col_gestion]].sort_index(ascending=False)
                st.dataframe(df_view, use_container_width=True, hide_index=True)
            else: 
                st.info("No hay gestiones registradas.")

            # --- SECCIÓN 3: DISEÑOS (DRIVE) ---
            st.write("---")
            st.subheader("🎨 Diseños y Documentación (Drive)")
            
            # Buscamos la carpeta de la empresa
            query_f = f"name = '{empresa_f}' and '{ID_CARPETA_RAIZ}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            res_folder = service_drive.files().list(q=query_f).execute()
            folders = res_folder.get('files', [])

            if not folders:
                st.info("No existe una carpeta de diseños para esta empresa.")
            else:
                id_sub = folders[0]['id']
                res_docs = service_drive.files().list(
                    q=f"'{id_sub}' in parents and trashed = false", 
                    fields="files(name, webViewLink, thumbnailLink)"
                ).execute()
                docs = res_docs.get('files', [])
                
                if not docs:
                    st.info("La carpeta está creada pero no tiene archivos.")
                else:
                    # Mostramos miniaturas en un grid de 4 columnas
                    cols_docs = st.columns(4)
                    for idx, doc in enumerate(docs):
                        with cols_docs[idx % 4]:
                            if doc.get('thumbnailLink'):
                                st.image(doc['thumbnailLink'], use_container_width=True)
                            else:
                                st.write("📄")
                            st.markdown(f"[{doc['name']}]({doc['webViewLink']})")

            # --- SECCIÓN 4: ÓRDENES DE COMPRA ---
            st.write("---")
            st.subheader("🛒 Historial de Órdenes de Compra")
            if not df_oc_f.empty:
                c_oc = ["ID", "Fecha", "Referencia", "Dólar", "Monto", "Facturación"]
                cols_validas = [col for col in c_oc if col in df_oc_f.columns]
                st.dataframe(df_oc_f[cols_validas], use_container_width=True)
                st.metric("Total Facturado", f"U$S {df_oc_f['Monto'].sum():,.2f}")
            else: 
                st.info("No hay órdenes registradas.")

            # --- SECCIÓN 5: COBROS ---
            st.write("---")
            st.subheader("💰 Estado de Cobros")
            if not df_cob_f.empty:
                df_cob_view = df_cob_f[["OC_ID", "Referencia", "Monto", "Estado", "Fecha"]].copy()
                st.table(df_cob_view)
            else:
                st.info("No hay registros de cobros.")

            # (Opcional: El botón de reporte HTML sigue igual pero podrías agregarle los links de Drive si quisieras)

# --- MÓDULO DISEÑO (VISUALIZADOR SEGURO) ---
elif opcion == "Diseño":
    st.header("🎨 Gestión de Documentación Técnica")
    
    if not st.session_state.db_contactos:
        st.warning("No hay empresas registradas.")
    else:
        nombres_empresas = sorted([c['Empresa'] for c in st.session_state.db_contactos])
        empresa_f = st.selectbox("📂 Seleccioná la empresa:", nombres_empresas)

        def buscar_carpeta_empresa(nombre):
            query = f"name = '{nombre}' and '{ID_CARPETA_RAIZ}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            res = service_drive.files().list(q=query).execute()
            folders = res.get('files', [])
            return folders[0]['id'] if folders else None

        id_subcarpeta = buscar_carpeta_empresa(empresa_f)

        if not id_subcarpeta:
            st.info(f"💡 No hay una carpeta creada para **{empresa_f}**.")
            if st.button(f"🆕 Crear Carpeta para {empresa_f}"):
                meta = {'name': empresa_f, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [ID_CARPETA_RAIZ]}
                service_drive.files().create(body=meta).execute()
                st.success("¡Carpeta creada con éxito!")
                st.rerun()
        else:
            # --- LISTADO DE ARCHIVOS SEGURO ---
            st.subheader(f"📁 Archivos de {empresa_f}")
            res_files = service_drive.files().list(
                q=f"'{id_subcarpeta}' in parents and trashed = false", 
                fields="files(id, name, webViewLink, thumbnailLink)"
            ).execute()
            files = res_files.get('files', [])

            if not files:
                st.info("La carpeta está vacía.")
            else:
                for f in files:
                    # Ajustamos las columnas para que la imagen tenga más protagonismo [1, 2]
                    c1, c2 = st.columns([1, 2]) 
                    with c1:
                        if f.get('thumbnailLink'): 
                            # Aumentamos el ancho a 300 y usamos el ancho del contenedor
                            st.image(f['thumbnailLink'], width=300, use_container_width=True)
                        else: 
                            st.write("📄 **Sin vista previa disponible**")
                    with c2:
                        st.write("##") # Espaciador para centrar un poco el texto
                        st.markdown(f"### {f['name']}")
                        st.link_button("👁️ Ver / Descargar en pantalla completa", f['webViewLink'], use_container_width=True)
                    st.write("---")
            
            # Botón para abrir la carpeta completa
            url_carpeta = f"https://drive.google.com/drive/folders/{id_subcarpeta}"
            st.link_button("📂 Abrir carpeta completa en Google Drive", url_carpeta, use_container_width=True)


# --- MÓDULO MAPA ACTUALIZADO CON PESTAÑAS ---
elif opcion == "Google Maps":
    st.header("🌎 Gestión de Mapa de Clientes")

    # Definimos las dos pestañas
    tab_general, tab_busqueda = st.tabs(["📍 Todas en el Mapa", "🔍 Buscar Empresa en Mapa"])

    # --- PESTAÑA 1: VISTA GENERAL ---
    with tab_general:
        st.subheader("Mapa General")
        
        # El link de siempre (aseguráte de que sea el de /embed para que no falle)
        URL_BASE = "https://www.google.com/maps/d/u/0/embed?mid=1gmz5MfwRKhXs2gYMK9mo-TfFt7g7pZ8&ehbc=2E312F" 
        
        # Botón para saltar a la App oficial
        st.link_button("📱 Abrir en App Google Maps (Pantalla Completa)", 
                       URL_BASE.replace("embed", "viewer"), 
                       use_container_width=True)

        try:
            st.components.v1.html( 
                f"""
                <div style="border:2px solid #4A90E2; border-radius:15px; overflow:hidden;">
                    <iframe src="https://www.google.com/maps/d/u/0/embed?mid=1gmz5MfwRKhXs2gYMK9mo-TfFt7g7pZ8&ehbc=2E312F" 
                    width="100%" height="800" 
                    frameborder="0"
                    allowfullscreen>
                    </iframe>
                </div>
                """,
                height=820,
            )

        except Exception as e:
            st.error(f"No se pudo cargar el mapa: {e}")
        
        st.info("💡 En esta vista puedes ver la distribución de todos tus pines.")

    # --- PESTAÑA 2: BUSCADOR DE PRECISIÓN ---
    with tab_busqueda:
        st.subheader("Buscador Directo al Pin")
        st.write("Seleccioná una empresa para abrir su ubicación exacta en Google Maps.")

        if st.session_state.db_contactos:
            df_contactos = pd.DataFrame(st.session_state.db_contactos)
            
            # Buscador con autocompletado
            empresa_buscada = st.selectbox(
                "🏢 Seleccioná o escribí el nombre de la empresa:", 
                [""] + sorted(df_contactos['Empresa'].tolist()),
                key="busqueda_mapa_tab"
            )
            
            if empresa_buscada:
                # Extraemos los datos de esa empresa
                datos_emp = df_contactos[df_contactos['Empresa'] == empresa_buscada].iloc[0]
                direccion = datos_emp.get('Maps', '')
                actividad = datos_emp.get('Actividad', 'Sin actividad definida')

                with st.container(border=True):
                    st.write(f"### {empresa_buscada}")
                    st.write(f"📍 **Dirección:** {direccion}")
                    st.write(f"🛠️ **Actividad:** {actividad}")
                    
                    # El link de búsqueda de Google Maps (esto abre el pin directamente)
                    search_url = f"https://www.google.com/maps/search/{direccion.replace(' ', '+')}"
                    
                    st.link_button(f"🚀 Ver pin de {empresa_buscada} en Maps", search_url, use_container_width=True)
        else:
            st.warning("No hay contactos en la base de datos para buscar.")

    st.write("---")
