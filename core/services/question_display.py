"""
問題表示に関連するサービスクラス
"""
import re
from ..models import Question, QuestionSet


class QuestionRetrievalService:
    """
    問題取得の責務（Single Responsibility Principle）
    """
    
    @staticmethod
    def get_questions(request, keyword, is_retry, question_text, question_id=None):
        """
        問題を取得（セッションまたはDBから）
        """
        if is_retry:
            # question_idが提供されている場合、そのIDで直接問題を取得し、同じキーワードの全問題を返す
            if question_id:
                try:
                    # question_idで問題を取得（存在確認）
                    Question.objects.get(id=question_id, user=request.user, theme=keyword)
                    # 同じキーワードの全問題を取得
                    return Question.objects.filter(
                        user=request.user, 
                        theme=keyword
                    ).order_by('id')
                except Question.DoesNotExist:
                    # question_idが見つからない場合、キーワードのみで検索
                    return Question.objects.filter(
                        user=request.user, 
                        theme=keyword
                    ).order_by('id')
            elif question_text:
                # question_textで完全一致検索
                questions = Question.objects.filter(
                    user=request.user, 
                    theme=keyword, 
                    question_text=question_text
                ).order_by('id')
                
                # 完全一致が見つからない場合、部分一致で検索
                if questions.count() == 0:
                    questions = Question.objects.filter(
                        user=request.user, 
                        theme=keyword,
                        question_text__contains=question_text[:50] if len(question_text) > 50 else question_text
                    ).order_by('id')
                
                return questions
            else:
                # question_textがない場合は、キーワードのみで検索
                return Question.objects.filter(
                    user=request.user, 
                    theme=keyword
                ).order_by('id')
        else:
            return request.session.get('all_questions', [])
    
    @staticmethod
    def get_current_question(all_questions, question_index, is_retry, question_id=None):
        """
        現在の問題を取得
        """
        if isinstance(all_questions, list):
            # セッションから取得した場合
            if not all_questions or question_index < 0 or question_index >= len(all_questions):
                raise IndexError(f"Question index {question_index} is out of range. Total questions: {len(all_questions)}")
            return all_questions[question_index]
        else:
            # QuerySetの場合（再挑戦時）
            count = all_questions.count()
            if count == 0:
                raise IndexError(f"No questions found. Total questions: {count}")
            
            # question_idが提供されている場合、そのIDで問題を見つける
            if question_id and is_retry:
                try:
                    # question_idで問題を直接取得
                    question = Question.objects.get(id=question_id)
                    # all_questionsの中に含まれているか確認
                    questions_list = list(all_questions)
                    for idx, q in enumerate(questions_list):
                        if q.id == int(question_id):
                            return q
                    # 見つからない場合、直接取得した問題を返す
                    return question
                except (Question.DoesNotExist, ValueError):
                    # question_idが見つからない場合、インデックスで取得
                    if question_index < 0 or question_index >= count:
                        raise IndexError(f"Question index {question_index} is out of range. Total questions: {count}")
                    questions_list = list(all_questions)
                    return questions_list[question_index]
            else:
                # question_idがない場合、インデックスで取得
                if question_index < 0 or question_index >= count:
                    raise IndexError(f"Question index {question_index} is out of range. Total questions: {count}")
                questions_list = list(all_questions)
                return questions_list[question_index]


class QuestionParser:
    """問題解析の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def parse_question(question_text):
        """
        問題文と選択肢を分離・解析
        """
        lines = question_text.split('\n')
        main_question = lines[0] if lines else ""
        
        # 選択肢を抽出 ((A)~(D))
        options = []
        for line in lines[1:]:  # 2行目以降から選択肢を探す
            if line.strip().startswith('(') and ')' in line:
                option_letter = line[1:line.index(')')].strip()
                option_text = line[line.index(')')+1:].strip()
                option_letter = option_letter.replace('(', '').replace(')', '')
                options.append({
                    'letter': option_letter,
                    'text': option_text
                })
        
        return main_question, options
    
    @staticmethod
    def build_context(
        main_question, 
        options, 
        question_text, 
        keyword, 
        question_number, 
        question_id, 
        all_questions, 
        is_retry
    ):
        """
        コンテキストを構築
        """
        return {
            'question': main_question,
            'options': options,
            'question_text': question_text,
            'keyword': keyword,
            'question_number': question_number,
            'question_id': question_id,
            'total_questions': len(all_questions),
            'has_next': question_number < len(all_questions),
            'has_previous': question_number > 1,
            'next_number': question_number + 1,
            'previous_number': question_number - 1,
            'is_retry': is_retry,
        }


class QuestionFilterService:
    """問題フィルタリングの責務（Single Responsibility Principle）"""
    
    @staticmethod
    def filter_questions(questions, filter_option):
        """
        フィルター条件に基づいて問題をフィルタリング
        """
        if filter_option == 'incorrect_first':
            return questions.filter(is_correct_first=False)
        elif filter_option == 'correct_first':
            return questions.filter(is_correct_first=True)
        elif filter_option == 'incorrect_second':
            return questions.filter(is_correct=False)
        elif filter_option == 'correct_second':
            return questions.filter(is_correct=True)
        elif filter_option == 'retry_none':
            return questions.filter(is_correct=None)
        else:
            return questions


class QuestionTextCleaner:
    """問題テキストクリーニングの責務（Single Responsibility Principle）"""
    
    @staticmethod
    def clean_question_text(text):
        """
        問題テキストから番号などを削除
        """
        # 最初の数字、記号、文字を削除（正規表現で一括処理）
        cleaned_text = re.sub(r'^[問題0-9:\.]+', '', text).strip()
        
        # ？または。で区切る
        if '？' in cleaned_text:
            cleaned_text = cleaned_text.split('？')[0].strip() + '？'
        elif '。' in cleaned_text:
            cleaned_text = cleaned_text.split('。')[0].strip() + '？'
        
        return cleaned_text
    
    @staticmethod
    def clean_questions(questions):
        """
        問題リストをクリーニング
        """
        cleaned_questions = []
        for question in questions:
            cleaned_text = QuestionTextCleaner.clean_question_text(question.question_text)
            cleaned_questions.append({
                'original_text': question.question_text,
                'text': cleaned_text,
                'question_number': question.question_number,
                'is_correct_first': question.is_correct_first,
                'is_correct': question.is_correct,
                'question_id': question.id
            })
        return cleaned_questions


class KeywordQuestionsContextBuilder:
    """キーワード問題コンテキスト構築の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def build_context(user, keyword, filter_option='all'):
        """
        キーワード問題表示用のコンテキストを構築
        """
        # QuestionSetの取得
        question_sets = QuestionSet.objects.filter(user=user)
        
        # キーワードに基づいて問題を取得
        questions = Question.objects.filter(user=user, theme=keyword)
        
        # フィルタリング
        questions = QuestionFilterService.filter_questions(questions, filter_option)
        
        # テキストクリーニング
        cleaned_questions = QuestionTextCleaner.clean_questions(questions)
        
        return {
            'questions': cleaned_questions,
            'keyword': keyword,
            'user': user,
            'question_sets': question_sets,
        }
