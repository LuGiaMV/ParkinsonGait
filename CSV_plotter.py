import pandas as pd
import matplotlib.pyplot as plt
import os
import re

if not os.path.basename(os.getcwd()) == "ParkinsonGait":
    os.chdir("ParkinsonGait")
dirs = [f for f in os.listdir() if os.path.isdir(f) and f.startswith("Marcha")]
# print(dirs)
print("\nSelecciona un dia:")
for i, f in enumerate(dirs):
    print(f"{i+1}. {f}")
carpeta = input("\nIngresa número de dia [Enter para seleccionar la última]: ")
if carpeta == "":
    carpeta = dirs[-1]
else:
    carpeta = dirs[int(carpeta)-1]
# print(carpeta)
files = ["_".join(f.split("_")[0:2]) for f in os.listdir(carpeta) if f.endswith("_arduino_1.csv")]
# print(files)
if len(files) != 1:
    print("\nSelecciona una marcha")
    for i, f in enumerate(files):
        print(f"{i+1}. {f}")
    marcha = input("\nIngresa número de Marcha [Enter para seleccionar la última]: ") 
    if marcha == "":
        marcha = files[-1]
    else:
        marcha = files[int(marcha)-1]
else:
    marcha = files[-1]
# print(marcha)
files = [f for f in os.listdir(carpeta) if f.startswith(marcha) and re.search(r"_arduino_\d.csv$", f)]
# print(files)
print("\nSelecciona un segmento de marcha:")
for i, f in enumerate(files):
    print(f"{i+1}. {f}")
seg = input("\nIngresa segmnto de marcha [Enter para seleccionar todos juntos]: ")
if seg == "":
    dfs = []
    for file in files:
        df = pd.read_csv(os.path.join(carpeta, file))
        dfs.append(df)
    data = pd.concat(dfs, ignore_index=True)
    # print(data.shape)
else:
    seg = files[int(seg)-1]
    data = pd.read_csv(os.path.join(carpeta, seg))

data["Timestamp"] = pd.to_datetime(data["Timestamp"])  # convertir a formato de tiempo
fig, axs = plt.subplots(6, 1, figsize=(15, 16))
fig.tight_layout(pad=3.0)
# data["id"] = data.index

axs[0].grid()
axs[0].plot(data["Timestamp"], data["xAcel_L"], label="X", color='r')
axs[0].plot(data["Timestamp"], data["yAcel_L"], label="Y", color='g')
axs[0].plot(data["Timestamp"], data["zAcel_L"], label="Z", color='b')
axs[0].set_title('Lectura de Acelerómetro Izquierdo')
axs[0].legend(loc="upper right")

axs[1].grid()
axs[1].plot(data["Timestamp"], data["xAcel_R"], label="X", color='y')
axs[1].plot(data["Timestamp"], data["yAcel_R"], label="Y", color='c')
axs[1].plot(data["Timestamp"], data["zAcel_R"], label="Z", color='m')
axs[1].set_title('Lectura de Acelerómetro Derecho')
axs[1].legend(loc="upper right")

axs[2].grid()
axs[2].plot(data["Timestamp"], data["xGyro_L"], label="X", color='r')
axs[2].plot(data["Timestamp"], data["yGyro_L"], label="Y", color='g')
axs[2].plot(data["Timestamp"], data["zGyro_L"], label="Z", color='b')
axs[2].set_title('Lectura de Giroscopio Izquierdo')
axs[2].legend(loc="upper right")

axs[3].grid()
axs[3].plot(data["Timestamp"], data["xGyro_R"], label="X", color='y')
axs[3].plot(data["Timestamp"], data["yGyro_R"], label="Y", color='c')
axs[3].plot(data["Timestamp"], data["zGyro_R"], label="Z", color='m')
axs[3].set_title('Lectura de Giroscopio Derecho')
axs[3].legend(loc="upper right")

axs[4].grid()
axs[4].plot(data["Timestamp"], data["xMag_L"], label="X", color='r')
axs[4].plot(data["Timestamp"], data["yMag_L"], label="Y", color='g')
axs[4].plot(data["Timestamp"], data["zMag_L"], label="Z", color='b')
axs[4].set_title('Lectura de Magnetómetro Izquierdo')
axs[4].legend(loc="upper right")

axs[5].grid()
axs[5].plot(data["Timestamp"], data["xMag_R"], label="X", color='y')
axs[5].plot(data["Timestamp"], data["yMag_R"], label="Y", color='c')
axs[5].plot(data["Timestamp"], data["zMag_R"], label="Z", color='m')
axs[5].set_title('Lectura de Magnetómetro Derecho')
axs[5].legend(loc="upper right")

plt.xlabel("Tiempo")
plt.show()
# plt.savefig("grafico_lecturas.png", dpi=100)