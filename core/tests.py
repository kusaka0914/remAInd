from django.test import TestCase
from django.contrib.auth import get_user_model

# モデル
from .models import Question

# 認証関連サービス
from .services.authentication import (
    SignupValidator, 
    LoginValidator, 
    AuthenticationService, 
    UserCreationService
)

# プロフィール関連サービス
from .services.profile import (
    ProfileStatisticsService, 
    KeywordAnalyzer, 
    ThemeRetrievalService
)

# 回答処理関連サービス
from .services.answer_processing import (
    AnswerValidationService, 
    UserStatisticsService
)

# 問題表示関連サービス
from .services.question_display import (
    QuestionFilterService, 
    QuestionTextCleaner, 
    QuestionParser
)

User = get_user_model()

class SignupValidatorTest(TestCase):
    """
    SignupValidatorのテスト
    """
    
    def test_empty_email_is_invalid(self):
        """
        空のメールアドレスでサインアップしようとしたらエラーになるか確認
        """
        # テストデータを準備
        email = ""  # 空
        password = "test1234"
        password_confirm = "test1234"
        
        # バリデーションを実行
        is_valid, error_message = SignupValidator.validate_signup_data(
            email, password, password_confirm
        )
        
        # 結果を確認（期待値: 無効であるべき）
        self.assertFalse(is_valid)  # is_validがFalseであることを確認
        self.assertEqual(error_message, 'すべての項目を入力してください。')
    
    def test_password_mismatch_is_invalid(self):
        """
        パスワードと確認パスワードが違ったらエラーになるか確認
        """
        email = "test@example.com"
        password = "test1234"
        password_confirm = "different1234"  # 違うパスワード
        
        is_valid, error_message = SignupValidator.validate_signup_data(
            email, password, password_confirm
        )
        
        self.assertFalse(is_valid)
        self.assertEqual(error_message, 'パスワードが一致しません。')
    
    def test_duplicate_email_is_invalid(self):
        """
        同じメールアドレスで2回登録しようとしたらエラーになるか確認
        """
        # 最初のユーザーを作成
        User.objects.create_user(
            email="existing@example.com",
            username="existing@example.com",
            password="test1234"
        )
        
        # 同じメールアドレスで再度登録しようとする
        is_valid, error_message = SignupValidator.validate_signup_data(
            "existing@example.com", "test1234", "test1234"
        )
        
        self.assertFalse(is_valid)
        self.assertEqual(error_message, 'このメールアドレスは既に登録されています。')
    
    def test_valid_data_is_accepted(self):
        """
        正しいデータならバリデーションが通るか確認
        """
        email = "new@example.com"
        password = "test1234"
        password_confirm = "test1234"
        
        is_valid, error_message = SignupValidator.validate_signup_data(
            email, password, password_confirm
        )
        
        self.assertTrue(is_valid)  # 有効であるべき
        self.assertIsNone(error_message)  # エラーメッセージはNoneであるべき


class ProfileStatisticsServiceTest(TestCase):
    """
    ProfileStatisticsServiceのテスト
    """
    
    def test_get_user_statistics_returns_correct_values(self):
        """
        ユーザーの統計情報が正しく取得できるか確認
        """
        # テスト用のユーザーを作成
        user = User.objects.create_user(
            email="test@example.com",
            username="test@example.com",
            password="test1234"
        )
        # 統計情報を設定
        user.correct_count = 10
        user.generate_count = 20
        user.accuracy = 50.0
        user.not_answered_count = 5
        user.save()
        
        # 統計情報を取得
        statistics = ProfileStatisticsService.get_user_statistics(user)
        
        # 結果を確認
        self.assertEqual(statistics['correct_count'], 10)
        self.assertEqual(statistics['generate_count'], 20)
        self.assertEqual(statistics['accuracy'], 50.0)
        self.assertEqual(statistics['not_answered_count'], 5)
    
    def test_get_user_statistics_returns_zero_when_accuracy_is_none(self):
        """
        accuracyがNoneの場合、0.0を返すか確認
        """
        user = User.objects.create_user(
            email="test@example.com",
            username="test@example.com",
            password="test1234"
        )
        user.accuracy = None
        user.save()
        
        statistics = ProfileStatisticsService.get_user_statistics(user)
        
        self.assertEqual(statistics['accuracy'], 0.0)


