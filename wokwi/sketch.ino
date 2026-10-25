#include <Servo.h>

// Grupo 3: Mateo Flores y Federico Soler.
// Brazo planar: hombro + humero + codo + antebrazo. Una articulacion por vez.
Servo servoHombro;
Servo servoCodo;
const int PIN_BOTON = 2;
const unsigned long T = 1500;
const unsigned long PASO_MS = 20;
const int PUNTOS[5][2] = {{30, 30}, {75, 30}, {75, 90}, {30, 90}, {30, 30}};
int anguloHombro = 30;
int anguloCodo = 30;
unsigned int ciclo = 0;
unsigned long inicioCiclo;

void registrar(const char *fase) {
  // Son consignas de posicion, no mediciones de sensores.
  Serial.print(ciclo);
  Serial.print(',');
  Serial.print(millis() - inicioCiclo);
  Serial.print(',');
  Serial.print(anguloHombro);
  Serial.print(',');
  Serial.print(anguloCodo);
  Serial.print(',');
  Serial.println(fase);
}

void setup() {
  pinMode(PIN_BOTON, INPUT_PULLUP);
  // Inicializacion escalonada: el codo sigue desconectado mientras se ubica
  // el hombro. No se ordenan dos desplazamientos iniciales a la vez.
  servoHombro.attach(9);
  servoHombro.write(anguloHombro);
  delay(T);
  servoCodo.attach(10);
  servoCodo.write(anguloCodo);
  delay(T);
  Serial.begin(115200);
  Serial.println("ciclo,tiempo_ms,hombro_deg,codo_deg,fase");
  Serial.println("# LISTO: presionar el pulsador");
}

void moverUnaArticulacion(Servo &motor, int &anguloActual, int destino,
                          const char *fase) {
  // Esta funcion solo escribe en el servo recibido. La otra consigna se mantiene.
  const int origen = anguloActual;
  unsigned long inicio = millis();
  float s = 0;
  while (s < 1.0) {
    s = (millis() - inicio) / (float)T;
    if (s > 1.0) s = 1.0;
    float k = 3*s*s - 2*s*s*s;
    anguloActual = origen + (destino - origen) * k;
    motor.write(anguloActual);
    registrar(fase);
    delay(PASO_MS);
  }
}

void pausaConRegistro(const char *fase) {
  const unsigned long duracion = 300;
  unsigned long inicio = millis();
  while (millis() - inicio < duracion) {
    registrar(fase);
    unsigned long transcurrido = millis() - inicio;
    if (transcurrido < duracion) {
      unsigned long restante = duracion - transcurrido;
      delay(restante < PASO_MS ? restante : PASO_MS);
    }
  }
  registrar(fase);
}

void loop() {
  if (digitalRead(PIN_BOTON) == LOW) {
    ciclo++;
    inicioCiclo = millis();
    registrar("inicio");
    moverUnaArticulacion(servoHombro, anguloHombro, PUNTOS[1][0], "hombro_1");
    pausaConRegistro("pausa_1");
    moverUnaArticulacion(servoCodo, anguloCodo, PUNTOS[2][1], "codo_2");
    pausaConRegistro("pausa_2");
    moverUnaArticulacion(servoHombro, anguloHombro, PUNTOS[3][0], "hombro_3");
    pausaConRegistro("pausa_3");
    moverUnaArticulacion(servoCodo, anguloCodo, PUNTOS[4][1], "codo_4");
    pausaConRegistro("pausa_4");
    registrar("fin");
    Serial.println("# FIN_CICLO");
    while (digitalRead(PIN_BOTON) == LOW) delay(10);
  }
}
