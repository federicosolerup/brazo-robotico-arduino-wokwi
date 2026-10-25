"""Visualizacion cinematica de un brazo con giro de base y elevacion de hombro.

Uso local: python visualizar_brazo.py --csv datos/captura_wokwi.csv
Sin --csv se usan datos teoricos, identificados como demostracion.
El notebook incluye estas mismas funciones y funciona sin descargar este archivo.
"""
from pathlib import Path
import argparse
import csv
import io
import re

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter, FFMpegWriter
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

PUNTOS = np.array([[90, 90], [30, 45], [150, 45], [90, 90]])
ALTURA_CM = 8.0
DESPLAZAMIENTO_CM = 3.0
LARGO_CM = 18.0
AZUL = '#176B9B'
NARANJA = '#DC7137'
TINTA = '#23384A'
FONDO = '#F7F8FA'


def datos_demostracion():
    """Calcula un ejemplo teorico; NO es una captura del simulador."""
    filas = []
    reloj = 0
    for i, (inicio, fin) in enumerate(zip(PUNTOS[:-1], PUNTOS[1:]), 1):
        for ms in range(0, 1501, 20):
            s = ms / 1500
            # Aproxima la conversion de Servo.write a grados enteros.
            q = (inicio + (fin - inicio) * (3*s*s - 2*s*s*s)).astype(int)
            filas.append([1, reloj + ms, *q, f'tramo_{i}'])
        reloj += 1520  # El original hace delay(20) tambien al llegar al extremo.
        for ms in range(0, 301, 20):
            filas.append([1, reloj + ms, *fin, f'pausa_{i}'])
        reloj += 300
    filas.append([1, reloj, 90, 90, 'fin'])
    texto = io.StringIO()
    w = csv.writer(texto, lineterminator='\n')
    w.writerow(['ciclo', 'tiempo_ms', 'base_deg', 'hombro_deg', 'fase'])
    w.writerows(filas)
    return cargar_csv(texto.getvalue(), origen='DEMOSTRACION TEORICA · sin captura de Wokwi')


def cargar_csv(texto, ciclo=None, origen='CSV importado · consignas angulares'):
    """Lee la salida serial. Conserva la ultima sesion y el ultimo ciclo elegible.

    Acepta comentarios #, encabezados repetidos y tiempos duplicados. Ante un
    reinicio del simulador, un nuevo encabezado separa las sesiones. Nunca ordena
    tiempos descendentes para ocultar un registro mezclado o corrupto.
    """
    ansi = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
    registros = {}
    encabezado = None
    sesion = -1
    requeridas = {'tiempo_ms', 'base_deg', 'hombro_deg'}
    for numero, linea in enumerate(texto.splitlines(), 1):
        linea = ansi.sub('', linea).strip().lstrip('\ufeff')
        if not linea or linea.startswith('#'):
            continue
        campos = next(csv.reader([linea]))
        campos = [v.strip() for v in campos]
        if requeridas.issubset(campos):
            encabezado = campos
            sesion += 1
            continue
        if encabezado is None:
            # Permite copiar mensajes de arranque anteriores al encabezado.
            continue
        if len(campos) != len(encabezado):
            raise ValueError(f'Linea {numero}: faltan columnas o la fila esta incompleta.')
        fila = dict(zip(encabezado, campos))
        try:
            c = int(fila.get('ciclo', '1'))
            t, b, h = [float(fila[k]) for k in ['tiempo_ms', 'base_deg', 'hombro_deg']]
        except ValueError as exc:
            raise ValueError(f'Linea {numero}: tiempo o angulos no numericos.') from exc
        if not np.isfinite([t, b, h]).all() or t < 0 or not (0 <= b <= 180 and 0 <= h <= 180):
            raise ValueError(f'Linea {numero}: tiempo o angulos fuera de rango.')
        registros.setdefault((sesion, c), []).append((t, b, h, fila.get('fase', 'registro')))
    elegibles = [k for k in registros if ciclo is None or k[1] == ciclo]
    if not elegibles:
        raise ValueError('No hay registros validos. Copiar el encabezado y un ciclo completo.')
    clave = elegibles[-1]
    filas = registros[clave]
    if any(b[0] < a[0] for a, b in zip(filas, filas[1:])):
        raise ValueError('El tiempo retrocede dentro de un ciclo. Revisar la captura.')
    # Varias consignas en el mismo ms: queda vigente la ultima de ese instante.
    unicas = {f[0]: f for f in filas}
    filas = list(unicas.values())
    if len(filas) < 2:
        raise ValueError('Se necesitan al menos dos instantes distintos.')
    valores = np.array([f[:3] for f in filas], dtype=float)
    return {
        't': (valores[:, 0] - valores[0, 0]) / 1000,
        'base': valores[:, 1], 'hombro': valores[:, 2],
        'fase': np.array([f[3] for f in filas]),
        'origen': origen, 'ciclo': clave[1], 'sesion': clave[0] + 1,
    }


