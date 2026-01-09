"""
認証に関連するサービスクラス
"""
from django.contrib.auth import get_user_model, authenticate, login
from django.contrib.auth.hashers import make_password


class SignupValidator:
    """サインアップバリデーションの責務（Single Responsibility Principle）"""
    
    @staticmethod
    def validate_signup_data(email, password, password_confirm):
        """
        サインアップデータのバリデーション
        """
        # 空チェック
        if not email or not password or not password_confirm:
            return False, 'すべての項目を入力してください。'
        
        # パスワード一致チェック
        if password != password_confirm:
            return False, 'パスワードが一致しません。'
        
        # メール重複チェック
        User = get_user_model()
        if User.objects.filter(email=email).exists():
            return False, 'このメールアドレスは既に登録されています。'
        
        return True, None


class LoginValidator:
    """ログインバリデーションの責務（Single Responsibility Principle）"""
    
    @staticmethod
    def validate_login_data(email, password):
        """
        ログインデータのバリデーション
        """
        if not email or not password:
            return False, 'メールアドレスとパスワードを入力してください。'
        return True, None


class AuthenticationService:
    """認証とログインの責務（Single Responsibility Principle）"""
    
    @staticmethod
    def authenticate_and_login(request, email, password):
        """
        ユーザーを認証してログインする
        """
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return user
        return None


class UserCreationService:
    """ユーザー作成とログインの責務（Single Responsibility Principle）"""
    
    @staticmethod
    def create_and_login_user(request, email, password):
        """
        ユーザーを作成してログインする
        """
        User = get_user_model()
        
        # ユーザー作成
        user = User.objects.create(
            email=email,
            username=email,
            password=make_password(password)
        )
        
        # 認証とログイン（backend属性を設定するため）
        return AuthenticationService.authenticate_and_login(request, email, password)
