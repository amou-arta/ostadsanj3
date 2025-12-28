from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
import datetime
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

# =========================
# ثابت‌های سیستم
# =========================
DAILY_REVIEW_LIMIT = 3  # تغییر از ۴ به ۳
DAILY_QUESTION_LIMIT = 3  # تغییر از ۴ به ۳

# =========================
# Professor
# =========================
class Professor(models.Model):
    name = models.CharField(max_length=200, verbose_name=_("نام کامل"))
    department = models.CharField(max_length=200, blank=True, verbose_name=_("دانشکده/دپارتمان"))
    bio = models.TextField(blank=True, verbose_name=_("بیوگرافی"), 
                          help_text=_("توضیحاتی درباره سوابق تحصیلی، تخصص‌ها و افتخارات استاد"))
    image = models.ImageField(
        upload_to='professors/',
        blank=True,
        null=True,
        verbose_name=_("عکس پروفایل"),
        help_text=_("عکس با ابعاد مناسب (ترجیحاً مربعی) حداکثر 2MB")
    )
    
    class Meta:
        verbose_name = _("استاد")
        verbose_name_plural = _("اساتید")
        ordering = ['name']
    
    def __str__(self):
        return self.name

    @property
    def average_rating(self):
        approved_reviews = self.reviews.filter(is_approved=True)
        if approved_reviews.exists():
            return round(sum(r.rating for r in approved_reviews) / approved_reviews.count(), 1)
        return None

    def get_image_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return '/static/images/default-professor.png'


# =========================
# Review
# =========================
class Review(models.Model):
    professor = models.ForeignKey(
        Professor,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_("استاد")
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("کاربر"))
    text = models.TextField(verbose_name=_("متن نظر"))
    rating = models.PositiveSmallIntegerField(verbose_name=_("امتیاز"))
    is_approved = models.BooleanField(default=False, verbose_name=_("تأیید شده"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))

    class Meta:
        verbose_name = _("نظر")
        verbose_name_plural = _("نظرات")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.rating}"

    def likes_count(self):
        return self.votes.filter(value=1).count()

    def dislikes_count(self):
        return self.votes.filter(value=-1).count()


# =========================
# Review Vote
# =========================
class ReviewVote(models.Model):
    VOTE_CHOICES = (
        (1, 'موافق'),
        (-1, 'مخالف'),
    )

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='votes',
        verbose_name=_("نظر")
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("کاربر"))
    value = models.SmallIntegerField(choices=VOTE_CHOICES, verbose_name=_("رأی"))

    class Meta:
        verbose_name = _("رأی به نظر")
        verbose_name_plural = _("رأی‌ها به نظرات")
        unique_together = ('review', 'user')
    
    def __str__(self):
        return f"{self.user.username} رأی {self.value} به نظر {self.review.id}"


# =========================
# Question
# =========================
class Question(models.Model):
    professor = models.ForeignKey(
        Professor,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name=_("استاد")
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("کاربر"))
    text = models.TextField(verbose_name=_("متن پرسش"))
    is_approved = models.BooleanField(default=False, verbose_name=_("تأیید شده"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))

    class Meta:
        verbose_name = _("پرسش")
        verbose_name_plural = _("پرسش‌ها")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.text[:30]}"


# =========================
# Answer
# =========================
class Answer(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name=_("پرسش")
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("کاربر"))
    text = models.TextField(verbose_name=_("متن پاسخ"))
    is_approved = models.BooleanField(default=False, verbose_name=_("تأیید شده"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))

    class Meta:
        verbose_name = _("پاسخ")
        verbose_name_plural = _("پاسخ‌ها")
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.text[:30]}"

    def likes_count(self):
        return self.votes.filter(value=1).count()

    def dislikes_count(self):
        return self.votes.filter(value=-1).count()


# =========================
# Answer Vote
# =========================
class AnswerVote(models.Model):
    VOTE_CHOICES = (
        (1, 'موافق'),
        (-1, 'مخالف'),
    )

    answer = models.ForeignKey(
        Answer,
        on_delete=models.CASCADE,
        related_name='votes',
        verbose_name=_("پاسخ")
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("کاربر"))
    value = models.SmallIntegerField(choices=VOTE_CHOICES, verbose_name=_("رأی"))

    class Meta:
        verbose_name = _("رأی به پاسخ")
        verbose_name_plural = _("رأی‌ها به پاسخ‌ها")
        unique_together = ('answer', 'user')
    
    def __str__(self):
        return f"{self.user.username} رأی {self.value} به پاسخ {self.answer.id}"


