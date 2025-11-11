# app.py
import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime
import threading
import plotly.express as px
import os

# Importar módulos locales
from src.config import PRODUCT_TO_WEIGHT, TRAY_WEIGHTS
from src.balance_reader import continuous_reading, probar_factor_escala  # ← AGREGAR probar_factor_escala
from src.data_manager import load_config, save_config, load_password, save_password
from src.utils import read_realtime_data, write_realtime_data



# ← NUEVO: Detectar si está en Streamlit Cloud
IS_STREAMLIT_CLOUD = os.environ.get('STREAMLIT_SERVER_ADDRESS') is not None
# Configuración de página
st.set_page_config(
    page_title="Sistema de Pesaje Industrial",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .big-weight {
        font-size: 4rem;
        font-weight: bold;
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin: 1rem 0;
        animation: pulse 2s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.9; }
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)





# Inicializar session_state
if 'history_list' not in st.session_state:
    st.session_state.history_list = []
if 'expeditions' not in st.session_state:
    st.session_state.expeditions = []
if 'last_product' not in st.session_state:
    st.session_state.last_product = ""
if 'is_server' not in st.session_state:
    st.session_state.is_server = False
if 'reading_thread' not in st.session_state:
    st.session_state.reading_thread = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'password' not in st.session_state:
    st.session_state.password = "admin123"  # Por defecto

# En app.py, después de los imports
probar_factor_escala()  # Ejecuta la prueba al inicio



# Cargar configuración al inicio
if 'config_loaded' not in st.session_state:
    history_list, expeditions, last_product = load_config()
    
    st.session_state.history_list = history_list
    st.session_state.expeditions = expeditions
    st.session_state.last_product = last_product
    st.session_state.password = load_password()
    
    st.session_state.config_loaded = True

# Leer datos en tiempo real
realtime_data = read_realtime_data()
current_peso = realtime_data['peso']
is_reading = realtime_data['reading']
status_text = realtime_data['status']

# SIDEBAR - Control de Balanza
st.sidebar.title("⚖️ Control de Balanza")

# Verificación de autenticación
if st.session_state.is_server and not st.session_state.authenticated:
    st.sidebar.warning("🔒 Autenticación Requerida")
    st.sidebar.markdown("### Ingrese la contraseña para modo Servidor")
    
    password_input = st.sidebar.text_input("Contraseña", type="password")
    
    if st.sidebar.button("🔑 Autenticar"):
        if password_input == st.session_state.password:
            st.session_state.authenticated = True
            st.sidebar.success("✅ Autenticación exitosa")
            time.sleep(1)
            st.rerun()
        else:
            st.sidebar.error("❌ Contraseña incorrecta")
            st.session_state.is_server = False
            time.sleep(2)
            st.rerun()

# Selector de modo
if not st.session_state.is_server or not st.session_state.authenticated:
    mode = st.sidebar.radio("Modo de operación", ["Cliente (solo lectura)", "Servidor (controlar balanza)"], index=0)
    st.session_state.is_server = (mode == "Servidor (controlar balanza)")
    
    if st.session_state.is_server and not st.session_state.authenticated:
        st.sidebar.info("🔒 Seleccione 'Servidor' y luego ingrese la contraseña")

# Controles de servidor
#if st.session_state.is_server and st.session_state.authenticated:
 #   st.sidebar.success("🖥️ Modo SERVIDOR activo")
    
  #  if st.sidebar.button("🔐 Cambiar Contraseña"):
   #     st.session_state.show_password_change = True
    # Controles de servidor - MODIFICADO
