from django.urls import path
from . import views

urlpatterns = [
    # ============================================
    # 認証関連
    # ============================================
    path('', views.LoginView.as_view(), name='root'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('signup/', views.SignupView.as_view(), name='signup'),
    
    # ============================================
    # 問題生成関連
    # ============================================
    path('generate/', views.IndexView.as_view(), name='generate'),
    path('generate_question/', views.GenerateQuestionView.as_view(), name='generate_question'),
    
    # ============================================
    # 問題表示・回答関連
    # ============================================
    path('question/<str:keyword>/<int:question_number>/', views.QuestionView.as_view(), name='question'),
    path('answer/<str:keyword>/<int:question_number>/', views.AnswerQuestionView.as_view(), name='answer'),
    path('explanation/<str:keyword>/<int:question_number>/', views.ExplanationView.as_view(), name='explanation'),
    
    # ============================================
    # プロフィール・キーワード関連
    # ============================================
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('allkeyword/', views.AllKeywordView.as_view(), name='allkeyword'),
    path('allquestion/', views.AllQuestionView.as_view(), name='allquestion'),
    path('keywords/<str:keyword>/', views.KeywordQuestionsView.as_view(), name='keyword_questions'),
    path('keyword_history/', views.KeywordHistoryView.as_view(), name='keyword_history'),
    
    # ============================================
    # 問題セット関連
    # ============================================
    path('add-to-questionset/', views.AddToQuestionSetView.as_view(), name='add_to_questionset'),
    path('create-questionset/', views.CreateQuestionSetView.as_view(), name='create_questionset'),
    
    # ============================================
    # 支払い・サブスクリプション関連
    # ============================================
    path('plans/', views.PlansView.as_view(), name='plans'),
    path('checkout/<str:plan>/', views.CreateCheckoutSessionView.as_view(), name='create_checkout_session'),
    path('success/', views.SuccessView.as_view(), name='success'),
    path('cancel/', views.CancelView.as_view(), name='cancel'),
    path('webhook/', views.StripeWebhookView.as_view(), name='stripe_webhook'),
]