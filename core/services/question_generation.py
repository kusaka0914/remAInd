"""
問題生成に関連するサービスクラス
"""
from django.utils import timezone
from difflib import SequenceMatcher
from PIL import Image
import PyPDF2
import openai
from ..models import Question


class QuestionSimilarityChecker:
    """問題の類似度チェックの責務（Single Responsibility Principle）"""
    
    @staticmethod
    def is_similar(new_question, past_questions, threshold=0.4):
        """
        問題の類似度をチェックする
        """
        for past_question in past_questions:
            similarity = SequenceMatcher(None, new_question, past_question.question_text).ratio()
            if similarity > threshold:
                return True
        return False


class FileProcessor:
    """ファイル処理の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def extract_text_from_image(uploaded_file):
        """
        画像ファイルからテキストを抽出
        """
        image = Image.open(uploaded_file)
        width, height = image.size
        # TODO: 実際のOCR処理を実装（現在はサイズ情報のみ）
        return f"画像のサイズは{width}x{height}です。"
    
    @staticmethod
    def extract_text_from_pdf(uploaded_file):
        """
        PDFファイルからテキストを抽出
        """
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        extracted_text = ""
        for page in pdf_reader.pages:
            extracted_text += page.extract_text()
        return extracted_text
    
    @staticmethod
    def process_file(uploaded_file):
        """
        ファイルタイプに応じて適切な処理を実行
        """
        file_type = uploaded_file.content_type
        
        if file_type.startswith('image/'):
            return FileProcessor.extract_text_from_image(uploaded_file)
        elif file_type == 'application/pdf':
            return FileProcessor.extract_text_from_pdf(uploaded_file)
        else:
            raise ValueError(f"サポートされていないファイルタイプ: {file_type}")


class PremiumLimitChecker:
    """プレミアム制限チェックの責務（Single Responsibility Principle）"""
    
    DAILY_LIMIT = 10
    
    @staticmethod
    def can_generate(user):
        """
        ユーザーが問題を生成できるかチェック
        """
        if user.is_premium:
            return True, None
        
        today = timezone.now().date()
        
        # 日付が変わった場合、カウントをリセット
        if user.last_generated_date != today:
            user.last_generated_date = today
            user.daily_generated_count = 0
            user.save()
        
        # 制限チェック
        if user.daily_generated_count >= PremiumLimitChecker.DAILY_LIMIT:
            return False, "1日に生成できる問題数の上限に達しました。"
        
        return True, None
    
    @staticmethod
    def update_daily_count(user, question_count):
        """
        日次カウントを更新（プレミアムユーザーでない場合のみ）
        """
        if not user.is_premium:
            user.daily_generated_count += question_count
            user.save()


class PromptBuilder:
    """プロンプト生成の責務（Single Responsibility Principle）"""
    
    DIFFICULTY_LEVEL_MAP = {
        'basic': '初級レベル',
        'intermediate': '中級レベル',
        'advanced': '上級レベル',
        'super_advanced': '超上級レベル',
        'master': '最上級レベル'
    }
    
    @staticmethod
    def build_file_prompt(extracted_text):
        """
        ファイルアップロード用のプロンプトを生成
        """
        theme = extracted_text[:10]
        prompt = f"次のテキストを読み、実用的な4択問題を10個作成してください。:{extracted_text}正解はまだ表示しないでください。"
        system_content = "問題の選択肢は (A)選択肢の内容 (B)選択肢の内容 (C)選択肢の内容 (D)選択肢の内容 という形で出力してください。"
        return prompt, system_content, theme
    
    @staticmethod
    def build_text_prompt(theme, difficulty='medium'):
        """
        テキスト入力用のプロンプトを生成
        """
        level = PromptBuilder.DIFFICULTY_LEVEL_MAP.get(difficulty, '上級')
        prompt = f"""{theme}に関する、実用的な4択問題を10個作成してください。
        作成する問題の難易度は{level}です。
        しっかりとこのレベルの問題を作成してください。
        選択肢は(A)~(D)の4つです。
        正解はまだ表示しないでください。"""
        system_content = "問題はきちんと1~10の順番で出力してください。"
        return prompt, system_content


class QuestionGenerationOrchestrator:
    """問題生成のオーケストレーション（Dependency Inversion Principle）"""
    
    def generate_from_file(self, request, user, uploaded_file):
        """
        ファイルから問題を生成
        """
        # ファイル処理
        extracted_text = FileProcessor.process_file(uploaded_file)
        
        # プロンプト生成
        prompt, system_content, theme = PromptBuilder.build_file_prompt(extracted_text)
        
        # 問題生成
        valid_questions = QuestionGenerator.generate_and_validate(
            prompt=prompt,
            system_content=system_content,
            past_questions=None,
            max_questions=10
        )
        
        # バリデーション
        if len(valid_questions) < 10:
            return None, "有効な問題を生成できませんでした。別のキーワードでお試しください。"
        
        # 保存
        QuestionPersistenceService.save_to_session(request, user, valid_questions, theme)
        
        return theme, None
    
    def generate_from_text(self, request, user, theme, difficulty):
        """
        テキスト入力から問題を生成
        """
        # プレミアム制限チェック
        can_generate, error_message = PremiumLimitChecker.can_generate(user)
        if not can_generate:
            return None, error_message
        
        # 過去の質問取得
        past_questions = Question.objects.filter(user=user, theme=theme)[:20]
        
        # プロンプト生成
        prompt, system_content = PromptBuilder.build_text_prompt(theme, difficulty)
        
        # 問題生成
        valid_questions = QuestionGenerator.generate_and_validate(
            prompt=prompt,
            system_content=system_content,
            past_questions=past_questions,
            max_questions=10
        )
        
        # バリデーション
        if len(valid_questions) < 10:
            return None, "有効な問題を生成できませんでした。別のキーワードでお試しください。"
        
        # 日次カウント更新
        PremiumLimitChecker.update_daily_count(user, len(valid_questions))
        
        # 保存
        QuestionPersistenceService.save_to_session(request, user, valid_questions, theme, difficulty)
        
        return theme, None


class QuestionGenerator:
    """問題生成と検証の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def generate_and_validate(prompt, system_content, past_questions=None, max_questions=10, max_attempts=5):
        """
        問題生成と検証
        """
        attempt = 0
        valid_questions = []
        
        while attempt < max_attempts and len(valid_questions) < max_questions:
            attempt += 1
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt}
                ]
            )
            questions_data_all = response.choices[0].message.content.strip()
            questions_data = questions_data_all.split('\n\n')
            
            for question_data in questions_data:
                lines = question_data.split('\n')
                non_empty_lines = [line for line in lines if line.strip() != '']
                if len(non_empty_lines) < 5:
                    continue
                
                main_question = lines[0].strip()
                if not main_question or len(main_question) < 10:
                    continue
                
                # 類似度チェック（過去の質問がある場合のみ）
                if past_questions and QuestionSimilarityChecker.is_similar(main_question, past_questions):
                    continue
                
                valid_questions.append(question_data)
                
                if len(valid_questions) >= max_questions:
                    break
            
            if len(valid_questions) >= max_questions:
                break
        
        return valid_questions


class QuestionPersistenceService:
    """問題の永続化の責務（Single Responsibility Principle）"""
    
    @staticmethod
    def save_to_session(request, user, valid_questions, theme, difficulty=None):
        """
        問題をセッションとDBに保存する
        """
        request.session['all_questions'] = []
        
        for i, question_data in enumerate(valid_questions[:10], 1):
            question_kwargs = {
                'user': user,
                'theme': theme,
                'question_text': question_data,
                'question_number': i,
            }
            if difficulty:
                question_kwargs['difficulty'] = difficulty
            
            question = Question.objects.create(**question_kwargs)
            
            request.session['all_questions'].append({
                'question_id': question.id,
                'question_text': question_data,
                'theme': theme,
                'question_number': i
            })
        
        request.session.modified = True
        user.generate_count += len(valid_questions)
        user.save()


