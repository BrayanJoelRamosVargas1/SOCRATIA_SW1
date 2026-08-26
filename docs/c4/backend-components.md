# C4 — Nivel 3: componentes del backend

```mermaid
flowchart TB
  API[FastAPI /api/v1]
  subgraph Identity
    Auth[Auth]
    Users[Users y roles]
  end
  subgraph Preparation
    Documents[Documents]
    RAG[RAG]
    Questions[Questions]
  end
  subgraph Practice
    Simulations[Simulations]
    Voice[Voice]
    Vision[Vision metrics]
    Evaluation[Evaluation]
    Reports[Reports]
  end
  subgraph Platform
    Subscriptions[Subscriptions]
    Payments[Payments]
    Admin[Admin]
    Audit[Audit]
  end

  API --> Auth --> Users
  API --> Documents --> RAG --> Questions --> Simulations
  Simulations --> Voice
  Simulations --> Vision
  Simulations --> Evaluation --> Reports
  API --> Subscriptions
  Payments --> Subscriptions
  API --> Admin
  API --> Audit
```

