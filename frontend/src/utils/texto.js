// Pone en mayúscula solo la primera letra ("jueves, 29 de octubre" → "Jueves, 29 de octubre").
// No usar text-transform: capitalize para fechas: convierte "de" en "De".
export function capitalizar(texto) {
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}
