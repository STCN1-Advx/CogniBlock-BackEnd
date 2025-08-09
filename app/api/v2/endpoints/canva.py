from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.api.v2.auth import get_current_user, require_canvas_access, require_canvas_owner
from app.schemas.canva import (
    CanvaPullRequest, 
    CardResponse, 
    CardUpdateRequest,
    CanvaPushRequest,
    ErrorResponse,
    CanvasCreate,
    CanvasUpdate
)
from app.schemas.user import User
from app.services.canva_service import CanvaService, CanvaServiceError, PermissionDeniedError, CanvaNotFoundError
from app.crud import canvas as canvas_crud, card as card_crud

router = APIRouter()


@router.get("/list", response_model=List[int])
async def get_canvas_list(
    x_user_id: UUID = Header(..., alias="x-user-id"),
    db: Session = Depends(get_db)
):
    """
    获取用户的画布ID列表
    
    通过x-user-id头部参数获取指定用户拥有的所有画布ID。
    
    Args:
        x_user_id: 用户ID（通过x-user-id头部传入）
        db: 数据库会话
        
    Returns:
        List[int]: 用户拥有的画布ID数组，例如 [101, 104, 602]
        
    Raises:
        HTTPException:
            - 400: 用户ID格式错误
            - 500: 服务器内部错误
    """
    try:
        # 获取用户的所有画布
        canvases = canvas_crud.get_by_owner(db, owner_id=x_user_id)
        
        # 提取画布ID并返回
        canvas_ids = [canvas.id for canvas in canvases]
        
        return canvas_ids
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user ID format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
             detail=f"Internal server error: {str(e)}"
         )


