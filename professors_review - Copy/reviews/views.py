from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
import datetime
import json
import logging

from .models import Professor, Review, Question, Answer, AnswerVote, ReviewVote, UserDailyLimit, ProfessorEvaluation
from .forms import ReviewForm, QuestionForm, AnswerForm, SignUpForm, ProfessorSearchForm, LoginForm, ProfessorEvaluationForm

# =========================
# ثابت‌های سیستم
# =========================
DAILY_REVIEW_LIMIT = 3
DAILY_QUESTION_LIMIT = 3

# =========================
# Setup logging
# =========================
logger = logging.getLogger(__name__)

# =========================
# Helper Functions
# =========================
def check_daily_limit(user, limit_type):
    """بررسی محدودیت روزانه کاربر"""
    try:
        daily_limit = UserDailyLimit.get_or_create_today(user)
        
        if limit_type == 'review':
            if not daily_limit.can_post_review:
                return False, f"شما امروز {DAILY_REVIEW_LIMIT} نظر ارسال کرده‌اید. فردا مجدد تلاش کنید."
            return True, "مجاز"
        
        elif limit_type == 'question':
            if not daily_limit.can_post_question:
                return False, f"شما امروز {DAILY_QUESTION_LIMIT} پرسش ارسال کرده‌اید. فردا مجدد تلاش کنید."
            return True, "مجاز"
        
    except Exception as e:
        logger.error(f"خطا در بررسی محدودیت روزانه کاربر {user.id}: {e}")
        return False, "خطا در سیستم. لطفاً با پشتیبانی تماس بگیرید."


# =========================
# Home + Search
# =========================
def home(request):
    query = request.GET.get('query', '').strip()
    professors = Professor.objects.all()
    if query:
        professors = professors.filter(
            Q(name__icontains=query) | Q(department__icontains=query)
        )
    return render(request, 'reviews/home.html', {
        'professors': professors,
        'query': query
    })


# =========================
# Signup
# =========================
def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'ثبت‌نام با موفقیت انجام شد!')
            return redirect('reviews:home')
        else:
            messages.error(request, 'لطفاً خطاهای زیر را اصلاح کنید.')
    else:
        form = SignUpForm()
    
    challenge_question = form.get_challenge_question() if hasattr(form, 'get_challenge_question') else ''
    
    return render(request, 'reviews/signup.html', {
        'form': form,
        'challenge_question': challenge_question
    })


# =========================
# Login
# =========================
def custom_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, 'ورود موفقیت‌آمیز بود!')
                return redirect('reviews:home')
        else:
            pass
    else:
        form = LoginForm()
    
    challenge_question = form.get_challenge_question() if hasattr(form, 'get_challenge_question') else ''
    
    return render(request, 'reviews/login.html', {
        'form': form,
        'challenge_question': challenge_question
    })


# =========================
# Search Professors
# =========================
def search_professors(request):
    form = ProfessorSearchForm(request.GET or None)
    results = None
    
    if form.is_valid():
        query = form.cleaned_data['query']
        if query:
            results = Professor.objects.filter(
                Q(name__icontains=query) | Q(department__icontains=query)
            )
        else:
            # اگر جستجو خالی بود، همه نتایج را نشان نده
            results = Professor.objects.none()
    
    return render(request, 'reviews/search.html', {
        'form': form,
        'results': results
    })


# =========================
# Helper functions for professor_detail
# =========================
def _handle_review_form(request, professor, review_form):
    """پردازش فرم نظر"""
    can_post, limit_message = check_daily_limit(request.user, 'review')
    
    if not can_post:
        return False, limit_message
    
    if review_form.is_valid():
        existing_review = Review.objects.filter(
            user=request.user,
            professor=professor,
            text=review_form.cleaned_data['text'],
            rating=review_form.cleaned_data['rating'],
            created_at__date=datetime.date.today()
        ).first()
        
        if existing_review:
            return False, 'این نظر قبلاً ثبت شده است.'
        
        review = review_form.save(commit=False)
        review.professor = professor
        review.user = request.user
        review.is_approved = False
        review.save()
        
        daily_limit = UserDailyLimit.get_or_create_today(request.user)
        daily_limit.increment_review()
        
        return True, 'نظر شما ثبت شد و پس از تأیید نمایش داده می‌شود.'
    else:
        return False, 'لطفاً خطاهای فرم را اصلاح کنید.'