# =========================
# Professor Evaluation (جدید)
# =========================
class ProfessorEvaluation(models.Model):
    """مدل برای ارزیابی کیفی استاد بر اساس ۶ پارامتر"""
    
    professor = models.ForeignKey(
        Professor,
        on_delete=models.CASCADE,
        related_name='evaluations',
        verbose_name=_("استاد")
    )
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        verbose_name=_("کاربر")
    )
    
    # پارامترهای ارزیابی (۱ تا ۵)
    teaching_method = models.PositiveSmallIntegerField(
        verbose_name=_("روش تدریس"),
        choices=[(i, f'{i} ستاره') for i in range(1, 6)],
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=3
    )
    
    grading_flexibility = models.PositiveSmallIntegerField(
        verbose_name=_("انعطاف پذیری در نمره دهی"),
        choices=[(i, f'{i} ستاره') for i in range(1, 6)],
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=3
    )
    
    exam_difficulty = models.PositiveSmallIntegerField(
        verbose_name=_("سختی امتحانات"),
        choices=[(i, f'{i} ستاره') for i in range(1, 6)],
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=3
    )
    
    subject_knowledge = models.PositiveSmallIntegerField(
        verbose_name=_("سواد در درس مربوطه"),
        choices=[(i, f'{i} ستاره') for i in range(1, 6)],
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=3
    )
    
    respect = models.PositiveSmallIntegerField(
        verbose_name=_("ادب و احترام"),
        choices=[(i, f'{i} ستاره') for i in range(1, 6)],
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=3
    )
    
    student_interaction = models.PositiveSmallIntegerField(
        verbose_name=_("تعامل با دانشجو"),
        choices=[(i, f'{i} ستاره') for i in range(1, 6)],
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=3
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("تاریخ به‌روزرسانی"))
    
    class Meta:
        verbose_name = _("ارزیابی کیفی")
        verbose_name_plural = _("ارزیابی‌های کیفی")
        unique_together = ('professor', 'user')  # هر کاربر یک ارزیابی برای هر استاد
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"ارزیابی {self.user.username} برای {self.professor.name}"
    
    # محاسبه میانگین کل ارزیابی
    @property
    def average_score(self):
        scores = [
            self.teaching_method,
            self.grading_flexibility,
            self.exam_difficulty,
            self.subject_knowledge,
            self.respect,
            self.student_interaction
        ]
        return round(sum(scores) / len(scores), 1)
    
    # آیا کاربر قبلاً این استاد را ارزیابی کرده؟
    @classmethod
    def user_has_evaluated(cls, professor, user):
        if not user.is_authenticated:
            return False
        return cls.objects.filter(professor=professor, user=user).exists()
    
    # گرفتن ارزیابی کاربر برای این استاد
    @classmethod
    def get_user_evaluation(cls, professor, user):
        if not user.is_authenticated:
            return None
        try:
            return cls.objects.get(professor=professor, user=user)
        except cls.DoesNotExist:
            return None
    
    # محاسبه میانگین هر پارامتر برای استاد
    @classmethod
    def get_professor_averages(cls, professor):
        evaluations = cls.objects.filter(professor=professor)
        if not evaluations.exists():
            return None
        
        parameter_names = {
            'teaching_method': 'روش تدریس',
            'grading_flexibility': 'انعطاف پذیری',
            'exam_difficulty': 'سختی امتحانات',
            'subject_knowledge': 'سواد علمی',
            'respect': 'ادب و احترام',
            'student_interaction': 'تعامل با دانشجو'
        }
        
        averages = {}
        for field, name in parameter_names.items():
            values = [getattr(eval_obj, field) for eval_obj in evaluations]
            if values:
                averages[field] = {
                    'name': name,
                    'average': round(sum(values) / len(values), 1),
                    'count': len(values),
                    'values': values  # برای نمودار توزیع
                }
        
        return averages


