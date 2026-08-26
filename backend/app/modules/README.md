# Paquetes funcionales del backend

La estructura física del monolito modular refleja los paquetes del modelo de casos de uso:

| Paquete físico | Paquete UML | Casos de uso | Estado |
| --- | --- | --- | --- |
| `p1_gestion_identidad_seguridad` | `P1_GestionIdentidadSeguridad` | CU01–CU05 | Implementado |
| `p2_gestion_documentos_preparacion` | `P2_GestionDocumentosPreparacion` | CU06–CU11 | En progreso |
| `p3_gestion_simulacion` | `P3_GestionSimulacion` | CU12–CU19 | Pendiente |
| `p4_gestion_evaluacion_resultados` | `P4_GestionEvaluacionResultados` | CU20–CU27 | Pendiente |
| `p5_gestion_saas` | `P5_GestionSaaS` | CU28–CU31 | Pendiente |
| `p6_gestion_administracion` | `P6_GestionAdministracion` | CU32–CU37 | Pendiente |

## Reglas

- Un paquete es propietario de sus rutas, servicios, modelos, repositorios, esquemas y políticas.
- `app/api/v1/router.py` sólo compone los routers públicos de los paquetes.
- Las integraciones externas permanecen en `app/integrations`; no pertenecen a un único paquete.
- Los paquetes pendientes contienen únicamente `README.md` y `__init__.py`.
- Una dependencia entre paquetes debe ser explícita y apuntar a una interfaz o contrato estable.