# 卡片管理 API
@router.post("/cards/add")
async def add_card_to_canvas(
    card_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    向画布添加卡片
    
    在指定画布中添加一个新卡片。
    
    Args:
        card_data: 卡片数据，包含canvas_id, content_id, position_x, position_y
        current_user: 当前认证用户
        db: 数据库会话
        
    Returns:
        dict: 创建的卡片信息
        
    Raises:
        HTTPException:
            - 400: 请求数据格式错误
            - 403: 用户无权限访问画布
            - 404: 画布或内容不存在
            - 500: 服务器内部错误
    """
    try:
        canvas_id = card_data.get("canvas_id")
        content_id = card_data.get("content_id")
        position_x = card_data.get("position_x", 0)
        position_y = card_data.get("position_y", 0)
        
        if not canvas_id or not content_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="canvas_id and content_id are required"
            )
        
        # 验证画布权限
        canva_service = CanvaService()
        canvas = canva_service.verify_user_permission(db, canvas_id, current_user.id)
        
        # 创建卡片
        card = card_crud.create(
            db,
            obj_in={
                "canvas_id": canvas_id,
                "content_id": content_id,
                "position_x": position_x,
                "position_y": position_y
            }
        )
        
        return {
            "card_id": card.id,
            "canvas_id": card.canvas_id,
            "content_id": card.content_id,
            "position_x": card.position_x,
            "position_y": card.position_y,
            "created_at": card.created_at.isoformat(),
            "updated_at": card.updated_at.isoformat(),
            "message": "Card added successfully"
        }
        
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except CanvaNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete("/cards/delete/{card_id}")
async def delete_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除卡片
    
    删除指定的卡片。用户必须有权限访问该卡片所在的画布。
    
    Args:
        card_id: 卡片ID
        current_user: 当前认证用户
        db: 数据库会话
        
    Returns:
        dict: 删除结果
        
    Raises:
        HTTPException:
            - 403: 用户无权限删除卡片
            - 404: 卡片不存在
            - 500: 服务器内部错误
    """
    try:
        # 获取卡片信息
        card = card_crud.get(db, card_id)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Card {card_id} not found"
            )
        
        # 验证画布权限
        canva_service = CanvaService()
        canva_service.verify_user_permission(db, card.canvas_id, current_user.id)
        
        # 删除卡片
        card_crud.delete(db, card_id)
        
        return {
            "message": "Card deleted successfully",
            "card_id": card_id
        }
        
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.put("/cards/update/{card_id}")
async def update_card(
    card_id: int,
    card_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新卡片信息
    
    更新卡片的位置或关联的内容。
    
    Args:
        card_id: 卡片ID
        card_data: 更新数据
        current_user: 当前认证用户
        db: 数据库会话
        
    Returns:
        dict: 更新后的卡片信息
        
    Raises:
        HTTPException:
            - 403: 用户无权限更新卡片
            - 404: 卡片不存在
            - 500: 服务器内部错误
    """
    try:
        # 获取卡片信息
        card = card_crud.get(db, card_id)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Card {card_id} not found"
            )
        
        # 验证画布权限
        canva_service = CanvaService()
        canva_service.verify_user_permission(db, card.canvas_id, current_user.id)
        
        # 更新卡片
        updated_card = card_crud.update(db, card, card_data)
        
        return {
            "card_id": updated_card.id,
            "canvas_id": updated_card.canvas_id,
            "content_id": updated_card.content_id,
            "position_x": updated_card.position_x,
            "position_y": updated_card.position_y,
            "created_at": updated_card.created_at.isoformat(),
            "updated_at": updated_card.updated_at.isoformat(),
            "message": "Card updated successfully"
        }
        
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/cards/{canvas_id}")
async def get_canvas_cards(
    canvas_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取画布中的所有卡片
    
    获取指定画布中的所有卡片信息。
    
    Args:
        canvas_id: 画布ID
        current_user: 当前认证用户
        db: 数据库会话
        
    Returns:
        dict: 卡片列表
        
    Raises:
        HTTPException:
            - 403: 用户无权限访问画布
            - 404: 画布不存在
            - 500: 服务器内部错误
    """
    try:
        # 验证画布权限
        canva_service = CanvaService()
        canvas = canva_service.verify_user_permission(db, canvas_id, current_user.id)
        
        # 获取卡片列表
        cards = card_crud.get_by_canvas(db, canvas_id)
        
        cards_data = []
        for card in cards:
            cards_data.append({
                "card_id": card.id,
                "canvas_id": card.canvas_id,
                "content_id": card.content_id,
                "position_x": card.position_x,
                "position_y": card.position_y,
                "created_at": card.created_at.isoformat(),
                "updated_at": card.updated_at.isoformat()
            })
        
        return {
            "canvas_id": canvas_id,
            "canvas_name": canvas.name,
            "cards_count": len(cards_data),
            "cards": cards_data
        }
        
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except CanvaNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/cards/batch")
async def batch_add_cards(
    batch_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    批量添加卡片
    
    在指定画布中批量添加多个卡片。
    
    Args:
        batch_data: 批量数据，包含canvas_id和cards列表
        current_user: 当前认证用户
        db: 数据库会话
        
    Returns:
        dict: 批量创建结果
        
    Raises:
        HTTPException:
            - 400: 请求数据格式错误
            - 403: 用户无权限访问画布
            - 404: 画布不存在
            - 500: 服务器内部错误
    """
    try:
        canvas_id = batch_data.get("canvas_id")
        cards_data = batch_data.get("cards", [])
        
        if not canvas_id or not cards_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="canvas_id and cards list are required"
            )
        
        # 验证画布权限
        canva_service = CanvaService()
        canvas = canva_service.verify_user_permission(db, canvas_id, current_user.id)
        
        # 批量创建卡片
        created_cards = []
        for card_data in cards_data:
            card = card_crud.create(
                db,
                obj_in={
                    "canvas_id": canvas_id,
                    "content_id": card_data.get("content_id"),
                    "position_x": card_data.get("position_x", 0),
                    "position_y": card_data.get("position_y", 0)
                }
            )
            created_cards.append({
                "card_id": card.id,
                "content_id": card.content_id,
                "position_x": card.position_x,
                "position_y": card.position_y
            })
        
        return {
            "canvas_id": canvas_id,
            "created_count": len(created_cards),
            "cards": created_cards,
            "message": f"Successfully created {len(created_cards)} cards"
        }
        
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except CanvaNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/pull", response_model=List[CardResponse])
async def pull_canvas(
    request: CanvaPullRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    拉取画布的当前状态
    
    获取指定画布的所有卡片及其位置和内容信息。
    用户必须有权限访问该画布。
    
    Args:
        request: 包含画布ID的请求
        current_user: 当前认证用户
        db: 数据库会话
        
    Returns:
        List[CardResponse]: 画布中所有卡片的列表
        
    Raises:
        HTTPException: 
            - 404: 画布不存在
            - 403: 用户无权限访问画布
            - 500: 服务器内部错误
    """
    try:
        # 初始化画布服务
        canva_service = CanvaService()
        
        # 验证用户权限（同时验证画布是否存在）
        canvas = canva_service.verify_user_permission(
            db,
            request.canva_id,
            current_user.id
        )
        
        # 获取画布卡片数据
        cards = card_crud.get_by_canvas(db, canvas_id=request.canva_id)
        
        # 转换为响应格式
        card_responses = []
        for card in cards:
            card_response = CardResponse(
                card_id=card.id,
                position={
                    "x": card.position_x,
                    "y": card.position_y
                },
                content_id=card.content_id
            )
            card_responses.append(card_response)
        
        return card_responses
        
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except CanvaNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except CanvaServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/push", status_code=status.HTTP_200_OK)
async def push_canvas(
    request: CanvaPushRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    推送画布更新
    
    更新画布中卡片的位置和状态。支持批量更新操作。
    用户必须有权限修改该画布。
    
    Args:
        request: 包含画布ID和卡片更新数据的请求
        current_user: 当前认证用户
        db: 数据库会话
        
    Returns:
        dict: 成功响应消息
        
    Raises:
        HTTPException:
            - 400: 请求数据格式错误
            - 403: 用户无权限修改画布
            - 404: 画布或卡片不存在
            - 500: 服务器内部错误
    """
    try:
        # 初始化画布服务
        canva_service = CanvaService()
        
        # 验证用户权限（同时验证画布是否存在）
        canvas = canva_service.verify_user_permission(
            db,
            request.canva_id,
            current_user.id
        )
        
        # 处理卡片更新和创建
        created_cards = []
        updated_cards = []
        
        for card_update in request.cards:
            if card_update.card_id is None:
                # 创建新卡片
                new_card_data = {
                    "canvas_id": request.canva_id,
                    "position_x": card_update.position.x,
                    "position_y": card_update.position.y,
                    "content_id": card_update.content_id,
                    "user_id": current_user.id
                }
                new_card = card_crud.create(db, obj_in=new_card_data)
                created_cards.append(new_card.id)
            else:
                # 更新现有卡片
                card = card_crud.get(db, id=card_update.card_id)
                if not card:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Card with id {card_update.card_id} not found"
                    )
                if card.canvas_id != request.canva_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Card {card_update.card_id} does not belong to canvas {request.canva_id}"
                    )
                
                # 验证内容访问权限（如果有content_id）
                if card_update.content_id is not None:
                    canva_service.verify_content_access(
                        db,
                        card_update.content_id,
                        current_user.id
                    )
                
                # 更新卡片
                update_data = {
                    "position_x": card_update.position.x,
                    "position_y": card_update.position.y
                }
                if card_update.content_id is not None:
                    update_data["content_id"] = card_update.content_id
                
                card_crud.update(db, db_obj=card, obj_in=update_data)
                updated_cards.append(card_update.card_id)
        
        # 更新画布的修改时间
        canvas_crud.update(
            db,
            db_obj=canvas,
            obj_in={"updated_at": "now()"}
        )
        
        return {
            "message": "Canvas updated successfully",
            "canvas_id": request.canva_id,
            "created_cards": created_cards,
            "updated_cards": updated_cards,
            "total_processed": len(request.cards)
        }
        
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，无法访问该画布"
        )
    except CanvaNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="画布不存在"
        )
    except CanvaServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="画布服务错误，请稍后重试"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请求数据格式错误"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务器内部错误，请稍后重试"
        )


@router.get("/info/{canvas_id}")
async def get_canvas_info(
    canvas_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取画布基本信息
    
    获取画布的基本信息，包括名称、所有者、创建时间等。
    用户必须有权限访问该画布。
    
    Args:
        canvas_id: 画布ID
        current_user: 当前认证用户
        db: 数据库会话
        
    Returns:
        dict: 画布基本信息
        
    Raises:
        HTTPException:
            - 403: 用户无权限访问画布
            - 404: 画布不存在
            - 500: 服务器内部错误
    """
    try:
        # 初始化画布服务
        canva_service = CanvaService()
        
        # 验证用户权限
        canvas = canva_service.verify_user_permission(db, canvas_id, current_user.id)
        
        # 获取画布信息
        canvas_info = {
            "canvas_id": canvas.id,
            "name": canvas.name,
            "owner_id": str(canvas.owner_id),
            "created_at": canvas.created_at.isoformat(),
            "updated_at": canvas.updated_at.isoformat()
        }
        
        return canvas_info
        
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except CanvaNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except CanvaServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/create", response_model=dict)
async def create_canvas(
    canvas_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建新画布
    
    为当前用户创建一个新的画布。
    
    Args:
        canvas_data: 画布创建数据，包含name字段
        current_user: 当前认证用户
        db: 数据库会话
        
    Returns:
        dict: 创建的画布信息
        
    Raises:
        HTTPException:
            - 400: 请求数据格式错误
            - 500: 服务器内部错误
    """
    try:
        # 创建画布
        canvas_create = CanvasCreate(name=canvas_data.get("name", "新画布"))
        canvas = canvas_crud.create(
            db,
            obj_in=canvas_create,
            owner_id=current_user.id
        )
        
        return {
            "canvas_id": canvas.id,
            "name": canvas.name,
            "owner_id": str(canvas.owner_id),
            "created_at": canvas.created_at.isoformat(),
            "updated_at": canvas.updated_at.isoformat(),
            "message": "Canvas created successfully"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete("/delete/{canvas_id}")
async def delete_canvas(
    canvas_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除画布
    
    删除指定的画布及其所有卡片。只有画布所有者可以删除。
    
    Args:
        canvas_id: 画布ID
        current_user: 当前认证用户
        db: 数据库会话
        
    Returns:
        dict: 删除结果
        
    Raises:
        HTTPException:
            - 403: 用户无权限删除画布
            - 404: 画布不存在
            - 500: 服务器内部错误
    """
    try:
        # 验证画布所有权
        canvas = canvas_crud.get_by_owner_and_id(db, current_user.id, canvas_id)
        if not canvas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Canvas {canvas_id} not found or access denied"
            )
        
        # 删除画布中的所有卡片
        deleted_cards_count = card_crud.delete_by_canvas(db, canvas_id)
        
        # 删除画布
        canvas_crud.delete(db, canvas_id)
        
        return {
            "message": "Canvas deleted successfully",
            "canvas_id": canvas_id,
            "deleted_cards_count": deleted_cards_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.put("/update/{canvas_id}")
async def update_canvas(
    canvas_id: int,
    canvas_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新画布信息
    
    更新画布的基本信息，如名称等。只有画布所有者可以更新。
    
    Args:
        canvas_id: 画布ID
        canvas_data: 更新数据
        current_user: 当前认证用户
        db: 数据库会话
        
    Returns:
        dict: 更新后的画布信息
        
    Raises:
        HTTPException:
            - 403: 用户无权限更新画布
            - 404: 画布不存在
            - 500: 服务器内部错误
    """
    try:
        # 验证画布所有权
        canvas = canvas_crud.get_by_owner_and_id(db, current_user.id, canvas_id)
        if not canvas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Canvas {canvas_id} not found or access denied"
            )
        
        # 更新画布
        updated_canvas = canvas_crud.update(db, canvas, canvas_data)
        
        return {
            "canvas_id": updated_canvas.id,
            "name": updated_canvas.name,
            "owner_id": str(updated_canvas.owner_id),
            "created_at": updated_canvas.created_at.isoformat(),
            "updated_at": updated_canvas.updated_at.isoformat(),
            "message": "Canvas updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )