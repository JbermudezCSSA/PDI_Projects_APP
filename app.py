import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime

# --- 1. CONFIGURACIÓN DE BASE DE DATOS (NUBE) ---
# Nos conectamos a Supabase usando la herramienta integrada de Streamlit
conn = st.connection("postgresql", type="sql")

# --- 2. LÓGICA DE NEGOCIO Y LÍMITES ---
def obtener_limite_diario(fecha):
    dia_semana = fecha.weekday()
    if dia_semana <= 3:  # Lunes a Jueves
        return 8.5
    elif dia_semana == 4: # Viernes
        return 7.0
    else: # Fines de semana
        return 0.0

def calcular_horas_dia(usuario, fecha):
    # Sumar las horas de un día concreto
    df = conn.query("SELECT SUM(horas) as total FROM registros WHERE usuario = :user AND fecha = :date", 
                    params={"user": usuario, "date": fecha})
    total = df.iloc[0]['total']
    return float(total) if pd.notna(total) else 0.0

# --- 3. INTERFAZ DE USUARIO (FRONTEND) ---
st.set_page_config(page_title="Formulario de Registro", layout="centered")

st.image("https://via.placeholder.com/150x50?text=COMSAN", width=150)
st.title("FORMULARIO DE REGISTRO")

# Lista de usuarios (Por ahora manual, igual que tu hoja de Excel)
lista_usuarios = ["Juan.Perez", "Maria.Gomez", "Carlos.Ruiz", "Admin"]
usuario_actual = st.selectbox("Selecciona tu usuario de red*", lista_usuarios)

# CARGAR PROYECTOS DESDE LA BASE DE DATOS DINÁMICAMENTE
df_proyectos = conn.query("SELECT nombre FROM proyectos WHERE activo = true ORDER BY nombre ASC")
lista_proyectos = df_proyectos['nombre'].tolist()

with st.form("registro_form"):
    proyecto = st.selectbox("Proyecto*", lista_proyectos)
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
        # Abrimos una sesión para escribir en la base de datos
        with conn.session as s:
            # Buscar si ya existe ese registro exacto
            resultado = s.execute(
                text("SELECT id, horas, observaciones FROM registros WHERE usuario=:user AND proyecto=:proj AND fecha=:date"),
                {"user": usuario_actual, "proj": proyecto, "date": fecha}
            ).fetchone()
            
            if resultado:
                # Sumar a lo existente
                id_reg, horas_viejas, obs_viejas = resultado
                nuevas_horas = float(horas_viejas) + horas
                
                # Unir observaciones
                if observaciones:
                    nueva_obs = f"{obs_viejas} | {observaciones}" if obs_viejas else observaciones
                else:
                    nueva_obs = obs_viejas

                s.execute(
                    text("UPDATE registros SET horas=:h, observaciones=:o WHERE id=:id"),
                    {"h": nuevas_horas, "o": nueva_obs, "id": id_reg}
                )
                s.commit()
                st.warning(f"Se ha SUMADO a tu registro existente. Total en este proyecto hoy: {nuevas_horas}h")
            else:
                # Insertar nuevo
                s.execute(
                    text("INSERT INTO registros (usuario, proyecto, fecha, horas, observaciones) VALUES (:u, :p, :f, :h, :o)"),
                    {"u": usuario_actual, "p": proyecto, "f": fecha, "h": horas, "o": observaciones}
                )
                s.commit()
                st.success("Registro creado con éxito.")

# --- 5. RESUMEN DEL DÍA ---
st.divider()
st.subheader("Resumen de registros")
horas_hoy = calcular_horas_dia(usuario_actual, fecha)
limite_hoy = obtener_limite_diario(fecha)

if limite_hoy > 0:
    porcentaje = min(horas_hoy / limite_hoy, 1.0)
    st.write(f"**DÍA: {fecha.strftime('%d/%m/%Y')}**")
    st.write(f"ESTADO: {horas_hoy} / {limite_hoy} h [{int(porcentaje*100)}%]")
    st.progress(porcentaje)
