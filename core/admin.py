from django.contrib import admin
from .models import Question, UserProgress, CustomUser, QuestionSet, Subscription


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """
    問題モデルの管理画面設定
    問題の一覧表示と検索機能を提供
    """
    list_display = ('theme', 'question_text', 'correct_option', 'is_correct', 'is_correct_first')
    search_fields = ('theme', 'question_text', 'correct_option', 'is_correct', 'is_correct_first')


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    """
    ユーザー進捗モデルの管理画面設定
    ユーザーの問題復習状況を管理
    """
    list_display = ('user', 'question', 'is_correct', 'review_date')


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    """
    カスタムユーザーモデルの管理画面設定
    ユーザー情報とプレミアムステータスを管理
    """
    list_display = ('email', 'is_premium')
    search_fields = ('email',)


@admin.register(QuestionSet)
class QuestionSetAdmin(admin.ModelAdmin):
    """
    問題セットモデルの管理画面設定
    問題セットの一覧表示と問題一覧を表示
    """
    list_display = ('name', 'user', 'description', 'created_at', 'get_questions')

    def get_questions(self, obj):
        """
        問題セットに含まれる問題の一覧を取得
        
        Args:
            obj: QuestionSetインスタンス
        
        Returns:
            str: 問題文をカンマ区切りで連結した文字列
        """
        return ", ".join([q.question_text for q in obj.questions.all()])
    
    get_questions.short_description = '問題一覧'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """
    サブスクリプションモデルの管理画面設定
    サブスクリプション情報の一覧表示、検索、フィルタリングを提供
    """
    list_display = ('user', 'plan', 'active', 'stripe_customer_id', 'created_at')
    search_fields = ('user__email', 'plan', 'stripe_customer_id')
    list_filter = ('plan', 'active', 'created_at')