import asyncio
import json
import aiohttp
from pathlib import Path
from typing import List, Dict, Any
from ollama import AsyncClient

class MetalDataProcessor:
    def __init__(self, model: str = "moondream", api_url: str = "http://localhost:8000/predict-manual"):
        self.client = AsyncClient()
        self.model = model
        self.api_url = api_url
        self.schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "Наименование": {"type": ["string", "null"]},
                            "Размер_A": {"type": ["number", "null"]},
                            "Марка": {"type": ["string", "null"]},
                            "Основная_марка": {"type": ["string", "null"]},
                            "Толщина": {"type": ["number", "null"]},
                            "Категория_цены": {"type": ["string", "null"]}
                        },
                        "required": ["Наименование"]
                    }
                }
            },
            "required": ["items"]
        }

    async def _get_prediction(self, user_id, item: Dict[str, Any]) -> float:
        async with aiohttp.ClientSession() as session:
            try:
                payload = {**item, "user_id": user_id}
                async with session.post(self.api_url, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("price", 0.0)
                    return 0.0
            except Exception:
                return 0.0

    async def _validate(self, path: str) -> bool:
        try:
            resp = await self.client.chat(
                model=self.model,
                format={'type': 'object', 'properties': {'answer': {'type': 'boolean'}}, 'required': ['answer']},
                messages=[{
                    'role': 'user', 
                    'content': 'Check if image contains metal products table.', 
                    'images': [path]
                }]
            )
            return json.loads(resp.message.content).get("answer", False)
        except Exception:
            return False

    async def _extract(self, path: str) -> List[Dict[str, Any]]:
        try:
            resp = await self.client.chat(
                model=self.model,
                format=self.schema,
                messages=[{
                    'role': 'user',
                    'content': 'Extract table to JSON.',
                    'images': [path]
                }],
                options={'num_ctx': 4096, 'temperature': 0}
            )
            return json.loads(resp.message.content).get("items", [])
        except Exception:
            return []

    async def run_batch(self, files: List[str]) -> List[Dict[str, Any]]:
        all_items = []
        for file_path in files:
            p = Path(file_path)
            if not p.exists():
                continue

            if await self._validate(file_path):
                items = await self._extract(file_path)
                if items:
                    tasks = [self._get_prediction(item) for item in items]
                    prices = await asyncio.gather(*tasks)
                    
                    for i, item in enumerate(items):
                        item["predicted_price"] = prices[i]
                        item["source"] = p.name
                    
                    all_items.extend(items)
        return all_items

async def main():
    processor = MetalDataProcessor()
    
    image_list = [
        "/home/ranil/Рабочий стол/PROJECT/ai/images/image1.png",
        "/home/ranil/Рабочий стол/PROJECT/ai/images/image2.png",
        "/home/ranil/Рабочий стол/PROJECT/ai/images/image3.png"
    ]

    results = await processor.run_batch(image_list)
    print(json.dumps(results, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