# =========================
# User Daily Limit
# =========================
class UserDailyLimit(models.Model):
    """مدل برای ذخیره محدودیت روزانه کاربران"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("کاربر"))
    date = models.DateField(default=datetime.date.today, verbose_name=_("تاریخ"))
    review_count = models.IntegerField(default=0, verbose_name=_("تعداد نظرات"))
    question_count = models.IntegerField(default=0, verbose_name=_("تعداد پرسش‌ها"))
    
    class Meta:
        verbose_name = _("محدودیت روزانه")
        verbose_name_plural = _("محدودیت‌های روزانه")
        unique_together = ('user', 'date')
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"
    
    @property
    def can_post_review(self):
        return self.review_count < DAILY_REVIEW_LIMIT
    
    @property
    def can_post_question(self):
        return self.question_count < DAILY_QUESTION_LIMIT
    
    @classmethod
    def get_or_create_today(cls, user):
        """دریافت یا ایجاد رکورد محدودیت برای کاربر امروز"""
        today = datetime.date.today()
        obj, created = cls.objects.get_or_create(
            user=user,
            date=today,
            defaults={'review_count': 0, 'question_count': 0}
        )
        return obj
    
    def increment_review(self):
        """افزایش شمارنده نظرات"""
        if self.review_count < DAILY_REVIEW_LIMIT:
            self.review_count += 1
            self.save()
            return True
        return False
    
    def increment_question(self):
        """افزایش شمارنده پرسش‌ها"""
        if self.question_count < DAILY_QUESTION_LIMIT:
            self.question_count += 1
            self.save()
            return True
        return False
    
    def decrement_review(self):
        """کاهش شمارنده نظرات (برای وقتی که نظر حذف می‌شود)"""
        if self.review_count > 0:
            self.review_count -= 1
            self.save()
            return True
        return False
    
    def decrement_question(self):
        """کاهش شمارنده پرسش‌ها (برای وقتی که پرسش حذف می‌شود)"""
        if self.question_count > 0:
            self.question_count -= 1
            self.save()
            return True
        return False


# =========================
# سیگنال‌ها برای کاهش شمارنده هنگام حذف
# =========================

@receiver(post_delete, sender=Review)
def decrease_review_count_on_delete(sender, instance, **kwargs):
    """هنگام حذف نظر، review_count کاربر را کاهش بده"""
    try:
        # پیدا کردن رکورد محدودیت برای روز ایجاد نظر
        limit_date = instance.created_at.date()
        daily_limit = UserDailyLimit.objects.filter(
            user=instance.user,
            date=limit_date
        ).first()
        
        if daily_limit:
            daily_limit.decrement_review()
            print(f"✓ کاهش review_count برای کاربر {instance.user.username} در تاریخ {limit_date}")
    except Exception as e:
        print(f"✗ خطا در کاهش review_count: {e}")


@receiver(post_delete, sender=Question)
def decrease_question_count_on_delete(sender, instance, **kwargs):
    """هنگام حذف پرسش، question_count کاربر را کاهش بده"""
    try:
        # پیدا کردن رکورد محدودیت برای روز ایجاد پرسش
        limit_date = instance.created_at.date()
        daily_limit = UserDailyLimit.objects.filter(
            user=instance.user,
            date=limit_date
        ).first()
        
        if daily_limit:
            daily_limit.decrement_question()
            print(f"✓ کاهش question_count برای کاربر {instance.user.username} در تاریخ {limit_date}")
    except Exception as e:
        print(f"✗ خطا در کاهش question_count: {e}")


# =========================
# تابع برای رفع مشکل داده‌های فعلی
# =========================
def fix_current_daily_limits():
    """رفع مشکل محدودیت‌های روزانه فعلی"""
    from django.db.models import Count
    
    print("در حال رفع مشکل محدودیت‌های روزانه...")
    
    # برای هر کاربر
    for user in User.objects.all():
        # پیدا کردن همه رکوردهای محدودیت
        daily_limits = UserDailyLimit.objects.filter(user=user)
        
        for daily_limit in daily_limits:
            # شمارش واقعی نظرات در آن تاریخ
            actual_review_count = Review.objects.filter(
                user=user,
                created_at__date=daily_limit.date
            ).count()
            
            # شمارش واقعی پرسش‌ها در آن تاریخ
            actual_question_count = Question.objects.filter(
                user=user,
                created_at__date=daily_limit.date
            ).count()
            
            # اگر اختلاف وجود داشت، اصلاح کن
            if daily_limit.review_count != actual_review_count:
                print(f"اصلاح review_count کاربر {user.username} در {daily_limit.date}: {daily_limit.review_count} → {actual_review_count}")
                daily_limit.review_count = actual_review_count
            
            if daily_limit.question_count != actual_question_count:
                print(f"اصلاح question_count کاربر {user.username} در {daily_limit.date}: {daily_limit.question_count} → {actual_question_count}")
                daily_limit.question_count = actual_question_count
            
            daily_limit.save()
    
    print("✓ رفع مشکل محدودیت‌های روزانه تکمیل شد.")