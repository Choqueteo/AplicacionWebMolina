import LegalLayout from '../components/layout/LegalLayout'

export default function PoliticaCookies() {
  return (
    <LegalLayout titulo="Política de Cookies">
      <p>
        Esta política explica qué almacenamiento local utiliza este sitio web y por qué.
      </p>

      <h2>¿Qué almacenamos?</h2>
      <p>
        Este sitio web utiliza <strong>exclusivamente almacenamiento técnico</strong> en el
        navegador (<code>localStorage</code>) para guardar el token de sesión (JWT) que
        permite mantenerte autenticado.
      </p>
      <ul>
        <li>
          <strong>Token de sesión (JWT):</strong> se guarda en <code>localStorage</code> al
          iniciar sesión y se elimina al cerrarla. Su único propósito es identificarte en
          cada petición al servidor.
        </li>
      </ul>

      <h2>¿Usamos cookies?</h2>
      <p>
        No. Este sitio no deposita ninguna cookie en tu navegador. El token de sesión se
        almacena en <code>localStorage</code>, no en una cookie.
      </p>

      <h2>¿Necesita consentimiento?</h2>
      <p>
        No. El almacenamiento técnico descrito es estrictamente necesario para prestar el
        servicio solicitado por el usuario (gestión de sesión). Está exento del requisito
        de consentimiento previo conforme al artículo 22.2 de la LSSI-CE y la guía de la AEPD
        sobre el uso de cookies.
      </p>

      <h2>¿Usamos analítica u otras tecnologías de seguimiento?</h2>
      <p>
        No. Este sitio no utiliza herramientas de analítica (Google Analytics, Hotjar, etc.)
        ni ninguna otra tecnología de seguimiento o publicidad. No se instala ningún script
        de terceros con fines de medición o personalización.
      </p>
      <p>
        Por este motivo, <strong>no se muestra un banner de cookies</strong>: no existe nada
        que requiera tu consentimiento previo.
      </p>

      <h2>Cambios futuros</h2>
      <p>
        Si en el futuro incorporáramos servicios de analítica u otras tecnologías no esenciales,
        actualizaríamos esta política y mostraríamos un panel de consentimiento que te permitiría
        aceptar o rechazar cada categoría de forma granular, sin que ningún script se cargara
        antes de tu elección.
      </p>

      <h2>Contacto</h2>
      <p>
        Para cualquier duda sobre el almacenamiento de datos en tu navegador puedes escribirnos
        a <a href="mailto:[email de contacto]">[email de contacto]</a>.
      </p>
    </LegalLayout>
  )
}
