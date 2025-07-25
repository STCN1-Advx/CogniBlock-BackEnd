from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.api.v2.auth import get_current_user, require_canvas_access, require_canvas_owner
from app.schemas.canva import (
    CanvaPullRequest, 
    CardResponse, 
    CardUpdateRequest,
    CanvaPushRequest,
    ErrorResponse
)
from app.schemas.user import User
from app.services.canva_service import CanvaService, CanvaServiceError, PermissionDeniedError, CanvaNotFoundError
from app.crud import canvas as canvas_crud, card as card_crud

router = APIRouter()


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
        canva_service = CanvaService(db)
        
        # 验证画布是否存在
        canvas = canvas_crud.get(db, id=request.canva_id)
        if not canvas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Canvas with id {request.canva_id} not found"
            )
        
        # 验证用户权限
        await canva_service.verify_user_permission(
            canvas_id=request.canva_id,
            user_id=current_user.id,
            permission_type="read"
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
        canva_service = CanvaService(db)
        
        # 验证画布是否存在
        canvas = canvas_crud.get(db, id=request.canva_id)
        if not canvas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Canvas with id {request.canva_id} not found"
            )
        
        # 验证用户权限（需要写权限）
        await canva_service.verify_user_permission(
            canvas_id=request.canva_id,
            user_id=current_user.id,
            permission_type="write"
        )
        
        # 验证所有卡片都属于该画布
        for card_update in request.cards:
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
        
        # 验证数据一致性
        await canva_service.validate_card_data_consistency(request.cards)
        
        # 批量更新卡片
        update_data = []
        for card_update in request.cards:
            # 验证内容访问权限
            await canva_service.verify_content_access(
                content_id=card_update.content_id,
                user_id=current_user.id
            )
            
            update_data.append({
                "card_id": card_update.card_id,
                "position_x": card_update.position.x,
                "position_y": card_update.position.y,
                "content_id": card_update.content_id
            })
        
        # 执行批量更新
        for update in update_data:
            card_crud.update(
                db,
                db_obj=card_crud.get(db, id=update["card_id"]),
                obj_in={
                    "position_x": update["position_x"],
                    "position_y": update["position_y"],
                    "content_id": update["content_id"]
                }
            )
        
        # 更新画布的修改时间
        canvas_crud.update(
            db,
            db_obj=canvas,
            obj_in={"updated_at": "now()"}
        )
        
        return {
            "message": "Canvas updated successfully",
            "canvas_id": request.canva_id,
            "updated_cards": len(request.cards)
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
    except CanvaServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Service error: {str(e)}"
        )
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
        canva_service = CanvaService(db)
        
        # 获取画布信息
        canvas_info = await canva_service.get_canva_info(
            canvas_id=canvas_id,
            user_id=current_user.id
        )
        
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