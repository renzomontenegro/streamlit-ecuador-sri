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
st.set_page_config(page_title="Consulta SRI Pro", page_icon="🕵️‍♂️", layout="wide")

# --- FUNCIONES AUXILIARES (Tu lógica original) ---
def human_delay(min_sec=0.5, max_sec=1.5):
    # Aumenté ligeramente los tiempos para el servidor que suele ser más lento
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

def get_base64_screenshot(driver):
    """Convierte la captura de pantalla a base64 para mostrarla en Streamlit sin guardarla."""
    try:
        return driver.get_screenshot_as_base64()
    except:
        return None

def create_driver():
    options = Options()
    # Argumentos críticos para entorno servidor (Linux/Docker)
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--headless=new') # Headless moderno
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # Intentar instalación automática, si falla (común en algunos hostings), usar default
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except:
        driver = webdriver.Chrome(options=options)
    
    # Script anti-detección
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
    })
    
    return driver

def consultar_persona(driver, nombre_busqueda, debug_mode=False):
    logs = []
    screenshot = None
    
    try:
        driver.get("https://srienlinea.sri.gob.ec/sri-en-linea/SriPagosWeb/ConsultaDeudasFirmesImpugnadas/Consultas/consultaDeudasFirmesImpugnadas")
        human_delay(2, 3)
        
        # 1. Limpieza de Popups (Tu código original)
        driver.execute_script("""
            ['noSoportado', 'advertenciaNavegador', 'disablingDiv'].forEach(id => {
                var el = document.getElementById(id);
                if (el) el.remove();
            });
            document.body.classList.remove('modal-open');
            document.querySelectorAll('.modal-backdrop, .ui-widget-overlay').forEach(el => el.remove());
        """)
        
        wait = WebDriverWait(driver, 15) # Tiempo de espera ampliado para servidor
        
        # 2. Click en pestaña "Apellidos y Nombres"
        try:
            btn = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'button[aria-label*="apellidos y nombres"]')
            ))
            if not safe_click(driver, btn):
                raise Exception("No se pudo hacer click en pestaña Nombres")
        except Exception as e:
            return {'error': 'Fallo al cambiar pestaña', 'logs': logs, 'img': get_base64_screenshot(driver)}

        human_delay(1, 2)
        
        # 3. Ingresar Texto
        try:
            input_elem = wait.until(EC.presence_of_element_located((By.ID, "busquedaRazonSocialId")))
            input_elem.clear()
            # A veces el click falla si hay overlays, forzamos JS si es necesario
            try: input_elem.click()
            except: driver.execute_script("arguments[0].click();", input_elem)
            
            human_type(input_elem, nombre_busqueda)
            human_delay(0.5, 1)
            input_elem.send_keys(Keys.ENTER)
        except Exception as e:
            return {'error': 'Fallo al escribir nombre', 'logs': logs, 'img': get_base64_screenshot(driver)}
        
        human_delay(3, 4) # Esperar a que cargue la tabla
        
        # 4. Extracción de datos (Tu script JS original optimizado)
        for intento in range(10): # 10 intentos de lectura
            human_delay(1, 1.5)
            
            # Tomar foto en cada intento si es debug mode (opcional, consume recursos)
            if debug_mode and intento == 5:
                screenshot = get_base64_screenshot(driver)

            try:
                result = driver.execute_script("""
                    var text = document.body.innerText || "";
                    
                    if (text.includes('Puntaje bajo') || text.includes('Captcha')) {
                        return {bloqueado: true};
                    }
                    
                    if (text.includes('no generó resultados')) {
                        return {sin_resultados: true};
                    }
                    
                    // Buscamos RUC en los spans específicos
                    var spans = document.querySelectorAll('span.titulo-consultas-1');
                    for (var i = 0; i < spans.length; i++) {
                        var txt = spans[i].textContent.trim().replace(/\\s/g, '');
                        // Regex para RUC válido (10 a 13 dígitos)
                        if (/^\\d{10,13}$/.test(txt)) {
                            return {ruc: txt};
                        }
                    }
                    
                    // Fallback: Buscar cualquier secuencia de 13 dígitos visible
                    var allText = document.body.innerText;
                    var match = allText.match(/\\d{13}/);
                    if (match) return {ruc: match[0]};

                    return null;
                """)
                
                if result:
                    if result.get('ruc'):
                        return {'ruc': result['ruc'], 'img': get_base64_screenshot(driver) if debug_mode else None}
                    if result.get('bloqueado'):
                        return {'error': 'Detectado como Robot/Bloqueado', 'img': get_base64_screenshot(driver)}
                    if result.get('sin_resultados'):
                        return {'sin_resultados': True, 'mensaje': 'Sin resultados en SRI', 'img': get_base64_screenshot(driver) if debug_mode else None}
            except:
                pass
        
        # Si llegamos aquí, no se encontró nada claro
        return {'sin_resultados': True, 'mensaje': 'Tiempo agotado / No cargó tabla', 'img': get_base64_screenshot(driver)}

    except Exception as e:
        return {'error': str(e)[:100], 'img': get_base64_screenshot(driver)}

