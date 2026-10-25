"""Brazo de hombro y codo con movimientos articulares alternados.

python visualizar_brazo.py --csv datos/captura_wokwi.csv --gif --mp4
Sin --csv se utiliza una demostración teórica identificada como tal.
"""
from pathlib import Path
import argparse
import csv
import io
import json
import re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter, FFMpegWriter
from matplotlib.patches import Circle, Arc, Polygon, FancyBboxPatch

PUNTOS = np.array([[30, 30], [75, 30], [75, 90], [30, 90], [30, 30]])
FASES = ['hombro_1', 'codo_2', 'hombro_3', 'codo_4']
ALTURA_CM = 12.0
HUMERO_CM = 18.0
ANTEBRAZO_CM = 15.0
AZUL = '#1C6DA1'
NARANJA = '#DA7841'
VERDE = '#17846B'
TINTA = '#21394A'
GRIS = '#738795'
FONDO = '#F6F8FA'


def cargar_csv(texto, ciclo=None, origen='CSV importado · consignas de Arduino'):
    """Lee encabezados seriales, reinicios, comentarios y varios ciclos."""
    ansi = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
    requeridas = {'tiempo_ms', 'hombro_deg', 'codo_deg'}
    encabezado, sesion, grupos = None, -1, {}
    for numero, linea in enumerate(texto.splitlines(), 1):
        linea = ansi.sub('', linea).strip().lstrip('\ufeff')
        if not linea or linea.startswith('#'):
            continue
        campos = [v.strip() for v in next(csv.reader([linea]))]
        if requeridas.issubset(campos):
            encabezado, sesion = campos, sesion+1
            continue
        if encabezado is None:
            continue
        if len(campos) != len(encabezado):
            raise ValueError(f'Línea {numero}: fila incompleta.')
        fila = dict(zip(encabezado, campos))
        try:
            c = int(fila.get('ciclo', '1'))
            t, h, e = [float(fila[k]) for k in ['tiempo_ms', 'hombro_deg', 'codo_deg']]
        except ValueError as exc:
            raise ValueError(f'Línea {numero}: valores no numéricos.') from exc
        if not np.isfinite([t, h, e]).all() or t < 0 or not (0 <= h <= 180 and 0 <= e <= 180):
            raise ValueError(f'Línea {numero}: valores fuera de rango.')
        grupos.setdefault((sesion, c), []).append((t, h, e, fila.get('fase', 'registro')))
    elegibles = [k for k in grupos if ciclo is None or k[1] == ciclo]
    if not elegibles:
        raise ValueError('Falta una captura válida: usar tiempo_ms,hombro_deg,codo_deg y un ciclo completo.')
    clave = elegibles[-1]
    filas = grupos[clave]
    if any(b[0] < a[0] for a, b in zip(filas, filas[1:])):
        raise ValueError('El tiempo retrocede dentro de un ciclo. Revisar la captura.')
    # No ocultar un cambio simultáneo ocurrido incluso en dos filas del mismo ms.
    originales = np.array([f[:3] for f in filas], dtype=float)
    cambios = np.abs(np.diff(originales[:, 1:3], axis=0)) > 1e-9
    if np.any(cambios[:, 0] & cambios[:, 1]):
        raise ValueError('La captura contiene cambios simultáneos de hombro y codo.')
    filas = list({f[0]: f for f in filas}.values())
    if len(filas) < 2:
        raise ValueError('Se necesitan al menos dos instantes distintos.')
    v = np.array([f[:3] for f in filas], dtype=float)
    return {'t': (v[:, 0]-v[0, 0])/1000, 'hombro': v[:, 1], 'codo': v[:, 2],
            'fase': np.array([f[3] for f in filas]), 'origen': origen,
            'ciclo': clave[1], 'sesion': clave[0]+1}


