# Django標準ライブラリ
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# サードパーティライブラリ
import json
import logging
import stripe

# ローカルインポート
from .models import Question
from .forms import FileUploadForm
from .services import (
    QuestionGenerationOrchestrator, 
    SignupValidator, 
    UserCreationService,
    LoginValidator,
    AuthenticationService,
    QuestionSimilarityChecker,
    QuestionRetrievalService,
    QuestionParser,
    AnswerValidationService,
    QuestionUpdateService,
    UserStatisticsService,
    AnswerContextBuilder,
    ExplanationRetrievalService,
    ExplanationContextBuilder,
    ProfileContextBuilder,
    ThemeRetrievalService,
    KeywordQuestionsContextBuilder,
    QuestionSetService,
    PlanPriceMapper,
    StripeWebhookValidator,
    CheckoutSessionService,
    StripeWebhookHandler,
)

# ロガー設定（モジュールレベルで定義）
logger = logging.getLogger(__name__)

# Userモデル取得（モジュールレベルで定義）
User = get_user_model()

class SignupView(View):
    """
    サインアップビュー
    """
    
    def dispatch(self, request, *args, **kwargs):
        """
        認証済みユーザーはリダイレクト
        """
        if request.user.is_authenticated:
            return redirect('generate')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        """
        GETリクエストの処理
        """
        return render(request, 'signup.html')
    
    def post(self, request):
        """
        POSTリクエストの処理
        """
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        
        # バリデーション
        is_valid, error_message = SignupValidator.validate_signup_data(
            email, password, password_confirm
        )
        
        if not is_valid:
            return render(request, 'signup.html', {'error_message': error_message})
        
        # ユーザー作成とログイン
        user = UserCreationService.create_and_login_user(request, email, password)
        
        if user:
            return redirect('generate')
        
        # ユーザー作成に失敗した場合
        return render(request, 'signup.html', {
            'error_message': 'ユーザーの作成に失敗しました。'
        })


class LoginView(View):
    """
    ログインビュー
    """
    
    def dispatch(self, request, *args, **kwargs):
        """
        認証済みユーザーはリダイレクト
        """
        if request.user.is_authenticated:
            return redirect('generate')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        """
        GETリクエストの処理
        """
        return render(request, 'login.html')
    
    def post(self, request):
        """
        POSTリクエストの処理
        """
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        # バリデーション
        is_valid, error_message = LoginValidator.validate_login_data(email, password)
        
        if not is_valid:
            return render(request, 'login.html', {'error_message': error_message})
        
        # 認証とログイン
        user = AuthenticationService.authenticate_and_login(request, email, password)
        
        if user:
            return redirect('generate')
        
        # 認証失敗
        return render(request, 'login.html', {
            'error_message': 'メールアドレスまたはパスワードが正しくありません。'
        })


class LogoutView(View):
    """
    ログアウトビュー
    """
    
    def post(self, request):
        """
        POSTリクエストでログアウト
        """
        logout(request)
        return redirect('login')
    
    def get(self, request):
        """
        GETリクエストでもログアウト可能
        """
        logout(request)
        return redirect('login')


