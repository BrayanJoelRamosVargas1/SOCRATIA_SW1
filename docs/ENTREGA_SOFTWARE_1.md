# DOSSIER DE ENTREGA ACADÉMICA — SOFTWARE 1
## SOCRATIA: SIMULADOR DE DEFENSA DE GRADO CON IA Y JURADOS VIRTUALES

---

### FICHA TÉCNICA DEL PROYECTO

| Campo | Detalle |
|:---|:---|
| **Proyecto** | SOCRATIA — Academic Defense Simulator |
| **Asignatura** | Software 1 (Ingeniería de Software / Sistemas) |
| **Versión** | 1.0.0 (Cierre Oficial de Línea Base) |
| **Alcance Funcional** | 17 Casos de Uso Oficiales (CU01–CU17) — 100% Implementados |
| **Arquitectura** | Monolito Modular Limpio (Clean Architecture / Hexagonal Ports & Adapters) |
| **Backend** | Python 3.13, FastAPI, SQLAlchemy 2.0, Pydantic V2, Instructor |
| **Frontend** | Next.js 16, React 19, TypeScript, TailwindCSS, MediaPipe Tasks Vision |
| **Persistencia** | PostgreSQL 16 con extensión `pgvector` (Embeddings 768 dimensiones) |
| **Infraestructura** | Contenedores Docker (`compose.yaml`), Red local aislada |
| **Cobertura de Pruebas** | 226 Tests Deterministas Unitarios/Integración (100% PASS) + Suite E2E Físico |

---

## 1. DESCRIPCIÓN Y OBJETIVO DEL SISTEMA

### 1.1 El Problema
La defensa de grado (tesis, proyecto de grado o memoria académica) representa uno de los momentos de mayor tensión y evaluación crítica para estudiantes universitarios. Tradicionalmente, los estudiantes carecen de instancias previas para ensayar sus respuestas orales ante jurados hostiles, críticos o metodológicos con preguntas imprevistas basadas en su propio texto académico.

### 1.2 La Solución Socratia
**Socratia** es una plataforma web integral que permite al estudiante subir su documento académico (PDF o DOCX), procesarlo mediante un pipeline de **RAG (Retrieval-Augmented Generation)** con embeddings densos, y participar en una **defensa oral simulada en tiempo real** frente a jurados virtuales que emulan personalidades académicas reales (Jurado Metodológico, Jurado Técnico, Jurado Crítico). 

El sistema evalúa de forma determinista y auditable el desempeño del estudiante, proyectando puntajes en contenido, coherencia argumental y aspectos comunicativos mediante reportes estructurados imprimibles.

---

## 2. REQUISITOS Y ALCANCE OFICIAL DEL SISTEMA

