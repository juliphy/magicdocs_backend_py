from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import aiohttp
import datetime
from pydantic import BaseModel

app = FastAPI()

uri = 'mongodb+srv://juliphyy:l7jOBx88bEV9kvw5@cluster0.vpa0axs.mongodb.net/?retryWrites=true&w=majority'
client = AsyncIOMotorClient(uri)
db = client['magicdocs']
API_KEY = "d2f5768f8798f57a63d32ddd6a4e9f8e"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ImageData(BaseModel):
    image: str

@app.get("/page")
async def get_page(id: str):
    collection = db['data']
    result = await collection.find_one({"id": id})
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    
    del result["_id"]
    result['status']["unlimit_end"] = None
    return JSONResponse(content=result, status_code = 200)


@app.get("/exist")
async def check_existence(id: str):
    collection = db['data']
    result = await collection.find_one({"id": id})
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return JSONResponse(content="Found", status_code=200)

@app.get("/login")
async def login(id: str):
    collection = db['data']
    settings = db['settings']
    result = await collection.find_one({"id": id})
    settings_result = await settings.find_one({})
    if not result or not settings_result:
        raise HTTPException(status_code=404, detail="Item not found")
    return {
        "isAdmin": result['status']['isAdmin'],
        "isLoginAllowed": settings_result['allowLogin']
    }

@app.post("/sign")
async def sign(id: str, image_data: ImageData):
    try:
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field('image', image_data.image)
            async with session.post(
                f'https://api.imgbb.com/1/upload?key={API_KEY}', 
                data=form
            ) as response:
                if response.status != 200:
                    raise HTTPException(status_code=500, detail="Error uploading image")
                data = await response.json()
                url = data['data']['url']

        collection = db['data']
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
