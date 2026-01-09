"""
プロフィールに関連するサービスクラス
"""
from ..models import Question


class ProfileStatisticsService:
    """プロフィール統計取得の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def get_user_statistics(user):
        """
        ユーザーの統計情報を取得
        """
        return {
            'correct_count': user.correct_count,
            'generate_count': user.generate_count,
            'accuracy': round(user.accuracy, 1) if user.accuracy else 0.0,
            'not_answered_count': user.not_answered_count,
        }


class KeywordAnalyzer:
    """キーワード分析の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def get_favorite_keyword(user):
        """
        最も多いキーワードを取得
        """
        user_questions = Question.objects.filter(user=user)
        
        # キーワードの集計
        keyword_counts = {}
        for question in user_questions:
            keyword = question.theme
            if keyword in keyword_counts:
                keyword_counts[keyword] += 1
            else:
                keyword_counts[keyword] = 1
        
        # 最も多いキーワードを取得
        return max(keyword_counts, key=keyword_counts.get) if keyword_counts else "なし"


class ProfileContextBuilder:
    """プロフィールコンテキスト構築の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def build_context(user):
        """
        プロフィール表示用のコンテキストを構築
        """
        statistics = ProfileStatisticsService.get_user_statistics(user)
        favorite_keyword = KeywordAnalyzer.get_favorite_keyword(user)
        
        return {
            **statistics,
            'favorite_keyword': favorite_keyword,
        }


class ThemeRetrievalService:
    """テーマ取得の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def get_user_themes(user, search_query=None, sort_option='alphabetical'):
        """
        ユーザーのテーマを取得（検索・ソート対応）
        """
        from django.db.models import Count
        
        # テーマごとの問題数をカウント
        user_themes = Question.objects.filter(user=user).values('theme').annotate(count=Count('theme'))
        
        # 検索フィルタリング
        if search_query:
            user_themes = user_themes.filter(theme__icontains=search_query)
        
        # 並び替え
        if sort_option == 'count':
            user_themes = user_themes.order_by('-count')
        else:
            user_themes = user_themes.order_by('theme')
        
        # テーマ名とその問題数のリストに変換
        return [{'theme': theme['theme'], 'count': theme['count']} for theme in user_themes]
    
    @staticmethod
    def get_user_keywords(user):
        """
        ユーザーのキーワード（テーマ）リストを取得（重複なし）
        """
        return Question.objects.filter(user=user).values_list('theme', flat=True).distinct()