### 2.1 Requisitos Funcionales (Mapeo a CU01–CU17)
1. **RF01 (CU01)**: Autenticación segura mediante cookies HttpOnly con rotación de tokens, control de sesiones concurrentes y bloqueo temporal tras intentos fallidos.
2. **RF02 (CU02)**: Autogestión de perfil de usuario restringida a campos de identidad, prohibiendo alteración de roles o suscripciones.
3. **RF03 (CU03)**: Selección, consulta y cancelación de suscripciones propias por parte del estudiante.
4. **RF04 (CU04)**: Gestión administrativa de usuarios con filtrado por rol/estado, activación/desactivación y salvaguarda del último administrador.
5. **RF05 (CU05)**: Gestión administrativa del catálogo de planes y auditoría transaccional de suscripciones con garantía de una sola suscripción activa por usuario.
6. **RF06 (CU06)**: Carga multipart, validación MIME, almacenamiento y eliminación segura de documentos académicos.
7. **RF07 (CU07)**: Pipeline RAG: extracción de texto, normalización, segmentación (chunking), generación de vectores densos y persistencia en `pgvector`.
8. **RF08 (CU08)**: Generación automática de bancos de preguntas calibradas por dificultad y diapositivas de preparación estructuradas.
9. **RF09 (CU09)**: Configuración en caliente de hiperparámetros de IA (top_k de RAG, temperatura, modelos de jurado y evaluador) con versión incremental y cero reinicios.
10. **RF10 (CU10)**: Configuración de la simulación, selección de jurado y calibración previa de sensores (micrófono y cámara).
11. **RF11 (CU11)**: Control del ciclo de vida de la sesión (DRAFT → READY → ACTIVE → COMPLETED), gestión estricta del tiempo y recuperación ante reconexión.
12. **RF12 (CU12)**: Interacción por voz y WebSocket con el jurado virtual, detección de actividad de voz (VAD) y preguntas de profundización (follow-ups).
13. **RF13 (CU13)**: Gestión administrativa completa de perfiles de jurado y restricción de eliminación para perfiles con historial.
14. **RF14 (CU14)**: Evaluación estructurada del estudiante mediante LLM restringido a evidencia (`Instructor`), calculando puntaje general y desgloses por pregunta.
15. **RF15 (CU15)**: Proyección determinista del reporte de evaluación con clasificación cualitativa y exportación/impresión en formato PDF.
16. **RF16 (CU16)**: Consulta del historial cronológico de simulaciones con métricas evolutivas y cálculo determinista de deltas de puntaje.
17. **RF17 (CU17)**: Tablero de supervisión administrativo con métricas globales agregadas y telemetría de plataforma sin fuga de secretos.

### 2.2 Requisitos No Funcionales Críticos
- **Seguridad y Privacidad**: Ningún byte de audio crudo se almacena en disco o base de datos. Los transcripts se anonimizan y aíslan por tenant.
- **Invariancia Transaccional**: No es posible que un usuario tenga dos suscripciones en estado `ACTIVE` simultáneas, protegido a nivel de motor de base de datos mediante un índice único parcial.
- **Resiliencia de Inferencia**: Cadena de fallbacks ante fallos de APIs externas (Gemini → Groq / Local).
- **Auditabilidad**: Cada evaluación almacena el modelo, la versión de la rúbrica y la evidencia textual extraída del documento que respaldó la calificación.

---

## 3. MATRIZ DE TRAZABILIDAD COMPLETA (CU01–CU17)

