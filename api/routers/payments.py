from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime, date

from api.dependencies import get_current_admin_user
from database.connection import get_session as get_db
from database.models import User, Payment, Subscription
from services.payment import PaymentManager, YooKassaProvider, WataProvider

router = APIRouter()


class PaymentStats(BaseModel):
    total_revenue: float
    revenue_today: float
    revenue_month: float
    total_transactions: int
    successful_payments: int
    failed_payments: int
    pending_payments: int


class RefundRequest(BaseModel):
    reason: str
    amount: Optional[float] = None


@router.get("/")
async def get_payments(
    current_admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    payment_system: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None)
) -> Dict[str, Any]:
    """Get payments list with pagination and filtering"""
    try:
        offset = (page - 1) * limit
        
        query = select(Payment).options(
            selectinload(Payment.user),
            selectinload(Payment.subscription)
        )
        
        filters = []
        if status:
            filters.append(Payment.status == status)
        if payment_system:
            filters.append(Payment.payment_system == payment_system)
        if user_id:
            filters.append(Payment.user_id == user_id)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.offset(offset).limit(limit).order_by(Payment.created_at.desc())
        
        result = await session.execute(query)
        payments = result.scalars().all()
        
        count_query = select(func.count(Payment.id))
        if filters:
            count_query = count_query.where(and_(*filters))
        
        total_result = await session.execute(count_query)
        total = total_result.scalar()
        
        payment_list = []
        for payment in payments:
            payment_data = {
                "id": payment.id,
                "user_id": payment.user_id,
                "user": {
                    "telegram_id": payment.user.telegram_id,
                    "username": payment.user.username,
                    "first_name": payment.user.first_name,
                    "last_name": payment.user.last_name
                } if payment.user else None,
                "subscription_id": payment.subscription_id,
                "amount": float(payment.amount),
                "currency": payment.currency,
                "payment_method": payment.payment_method,
                "payment_system": payment.payment_system,
                "status": payment.status,
                "external_payment_id": payment.external_payment_id,
                "description": payment.description,
                "created_at": payment.created_at,
                "updated_at": payment.updated_at
            }
            payment_list.append(payment_data)
        
        return {
            "payments": payment_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payments: {str(e)}"
        )


@router.get("/stats")
async def get_payment_stats(
    current_admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db)
) -> PaymentStats:
    """Get payment statistics"""
    try:
        today = date.today()
        
        total_revenue_query = select(func.sum(Payment.amount)).where(
            Payment.status == "completed"
        )
        total_revenue_result = await session.execute(total_revenue_query)
        total_revenue = float(total_revenue_result.scalar() or 0)
        
        revenue_today_query = select(func.sum(Payment.amount)).where(
            and_(
                Payment.status == "completed",
                func.date(Payment.created_at) == today
            )
        )
        revenue_today_result = await session.execute(revenue_today_query)
        revenue_today = float(revenue_today_result.scalar() or 0)
        
        revenue_month_query = select(func.sum(Payment.amount)).where(
            and_(
                Payment.status == "completed",
                func.extract('year', Payment.created_at) == today.year,
                func.extract('month', Payment.created_at) == today.month
            )
        )
        revenue_month_result = await session.execute(revenue_month_query)
        revenue_month = float(revenue_month_result.scalar() or 0)
        
        total_transactions_query = select(func.count(Payment.id))
        total_transactions_result = await session.execute(total_transactions_query)
        total_transactions = total_transactions_result.scalar()
        
        successful_query = select(func.count(Payment.id)).where(Payment.status == "completed")
        successful_result = await session.execute(successful_query)
        successful_payments = successful_result.scalar()
        
        failed_query = select(func.count(Payment.id)).where(Payment.status == "failed")
        failed_result = await session.execute(failed_query)
        failed_payments = failed_result.scalar()
        
        pending_query = select(func.count(Payment.id)).where(Payment.status == "pending")
        pending_result = await session.execute(pending_query)
        pending_payments = pending_result.scalar()
        
        return PaymentStats(
            total_revenue=total_revenue,
            revenue_today=revenue_today,
            revenue_month=revenue_month,
            total_transactions=total_transactions,
            successful_payments=successful_payments,
            failed_payments=failed_payments,
            pending_payments=pending_payments
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payment stats: {str(e)}"
        )


