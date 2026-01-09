"""
支払い・Stripeに関連するサービスクラス
"""
import logging
import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from ..models import Subscription

logger = logging.getLogger(__name__)
User = get_user_model()


class PlanPriceMapper:
    """プランと価格IDのマッピングの責務（Single Responsibility Principle）"""
    
    PLAN_PRICE_MAP = {
        'basic': 'price_1QWgzYRsfW3rHLql8AgXGsxq',
        'premium': 'price_1QWh03RsfW3rHLqlJwmfjxTP',
    }
    
    PRICE_PLAN_MAP = {
        'price_1QWgzYRsfW3rHLql8AgXGsxq': 'basic',
        'price_1QWh03RsfW3rHLqlJwmfjxTP': 'premium',
    }
    
    @classmethod
    def get_price_id(cls, plan):
        """
        プラン名から価格IDを取得
        """
        return cls.PLAN_PRICE_MAP.get(plan)
    
    @classmethod
    def get_plan_from_price_id(cls, price_id):
        """
        価格IDからプラン名を取得
        """
        return cls.PRICE_PLAN_MAP.get(price_id, 'basic')


class StripeWebhookValidator:
    """Stripe Webhook署名検証の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def verify_signature(payload, sig_header):
        """
        Webhook署名を検証
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            logger.info(f"Received event: {event['type']}")
            return event, None
        except ValueError as e:
            logger.error("Invalid payload")
            return None, ValueError("Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error("Invalid signature")
            return None, stripe.error.SignatureVerificationError("Invalid signature")


class CheckoutSessionService:
    """チェックアウトセッション作成の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def create_session(user_email, price_id, domain, success_url, cancel_url):
        """
        Stripeチェックアウトセッションを作成
        """
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                customer_email=user_email,
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
            )
            logger.info(f"Checkout session created: {checkout_session.id}")
            return checkout_session, None
        except stripe.error.InvalidRequestError as e:
            logger.error(f"Stripe InvalidRequestError: {e.user_message}")
            return None, stripe.error.InvalidRequestError(e.user_message, param=None)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return None, Exception(str(e))


class SubscriptionService:
    """サブスクリプション操作の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def get_user_by_email(email):
        """
        メールアドレスからユーザーを取得
        """
        try:
            return User.objects.get(email=email), None
        except User.DoesNotExist:
            logger.error(f"User with email {email} does not exist.")
            return None, ValueError(f"User with email {email} does not exist.")
    
    @staticmethod
    def get_user_by_customer_id(customer_id):
        """
        Stripe顧客IDからユーザーを取得
        """
        try:
            return User.objects.get(subscription__stripe_customer_id=customer_id), None
        except User.DoesNotExist:
            logger.error(f"User with customer ID {customer_id} does not exist.")
            return None, ValueError(f"User with customer ID {customer_id} does not exist.")
    
    @staticmethod
    def create_or_update_subscription(user, customer_id, subscription_id, plan):
        """
        サブスクリプションを作成または更新
        """
        subscription, created = Subscription.objects.get_or_create(user=user)
        subscription.stripe_customer_id = customer_id
        subscription.stripe_subscription_id = subscription_id
        subscription.active = True
        subscription.plan = plan
        subscription.save()
        logger.info(f"Subscription saved: {subscription}")
        return subscription
    
    @staticmethod
    def determine_plan_from_subscription(subscription_id):
        """
        サブスクリプションIDからプランを判定
        """
        subscription = stripe.Subscription.retrieve(subscription_id)
        price_id = subscription['items']['data'][0]['price']['id']
        return PlanPriceMapper.get_plan_from_price_id(price_id)


class UserPremiumService:
    """ユーザープレミアム状態更新の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def set_premium(user, customer_id=None):
        """
        ユーザーをプレミアムに設定
        """
        user.is_premium = True
        if customer_id:
            user.stripe_customer_id = customer_id
        user.save()
        logger.info(f"User {user.username} is_premium set to True.")
    
    @staticmethod
    def remove_premium(user):
        """
        ユーザーのプレミアムを解除
        """
        user.is_premium = False
        user.save()
        logger.info(f"User {user.username} is_premium set to False.")


class StripeWebhookHandler:
    """Stripe Webhookイベント処理の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def handle_checkout_session(session):
        """
        チェックアウトセッション完了時の処理
        """
        customer_email = session.get('customer_email')
        logger.info(f"Handling checkout session for email: {customer_email}")
        
        if not customer_email:
            logger.error("No customer_email found in session.")
            return
        
        user, error = SubscriptionService.get_user_by_email(customer_email)
        if error:
            return
        
        logger.info(f"Found user: {user.username}")
        
        subscription_id = session.get('subscription')
        logger.info(f"Subscription ID: {subscription_id}")
        
        if not subscription_id:
            logger.error("No subscription ID found in session.")
            return
        
        # プランを判定
        plan = SubscriptionService.determine_plan_from_subscription(subscription_id)
        
        # サブスクリプションを作成または更新
        SubscriptionService.create_or_update_subscription(
            user, session.get('customer'), subscription_id, plan
        )
        
        # ユーザーのstripe_customer_idを更新
        user.stripe_customer_id = session.get('customer')
        user.save()
        
        # ユーザーをプレミアムに設定
        UserPremiumService.set_premium(user)
    
    @staticmethod
    def handle_subscription_deleted(subscription):
        """
        サブスクリプション削除時の処理
        """
        customer_id = subscription.get('customer')
        
        user, error = SubscriptionService.get_user_by_customer_id(customer_id)
        if error:
            return
        
        logger.info(f"Found user: {user.username} for subscription deletion.")
        
        # ユーザーのプレミアムを解除
        UserPremiumService.remove_premium(user)
    
    @staticmethod
    def handle_invoice_payment_succeeded(invoice):
        """
        支払い成功時の処理
        """
        logger.info("Payment succeeded for invoice: " + invoice.get('id'))
        
        customer_id = invoice.get('customer')
        if not customer_id:
            logger.error("No customer ID found in invoice.")
            return
        
        user, error = SubscriptionService.get_user_by_customer_id(customer_id)
        if error:
            return
        
        logger.info(f"Found user: {user.username} for invoice payment.")
        
        # ユーザーのstripe_customer_idを更新し、プレミアムに設定
        UserPremiumService.set_premium(user, customer_id)