def datos_demostracion():
    """Calcula datos de ejemplo; no son una ejecución del simulador."""
    filas, reloj = [], 0
    for i, (a, b) in enumerate(zip(PUNTOS[:-1], PUNTOS[1:])):
        for ms in range(0, 1501, 20):
            s = ms/1500
            q = (a+(b-a)*(3*s*s-2*s*s*s)).astype(int)
            filas.append([1, reloj+ms, *q, FASES[i]])
        reloj += 1520
        for ms in range(0, 301, 20):
            filas.append([1, reloj+ms, *b, f'pausa_{i+1}'])
        reloj += 300
    filas.append([1, reloj, 30, 30, 'fin'])
    texto = io.StringIO()
    w = csv.writer(texto, lineterminator='\n')
    w.writerow(['ciclo', 'tiempo_ms', 'hombro_deg', 'codo_deg', 'fase'])
    w.writerows(filas)
    return cargar_csv(texto.getvalue(), origen='DEMOSTRACIÓN TEÓRICA · sin captura de Wokwi')


def cinematica(hombro, codo, altura=ALTURA_CM, humero=HUMERO_CM, antebrazo=ANTEBRAZO_CM):
    """Cinemática 2R en el plano vertical XZ, con hombro fijo en (0, altura).

    Hombro: ángulo absoluto del húmero respecto de +X.
    Codo: flexión relativa entre húmero prolongado y antebrazo; 0° = extendido.
    """
    q1, q2 = np.broadcast_arrays(np.deg2rad(hombro), np.deg2rad(codo))
    e = np.stack([humero*np.cos(q1), altura+humero*np.sin(q1)], axis=-1)
    w = e+np.stack([antebrazo*np.cos(q1+q2), antebrazo*np.sin(q1+q2)], axis=-1)
    return e, w


def verificar_independencia(datos):
    q = np.column_stack([datos['hombro'], datos['codo']])
    cambios = np.abs(np.diff(q, axis=0)) > 1e-9
    simultaneos = int(np.sum(cambios[:, 0] & cambios[:, 1]))
    tramos = {}
    for i, fase in enumerate(FASES):
        sel = np.flatnonzero(datos['fase'] == fase)
        activo = 0 if fase.startswith('hombro') else 1
        correcto = len(sel) > 1 and bool(np.allclose(q[sel, 1-activo], PUNTOS[i, 1-activo]))
        correcto = correcto and bool(np.allclose(q[sel[0]], PUNTOS[i])) and bool(np.allclose(q[sel[-1]], PUNTOS[i+1])) if len(sel) else False
        tramos[fase] = {'articulacion_activa': 'hombro' if activo == 0 else 'codo',
                        'otra_articulacion_fija_y_extremos_correctos': bool(correcto)}
    cursor, encontrados = 0, []
    for objetivo in PUNTOS:
        indices = np.flatnonzero(np.all(np.isclose(q[cursor:], objetivo), axis=1))
        if not len(indices):
            break
        cursor += int(indices[0]); encontrados.append(float(datos['t'][cursor])); cursor += 1
    return {'origen': datos['origen'], 'muestras': len(q),
            'duracion_s': round(float(datos['t'][-1]), 3),
            'cambios_simultaneos': simultaneos,
            'articulaciones_independientes': simultaneos == 0,
            'configuraciones_en_orden': len(encontrados) == 5,
            'regresa_a_reposo': bool(np.allclose(q[-1], PUNTOS[0])), 'tramos': tramos}


