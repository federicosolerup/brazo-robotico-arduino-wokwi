#include <Servo.h>

// Grupo 3: Mateo Flores y Federico Soler.
// Misma secuencia del TP. Se agrega registro de las consignas por Serial.
Servo servoBase;
Servo servoHombro;
const int PIN_BOTON = 2;
const int PUNTOS[4][2] = {{90, 90}, {30, 45}, {150, 45}, {90, 90}};
const unsigned long T = 1500;
const unsigned long PASO_MS = 20;
unsigned long inicioCiclo;
unsigned int ciclo = 0;
int anguloBase = 90;
int anguloHombro = 90;

void registrar(const char *fase) {
  // Se registran los enteros enviados a Servo.write(), no posiciones medidas.
  Serial.print(ciclo);
  Serial.print(',');
  Serial.print(millis() - inicioCiclo);
  Serial.print(',');
  Serial.print(anguloBase);
  Serial.print(',');
  Serial.print(anguloHombro);
  Serial.print(',');
  Serial.println(fase);
}

void setup() {
  servoBase.attach(9);
  servoHombro.attach(10);
  pinMode(PIN_BOTON, INPUT_PULLUP);
  servoBase.write(anguloBase);
  servoHombro.write(anguloHombro);
  Serial.begin(115200);
  Serial.println("ciclo,tiempo_ms,base_deg,hombro_deg,fase");
}

void moverCubico(int b0, int h0, int bf, int hf,
                 unsigned long duracion, const char *fase) {
  unsigned long inicio = millis();
  float s = 0;
  while (s < 1.0) {
    s = (millis() - inicio) / (float)duracion;
    if (s > 1.0) s = 1.0;
    float k = 3*s*s - 2*s*s*s;
    // Misma conversion a int que realizaba implicitamente Servo.write().
    anguloBase = b0 + (bf - b0) * k;
    anguloHombro = h0 + (hf - h0) * k;
    servoBase.write(anguloBase);
    servoHombro.write(anguloHombro);
    registrar(fase);
    delay(PASO_MS);
  }
}

void pausaConRegistro(unsigned long duracion, const char *fase) {
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
    const char *tramos[] = {"tramo_1", "tramo_2", "tramo_3"};
    const char *pausas[] = {"pausa_1", "pausa_2", "pausa_3"};
    for (int i = 0; i < 3; i++) {
      moverCubico(PUNTOS[i][0], PUNTOS[i][1],
                  PUNTOS[i+1][0], PUNTOS[i+1][1], T, tramos[i]);
      // El original tambien hacia una pausa despues del tercer tramo.
      pausaConRegistro(300, pausas[i]);
    }
    registrar("fin");
    Serial.println("# FIN_CICLO");
    // Mantener el boton presionado no repite la secuencia.
    while (digitalRead(PIN_BOTON) == LOW) delay(10);
  }
}
