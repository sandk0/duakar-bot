import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text, case
from decimal import Decimal
import json

from database.models import (
    User, Subscription, Payment, VPNConfig, 
    UsageStats, ReferralStats, ActionLog
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Advanced analytics and reporting service"""
    
    async def get_conversion_funnel(self, session: AsyncSession) -> Dict[str, Any]:
        """Get user conversion funnel analytics"""
        try:
            # Total registered users
            total_users_result = await session.execute(
                select(func.count(User.id))
            )
            total_users = total_users_result.scalar()
            
            # Users who started trial
            trial_users_result = await session.execute(
                select(func.count(User.id.distinct())).select_from(
                    User.__table__.join(Subscription.__table__)
                ).where(Subscription.is_trial == True)
            )
            trial_users = trial_users_result.scalar()
            
            # Users who made first payment
            paid_users_result = await session.execute(
                select(func.count(User.id.distinct())).select_from(
                    User.__table__.join(Payment.__table__)
                ).where(Payment.status == 'completed')
            )
            paid_users = paid_users_result.scalar()
            
            # Users with active subscription
            active_users_result = await session.execute(
                select(func.count(User.id.distinct())).select_from(
                    User.__table__.join(Subscription.__table__)
                ).where(
                    and_(
                        Subscription.status == 'active',
                        Subscription.end_date > datetime.utcnow()
                    )
                )
            )
            active_users = active_users_result.scalar()
            
            # Calculate conversion rates
            trial_conversion = (trial_users / total_users * 100) if total_users > 0 else 0
            payment_conversion = (paid_users / trial_users * 100) if trial_users > 0 else 0
            retention_rate = (active_users / paid_users * 100) if paid_users > 0 else 0
            
            return {
                'funnel_stages': {
                    'registered': total_users,
                    'trial_started': trial_users,
                    'first_payment': paid_users,
                    'active_subscription': active_users
                },
                'conversion_rates': {
                    'registration_to_trial': round(trial_conversion, 2),
                    'trial_to_payment': round(payment_conversion, 2),
                    'payment_to_active': round(retention_rate, 2),
                    'overall_conversion': round((active_users / total_users * 100) if total_users > 0 else 0, 2)
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating conversion funnel: {e}")
            return {}
    
    async def get_cohort_analysis(
        self, 
        session: AsyncSession,
        months: int = 6
    ) -> Dict[str, Any]:
        """Get user cohort analysis"""
        try:
            cohort_data = {}
            current_date = date.today()
            
            for i in range(months):
                cohort_month = current_date.replace(day=1) - timedelta(days=32*i)
                cohort_month = cohort_month.replace(day=1)
                next_month = (cohort_month.replace(day=28) + timedelta(days=4)).replace(day=1)
                
                # Users registered in this cohort
                cohort_users_result = await session.execute(
                    select(func.count(User.id)).where(
                        and_(
                            User.created_at >= cohort_month,
                            User.created_at < next_month
                        )
                    )
                )
                cohort_size = cohort_users_result.scalar()
                
                if cohort_size == 0:
                    continue
                
                # Calculate retention for each month after
                retention_data = []
                for month_offset in range(6):  # Check 6 months of retention
                    check_date = next_month + timedelta(days=32*month_offset)
                    check_next_month = (check_date.replace(day=28) + timedelta(days=4)).replace(day=1)
                    
                    # Users from cohort still active in this month
                    active_users_result = await session.execute(
                        select(func.count(User.id.distinct())).select_from(
                            User.__table__.join(Subscription.__table__)
                        ).where(
                            and_(
                                User.created_at >= cohort_month,
                                User.created_at < next_month,
                                Subscription.status == 'active',
                                Subscription.end_date >= check_date,
                                Subscription.end_date < check_next_month
                            )
                        )
                    )
                    active_users = active_users_result.scalar()
                    
                    retention_rate = (active_users / cohort_size * 100) if cohort_size > 0 else 0
                    retention_data.append({
                        'month': month_offset,
                        'active_users': active_users,
                        'retention_rate': round(retention_rate, 2)
                    })
                
                cohort_data[cohort_month.strftime('%Y-%m')] = {
                    'cohort_size': cohort_size,
                    'retention': retention_data
                }
            
            return cohort_data
            
        except Exception as e:
            logger.error(f"Error calculating cohort analysis: {e}")
            return {}
    
    async def get_revenue_analytics(
        self, 
        session: AsyncSession,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get detailed revenue analytics"""
        try:
            start_date = date.today() - timedelta(days=days)
            
            # Daily revenue
            daily_revenue_result = await session.execute(
                select(
                    func.date(Payment.created_at).label('date'),
                    func.sum(Payment.amount).label('revenue'),
                    func.count(Payment.id).label('transactions')
                ).where(
                    and_(
                        Payment.status == 'completed',
                        Payment.created_at >= start_date
                    )
                ).group_by(
                    func.date(Payment.created_at)
                ).order_by('date')
            )
            
            daily_data = []
            total_revenue = Decimal('0')
            total_transactions = 0
            
            for row in daily_revenue_result:
                daily_data.append({
                    'date': row.date.strftime('%Y-%m-%d'),
                    'revenue': float(row.revenue),
                    'transactions': row.transactions
                })
                total_revenue += row.revenue
                total_transactions += row.transactions
            
            # Revenue by payment method
            payment_method_result = await session.execute(
                select(
                    Payment.payment_method,
                    func.sum(Payment.amount).label('revenue'),
                    func.count(Payment.id).label('count')
                ).where(
                    and_(
                        Payment.status == 'completed',
                        Payment.created_at >= start_date
                    )
                ).group_by(Payment.payment_method)
            )
            
            payment_methods = []
            for row in payment_method_result:
                payment_methods.append({
                    'method': row.payment_method or 'Unknown',
                    'revenue': float(row.revenue),
                    'transactions': row.count,
                    'percentage': float(row.revenue / total_revenue * 100) if total_revenue > 0 else 0
                })
            
            # Average revenue per user (ARPU)
            arpu_result = await session.execute(
                select(
                    func.avg(func.sum(Payment.amount)).label('arpu')
                ).select_from(
                    Payment.__table__
                ).where(
                    and_(
                        Payment.status == 'completed',
                        Payment.created_at >= start_date
                    )
                ).group_by(Payment.user_id)
            )
            arpu = arpu_result.scalar() or Decimal('0')
            
            return {
                'summary': {
                    'total_revenue': float(total_revenue),
                    'total_transactions': total_transactions,
                    'average_transaction': float(total_revenue / total_transactions) if total_transactions > 0 else 0,
                    'arpu': float(arpu)
                },
                'daily_revenue': daily_data,
                'payment_methods': payment_methods
            }
            
        except Exception as e:
            logger.error(f"Error calculating revenue analytics: {e}")
            return {}
    
    async def get_user_behavior_analytics(
        self, 
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Get user behavior analytics"""
        try:
            # Usage patterns
            usage_patterns_result = await session.execute(
                select(
                    func.avg(UsageStats.bytes_uploaded + UsageStats.bytes_downloaded).label('avg_usage'),
                    func.percentile_cont(0.5).within_group(
                        UsageStats.bytes_uploaded + UsageStats.bytes_downloaded
                    ).label('median_usage'),
                    func.max(UsageStats.bytes_uploaded + UsageStats.bytes_downloaded).label('max_usage')
                )
            )
            usage_stats = usage_patterns_result.first()
            
            # Active hours analysis (if we track connection times)
            active_hours_result = await session.execute(
                select(
                    func.extract('hour', VPNConfig.last_used_at).label('hour'),
                    func.count(VPNConfig.id).label('connections')
                ).where(
                    VPNConfig.last_used_at >= datetime.utcnow() - timedelta(days=7)
                ).group_by('hour').order_by('hour')
            )
            
            active_hours = []
            for row in active_hours_result:
                active_hours.append({
                    'hour': int(row.hour) if row.hour else 0,
                    'connections': row.connections
                })
            
            # User lifecycle stages
            lifecycle_result = await session.execute(
                select(
                    case(
                        (and_(Subscription.is_trial == True, Subscription.status == 'active'), 'trial'),
                        (and_(Subscription.is_trial == False, Subscription.status == 'active'), 'paid_active'),
                        (Subscription.status == 'expired', 'expired'),
                        (Subscription.status == 'cancelled', 'cancelled'),
                        else_='new'
                    ).label('stage'),
                    func.count(User.id).label('count')
                ).select_from(
                    User.__table__.outerjoin(Subscription.__table__)
                ).group_by('stage')
            )
            
            lifecycle_stages = {}
            for row in lifecycle_result:
                lifecycle_stages[row.stage] = row.count
            
            return {
                'usage_patterns': {
                    'average_usage_gb': round(float(usage_stats.avg_usage or 0) / (1024**3), 2),
                    'median_usage_gb': round(float(usage_stats.median_usage or 0) / (1024**3), 2),
                    'max_usage_gb': round(float(usage_stats.max_usage or 0) / (1024**3), 2)
                },
                'active_hours': active_hours,
                'lifecycle_stages': lifecycle_stages
            }
            
        except Exception as e:
            logger.error(f"Error calculating user behavior analytics: {e}")
            return {}
    
    async def get_churn_analysis(
        self, 
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Get churn analysis"""
        try:
            # Users who churned in the last 30 days
            churn_cutoff = datetime.utcnow() - timedelta(days=30)
            
            churned_users_result = await session.execute(
                select(func.count(Subscription.id)).where(
                    and_(
                        Subscription.status.in_(['expired', 'cancelled']),
                        Subscription.updated_at >= churn_cutoff
                    )
                )
            )
            churned_users = churned_users_result.scalar()
            
            # Total active users at the beginning of period
            active_users_result = await session.execute(
                select(func.count(Subscription.id)).where(
                    and_(
                        Subscription.status == 'active',
                        Subscription.created_at < churn_cutoff
                    )
                )
            )
            active_users_start = active_users_result.scalar()
            
            # Calculate churn rate
            churn_rate = (churned_users / active_users_start * 100) if active_users_start > 0 else 0
            
            # Churn reasons analysis
            churn_reasons_result = await session.execute(
                select(
                    case(
                        (Subscription.status == 'expired', 'Payment Failed/Expired'),
                        (Subscription.status == 'cancelled', 'Voluntary Cancellation'),
                        else_='Unknown'
                    ).label('reason'),
                    func.count(Subscription.id).label('count')
                ).where(
                    and_(
                        Subscription.status.in_(['expired', 'cancelled']),
                        Subscription.updated_at >= churn_cutoff
                    )
                ).group_by('reason')
            )
            
            churn_reasons = []
            for row in churn_reasons_result:
                churn_reasons.append({
                    'reason': row.reason,
                    'count': row.count,
                    'percentage': round(row.count / churned_users * 100, 2) if churned_users > 0 else 0
                })
            
            return {
                'churn_rate': round(churn_rate, 2),
                'churned_users': churned_users,
                'churn_reasons': churn_reasons
            }
            
        except Exception as e:
            logger.error(f"Error calculating churn analysis: {e}")
            return {}
    
    async def generate_comprehensive_report(
        self, 
        session: AsyncSession,
        report_type: str = 'monthly'
    ) -> Dict[str, Any]:
        """Generate comprehensive analytics report"""
        try:
            report = {
                'generated_at': datetime.utcnow().isoformat(),
                'report_type': report_type,
                'period_days': 30 if report_type == 'monthly' else 7
            }
            
            # Get all analytics
            report['conversion_funnel'] = await self.get_conversion_funnel(session)
            report['revenue_analytics'] = await self.get_revenue_analytics(session, report['period_days'])
            report['user_behavior'] = await self.get_user_behavior_analytics(session)
            report['churn_analysis'] = await self.get_churn_analysis(session)
            
            if report_type == 'monthly':
                report['cohort_analysis'] = await self.get_cohort_analysis(session)
            
            # Add executive summary
            report['executive_summary'] = await self._generate_executive_summary(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating comprehensive report: {e}")
            return {}
    
    async def _generate_executive_summary(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary from analytics data"""
        try:
            summary = {}
            
            # Key metrics
            if 'conversion_funnel' in report_data:
                funnel = report_data['conversion_funnel']
                summary['total_users'] = funnel['funnel_stages'].get('registered', 0)
                summary['conversion_rate'] = funnel['conversion_rates'].get('overall_conversion', 0)
            
            if 'revenue_analytics' in report_data:
                revenue = report_data['revenue_analytics']
                summary['total_revenue'] = revenue['summary'].get('total_revenue', 0)
                summary['arpu'] = revenue['summary'].get('arpu', 0)
            
            if 'churn_analysis' in report_data:
                churn = report_data['churn_analysis']
                summary['churn_rate'] = churn.get('churn_rate', 0)
            
            # Insights and recommendations
            insights = []
            
            if summary.get('conversion_rate', 0) < 10:
                insights.append("Conversion rate is below 10% - consider improving onboarding flow")
            
            if summary.get('churn_rate', 0) > 15:
                insights.append("Churn rate is high - focus on retention strategies")
            
            if summary.get('arpu', 0) < 500:  # Assuming RUB currency
                insights.append("ARPU is low - consider upselling opportunities")
            
            summary['insights'] = insights
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {e}")
            return {}