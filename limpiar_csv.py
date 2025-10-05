import pandas as pd
import re

# Cambia esta ruta por la de tu archivo original
input_file = r'C:\Users\User\Documents\datos_planos.csv'
output_file = r'C:\Users\User\Documents\datos_planos_limpio.csv'

# Leer el CSV con codificación latin-1 para evitar errores
df = pd.read_csv(input_file, encoding='latin-1')

# Función para limpiar texto (eliminar caracteres no ASCII y control)
def limpiar_texto(texto):
    if pd.isna(texto):
        return texto
    # Eliminar caracteres que no sean ASCII imprimibles ni comunes
    texto_limpio = re.sub(r'[^\x20-\x7EáéíóúÁÉÍÓÚñÑüÜ.,;:()¿¡\-\n\r\t]', '', texto)
    return texto_limpio

# Aplicar limpieza solo a la columna relato_consulta (texto largo)
df['relato_consulta'] = df['relato_consulta'].apply(limpiar_texto)

# Guardar CSV limpio en UTF-8
df.to_csv(output_file, index=False, encoding='utf-8')

print(f'Archivo limpio guardado en: {output_file}')
