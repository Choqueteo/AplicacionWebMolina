import LegalLayout from '../components/layout/LegalLayout'

export default function PoliticaPrivacidad() {
  return (
    <LegalLayout titulo="Política de Privacidad">
      <p>
        En cumplimiento del Reglamento (UE) 2016/679 (RGPD) y la Ley Orgánica 3/2018 (LOPDGDD),
        te informamos del tratamiento de tus datos personales.
      </p>

      <h2>Responsable del tratamiento</h2>
      <ul>
        <li><strong>Denominación social / nombre comercial:</strong> RM — Peluquería · Barbería</li>
        <li><strong>Razón social / titular:</strong> RMolinaStyle</li>
        <li><strong>Email de contacto:</strong>Aún no disponible (consulte rmolinastyle en Instagram)</li>
      </ul>

      <h2>Datos que tratamos</h2>
      <ul>
        <li>Nombre completo</li>
        <li>Dirección de correo electrónico</li>
        <li>Número de teléfono</li>
        <li>Historial de citas (servicios, fechas y horas)</li>
        <li>Fecha y versión de aceptación de esta política</li>
      </ul>

      <h2>Finalidad del tratamiento</h2>
      <ul>
        <li>Gestionar el registro de usuarios y el acceso al servicio de reservas.</li>
        <li>Gestionar, confirmar y recordar las citas reservadas.</li>
        <li>Contactar al cliente en caso de cambios o incidencias en su cita.</li>
      </ul>

      <h2>Base legal</h2>
      <ul>
        <li>
          <strong>Ejecución de un contrato:</strong> el tratamiento es necesario para la prestación
          del servicio de reservas (art. 6.1.b RGPD).
        </li>
        <li>
          <strong>Consentimiento:</strong> otorgado en el momento del registro mediante aceptación
          expresa de esta política (art. 6.1.a RGPD).
        </li>
      </ul>

      <h2>Destinatarios y encargados del tratamiento</h2>
      <p>Tus datos pueden ser accedidos o procesados por los siguientes encargados:</p>
      <ul>
        <li>
          <strong>Render Services, Inc.</strong> — proveedor de alojamiento (servidores en
          Frankfurt, Unión Europea). Los datos permanecen en la UE.
        </li>
        <li>
          <strong>Cloudflare, Inc.</strong> — proveedor de red de distribución de contenido (CDN)
          y protección frente a ataques.
        </li>
        <li>
          <strong>Telegram Messenger Inc.</strong> — usado únicamente para notificaciones internas
          al peluquero (recordatorios de citas). Implica una <strong>transferencia internacional
          de datos fuera de la UE</strong>; base legal aplicable: [indicar mecanismo de transferencia,
          p. ej. cláusulas contractuales tipo o decisión de adecuación].
        </li>
      </ul>
      <p>No se ceden datos a terceros con fines comerciales ni publicitarios.</p>

      <h2>Transferencias internacionales</h2>
      <p>
        El uso de Telegram para el envío de notificaciones al peluquero implica la transferencia de
        datos (nombre del cliente, teléfono, fecha y hora de la cita) a servidores fuera del Espacio
        Económico Europeo. La base legal de esta transferencia es: [indicar mecanismo aplicable].
      </p>

      <h2>Plazo de conservación</h2>
      <p>
        Los datos se conservarán mientras el usuario mantenga su cuenta activa y, una vez suprimida,
        durante el plazo mínimo exigido por las obligaciones legales aplicables.
        [Indicar plazo concreto si se conoce.]
      </p>

      <h2>Derechos del interesado</h2>
      <p>
        Puedes ejercer en cualquier momento los siguientes derechos:
      </p>
      <ul>
        <li><strong>Acceso:</strong> conocer qué datos tuyos tratamos.</li>
        <li><strong>Rectificación:</strong> corregir datos inexactos o incompletos.</li>
        <li><strong>Supresión:</strong> solicitar el borrado de tus datos («derecho al olvido»).</li>
        <li><strong>Limitación:</strong> solicitar que suspendamos temporalmente el tratamiento.</li>
        <li><strong>Oposición:</strong> oponerte al tratamiento en determinadas circunstancias.</li>
        <li><strong>Portabilidad:</strong> recibir tus datos en formato estructurado.</li>
      </ul>
      <p>
        Puedes ejercer estos derechos desde tu cuenta (sección «Mi cuenta») o enviando
        un escrito a <a href="mailto:[email de contacto]">[email de contacto]</a>.
      </p>
      <p>
        Si no obtienes una respuesta satisfactoria, puedes reclamar ante la{' '}
        <strong>Agencia Española de Protección de Datos (AEPD)</strong>{' '}
        en <a href="https://www.aepd.es" target="_blank" rel="noopener noreferrer">www.aepd.es</a>.
      </p>

      <h2>Seguridad</h2>
      <p>
        Aplicamos medidas técnicas y organizativas adecuadas para proteger tus datos: cifrado de
        contraseñas con bcrypt, comunicaciones cifradas mediante HTTPS/TLS, acceso restringido
        a la base de datos y copias de seguridad periódicas.
      </p>

      <h2>Cambios en esta política</h2>
      <p>
        Podemos actualizar esta política para adaptarla a cambios normativos o del servicio.
        Cuando lo hagamos, lo comunicaremos por los canales habituales y, si los cambios son
        sustanciales, solicitaremos de nuevo tu consentimiento.
      </p>
    </LegalLayout>
  )
}
