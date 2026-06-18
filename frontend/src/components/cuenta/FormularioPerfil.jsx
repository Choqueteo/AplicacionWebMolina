import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import FormField from '../ui/FormField'
import Button from '../ui/Button'
import client from '../../api/client'
import styles from './FormularioPerfil.module.css'

export default function FormularioPerfil() {
  const { usuario, refreshUsuario } = useAuth()
  const [nombre,   setNombre]   = useState(() => usuario?.nombre_completo ?? '')
  const [telefono, setTelefono] = useState(() => usuario?.telefono ?? '')
  const [errores,      setErrores]      = useState({})
  const [errorGeneral, setErrorGeneral] = useState('')
  const [exito,        setExito]        = useState(false)
  const [guardando,    setGuardando]    = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErrores({})
    setErrorGeneral('')
    setExito(false)
    setGuardando(true)
    try {
      await client.patch('/usuarios/me', { nombre_completo: nombre, telefono })
      await refreshUsuario()
      setExito(true)
    } catch (err) {
      const status = err.response?.status
      const data   = err.response?.data
      if (status === 422 && Array.isArray(data?.detail)) {
        const campos = {}
        for (const item of data.detail) {
          const campo = item.loc?.[1]
          if      (campo === 'nombre_completo') campos.nombre_completo = item.msg
          else if (campo === 'telefono')        campos.telefono        = item.msg
          else                                  setErrorGeneral(item.msg)
        }
        setErrores(campos)
      } else {
        setErrorGeneral(
          typeof data?.detail === 'string'
            ? data.detail
            : 'Error al guardar los cambios'
        )
      }
    } finally {
      setGuardando(false)
    }
  }

  return (
    <section className={styles.seccion}>
      <h2 className={styles.titulo}>Datos personales</h2>
      <form onSubmit={handleSubmit} noValidate className={styles.form}>
        <FormField
          label="Email"
          name="email"
          type="email"
          value={usuario?.email ?? ''}
          disabled
          readOnly
          ayuda="El email no es editable."
        />
        <FormField
          label="Nombre completo"
          name="nombre_completo"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          error={errores.nombre_completo}
          ayuda="Nombre y apellidos (mínimo dos palabras)"
          required
        />
        <FormField
          label="Teléfono"
          name="telefono"
          type="tel"
          value={telefono}
          onChange={(e) => setTelefono(e.target.value)}
          error={errores.telefono}
          ayuda="Número español (9 dígitos)"
          required
        />
        {errorGeneral && (
          <p className={styles.msgError} role="alert">{errorGeneral}</p>
        )}
        {exito && (
          <p className={styles.msgExito} role="status">Cambios guardados correctamente.</p>
        )}
        <Button type="submit" loading={guardando}>Guardar cambios</Button>
      </form>
    </section>
  )
}
