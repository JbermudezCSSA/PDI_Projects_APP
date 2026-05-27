import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN DE BASE DE DATOS SQL ---
def init_db():
    conn = sqlite3.connect('control_horas.db')
    c = conn.cursor()
    # Tabla de registros
    c.execute('''
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            proyecto TEXT,
            fecha DATE,
            horas REAL,
            observaciones TEXT
        )
    ''')
    conn.commit()
    return conn

conn = init_db()

# --- 2. LÓGICA DE NEGOCIO Y LÍMITES ---
def obtener_limite_diario(fecha):
    # Lunes=0, Domingo=6
    dia_semana = fecha.weekday()
    if dia_semana <= 3:  # Lunes a Jueves [cite: 35]
        return 8.5
    elif dia_semana == 4: # Viernes [cite: 36]
        return 7.0
    else: # Fines de semana [cite: 36]
        return 0.0

def calcular_horas_dia(usuario, fecha):
    c = conn.cursor()
    c.execute("SELECT SUM(horas) FROM registros WHERE usuario=? AND fecha=?", (usuario, fecha))
    total = c.fetchone()[0]
    return total if total else 0.0

# --- 3. INTERFAZ DE USUARIO (FRONTEND) ---
st.set_page_config(page_title="Formulario de Registro", layout="centered")

# Simular Application.UserName del VBA
usuario_actual = os.getlogin()

st.image("https://via.placeholder.com/150x50?text=COMSAN", width=150) # Sustituir por tu logo
st.title("FORMULARIO DE REGISTRO")

# Formulario
with st.form("registro_form"):
    st.write(f"**Usuario:** {usuario_actual}")
    
    # Proyectos activos (Mockup, idealmente vendría de otra tabla SQL)
    proyecto = st.selectbox("Proyecto*", ["CP18-12_NORMATIVA EUROPEA", "PROYECTO_B", "PROYECTO_C"])
    
    fecha = st.date_input("Fecha*")
    horas = st.number_input("Horas* (entre 0.5 - 8.5)", min_value=0.5, max_value=8.5, step=0.5)
    observaciones = st.text_area("Observaciones")
    
    enviado = st.form_submit_button("Registrar")

# --- 4. PROCESAMIENTO AL ENVIAR ---
if enviado:
    limite = obtener_limite_diario(fecha)
    horas_actuales = calcular_horas_dia(usuario_actual, fecha)
    nuevo_total = horas_actuales + horas
    
    if limite == 0.0:
        st.error("No se pueden registrar horas en fin de semana.")
    elif nuevo_total > limite:
        st.error(f"Supera el máximo diario. Llevas {horas_actuales}h y el límite hoy es {limite}h.")
    else:
        # Verificar si ya existe un registro exacto (para sustituir/sumar) [cite: 16]
        c = conn.cursor()
        c.execute("SELECT id, horas, observaciones FROM registros WHERE usuario=? AND proyecto=? AND fecha=?", 
                  (usuario_actual, proyecto, fecha))
        registro_existente = c.fetchone()
        
        if registro_existente:
            # En Streamlit, como es web, actualizamos directamente sumando (o puedes añadir un st.radio fuera del form para elegir)
            id_reg, horas_viejas, obs_viejas = registro_existente
            nuevas_horas_totales = horas_viejas + horas
            nueva_obs = f"{obs_viejas} | {observaciones}" if observaciones else obs_viejas
            
            c.execute("UPDATE registros SET horas=?, observaciones=? WHERE id=?", 
                      (nuevas_horas_totales, nueva_obs, id_reg))
            st.warning(f"Se ha SUMADO a tu registro existente. Total en este proyecto hoy: {nuevas_horas_totales}h")
        else:
            # Nuevo registro
            c.execute("INSERT INTO registros (usuario, proyecto, fecha, horas, observaciones) VALUES (?, ?, ?, ?, ?)",
                      (usuario_actual, proyecto, fecha, horas, observaciones))
            st.success("Registro creado con éxito.")
        
        conn.commit()

# --- 5. RESUMEN DE REGISTROS (BARRA DE PROGRESO) ---
st.divider()
st.subheader("Resumen de registros")
horas_hoy = calcular_horas_dia(usuario_actual, fecha)
limite_hoy = obtener_limite_diario(fecha)

if limite_hoy > 0:
    porcentaje = min(horas_hoy / limite_hoy, 1.0)
    st.write(f"**DÍA: {fecha.strftime('%d/%m/%Y')}**")
    st.write(f"ESTADO: {horas_hoy} / {limite_hoy} h [{int(porcentaje*100)}%]")
    st.progress(porcentaje)
    
    # Detalle del día
    df_detalle = pd.read_sql_query(
        "SELECT proyecto, horas FROM registros WHERE usuario=? AND fecha=?", 
        conn, params=(usuario_actual, fecha)
    )
    if not df_detalle.empty:
        st.write("**DETALLE DEL DÍA:**")
        for _, row in df_detalle.iterrows():
            st.write(f"• {row['proyecto']}: {row['horas']} h")