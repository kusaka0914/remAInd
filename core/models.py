from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser


class Question(models.Model):
    """
    問題モデル
    ユーザーが生成した問題とその回答状況を管理
    """
    # 必須フィールド
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="questions"
    )
    theme = models.CharField(max_length=255, verbose_name="テーマ")
    question_text = models.TextField(verbose_name="問題文")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    
    # オプショナルフィールド
    correct_option = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="正解選択肢"
    )
    is_correct = models.BooleanField(
        null=True, 
        blank=True, 
        verbose_name="正解かどうか（再挑戦時）"
    )
    is_correct_first = models.BooleanField(
        null=True, 
        blank=True, 
        verbose_name="初回正解かどうか"
    )
    explanation = models.TextField(
        null=True, 
        blank=True, 
        verbose_name="解説"
    )
    question_number = models.IntegerField(
        default=1, 
        null=True, 
        blank=True, 
        verbose_name="問題番号"
    )
    difficulty = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="難易度"
    )

    class Meta:
        verbose_name = "問題"
        verbose_name_plural = "問題"
        ordering = ['-created_at']

    def __str__(self):
        return self.question_text


class UserProgress(models.Model):
    """
    ユーザーの進捗モデル
    問題の復習状況を管理（現在は未使用の可能性あり）
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="progress"
    )
    question = models.ForeignKey(
        Question, 
        on_delete=models.CASCADE
    )
    is_correct = models.BooleanField(verbose_name="正解かどうか")
    review_date = models.DateTimeField(verbose_name="復習日時")

    class Meta:
        verbose_name = "ユーザー進捗"
        verbose_name_plural = "ユーザー進捗"
        ordering = ['-review_date']

    def __str__(self):
        return f"{self.user.username} - {self.question.question_text}"


class CustomUser(AbstractUser):
    """
    カスタムユーザーモデル
    ユーザーの統計情報とプレミアム情報を管理
    """
    # プレミアム関連
    is_premium = models.BooleanField(
        default=False, 
        verbose_name="プレミアム会員かどうか"
    )
    stripe_customer_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Stripe顧客ID"
    )
    
    # 統計情報
    correct_count = models.IntegerField(
        default=0, 
        null=True, 
        blank=True, 
        verbose_name="正解数"
    )
    generate_count = models.IntegerField(
        default=0, 
        null=True, 
        blank=True, 
        verbose_name="生成問題数"
    )
    accuracy = models.FloatField(
        default=0, 
        null=True, 
        blank=True, 
        verbose_name="正答率"
    )
    not_answered_count = models.IntegerField(
        default=0, 
        null=True, 
        blank=True, 
        verbose_name="未回答問題数"
    )
    
    # 日次生成制限関連
    last_generated_date = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="最終生成日"
    )
    daily_generated_count = models.IntegerField(
        default=0, 
        verbose_name="日次生成数"
    )

    class Meta:
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"

    def __str__(self):
        return self.username


class QuestionSet(models.Model):
    """
    問題セットモデル
    複数の問題をグループ化して管理
    """
    # 必須フィールド
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="question_sets"
    )
    name = models.CharField(max_length=255, verbose_name="セット名")
    questions = models.ManyToManyField(
        Question, 
        related_name="question_sets", 
        verbose_name="問題"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="作成日時"
    )
    
    # オプショナルフィールド
    description = models.TextField(
        null=True, 
        blank=True, 
        verbose_name="説明"
    )
    author = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="著者"
    )
    publisher = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="出版社"
    )

    class Meta:
        verbose_name = "問題セット"
        verbose_name_plural = "問題セット"
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Subscription(models.Model):
    """
    サブスクリプションモデル
    Stripe経由のサブスクリプション情報を管理
    """
    PLAN_CHOICES = [
        ('basic', 'ベーシックプラン'),
        ('premium', 'プレミアムプラン'),
    ]

    # 必須フィールド
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    plan = models.CharField(
        max_length=50, 
        choices=PLAN_CHOICES, 
        verbose_name="プラン"
    )
    active = models.BooleanField(
        default=False, 
        verbose_name="有効かどうか"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="作成日時"
    )
    
    # オプショナルフィールド
    stripe_customer_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Stripe顧客ID"
    )
    stripe_subscription_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="StripeサブスクリプションID"
    )

    class Meta:
        verbose_name = "サブスクリプション"
        verbose_name_plural = "サブスクリプション"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.plan}"