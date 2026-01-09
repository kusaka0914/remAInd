"""
回答処理に関連するサービスクラス
"""
import openai
import re
from ..models import Question


class AnswerValidationService:
    """AIによる回答判定の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def check_answer_with_ai(question_text, user_answer):
        """
        AIを使用してユーザーの回答を判定し、正解と解説を取得する
        """
        system_content = """
        正解は必ず(A)〜(D)の中から1つ選んでください。
        以下の形式で出力してください：
        正解:(A/B/C/D)
        解説:解説内容

        【重要】解説の文字数制限：
        - 解説は必ず180文字以上200文字以内で出力してください。
        - この制限を厳守してください。200文字を超える場合は、内容を簡潔にまとめてください。
        - 文字数を数えて確認してから出力してください。
        """

        check_prompt = f"""
        問題: {question_text}
        ユーザーの回答: {user_answer}
        
        この回答が正しいかどうかを判定し、解説を提供してください。
        """
        
        check_response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": check_prompt}
            ]
        )
        
        explanation = check_response.choices[0].message.content.strip()
        
        # 説明文から正解と解説を抽出
        correct_option = None
        explanation_text = ""
        
        for line in explanation.split('\n'):
            if line.startswith('正解:'):
                correct_option = re.sub(r'正解:|[()]', '', line).strip()
            elif line.startswith('解説:'):
                explanation_text = line.replace('解説:', '').strip()
        
        return correct_option, explanation_text, explanation
    
    @staticmethod
    def is_correct(user_answer, correct_option):
        """
        正誤を判定（大文字小文字を区別しない）
        """
        return user_answer.upper() == correct_option.upper()


class QuestionUpdateService:
    """Questionモデル更新の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def update_question(question_id, is_correct, correct_option, explanation_text):
        """
        Questionモデルを更新
        """
        question = Question.objects.get(id=question_id)
        
        # 初回回答か再回答かを判定
        if question.is_correct_first is None:
            question.is_correct_first = is_correct
            is_first = True
        else:
            question.is_correct = is_correct
            is_first = False
        
        question.correct_option = correct_option
        question.explanation = explanation_text
        question.save()
        
        return is_first


class UserStatisticsService:
    """ユーザー統計更新の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def update_statistics(user, is_first, is_correct):
        """
        ユーザーの統計を更新
        """
        # 初回正解の場合、正解数を増やす
        if is_first and is_correct:
            user.correct_count += 1
        
        # 正答率を更新
        if user.generate_count > 0:
            user.accuracy = user.correct_count / user.generate_count * 100
        
        user.save()
    
    @staticmethod
    def update_not_answered_count(user):
        """
        未回答問題数を更新
        """
        # is_correctがNoneの質問をフィルタリング
        not_answered_questions = Question.objects.filter(user=user, is_correct=None)
        
        # カウントを計算
        not_answered_count = not_answered_questions.count()
        
        # ユーザーオブジェクトを更新
        user.not_answered_count = not_answered_count
        user.save()


class AnswerContextBuilder:
    """回答コンテキスト構築の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def build_context(
        question_text,
        keyword,
        question_number,
        question_id,
        total_questions,
        is_correct,
        explanation_text,
        correct_option,
        is_retry,
        user_answer
    ):
        """
        回答表示用のコンテキストを構築
        """
        is_retry_bool = is_retry == 'True' if isinstance(is_retry, str) else bool(is_retry)
        
        return {
            'question': question_text,
            'keyword': keyword,
            'question_number': question_number,
            'total_questions': total_questions,
            'has_next': question_number < total_questions,
            'next_number': question_number + 1,
            'is_correct': is_correct,
            'question_id': question_id,
            'explanation': explanation_text,
            'correct_option': correct_option,
            'is_retry': is_retry,
            'user_answer': user_answer,
            'show_back_link': not is_retry_bool,  # 再挑戦時は非表示
            'show_user_answer': True,
            'show_images': True,
            'show_next_button': not is_retry_bool,  # 再挑戦時は非表示
        }


class ExplanationRetrievalService:
    """解説取得の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def get_question_with_explanation(user, question_id):
        """
        問題と解説を取得
        """
        question = Question.objects.get(id=question_id, user=user)
        
        if not question.explanation:
            raise ValueError("解説がまだ生成されていません。")
        
        return question


class ExplanationContextBuilder:
    """解説表示コンテキスト構築の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def build_context(question, keyword, question_number, is_retry):
        """
        解説表示用のコンテキストを構築
        """
        # 正誤判定（初回回答があればそれを使用、なければ再回答を使用）
        is_correct = question.is_correct_first if question.is_correct_first is not None else question.is_correct
        
        return {
            'question': question.question_text,
            'keyword': keyword,
            'question_number': question_number,
            'total_questions': 1,
            'has_next': False,
            'next_number': question_number + 1,
            'is_correct': is_correct,
            'question_id': question.id,
            'explanation': question.explanation,
            'correct_option': question.correct_option,
            'is_retry': 'True' if is_retry else '',
            'user_answer': '',
            'show_back_link': False,
            'show_user_answer': False,
            'show_images': False,
            'show_next_button': False,
        }