def crear_animacion(datos, fps=20):
    if not 1 <= fps <= 60:
        raise ValueError('FPS debe estar entre 1 y 60.')
    r = verificar_independencia(datos)
    if r['cambios_simultaneos']:
        raise ValueError('Este proyecto requiere una articulación por vez.')
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'text.color': TINTA, 'axes.labelcolor': TINTA,
                         'xtick.color': GRIS, 'ytick.color': GRIS})
    fig = plt.figure(figsize=(14, 8), facecolor=FONDO)
    fig.text(.045, .94, 'Hombro y codo', fontsize=28, weight='bold')
    fig.text(.045, .9, 'GRUPO 3   /   Mateo Flores · Federico Soler', fontsize=10, color=GRIS)
    fig.text(.955, .943, 'UNA ARTICULACIÓN POR VEZ', ha='right', fontsize=12, weight='bold', color=VERDE)
    fig.text(.955, .903, datos['origen'], ha='right', fontsize=9, color=GRIS)
    ax = fig.add_axes([.045, .19, .56, .64], facecolor=FONDO)
    ax.set(xlim=(-22, 35), ylim=(0, 48), xlabel='Alcance horizontal · X (cm)', ylabel='Altura · Z (cm)')
    ax.set_aspect('equal'); ax.set_xticks([-20, 0, 10, 20, 30]); ax.set_yticks([0, 12, 24, 36, 48])
    ax.grid(color='#E2E8ED', lw=.7, zorder=0)
    ax.spines[['top', 'right']].set_visible(False)
    # Torso y cabeza fijos: no hay una plataforma ni giro de base.
    ax.add_patch(Polygon([(-7, 0), (-8, 13), (-5, 17), (-2, 16), (0, 12), (-1.5, 0)],
                         facecolor='#DCE3E9', edgecolor='#B6C3CE', lw=1.3, zorder=2))
    ax.add_patch(Circle((-5.1, 21), 3, facecolor='#E5EBEF', edgecolor='#B6C3CE', lw=1.3))
    ax.text(-7, 4, 'Torso\nfijo', fontsize=9, color=GRIS, ha='center')
    ax.plot([-15, 30], [0, 0], color='#B6C3CE', lw=2)
    e, w = cinematica(datos['hombro'], datos['codo'])
    ax.plot(w[:, 0], w[:, 1], color='#D0DDE5', lw=1.2, zorder=1)
    (rastro,) = ax.plot([], [], color=VERDE, lw=1.6, alpha=.65, zorder=2)
    (humero_borde,) = ax.plot([], [], color='white', lw=24, solid_capstyle='round', zorder=3)
    (humero,) = ax.plot([], [], color=AZUL, lw=18, solid_capstyle='round', zorder=4)
    (ante_borde,) = ax.plot([], [], color='white', lw=22, solid_capstyle='round', zorder=3)
    (antebrazo,) = ax.plot([], [], color=NARANJA, lw=16, solid_capstyle='round', zorder=4)
    aro_h = Circle((0, ALTURA_CM), 1.7, facecolor='white', edgecolor=AZUL, lw=2.5, zorder=6)
    aro_c = Circle((0, 0), 1.6, facecolor='white', edgecolor=NARANJA, lw=2.5, zorder=6)
    ax.add_patch(aro_h); ax.add_patch(aro_c)
    ax.plot([0], [ALTURA_CM], 'o', color=AZUL, ms=5, zorder=7)
    (centro_c,) = ax.plot([], [], 'o', color=NARANJA, ms=5, zorder=7)
    (muneca,) = ax.plot([], [], 'o', ms=10, color=VERDE, mec='white', mew=2, zorder=7)
    arco_h = Arc((0, ALTURA_CM), 11, 11, theta1=0, theta2=30, color=AZUL, lw=1.5)
    arco_c = Arc((0, 0), 9, 9, theta1=30, theta2=60, color=NARANJA, lw=1.5)
    ax.add_patch(arco_h); ax.add_patch(arco_c)
    (referencia,) = ax.plot([], [], color=NARANJA, ls=':', lw=1, zorder=1)
    h_label = ax.annotate('HÚMERO', xy=(0, 0), xytext=(-18, 31), fontsize=10,
                          color=AZUL, weight='bold', zorder=9,
                          arrowprops={'arrowstyle': '-', 'color': AZUL, 'lw': .9})
    a_label = ax.annotate('ANTEBRAZO', xy=(0, 0), xytext=(20, 45), fontsize=10,
                          color=NARANJA, weight='bold', ha='center', zorder=9,
                          arrowprops={'arrowstyle': '-', 'color': NARANJA, 'lw': .9})
    c_label = ax.text(0, 0, 'Codo · D10', fontsize=9, color=TINTA)
    w_label = ax.text(0, 0, 'Muñeca\nEfector final', fontsize=9, color=VERDE)
    ax.annotate('Hombro · D9', (0, ALTURA_CM), (-17, 9), fontsize=9, color=TINTA,
                arrowprops={'arrowstyle': '-', 'color': GRIS, 'lw': .8})
    graf = fig.add_axes([.66, .415, .30, .285], facecolor='white')
    graf.plot(datos['t'], datos['hombro'], color=AZUL, lw=2.3, drawstyle='steps-post', label='Hombro · D9')
    graf.plot(datos['t'], datos['codo'], color=NARANJA, lw=2.3, drawstyle='steps-post', label='Codo · D10')
    graf.set(xlim=(0, max(float(datos['t'][-1]), .1)), ylim=(20, 105),
             xlabel='Tiempo (s)', ylabel='Ángulo articular (°)')
    graf.set_yticks([30, 60, 75, 90]); graf.grid(alpha=.13)
    graf.spines[['top', 'right']].set_visible(False)
    graf.legend(frameon=False, loc='upper left', fontsize=9)
    cursor = graf.axvline(0, color=TINTA, ls='--', lw=1)
    (p_h,) = graf.plot([], [], 'o', ms=6, color=AZUL)
    (p_c,) = graf.plot([], [], 'o', ms=6, color=NARANJA)
    estado = fig.text(.66, .82, '', fontsize=16, weight='bold')
    detalle = fig.text(.66, .78, '', fontsize=10, color=GRIS)
    reloj = fig.text(.66, .735, '', fontsize=10, color=GRIS)
    angulos = fig.text(.66, .32, '', fontsize=17, weight='bold')
    fig.add_artist(FancyBboxPatch((.655, .215), .305, .06, transform=fig.transFigure,
                                 boxstyle='round,pad=0.012', facecolor='#E6F2ED', edgecolor='none'))
    fig.text(.67, .238, 'CAMBIOS SIMULTÁNEOS: 0', color=VERDE, fontsize=11, weight='bold')
    fig.text(.045, .12, 'HOMBRO → HÚMERO → CODO → ANTEBRAZO → MUÑECA', color=TINTA, fontsize=10, weight='bold')
    fig.text(.045, .079, 'Vista lateral · plano vertical. El codo se mide respecto del húmero; 0° significa brazo extendido.', color=GRIS, fontsize=9)
    fig.text(.045, .047, 'Dimensiones ilustrativas: húmero 18 cm y antebrazo 15 cm. La muñeca es el efector, sin otro actuador.', color=GRIS, fontsize=9)
    instantes = np.r_[np.arange(0, datos['t'][-1], 1/fps), datos['t'][-1]]

    def actualizar(t):
        i = max(0, min(int(np.searchsorted(datos['t'], t, side='right')-1), len(datos['t'])-1))
        elbow, wrist = e[i], w[i]
        q1, q2 = datos['hombro'][i], datos['codo'][i]
        fase = datos['fase'][i]
        h_activo, c_activo = fase.startswith('hombro_'), fase.startswith('codo_')
        for line in [humero_borde, humero]: line.set_data([0, elbow[0]], [ALTURA_CM, elbow[1]])
        for line in [ante_borde, antebrazo]: line.set_data([elbow[0], wrist[0]], [elbow[1], wrist[1]])
        aro_c.center = elbow
        aro_h.set_linewidth(4 if h_activo else 2)
        aro_c.set_linewidth(4 if c_activo else 2)
        centro_c.set_data([elbow[0]], [elbow[1]])
        muneca.set_data([wrist[0]], [wrist[1]])
        rastro.set_data(w[:i+1, 0], w[:i+1, 1])
        arco_h.theta2 = q1
        arco_c.center = elbow; arco_c.theta1 = q1; arco_c.theta2 = q1+q2
        u = np.array([np.cos(np.deg2rad(q1)), np.sin(np.deg2rad(q1))])
        referencia.set_data([elbow[0], elbow[0]+5*u[0]], [elbow[1], elbow[1]+5*u[1]])
        h_label.xy = (elbow[0]/2, (ALTURA_CM+elbow[1])/2)
        a_label.xy = ((elbow[0]+wrist[0])/2, (elbow[1]+wrist[1])/2)
        c_label.set_position((elbow[0]+2, elbow[1]-2))
        w_label.set_position((wrist[0]+2, wrist[1]-.5))
        cursor.set_xdata([t, t]); p_h.set_data([t], [q1]); p_c.set_data([t], [q2])
        if h_activo:
            estado.set_text('Mueve el hombro'); estado.set_color(AZUL)
            detalle.set_text(f'Codo fijo en {q2:.0f}° · acompaña al húmero')
        elif c_activo:
            estado.set_text('Mueve el codo'); estado.set_color(NARANJA)
            detalle.set_text(f'Hombro fijo en {q1:.0f}° · húmero quieto')
        else:
            estado.set_text('Reposo final' if fase == 'fin' else 'Pausa · ambas articulaciones fijas')
            estado.set_color(TINTA); detalle.set_text('Se mantienen las dos consignas angulares')
        reloj.set_text(f't = {t:.2f} s   /   {datos["t"][-1]:.2f} s')
        angulos.set_text(f'Hombro {q1:.0f}°    Codo {q2:.0f}°')
        return humero, antebrazo, muneca, cursor, estado

    actualizar(0)
    anim = FuncAnimation(fig, actualizar, frames=instantes, interval=1000/fps, blit=False, repeat=False)
    anim.actualizar_instante = actualizar
    return fig, anim