class KeywordAnalyzerTest(TestCase):
    """
    KeywordAnalyzerのテスト
    """
    
    def test_get_favorite_keyword_returns_most_common(self):
        """
        問題が複数ある場合、最も多いキーワードを取得できるか確認
        """
        user = User.objects.create_user(
            email="test@example.com",
            username="test@example.com",
            password="test1234"
        )
        
        # 問題を作成（「Python」が3個、「Django」が2個）
        Question.objects.create(user=user, theme="Python", question_text="問題1")
        Question.objects.create(user=user, theme="Python", question_text="問題2")
        Question.objects.create(user=user, theme="Python", question_text="問題3")
        Question.objects.create(user=user, theme="Django", question_text="問題4")
        Question.objects.create(user=user, theme="Django", question_text="問題5")
        
        # 最も多いキーワードを取得
        favorite_keyword = KeywordAnalyzer.get_favorite_keyword(user)
        
        # 結果を確認（「Python」が最も多いので、それが返されるべき）
        self.assertEqual(favorite_keyword, "Python")
    
    def test_get_favorite_keyword_returns_none_when_no_questions(self):
        """
        問題がない場合、「なし」を返すか確認
        """
        user = User.objects.create_user(
            email="test@example.com",
            username="test@example.com",
            password="test1234"
        )
        # 問題は作成しない
        
        favorite_keyword = KeywordAnalyzer.get_favorite_keyword(user)
        
        self.assertEqual(favorite_keyword, "なし")


class LoginValidatorTest(TestCase):
    """
    LoginValidatorのテスト
    """
    
    def test_empty_email_is_invalid(self):
        """
        空のメールアドレスでログインしようとしたらエラーになるか確認
        """
        email = ""
        password = "test1234"
        
        is_valid, error_message = LoginValidator.validate_login_data(email, password)
        
        self.assertFalse(is_valid)
        self.assertEqual(error_message, 'メールアドレスとパスワードを入力してください。')
    
    def test_empty_password_is_invalid(self):
        """
        空のパスワードでログインしようとしたらエラーになるか確認
        """
        email = "test@example.com"
        password = ""
        
        is_valid, error_message = LoginValidator.validate_login_data(email, password)
        
        self.assertFalse(is_valid)
        self.assertEqual(error_message, 'メールアドレスとパスワードを入力してください。')
    
    def test_valid_data_is_accepted(self):
        """
        正しいデータならバリデーションが通るか確認
        """
        email = "test@example.com"
        password = "test1234"
        
        is_valid, error_message = LoginValidator.validate_login_data(email, password)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error_message)


class AnswerValidationServiceTest(TestCase):
    """
    AnswerValidationServiceのテスト
    """
    
    def test_is_correct_returns_true_when_answers_match(self):
        """
        回答が一致する場合、Trueを返すか確認
        """
        user_answer = "A"
        correct_option = "A"
        
        result = AnswerValidationService.is_correct(user_answer, correct_option)
        
        self.assertTrue(result)
    
    def test_is_correct_returns_false_when_answers_dont_match(self):
        """
        回答が一致しない場合、Falseを返すか確認
        """
        user_answer = "A"
        correct_option = "B"
        
        result = AnswerValidationService.is_correct(user_answer, correct_option)
        
        self.assertFalse(result)
    
    def test_is_correct_is_case_insensitive(self):
        """
        大文字小文字を区別しないか確認
        """
        # 大文字と小文字の組み合わせ
        self.assertTrue(AnswerValidationService.is_correct("a", "A"))
        self.assertTrue(AnswerValidationService.is_correct("A", "a"))
        self.assertTrue(AnswerValidationService.is_correct("b", "B"))
        self.assertTrue(AnswerValidationService.is_correct("B", "b"))


