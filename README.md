Cherry's Extras Bot
Bot de Telegram que escucha mensajes con tarjetas de crédito en formato CC|MM|YY|CVV, las procesa, genera 8 variantes enmascaradas y las publica en un canal con imagen y botones.

🚀 Despliegue en Railway
Sube este repositorio a Railway.
Configura las siguientes variables de entorno en el panel de Railway:
Variable	Descripción	Ejemplo
API_ID	Tu API ID de my.telegram.org	123456
API_HASH	Tu API hash	abcdef...
BOT_TOKEN	Token del bot de Telegram	123:ABC...
CHANNEL_ID	ID del canal donde publicar (número negativo)	-1001234567890
PHONE_NUMBER	Número de teléfono de la cuenta que escucha	+584123889230
PUBLICATION_DELAY_SECONDS	(Opcional) Segundos entre publicaciones	5
SESSION_STRING	Obligatorio (ver abajo)	Cadena larga
Obtener SESSION_STRING:

Ejecuta el script localmente (con las mismas credenciales) para que se autentique.
Copia la cadena que aparece en la consola después del mensaje GUARDA ESTA CADENA....
Pégala como valor de SESSION_STRING en Railway.
Reinicia el despliegue en Railway.
El bot comenzará a escuchar mensajes en todos los chats donde esté agregado (privados, grupos, canales).

⚙️ Funcionamiento
Detecta tarjetas en formato XXXXXXXXXXXXXXXX|MM|YY|CVV (14-16 dígitos).
Evita duplicados mediante caché.
Consulta información del BIN desde bins.antipublic.cc.
Genera 8 enmascaramientos distintos (extras).
Publica en el canal configurado con una imagen aleatoria.
Control de velocidad para evitar baneos por spam.
📦 Dependencias
Ver requirements.txt.

🛠️ Mantenimiento
Los logs se imprimen en consola (visibles en Railway).
Si cambias de número, actualiza PHONE_NUMBER y regenera la SESSION_STRING.
⚠️ Nota importante
Este bot está diseñado para fines educativos o de automatización personal.
El uso indebido de tarjetas de crédito es ilegal. Úsalo bajo tu propia responsabilidad.

Creado por [Tu nombre] – Adaptado para Railway.
