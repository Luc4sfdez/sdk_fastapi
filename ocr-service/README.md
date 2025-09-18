# OCR Service

Microservicio de OCR (Optical Character Recognition) para extraer texto de imágenes y documentos.

## 🚀 Características

- ✅ **Múltiples formatos**: JPG, PNG, PDF, TIFF, BMP
- ✅ **Procesamiento asíncrono**: No bloquea la API
- ✅ **Múltiples idiomas**: Español, inglés, etc.
- ✅ **Metadatos**: Confianza, dimensiones, DPI
- ✅ **API REST completa**: Upload, process, status, results
- ✅ **Documentación automática**: Swagger UI
- ✅ **Containerizado**: Docker ready

## 📋 Endpoints

### Principales
- `POST /upload` - Subir archivo para OCR
- `POST /process` - Procesar OCR de archivo
- `GET /status/{task_id}` - Estado del procesamiento
- `GET /results/{task_id}` - Obtener resultados
- `GET /list` - Listar todos los resultados
- `DELETE /results/{task_id}` - Eliminar resultado

### Utilidad
- `GET /` - Información del servicio
- `GET /health` - Health check
- `GET /docs` - Documentación Swagger

## 🔧 Instalación

### Opción 1: Local
```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servicio
python main.py

# O con uvicorn
uvicorn main:app --host 0.0.0.0 --port 8006 --reload
```

### Opción 2: Docker
```bash
# Construir imagen
docker build -t ocr-service .

# Ejecutar contenedor
docker run -p 8006:8006 ocr-service
```

## 📖 Uso

### 1. Subir archivo
```bash
curl -X POST "http://localhost:8006/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@mi_documento.jpg"
```

Respuesta:
```json
{
  "file_id": "uuid-del-archivo",
  "filename": "uuid_mi_documento.jpg",
  "original_name": "mi_documento.jpg",
  "size": 1024000,
  "message": "Archivo subido correctamente"
}
```

### 2. Procesar OCR
```bash
curl -X POST "http://localhost:8006/process" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "uuid-del-archivo",
    "language": "spa",
    "extract_tables": false,
    "extract_metadata": true
  }'
```

Respuesta:
```json
{
  "task_id": "uuid-de-la-tarea",
  "status": "pending",
  "message": "Procesamiento OCR iniciado"
}
```

### 3. Verificar estado
```bash
curl "http://localhost:8006/status/uuid-de-la-tarea"
```

Respuesta:
```json
{
  "id": "uuid-de-la-tarea",
  "status": "completed",
  "progress": 100,
  "message": "OCR completado exitosamente",
  "created_at": "2025-12-17T23:45:00",
  "completed_at": "2025-12-17T23:45:05"
}
```

### 4. Obtener resultados
```bash
curl "http://localhost:8006/results/uuid-de-la-tarea"
```

Respuesta:
```json
{
  "id": "uuid-de-la-tarea",
  "file_id": "uuid-del-archivo",
  "filename": "mi_documento.jpg",
  "text": "Texto extraído del documento...",
  "confidence": 95.2,
  "language": "spa",
  "pages": 1,
  "processing_time": 2.1,
  "metadata": {
    "file_size": 1024000,
    "format": ".jpg",
    "dimensions": "1920x1080",
    "dpi": 300
  },
  "created_at": "2025-12-17T23:45:05"
}
```

## 🔧 Configuración

### Variables de entorno
- `MAX_FILE_SIZE`: Tamaño máximo de archivo (default: 10MB)
- `UPLOAD_DIR`: Directorio de uploads (default: ./uploads)
- `RESULTS_DIR`: Directorio de resultados (default: ./results)

### Idiomas soportados
- `spa`: Español
- `eng`: Inglés
- `fra`: Francés
- `deu`: Alemán

## 🧪 Testing

```bash
# Ejecutar tests
python -m pytest tests/

# Test manual con curl
curl "http://localhost:8006/health"
```

## 🚀 Integración con API Gateway

En el API Gateway, añadir rutas:
```python
# Rutas OCR
app.mount("/ocr", proxy_to("http://ocr-service:8006"))
```

Acceso a través del gateway:
- `POST /ocr/upload`
- `POST /ocr/process`
- `GET /ocr/results/{task_id}`

## 📊 Monitoreo

El servicio expone métricas en:
- `/health` - Estado del servicio
- Logs estructurados
- Estadísticas de uso

## 🔮 Próximas mejoras

- [ ] Integración con Tesseract real
- [ ] Soporte para tablas (pandas)
- [ ] OCR de PDFs multipágina
- [ ] Cache de resultados
- [ ] Webhooks para notificaciones
- [ ] Batch processing
- [ ] ML para mejora de precisión