def cinematica(base, hombro, altura=ALTURA_CM, offset=DESPLAZAMIENTO_CM, largo=LARGO_CM):
    """Modelo Rz(phi) · Tx(offset) · Tz(altura) · Ry(-beta) · Tx(largo).

    phi = 90 - base (90 grados es el frente +X); beta = hombro, medido
    desde la horizontal. +Y corresponde al lado izquierdo del robot.
    Las longitudes son ilustrativas y el offset es un eslabon fijo.
    """
    phi, beta = np.deg2rad(90 - np.asarray(base)), np.deg2rad(hombro)
    hombro_xyz = np.stack([offset*np.cos(phi), offset*np.sin(phi),
                          np.broadcast_to(altura, np.shape(phi))], axis=-1)
    extremo = hombro_xyz + np.stack([largo*np.cos(beta)*np.cos(phi),
                                    largo*np.cos(beta)*np.sin(phi),
                                    largo*np.sin(beta)], axis=-1)
    return hombro_xyz, extremo


def informe(datos):
    """Verifica las consignas registradas contra la secuencia del TP."""
    q = np.column_stack([datos['base'], datos['hombro']])
    encontrados = []
    cursor = 0
    for punto in PUNTOS:
        indices = np.flatnonzero(np.all(np.isclose(q[cursor:], punto), axis=1))
        if not len(indices):
            break
        cursor += int(indices[0])
        encontrados.append(float(datos['t'][cursor]))
        cursor += 1
    segundo = datos['fase'] == 'tramo_2'
    fijo = bool(np.allclose(datos['hombro'][segundo], 45)) if segundo.any() else None
    return {
        'origen': datos['origen'], 'ciclo': datos['ciclo'],
        'muestras': len(q), 'duracion_s': round(float(datos['t'][-1]), 3),
        'configuraciones_en_orden': len(encontrados) == 4,
        'primera_consigna_objetivo_s': encontrados,
        'hombro_fijo_en_tramo_2': fijo,
        'regresa_a_90_90': bool(np.allclose(q[-1], [90, 90])),
    }