def _handle_question_form(request, professor, question_form):
    """پردازش فرم پرسش"""
    can_post, limit_message = check_daily_limit(request.user, 'question')
    
    if not can_post:
        return False, limit_message
    
    if question_form.is_valid():
        existing_question = Question.objects.filter(
            user=request.user,
            professor=professor,
            text=question_form.cleaned_data['text'],
            created_at__date=datetime.date.today()
        ).first()
        
        if existing_question:
            return False, 'این پرسش قبلاً ثبت شده است.'
        
        question = question_form.save(commit=False)
        question.professor = professor
        question.user = request.user
        question.is_approved = False
        question.save()
        
        daily_limit = UserDailyLimit.get_or_create_today(request.user)
        daily_limit.increment_question()
        
        return True, 'پرسش شما ثبت شد و پس از تأیید نمایش داده می‌شود.'
    else:
        return False, 'لطفاً خطاهای فرم را اصلاح کنید.'


def _handle_answer_form(request, professor, answer_form):
    """پردازش فرم پاسخ"""
    try:
        question = Question.objects.get(
            id=request.POST.get('question_id'),
            professor=professor,
            is_approved=True
        )
    except Question.DoesNotExist:
        return False, 'پرسش مورد نظر یافت نشد.'
    
    if answer_form.is_valid():
        existing_answer = Answer.objects.filter(
            user=request.user,
            question=question,
            text=answer_form.cleaned_data['text'],
            created_at__date=datetime.date.today()
        ).first()
        
        if existing_answer:
            return False, 'این پاسخ قبلاً ثبت شده است.'
        
        answer = answer_form.save(commit=False)
        answer.question = question
        answer.user = request.user
        answer.is_approved = False
        answer.save()
        return True, 'پاسخ شما ثبت شد و پس از تأیید نمایش داده می‌شود.'
    else:
        return False, 'لطفاً خطاهای فرم را اصلاح کنید.'


def _handle_evaluation_form(request, professor, user_evaluation, evaluation_form):
    """پردازش فرم ارزیابی"""
    if evaluation_form.is_valid():
        evaluation = evaluation_form.save(commit=False)
        evaluation.professor = professor
        evaluation.user = request.user
        
        if user_evaluation:
            evaluation.id = user_evaluation.id
            evaluation.created_at = user_evaluation.created_at
            message_text = 'ارزیابی شما با موفقیت به‌روزرسانی شد.'
        else:
            message_text = 'ارزیابی شما با موفقیت ثبت شد.'
        
        evaluation.save()
        return True, message_text
    else:
        return False, 'لطفاً خطاهای فرم را اصلاح کنید.'