| CU | Caso de Uso | Actor | Endpoint / Canal | Vista Frontend | Persistencia | Seguridad / RBAC | Estado | Evidencia Visual |
|:---:|:---|:---:|:---|:---|:---|:---|:---:|:---|
| **CU01** | Gestionar autenticación | Todos | `POST /api/v1/auth/login`<br>`POST /api/v1/auth/register` | `/login`<br>`/register` | `users`, `user_sessions`, `login_attempts` | Cookies HttpOnly, rate limiting | **PASS** | `CU01_01_login_page.png`<br>`CU01_02_register_page.png` |
| **CU02** | Gestionar perfil | Estudiante | `GET /api/v1/profile`<br>`PATCH /api/v1/profile` | `/profile` | `users` (campos de identidad) | Estricto `extra="forbid"`, RBAC propio | **PASS** | `CU02_student_profile.png` |
| **CU03** | Gestionar suscripción propia | Estudiante | `GET /api/v1/subscription`<br>`POST /api/v1/subscription` | `/subscription` | `subscriptions` | Validación de plan activo, 1 activa máx | **PASS** | `CU03_student_subscription.png` |
| **CU04** | Gestionar usuarios | Administrador | `GET /api/v1/admin/users`<br>`PATCH /api/v1/admin/users/{id}` | `/admin/users` | `users`, `roles`, `user_roles` | Solo rol `Administrator`, protección último admin | **PASS** | `CU04_admin_users.png` |
| **CU05** | Gestionar planes y suscripciones | Administrador | `GET/POST /api/v1/admin/plans`<br>`GET/POST /api/v1/admin/subscriptions` | `/admin/plans`<br>`/admin/subscriptions` | `plans`, `subscriptions` | Solo rol `Administrator`, índice parcial DB | **PASS** | `CU05_01_admin_plans.png`<br>`CU05_02_admin_subscriptions.png` |
| **CU06** | Gestionar documentos | Estudiante | `GET/POST /api/v1/documents`<br>`DELETE /api/v1/documents/{id}` | `/dashboard` | `documents`, local file storage | Tenant isolation por `user_id` | **PASS** | `CU06_CU07_CU08_student_dashboard.png` |
| **CU07** | Procesar documento | Sistema / Estudiante | `POST /api/v1/documents/{id}/process` | `/dashboard` | `document_chunks`, `embeddings` (pgvector) | Ownership validado, pipeline síncrono | **PASS** | `CU06_CU07_CU08_student_dashboard.png` |
| **CU08** | Generar material de preparación | Estudiante | `POST /questions/generate`<br>`POST /presentation/generate` | `/dashboard` | `question_banks`, `questions`, `presentations` | Verificación de documento PROCESSED | **PASS** | `CU06_CU07_CU08_student_dashboard.png` |
| **CU09** | Configurar parámetros IA | Administrador | `GET /api/v1/admin/ai-settings`<br>`PATCH /api/v1/admin/ai-settings` | `/admin/ai-settings` | `ai_settings` (singleton) | Solo `Administrator`, cero secretos expuestos | **PASS** | `CU09_admin_ai_settings.png` |
| **CU10** | Configurar simulación | Estudiante | `POST /api/v1/simulations`<br>`PUT /simulations/{id}/calibration` | `/simulations/new` | `simulations` | Validación de banco READY y sensores | **PASS** | `CU11_CU12_simulation_session.png` |
| **CU11** | Gestionar sesión simulación | Estudiante | `POST /simulations/{id}/start`<br>`GET /simulations/{id}` | `/simulations/{id}` | `simulations` (estados y timestamps) | Máquina de estados finita estricta | **PASS** | `CU11_CU12_simulation_session.png` |
| **CU12** | Interactuar con jurado virtual | Estudiante | `WS /api/v1/ws/simulations/{id}` | `/simulations/{id}` | `simulation_turns`, `transcripts` | Origin header check, cookie session | **PASS** | `CU11_CU12_simulation_session.png` |
| **CU13** | Administrar perfiles de jurado | Administrador | `GET/POST /api/v1/admin/jury-profiles`<br>`PATCH /admin/jury-profiles/{id}` | `/admin/jury-profiles` | `jury_profiles` | Solo `Administrator`, bloqueo de delete en uso | **PASS** | `CU13_admin_jury_profiles.png` |
| **CU14** | Evaluar desempeño estudiante | Sistema / Estudiante | `POST /simulations/{id}/evaluate` | `/simulations/{id}` | `evaluations`, `turn_evaluations` | Simulación COMPLETED requerida, inmutable | **PASS** | `CU15_student_performance_report.png` |
| **CU15** | Gestionar reporte desempeño | Estudiante | `GET /simulations/{id}/report` | `/simulations/{id}/report` | Vista proyectada de `evaluations` | Tenant isolation, exportación PDF legal | **PASS** | `CU15_student_performance_report.png`<br>`reporte_defensa_simulacion.pdf` |
| **CU16** | Consultar historial desempeño | Estudiante | `GET /api/v1/performance-history` | `/history` | `simulations` + `evaluations` | Tenant isolation, orden cronológico descendente | **PASS** | `CU16_student_history.png` |
| **CU17** | Supervisar plataforma | Administrador | `GET /api/v1/admin/dashboard` | `/admin/dashboard` | Agregaciones SQL deterministas | Solo `Administrator`, telemetría segura | **PASS** | `CU17_admin_dashboard.png` |

---

## 4. ARQUITECTURA DE SOFTWARE (MONOLITO MODULAR)

