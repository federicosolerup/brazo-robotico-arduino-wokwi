
# Brazo Robótico

Cadena **hombro → húmero → codo → antebrazo → muñeca**, con dos servomotores, la muñeca es el efector final.

**PDF:** [Abrir informe](05_ActividadGrupal_Mod09_Sensores_Grupo3.pdf)

**Wokwi:** [Abrir simulación](https://wokwi.com/projects/478894577015484417)

![Hombro y codo, una articulación por vez](salidas/brazo.gif)

## Secuencia

| Tramo | Articulación que se mueve | Hombro | Codo |
|---|---|---:|---:|
| P0 · Reposo | Ninguna | 30° | 30° |
| P0 → P1 | Hombro | 30° → 75° | Fijo en 30° |
| P1 → P2 | Codo | Fijo en 75° | 30° → 90° |
| P2 → P3 | Hombro | 75° → 30° | Fijo en 90° |
| P3 → P4 | Codo | Fijo en 30° | 90° → 30° |
