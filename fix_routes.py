import pandas as pd

df = pd.read_csv('historial_extendido.csv')

# Corregir ruta_completa
def fix_ruta(row):
    if pd.notna(row['aeropuertos_escala']) and row['aeropuertos_escala'] != '':
        return f"{row['origen']},{row['aeropuertos_escala']},{row['destino']}"
    else:
        return f"{row['origen']},{row['destino']}"

df['ruta_completa'] = df.apply(fix_ruta, axis=1)
df.to_csv('historial_extendido.csv', index=False)
print("✅ Rutas corregidas")
print(df[['origen', 'aeropuertos_escala', 'destino', 'ruta_completa']].head())
