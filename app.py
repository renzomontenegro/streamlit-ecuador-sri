import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import random
import pandas as pd
from webdriver_manager.chrome import ChromeDriverManager
import os

# --- Funciones Auxiliares ---
def human_delay(min_sec=0.1, max_sec=0.4):
    time.sleep(random.uniform(min_sec, max_sec))

def safe_click(driver, element, intentos=3):
    for i in range(intentos):
        try:
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            human_delay(0.3, 0.5)
            try:
                element.click()
                return True
            except:
                try:
                    ActionChains(driver).move_to_element(element).click().perform()
                    return True
                except:
                    driver.execute_script("arguments[0].click();", element)
                    return True
        except:
            human_delay(0.5, 1)
    return False

def human_type(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.15))

def create_driver():
    options = Options()
    # Opciones críticas para correr en servidores (Docker/Linux)
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--headless=new') # Siempre headless en servidor
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # Intentar usar el driver instalado en el sistema o instalarlo
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        # Fallback para entornos donde no se puede instalar automáticamente
        driver = webdriver.Chrome(options=options)
        
    return driver

def consultar_persona(driver, nombre_busqueda):
    try:
        driver.get("https://srienlinea.sri.gob.ec/sri-en-linea/SriPagosWeb/ConsultaDeudasFirmesImpugnadas/Consultas/consultaDeudasFirmesImpugnadas")
        human_delay(2, 3)
        
        # Limpiar popups
        driver.execute_script("""
            ['noSoportado', 'advertenciaNavegador', 'disablingDiv'].forEach(id => {
                var el = document.getElementById(id);
                if (el) el.remove();
            });
            document.body.classList.remove('modal-open');
            document.querySelectorAll('.modal-backdrop, .ui-widget-overlay').forEach(el => el.remove());
        """)
        human_delay(0.5, 1)
        
        wait = WebDriverWait(driver, 10)
        
        btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'button[aria-label*="apellidos y nombres"]')
        ))
        safe_click(driver, btn)
        human_delay(1.5, 2.5)
        
        input_elem = wait.until(EC.presence_of_element_located((By.ID, "busquedaRazonSocialId")))
        input_elem.clear()
        input_elem.click()
        human_type(input_elem, nombre_busqueda)
        human_delay(0.5, 1)
        
        # Lógica de click en botón consultar
        input_elem.send_keys(Keys.ENTER) 
        human_delay(2, 3)
        
        for i in range(10): # Intentos de lectura
            human_delay(1, 1.2)
            try:
                result = driver.execute_script("""
                    var text = document.body.innerText || "";
                    if (text.includes('Puntaje bajo')) return {bloqueado: true};
                    if (text.includes('no generó resultados')) return {sin_resultados: true, mensaje: 'Sin resultados'};
                    var spans = document.querySelectorAll('span.titulo-consultas-1');
                    for (var i = 0; i < spans.length; i++) {
                        var txt = spans[i].textContent.trim().replace(/\\s/g, '');
                        if (/^\\d{10,13}$/.test(txt)) return {ruc: txt};
                    }
                    return null;
                """)
                if result: return result
            except: continue
            
        return {'sin_resultados': True, 'mensaje': 'Tiempo de espera agotado'}
        
    except Exception as e:
        return {'error': str(e)[:100]}

# --- Interfaz Streamlit ---
st.set_page_config(page_title="Consulta SRI", page_icon="🔍")

st.title("🔍 Consulta RUC masiva SRI")
st.markdown("Ingresa los nombres y el sistema buscará sus RUCs automáticamente.")

# Input de texto
txt_input = st.text_area("Pega los nombres (uno por línea):", height=150)

if st.button("🚀 Iniciar Consulta", type="primary"):
    nombres = [n.strip() for n in txt_input.split('\n') if n.strip()]
    
    if not nombres:
        st.warning("Por favor ingresa al menos un nombre.")
    else:
        result_container = st.container()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        resultados = []
        driver = None
        
        try:
            with st.spinner('Iniciando navegador virtual...'):
                driver = create_driver()
            
            total = len(nombres)
            for i, nombre in enumerate(nombres):
                status_text.text(f"Procesando ({i+1}/{total}): {nombre}...")
                
                datos = consultar_persona(driver, nombre)
                
                # Procesar respuesta
                ruc_val = "Error"
                if datos.get('ruc'): ruc_val = datos['ruc']
                elif datos.get('sin_resultados'): ruc_val = "Sin Resultados"
                elif datos.get('bloqueado'): ruc_val = "BLOQUEADO"
                else: ruc_val = datos.get('error', 'Error')
                
                resultados.append({'Nombre': nombre, 'RUC/Estado': ruc_val})
                progress_bar.progress((i + 1) / total)
                
                # Mostrar resultado en tiempo real
                st.success(f"**{nombre}**: {ruc_val}")
                
        except Exception as e:
            st.error(f"Error general: {e}")
        finally:
            if driver: driver.quit()
            status_text.text("✅ Proceso finalizado")
            
            # Mostrar tabla y botón de descarga
            if resultados:
                df = pd.DataFrame(resultados)
                st.dataframe(df)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar Excel (CSV)",
                    data=csv,
                    file_name='resultados_sri.csv',
                    mime='text/csv',
                )