def crear_animacion(datos, fps=25):
    """Devuelve figura y animacion. Mantiene cada consigna hasta la siguiente."""
    if not 1 <= fps <= 60:
        raise ValueError('Elegir una frecuencia entre 1 y 60 cuadros por segundo.')
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'text.color': TINTA, 'axes.labelcolor': TINTA,
                         'xtick.color': TINTA, 'ytick.color': TINTA})
    fig = plt.figure(figsize=(13.6, 7.7), facecolor=FONDO)
    fig.text(.045, .935, 'Brazo robótico', fontsize=25, weight='bold')
    fig.text(.045, .895, 'GRUPO 3   /   Mateo Flores · Federico Soler', fontsize=10, color='#617486')
    fig.text(.955, .933, '2 GRADOS DE LIBERTAD', ha='right', fontsize=11, weight='bold', color=AZUL)
    fig.text(.955, .895, datos['origen'], ha='right', fontsize=9, color='#617486')
    ax = fig.add_axes([.025, .17, .59, .69], projection='3d', facecolor=FONDO)
    ax.view_init(elev=22, azim=40)
    ax.set(xlim=(-7, 24), ylim=(-21, 21), zlim=(0, 29),
           xlabel='X · frente (cm)', ylabel='Y · izquierda (cm)', zlabel='Z (cm)')
    ax.set_box_aspect((31, 42, 29))
    ax.set_xticks([0, 10, 20]); ax.set_yticks([-20, 0, 20]); ax.set_zticks([0, 10, 20])
    ax.tick_params(labelsize=8, pad=0)
    for eje in [ax.xaxis, ax.yaxis, ax.zaxis]:
        eje.pane.fill = False
        eje.pane.set_edgecolor('#DAE1E7')
        eje._axinfo['grid']['color'] = '#E0E6EC'
    a = np.linspace(0, 2*np.pi, 40)
    z = np.array([0, ALTURA_CM - .8])
    xx = 3.4 * np.cos(a)[None, :] * np.ones((2, 1))
    yy = 3.4 * np.sin(a)[None, :] * np.ones((2, 1))
    zz = np.broadcast_to(z[:, None], xx.shape)
    ax.plot_surface(xx, yy, zz, color='#9AAAB6', alpha=.85, linewidth=0, shade=True)
    ax.plot(4.4*np.cos(a), 4.4*np.sin(a), np.full_like(a, ALTURA_CM),
            color='#ABB9C5', ls='--', lw=1)
    hombros, extremos = cinematica(datos['base'], datos['hombro'])
    _, objetivos = cinematica(PUNTOS[:, 0], PUNTOS[:, 1])
    for i, punto in enumerate(objetivos[:3]):
        ax.scatter(*punto, s=24, color='#A7B5C0', depthshade=False)
        ax.text(punto[0], punto[1], punto[2]+1.1, ['P0 / P3', 'P1', 'P2'][i],
                fontsize=9, color='#708596')
    ax.plot(extremos[:, 0], extremos[:, 1], extremos[:, 2], color='#D6E0E7', lw=1.2)
    (rastro,) = ax.plot([], [], [], color=AZUL, alpha=.65, lw=2)
    (soporte,) = ax.plot([], [], [], color=NARANJA, lw=7, solid_capstyle='round')
    (brazo,) = ax.plot([], [], [], color=AZUL, lw=13, solid_capstyle='round')
    (juntas,) = ax.plot([], [], [], 'o', color=NARANJA, ms=10, mec='white', mew=2)
    (punta,) = ax.plot([], [], [], 'o', color=AZUL, ms=8, mec='white', mew=2)
    (proyeccion,) = ax.plot([], [], [], color='#B5C6D1', ls=':', lw=1)
    plataforma = Poly3DCollection([], facecolors=NARANJA, edgecolors='white', alpha=.8)
    ax.add_collection3d(plataforma)

    graf = fig.add_axes([.67, .39, .29, .33], facecolor='white')
    graf.plot(datos['t'], datos['base'], color=AZUL, lw=2, drawstyle='steps-post', label='Base · D9')
    graf.plot(datos['t'], datos['hombro'], color=NARANJA, lw=2, drawstyle='steps-post', label='Hombro · D10')
    graf.set(xlim=(0, max(float(datos['t'][-1]), .1)), ylim=(20, 165), xlabel='Tiempo (s)', ylabel='Consigna (°)')
    graf.set_yticks([30, 45, 90, 150]); graf.grid(alpha=.15)
    graf.spines[['top', 'right']].set_visible(False)
    graf.legend(frameon=False, loc='upper left', fontsize=9)
    cursor = graf.axvline(0, color=TINTA, lw=1.1, ls='--')
    (punto_b,) = graf.plot([], [], 'o', color=AZUL, ms=6)
    (punto_h,) = graf.plot([], [], 'o', color=NARANJA, ms=6)
    estado = fig.text(.67, .81, '', fontsize=15, weight='bold')
    reloj = fig.text(.67, .765, '', fontsize=11, color='#617486')
    angulos = fig.text(.67, .295, '', fontsize=16, weight='bold')
    posicion = fig.text(.67, .25, '', fontsize=10, color='#617486')
    fig.text(.045, .105, 'MODELO CINEMÁTICO', fontsize=9, weight='bold', color=AZUL)
    fig.text(.045, .074, 'Base giratoria + hombro + un eslabón móvil. Dimensiones ilustrativas: h = 8 cm, d = 3 cm, L = 18 cm.', fontsize=9)
    fig.text(.045, .044, 'Se representan consignas de posición; el modelo no calcula cargas, torque ni error de seguimiento.', fontsize=9, color='#617486')
    nombres = {'inicio': 'P0 · Reposo', 'tramo_1': '01 · Hacia P1', 'pausa_1': 'P1 · Pausa',
               'tramo_2': '02 · Giro con hombro fijo', 'pausa_2': 'P2 · Pausa',
               'tramo_3': '03 · Regreso a P0', 'pausa_3': 'P3 · Reposo final', 'fin': 'Secuencia completa'}
    instantes = np.arange(0, datos['t'][-1], 1/fps)
    instantes = np.r_[instantes, datos['t'][-1]]

    def actualizar(t):
        i = min(int(np.searchsorted(datos['t'], t, side='right')-1), len(datos['t'])-1)
        i = max(i, 0)
        s, e = hombros[i], extremos[i]
        phi = np.deg2rad(90-datos['base'][i])
        u = np.array([np.cos(phi), np.sin(phi), 0.])
        v = np.array([-np.sin(phi), np.cos(phi), 0.])
        centro = np.array([0., 0., ALTURA_CM])
        plataforma.set_verts([[centro+du*u+dv*v for du, dv in [(-2,-1.5),(4,-1.5),(4,1.5),(-2,1.5)]]])
        soporte.set_data_3d([0, s[0]], [0, s[1]], [ALTURA_CM, s[2]])
        brazo.set_data_3d([s[0], e[0]], [s[1], e[1]], [s[2], e[2]])
        juntas.set_data_3d([s[0]], [s[1]], [s[2]])
        punta.set_data_3d([e[0]], [e[1]], [e[2]])
        rastro.set_data_3d(extremos[:i+1, 0], extremos[:i+1, 1], extremos[:i+1, 2])
        proyeccion.set_data_3d([e[0], e[0]], [e[1], e[1]], [0, e[2]])
        cursor.set_xdata([t, t])
        punto_b.set_data([t], [datos['base'][i]])
        punto_h.set_data([t], [datos['hombro'][i]])
        estado.set_text(nombres.get(datos['fase'][i], 'Reproducción del registro'))
        reloj.set_text(f't = {t:0.2f} s   /   {datos["t"][-1]:0.2f} s')
        angulos.set_text(f'Base {datos["base"][i]:.0f}°    Hombro {datos["hombro"][i]:.0f}°')
        posicion.set_text(f'Extremo (cm):  x {e[0]:.1f}   y {e[1]:.1f}   z {e[2]:.1f}')
        return brazo, soporte, juntas, punta, rastro, cursor, estado

    actualizar(0)
    anim = FuncAnimation(fig, actualizar, frames=instantes, interval=1000/fps, blit=False, repeat=False)
    # Permite guardar capturas de instantes concretos sin recalcular otra escena.
    anim.actualizar_instante = actualizar
    return fig, anim