@router.get("/{payment_id}")
async def get_payment(
    payment_id: int,
    current_admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get specific payment details"""
    try:
        query = select(Payment).options(
            selectinload(Payment.user),
            selectinload(Payment.subscription)
        ).where(Payment.id == payment_id)
        
        result = await session.execute(query)
        payment = result.scalar_one_or_none()
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        return {
            "id": payment.id,
            "user_id": payment.user_id,
            "user": {
                "telegram_id": payment.user.telegram_id,
                "username": payment.user.username,
                "first_name": payment.user.first_name,
                "last_name": payment.user.last_name,
                "created_at": payment.user.created_at
            } if payment.user else None,
            "subscription_id": payment.subscription_id,
            "subscription": {
                "id": payment.subscription.id,
                "plan_type": payment.subscription.plan_type,
                "status": payment.subscription.status,
                "is_trial": payment.subscription.is_trial
            } if payment.subscription else None,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "payment_system": payment.payment_system,
            "status": payment.status,
            "external_payment_id": payment.external_payment_id,
            "description": payment.description,
            "metadata": payment.metadata,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payment: {str(e)}"
        )


@router.post("/{payment_id}/refund")
async def refund_payment(
    payment_id: int,
    refund_request: RefundRequest,
    current_admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Process payment refund"""
    try:
        result = await session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        if payment.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only refund completed payments"
            )
        
        refund_amount = refund_request.amount or payment.amount
        
        if refund_amount > payment.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refund amount cannot exceed payment amount"
            )
        
        try:
            payment_service = PaymentManager()
            
            if payment.payment_system == "yookassa":
                provider = YooKassaProvider()
            elif payment.payment_system == "wata":
                provider = WataProvider()
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Refund not supported for payment system: {payment.payment_system}"
                )
            
            refund_result = await provider.refund_payment(
                payment.external_payment_id,
                float(refund_amount),
                refund_request.reason
            )
            
            if refund_result.get("success"):
                payment.status = "refunded"
                payment.description = f"{payment.description or ''} | Refunded: {refund_request.reason}"
                await session.commit()
                
                return {
                    "message": "Payment refunded successfully",
                    "payment_id": payment_id,
                    "refund_amount": float(refund_amount),
                    "refund_id": refund_result.get("refund_id")
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Refund failed: {refund_result.get('error', 'Unknown error')}"
                )
                
        except Exception as provider_error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Refund processing failed: {str(provider_error)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process refund: {str(e)}"
        )


@router.post("/webhooks/yookassa")
async def yookassa_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Handle YooKassa webhook notifications"""
    try:
        webhook_data = await request.json()
        
        event_type = webhook_data.get("event")
        payment_data = webhook_data.get("object", {})
        external_payment_id = payment_data.get("id")
        
        if not external_payment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing payment ID in webhook"
            )
        
        result = await session.execute(
            select(Payment).where(Payment.external_payment_id == external_payment_id)
        )
        payment = result.scalar_one_or_none()
        
        if not payment:
            return {"status": "ignored", "reason": "Payment not found"}
        
        if event_type == "payment.succeeded":
            payment.status = "completed"
            payment.updated_at = datetime.now()
            await session.commit()
            
            return {"status": "processed", "event": "payment_completed"}
            
        elif event_type == "payment.canceled":
            payment.status = "cancelled"
            payment.updated_at = datetime.now()
            await session.commit()
            
            return {"status": "processed", "event": "payment_cancelled"}
            
        elif event_type == "refund.succeeded":
            payment.status = "refunded"
            payment.updated_at = datetime.now()
            await session.commit()
            
            return {"status": "processed", "event": "payment_refunded"}
        
        return {"status": "ignored", "reason": f"Unhandled event type: {event_type}"}
        
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.post("/webhooks/wata")
async def wata_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Handle Wata webhook notifications"""
    try:
        webhook_data = await request.json()
        
        payment_status = webhook_data.get("status")
        external_payment_id = webhook_data.get("payment_id")
        
        if not external_payment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing payment ID in webhook"
            )
        
        result = await session.execute(
            select(Payment).where(Payment.external_payment_id == external_payment_id)
        )
        payment = result.scalar_one_or_none()
        
        if not payment:
            return {"status": "ignored", "reason": "Payment not found"}
        
        if payment_status == "completed":
            payment.status = "completed"
        elif payment_status == "failed":
            payment.status = "failed"
        elif payment_status == "cancelled":
            payment.status = "cancelled"
        else:
            return {"status": "ignored", "reason": f"Unknown status: {payment_status}"}
        
        payment.updated_at = datetime.now()
        await session.commit()
        
        return {"status": "processed", "payment_status": payment_status}
        
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )