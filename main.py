from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import aiohttp
import os
from pydantic import BaseModel
import asyncio

app = FastAPI()


@app.on_event("startup")
async def startup_event() -> None:
    uri = os.environ.get("MONGO_URI")
    app.state.client = AsyncIOMotorClient(uri)
    app.state.db = app.state.client["magicdocs"]
    app.state.api_key = os.environ.get("API_KEY")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    app.state.client.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ImageData(BaseModel):
    image: str


async def fetch_data_item(item_id: str) -> dict:
    collection = app.state.db["data"]
    document = await collection.find_one({"id": item_id})
    if not document:
        raise HTTPException(status_code=404, detail="Item not found")
    return document

@app.get("/page")
async def get_page(id: str):
    result = await fetch_data_item(id)
    result.pop("_id", None)
    result["status"]["unlimit_end"] = None
    return JSONResponse(content=result, status_code=200)


@app.get("/exist")
async def check_existence(id: str):
    await fetch_data_item(id)
    return JSONResponse(content="Found", status_code=200)

@app.get("/login")
async def login(id: str):
    collection = app.state.db["data"]
    settings = app.state.db["settings"]
    result, settings_result = await asyncio.gather(
        collection.find_one({"id": id}),
        settings.find_one({})
    )
    if not result or not settings_result:
        raise HTTPException(status_code=404, detail="Item not found")
    return {
        "isAdmin": result["status"]["isAdmin"],
        "isLoginAllowed": settings_result["allowLogin"],
    }

@app.post("/sign")
async def sign(id: str, image_data: ImageData):
    try:
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field('image', image_data.image)
            async with session.post(
                f'https://api.imgbb.com/1/upload?key={app.state.api_key}',
                data=form
            ) as response:
                if response.status != 200:
                    raise HTTPException(status_code=500, detail="Error uploading image")
                data = await response.json()
                url = data['data']['url']

        collection = app.state.db['data']
        result = await collection.update_one(
            {"id": id},
            {"$set": {"img.urlSign": url}}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Item not found or not updated")
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3132)