class UserStatisticsServiceTest(TestCase):
    """
    UserStatisticsServiceのテスト
    """
    
    def test_update_statistics_increments_correct_count_on_first_correct(self):
        """
        初回正解の場合、正解数が増えるか確認
        """
        user = User.objects.create_user(
            email="test@example.com",
            username="test@example.com",
            password="test1234"
        )
        user.generate_count = 10
        user.correct_count = 5
        user.save()
        
        UserStatisticsService.update_statistics(user, is_first=True, is_correct=True)
        
        user.refresh_from_db()
        self.assertEqual(user.correct_count, 6)  # 5 + 1 = 6
    
    def test_update_statistics_does_not_increment_on_second_attempt(self):
        """
        2回目の回答では正解数が増えないか確認
        """
        user = User.objects.create_user(
            email="test@example.com",
            username="test@example.com",
            password="test1234"
        )
        user.generate_count = 10
        user.correct_count = 5
        user.save()
        
        UserStatisticsService.update_statistics(user, is_first=False, is_correct=True)
        
        user.refresh_from_db()
        self.assertEqual(user.correct_count, 5)  # 増えない
    
    def test_update_statistics_calculates_accuracy_correctly(self):
        """
        正答率が正しく計算されるか確認
        """
        user = User.objects.create_user(
            email="test@example.com",
            username="test@example.com",
            password="test1234"
        )
        user.generate_count = 10
        user.correct_count = 7
        user.save()
        
        UserStatisticsService.update_statistics(user, is_first=True, is_correct=True)
        
        user.refresh_from_db()
        # 7 + 1 = 8正解、10問中なので80%
        self.assertEqual(user.accuracy, 80.0)
    
    def test_update_not_answered_count_counts_none_questions(self):
        """
        is_correctがNoneの問題数を正しくカウントするか確認
        """
        user = User.objects.create_user(
            email="test@example.com",
            username="test@example.com",
            password="test1234"
        )
        
        # is_correctがNoneの問題を3つ作成
        Question.objects.create(user=user, theme="Python", question_text="問題1", is_correct=None)
        Question.objects.create(user=user, theme="Python", question_text="問題2", is_correct=None)
        Question.objects.create(user=user, theme="Python", question_text="問題3", is_correct=None)
        
        # is_correctが設定されている問題も作成（カウントされない）
        Question.objects.create(user=user, theme="Python", question_text="問題4", is_correct=True)
        
        UserStatisticsService.update_not_answered_count(user)
        
        user.refresh_from_db()
        self.assertEqual(user.not_answered_count, 3)


class QuestionParserTest(TestCase):
    """
    QuestionParserのテスト
    """
    
    def test_parse_question_extracts_main_question(self):
        """
        問題文が正しく抽出されるか確認
        """
        question_text = "Pythonとは何か？\n(A) プログラミング言語\n(B) 動物\n(C) 食べ物\n(D) 国"
        
        main_question, options = QuestionParser.parse_question(question_text)
        
        self.assertEqual(main_question, "Pythonとは何か？")
    
    def test_parse_question_extracts_options(self):
        """
        選択肢が正しく抽出されるか確認
        """
        question_text = "Pythonとは何か？\n(A) プログラミング言語\n(B) 動物\n(C) 食べ物\n(D) 国"
        
        main_question, options = QuestionParser.parse_question(question_text)
        
        self.assertEqual(len(options), 4)
        self.assertEqual(options[0]['letter'], 'A')
        self.assertEqual(options[0]['text'], 'プログラミング言語')
        self.assertEqual(options[1]['letter'], 'B')
        self.assertEqual(options[1]['text'], '動物')
    
    def test_parse_question_handles_empty_question(self):
        """
        空の問題文を処理できるか確認
        """
        question_text = ""
        
        main_question, options = QuestionParser.parse_question(question_text)
        
        self.assertEqual(main_question, "")
        self.assertEqual(len(options), 0)


class QuestionTextCleanerTest(TestCase):
    """
    QuestionTextCleanerのテスト
    """
    
    def test_clean_question_text_removes_prefix_numbers(self):
        """
        問題番号などの接頭辞が削除されるか確認
        """
        text = "問題1: Pythonとは何か？"
        
        cleaned = QuestionTextCleaner.clean_question_text(text)
        
        self.assertEqual(cleaned, "Pythonとは何か？")
    
    def test_clean_question_text_handles_question_mark(self):
        """
        ？で区切られるか確認
        """
        text = "問題1: Pythonとは何か？これは説明です。"
        
        cleaned = QuestionTextCleaner.clean_question_text(text)
        
        self.assertEqual(cleaned, "Pythonとは何か？")
    
    def test_clean_question_text_handles_period(self):
        """
        。で区切られるか確認
        """
        text = "問題1: Pythonとは何か。これは説明です。"
        
        cleaned = QuestionTextCleaner.clean_question_text(text)
        
        self.assertEqual(cleaned, "Pythonとは何か？")


