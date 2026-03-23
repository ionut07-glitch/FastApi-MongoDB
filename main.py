from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse # Para servir el HTML
from pymongo import MongoClient
from pydantic import BaseModel
from bson import ObjectId
import certifi
from datetime import datetime
import os

app = FastAPI(title="MFlix API Full Stack - Ionut Edition")

# 1. Configuración de CORS
# Permite que tu navegador y otros dispositivos se conecten sin errores de seguridad
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Conexión a MongoDB Atlas (PyMongo Oficial)
MONGO_URL = "mongodb+srv://ionutantonioardelean:YqHSQRab6VbSeUjD@cluster0.6tlofo9.mongodb.net/"
client = MongoClient(MONGO_URL, tlsCAFile=certifi.where())
db = client['sample_mflix']
collection = db['comments']

# 3. Modelos de Datos (Pydantic)
class ComentarioSchema(BaseModel):
    name: str
    email: str
    movie_id: str
    text: str

class ActualizarSchema(BaseModel):
    text: str

# 4. Función de Serialización (Limpieza de datos para JSON)
def serializar(doc):
    if not doc: return None
    for k, v in doc.items():
        if isinstance(v, (ObjectId, datetime)):
            doc[k] = str(v)
    doc["_id"] = str(doc["_id"])
    return doc

# --- ENDPOINTS ---

# SERVIR HTML: Accede a http://192.168.221.31:8000/ver
@app.get("/ver", include_in_schema=False)
def ver_pagina_web():
    # Asegúrate de que index.html esté en la misma carpeta que este archivo
    ruta_html = os.path.join(os.getcwd(), "index.html")
    if os.path.exists(ruta_html):
        return FileResponse(ruta_html)
    return {"error": "Archivo index.html no encontrado en la carpeta del servidor"}

@app.get("/")
def inicio():
    return {"status": "API Online", "web": "/ver", "docs": "/docs"}

# LISTAR: Los últimos 10 comentarios
@app.get("/comentarios")
def listar_comentarios():
    cursor = collection.find().sort("date", -1).limit(10)
    return [serializar(doc) for doc in cursor]

# BUSCAR POR NOMBRE: (Find con Regex)
@app.get("/buscar/{nombre}")
def buscar_por_nombre(nombre: str):
    query = {"name": {"$regex": nombre, "$options": "i"}}
    cursor = collection.find(query).limit(10)
    resultados = [serializar(doc) for doc in cursor]
    if not resultados:
        return {"mensaje": f"No se han encontrado comentarios de: {nombre}"}
    return resultados

# BUSCAR POR ID: (Find One)
@app.get("/buscar_id/{id_comentario}")
def buscar_por_id(id_comentario: str):
    try:
        resultado = collection.find_one({"_id": ObjectId(id_comentario)})
        if not resultado:
            raise HTTPException(status_code=404, detail="ID no encontrado")
        return serializar(resultado)
    except:
        raise HTTPException(status_code=400, detail="Formato de ID no válido")

# CREAR: Nuevo comentario (POST)
@app.post("/crear")
def crear_comentario(datos: ComentarioSchema):
    doc = datos.dict()
    doc["date"] = datetime.utcnow()
    try:
        doc["movie_id"] = ObjectId(doc["movie_id"])
    except: pass
    res = collection.insert_one(doc)
    return {"mensaje": "Insertado correctamente", "id": str(res.inserted_id)}

# ACTUALIZAR: Editar texto (PUT)
@app.put("/actualizar/{id_comentario}")
def actualizar_comentario(id_comentario: str, datos: ActualizarSchema):
    res = collection.update_one(
        {"_id": ObjectId(id_comentario)},
        {"$set": {"text": datos.text, "date": datetime.utcnow()}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="No encontrado para actualizar")
    return {"mensaje": "Actualizado correctamente"}

# BORRAR: Eliminar (DELETE)
@app.delete("/borrar/{id_comentario}")
def borrar_comentario(id_comentario: str):
    try:
        res = collection.delete_one({"_id": ObjectId(id_comentario)})
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="ID no encontrado")
        return {"mensaje": "Comentario eliminado con éxito"}
    except:
        raise HTTPException(status_code=400, detail="Error al borrar o ID inválido")
