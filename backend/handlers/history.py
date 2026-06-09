"""
Обработчики для управления историей предсказаний пользователя.
"""
import json
from aiohttp import web
from app_db import (
    run_fetchall_predictions_history, 
    run_hide_prediction, 
    run_hide_all_predictions
)

history_routes = web.RouteTableDef()


@history_routes.get("/api/predictions-history/{user_id}")
async def get_predictions_history(request: web.Request):
    """
    Возвращает историю предсказаний пользователя.
    
    URL parameters:
        - user_id: ID пользователя или 'me'/'current' для текущего
    
    Query parameters:
        - limit: Количество записей (по умолчанию 50)
    
    Returns:
        JSON со списком предсказаний
    """
    try:
        user_id = request.match_info['user_id']

        # поддержка специального маркера 'me' для запроса по cookie
        if user_id in ('me', 'current'):
            cookie_uid = request.cookies.get('user_id')
            if not cookie_uid:
                return web.json_response({"error": "Unauthorized"}, status=401)
            user_id = cookie_uid
        
        # получение количества записей (по умолчанию 50)
        limit = request.query.get('limit', 50)
        try:
            limit = int(limit)
            if limit < 1:
                limit = 1
        except ValueError:
            limit = 50
        
        # получение истории из БД
        try:
            user_id_int = int(user_id)
        except Exception:
            return web.json_response({"error": "Invalid user_id"}, status=400)

        records = await run_fetchall_predictions_history(request.app, user_id_int, limit)
        
        if not records:
            return web.json_response({"history": []}, status=200)
        
        # преобразование результатов
        history = []
        for record in records:
            history.append({
                'id': record['id'],
                'input_data': json.loads(record['input_data']),
                'predicted_price': float(record['predicted_price']),
                'created_at': record['created_at'].isoformat()
            })
        
        return web.json_response({"history": history}, status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@history_routes.post("/api/hide-prediction/{prediction_id}/{user_id}")
async def hide_prediction(request: web.Request):
    """
    Скрывает отдельное предсказание пользователя из истории (soft delete).
    
    URL parameters:
        - prediction_id: ID предсказания
        - user_id: ID пользователя или 'me'/'current'
    """
    try:
        prediction_id = request.match_info['prediction_id']
        user_id = request.match_info['user_id']

        # поддержка маркера 'me' для user_id
        if user_id in ('me', 'current'):
            cookie_uid = request.cookies.get('user_id')
            if not cookie_uid:
                return web.json_response({"error": "Unauthorized"}, status=401)
            user_id = cookie_uid
        
        try:
            prediction_id = int(prediction_id)
            user_id = int(user_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID format"}, status=400)
        
        success = await run_hide_prediction(request.app, prediction_id, user_id)
        
        if success:
            return web.json_response({"success": True}, status=200)
        else:
            return web.json_response({"error": "Record not found"}, status=404)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@history_routes.post("/api/hide-all-predictions/{user_id}")
async def hide_all_predictions(request: web.Request):
    """
    Скрывает все предсказания пользователя из истории (soft delete).
    
    URL parameters:
        - user_id: ID пользователя или 'me'/'current'
    """
    try:
        user_id = request.match_info['user_id']

        if user_id in ('me', 'current'):
            cookie_uid = request.cookies.get('user_id')
            if not cookie_uid:
                return web.json_response({"error": "Unauthorized"}, status=401)
            user_id = cookie_uid

        try:
            user_id = int(user_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID format"}, status=400)

        count = await run_hide_all_predictions(request.app, user_id)
        
        return web.json_response({"success": True, "hidden_count": count}, status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
