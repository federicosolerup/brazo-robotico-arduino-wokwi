# Texto sugerido para el informe

## Brazo con movimientos articulares independientes

Se desarrolló un brazo robótico planar de dos grados de libertad, compuesto por hombro, húmero, codo y antebrazo. La muñeca, ubicada en el extremo del antebrazo, actúa como efector final y no incorpora un tercer servomotor.

El servo conectado a D9 controla el hombro y el conectado a D10 controla el codo. El programa ejecuta cuatro desplazamientos alternados: primero mueve el hombro de 30° a 75° con el codo fijo en 30°; luego flexiona el codo hasta 90° con el hombro fijo; después devuelve el hombro a 30° y, finalmente, devuelve el codo a 30°. Cada tramo utiliza una interpolación cúbica de 1,5 segundos y una pausa de 0,3 segundos al terminar.

El ángulo del codo se mide respecto del húmero. Cuando gira el hombro, el antebrazo acompaña el movimiento porque forma parte de la misma cadena mecánica; sin embargo, la flexión del codo permanece constante. Cuando se mueve únicamente el codo, el húmero permanece inmóvil.

Para visualizar la secuencia se registraron en Wokwi el tiempo y las consignas angulares enviadas a ambos servomotores. El notebook de Python utiliza esos datos y la cinemática directa de un manipulador de dos articulaciones rotacionales para representar el brazo en vista lateral, junto con los gráficos de los ángulos y la indicación de qué articulación se mueve.

Se obtuvieron 363 registros de una secuencia de aproximadamente 7,34 segundos. La comparación entre muestras consecutivas mostró cero cambios simultáneos de las consignas del hombro y del codo. También se verificaron los extremos de cada tramo y el regreso a la configuración inicial.

Las dimensiones del húmero y del antebrazo se fijaron con fines ilustrativos en 18 cm y 15 cm. La visualización reproduce las órdenes angulares del programa, sin medir la respuesta física ni calcular cargas o torque.

**Epígrafe sugerido:** Brazo de hombro y codo con movimientos alternados. Se identifican el húmero, el antebrazo y la muñeca como efector final; los gráficos muestran que las dos consignas angulares no cambian simultáneamente.