@method_decorator(login_required, name='dispatch')
class QuestionView(View):
    """
    問題表示ビュー
    """
    
    def get(self, request, keyword, question_number):
        """
        GETリクエストの処理
        """
        return self._handle_request(request, keyword, question_number)
    
    def post(self, request, keyword, question_number):
        """
        POSTリクエストの処理
        """
        return self._handle_request(request, keyword, question_number)
    
    def _handle_request(self, request, keyword, question_number):
        """
        リクエスト処理の共通ロジック
        """
        # GETリクエストの場合、retryはURLパラメータから取得
        if request.method == 'GET':
            is_retry = request.GET.get('retry', 'false') == 'true'
            question_text = request.GET.get('question_text', '')
            question_id = request.GET.get('question_id', '')
        else:
            is_retry = request.POST.get('retry', 'false') == 'true'
            question_text = request.POST.get('question_text', '')
            question_id = request.POST.get('question_id', '')
        
        # 問題取得
        all_questions = QuestionRetrievalService.get_questions(
            request, keyword, is_retry, question_text, question_id
        )
        
        # 問題が存在しない場合のエラーハンドリング
        question_count = len(all_questions) if isinstance(all_questions, list) else all_questions.count()
        if question_count == 0:
            logger.error(f"No questions found for keyword: {keyword}, is_retry: {is_retry}, question_text: {question_text[:50] if question_text else 'None'}")
            # 問題一覧にリダイレクト
            if is_retry:
                return redirect('keyword_questions', keyword=keyword)
            else:
                return redirect('generate')
        
        # 現在の問題を取得（エラーハンドリング付き）
        try:
            current_question = QuestionRetrievalService.get_current_question(
                all_questions, question_number - 1, is_retry, question_id
            )
        except IndexError as e:
            logger.error(f"IndexError in get_current_question: {e}, question_number: {question_number}, total: {question_count}")
            # 問題一覧にリダイレクト
            if is_retry:
                return redirect('keyword_questions', keyword=keyword)
            else:
                return redirect('generate')
        
        # セッションから取得した場合、question_textを更新
        if isinstance(all_questions, list):
            question_text = current_question['question_text']
            question_id = current_question.get('question_id', question_id)
        else:
            # QuerySetの場合
            question_text = current_question.question_text
            question_id = current_question.id
        
        # 問題解析
        main_question, options = QuestionParser.parse_question(question_text)
        
        # コンテキスト構築
        context = QuestionParser.build_context(
            main_question=main_question,
            options=options,
            question_text=question_text,
            keyword=keyword,
            question_number=question_number,
            question_id=question_id,
            all_questions=all_questions,
            is_retry=is_retry
        )
        
        return render(request, 'question.html', context)


@method_decorator(login_required, name='dispatch')
class IndexView(View):
    """
    インデックスビュー
    """
    
    def get(self, request):
        """
        GETリクエストの処理
        """
        user = request.user
        context = {
            'daily_generated_count': user.daily_generated_count,
            'is_premium': user.is_premium
        }
        return render(request, 'index.html', context)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class GenerateQuestionView(View):
    """
    問題生成ビュー
    """
    
    def _get_orchestrator(self):
        """
        オーケストレーターを取得
        """
        return QuestionGenerationOrchestrator()
    
    def post(self, request):
        """
        POSTリクエストの処理
        """
        form = FileUploadForm(request.POST, request.FILES)
        
        # ファイルアップロードの場合
        if form.is_valid() and request.FILES.get('file'):
            return self._handle_file_upload(request, form)
        
        # テキスト入力の場合
        return self._handle_text_input(request)
    
    def _handle_file_upload(self, request, form):
        """
        ファイルアップロード処理
        """
        try:
            uploaded_file = form.cleaned_data['file']
            orchestrator = self._get_orchestrator()
            theme, error_message = orchestrator.generate_from_file(
                request, request.user, uploaded_file
            )
            
            if error_message:
                return render(request, 'index.html', {'error_message': error_message})
            
            return redirect('question', keyword=theme, question_number=1)
        
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    def _handle_text_input(self, request):
        """
        テキスト入力処理
        """
        try:
            theme = request.POST.get('theme', '').replace('　', ' ')
            difficulty = request.POST.get('difficulty', 'medium')
            
            orchestrator = self._get_orchestrator()
            theme, error_message = orchestrator.generate_from_text(
                request, request.user, theme, difficulty
            )
            
            if error_message:
                return render(request, 'index.html', {'error_message': error_message})
            
            return redirect('question', keyword=theme, question_number=1)
        
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class AnswerQuestionView(View):
    """
    回答処理ビュー
    """
    
    def post(self, request, keyword, question_number):
        """
        POSTリクエストの処理
        """
        try:
            user_answer = request.POST.get('answer', '')
            is_retry = request.POST.get('retry', 'false') == 'true'
            question_text = request.POST.get('question_text', '')
            question_id = request.POST.get('question_id', '')
            
            # 問題取得
            all_questions, question_text, question_id = self._get_question_data(
                request, keyword, question_number, is_retry, question_text, question_id
            )
            
            # AIによる回答判定
            correct_option, explanation_text, _ = AnswerValidationService.check_answer_with_ai(
                question_text, user_answer
            )
            
            # 正誤判定
            is_correct = AnswerValidationService.is_correct(user_answer, correct_option)
            
            # Questionモデルを更新
            is_first = QuestionUpdateService.update_question(
                question_id, is_correct, correct_option, explanation_text
            )
            
            # ユーザー統計を更新
            UserStatisticsService.update_statistics(request.user, is_first, is_correct)
            
            # コンテキスト構築
            context = AnswerContextBuilder.build_context(
                question_text=question_text,
                keyword=keyword,
                question_number=question_number,
                question_id=question_id,
                total_questions=len(all_questions) if isinstance(all_questions, list) else all_questions.count(),
                is_correct=is_correct,
                explanation_text=explanation_text,
                correct_option=correct_option,
                is_retry='True' if is_retry else 'False',
                user_answer=user_answer
            )
            
            return render(request, 'answer.html', context)
        
        except IndexError as e:
            logger.error(f"IndexError in answer_question: {e}")
            if is_retry:
                return redirect('keyword_questions', keyword=keyword)
            else:
                return redirect('generate')
        except Exception as e:
            logger.error(f"Error in answer_question: {e}")
            return JsonResponse({"error": str(e)}, status=500)
    
    def _get_question_data(self, request, keyword, question_number, is_retry, question_text, question_id):
        """
        問題データを取得
        """
        # 問題取得
        all_questions = QuestionRetrievalService.get_questions(
            request, keyword, is_retry, question_text, question_id
        )
        
        # 問題が存在しない場合のエラーハンドリング
        question_count = len(all_questions) if isinstance(all_questions, list) else all_questions.count()
        if question_count == 0:
            raise IndexError(f"No questions found for keyword: {keyword}")
        
        # 現在の問題を取得
        try:
            current_question = QuestionRetrievalService.get_current_question(
                all_questions, question_number - 1, is_retry, question_id
            )
        except IndexError as e:
            logger.error(f"IndexError in get_current_question: {e}")
            raise
        
        # セッションから取得した場合とQuerySetの場合で処理を分ける
        if isinstance(all_questions, list):
            # セッションから取得した場合
            question_text = current_question['question_text']
            question_id = current_question.get('question_id', question_id)
        else:
            # QuerySetの場合
            question_text = current_question.question_text
            question_id = current_question.id
        
        return all_questions, question_text, question_id


