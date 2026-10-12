$ErrorActionPreference = "Stop"

$projectPath = "C:\Users\ElCremosasWee\SOCRATIA_SW1\docs\uml\SOCRATIA_Model.eapx"

Write-Host "Opening Enterprise Architect via COM..."
$eaApp = New-Object -ComObject "EA.App"
$repo = $eaApp.Repository

try {
    $opened = $repo.OpenFile($projectPath)
    if (-not $opened) {
        throw "Could not open $projectPath in Enterprise Architect."
    }
    Write-Host "Successfully opened $projectPath"

    # Get root model package
    $models = $repo.Models
    if ($models.Count -eq 0) {
        throw "No root model found in EABase."
    }
    $rootPkg = $models.GetAt(0)
    $rootPkg.Name = "SOCRATIA - Modelo de Arquitectura y Diseno"
    $rootPkg.Update()

    # -------------------------------------------------------------
    # 1. Package: Casos de Uso (CU01-CU17)
    # -------------------------------------------------------------
    Write-Host "Building Casos de Uso package..."
    $ucPkg = $rootPkg.Packages.AddNew("1. Casos de Uso (CU01-CU17)", "")
    $ucPkg.Notes = "Catalogo completo de los 17 casos de uso oficiales de Socratia."
    $ucPkg.Update()

    # Actors
    $actorStudent = $ucPkg.Elements.AddNew("Estudiante", "Actor")
    $actorStudent.Notes = "Usuario estudiante que prepara su tesis y realiza simulaciones de defensa oral."
    $actorStudent.Update()

    $actorAdmin = $ucPkg.Elements.AddNew("Administrador", "Actor")
    $actorAdmin.Notes = "Usuario con privilegios de gestion de usuarios, planes, jurados y configuracion de IA."
    $actorAdmin.Update()

    $actorJury = $ucPkg.Elements.AddNew("Jurado Virtual", "Actor")
    $actorJury.Notes = "Actor virtual de sistema que emula las personalidades de jurado y evalua las respuestas."
    $actorJury.Update()

    # Diagram UC
    $ucDiagram = $ucPkg.Diagrams.AddNew("Diagrama General de Casos de Uso", "Use Case")
    $ucDiagram.Notes = "Diagrama general de los 17 casos de uso y actores del sistema."
    $ucDiagram.Update()

    # Add actors to diagram
    $dObj1 = $ucDiagram.DiagramObjects.AddNew("", "")
    $dObj1.ElementID = $actorStudent.ElementID
    $dObj1.left = 50; $dObj1.right = 150; $dObj1.top = -100; $dObj1.bottom = -200
    $dObj1.Update()

    $dObj2 = $ucDiagram.DiagramObjects.AddNew("", "")
    $dObj2.ElementID = $actorAdmin.ElementID
    $dObj2.left = 50; $dObj2.right = 150; $dObj2.top = -300; $dObj2.bottom = -400
    $dObj2.Update()

    $dObj3 = $ucDiagram.DiagramObjects.AddNew("", "")
    $dObj3.ElementID = $actorJury.ElementID
    $dObj3.left = 800; $dObj3.right = 900; $dObj3.top = -200; $dObj3.bottom = -300
    $dObj3.Update()

    $useCases = @(
        @{ Name = "CU01 - Gestionar autenticacion"; Notes = "Registro, login HttpOnly, bloqueo por intentos y logout."; Actor = $actorStudent },
        @{ Name = "CU02 - Gestionar perfil propio"; Notes = "Edicion de datos personales con proteccion de roles."; Actor = $actorStudent },
        @{ Name = "CU03 - Gestionar suscripcion propia"; Notes = "Consulta de planes, suscripcion activa y cancelacion."; Actor = $actorStudent },
        @{ Name = "CU04 - Gestionar usuarios"; Notes = "Listado, activacion/desactivacion y roles por el Administrador."; Actor = $actorAdmin },
        @{ Name = "CU05 - Gestionar planes y suscripciones"; Notes = "CRUD de planes y auditoria de suscripciones activas."; Actor = $actorAdmin },
        @{ Name = "CU06 - Gestionar documentos academicos"; Notes = "Subida multipart, validacion MIME y almacenamiento de tesis."; Actor = $actorStudent },
        @{ Name = "CU07 - Procesar documento (RAG)"; Notes = "Extraccion, chunking, generacion de vectores y persistencia pgvector."; Actor = $actorStudent },
        @{ Name = "CU08 - Generar material de preparacion"; Notes = "Generacion de bancos de preguntas y diapositivas de defensa."; Actor = $actorStudent },
        @{ Name = "CU09 - Configurar parametros de IA"; Notes = "Ajuste dinámico de top_k, temperatura y modelos sin reinicio."; Actor = $actorAdmin },
        @{ Name = "CU10 - Configurar simulacion"; Notes = "Seleccion de jurado, calibracion de microfono/camara y readiness."; Actor = $actorStudent },
        @{ Name = "CU11 - Gestionar sesion de simulacion"; Notes = "Control de estados (DRAFT->READY->ACTIVE->COMPLETED) y tiempo."; Actor = $actorStudent },
        @{ Name = "CU12 - Interactuar con jurado virtual"; Notes = "Comunicacion WebSocket, deteccion de voz VAD y follow-ups."; Actor = $actorStudent },
        @{ Name = "CU13 - Administrar perfiles de jurado"; Notes = "Gestion de personalidades (Metodologico, Critico, Tecnico)."; Actor = $actorAdmin },
        @{ Name = "CU14 - Evaluar desempeno del estudiante"; Notes = "Evaluacion estructurada LLM via Instructor con rúbricas 0-100."; Actor = $actorJury },
        @{ Name = "CU15 - Gestionar reporte de desempeno"; Notes = "Proyeccion determinista de scores y guardado como PDF."; Actor = $actorStudent },
        @{ Name = "CU16 - Consultar historial de desempeno"; Notes = "Evolucion temporal de puntajes y calculo determinista de deltas."; Actor = $actorStudent },
        @{ Name = "CU17 - Supervisar plataforma"; Notes = "Tablero administrativo con metricas de usuarios, simulaciones y salud."; Actor = $actorAdmin }
    )

    $yPos = -50
    $col = 0
    foreach ($uc in $useCases) {
        $ucElem = $ucPkg.Elements.AddNew($uc.Name, "UseCase")
        $ucElem.Notes = $uc.Notes
        $ucElem.Update()

        # Connect actor to usecase
        $conn = $uc.Actor.Connectors.AddNew("", "Association")
        $conn.SupplierID = $ucElem.ElementID
        $conn.Update()

        $dObj = $ucDiagram.DiagramObjects.AddNew("", "")
        $dObj.ElementID = $ucElem.ElementID
        $x = 220 + ($col * 260)
        $dObj.left = $x; $dObj.right = $x + 230; $dObj.top = $yPos; $dObj.bottom = $yPos - 60
        $dObj.Update()

        $col++
        if ($col -ge 2) {
            $col = 0
            $yPos -= 80
        }
    }
    $ucDiagram.Update()
    $ucPkg.Packages.Refresh()

    # -------------------------------------------------------------
    # 2. Package: Clases de Dominio
    # -------------------------------------------------------------
    Write-Host "Building Clases de Dominio package..."
    $classPkg = $rootPkg.Packages.AddNew("2. Clases de Dominio", "")
    $classPkg.Notes = "Modelo entidad-relacion relacional y clases de dominio en Clean Architecture."
    $classPkg.Update()

    $classDiagram = $classPkg.Diagrams.AddNew("Diagrama de Clases de Dominio", "Logical")
    $classDiagram.Update()

    $domainClasses = @(
        @{
            Name = "User";
            Attributes = @("id: UUID", "email: String", "password_hash: String", "full_name: String", "is_active: Boolean", "auth_version: Integer")
        },
        @{
            Name = "Role";
            Attributes = @("id: Integer", "name: String", "description: String")
        },
        @{
            Name = "Document";
            Attributes = @("id: UUID", "user_id: UUID", "original_name: String", "sha256_hash: String", "status: Enum")
        },
        @{
            Name = "DocumentChunk";
            Attributes = @("id: UUID", "document_id: UUID", "chunk_index: Integer", "content: Text", "embedding: Vector768")
        },
        @{
            Name = "QuestionBank";
            Attributes = @("id: UUID", "document_id: UUID", "user_id: UUID", "status: Enum")
        },
        @{
            Name = "Question";
            Attributes = @("id: UUID", "question_bank_id: UUID", "question: Text", "category: Enum", "difficulty: Enum", "expected_answer_points: JSON")
        },
        @{
            Name = "JuryProfile";
            Attributes = @("id: UUID", "name: String", "personality_type: Enum", "system_prompt: Text", "is_active: Boolean")
        },
        @{
            Name = "Simulation";
            Attributes = @("id: UUID", "user_id: UUID", "document_id: UUID", "jury_profile_id: UUID", "status: Enum", "started_at: DateTime", "finished_at: DateTime")
        },
        @{
            Name = "SimulationTurn";
            Attributes = @("id: UUID", "simulation_id: UUID", "turn_number: Integer", "student_transcript: Text", "jury_response: Text", "created_at: DateTime")
        },
        @{
            Name = "Evaluation";
            Attributes = @("id: UUID", "simulation_id: UUID", "overall_score: Float", "content_score: Float", "status: Enum", "created_at: DateTime")
        },
        @{
            Name = "TurnEvaluation";
            Attributes = @("id: UUID", "evaluation_id: UUID", "turn_score: Float", "classification: Enum", "strengths: JSON", "weaknesses: JSON", "contradictions: JSON")
        },
        @{
            Name = "Plan";
            Attributes = @("id: UUID", "name: String", "price: Numeric", "is_active: Boolean", "description: Text")
        },
        @{
            Name = "Subscription";
            Attributes = @("id: UUID", "user_id: UUID", "plan_id: UUID", "status: Enum", "price_at_subscription: Numeric", "started_at: DateTime")
        },
        @{
            Name = "AISettings";
            Attributes = @("id: Integer", "rag_top_k: Integer", "jury_model: String", "evaluator_model: String", "config_version: Integer", "updated_at: DateTime")
        }
    )

    $cx = 50; $cy = -50
    $cCol = 0
    foreach ($dc in $domainClasses) {
        $clsElem = $classPkg.Elements.AddNew($dc.Name, "Class")
        $clsElem.Update()

        foreach ($attr in $dc.Attributes) {
            $parts = $attr.Split(":")
            $aName = $parts[0].Trim()
            $aType = if ($parts.Length -gt 1) { $parts[1].Trim() } else { "String" }
            $att = $clsElem.Attributes.AddNew($aName, $aType)
            $att.Update()
        }
        $clsElem.Update()

        $dObj = $classDiagram.DiagramObjects.AddNew("", "")
        $dObj.ElementID = $clsElem.ElementID
        $dObj.left = $cx; $dObj.right = $cx + 200; $dObj.top = $cy; $dObj.bottom = $cy - 140
        $dObj.Update()

        $cx += 240
        $cCol++
        if ($cCol -ge 4) {
            $cCol = 0
            $cx = 50
            $cy -= 180
        }
    }
    $classDiagram.Update()
    $classPkg.Packages.Refresh()

    # -------------------------------------------------------------
    # 3. Package: Componentes de Arquitectura
    # -------------------------------------------------------------
    Write-Host "Building Componentes de Arquitectura package..."
    $compPkg = $rootPkg.Packages.AddNew("3. Componentes de Arquitectura", "")
    $compPkg.Notes = "Diagrama de componentes de software del monolito modular y servicios de IA."
    $compPkg.Update()

    $compDiagram = $compPkg.Diagrams.AddNew("Diagrama de Componentes del Sistema", "Component")
    $compDiagram.Update()

    $components = @(
        "Frontend::NextJS 16 Web Client",
        "Backend::FastAPI Gateway & Auth",
        "Module::P1 Identidad & Seguridad",
        "Module::P2 Documentos & RAG Coordinator",
        "Module::P3 Motor de Simulacion WebSocket",
        "Module::P4 Evaluacion & Reportes (Instructor)",
        "Module::P5 Gestion SaaS & Suscripciones",
        "Module::P6 Administracion & Supervisión",
        "External::PostgreSQL 16 & pgvector",
        "External::Groq Whisper STT",
        "External::Google Gemini Flash LLM",
        "External::ElevenLabs TTS Streaming"
    )

    $cx = 50; $cy = -50
    $cCol = 0
    foreach ($compName in $components) {
        $cElem = $compPkg.Elements.AddNew($compName, "Component")
        $cElem.Update()

        $dObj = $compDiagram.DiagramObjects.AddNew("", "")
        $dObj.ElementID = $cElem.ElementID
        $dObj.left = $cx; $dObj.right = $cx + 220; $dObj.top = $cy; $dObj.bottom = $cy - 80
        $dObj.Update()

        $cx += 250
        $cCol++
        if ($cCol -ge 3) {
            $cCol = 0
            $cx = 50
            $cy -= 120
        }
    }
    $compDiagram.Update()
    $compPkg.Packages.Refresh()

    # -------------------------------------------------------------
    # 4. Package: Secuencia de Interaccion con Jurado
    # -------------------------------------------------------------
    Write-Host "Building Secuencia de Interaccion package..."
    $seqPkg = $rootPkg.Packages.AddNew("4. Secuencia de Interaccion con Jurado", "")
    $seqPkg.Notes = "Diagrama de secuencia del turno interactivo de defensa oral."
    $seqPkg.Update()

    $seqDiagram = $seqPkg.Diagrams.AddNew("Diagrama de Secuencia - Turno de Voz", "Sequence")
    $seqDiagram.Update()

    $lifelines = @("Estudiante", "WebSocket_Router", "Groq_STT", "Jury_Router_LLM", "ElevenLabs_TTS", "PostgreSQL_Database")
    $lx = 50
    foreach ($ll in $lifelines) {
        $llElem = $seqPkg.Elements.AddNew($ll, "Sequence")
        $llElem.Update()

        $dObj = $seqDiagram.DiagramObjects.AddNew("", "")
        $dObj.ElementID = $llElem.ElementID
        $dObj.left = $lx; $dObj.right = $lx + 100; $dObj.top = -50; $dObj.bottom = -450
        $dObj.Update()
        $lx += 150
    }
    $seqDiagram.Update()
    $seqPkg.Packages.Refresh()

    # Save and close repository
    $repo.SaveAllDiagrams()
    $repo.CloseFile()
    Write-Host "Model created and saved successfully into $projectPath"
}
finally {
    $repo.Exit()
}
