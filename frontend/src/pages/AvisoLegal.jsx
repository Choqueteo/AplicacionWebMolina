import LegalLayout from '../components/layout/LegalLayout'

export default function AvisoLegal() {
  return (
    <LegalLayout titulo="Aviso Legal">
      <p>
        En cumplimiento del artículo 10 de la Ley 34/2002, de 11 de julio, de Servicios de la Sociedad
        de la Información y del Comercio Electrónico (LSSI-CE), se pone a disposición de los usuarios la
        siguiente información:
      </p>

      <h2>Datos identificativos del titular</h2>
      <ul>
        <li><strong>Denominación social / nombre comercial:</strong> RM — Peluquería · Barbería</li>
        <li><strong>Razón social / titular:</strong> RMolinaStyle</li>
        <li><strong>Email de contacto:</strong>Aún no disponible (consulte rmolinastyle en Instagram)</li>
      </ul>

      <h2>Objeto y actividad</h2>
      <p>
        Este sitio web tiene por objeto la gestión de reservas de citas para el establecimiento
        RM — Peluquería · Barbería. El acceso y uso de este sitio web implica la aceptación
        de las presentes condiciones legales.
      </p>

      <h2>Propiedad intelectual e industrial</h2>
      <p>
        Los contenidos de este sitio web (textos, imágenes, logotipos y código fuente) son propiedad
        del titular o de sus licenciantes. Queda prohibida su reproducción, distribución o modificación
        sin autorización expresa.
      </p>

      <h2>Responsabilidad</h2>
      <p>
        El titular no garantiza la ausencia de errores en los contenidos ni la disponibilidad continua
        del servicio. El uso de este sitio web es responsabilidad del usuario.
      </p>

      <h2>Legislación aplicable</h2>
      <p>
        El presente aviso legal se rige por la legislación española. Para cualquier controversia,
        las partes se someten a los Juzgados y Tribunales correspondientes al domicilio del titular,
        salvo que la normativa de consumidores establezca otro fuero.
      </p>

      <h2>Contacto</h2>
      <p>
        Para cualquier consulta relacionada con este aviso legal puede dirigirse a{' '}
        <a href="mailto:[email de contacto]">[email de contacto]</a>.
      </p>
    </LegalLayout>
  )
}
