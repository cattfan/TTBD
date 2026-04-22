from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
import asyncio
import os
import shutil
import pandas as pd
from scraper import run_scraper

app = FastAPI()

templates = Jinja2Templates(directory="templates")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_log(self, message: str):
        for conn in self.active_connections:
            try: await conn.send_json({"type": "log", "message": message})
            except: pass

    async def broadcast_status(self, status: dict):
        for conn in self.active_connections:
            try: await conn.send_json({"type": "status", "data": status})
            except: pass

    async def broadcast_data(self, row: dict):
        for conn in self.active_connections:
            try: await conn.send_json({"type": "data", "row": row})
            except: pass

manager = ConnectionManager()
EXCEL_DIR = os.path.dirname(os.path.abspath(__file__))

# Biến toàn cục lưu file đang được chọn
CURRENT_SELECTED_FILE = "Test_Updated.xlsx"

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/list-files")
async def list_files():
    files = [f for f in os.listdir(EXCEL_DIR) if f.endswith('.xlsx') or f.endswith('.xls')]
    return {"files": files, "current": CURRENT_SELECTED_FILE}

@app.post("/select-file")
async def select_file(data: dict):
    global CURRENT_SELECTED_FILE
    filename = data.get("filename")
    if filename and os.path.exists(os.path.join(EXCEL_DIR, filename)):
        CURRENT_SELECTED_FILE = filename
        return {"success": True, "selected": CURRENT_SELECTED_FILE}
    return {"success": False, "error": "File không tồn tại"}

@app.get("/preview-excel")
async def preview_excel():
    target_path = os.path.join(EXCEL_DIR, CURRENT_SELECTED_FILE)
    if not os.path.exists(target_path):
        return {"columns": [], "data": [], "message": f"Không tìm thấy file {CURRENT_SELECTED_FILE}. Vui lòng chọn hoặc tải file lên."}
    try:
        # Đọc file với engine openpyxl để ổn định hơn trên Windows
        df = pd.read_excel(target_path, engine='openpyxl')
        # Chuyển đổi các cột ngày tháng sang chuỗi để tránh lỗi JSON
        for col in df.select_dtypes(include=['datetime']).columns:
            df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            
        data = df.head(100).fillna("").to_dict(orient="records")
        columns = df.columns.tolist()
        return {"columns": columns, "data": data}
    except Exception as e:
        return {"columns": [], "data": [], "message": f"File đang bận hoặc lỗi: {str(e)}"}

@app.get("/download-excel")
async def download_excel():
    target_path = os.path.join(EXCEL_DIR, CURRENT_SELECTED_FILE)
    if not os.path.exists(target_path):
        return JSONResponse(content={"error": "File không tồn tại"}, status_code=404)
    return FileResponse(
        path=target_path,
        filename=CURRENT_SELECTED_FILE,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.post("/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    global CURRENT_SELECTED_FILE
    try:
        if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            return {"success": False, "error": "Chỉ chấp nhận file Excel (.xlsx, .xls)"}
            
        save_path = os.path.join(EXCEL_DIR, file.filename)
        with open(save_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        CURRENT_SELECTED_FILE = file.filename # Tự động chọn file vừa upload
        return {"success": True, "filename": file.filename}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "start":
                target_path = os.path.join(EXCEL_DIR, CURRENT_SELECTED_FILE)
                asyncio.create_task(run_scraper(target_path, manager))
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