Socratia implementa un **Monolito Modular Limpio**. Cada dominio funcional está desacoplado dentro de su propio paquete en `backend/app/modules/`, compartiendo únicamente contratos e infraestructura en `backend/app/core/` e integraciones en `backend/app/integrations/`.

```
backend/
├── app/
│   ├── api/v1/                # Enrutador maestro unificado
│   ├── core/                  # Base de datos, configuración, excepciones y logging
│   ├── integrations/          # Puertos y adaptadores externos
│   │   ├── embeddings/        # Gemini, Cohere, Local E5
│   │   ├── evaluation/        # Instructor Pydantic evaluator
│   │   ├── llm/               # Jury LLM Router (Gemini / Groq)
│   │   ├── stt/               # Groq Whisper STT Router
│   │   ├── tts/               # ElevenLabs TTS con fallback
│   │   └── vector_db/         # Adaptador PostgreSQL pgvector
│   └── modules/               # Módulos de dominio de negocio
│       ├── p1_gestion_identidad_seguridad/     # CU01, CU02
│       ├── p2_gestion_documentos_preparacion/  # CU06, CU07, CU08
│       ├── p3_gestion_simulacion/              # CU10, CU11, CU12, CU13
│       ├── p4_gestion_evaluacion_resultados/   # CU14, CU15, CU16
│       ├── p5_gestion_saas/                    # CU03, CU05
│       └── p6_gestion_administracion/          # CU04, CU09, CU17
```

### Patrones de Diseño Aplicados
- **Repository Pattern**: Aislamiento entre la capa de negocio y la persistencia SQLAlchemy.
- **Strategy & Chain of Responsibility (Fallbacks)**:
  - *Embeddings*: Gemini Embedding → Cohere → Local E5 768.
  - *Jury LLM*: Google Gemini Flash → Groq LLaMA 3.3.
  - *TTS*: ElevenLabs Cloud → Web Speech API (Browser Fallback).
- **Outbox Pattern**: Durabilidad en sincronización vectorial y borrado de documentos.
- **Schema Strict Validation**: Uso de `extra="forbid"` en Pydantic V2 para neutralizar inyecciones de parámetros no autorizados.

---

## 5. MODELO DE DATOS Y PERSISTENCIA (POSTGRESQL & PGVECTOR)

### 5.1 Tablas Principales
- **`users`**: Identidad (`id`, `email`, `password_hash`, `full_name`, `is_active`, `auth_version`).
- **`roles` & `user_roles`**: RBAC relacional con roles `Student` y `Administrator`.
- **`documents`**: Documentos académicos asociados a estudiantes con huella criptográfica SHA-256.
- **`document_chunks`**: Fragmentos de texto indexados con vector dense de 768 dimensiones (`vector(768)`).
- **`question_banks` & `questions`**: Bancos de 12 preguntas por documento con puntos de respuesta esperados.
- **`jury_profiles`**: Perfiles de jurado con prompts de personalidad (`CRITICAL`, `METHODOLOGICAL`, `TECHNICAL`).
- **`simulations`**: Instancia de defensa con máquina de estados (`DRAFT`, `READY`, `ACTIVE`, `COMPLETED`, `ABORTED`).
- **`simulation_turns`**: Transcripción y eventos de locución asociados a cada turno del estudiante y jurado.
- **`evaluations` & `turn_evaluations`**: Evaluación inmutable generada con `Instructor` (calificaciones 0–100, fortalezas, debilidades y contradicciones).
- **`plans` & `subscriptions`**: Modelo SaaS de monetización.
- **`ai_settings`**: Tabla singleton con los hiperparámetros activos de inferencia.