@method_decorator(login_required, name='dispatch')
class ProfileView(View):
    """
    プロフィールビュー
    """
    
    def get(self, request):
        """
        GETリクエストの処理
        """
        context = ProfileContextBuilder.build_context(request.user)
        return render(request, 'profile.html', context)

@method_decorator(login_required, name='dispatch')
class AllKeywordView(View):
    """
    全キーワードビュー
    """
    
    def get(self, request):
        """
        GETリクエストの処理
        """
        search_query = request.GET.get('search', '')
        sort_option = request.GET.get('sort', 'alphabetical')
        
        # テーマ取得
        user_themes_list = ThemeRetrievalService.get_user_themes(
            request.user, search_query, sort_option
        )
        
        return render(request, 'allkeyword.html', {'user_themes': user_themes_list})

class AllQuestionView(View):
    """
    全問題ビュー
    """
    
    def get(self, request):
        """
        GETリクエストの処理
        """
        return render(request, 'allquestion.html')

@method_decorator(login_required, name='dispatch')
class KeywordQuestionsView(View):
    """
    キーワード問題ビュー
    """
    
    def get(self, request, keyword):
        """
        GETリクエストの処理
        """
        filter_option = request.GET.get('filter', 'all')
        
        # コンテキスト構築
        context = KeywordQuestionsContextBuilder.build_context(
            request.user, keyword, filter_option
        )
        
        return render(request, 'keyword_questions.html', context)

@method_decorator(login_required, name='dispatch')
class ExplanationView(View):
    """
    解説表示ビュー
    """
    
    def post(self, request, keyword, question_number):
        """
        POSTリクエストの処理
        """
        try:
            question_id = request.POST.get('question_id', '')
            is_retry = request.POST.get('retry', '')
            
            # 問題と解説を取得
            question = ExplanationRetrievalService.get_question_with_explanation(
                request.user, question_id
            )
            
            # コンテキスト構築
            context = ExplanationContextBuilder.build_context(
                question, keyword, question_number, is_retry
            )
            
            return render(request, 'answer.html', context)
        
        except Question.DoesNotExist:
            logger.error(f"Question not found: {question_id}")
            return JsonResponse({"error": "問題が見つかりませんでした。"}, status=404)
        except ValueError as e:
            logger.error(f"Explanation not found: {e}")
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            logger.error(f"Error in explanation_view: {e}")
            return JsonResponse({"error": str(e)}, status=500)

