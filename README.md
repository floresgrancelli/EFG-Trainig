# EFG Training 💜

App independiente de entrenamiento, con estética negro/púrpura, rutina importada y evolución pública.

## Qué se importó

- **5 días por semana y 4 semanas de programación**.
- **182 filas de ejercicios** (46 + 46 + 45 + 45), con todos los nombres, series, repeticiones, intensidad/RIR, patrón muscular, bloque y observaciones técnicas.
- **33 pesos de referencia informados en libras** en la primera semana y sus conversiones a kg.
- Caso especial de curl femoral **70 / 90 / 110 / 110 lb**, conservado como cuatro cargas por serie en lugar del error original de la planilla.
- Las celdas vacías permanecen vacías. Ninguna de las cargas de referencia se presenta como sesión efectivamente realizada.
- No se incluyeron los nombres del alumno, entrenador ni gimnasio del encabezado original en los datos públicos.

## Archivos

- \`app.py\`: app web pública, gráficos, registro y edición.
- \`data/plan.json\`: programación de cuatro semanas, importada desde Excel.
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

Cada modificación se registra como commit. El público puede consultar la rutina y el historial, pero no puede escribir sin el token privado. Los gráficos se generan con sesiones **reales**, no a partir de las referencias del Excel.

## Independencia del laboratorio

Este proyecto **NO** modifica ni comparte archivos con \`Edu-Flores-Grancelli-lab\`. Ambos pueden desplegarse con URL diferentes.