if st.session_state.is_server and st.session_state.authenticated:
    
    # ← NUEVO: Mostrar modo según ubicación
    if IS_STREAMLIT_CLOUD:
        st.sidebar.warning("🌐 Modo Cloud - Conectado al servidor local")
        st.sidebar.info("""
        **Configuración:**
        - Servidor local ejecutándose
        - Datos en tiempo real
        - Solo lectura en cloud
        """)
    else:
        st.sidebar.success("💻 Modo Local - Control directo de balanza")
    
    # Mantener el resto de controles igual...
    if st.sidebar.button("🔐 Cambiar Contraseña"):
        st.session_state.show_password_change = True
    if st.session_state.get('show_password_change', False):
        st.sidebar.markdown("### Cambiar Contraseña")
        new_password = st.sidebar.text_input("Nueva Contraseña", type="password")
        confirm_password = st.sidebar.text_input("Confirmar Contraseña", type="password")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("💾 Guardar"):
                if new_password and new_password == confirm_password:
                    if save_password(new_password):
                        st.session_state.password = new_password
                        st.sidebar.success("✅ Contraseña actualizada")
                        st.session_state.show_password_change = False
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.sidebar.error("❌ Error guardando contraseña")
                else:
                    st.sidebar.error("❌ Las contraseñas no coinciden")
        with col2:
            if st.button("❌ Cancelar"):
                st.session_state.show_password_change = False
                st.rerun()
    
    st.sidebar.markdown("### Conexión")
    
    if 'serial_port' not in st.session_state:
        st.session_state.serial_port = "COM4"
    if 'serial_baud' not in st.session_state:
        st.session_state.serial_baud = 9600
    if 'serial_format' not in st.session_state:
        st.session_state.serial_format = "el05"

    st.session_state.serial_port = st.sidebar.text_input("Puerto", st.session_state.serial_port)
    st.session_state.serial_baud = st.sidebar.selectbox("Baud Rate", [9600, 19200, 38400], 
        index=[9600, 19200, 38400].index(st.session_state.serial_baud))
    st.session_state.serial_format = st.sidebar.selectbox("Formato", ["el05", "cond"], 
        index=["el05", "cond"].index(st.session_state.serial_format))

    col1, col2 = st.sidebar.columns(2)
    with col1:
        # ← MODIFICADO: Deshabilitar controles en Cloud
        if IS_STREAMLIT_CLOUD:
            st.button("Iniciar", key="start_btn", disabled=True, 
                     help="⛔ Control solo disponible en modo local")
        else:
            if st.button("Iniciar", key="start_btn", disabled=is_reading):
                write_realtime_data(0.0, True, "Iniciando...")
                
                if st.session_state.reading_thread is None or not st.session_state.reading_thread.is_alive():
                    st.session_state.reading_thread = threading.Thread(
                        target=continuous_reading,
                        args=(
                            st.session_state.serial_port,
                            st.session_state.serial_baud,
                            st.session_state.serial_format
                        ),
                        daemon=True
                    )
                    st.session_state.reading_thread.start()
                
                st.rerun()
    
    with col2:
        # ← MODIFICADO: Deshabilitar controles en Cloud
        if IS_STREAMLIT_CLOUD:
            st.button("⏹️ Detener", disabled=True,
                     help="⛔ Control solo disponible en modo local")
        else:
            if st.button("⏹️ Detener", disabled=not is_reading):
                write_realtime_data(0.0, False, "Detenido")
                st.rerun()
   # col1, col2 = st.sidebar.columns(2)
    #with col1:
     #   if st.button("Iniciar", key="start_btn", disabled=is_reading):
      #      write_realtime_data(0.0, True, "Iniciando...")
            
       #     if st.session_state.reading_thread is None or not st.session_state.reading_thread.is_alive():
        #        st.session_state.reading_thread = threading.Thread(
         #           target=continuous_reading,
          #          args=(
           #             st.session_state.serial_port,
            #            st.session_state.serial_baud,
             #           st.session_state.serial_format
                 #   ),
              #      daemon=True
               # )
                #st.session_state.reading_thread.start()
            
            #st.rerun()
    
    #with col2:
     #   if st.button("⏹️ Detener", disabled=not is_reading):
      #      write_realtime_data(0.0, False, "Detenido")
       #     st.rerun()


    
    if st.sidebar.button("🚪 Cerrar Sesión Servidor"):
        st.session_state.authenticated = False
        st.session_state.is_server = False
        write_realtime_data(0.0, False, "Detenido (Sesión cerrada)")
        st.sidebar.success("✅ Sesión de servidor cerrada")
        time.sleep(1)
        st.rerun()

else:
    st.sidebar.info("📱 Modo CLIENTE - Solo lectura")
    st.sidebar.markdown("Conectado al servidor para ver datos en tiempo real")
    st.sidebar.warning("🔒 **Modo de solo lectura**")

