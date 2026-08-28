# Adaptadores externos

Los módulos de negocio dependen de interfaces definidas aquí, no de SDK concretos. `email/`
implementa correo transaccional mediante SMTP estándar y `storage/` conserva el contrato de
archivos. Los clientes de OpenAI/Gemini, S3, Pinecone, STT, TTS y pagos se incorporarán sólo en el
sprint que los necesite.