def guardar_html(anim, destino, fps=20):
    with plt.rc_context({'animation.frame_format': 'jpeg', 'savefig.dpi': 90, 'animation.embed_limit': 80}):
        reproductor = anim.to_jshtml(fps=fps, default_mode='once')
    reproductor = re.sub(r'<link rel="stylesheet"[^>]*font-awesome[^>]*>', '', reproductor)
    reproductor = reproductor.replace('<i class="fa fa-play fa-flip-horizontal"></i>', '◀')
    iconos = {'fa-fast-backward': '⏮', 'fa-step-backward': '◀', 'fa-backward': '◁',
              'fa-pause': 'Ⅱ', 'fa-play': '▶', 'fa-step-forward': '▶', 'fa-fast-forward': '⏭',
              'fa-minus': '−', 'fa-plus': '+'}
    for k, v in iconos.items(): reproductor = reproductor.replace(f'<i class="fa {k}"></i>', v)
    pagina = ('<!doctype html><html lang="es"><meta charset="utf-8">'
              '<meta name="viewport" content="width=device-width, initial-scale=1">'
              '<title>Hombro y codo · movimientos independientes</title>'
              '<style>body{margin:0;background:#F6F8FA;font-family:Arial,sans-serif}'
              '.animation{margin:auto;max-width:1400px}.animation img{max-width:100%;height:auto}'
              'button,input,select{font-size:15px}</style>'+reproductor+'</html>')
    Path(destino).write_text(pagina, encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--csv', type=Path)
    p.add_argument('--ciclo', type=int)
    p.add_argument('--salida', type=Path, default=Path(__file__).resolve().parent/'salidas')
    p.add_argument('--gif', action='store_true'); p.add_argument('--mp4', action='store_true')
    p.add_argument('--fps', type=int, default=20)
    a = p.parse_args()
    d = cargar_csv(a.csv.read_text(encoding='utf-8-sig'), ciclo=a.ciclo,
                   origen='Captura Wokwi · hombro y codo') if a.csv else datos_demostracion()
    r = verificar_independencia(d)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    a.salida.mkdir(exist_ok=True, parents=True)
    (a.salida.parent/'datos').mkdir(exist_ok=True)
    (a.salida.parent/'datos/verificacion.json').write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding='utf-8')
    fig, anim = crear_animacion(d, fps=a.fps)
    guardar_html(anim, a.salida/'brazo_interactivo.html', fps=a.fps)
    for i, fase in enumerate(['inicio', 'pausa_1', 'pausa_2', 'pausa_3', 'fin']):
        indices = np.flatnonzero(d['fase'] == fase)
        if len(indices):
            anim.actualizar_instante(d['t'][indices[0]])
            fig.savefig(a.salida/f'P{i}.png', dpi=125, facecolor=fig.get_facecolor())
    anim.actualizar_instante(2.6)
    fig.savefig(a.salida/'vista_previa.png', dpi=100, facecolor=fig.get_facecolor())
    if a.gif: anim.save(a.salida/'brazo.gif', writer=PillowWriter(fps=a.fps), dpi=85)
    if a.mp4: anim.save(a.salida/'brazo.mp4', writer=FFMpegWriter(fps=a.fps, bitrate=1800), dpi=100)
    plt.close(fig)


if __name__ == '__main__':
    main()