class QuestionFilterServiceTest(TestCase):
    """
    QuestionFilterServiceのテスト
    """
    
    def setUp(self):
        """
        テスト用のユーザーと問題を作成
        """
        self.user = User.objects.create_user(
            email="test@example.com",
            username="test@example.com",
            password="test1234"
        )
        
        # 様々な状態の問題を作成
        Question.objects.create(
            user=self.user,
            theme="Python",
            question_text="問題1",
            is_correct_first=True,
            is_correct=True
        )
        Question.objects.create(
            user=self.user,
            theme="Python",
            question_text="問題2",
            is_correct_first=False,
            is_correct=False
        )
        Question.objects.create(
            user=self.user,
            theme="Python",
            question_text="問題3",
            is_correct_first=None,
            is_correct=None
        )
    
    def test_filter_questions_incorrect_first(self):
        """
        初回不正解の問題をフィルタリングできるか確認
        """
        questions = Question.objects.filter(user=self.user)
        
        filtered = QuestionFilterService.filter_questions(questions, 'incorrect_first')
        
        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first().is_correct_first, False)
    
    def test_filter_questions_correct_first(self):
        """
        初回正解の問題をフィルタリングできるか確認
        """
        questions = Question.objects.filter(user=self.user)
        
        filtered = QuestionFilterService.filter_questions(questions, 'correct_first')
        
        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first().is_correct_first, True)
    
    def test_filter_questions_retry_none(self):
        """
        未回答の問題をフィルタリングできるか確認
        """
        questions = Question.objects.filter(user=self.user)
        
        filtered = QuestionFilterService.filter_questions(questions, 'retry_none')
        
        self.assertEqual(filtered.count(), 1)
        self.assertIsNone(filtered.first().is_correct)
    
    def test_filter_questions_all_returns_all(self):
        """
        'all'オプションで全ての問題が返されるか確認
        """
        questions = Question.objects.filter(user=self.user)
        
        filtered = QuestionFilterService.filter_questions(questions, 'all')
        
        self.assertEqual(filtered.count(), 3)


class ThemeRetrievalServiceTest(TestCase):
    """
    ThemeRetrievalServiceのテスト
    """
    
    def setUp(self):
        """
        テスト用のユーザーと問題を作成
        """
        self.user = User.objects.create_user(
            email="test@example.com",
            username="test@example.com",
            password="test1234"
        )
        
        Question.objects.create(user=self.user, theme="Python", question_text="問題1")
        Question.objects.create(user=self.user, theme="Python", question_text="問題2")
        Question.objects.create(user=self.user, theme="Django", question_text="問題3")
        Question.objects.create(user=self.user, theme="JavaScript", question_text="問題4")
    
    def test_get_user_themes_returns_all_themes(self):
        """
        全てのテーマが取得できるか確認
        """
        themes = ThemeRetrievalService.get_user_themes(self.user)
        
        self.assertEqual(len(themes), 3)
        theme_names = [theme['theme'] for theme in themes]
        self.assertIn('Python', theme_names)
        self.assertIn('Django', theme_names)
        self.assertIn('JavaScript', theme_names)
    
    def test_get_user_themes_counts_questions_per_theme(self):
        """
        テーマごとの問題数が正しくカウントされるか確認
        """
        themes = ThemeRetrievalService.get_user_themes(self.user)
        
        python_theme = next(theme for theme in themes if theme['theme'] == 'Python')
        self.assertEqual(python_theme['count'], 2)
    
    def test_get_user_themes_filters_by_search_query(self):
        """
        検索クエリでフィルタリングできるか確認
        """
        themes = ThemeRetrievalService.get_user_themes(self.user, search_query='Python')
        
        self.assertEqual(len(themes), 1)
        self.assertEqual(themes[0]['theme'], 'Python')
    
    def test_get_user_themes_sorts_by_count(self):
        """
        問題数でソートできるか確認
        """
        themes = ThemeRetrievalService.get_user_themes(self.user, sort_option='count')
        
        # 問題数が多い順にソートされる（Python: 2, Django: 1, JavaScript: 1）
        self.assertEqual(themes[0]['theme'], 'Python')
        self.assertEqual(themes[0]['count'], 2)
    
    def test_get_user_keywords_returns_distinct_keywords(self):
        """
        重複なしのキーワードリストが取得できるか確認
        """
        keywords = ThemeRetrievalService.get_user_keywords(self.user)
        
        self.assertEqual(len(keywords), 3)
        self.assertIn('Python', keywords)
        self.assertIn('Django', keywords)
        self.assertIn('JavaScript', keywords)