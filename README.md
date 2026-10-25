# Brazo robótico con Arduino, Wokwi y Python

**Grupo 3 · Mateo Flores y Federico Soler**

Introducción a la Robótica · Universidad de Palermo

Control y visualización de un brazo con **dos grados de libertad**: giro de base y elevación de hombro. El programa de Arduino ejecutado en Wokwi registra sus consignas angulares; un notebook de Python reproduce esos datos como un brazo en 3D con gráficos sincronizados.

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/federicosolerup/brazo-robotico-arduino-wokwi/blob/main/Brazo_Robotico_Grupo3.ipynb)

## Demostración

![Brazo animado y consignas angulares de la base y del hombro](salidas/brazo.gif)

- **[Abrir el notebook en Google Colab](https://colab.research.google.com/github/federicosolerup/brazo-robotico-arduino-wokwi/blob/main/Brazo_Robotico_Grupo3.ipynb)** y elegir **Entorno de ejecución → Ejecutar todas**. La captura de Wokwi ya está incluida; no hace falta subir archivos para la primera reproducción.
- [Ver el notebook en GitHub](Brazo_Robotico_Grupo3.ipynb).
- [Descargar el video MP4](salidas/brazo.mp4?raw=true).
- [Descargar el reproductor HTML](salidas/brazo_interactivo.html?raw=true). Guardarlo y abrirlo en el navegador: incluye los cuadros y controles y funciona sin internet.
- [Consultar el proyecto original en Wokwi](https://wokwi.com/projects/477503605988146177).

GitHub muestra el notebook como documento estático. La animación con controles se ejecuta en Colab o en el HTML descargado.

## Qué hace el proyecto

Al presionar el pulsador se ejecuta esta secuencia:

| Configuración | Base, D9 | Hombro, D10 |
|---|---:|---:|
| P0 · Reposo | 90° | 90° |
| P1 | 30° | 45° |
| P2 | 150° | 45° |
| P3 · Regreso | 90° | 90° |

Cada tramo utiliza una interpolación cúbica de 1500 ms, con velocidad ideal nula al iniciar y terminar:

```text
s = t / T
q(t) = q0 + (qf - q0) · (3s² - 2s³)
```

Hay pausas de 300 ms después de cada tramo, incluida la pausa final presente en el programa original. En el segundo tramo el hombro se mantiene en 45° mientras gira la base, por lo que el extremo describe un arco. Mantener el pulsador presionado no repite el ciclo.

## De Wokwi a la animación

```text
Arduino en Wokwi → monitor serie → CSV → cinemática directa → brazo en 3D
```

La captura incluida contiene **271 registros**, con una duración observada de **5488 ms**. Se obtuvo ejecutando el [sketch instrumentado](wokwi/sketch.ino) en una sesión temporal del proyecto de Wokwi, sin guardar cambios en el proyecto publicado.

El registro contiene los mismos ángulos enteros enviados a `Servo.write()`, junto con el tiempo obtenido de `millis()` y la fase de la secuencia:

```csv
ciclo,tiempo_ms,base_deg,hombro_deg,fase
1,0,90,90,inicio
1,1,90,90,tramo_1
1,22,89,89,tramo_1
```

La visualización mantiene cada consigna hasta la siguiente muestra. La impresión serial agrega una pequeña carga de procesamiento; por eso se utilizan los tiempos registrados, sin suponer intervalos exactamente iguales a 20 ms.

Se verificó que las cuatro configuraciones aparecen en orden, el hombro permanece fijo durante el segundo tramo y ambas consignas terminan en 90°. Los resultados están en [verificacion.json](datos/verificacion.json), y la procedencia y las huellas SHA-256 del sketch y del diagrama en [procedencia.json](datos/procedencia.json).

## Modelo cinemático

Se representa una base giratoria, un hombro y un único eslabón móvil. Las dimensiones son ilustrativas: altura `h = 8 cm`, desplazamiento fijo `d = 3 cm` entre el eje de la base y el hombro y longitud del brazo `L = 18 cm`.

Se define X hacia el frente, Y hacia la izquierda del robot y Z hacia arriba. Los ángulos del modelo se relacionan con las consignas como `φ = 90° − base_deg` y `β = hombro_deg`. La posición del extremo se obtiene mediante cinemática directa:

```text
x = (d + L cos β) cos φ
y = (d + L cos β) sin φ
z = h + L sin β
```

La separación `d` es fija y permite visualizar el giro de la base incluso con el eslabón vertical. El modelo reproduce **órdenes de posición**; no mide la respuesta física de los servos ni calcula torque, cargas o colisiones. Los ángulos enviados están cuantizados en grados enteros.

## Ejecutar en el equipo

Requiere Python 3.10 o posterior. Desde la carpeta del repositorio:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

python -m pip install -r requirements.txt
python visualizar_brazo.py --csv datos/captura_wokwi.csv --gif --mp4
```

La salida se guarda en `salidas/`. El MP4 requiere FFmpeg instalado y disponible en PATH; si no está disponible, omitir `--mp4`. El HTML y el GIF no necesitan FFmpeg. Sin `--csv` se genera una demostración teórica, identificada expresamente como tal.

## Capturar otra ejecución

1. Abrir el proyecto de Wokwi y pegar [wokwi/sketch.ino](wokwi/sketch.ino) en el editor de `sketch.ino`. Conservar las conexiones: D9 a base, D10 a hombro y D2 al pulsador conectado a GND. Se utiliza `INPUT_PULLUP`.
2. Iniciar la simulación, presionar el pulsador y esperar hasta `# FIN_CICLO`.
3. Copiar el monitor serie, incluido el encabezado CSV, y guardarlo en UTF-8 con extensión `.csv`.
4. En Colab, elegir `MODO = "subir_csv"` o `"pegar_csv"`. El notebook también permite elegir un ciclo si se registraron varios.

## Archivos

| Archivo o carpeta | Contenido |
|---|---|
| [Brazo_Robotico_Grupo3.ipynb](Brazo_Robotico_Grupo3.ipynb) | Notebook completo, con datos y código de Arduino incluidos |
| [visualizar_brazo.py](visualizar_brazo.py) | Lectura de CSV, geometría, animación y exportación local |
| [wokwi/](wokwi/) | Sketch instrumentado, conexionado y dependencia Servo |
| [datos/](datos/) | Captura, procedencia y verificación |
| [salidas/](salidas/) | GIF, MP4, HTML, captura de Wokwi y cuatro imágenes para el informe |
| [LEEME.md](LEEME.md) | Guía detallada y texto sugerido para el trabajo escrito |

## Referencias

- Universidad de Palermo. *Trayectorias* e *Implementación de las trayectorias robóticas*. Apuntes del módulo 6 de Introducción a la Robótica.
- [Monitor serie de Wokwi](https://docs.wokwi.com/guides/serial-monitor).
- [Servomotor de Wokwi](https://docs.wokwi.com/parts/wokwi-servo).
- [Animaciones de Matplotlib](https://matplotlib.org/stable/api/animation_api.html).
- [Gráficos 3D de Matplotlib](https://matplotlib.org/stable/gallery/mplot3d/index.html).