# =========================
# Professor Detail
# =========================
@login_required
def professor_detail(request, pk):
    professor = get_object_or_404(Professor, pk=pk)

    # استفاده از select_related و prefetch_related برای بهبود performance
    reviews = Review.objects.filter(
        professor=professor,
        is_approved=True
    ).select_related('user').prefetch_related('votes').order_by('-created_at')

    questions = Question.objects.filter(
        professor=professor,
        is_approved=True
    ).select_related('user').prefetch_related(
        'answers', 'answers__user', 'answers__votes'
    ).order_by('-created_at')

    for question in questions:
        question.answers_approved = question.answers.filter(is_approved=True)

    review_form = ReviewForm()
    question_form = QuestionForm()
    answer_form = AnswerForm()
    evaluation_form = ProfessorEvaluationForm()
    
    # بررسی ارزیابی کاربر
    user_evaluation = None
    user_evaluation = ProfessorEvaluation.get_user_evaluation(professor, request.user)
    if user_evaluation:
        evaluation_form = ProfessorEvaluationForm(instance=user_evaluation)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'review':
            review_form = ReviewForm(request.POST)
            success, message = _handle_review_form(request, professor, review_form)
            if success:
                messages.success(request, message)
                return redirect('reviews:professor_detail', pk=pk)
            else:
                messages.error(request, message)

        elif form_type == 'question':
            question_form = QuestionForm(request.POST)
            success, message = _handle_question_form(request, professor, question_form)
            if success:
                messages.success(request, message)
                return redirect('reviews:professor_detail', pk=pk)
            else:
                messages.error(request, message)

        elif form_type == 'answer':
            answer_form = AnswerForm(request.POST)
            success, message = _handle_answer_form(request, professor, answer_form)
            if success:
                messages.success(request, message)
                return redirect('reviews:professor_detail', pk=pk)
            else:
                messages.error(request, message)

        elif form_type == 'evaluation':
            evaluation_form = ProfessorEvaluationForm(request.POST, instance=user_evaluation)
            success, message = _handle_evaluation_form(request, professor, user_evaluation, evaluation_form)
            if success:
                messages.success(request, message)
                # استفاده از HttpResponseRedirect به جای redirect برای اضافه کردن query parameter
                return HttpResponseRedirect(
                    reverse('reviews:professor_detail', args=[pk]) + '?tab=evaluation'
                )
            else:
                messages.error(request, message)

    # محاسبه محدودیت‌های روزانه
    daily_limit = UserDailyLimit.get_or_create_today(request.user)
    review_limit_info = {
        'remaining': DAILY_REVIEW_LIMIT - daily_limit.review_count,
        'total': DAILY_REVIEW_LIMIT,
        'reached_limit': daily_limit.review_count >= DAILY_REVIEW_LIMIT
    }
    
    question_limit_info = {
        'remaining': DAILY_QUESTION_LIMIT - daily_limit.question_count,
        'total': DAILY_QUESTION_LIMIT,
        'reached_limit': daily_limit.question_count >= DAILY_QUESTION_LIMIT
    }

    # محاسبه داده‌های نمودار
    chart_data = None
    has_evaluations = False
    total_evaluations = 0
    
    # بررسی وجود ارزیابی‌ها برای نمودار
    evaluation_averages = ProfessorEvaluation.get_professor_averages(professor)
    
    if evaluation_averages:
        has_evaluations = True
        # محاسبه total_evaluations به صورت ایمن
        evaluation_values = list(evaluation_averages.values())
        if evaluation_values:
            total_evaluations = evaluation_values[0]['count']
        
        # آماده‌سازی داده‌های نمودار
        chart_data = {
            'labels': [avg['name'] for avg in evaluation_averages.values()],
            'averages': [avg['average'] for avg in evaluation_averages.values()],
            'counts': [avg['count'] for avg in evaluation_averages.values()],
            'max_value': 5,
            'min_value': 1,
            'total_evaluations': total_evaluations,
        }

    context = {
        'professor': professor,
        'reviews': reviews,
        'questions': questions,
        'review_form': review_form,
        'question_form': question_form,
        'answer_form': answer_form,
        'evaluation_form': evaluation_form,
        'user_evaluation': user_evaluation,
        'review_limit': review_limit_info,
        'question_limit': question_limit_info,
        'DAILY_REVIEW_LIMIT': DAILY_REVIEW_LIMIT,
        'DAILY_QUESTION_LIMIT': DAILY_QUESTION_LIMIT,
        'chart_data_json': json.dumps(chart_data, ensure_ascii=False) if chart_data else '{}',
        'has_evaluations': has_evaluations,
        'total_evaluations': total_evaluations,
    }
    
    return render(request, 'reviews/professor_detail.html', context)