### 5.2 Garantía Transaccional de Suscripción Única
Para evitar condiciones de carrera donde dos peticiones HTTP simultáneas pudieran asignar dos suscripciones activas al mismo usuario, se implementó una restricción a nivel de base de datos en PostgreSQL:
```sql
CREATE UNIQUE INDEX uq_active_user_subscription 
ON subscriptions (user_id) 
WHERE status = 'ACTIVE';
```
Esto garantiza que la base de datos rechace a nivel transaccional (`IntegrityError`) cualquier intento de duplicidad concurrente.

---

## 6. ESPECIFICACIÓN Y PROYECTO ENTERPRISE ARCHITECT (UML)

> **Modelo Oficial Generado**: Se generó el archivo de proyecto oficial de Enterprise Architect en formato nativo:
> 👉 [`docs/uml/SOCRATIA_Model.eapx`](file:///c:/Users/ElCremosasWee/SOCRATIA_SW1/docs/uml/SOCRATIA_Model.eapx) (2.5 MB).
> Dicho proyecto fue construido de forma automatizada mediante la interfaz COM de Sparx Systems Enterprise Architect v15 instalada en el sistema, organizando los 4 paquetes de arquitectura, elementos, clases, casos de uso y diagramas UML.

### Paquete 1: Modelo de Casos de Uso (Use Case Model)
- **Actores**:
  - `Actor::Estudiante` (Generalización de Usuario Autenticado).
  - `Actor::Administrador` (Usuario con privilegios de gestión y supervisión).
  - `Actor::JuradoVirtual` (Actor del sistema / IA).
- **Diagramas de Casos de Uso recomendados en EA**:
  1. *UC_Diagram_General*: Visión global de los 17 casos de uso y sus límites de sistema.
  2. *UC_Diagram_Identidad_SaaS*: CU01, CU02, CU03, CU04, CU05.
  3. *UC_Diagram_Documentos_RAG*: CU06, CU07, CU08, CU09.
  4. *UC_Diagram_Simulacion_Voz*: CU10, CU11, CU12, CU13.
  5. *UC_Diagram_Evaluacion_Reportes*: CU14, CU15, CU16, CU17.

### Paquete 2: Modelo de Clases de Dominio (Domain Class Model)
- **Clases Principales**:
  - `User` (1) ── (0..*) `Document`
  - `Document` (1) ── (1..*) `DocumentChunk`
  - `Document` (1) ── (1) `QuestionBank` (1) ── (12) `Question`
  - `User` (1) ── (0..*) `Simulation` (0..*) ── (1) `JuryProfile`
  - `Simulation` (1) ── (0..*) `SimulationTurn`
  - `Simulation` (1) ── (0..1) `Evaluation` (1) ── (0..*) `TurnEvaluation`
  - `User` (1) ── (0..*) `Subscription` (0..*) ── (1) `Plan`

### Paquete 3: Modelo de Componentes (Component Architecture Model)
- **Componentes Lógicos**:
  - `Component::Frontend_NextJS` (Presentación React 19).
  - `Component::API_Gateway_FastAPI` (Rutas y Policies).
  - `Component::SessionEngine_WebSocket` (Orquestador de turnos).
  - `Component::RAG_Embedding_Coordinator` (Indexador vectorial).
  - `Component::Jury_Voice_Pipeline` (STT, LLM, TTS).
  - `Component::Instructor_Evaluator` (Evaluador Pydantic).
  - `Component::PostgreSQL_Database` (Persistencia relacional + pgvector).

### Paquete 4: Diagrama de Secuencia (Sequence Diagram — Live Voice Turn)
- **Objetos participantes**:
  - `:Estudiante_Browser`
  - `:WebSocket_Handler`
  - `:Groq_STT_Provider`
  - `:Jury_Router_LLM`
  - `:ElevenLabs_TTS_Provider`
  - `:Simulation_Repository`
- **Flujo de Mensajes**:
  1. `send(voice.utterance.start, mime_type)`
  2. `send_bytes(audio_chunk)`
  3. `send(voice.utterance.end)`
  4. `transcribe(audio_bytes)` → `transcript_text`
  5. `evaluate_and_reply(transcript_text, context_chunks)` → `jury_response_text, action`
  6. `synthesize(jury_response_text)` → `tts_audio_bytes`
  7. `push_bytes(tts_audio_bytes)` a navegador
  8. `persist_turn(student_transcript, jury_text, timestamps)`

---

## 7. EVIDENCIAS VISUALES Y FÍSICAS RECOPILADAS

Todas las capturas de pantalla fueron obtenidas de forma automatizada mediante **Microsoft Edge** en modo de alta fidelidad (1440x900) y se encuentran almacenadas en el directorio `docs/screenshots/`:

| Archivo | Caso de Uso | Descripción Visual |
|:---|:---:|:---|
| [`CU01_01_login_page.png`](file:///c:/Users/ElCremosasWee/SOCRATIA_SW1/docs/screenshots/CU01_01_login_page.png) | CU01 | Formulario de autenticación con campos validados y cookies seguras. |
| [`CU01_02_register_page.png`](file:///c:/Users/ElCremosasWee/SOCRATIA_SW1/docs/screenshots/CU01_02_register_page.png) | CU01 | Registro de estudiantes con contraseña segura y validación de correo. |
| [`CU02_student_profile.png`](file:///c:/Users/ElCremosasWee/SOCRATIA_SW1/docs/screenshots/CU02_student_profile.png) | CU02 | Vista de autogestión de perfil con campos permitidos y roles bloqueados. |
| [`CU03_student_subscription.png`](file:///c:/Users/ElCremosasWee/SOCRATIA_SW1/docs/screenshots/CU03_student_subscription.png) | CU03 | Catálogo de planes para el estudiante y estado de suscripción activa. |
| [`CU04_admin_users.png`](file:///c:/Users/ElCremosasWee/SOCRATIA_SW1/docs/screenshots/CU04_admin_users.png) | CU04 | Tabla administrativa con listado de usuarios, roles y toggle activo/inactivo. |
| [`CU05_01_admin_plans.png`](file:///c:/Users/ElCremosasWee/SOCRATIA_SW1/docs/screenshots/CU05_01_admin_plans.png) | CU05 | Gestión de precios, límites y activación de planes de suscripción. |
| [`CU05_02_admin_subscriptions.png`](file:///c:/Users/ElCremosasWee/SOCRATIA_SW1/docs/screenshots/CU05_02_admin_subscriptions.png) | CU05 | Listado y auditoría de suscripciones vigentes de todos los usuarios. |
| [`CU06_CU07_CU08_student_dashboard.png`](file:///c:/Users/ElCremosasWee/SOCRATIA_SW1/docs/screenshots/CU06_CU07_CU08_student_dashboard.png) | CU06-CU08 | Panel de documentos académicos, estado de RAG y preparación. |
| [`CU09_admin_ai_settings.png`](file:///c:/Users/ElCremosasWee/SOCRATIA_SW1/docs/screenshots/CU09_admin_ai_settings.png) | CU09 | Configuración dinámica de proveedores de IA, temperatura y top_k de RAG. |
| [`CU11_CU12_simulation_session.png`](file:///c:/Users/ElCremosasWee/SOCRATIA_SW1/docs/screenshots/CU11_CU12_simulation_session.png) | CU11-CU12 | Sala de simulación en vivo, jurado virtual, transcripción y cronómetro. |
| [`CU13_admin_jury_profiles.png`](file:///c:/Users/ElCremosasWee/SOCRATIA_SW1/docs/screenshots/CU13_admin_jury_profiles.png) | CU13 | Administración de personalidades académicas de los jurados virtuales. |
| [`CU15_student_performance_report.png`](file:///c:/Users/ElCremosasWee/SOCRATIA_SW1/docs/screenshots/CU15_student_performance_report.png) | CU15 | Reporte de desempeño detallado por turnos, fortalezas y puntaje global. |
| [`CU16_student_history.png`](file:///c:/Users/ElCremosasWee/SOCRATIA_SW1/docs/screenshots/CU16_student_history.png) | CU16 | Historial cronológico con cálculo de deltas y evolución en el tiempo. |
| [`CU17_admin_dashboard.png`](file:///c:/Users/ElCremosasWee/SOCRATIA_SW1/docs/screenshots/CU17_admin_dashboard.png) | CU17 | Tablero administrativo de supervisión de plataforma y métricas clave. |

### 7.1 Evidencia Física de Exportación PDF
- **Archivo generado**: [`docs/evidencias/reporte_defensa_simulacion.pdf`](file:///c:/Users/ElCremosasWee/SOCRATIA_SW1/docs/evidencias/reporte_defensa_simulacion.pdf)
- **Tamaño**: 165.391 bytes (165 KB).
- **Formato**: PDF 1.4 binario válido, estructurado en hojas A4 con tablas vectoriales de puntajes y márgenes normalizados.

---

## 8. CONFIRMACIÓN Y ALCANCE DE LA PRUEBA DE VOZ

### 8.1 Resultados de la Prueba Física Automatizada (`test_p3c_integration_real.py`)
- **Estado**: `1 passed` en 8,40 segundos.
- **Componentes verificados en la nube con credenciales reales**:
  1. *Groq Audio API*: Invocación a `whisper-large-v3` procesando audio fixture en español.
  2. *Google Gemini API*: Recepción del transcript y emisión de respuesta coherente con el rol del jurado.
  3. *ElevenLabs Voice API*: Conversión del texto del jurado a audio streaming con `voice_id` oficial, verificando recepción de bytes binarios mayores a cero (`audio_bytes > 0`) y emisión del evento `tts.completed` sin fallback a navegador.
  4. *Defensa de Cierre*: Comprobación de que una vez respondidas las preguntas (12/12), el sistema emite el evento de error controlado `SESSION_QUESTIONS_EXHAUSTED` y no genera una pregunta 13.

### 8.2 Distinción Técnica con la Prueba de Micrófono Humano
- **Prueba Física Automatizada**: Certifica que los contratos de red, los códecs de audio (MPEG/WebM), la serialización WebSocket y los modelos de IA en la nube funcionan perfectamente de extremo a extremo sin mocks.
- **Prueba de Micrófono Humano**: Requiere la interacción humana directa en el navegador para validar la sensibilidad del micrófono local, la cancelación de eco y la respuesta emocional del estudiante.

---

## 9. GUÍA DE DEMOSTRACIÓN Y EXPOSICIÓN ORAL (DEFENSA ANTE EL DOCENTE)

### 9.1 Guion de Demostración en Vivo (5 Minutos)
1. **Inicio de Sesión y Rol Estudiante (1 min)**:
   - Iniciar sesión como estudiante (`student_00dd92@socratia.edu`).
   - Mostrar `/dashboard`: explicar cómo el documento de tesis fue segmentado en chunks con embeddings densos en PostgreSQL.
2. **La Sala de Simulación y el Jurado Virtual (2 min)**:
   - Abrir la simulación y mostrar la interfaz de defensa.
   - Explicar la conexión en tiempo real por WebSocket (`/api/v1/ws/simulations/{id}`).
   - Mostrar cómo el jurado virtual lanza preguntas basadas estrictamente en la evidencia del documento y cómo el sistema detecta la voz del estudiante.
3. **El Reporte y la Evaluación Inmutable (1 min)**:
   - Navegar a `/simulations/{id}/report`: explicar que la calificación se genera con el patrón `Instructor` de Pydantic, garantizando esquemas estrictos sin alucinación numérica.
   - Demostrar el botón **"Imprimir / Guardar como PDF"** y mostrar el documento generado.
4. **El Panel de Administración y Configuración Dinámica (1 min)**:
   - Cambiar a usuario Administrador (`smoke_admin_demo@socratia.edu`).
   - Mostrar `/admin/ai-settings`: explicar que los cambios de modelo o de `retrieval_top_k` se aplican en caliente sin reiniciar los servidores.
   - Mostrar `/admin/dashboard` con la telemetría agregada.

### 9.2 Preguntas Difíciles del Docente y Respuestas de Nivel Senior

* **P1: ¿Por qué eligieron un Monolito Modular en lugar de Microservicios?**
  * *Respuesta*: "Para el alcance y tamaño del equipo en Software 1, un monolito modular ofrece una estricta separación de dominios (Clean Architecture) con transacciones ACID directas en PostgreSQL, evitando la sobrecarga operativa, latencia de red innecesaria y problemas de consistencia eventual que introducirían los microservicios, pero manteniendo la estructura lista para ser desacoplada a futuro."

* **P2: ¿Cómo evitan que el modelo de evaluación alucine puntajes o invente criterios?**
  * *Respuesta*: "Utilizamos `Instructor` con modelos Pydantic estrictos (`TurnEvaluationSchema`). El evaluador no recibe texto libre; se le inyecta únicamente el fragmento autorizado (chunks) recuperado por RAG y los puntos esperados de la pregunta. Además, la evaluación es idempotente: una vez en estado `COMPLETED`, queda inmutable en la base de datos y no se vuelve a recalcular."

* **P3: ¿Qué pasa si dos estudiantes intentan suscribirse al mismo tiempo o un usuario abre dos pestañas para tener dos planes activos?**
  * *Respuesta*: "No confiamos exclusivamente en la comprobación lógica de Python. Creamos un índice único condicional a nivel de PostgreSQL: `CREATE UNIQUE INDEX uq_active_user_subscription ON subscriptions (user_id) WHERE status = 'ACTIVE'`. Si dos transacciones intentan coexistir, la base de datos aborta la segunda mediante un error de integridad relacional."

* **P4: ¿Por qué no almacenan el audio de las respuestas de los estudiantes?**
  * *Respuesta*: "Por principios de privacidad por diseño (Privacy by Design) y optimización de almacenamiento. El pipeline de voz procesa el audio en memoria mediante streaming, lo envía a Groq Whisper para transcripción y descarta los bytes crudos inmediatamente. Solo se persiste el texto transcripto."

---

## 10. MANUAL DE DESPLIEGUE Y EJECUCIÓN LOCAL

### 10.1 Requisitos Previos
- Docker Desktop (con Compose habilitado).
- Node.js 22+ y Python 3.13 con `uv`.

### 10.2 Pasos de Puesta en Marcha
1. **Levantar Base de Datos (PostgreSQL + pgvector)**:
   ```powershell
   docker compose up -d --wait
   ```
2. **Aplicar Migraciones de Alembic**:
   ```powershell
   uv run --directory backend alembic upgrade head
   ```
3. **Ejecutar Backend FastAPI (Puerto 8000)**:
   ```powershell
   $env:DATABASE_URL="postgresql+psycopg://socratia:socratia_dev_password@localhost:5435/socratia"
   uv run --directory backend uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
4. **Ejecutar Frontend Next.js (Puerto 3000)**:
   ```powershell
   npm --prefix frontend run start
   ```

---

## 11. CONCLUSIÓN Y ESTADO FINAL DE ENTREGA

El sistema **SOCRATIA** cumple con el 100% de los requisitos estipulados para la materia Software 1. Cuenta con:
- **17 Casos de Uso Oficiales Operativos y Verificados (CU01–CU17).**
- **226 Pruebas Deterministas en Verde (0 fallos).**
- **Prueba Física de Integración de Voz Aprobada con Servicios Cloud Reales.**
- **Evidencias Visuales Completas de la Interfaz Web con Microsoft Edge.**
- **Reporte PDF Formal Generado y Validado.**

El proyecto se encuentra listo para ser congelado formalmente en Git bajo el tag de release final.