status_color = "🟢" if is_reading else "🔴"
st.sidebar.markdown(f"**Estado:** {status_color} {status_text}")

if is_reading:
    last_update = datetime.fromtimestamp(realtime_data['last_update'])
    time_diff = (datetime.now() - last_update).total_seconds()
    
    if time_diff < 5:
        st.sidebar.success(f"⏱️ Actualizado hace {time_diff:.1f}s")
    else:
        st.sidebar.warning(f"⚠️ Sin actualización ({time_diff:.0f}s)")

st.sidebar.markdown("---")

# MAIN - Tabs
tab1, tab2, tab3 = st.tabs(["📊 Pesaje Actual", "📦 Historial", "🚚 Expediciones"])

with tab1:
    peso_display = current_peso
    st.markdown(f"""
    <div class="big-weight">
        {peso_display:.2f} kg
    </div>
    """, unsafe_allow_html=True)
    
    if is_reading:
        st.success("✅ Balanza activa - Datos compartidos en tiempo real para todos los usuarios")
    else:
        st.warning("⚠️ Balanza detenida - Actívala desde el modo SERVIDOR")
    
    st.markdown("---")
    
    # Formulario de cálculo
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🧮 Cálculo de Peso Neto")
        
        if not st.session_state.is_server or not st.session_state.authenticated:
            st.info("📊 **Modo Visualización** - Los cálculos son solo de referencia")
        
        producto = st.selectbox(
            "Producto",
            options=list(PRODUCT_TO_WEIGHT.keys()),
            index=list(PRODUCT_TO_WEIGHT.keys()).index(st.session_state.last_product) 
                  if st.session_state.last_product in PRODUCT_TO_WEIGHT else 0,
            disabled=(not st.session_state.is_server or not st.session_state.authenticated)
        )
        
        col_a, col_b = st.columns(2)
        with col_a:
            cajas = st.number_input("Cantidad de Cajas", min_value=0, value=0, step=1,
                                   disabled=(not st.session_state.is_server or not st.session_state.authenticated))
            pallet = st.number_input("Peso del Pallet (kg)", min_value=0.0, value=0.0, step=0.1,
                                    disabled=(not st.session_state.is_server or not st.session_state.authenticated))
        
        with col_b:
            bandeja = st.selectbox("Tipo de Bandeja", list(TRAY_WEIGHTS.keys()),
                                  disabled=(not st.session_state.is_server or not st.session_state.authenticated))
            cant_bandejas = st.number_input("Cantidad de Bandejas", min_value=0, value=0, step=1,
                                           disabled=(not st.session_state.is_server or not st.session_state.authenticated))
        
        # Nuevos campos: Número de lote y Cantidad de hormas
        col_c, col_d = st.columns(2)
        with col_c:
            lote = st.text_input("Número de Lote", value="",
                                 disabled=(not st.session_state.is_server or not st.session_state.authenticated))
        with col_d:
            hormas = st.number_input("Cantidad de Hormas", min_value=0, value=200, step=1,
                                     disabled=(not st.session_state.is_server or not st.session_state.authenticated))
        
        # Cálculos
        peso_caja = PRODUCT_TO_WEIGHT[producto]
        peso_cajas = cajas * peso_caja
        peso_bandejas = cant_bandejas * TRAY_WEIGHTS[bandeja]
        peso_bruto = peso_display
        peso_neto = peso_bruto - pallet - peso_cajas - peso_bandejas
        
        # Mostrar desglose
        st.markdown("### 📋 Desglose del Cálculo")
        col_calc1, col_calc2, col_calc3, col_calc4 = st.columns(4)
        
        with col_calc1:
            st.metric("Peso Bruto", f"{peso_bruto:.2f} kg")
        with col_calc2:
            st.metric("Cajas", f"-{peso_cajas:.2f} kg", delta=f"{cajas} × {peso_caja}")
        with col_calc3:
            st.metric("Bandejas", f"-{peso_bandejas:.2f} kg", delta=f"{cant_bandejas} × {TRAY_WEIGHTS[bandeja]}")
        with col_calc4:
            st.metric("Pallet", f"-{pallet:.2f} kg")
        
        st.markdown("---")
        
        color = "green" if peso_neto >= 0 else "red"
        st.markdown(f"### ✅ **Peso Neto: <span style='color:{color}'>{peso_neto:.2f} kg</span>**", unsafe_allow_html=True)
        
        if st.session_state.is_server and st.session_state.authenticated:
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
              if st.button("Guardar Registro", type="primary"):
                if peso_bruto > 0:
                    entry = {
                        'producto': producto,
                        'cajas': cajas,
                        'bandeja': bandeja,
                        'cant_bandeja': cant_bandejas,
                        'pallet': pallet,
                        'bruto': peso_bruto,
                        'neto': peso_neto,
                        'lote': lote,
                        'hormas': hormas,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.session_state.history_list.append(entry)
                    st.session_state.last_product = producto
                    
                    # ← CORREGIDO: UNA SOLA LLAMADA
                    save_config(st.session_state.history_list, st.session_state.expeditions, st.session_state.last_product)
                    
                    st.success(f"Registro guardado: {peso_neto:.2f} kg")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Peso bruto debe ser mayor a 0")
            
            with col_btn2:
                if st.button("🗑️ Limpiar Campos"):
                    st.rerun()
        else:
            st.warning("🔒 **Modo de solo lectura** - No se pueden guardar registros")
    
    with col2:
        st.subheader("📊 Estadísticas")
        total_neto = sum(item['neto'] for item in st.session_state.history_list)
        
        st.metric("Total Registros", len(st.session_state.history_list))
        st.metric("Total Neto Acumulado", f"{total_neto:.2f} kg")
        
        if st.session_state.history_list:
            promedio = total_neto / len(st.session_state.history_list)
            st.metric("Promedio por Pallet", f"{promedio:.2f} kg")
            
            ultimo = st.session_state.history_list[-1]
            st.markdown("---")
            st.markdown("**Último registro:**")
            st.text(f"{ultimo['producto']}")
            st.text(f"Neto: {ultimo['neto']:.2f} kg")

# ... (el resto del código de las tabs 2 y 3 se mantiene igual que en la versión anterior)

with tab2:
    st.subheader("📦 Historial de Pallets Actual")
    
    if st.session_state.history_list:
        df = pd.DataFrame(st.session_state.history_list)
        df.index = range(1, len(df) + 1)
        df.index.name = '#'
        
        cols_to_show = ['producto', 'cajas', 'bandeja', 'cant_bandeja', 'pallet', 'bruto', 'neto', 'lote', 'hormas', 'timestamp']
        display_df = df[cols_to_show].copy()
        display_df.columns = ['Producto', 'Cajas', 'Bandeja', 'Cant.Band.', 'Pallet(kg)', 'Bruto(kg)', 'Neto(kg)', 'Lote', 'Hormas', 'Fecha/Hora']
        
        st.dataframe(display_df, width='stretch', height=400)
        
        total_neto = df['neto'].sum()
        st.markdown(f"### 💰 **Total Neto: {total_neto:.2f} kg**")
        
        if st.session_state.is_server and st.session_state.authenticated:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                csv = display_df.to_csv(encoding='utf-8')
                st.download_button(
                    "📥 Exportar CSV",
                    csv,
                    f"historial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv"
                )
            
            with col2:
                if st.button("Archivar → Expedición", type="primary"):
                    today = datetime.now().strftime("%d/%m/%y")
                    today_expeditions = [e for e in st.session_state.expeditions if e['date'] == today]
                    next_num = len(today_expeditions) + 1
                    exp_name = f"{today} - Expedición {next_num}"
                    
                    expedition = {
                        "date": today,
                        "name": exp_name,
                        "total": total_neto,
                        "records": st.session_state.history_list.copy()
                    }
                    st.session_state.expeditions.append(expedition)
                    st.session_state.history_list = []
                    
                    # ← CORREGIDO
                    save_config(st.session_state.history_list, st.session_state.expeditions, st.session_state.last_product)
                    
                    st.success(f"Expedición creada: {exp_name}")
                    time.sleep(1)
                    st.rerun()
            
            with col3:
                if st.button("Limpiar Todo"):
                    if st.session_state.history_list:
                        st.session_state.history_list = []
                        
                        # ← CORREGIDO
                        save_config(st.session_state.history_list, st.session_state.expeditions, st.session_state.last_product)
                        
                        st.success("Historial limpiado")
                        time.sleep(1)
                        st.rerun()
        else:
            st.info("🔒 **Modo de solo lectura** - Conecte como servidor para realizar acciones")
        
        if len(df) > 0:
            st.markdown("---")
            st.subheader("📈 Distribución de Peso por Producto")
            fig = px.bar(df.groupby('producto')['neto'].sum().reset_index(), 
                        x='producto', y='neto', 
                        labels={'neto': 'Peso Neto (kg)', 'producto': 'Producto'},
                        color='neto',
                        color_continuous_scale='Viridis')
            fig.update_layout(showlegend=False, xaxis_tickangle=-45)
            st.plotly_chart(fig, width='stretch')
    else:
        st.info("📭 No hay registros en el historial actual")

with tab3:
    st.subheader("🚚 Expediciones Archivadas")
    
    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    
    with col_f1:
        filter_prod = st.text_input("🔍 Filtrar por producto", "")
    with col_f2:
        filter_date = st.text_input("📅 Filtrar por fecha (DD/MM/YY)", "")
    with col_f3:
        if st.button("🔄 Limpiar filtros"):
            st.rerun()
    
    if st.session_state.expeditions:
        filtered_exp = st.session_state.expeditions.copy()
        
        if filter_date:
            filtered_exp = [e for e in filtered_exp if filter_date in e['date']]
        
        if filter_prod:
            filtered_exp = [e for e in filtered_exp 
                          if any(filter_prod.lower() in rec['producto'].lower() 
                                for rec in e['records'])]
        
        if filtered_exp:
            for i, exp in enumerate(filtered_exp):
                with st.expander(f"📦 {exp['name']} - Total: {exp['total']:.2f} kg ({len(exp['records'])} pallets)"):
                    productos = set(rec['producto'] for rec in exp['records'])
                    st.markdown(f"**Productos:** {', '.join(sorted(productos))}")
                    
                    df_exp = pd.DataFrame(exp['records'])
                    df_exp.index = range(1, len(df_exp) + 1)
                    display_exp = df_exp[['producto', 'cajas', 'bandeja', 'cant_bandeja', 'pallet', 'bruto', 'neto', 'lote', 'hormas']].copy()
                    display_exp.columns = ['Producto', 'Cajas', 'Bandeja', 'Cant.Band.', 'Pallet(kg)', 'Bruto(kg)', 'Neto(kg)', 'Lote', 'Hormas']
                    
                    st.dataframe(display_exp, width='stretch')
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        csv = display_exp.to_csv(encoding='utf-8')
                        st.download_button(
                            "📥 Exportar",
                            csv,
                            f"{exp['name'].replace('/', '-')}.csv",
                            "text/csv",
                            key=f"exp_{i}"
                        )
                    with col2:
                        if st.button("Eliminar", key=f"del_{i}"):
                            st.session_state.expeditions.remove(exp)
                            
                            # ← CORREGIDO
                            save_config(st.session_state.history_list, st.session_state.expeditions, st.session_state.last_product)
                            
                            st.success("Expedición eliminada")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.info("🔒 Solo lectura")
        else:
            st.warning("🔍 No se encontraron expediciones con los filtros aplicados")
    else:
        st.info("📭 No hay expediciones archivadas")

# Auto-refresh
time.sleep(1)
st.rerun()

# Footer
st.markdown("---")
col_footer1, col_footer2, col_footer3 = st.columns([2, 1, 1])
with col_footer1:
    st.markdown("**Sistema de Pesaje Industrial v2.0** | Multi-usuario | 🔒 Seguro")
with col_footer2:
    if st.session_state.is_server and st.session_state.authenticated:
        st.markdown("👥 Modo: 🖥️ Servidor (Autenticado)")
    else:
        st.markdown("👥 Modo: 📱 Cliente (Solo lectura)")
with col_footer3:
    st.markdown(f"🕐 {datetime.now().strftime('%H:%M:%S')}")
