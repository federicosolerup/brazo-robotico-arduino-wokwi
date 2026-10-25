# Brazo robótico — Grupo 3

Visualización del proyecto de Mateo Flores y Federico Soler. Se conserva la secuencia del TP: `(90,90) → (30,45) → (150,45) → (90,90)`, con tres tramos cúbicos de 1500 ms y pausas de 300 ms, incluida la pausa final del programa original.

## Para verlo ahora

Abrir `salidas/brazo_interactivo.html` en Chrome o Edge y presionar ▶. Permite pausar, recorrer los cuadros y cambiar la velocidad. Funciona sin internet. `salidas/brazo.mp4` sirve para presentar o insertar en las diapositivas; `P0.png` a `P3.png` son capturas para el informe.

## Para usar Google Colab

Abrir directamente [el notebook desde GitHub en Colab](https://colab.research.google.com/github/federicosolerup/brazo-robotico-arduino-wokwi/blob/main/Brazo_Robotico_Grupo3.ipynb) y elegir **Entorno de ejecución → Ejecutar todas**.

Si se utiliza una copia descargada:

1. En Colab, elegir **Archivo → Subir notebook** y seleccionar `Brazo_Robotico_Grupo3.ipynb`. También se puede abrir el notebook desde Google Drive con Google Colaboratory.
2. Elegir **Entorno de ejecución → Ejecutar todas**. La primera ejecución usa una captura real de Wokwi incluida dentro del notebook y no necesita archivos adicionales.
3. Para una captura nueva, cambiar `MODO` a `subir_csv`, ejecutar y seleccionar el archivo guardado del monitor serie. Con `pegar_csv` también se puede pegar el texto directamente en la celda indicada.

El notebook contiene el código Python completo, el CSV de la captura y el sketch de Arduino. Puede descargarse un ZIP con el proyecto de Wokwi desde su última celda.

## Cómo se obtuvo la captura incluida

Se abrió el [proyecto original](https://wokwi.com/projects/477503605988146177), se reemplazó temporalmente el código del editor por `wokwi/sketch.ino`, se inició la simulación y se presionó el pulsador. Se recogieron **271 filas** del monitor serie, con una duración registrada de **5488 ms**. El proyecto publicado no se modificó ni se guardó.

`datos/captura_wokwi.csv` contiene los datos; `datos/procedencia.json` identifica el proyecto, el método, la fecha y las huellas SHA-256 del sketch y el conexionado. `salidas/captura_wokwi.png` documenta la ejecución.

El CSV registra los **ángulos enteros que el programa pasa a `Servo.write()`**. No registra posiciones medidas ni la respuesta mecánica del servo. La impresión serial agrega una pequeña carga al programa: los tiempos se toman de `millis()`, por lo que la reproducción usa los tiempos observados y no presupone muestras exactamente cada 20 ms. Los ángulos se mantienen hasta la siguiente muestra; no se interpola una curva nueva sobre los datos.

## Para obtener otra captura

1. Abrir el proyecto de Wokwi y pegar el contenido de `wokwi/sketch.ino` en `sketch.ino`. Se mantienen las conexiones existentes: D9 a base, D10 a hombro y D2 al pulsador conectado a GND. `INPUT_PULLUP` permanece activo.
2. Iniciar la simulación y presionar el botón. Esperar hasta `# FIN_CICLO`.
3. Copiar el texto del monitor serie, incluido el encabezado `ciclo,tiempo_ms,base_deg,hombro_deg,fase`, y guardarlo como archivo de texto UTF-8 con extensión `.csv`. El encabezado se imprime al iniciar la simulación.
4. Cargar el archivo en Colab. Si contiene varios ciclos, se usa el último por defecto; `CICLO` permite seleccionar otro. Ante reinicios con encabezado repetido, se toma la última sesión disponible.

## Qué robot representa

Es un modelo con **dos articulaciones rotacionales**: giro de base alrededor de Z y elevación del hombro. Incluye un único eslabón móvil sobre el hombro; no hay codo móvil ni tercer actuador.

Las dimensiones se eligen únicamente para visualizar: altura del hombro `h = 8 cm`, separación fija respecto del eje de la base `d = 3 cm` y longitud del brazo `L = 18 cm`. No son medidas de un prototipo construido. La separación fija permite ver el giro de la base incluso cuando el brazo está vertical.

Se define X hacia el frente, Y hacia la izquierda del robot y Z hacia arriba. El ángulo de orientación es `φ = 90° − base_deg`; la elevación es `β = hombro_deg`, medida desde la horizontal. Así, base = 90° mira hacia +X y hombro = 90° deja el brazo vertical.

La cinemática directa del extremo es:

```text
x = (d + L cos β) cos φ
y = (d + L cos β) sin φ
z = h + L sin β
```

Todos los cálculos trigonométricos convierten los grados a radianes. El modelo representa el movimiento ordenado; no calcula fuerzas, torque, cargas, colisiones ni error de seguimiento. El gráfico muestra las consignas enviadas a los servos, no una señal de encoder. La asignación de velocidad nula corresponde al perfil cúbico ideal; la salida de `Servo.write()` está cuantizada en grados enteros.

## Ejecutar como script local

Desde esta carpeta:

```powershell
python -m pip install -r requirements.txt
python visualizar_brazo.py --csv datos/captura_wokwi.csv --gif --mp4
```

MP4 requiere FFmpeg en PATH; HTML y GIF no lo necesitan. Sin `--csv`, se genera una demostración teórica claramente identificada, sin presentarla como captura de Wokwi.

## Texto sugerido para el informe

> Para visualizar el movimiento del brazo se desarrolló un modelo cinemático en Python. El programa de Arduino ejecutado en Wokwi registra por el puerto serie el tiempo y las consignas angulares enviadas a los servomotores. El notebook lee ese registro y representa un brazo con giro de base y elevación de hombro, junto con los gráficos de sus ángulos. El segundo tramo mantiene el hombro en 45° mientras gira la base, por lo que el extremo describe un arco. Las dimensiones del modelo son ilustrativas; la visualización reproduce las órdenes de posición y no constituye una simulación dinámica ni una medición de la respuesta física.

## Referencias

- Universidad de Palermo. *Trayectorias* e *Implementación de las trayectorias robóticas*. Apuntes del módulo 6 de Introducción a la Robótica.
- [Monitor serie de Wokwi](https://docs.wokwi.com/guides/serial-monitor).
- [Servo de Wokwi](https://docs.wokwi.com/parts/wokwi-servo).
- [Animaciones de Matplotlib](https://matplotlib.org/stable/api/animation_api.html).
- [Gráficos 3D de Matplotlib](https://matplotlib.org/stable/gallery/mplot3d/index.html).
