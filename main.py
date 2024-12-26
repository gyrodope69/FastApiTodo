from urllib.parse import quote_plus
from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from bson import ObjectId

app = FastAPI()

# MongoDB connection
escaped_username = quote_plus(username)
escaped_password = quote_plus(password)
uri = f"mongodb+srv://{escaped_username}:{escaped_password}@cluster0.zdlq43f.mongodb.net/TodoList"
conn = MongoClient(uri)
db = conn["TodoList"]

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")

class Task(BaseModel):
    id: PyObjectId = None
    title: str
    description: str = None
    is_done: bool = False

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "title": "Learn FastAPI",
                "description": "Study FastAPI documentation",
                "is_done": False
            }
        }

# Routes
@app.get('/')
async def root():
    return {"message": "Hello World from FastAPI"}

@app.post("/tasks")
async def add_task(task: Task):
    task_dict = task.dict()
    task_dict.pop("id", None)  # Remove ID since MongoDB generates it
    result = db.tasks.insert_one(task_dict)
    return {"task_id": str(result.inserted_id)}

@app.get("/tasks")
async def list_tasks():
    tasks = db.tasks.find()
    return [{"id": str(task["_id"]), "title": task["title"], "description": task.get("description"), "is_done": task["is_done"]} for task in tasks]

@app.put("/tasks/{task_id}")
async def update_task(task_id: str, task: Task):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID")

    result = db.tasks.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": task.dict(exclude_unset=True)}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"message": "Task updated successfully"}

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID")

    result = db.tasks.delete_one({"_id": ObjectId(task_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"message": "Task deleted successfully"}

@app.delete("/tasks")
async def delete_all_tasks():
    result = db.tasks.delete_many({})
    return {"deleted_count": result.deleted_count}
