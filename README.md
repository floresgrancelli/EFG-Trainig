# EFG Training 💜

App independiente de entrenamiento, con estética negro/púrpura, rutina importada y evolución pública.

## Qué se importó

- **5 días por semana y 12 semanas de programación** (3 ciclos de 4 semanas).
- **182 ejercicios del plan original** (46 + 46 + 45 + 45), conservados, más **362** en las semanas 5–12 (estructura repetida): total **544 ejercicios programados**. Las cargas futuras no se inventan.
- **33 pesos de referencia informados en libras** en la primera semana y sus conversiones a kg.
- Caso especial de curl femoral **70 / 90 / 110 / 110 lb**, conservado como cuatro cargas por serie en lugar del error original de la planilla.
- Las celdas vacías permanecen vacías. Ninguna de las cargas de referencia se presenta como sesión efectivamente realizada.
- No se incluyeron los nombres del alumno, entrenador ni gimnasio del encabezado original en los datos públicos.

## Archivos

- \`app.py\`: app web pública, gráficos, registro y edición.
- \`data/plan.json\`: programación de doce semanas; cuatro originales importadas desde Excel y ocho creadas repitiendo el ciclo.
- \`data/history.json\`: sesiones reales. Comienza vacío y se guarda en GitHub cuando el administrador registra datos.
- \`requirements.txt\`: dependencias.
- \`.streamlit/config.toml\`: tema oscuro violeta.

## Publicar en Streamlit Community Cloud

1. Ingresar en [share.streamlit.io](https://share.streamlit.io), autenticar con GitHub y elegir **New app**.
2. Elegir repositorio \`floresgrancelli/EFG-Training\`, rama \`main\` y main file path \`app.py\`.
3. Elegir un subdominio disponible, por ejemplo \`efg-training\`.
4. En **App settings > Secrets**, configurar **solo dentro de Streamlit Cloud**:

\`\`\`toml
ADMIN_PIN = "ELEGIR_UN_PIN_LARGO_Y_PRIVADO"
GITHUB_TOKEN = "PEGAR_AQUI_TOKEN_FINE_GRAINED"
\`\`\`

**No pegar el PIN ni el token en GitHub, en el código, en capturas, ni en este chat.** Elegir un PIN largo y no reutilizado; la protección por PIN es básica y no sustituye autenticación robusta.

Para \`GITHUB_TOKEN\`, crear un **Fine-grained Personal Access Token** desde la configuración de GitHub:
- Propietario: \`floresgrancelli\`.
- Acceso únicamente a este repositorio (\`EFG-Training\`).
- Repository permissions: **Contents = Read and write** (los demás permisos mínimos que exija GitHub).
- Mantenerlo secreto. Renovarlo antes de su vencimiento.

Hasta que estos Secrets estén configurados, el programa es de **solo lectura**, y el formulario de acceso lo indica de forma explícita.

**Nota de seguridad:** un PIN no equivale a un sistema de identidad avanzado; usar uno largo, distinto de otras contraseñas. Para varios administradores o datos sensibles, migrar a autenticación formal y a una base de datos privada. Esta versión guarda el historial en un repositorio **público** porque se decidió que los entrenamientos y estadísticas sean visibles para cualquiera. No almacenar datos médicos.

## Guardado de entrenamientos

Con el PIN correcto, la pestaña **ADMIN** permite:
- Registrar las series de un ejercicio, con peso en kg o lb y repeticiones.
- Cargar y corregir el peso corporal por fecha, para generar gráficos semanales públicos.
- Guardar en \`data/history.json\` con la fecha, semana, día y observaciones.
- Actualizar una sesión anterior registrando de nuevo el mismo ejercicio y fecha.
- Editar el texto del plan; GitHub redepliega automáticamente la nueva versión.

Cada modificación se registra como commit. El público puede consultar la rutina y el historial, pero no puede escribir sin el token privado. Los gráficos de sesiones reales se generan con sesiones **reales**, sin convertir referencias del Excel en entrenamientos inventados.

## Temporizador de descansos

- Nueva pestaña **⏱️ TEMPORIZADOR** para utilizar desde iPhone o Mac durante la rutina.
- Tres descansos predefinidos: **3:00**, **2:00** y **1:30** minutos.
- Botones **Iniciar / Continuar**, **Pausar** y **Reiniciar**; círculo de progreso y señal sonora/vibración cuando el navegador lo permita.
- Cuenta atrás basada en la hora real, por lo que se recalcula aunque el navegador limite la actualización en segundo plano. El aviso sonoro **no está garantizado** con iPhone bloqueado.
- El contador se ejecuta en el navegador y no guarda ni publica información de salud.

## Evolución por repeticiones a igual carga

- En **PROGRESO**, seleccioná un ejercicio y una carga fija: el gráfico muestra la serie con mayor número de repeticiones registrada **en cada fecha con esa carga**.
- La comparación incluye la última mejor serie y el cambio de repeticiones respecto del primer registro a la misma carga.
- En **HISTORIAL**, el selector de indicadores ahora incluye **Repeticiones a igual carga**, además de carga máxima, volumen y repeticiones totales.
- Se muestran únicamente registros reales: **no** se suman repeticiones entre series distintas para declarar una mejora.
- Tené en cuenta el RIR y la técnica al comparar rendimiento; no se calcula una estimación de fuerza máxima.

## Máximo móvil en la rutina resumida

- La solapa **Rutina resumen** permite elegir las 12 semanas, de lunes a viernes, y ver pesos en kg/lb.
- Muestra **una sola cifra por ejercicio**, sin subtítulo de «semana 1»: la mayor carga conocida de los **últimos 30 días**, considerando reportes semanales y sesiones registradas desde ADMIN.
- Una carga nueva mayor actualiza automáticamente el máximo cuando se refresca el historial; puede bajar si un registro anterior queda fuera de los 30 días.
- Sin dato fechado reciente, se conserva como orientación la **referencia inicial sin fecha del Excel**, identificada en una nota general. No se presenta como entrenamiento nuevo.
- Las semanas 5–12 repiten el esquema de las primeras cuatro (sin progresiones de peso inventadas). Pueden editarse desde ADMIN.

## Independencia del laboratorio

Este proyecto **NO** modifica ni comparte archivos con \`Edu-Flores-Grancelli-lab\`. Ambos pueden desplegarse con URL diferentes.

## Bloque de hipertrofia y rutinas antiguas

- `data/active_plan.json` contiene las doce semanas del nuevo bloque: core y movilidad en dos vueltas, principales con tres series de 8–12 a RIR 2 y descansos explícitos.
- `data/plan.json` sigue siendo el plan anterior completo. No se reescriben sus 565 entradas ni las sesiones históricas para activar el nuevo plan.
- **Mi rutina** y **Rutina resumen** muestran el bloque nuevo. **Rutinas antiguas** permite consultar semanas, ejercicios, últimas cargas, mejores cargas comparables, referencias sin fecha y evolución de reportes anteriores.
- Las nuevas sesiones tienen `block_id` e identificadores distintos; Semana 1 del nuevo bloque no coincide con Semana 1 del anterior.
- Los gráficos utilizan equivalencias explícitas de nombres, separan variantes y condiciones de carga, y permiten filtrar por bloque. La primera sesión efectivamente registrada del bloque nuevo se marca en la curva; no se inventa una fecha de entrenamiento.
- Los pesos por mancuerna o por lado se conservan como tales, sin convertirlos en carga total ni sumar barras o plataformas desconocidas. Los giros rusos se ingresan por lado y se almacenan también como repeticiones totales para conservar la convención previa; la plancha se ingresa en segundos.
- Al guardar una sesión se conserva el documento histórico completo, incluidos otros metadatos; solo se actualiza el registro identificado por fecha y ejercicio del bloque nuevo.

Validación: `python -m unittest -v test_blocks.py` y arranque con `streamlit.testing.v1.AppTest`. El cambio se probó también con guardado simulado, sin crear entrenamientos reales.