@method_decorator(login_required, name='dispatch')
class KeywordHistoryView(View):
    """
    キーワード履歴ビュー
    """
    
    def get(self, request):
        """
        GETリクエストの処理
        """
        # キーワードリストを取得
        keywords = ThemeRetrievalService.get_user_keywords(request.user)
        return JsonResponse({'keywords': list(keywords)})

@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """
    Stripe Webhookビュー
    """
    
    def post(self, request):
        """
        POSTリクエストの処理
        """
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        
        # Webhook署名を検証
        event, error = StripeWebhookValidator.verify_signature(payload, sig_header)
        if error:
            return HttpResponse(status=400)
        
        # イベントタイプに応じて処理を分岐
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            StripeWebhookHandler.handle_checkout_session(session)
        
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            StripeWebhookHandler.handle_subscription_deleted(subscription)
        
        elif event['type'] == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            StripeWebhookHandler.handle_invoice_payment_succeeded(invoice)
        
        return HttpResponse(status=200)

@method_decorator(login_required, name='dispatch')
class CreateCheckoutSessionView(View):
    """
    チェックアウトセッション作成ビュー
    """
    
    def post(self, request, plan):
        """
        POSTリクエストの処理
        """
        # プランから価格IDを取得
        price_id = PlanPriceMapper.get_price_id(plan)
        if not price_id:
            logger.error(f"Invalid plan requested: {plan}")
            return HttpResponse("Invalid plan", status=400)
        
        # ドメイン設定（ローカル開発環境の場合。デプロイ先では適宜変更）
        domain = "http://localhost:8001"
        success_url = domain + reverse('success')
        cancel_url = domain + reverse('cancel')
        
        # チェックアウトセッションを作成
        checkout_session, error = CheckoutSessionService.create_session(
            user_email=request.user.email,
            price_id=price_id,
            domain=domain,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        if error:
            if isinstance(error, stripe.error.InvalidRequestError):
                return HttpResponse(f"Stripe error: {error.user_message}", status=400)
            return HttpResponse("An unexpected error occurred.", status=500)
        
        return redirect(checkout_session.url, code=303)

class SuccessView(View):
    """
    支払い成功ビュー
    """
    
    def get(self, request):
        """
        GETリクエストの処理
        """
        return render(request, 'success.html')


class CancelView(View):
    """
    支払いキャンセルビュー
    """
    
    def get(self, request):
        """
        GETリクエストの処理
        """
        return render(request, 'plans.html')

@method_decorator(login_required, name='dispatch')
class PlansView(View):
    """
    プラン一覧ビュー
    """
    
    def get(self, request):
        """
        GETリクエストの処理
        """
        return render(request, 'plans.html')

@method_decorator(csrf_exempt, name='dispatch')
class AddToQuestionSetView(View):
    """
    問題セット追加ビュー
    """
    
    def post(self, request):
        """
        POSTリクエストの処理
        """
        try:
            data = json.loads(request.body)
            question_texts = data.get('questions', [])
            collection_ids = data.get('collections', [])
            
            # 複数の問題セットに問題を追加
            QuestionSetService.add_to_multiple_sets(collection_ids, question_texts)
            
            return JsonResponse({'success': True})
        except ValueError as e:
            logger.error(f"Error adding to questionset: {e}")
            return JsonResponse({'success': False}, status=404)
        except Exception as e:
            logger.error(f"Unexpected error in add_to_questionset: {e}")
            return JsonResponse({'success': False}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class CreateQuestionSetView(View):
    """
    問題セット作成ビュー
    """
    
    def post(self, request):
        """
        POSTリクエストの処理
        """
        try:
            data = json.loads(request.body)
            name = data.get('name')
            description = data.get('description')
            author = data.get('author')
            publisher = data.get('publisher')
            question_texts = data.get('questions', [])
            
            # 問題セットを作成し、問題を追加
            QuestionSetService.create_questionset(
                user=request.user,
                name=name,
                description=description,
                author=author,
                publisher=publisher,
                question_texts=question_texts
            )
            
            return JsonResponse({'success': True})
        except Exception as e:
            logger.error(f"Error creating questionset: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)