# =========================
# Vote Review (AJAX)
# =========================
@login_required
@csrf_protect
def vote_review(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    review_id = request.POST.get("review_id")
    value = request.POST.get("value")
    
    if not review_id or not value:
        return JsonResponse({"error": "Missing parameters"}, status=400)
    
    try:
        value = int(value)
        if value not in (1, -1):
            return JsonResponse({"error": "Invalid value"}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Value must be integer"}, status=400)

    try:
        review = Review.objects.get(id=review_id, is_approved=True)
    except Review.DoesNotExist:
        return JsonResponse({"error": "Review not found or not approved"}, status=404)

    vote, created = ReviewVote.objects.get_or_create(
        review=review,
        user=request.user,
        defaults={"value": value}
    )

    if not created and vote.value == value:
        vote.delete()
    else:
        vote.value = value
        vote.save()

    likes_count = review.likes_count()
    dislikes_count = review.dislikes_count()

    return JsonResponse({
        "success": True,
        "likes_count": likes_count,
        "dislikes_count": dislikes_count
    })


# =========================
# Vote Answer (AJAX)
# =========================
@login_required
@csrf_protect
def vote_answer_ajax(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    answer_id = request.POST.get("answer_id")
    value = request.POST.get("value")
    
    if not answer_id or not value:
        return JsonResponse({"error": "Missing parameters"}, status=400)
    
    try:
        value = int(value)
        if value not in (1, -1):
            return JsonResponse({"error": "Invalid value"}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Value must be integer"}, status=400)

    try:
        answer = Answer.objects.get(id=answer_id, is_approved=True)
    except Answer.DoesNotExist:
        return JsonResponse({"error": "Answer not found or not approved"}, status=404)

    vote, created = AnswerVote.objects.get_or_create(
        answer=answer,
        user=request.user,
        defaults={"value": value}
    )

    if not created and vote.value == value:
        vote.delete()
    else:
        vote.value = value
        vote.save()

    likes_count = answer.likes_count()
    dislikes_count = answer.dislikes_count()

    return JsonResponse({
        "success": True,
        "likes_count": likes_count,
        "dislikes_count": dislikes_count
    })


# =========================
# Live Search
# =========================
def live_search_professors(request):
    query = request.GET.get('query', '').strip()
    professors = Professor.objects.all()
    if query:
        professors = professors.filter(
            Q(name__icontains=query) | Q(department__icontains=query)
        )[:10]  # محدود کردن نتایج برای performance

    html = render_to_string(
        'reviews/partials/professor_list.html',
        {'professors': professors},
        request=request
    )
    return JsonResponse({'html': html})


# =========================
# User Daily Stats
# =========================
@login_required
def user_daily_stats(request):
    """نمایش آمار روزانه کاربر"""
    try:
        daily_limit = UserDailyLimit.get_or_create_today(request.user)
        
        return JsonResponse({
            'success': True,
            'review_count': daily_limit.review_count,
            'question_count': daily_limit.question_count,
            'review_remaining': DAILY_REVIEW_LIMIT - daily_limit.review_count,
            'question_remaining': DAILY_QUESTION_LIMIT - daily_limit.question_count,
            'date': daily_limit.date.isoformat()
        })
    except Exception as e:
        logger.error(f"خطا در دریافت آمار روزانه کاربر {request.user.id}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'خطا در دریافت آمار'
        }, status=500)

# =========================
# Delete Evaluation
# =========================
@login_required
def delete_evaluation(request, pk):
    """حذف ارزیابی کاربر"""
    if request.method == 'POST':
        try:
            evaluation = ProfessorEvaluation.objects.get(
                professor_id=pk,
                user=request.user
            )
            evaluation.delete()
            messages.success(request, 'ارزیابی شما با موفقیت حذف شد.')
            return HttpResponseRedirect(
                reverse('reviews:professor_detail', args=[pk]) + '?tab=evaluation'
            )
        except ProfessorEvaluation.DoesNotExist:
            messages.error(request, 'ارزیابی یافت نشد.')
            return HttpResponseRedirect(
                reverse('reviews:professor_detail', args=[pk]) + '?tab=evaluation'
            )
        except Exception as e:
            logger.error(f"خطا در حذف ارزیابی کاربر {request.user.id}: {e}")
            messages.error(request, 'خطا در حذف ارزیابی. لطفاً مجدد تلاش کنید.')
            return HttpResponseRedirect(
                reverse('reviews:professor_detail', args=[pk]) + '?tab=evaluation'
            )
    
    # اگر روش GET باشد، کاربر را به صفحه استاد هدایت کن
    return redirect('reviews:professor_detail', pk=pk)

# =========================
# Get Evaluation Chart Data (AJAX)
# =========================
def get_evaluation_chart_data(request, professor_id):
    """دریافت داده‌های نمودار ارزیابی به صورت AJAX"""
    try:
        professor = get_object_or_404(Professor, pk=professor_id)
        evaluation_averages = ProfessorEvaluation.get_professor_averages(professor)
        
        if not evaluation_averages:
            return JsonResponse({
                'success': True,
                'has_data': False,
                'message': 'هنوز ارزیابی‌ای برای این استاد ثبت نشده است.'
            })
        
        # محاسبه ایمن total_evaluations
        total_evaluations = 0
        evaluation_values = list(evaluation_averages.values())
        if evaluation_values:
            total_evaluations = evaluation_values[0]['count']
        
        chart_data = {
            'success': True,
            'has_data': True,
            'labels': [avg['name'] for avg in evaluation_averages.values()],
            'averages': [avg['average'] for avg in evaluation_averages.values()],
            'counts': [avg['count'] for avg in evaluation_averages.values()],
            'max_value': 5,
            'min_value': 1,
            'total_evaluations': total_evaluations,
        }
        
        return JsonResponse(chart_data)
    except Exception as e:
        logger.error(f"خطا در دریافت داده‌های نمودار ارزیابی استاد {professor_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'خطا در دریافت داده‌ها'
        }, status=500)