def guardar_html(anim, destino, fps=25):
    plt.rcParams['animation.embed_limit'] = 80
    with plt.rc_context({'animation.frame_format': 'jpeg', 'savefig.dpi': 90}):
        reproductor = anim.to_jshtml(fps=fps, default_mode='once')
    # Los cuadros y el JS quedan embebidos. Sustituye los iconos de un CDN
    # por caracteres locales para que el reproductor funcione sin internet.
    reproductor = re.sub(r'<link rel="stylesheet"[^>]*font-awesome[^>]*>', '', reproductor)
    reproductor = reproductor.replace('<i class="fa fa-play fa-flip-horizontal"></i>', '◀')
    iconos = {'fa-fast-backward': '⏮', 'fa-step-backward': '◀', 'fa-backward': '◁',
              'fa-pause': 'Ⅱ', 'fa-play': '▶', 'fa-forward': '▷',
              'fa-step-forward': '▶', 'fa-fast-forward': '⏭',
              'fa-minus': '−', 'fa-plus': '+'}
    for clase, simbolo in iconos.items():
        reproductor = reproductor.replace(f'<i class="fa {clase}"></i>', simbolo)
    pagina = ('<!doctype html><html lang="es"><meta charset="utf-8">'
              '<meta name="viewport" content="width=device-width, initial-scale=1">'
              '<title>Brazo robótico · Grupo 3</title>'
              '<style>body{margin:0;background:#F7F8FA;font-family:Arial,sans-serif}'
              '.animation{margin:0 auto;max-width:1360px}.animation img{max-width:100%;height:auto}'
              'button,input,select{font-size:15px}</style>' + reproductor + '</html>')
    Path(destino).write_text(pagina, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, help='Registro serial con encabezado CSV.')
    parser.add_argument('--ciclo', type=int, help='Ciclo a visualizar; por defecto el ultimo.')
    parser.add_argument('--salida', type=Path, default=Path(__file__).resolve().parent/'salidas')
    parser.add_argument('--gif', action='store_true')
    parser.add_argument('--mp4', action='store_true', help='Requiere ffmpeg en PATH.')
    parser.add_argument('--fps', type=int, default=25)
    args = parser.parse_args()
    if args.csv:
        datos = cargar_csv(args.csv.read_text(encoding='utf-8-sig'), ciclo=args.ciclo,
                           origen='Registro CSV · consignas del programa Arduino')
    else:
        datos = datos_demostracion()
    print(informe(datos))
    args.salida.mkdir(parents=True, exist_ok=True)
    fig, anim = crear_animacion(datos, fps=args.fps)
    guardar_html(anim, args.salida/'brazo_interactivo.html', fps=args.fps)
    # Capturas durante las pausas, si el registro contiene las fases del sketch.
    q = np.column_stack([datos['base'], datos['hombro']])
    inicio = 0
    for n, punto in enumerate(PUNTOS):
        indices = np.flatnonzero(np.all(np.isclose(q[inicio:], punto), axis=1))
        if len(indices):
            fase = ['inicio', 'pausa_1', 'pausa_2', 'fin'][n]
            candidatos = np.flatnonzero((datos['fase'] == fase) &
                                        np.all(np.isclose(q, punto), axis=1))
            i = int(candidatos[0]) if len(candidatos) else inicio + int(indices[0])
            anim.actualizar_instante(datos['t'][i])
            fig.savefig(args.salida/f'P{n}.png', dpi=140, facecolor=fig.get_facecolor())
            inicio = i+1
    if args.gif:
        anim.save(args.salida/'brazo.gif', writer=PillowWriter(fps=args.fps), dpi=85)
    if args.mp4:
        anim.save(args.salida/'brazo.mp4', writer=FFMpegWriter(fps=args.fps, bitrate=1800), dpi=100)
    plt.close(fig)
    print(f'Archivos generados en {args.salida.resolve()}')


if __name__ == '__main__':
    main()