# --- INTERFAZ STREAMLIT ---

st.title("🕵️‍♂️ Consulta Masiva SRI (Selenium Headless)")

st.markdown("""
Esta herramienta usa un navegador virtual para consultar el SRI.
**Nota:** Si obtienes muchos errores, activa el modo Debug para ver qué está viendo el robot.
""")

# Sidebar para configuración
with st.sidebar:
    st.header("Configuración")
    debug_mode = st.checkbox("📸 Modo Debug (Ver capturas)", value=False, help="Muestra una foto de lo que ve el navegador. Útil si salen errores.")
    st.info("Si el servidor está lento, el proceso puede tardar unos 10-15 segundos por persona.")

# Área de entrada
txt_input = st.text_area("Pega los nombres aquí (uno por línea):", height=150, placeholder="Ejemplo:\nJUAN PEREZ\nMARIA LOPEZ")

if st.button("🚀 Iniciar Búsqueda", type="primary"):
    nombres = [n.strip() for n in txt_input.split('\n') if n.strip()]
    
    if not nombres:
        st.warning("⚠️ Por favor ingresa al menos un nombre.")
    else:
        # Contenedores para UI dinámica
        progress_bar = st.progress(0)
        status_text = st.empty()
        result_container = st.container()
        
        resultados_lista = []
        driver = None
        
        try:
            with st.spinner('🔧 Iniciando navegador virtual... (esto toma unos segundos)'):
                driver = create_driver()
            
            total = len(nombres)
            
            for i, nombre in enumerate(nombres):
                status_text.markdown(f"⏳ Procesando **{i+1}/{total}**: `{nombre}`...")
                
                # LLAMADA PRINCIPAL
                datos = consultar_persona(driver, nombre, debug_mode)
                
                # LÓGICA DE RESPUESTA
                ruc_final = "Error"
                estado = "Desconocido"
                
                if datos.get('ruc'):
                    ruc_final = datos['ruc']
                    estado = "Encontrado"
                    st.toast(f"✅ {nombre}: {ruc_final}")
                elif datos.get('sin_resultados'):
                    ruc_final = "Sin Resultados"
                    estado = "No Encontrado"
                elif datos.get('error'):
                    ruc_final = f"Error: {datos['error']}"
                    estado = "Error Sistema"
                
                # Guardar resultado
                resultados_lista.append({
                    'Nombre Buscado': nombre,
                    'Resultado RUC': ruc_final,
                    'Estado': estado,
                    'Fecha': time.strftime("%Y-%m-%d %H:%M")
                })
                
                # ACTUALIZAR BARRA
                progress_bar.progress((i + 1) / total)
                
                # MOSTRAR RESULTADO VISUAL (Expandible para fotos)
                with result_container:
                    with st.expander(f"{'✅' if estado == 'Encontrado' else '⚠️'} {nombre} -> {ruc_final}", expanded=(debug_mode or estado == "Error Sistema")):
                        if datos.get('img'):
                            st.image(base64.b64decode(datos['img']), caption=f"Captura del navegador para: {nombre}")
                        else:
                            st.write("No se requirió captura de pantalla.")
                            
        except Exception as e:
            st.error(f"💥 Error crítico del navegador: {e}")
        finally:
            if driver:
                driver.quit()
            status_text.success("✅ Proceso Finalizado")
            
            # --- SECCIÓN DE DESCARGA ---
            if resultados_lista:
                df = pd.DataFrame(resultados_lista)
                
                st.divider()
                st.subheader("📊 Resultados Finales")
                st.dataframe(df, use_container_width=True)
                
                # Botón CSV
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar Reporte (CSV)",
                    data=csv,
                    file_name=f'reporte_sri_{int(time.time())}.csv',
                    mime='text/csv',
                )