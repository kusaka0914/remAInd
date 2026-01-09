"""
問題セットに関連するサービスクラス
"""
from ..models import Question, QuestionSet


class QuestionSearchTextCleaner:
    """問題検索用テキストクリーニングの責務（Single Responsibility Principle）"""
    
    @staticmethod
    def clean_text(text):
        """
        問題テキストから不要な文字を削除（検索用）
        """
        return text.replace("…", "")


class QuestionSearchService:
    """問題検索の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def find_questions_by_text(question_text):
        """
        問題テキストから問題を検索
        """
        cleaned_text = QuestionSearchTextCleaner.clean_text(question_text)
        return Question.objects.filter(question_text__contains=cleaned_text)


class QuestionSetService:
    """問題セット操作の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def add_questions_to_set(question_set, question_texts):
        """
        問題セットに問題を追加
        """
        for question_text in question_texts:
            questions = QuestionSearchService.find_questions_by_text(question_text)
            question_set.questions.add(*questions)
    
    @staticmethod
    def create_questionset(user, name, description=None, author=None, publisher=None, question_texts=None):
        """
        問題セットを作成し、問題を追加
        """
        question_set = QuestionSet.objects.create(
            user=user,
            name=name,
            description=description,
            author=author,
            publisher=publisher
        )
        
        if question_texts:
            QuestionSetService.add_questions_to_set(question_set, question_texts)
        
        return question_set
    
    @staticmethod
    def add_to_multiple_sets(collection_ids, question_texts):
        """
        複数の問題セットに問題を追加
        """
        for collection_id in collection_ids:
            try:
                question_set = QuestionSet.objects.get(id=collection_id)
                QuestionSetService.add_questions_to_set(question_set, question_texts)
            except QuestionSet.DoesNotExist:
                raise ValueError(f"QuestionSet with id {collection_id} does not exist")
