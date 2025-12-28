from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'reviews'

urlpatterns = [
    # صفحه اصلی و لیست اساتید
    path('', views.home, name='home'),
    
    # صفحه پروفایل استاد (حالا شامل ارزیابی و نمودار هم می‌شود)
    path('professor/<int:pk>/', views.professor_detail, name='professor_detail'),
    
    # دریافت داده‌های نمودار ارزیابی (جدید)
    path('professor/<int:professor_id>/chart-data/', views.get_evaluation_chart_data, name='evaluation_chart_data'),
    
    # سیستم رأی‌دهی
    path('vote-review/', views.vote_review, name='vote_review'),
    path('vote-answer/', views.vote_answer_ajax, name='vote_answer_ajax'),
    
    # جستجوی زنده
    path('live-search/', views.live_search_professors, name='live_search'),
    
    # آمار روزانه کاربر
    path('daily-stats/', views.user_daily_stats, name='user_daily_stats'),
    
    path('professor/<int:pk>/delete-evaluation/', views.delete_evaluation, name='delete_evaluation'),

    # احراز هویت
    path('login/', views.custom_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('signup/', views.signup, name='signup'),
    
    # جستجوی اساتید (صفحه جداگانه)
    path('search/', views.search_professors, name='search_professors'),
]