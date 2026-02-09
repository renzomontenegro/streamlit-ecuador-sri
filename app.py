import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
import pandas as pd
import base64

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Consulta SRI Original", page_icon="🦅", layout="wide")

# --- FUNCIONES EXACTAS DE TU CÓDIGO ORIGINAL ---
def human_delay(min_sec=0.1, max_sec=0.4):
    # Ligeramente ajustado para servidor, pero manteniendo la esencia rápida
    time.sleep(random.uniform(min_sec, max_sec))

def safe_click(driver, element, intentos=3):
    # Tu lógica exacta de safe_click
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
    # Tu lógica exacta de tipeo humano
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.15))

def get_base64_screenshot(driver):
    """Ayuda visual para debug"""
    try:
        return driver.get_screenshot_as_base64()
    except:
        return None

def create_driver():
    options = Options()
    # Opciones de servidor obligatorias (no se pueden quitar)
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except:
        driver = webdriver.Chrome(options=options)
    
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
    })
    
    return driver

def consultar_persona(driver, nombre_busqueda, debug_mode=False):
    # Lógica idéntica a tu función consultar_persona original
    try:
        driver.get("https://srienlinea.sri.gob.ec/sri-en-linea/SriPagosWeb/ConsultaDeudasFirmesImpugnadas/Consultas/consultaDeudasFirmesImpugnadas")
        human_delay(2, 3)
        
        # 1. Limpieza de Popups (Tu script original)
        driver.execute_script("""
            ['noSoportado', 'advertenciaNavegador', 'disablingDiv'].forEach(id => {
                var el = document.getElementById(id);
                if (el) el.remove();
            });
            document.body.classList.remove('modal-open');
            document.querySelectorAll('.modal-backdrop, .ui-widget-overlay').forEach(el => el.remove());
        """)
        human_delay(0.5, 1)
        
        wait = WebDriverWait(driver, 15)
        
        # 2. Clic en pestaña Apellidos (Tu selector original)
        try:
            btn = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'button[aria-label*="apellidos y nombres"]')
            ))
            safe_click(driver, btn)
        except Exception as e:
            return {'error': 'Error click pestaña', 'img': get_base64_screenshot(driver)}

        human_delay(1.5, 2.5)
        
        # 3. Ingreso de datos
        input_elem = wait.until(EC.presence_of_element_located((By.ID, "busquedaRazonSocialId")))
        input_elem.clear()
        human_delay(0.2, 0.4)
        
        try: input_elem.click()
        except: pass
        
        human_type(input_elem, nombre_busqueda)
        human_delay(0.5, 1)
        
        # --- AQUÍ ESTÁ LA MAGIA RECUPERADA ---
        # Tu lógica original para cazar el botón Consultar
        consultar_btn = None
        for intento in range(10):
            try:
                # Intento 1: Por clase cyan-btn
                btn = driver.find_element(By.CSS_SELECTOR, "button.cyan-btn:not([disabled])")
                if btn.is_displayed():
                    consultar_btn = btn
                    break
            except:
                pass
            
            if not consultar_btn:
                try:
                    # Intento 2: Por texto 'Consultar' (XPath)
                    btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Consultar')]")
                    for b in btns:
                        if b.is_displayed() and b.get_attribute('disabled') != 'true':
                            consultar_btn = b
                            break
                except:
                    pass
            
            if consultar_btn:
                break
            
            human_delay(0.5, 1)
        
        # Ejecutar la acción (Clic o Enter)
        if not consultar_btn:
            input_elem.send_keys(Keys.ENTER)
        else:
            safe_click(driver, consultar_btn)
        # -------------------------------------
        
        human_delay(2, 3)
        
        # 4. Lectura de Resultados (Tu script JS original)
        for i in range(15):
            human_delay(1, 1.2)
            
            try:
                result = driver.execute_script("""
                    var text = document.body.innerText || "";
                    
                    if (text.includes('Puntaje bajo')) {
                        return {bloqueado: true};
                    }
                    
                    if (text.includes('no generó resultados')) {
                        return {sin_resultados: true, mensaje: 'La búsqueda no generó resultados'};
                    }
                    
                    var spans = document.querySelectorAll('span.titulo-consultas-1');
                    for (var i = 0; i < spans.length; i++) {
                        var txt = spans[i].textContent.trim().replace(/\\s/g, '');
                        if (/^\\d{10,13}$/.test(txt)) {
                            return {ruc: txt};
                        }
                    }
                    
                    return null;
                """)
                
                if result:
                    # Añadimos la imagen si está en modo debug
                    if debug_mode: result['img'] = get_base64_screenshot(driver)
                    return result
                    
            except:
                continue
        
        # Timeout
        return {'sin_resultados': True, 'mensaje': 'Tiempo agotado', 'img': get_base64_screenshot(driver)}
        
    except Exception as e:
        return {'error': str(e)[:100], 'img': get_base64_screenshot(driver)}

# --- INTERFAZ STREAMLIT ---
st.title("🦅 Consulta SRI (Motor Original)")

with st.sidebar:
    debug_mode = st.checkbox("📸 Modo Debug", value=False)
    st.info("Este modo usa exactamente tu lógica original de Python.")

txt_input = st.text_area("Pega los nombres (uno por línea):", height=150)

if st.button("🚀 Iniciar Consulta Real", type="primary"):
    nombres = [n.strip() for n in txt_input.split('\n') if n.strip()]
    
    if not nombres:
        st.warning("Sin nombres.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        result_container = st.container()
        
        resultados = []
        driver = None
        
        try:
            with st.spinner('Cargando motor...'):
                driver = create_driver()
            
            total = len(nombres)
            for i, nombre in enumerate(nombres):
                status_text.text(f"Procesando {i+1}/{total}: {nombre}")
                
                datos = consultar_persona(driver, nombre, debug_mode)
                
                ruc_val = "Error"
                if datos.get('ruc'): 
                    ruc_val = datos['ruc']
                    st.toast(f"✅ {nombre}: {ruc_val}")
                elif datos.get('sin_resultados'): 
                    ruc_val = "Sin Resultados"
                elif datos.get('bloqueado'):
                    ruc_val = "BLOQUEADO"
                else: 
                    ruc_val = datos.get('error', 'Error')
                
                resultados.append({'Nombre': nombre, 'RUC': ruc_val})
                progress_bar.progress((i + 1) / total)
                
                with result_container:
                    with st.expander(f"{nombre}: {ruc_val}", expanded=debug_mode):
                        if datos.get('img'):
                            st.image(base64.b64decode(datos['img']), caption="Evidencia")
                        else:
                            st.write("Sin captura.")

        except Exception as e:
            st.error(f"Error fatal: {e}")
        finally:
            if driver: driver.quit()
            status_text.text("Finalizado.")
            
            if resultados:
                df = pd.DataFrame(resultados)
                st.dataframe(df)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Descargar CSV", csv, "resultados.csv", "text/csv")