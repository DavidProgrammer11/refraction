# Registro de cambios

Todos los cambios relevantes de Refracción se apuntan aquí, escritos para quien usa la app.

## [2.1.0] - 2026-10-29

### Añadido
- Exportar el cálculo a PDF (Archivo › Exportar el cálculo a PDF…, Ctrl+P, o el enlace de la
  tarjeta de resultado): en un A4, la primera página lleva el resultado, el diagrama y la curva
  de la ley de Snell, y la segunda el paso a paso entero.
- Junto a cada haz, una cota de su longitud de onda (λ₁ y λ₂): se ve cuánto se aprietan las ondas.

### Cambiado
- Las ondas se dibujan como bandas que avanzan, en un haz más ancho: se ve cómo se quiebran los
  frentes al cruzar la superficie.
- Los rayos brillan como luz y la superficie de separación lleva su rótulo.
- En el paso a paso, las divisiones se escriben como fracciones, igual que en un libro.
- El ejecutable pesa casi la mitad y se comprueba solo al compilarlo.

### Corregido
- Con la ventana minimizada, la animación seguía funcionando y gastando batería.
- Los botones propios de Qt salían en inglés («Yes», «No»); ahora dicen «Sí», «No», «Cancelar».
- El nombre y la cota del haz refractado ya no quedan dentro del haz cuando este sale más ancho.

## [2.0.0] - 2026-10-29

Versión nueva desde cero, en PySide6, sobre la calculadora original.

### Añadido
- Diagrama de la refracción con los dos medios, la normal, los rayos incidente, reflejado y
  refractado, y sus ángulos. Los rayos se arrastran con el ratón.
- Frentes de onda animados que enseñan por qué se dobla la luz (λ = λ₀ / n).
- El cálculo paso a paso con los números del usuario, con comprobación y explicación física.
- Reflexión total interna con su ángulo crítico, ángulos imposibles e índices indeterminados,
  explicados en vez de dar un error.
- Gráficas de la curva θ₂(θ₁) y de la luz reflejada y transmitida (Fresnel, Brewster).
- Lista de 16 materiales y 8 ejemplos reales en el menú Ejemplos.
- Historial de cálculos, exportable a Excel (CSV).
- Guardar el diagrama como PNG y copiarlo al portapapeles.
- La ventana recuerda cómo se dejó (incógnita, datos, pestaña y tamaño).

### Cambiado
- Se elige qué calcular con unos botones, en lugar de dejar una casilla vacía.
- El resultado aparece al momento, sin pulsar «Calcular».
- Los números se escriben y se muestran con coma decimal; el punto también vale.

### Corregido
- La reflexión total interna ya no sale como «Error al ingresar».
- Si se dejaban varias casillas vacías, el resultado dependía de cuál se miraba primero.

## [1.0.0]

- Calculadora de la ley de Snell en Tkinter (`legado/refraction.pyw`).
